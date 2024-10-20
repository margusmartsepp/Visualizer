import warnings

# Suppress specific UserWarning from pywinauto
warnings.filterwarnings("ignore", category=UserWarning, message="Revert to STA COM threading mode")
# Suppress all DeprecationWarnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import os
import sys
import logging
import argparse
import shutil
import threading
from datetime import datetime
from flask import Flask, send_file, jsonify, request
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QMessageBox, QLineEdit, QFormLayout, QFileDialog, QCheckBox, QTabWidget, QSystemTrayIcon, QMenu, QAction, QWidget, QSizePolicy
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices
from PIL import Image
import mss
import mss.tools
import dxcam
from pywinauto import Desktop
import qt_material

# =========================
# Configuration
# =========================
DEFAULT_FLASK_HOST = '127.0.0.1'
DEFAULT_FLASK_PORT = 5000
INTERVAL_SECONDS = 3

# =========================
# Logging Configuration
# =========================
logging.basicConfig(
    filename='screenshot_viewer.log',
    level=logging.DEBUG,
    format='%(asctime)s:%(levelname)s:%(message)s'
)

# =========================
# Flask Application and API Handlers
# =========================
class FlaskApp:
    def __init__(self, screenshot_manager, host=DEFAULT_FLASK_HOST, port=DEFAULT_FLASK_PORT):
        self.app = Flask(__name__)
        self.screenshot_manager = screenshot_manager
        self.host = host
        self.port = port
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/screenshot', methods=['GET'])
        def get_screenshot():
            screenshot_path = self.screenshot_manager.file_path
            if os.path.exists(screenshot_path):
                try:
                    logging.info("Screenshot requested.")
                    return send_file(screenshot_path, mimetype='image/png')
                except Exception as e:
                    logging.error(f"Error in /screenshot: {e}")
                    return jsonify({'error': str(e)}), 500
            else:
                logging.warning("No screenshot available.")
                return jsonify({'error': 'No screenshot available.'}), 404

        @self.app.route('/metadata', methods=['GET'])
        def get_metadata():
            screenshot_path = self.screenshot_manager.file_path
            if os.path.exists(screenshot_path):
                try:
                    timestamp = datetime.fromtimestamp(os.path.getmtime(screenshot_path)).strftime("%Y-%m-%d %H:%M:%S")
                    with Image.open(screenshot_path) as img:
                        width, height = img.size
                    return jsonify({'timestamp': timestamp, 'dimensions': f"{width}x{height}"}), 200
                except Exception as e:
                    logging.error(f"Error in /metadata: {e}")
                    return jsonify({'error': str(e)}), 500
            else:
                return jsonify({'error': 'No screenshot available.'}), 404

        @self.app.route('/status', methods=['GET'])
        def get_status():
            return jsonify({'status': 'running'}), 200
        
        @self.app.route('/viewer', methods=['GET'])
        def viewer():
            """Endpoint to serve the HTML viewer page."""
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Live Screenshot Viewer</title>
                <style>
                    body {{
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background-color: #f0f0f0;
                    }}
                    img {{
                        max-width: 90%;
                        max-height: 90%;
                        border: 2px solid #ccc;
                        box-shadow: 0 0 10px rgba(0,0,0,0.5);
                    }}
                </style>
            </head>
            <body>
                <img id="screenshot" src="/screenshot?timestamp={int(datetime.now().timestamp() * 1000)}" alt="Latest Screenshot">
                
                <script>
                    // Function to refresh the image
                    function refreshImage() {{
                        var img = document.getElementById('screenshot');
                        var timestamp = new Date().getTime();
                        img.src = '/screenshot?timestamp=' + timestamp;
                    }}

                    // Refresh the image every {INTERVAL_SECONDS} seconds
                    setInterval(refreshImage, {INTERVAL_SECONDS * 1000});
                </script>
            </body>
            </html>
            """
            logging.info("Viewer page requested via /viewer endpoint.")
            return html_content

        @self.app.route('/shutdown', methods=['POST'])
        def shutdown_server():
            """Endpoint to shutdown the Flask server."""
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                logging.error("Shutdown attempted, but not running with the Werkzeug Server.")
                return jsonify({'error': 'Not running with the Werkzeug Server'}), 500
            func()
            logging.info("Server shutting down via /shutdown endpoint.")
            return jsonify({'message': 'Server shutting down...'}), 200
        
class FlaskAppThread(threading.Thread):
    def __init__(self, flask_app):
        super().__init__()
        self.flask_app = flask_app
        self.daemon = True

    def run(self):
        logging.info(f"Starting Flask server on {self.flask_app.host}:{self.flask_app.port}")
        self.flask_app.app.run(host=self.flask_app.host, port=self.flask_app.port, threaded=True)

# =========================
# Screenshot Manager and Capture Functions
# =========================

def capture_full_screen(output_path):
    """Capture the primary monitor's full screen."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Primary monitor
        screenshot = sct.grab(monitor)
        mss.tools.to_png(screenshot.rgb, screenshot.size, output=output_path)
    logging.info(f"Captured full screen: {output_path}")
    return output_path

def capture_specific_monitor(monitor_index, output_path):
    """Capture a specific monitor based on index."""
    with mss.mss() as sct:
        monitors = sct.monitors
        if monitor_index < 1 or monitor_index > len(monitors) - 1:
            raise ValueError("Invalid monitor index.")
        monitor = monitors[monitor_index]
        screenshot = sct.grab(monitor)
        mss.tools.to_png(screenshot.rgb, screenshot.size, output=output_path)
    logging.info(f"Captured monitor {monitor_index}: {output_path}")
    return output_path

def capture_window(title, output_path):
    """Capture a specific application window."""
    try:
        # Connect to the window
        app = Desktop(backend="uia").window(title=title)
        # Bring window to the foreground
        app.set_focus()
        # Get window rectangle
        rect = app.rectangle()
        bbox = {
            "top": rect.top,
            "left": rect.left,
            "width": rect.width(),
            "height": rect.height(),
        }
        with mss.mss() as sct:
            screenshot = sct.grab(bbox)
            mss.tools.to_png(screenshot.rgb, screenshot.size, output=output_path)
        logging.info(f"Captured window '{title}': {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"Error capturing window '{title}': {e}")
        return None

def capture_directx_game(game_title, output_path):
    """Capture a DirectX game window."""
    try:
        # Initialize dxcam
        cam = dxcam.create()
        # Set the window to capture
        cam.set_window(game_title)
        # Capture frame
        frame = cam.grab()
        # Convert to PIL Image
        img = Image.fromarray(frame)
        img.save(output_path)
        logging.info(f"Captured DirectX game '{game_title}': {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"Error capturing DirectX game '{game_title}': {e}")
        return None

def capture_browser_tab(tab_title, output_path):
    """Capture a specific browser tab based on window title."""
    try:
        return capture_window(tab_title, output_path)
    except Exception as e:
        logging.error(f"Error capturing browser tab '{tab_title}': {e}")
        return None
# =========================
# Screenshot Manager and Capture Functions
# =========================
class ScreenshotManager:
    """
    Manages screenshot capturing and saving.
    Separates business logic from UI.
    """
    def __init__(self, reuse_same_image=True, directory=None, selected_mode="Full Screen"):
        # Default directory set to 'Images' subfolder if no directory is provided
        if directory is None:
            self.custom_directory = os.path.join(os.getcwd(), 'Images')
        else:
            self.custom_directory = directory
        
        self.reuse_same_image = reuse_same_image
        self.selected_mode = selected_mode
        self.file_name = self.get_base_filename()  # Base file name for reuse
        self.file_path = os.path.join(self.custom_directory, self.file_name)
        self.INTERVAL_SECONDS = INTERVAL_SECONDS  # Set from config.py

        # Ensure the directory exists
        os.makedirs(self.custom_directory, exist_ok=True)
        logging.info(f"ScreenshotManager initialized with path: {self.file_path} and interval: {self.INTERVAL_SECONDS} seconds.")

    def get_base_filename(self):
        """Generate base file name based on capture mode."""
        base_name = ''.join(e for e in self.selected_mode if e.isalnum())
        return f"{base_name}.png"

    def get_unique_filename(self):
        """Generate unique file name with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        return f"{timestamp}.png"

    def capture_and_save(self, capture_function):
        """
        Capture a screenshot using the provided function, save it with a timestamped filename
        or to a single file based on the reuse mode, and return the necessary data for signal emission.

        :param capture_function: The function to capture the screenshot.
        :return: Tuple containing path, width, height, timestamp.
        """
        try:
            # Capture the screenshot
            path = capture_function()
            if path:
                # Get screenshot dimensions
                with mss.mss() as sct:
                    screenshot = sct.grab(sct.monitors[1])  # Assuming primary monitor
                    width = screenshot.width
                    height = screenshot.height

                # Generate timestamp with seconds precision
                timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

                if self.reuse_same_image:
                    # If reuse is enabled, no need to copy if the source and destination are the same
                    if path != self.file_path:
                        shutil.copy(path, self.file_path)
                    logging.info(f"Screenshot saved to reused file: {self.file_path}")
                    return (self.file_path, width, height, timestamp)
                else:
                    # Create unique filename with timestamp
                    unique_filename = self.get_unique_filename()
                    unique_file_path = os.path.join(self.custom_directory, unique_filename)

                    # Copy to unique_file_path
                    shutil.copy(path, unique_file_path)
                    logging.info(f"Screenshot saved: {unique_file_path}")

                    return (unique_file_path, width, height, timestamp)
            else:
                logging.warning("Capture function returned None.")
                return None
        except Exception as e:
            logging.error(f"Error during capture and save: {e}")
            return None

# =========================
# Screenshot Window (UI)
# =========================
class ScreenshotDisplayWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Latest Screenshot")
        self.setGeometry(1500, 100, 400, 300)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        central_widget = QWidget()
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label)

        close_button = QPushButton("X")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, alignment=Qt.AlignRight)

    def update_image(self, image_path):
        if not os.path.exists(image_path):
            self.image_label.setText("No Screenshot")
            return
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.image_label.setText("Failed to Load Image")
        else:
            self.image_label.setPixmap(pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio))

class ScreenshotEmitter(QObject):
    screenshot_signal = pyqtSignal(str, int, int, str)  # path, width, height, timestamp
    copy_to_clipboard_signal = pyqtSignal()

class ScreenshotWindow(QMainWindow):
    def __init__(self, screenshot_manager, args):
        super().__init__()

        import pythoncom
        pythoncom.CoInitialize()

        self.screenshot_manager = screenshot_manager
        self.emitter = ScreenshotEmitter()
        self.emitter.screenshot_signal.connect(self.update_image)
        self.emitter.copy_to_clipboard_signal.connect(self.copy_to_clipboard)
        self.capturing = False
        self.host = args.host
        self.port = args.port
        self.latest_timestamp = ""
        self.latest_dimensions = ""

        self.floating_window = ScreenshotDisplayWindow()
        self.floating_window.hide()

        self.init_ui()
        self.apply_initial_configurations(args)
        self.init_system_tray()

    def init_ui(self):
        self.setWindowTitle("Visualizer - Live Screenshot Viewer")
        self.setGeometry(100, 100, 800, 600)

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        capture_controls_layout = QHBoxLayout()
        self.capture_mode_combo = QComboBox()
        self.capture_mode_combo.addItems([
            "Full Screen", "Specific Application", "Specific Monitor", "DirectX Game", "Specific Browser Tab"
        ])
        capture_controls_layout.addWidget(QLabel("Capture Mode:"))
        capture_controls_layout.addWidget(self.capture_mode_combo)
        capture_controls_layout.addStretch()
        self.toggle_capture_button = QPushButton("Start Capturing")
        self.toggle_capture_button.setCheckable(True)
        self.toggle_capture_button.clicked.connect(self.toggle_capturing)
        capture_controls_layout.addWidget(self.toggle_capture_button)

        main_layout.addLayout(capture_controls_layout)

        self.image_label = QLabel("No Screenshot")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedSize(780, 400)
        self.image_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.image_label.setStyleSheet("background-color: #eee; border: 1px solid #ccc;")
        main_layout.addWidget(self.image_label)

        self.tabs = QTabWidget()
        self.init_settings_tab()
        main_layout.addWidget(self.tabs)

    def init_settings_tab(self):
        """Initialize the Settings tab with relevant controls."""
        settings_tab = QWidget()
        settings_layout = QVBoxLayout()
        settings_tab.setLayout(settings_layout)

        # Configuration Form
        config_form = QFormLayout()

        # Host and Port on the same line
        host_port_layout = QHBoxLayout()
        self.host_input = QLineEdit(DEFAULT_FLASK_HOST)
        self.port_input = QLineEdit(str(DEFAULT_FLASK_PORT))

        host_port_layout.addWidget(QLabel("Flask Host:"))
        host_port_layout.addWidget(self.host_input)

        host_port_layout.addWidget(QLabel("Port:"))
        host_port_layout.addWidget(self.port_input)

        open_viewer_button = QPushButton("Open Viewer")
        open_viewer_button.clicked.connect(self.open_viewer_in_browser)
        
        open_screenshot_button = QPushButton("Open Screenshot")
        open_screenshot_button.clicked.connect(self.open_latest_screenshot_in_browser)
        
        host_port_layout.addWidget(open_viewer_button)
        host_port_layout.addWidget(open_screenshot_button)

        config_form.addRow(host_port_layout)

        # Directory Input
        self.directory_input = QLineEdit(os.getcwd())
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_directory)
        directory_layout = QHBoxLayout()
        self.reuse_checkbox = QCheckBox("Reuse Same Image")
        self.reuse_checkbox.setChecked(True)  # Enabled by default
        directory_layout.addWidget(self.reuse_checkbox)
        directory_layout.addWidget(self.directory_input)
        directory_layout.addWidget(browse_button)

        config_form.addRow("", directory_layout)

        settings_layout.addLayout(config_form)

        # Theme Selection
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Select Theme:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(qt_material.list_themes())
        apply_button = QPushButton("Apply Settings")
        apply_button.clicked.connect(self.apply_settings)
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addWidget(apply_button)
        settings_layout.addLayout(theme_layout)

        # Add Settings Tab to Tabs
        self.tabs.addTab(settings_tab, "Settings")

    def open_viewer_in_browser(self):
        """Open the viewer page in the default browser."""
        viewer_url = f"http://{self.host_input.text()}:{self.port_input.text()}/viewer"
        QDesktopServices.openUrl(QUrl(viewer_url))

    def open_latest_screenshot_in_browser(self):
        """Open the latest screenshot in the default browser."""
        screenshot_url = f"http://{self.host_input.text()}:{self.port_input.text()}/screenshot"
        QDesktopServices.openUrl(QUrl(screenshot_url))

    def apply_initial_configurations(self, args):
        self.host_input.setText(self.host)
        self.port_input.setText(str(self.port))
        self.reuse_checkbox.setChecked(self.screenshot_manager.reuse_same_image)
        self.directory_input.setText(self.screenshot_manager.custom_directory)
        if args.start:
            self.toggle_capture_button.setChecked(True)
            self.toggle_capture_button.setText("Stop Capturing")
            self.start_capturing()

    def apply_settings(self):
        try:
            new_host = self.host_input.text()
            new_port = int(self.port_input.text())
            self.host = new_host
            self.port = new_port
            self.screenshot_manager.reuse_same_image = self.reuse_checkbox.isChecked()
            new_directory = self.directory_input.text()
            self.screenshot_manager.custom_directory = new_directory
            self.screenshot_manager.file_path = os.path.join(new_directory, self.screenshot_manager.file_name)
            os.makedirs(new_directory, exist_ok=True)
            selected_theme = self.theme_combo.currentText()
            if selected_theme in qt_material.list_themes():
                qt_material.apply_stylesheet(QApplication.instance(), theme=selected_theme)
            else:
                QMessageBox.warning(self, "Theme Not Found", f"The selected theme '{selected_theme}' is not available.")
            QMessageBox.information(self, "Settings Applied", "Settings have been successfully applied.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply settings: {e}")

    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.directory_input.text())
        if directory:
            self.directory_input.setText(directory)

    def toggle_capturing(self, checked):
        if checked:
            self.toggle_capture_button.setText("Stop Capturing")
            self.start_capturing()
        else:
            self.toggle_capture_button.setText("Start Capturing")
            self.stop_capturing()

    def start_capturing(self):
        try:
            self.capturing = True
            self.capture_timer = QTimer()
            self.capture_timer.timeout.connect(self.capture_screenshot)
            self.capture_timer.start(self.screenshot_manager.INTERVAL_SECONDS * 1000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start capturing: {e}")
            self.toggle_capture_button.setChecked(False)
            self.toggle_capture_button.setText("Start Capturing")

    def stop_capturing(self):
        try:
            self.capturing = False
            if hasattr(self, 'capture_timer'):
                self.capture_timer.stop()
                del self.capture_timer
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to stop capturing: {e}")

    def capture_screenshot(self):
        try:
            mode = self.capture_mode_combo.currentText()
            capture_function = None
            if mode == "Full Screen":
                capture_function = lambda: capture_full_screen(self.screenshot_manager.file_path)
            elif mode == "Specific Application":
                capture_function = lambda: capture_window("App Title", self.screenshot_manager.file_path)
            elif mode == "Specific Monitor":
                capture_function = lambda: capture_specific_monitor(1, self.screenshot_manager.file_path)
            elif mode == "DirectX Game":
                capture_function = lambda: capture_directx_game("Game Title", self.screenshot_manager.file_path)
            elif mode == "Specific Browser Tab":
                capture_function = lambda: capture_browser_tab("Tab Title", self.screenshot_manager.file_path)
            result = self.screenshot_manager.capture_and_save(capture_function)
            if result:
                image_path, width, height, timestamp = result
                self.latest_timestamp = timestamp
                self.latest_dimensions = f"{width}x{height}"
                self.update_image(image_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to capture screenshot: {e}")

    def update_image(self, image_path):
        if not os.path.exists(image_path):
            self.image_label.setText("No Screenshot")
            return
        pixmap = QPixmap(image_path)
        scaled_pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio)
        self.image_label.setPixmap(scaled_pixmap)

    def copy_to_clipboard(self):
        target_path = self.screenshot_manager.file_path
        if not os.path.exists(target_path):
            QMessageBox.warning(self, "No Screenshot", "No screenshot available to copy.")
            return
        clipboard = QApplication.instance().clipboard()
        image = QPixmap(target_path)
        if image.isNull():
            QMessageBox.warning(self, "Invalid Image", "Failed to load the latest screenshot.")
            return
        clipboard.setPixmap(image)
        QMessageBox.information(self, "Copied", "Latest screenshot has been copied to the clipboard.")

    def init_system_tray(self):
        icon_path = 'screenshot_icon.png'
        if os.path.exists(icon_path):
            tray_icon = QIcon(icon_path)
        else:
            tray_icon = QIcon.fromTheme("applications-system")
        self.tray_icon = QSystemTrayIcon(tray_icon, self)
        tray_menu = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show_window)
        start_action = QAction("Start Capturing", self)
        start_action.triggered.connect(lambda: self.toggle_capture_button.click() if not self.capturing else None)
        stop_action = QAction("Stop Capturing", self)
        stop_action.triggered.connect(lambda: self.toggle_capture_button.click() if self.capturing else None)
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(show_action)
        tray_menu.addAction(start_action)
        tray_menu.addAction(stop_action)
        tray_menu.addSeparator()
        tray_menu.addAction(about_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def show_window(self):
        self.show()
        self.setWindowState(Qt.WindowActive)

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage("Visualizer", "Application was minimized to Tray.", QSystemTrayIcon.Information, 2000)

    def show_about(self):
        QMessageBox.information(self, "About", "Visualizer\nVersion 1.0\nAdvanced Live Screenshot Viewer")

# =========================
# Main Application Logic
# =========================
def parse_arguments():
    """Parse command-line arguments for the application."""
    parser = argparse.ArgumentParser(description="Visualizer - Advanced Live Screenshot Viewer")

    parser.add_argument('--host', type=str, default=DEFAULT_FLASK_HOST,
                        help='Flask server host (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=DEFAULT_FLASK_PORT,
                        help='Flask server port (default: 5000)')
    parser.add_argument('--mode', type=str, choices=[
        "Full Screen",
        "Specific Application",
        "Specific Monitor",
        "DirectX Game",
        "Specific Browser Tab"
    ], default="Full Screen",
    help='Capture mode (default: Full Screen)')
    parser.add_argument('--start', action='store_true',
                        help='Start capturing immediately upon launch')
    parser.add_argument('--no-reuse', action='store_false', dest='reuse',
                        help='Disable reuse same image mode')
    parser.add_argument('--directory', type=str, default=os.getcwd(),
                        help='Directory to save screenshots (default: current working directory)')
    parser.set_defaults(reuse=True)
    args = parser.parse_args()
    return args

def main():
    # Parse command-line arguments
    args = parse_arguments()

    # Initialize the ScreenshotManager
    screenshot_manager = ScreenshotManager(directory=args.directory)

    # Initialize Flask app and run it in a separate thread
    flask_app = FlaskApp(screenshot_manager, host=args.host, port=args.port)
    flask_thread = FlaskAppThread(flask_app)
    flask_thread.start()

    # Create the Qt Application
    app = QApplication(sys.argv)

    # Apply the default theme (light_blue_500.xml) before creating the main window
    default_theme = "light_blue_500.xml"
    try:
        qt_material.apply_stylesheet(app, theme=default_theme)
        logging.info(f"Applied default theme: {default_theme}")
    except Exception as e:
        logging.error(f"Failed to apply theme {default_theme}: {e}")
        QMessageBox.warning(None, "Theme Error", f"Could not apply default theme: {default_theme}")

    # Create the main window and pass required arguments
    window = ScreenshotWindow(screenshot_manager, args)

    # Show the window
    window.show()

    # Execute the application event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
