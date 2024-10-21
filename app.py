# pylint: disable=too-many-lines, too-few-public-methods, too-many-instance-attributes, disable=no-member
"""
This module provides the core functionality for the Visualizer application, 
a Python-based screenshot capturing and viewing tool with both a graphical 
user interface (GUI) and a Flask-based REST API.

Main components:
- `ScreenshotManager`: Manages the capturing and saving of screenshots based
  on different modes (e.g., full screen, specific window, etc.).
- `FlaskApp`: Runs a Flask web server that serves screenshots and metadata 
  through various API endpoints.
- `ScreenshotWindow`: A PyQt5-based GUI that allows users to configure 
  screenshot settings, view captured images, and control the application.
- `FlaskAppThread`: A separate thread to run the Flask server concurrently with the GUI.
- Screenshot capture methods: Functions that capture screenshots from various 
  sources such as full screen, specific windows, and DirectX games.

Key functionalities:
- REST API endpoints for accessing the latest screenshot, its metadata, and controlling the server.
- GUI components that allow users to set capture modes, view screenshots, and apply settings.
- System tray integration for minimizing the application and quick access to actions.
- Comprehensive logging for tracking errors and user actions.

Dependencies:
- PyQt5 for the GUI components.
- Flask for the REST API.
- mss for capturing screenshots.
- PIL for image processing.
- dxcam for capturing DirectX game screenshots.
- pywinauto for capturing specific application windows.

Usage:
This module can be run directly to start both the GUI and the Flask server, 
or it can be tested using a unit testing framework.
"""

import warnings
import os
import sys
import logging
import argparse
import threading
from datetime import datetime
from flask import Flask, send_file, jsonify, request
 # pylint: disable=no-name-in-module
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QFileDialog,
    QSizePolicy,
    QTabWidget,
    QMessageBox,
    QAction,
    QSystemTrayIcon,
    QMenu,
)
from PyQt5.QtGui import QIcon, QPixmap, QDesktopServices # pylint: disable=no-name-in-module
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QUrl # pylint: disable=no-name-in-module
from PIL import Image, UnidentifiedImageError
import mss
import mss.tools
import dxcam
import pythoncom
from pywinauto import Desktop, ElementNotFoundError
import qt_material

# Suppress specific UserWarning from pywinauto
warnings.filterwarnings(
    "ignore", category=UserWarning, message="Revert to STA COM threading mode"
)
# Suppress all DeprecationWarnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# =========================
# Configuration
# =========================
DEFAULT_FLASK_HOST = "127.0.0.1"
DEFAULT_FLASK_PORT = 5000
INTERVAL_SECONDS = 3

# =========================
# Logging Configuration
# =========================
logging.basicConfig(
    filename="screenshot_viewer.log",
    level=logging.DEBUG,
    format="%(asctime)s:%(levelname)s:%(message)s",
)

# =========================
# Flask Application and API Handlers
# =========================
class FlaskApp:
    """Flask application for handling screenshot requests."""

    def __init__(
        self, screenshot_manager, host=DEFAULT_FLASK_HOST, port=DEFAULT_FLASK_PORT
    ):
        """
        Initialize the FlaskApp.

        Args:
            screenshot_manager (ScreenshotManager): The manager for screenshots.
            host (str): Host address for the Flask server.
            port (int): Port number for the Flask server.
        """
        self.app = Flask(__name__)
        self.screenshot_manager = screenshot_manager
        self.host = host
        self.port = port
        self.setup_routes()

    def setup_routes(self):
        """Set up the API routes for the Flask application."""
        @self.app.route("/screenshot", methods=["GET"])
        def get_screenshot():
            """Get the latest screenshot."""
            screenshot_path = self.screenshot_manager.file_path
            if os.path.exists(screenshot_path):
                try:
                    logging.info("Screenshot requested.")
                    return send_file(screenshot_path, mimetype="image/png")
                except IOError as e:
                    logging.error("Error in /screenshot: %s", e)
                    return jsonify({"error": str(e)}), 500
            else:
                logging.warning("No screenshot available.")
                return jsonify({"error": "No screenshot available."}), 404

        @self.app.route("/metadata", methods=["GET"])
        def get_metadata():
            """Get metadata of the latest screenshot."""
            screenshot_path = self.screenshot_manager.file_path
            if os.path.exists(screenshot_path):
                try:
                    timestamp = datetime.fromtimestamp(
                        os.path.getmtime(screenshot_path)
                    ).strftime("%Y-%m-%d %H:%M:%S")
                    with Image.open(screenshot_path) as img:
                        width, height = img.size
                    return (
                        jsonify(
                            {"timestamp": timestamp, "dimensions": f"{width}x{height}"}
                        ),
                        200,
                    )
                except (IOError, UnidentifiedImageError) as e:
                    logging.error("Error in /metadata: %s", e, exc_info=True)
                    return jsonify({"error": str(e)}), 500
            else:
                logging.warning("No metadata available.")
                return jsonify({"error": "No metadata available."}), 404

        @self.app.route("/status", methods=["GET"])
        def get_status():
            """Get the status of the Flask server."""
            return jsonify({"status": "running"}), 200

        @self.app.route("/viewer", methods=["GET"])
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
                <img id="screenshot" src="/screenshot?timestamp={
                    int(datetime.now().timestamp() * 1000)}" alt="Latest Screenshot">
                
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

        @self.app.route("/shutdown", methods=["POST"])
        def shutdown_server():
            """Endpoint to shutdown the Flask server."""
            func = request.environ.get("werkzeug.server.shutdown")
            if func is None:
                logging.error(
                    "Shutdown attempted, but not running with the Werkzeug Server."
                )
                return jsonify({"error": "Not running with the Werkzeug Server"}), 500
            func()
            logging.info("Server shutting down via /shutdown endpoint.")
            return jsonify({"message": "Server shutting down..."}), 200

class FlaskAppThread(threading.Thread):
    """Thread to run the Flask server."""

    def __init__(self, flask_app):
        """
        Initialize the FlaskAppThread.

        Args:
            flask_app (FlaskApp): The Flask application instance.
        """
        super().__init__()
        self.flask_app = flask_app
        self.daemon = True

    def run(self):
        """Run the Flask server."""
        logging.info(
            "Starting Flask server on %s:%d", self.flask_app.host, self.flask_app.port
        )
        self.flask_app.app.run(
            host=self.flask_app.host, port=self.flask_app.port, threaded=True
        )

# =========================
# Screenshot Manager and Capture Functions
# =========================
class ScreenshotManager:
    """Manages screenshot capturing and saving."""

    def __init__(
        self, reuse_same_image=True, directory=None, selected_mode="Full Screen"
    ):
        """
        Initialize the ScreenshotManager.

        Args:
            reuse_same_image (bool): Whether to reuse the same image file.
            directory (str): Directory to save screenshots.
            selected_mode (str): Initial capture mode.
        """
        if directory is None:
            self.custom_directory = os.path.join(os.getcwd(), "Images")
        else:
            self.custom_directory = directory

        self.reuse_same_image = reuse_same_image
        self.selected_mode = selected_mode
        self.file_name = self.get_base_filename()
        self.file_path = os.path.join(self.custom_directory, self.file_name)
        self.interval_seconds = INTERVAL_SECONDS

        os.makedirs(self.custom_directory, exist_ok=True)
        logging.info(
            "ScreenshotManager initialized with path: %s and interval: %d seconds.",
            self.file_path,
            self.interval_seconds,
        )

    def get_base_filename(self):
        """Generate base file name based on capture mode."""
        base_name = "".join(e for e in self.selected_mode if e.isalnum())
        return f"{base_name.lower()}.png"

    def capture_and_save(self, capture_function):
        """
        Capture a screenshot using the provided capture function and save it.

        Args:
            capture_function (callable): Function to capture the screenshot.

        Returns:
            tuple or None: (path, width, height, timestamp) if successful, else None.
        """
        try:
            if self.reuse_same_image and os.path.exists(self.file_path):
                logging.warning("Reusing existing file: %s", self.file_path)
                return self.file_path, 0, 0, datetime.now()

            result_path = capture_function()
            logging.info("Screenshot captured: %s", result_path)
            return result_path, 0, 0, datetime.now()
        except (IOError, mss.exception.ScreenShotError) as e:
            logging.error("Error during capture and save: %s", e)
            return None

def capture_full_screen(output_path):
    """
    Capture the primary monitor's full screen.

    Args:
        output_path (str): Path to save the screenshot.

    Returns:
        str: Path where the screenshot is saved.
    """
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Primary monitor
        screenshot = sct.grab(monitor)
        mss.tools.to_png(screenshot.rgb, screenshot.size, output=output_path)
    logging.info("Captured full screen: %s", output_path)
    return output_path

def capture_specific_monitor(_capture_manager, output_path):
    """
    Capture a specific monitor based on index.

    Args:
        capture_manager (ScreenshotManager): The screenshot manager.
        output_path (str): Path to save the screenshot.

    Returns:
        str: Path where the screenshot is saved.
    """
    monitor_index = 1  # Example index; modify as needed
    with mss.mss() as sct:
        monitors = sct.monitors
        if monitor_index < 1 or monitor_index > len(monitors) - 1:
            raise ValueError("Invalid monitor index.")
        monitor = monitors[monitor_index]
        screenshot = sct.grab(monitor)
        mss.tools.to_png(screenshot.rgb, screenshot.size, output=output_path)
    logging.info("Captured monitor %d: %s", monitor_index, output_path)
    return output_path

def capture_window(title, output_path):
    """
    Capture a specific application window.

    Args:
        title (str): Title of the window to capture.
        output_path (str): Path to save the screenshot.

    Returns:
        str or None: Path where the screenshot is saved or None if failed.
    """
    try:
        app = Desktop(backend="uia").window(title=title)
        app.set_focus()
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
        logging.info("Captured window '%s': %s", title, output_path)
        return output_path
    except ElementNotFoundError as e:
        logging.error("Window '%s' not found: %s", title, e)
        return None
    except mss.exception.ScreenShotError as e:
        logging.error("Error capturing window '%s': %s", title, e)
        return None

def capture_directx_game(game_title, output_path):
    """
    Capture a DirectX game window.

    Args:
        game_title (str): Title of the DirectX game window.
        output_path (str): Path to save the screenshot.

    Returns:
        str or None: Path where the screenshot is saved or None if failed.
    """
    try:
        cam = dxcam.create()
        cam.set_window(game_title)
        frame = cam.grab()
        img = Image.fromarray(frame)
        img.save(output_path)
        logging.info("Captured DirectX game '%s': %s", game_title, output_path)
        return output_path
    except dxcam.DXCamError as e:
        logging.error("DirectX game window '%s' not found: %s", game_title, e)
        return None
    except IOError as e:
        logging.error("Error saving DirectX game screenshot '%s': %s", game_title, e)
        return None

def capture_browser_tab(tab_title, output_path):
    """
    Capture a specific browser tab based on window title.

    Args:
        tab_title (str): Title of the browser tab to capture.
        output_path (str): Path to save the screenshot.

    Returns:
        str or None: Path where the screenshot is saved or None if failed.
    """
    try:
        return capture_window(tab_title, output_path)
    except (ElementNotFoundError, mss.exception.ScreenShotError, IOError) as e:
        logging.error("Error capturing browser tab '%s': %s", tab_title, e)
        return None

# =========================
# Screenshot Window (UI)
# =========================
class ScreenshotDisplayWindow(QMainWindow):
    """A floating window to display the latest screenshot."""

    def __init__(self):
        """Initialize the ScreenshotDisplayWindow."""
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
        """
        Update the displayed image.

        Args:
            image_path (str): Path to the new image.
        """
        if not os.path.exists(image_path):
            self.image_label.setText("No Screenshot")
            return
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.image_label.setText("Failed to Load Image")
        else:
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)

class ScreenshotEmitter(QObject):
    """Emitter for screenshot signals."""

    screenshot_signal = pyqtSignal(str, int, int, str)  # path, width, height, timestamp
    copy_to_clipboard_signal = pyqtSignal()

class ScreenshotWindow(QMainWindow):
    """Main window for the Visualizer application."""

    def __init__(self, screenshot_manager, args):
        """
        Initialize the ScreenshotWindow.

        Args:
            screenshot_manager (ScreenshotManager): Manager for screenshots.
            args (argparse.Namespace): Parsed command-line arguments.
        """
        super().__init__()
        pythoncom.CoInitialize()

        self.screenshot_manager = screenshot_manager
        self.emitter = ScreenshotEmitter()
        self.emitter.screenshot_signal.connect(self._update_image)
        self.emitter.copy_to_clipboard_signal.connect(self.copy_to_clipboard)

        # Initialize attributes that will be defined later in the methods
        self.capturing = False
        self.host = args.host
        self.port = args.port
        self.latest_timestamp = ""
        self.latest_dimensions = ""
        self.floating_window = ScreenshotDisplayWindow()
        self.capture_mode_combo = None  # Initialized later in _init_ui
        self.toggle_capture_button = None  # Initialized later in _init_ui
        self.image_label = None  # Initialized later in _init_ui
        self.host_input = None  # Initialized later in _init_settings_tab
        self.port_input = None  # Initialized later in _init_settings_tab
        self.directory_input = None  # Initialized later in _init_settings_tab
        self.reuse_checkbox = None  # Initialized later in _init_settings_tab
        self.theme_combo = None  # Initialized later in _init_settings_tab
        self.tabs = None  # Initialized later in _init_ui
        self.capture_timer = None  # Initialized later in _init_ui
        self.floating_window.hide()

        # Initialize UI and other components
        self._init_ui()
        self._apply_initial_configurations(args)
        self._init_system_tray()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Visualizer - Live Screenshot Viewer")
        self.setGeometry(100, 100, 800, 600)

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        capture_controls_layout = QHBoxLayout()
        self.capture_mode_combo = QComboBox()
        self.capture_mode_combo.addItems(
            [
                "Full Screen",
                "Specific Application",
                "Specific Monitor",
                "DirectX Game",
                "Specific Browser Tab",
            ]
        )
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
        self.image_label.setStyleSheet(
            "background-color: #eee; border: 1px solid #ccc;"
        )
        main_layout.addWidget(self.image_label)

        self.tabs = QTabWidget()
        self._init_settings_tab()
        main_layout.addWidget(self.tabs)

    def _init_settings_tab(self):
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
        open_viewer_button.clicked.connect(self._open_viewer_in_browser)

        open_screenshot_button = QPushButton("Open Screenshot")
        open_screenshot_button.clicked.connect(self._open_latest_screenshot_in_browser)

        host_port_layout.addWidget(open_viewer_button)
        host_port_layout.addWidget(open_screenshot_button)

        config_form.addRow(host_port_layout)

        # Directory Input
        self.directory_input = QLineEdit(os.getcwd())
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._browse_directory)
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
        apply_button.clicked.connect(self._apply_settings)
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addWidget(apply_button)
        settings_layout.addLayout(theme_layout)

        # Add Settings Tab to Tabs
        self.tabs.addTab(settings_tab, "Settings")

    def _open_viewer_in_browser(self):
        """Open the viewer page in the default browser."""
        viewer_url = f"http://{self.host_input.text()}:{self.port_input.text()}/viewer"
        QDesktopServices.openUrl(QUrl(viewer_url))

    def _open_latest_screenshot_in_browser(self):
        """Open the latest screenshot in the default browser."""
        screenshot_url = (
            f"http://{self.host_input.text()}:{self.port_input.text()}/screenshot"
        )
        QDesktopServices.openUrl(QUrl(screenshot_url))

    def _apply_initial_configurations(self, args):
        """
        Apply initial configurations based on command-line arguments.

        Args:
            args (argparse.Namespace): Parsed command-line arguments.
        """
        self.host_input.setText(self.host)
        self.port_input.setText(str(self.port))
        self.reuse_checkbox.setChecked(self.screenshot_manager.reuse_same_image)
        self.directory_input.setText(self.screenshot_manager.custom_directory)
        if args.start:
            self.toggle_capture_button.setChecked(True)
            self.toggle_capture_button.setText("Stop Capturing")
            self.start_capturing()

    def _apply_settings(self):
        """Apply settings from the Settings tab."""
        try:
            new_host = self.host_input.text()
            new_port = int(self.port_input.text())
            self.host = new_host
            self.port = new_port
            self.screenshot_manager.reuse_same_image = self.reuse_checkbox.isChecked()
            new_directory = self.directory_input.text()
            self.screenshot_manager.custom_directory = new_directory
            self.screenshot_manager.file_path = os.path.join(
                new_directory, self.screenshot_manager.file_name
            )
            os.makedirs(new_directory, exist_ok=True)
            selected_theme = self.theme_combo.currentText()
            if selected_theme in qt_material.list_themes():
                qt_material.apply_stylesheet(
                    QApplication.instance(), theme=selected_theme
                )
            else:
                QMessageBox.warning(
                    self,
                    "Theme Not Found",
                    f"The selected theme '{selected_theme}' is not available.",
                )
            logging.info("Settings have been successfully applied.")
        except ValueError as e:
            QMessageBox.critical(self, "Error", f"Invalid input: {e}")
            logging.error("Invalid input when applying settings: %s", e)
        except (TypeError, OSError) as e:
            QMessageBox.critical(self, "Error", f"Failed to apply settings: {e}")
            logging.error("Failed to apply settings: %s", e, exc_info=True)

    def _browse_directory(self):
        """Open a dialog to browse and select a directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Save Directory", self.directory_input.text()
        )
        if directory:
            self.directory_input.setText(directory)

    def toggle_capturing(self, checked):
        """
        Toggle the screenshot capturing process.

        Args:
            checked (bool): Whether capturing is enabled.
        """
        if checked:
            self.toggle_capture_button.setText("Stop Capturing")
            self.start_capturing()
        else:
            self.toggle_capture_button.setText("Start Capturing")
            self.stop_capturing()

    def start_capturing(self):
        """Start the screenshot capturing timer."""
        try:
            self.capturing = True
            self.capture_timer = QTimer()
            self.capture_timer.timeout.connect(self.capture_screenshot)
            self.capture_timer.start(self.screenshot_manager.interval_seconds * 1000)
            logging.info("Started capturing screenshots.")
        except (ValueError, RuntimeError, OSError) as e:
            QMessageBox.critical(self, "Error", f"Failed to start capturing: {e}")
            logging.error("Failed to start capturing: %s", e, exc_info=True)
            self.toggle_capture_button.setChecked(False)
            self.toggle_capture_button.setText("Start Capturing")

    def stop_capturing(self):
        """Stop the screenshot capturing timer."""
        try:
            self.capturing = False
            if hasattr(self, "capture_timer"):
                self.capture_timer.stop()
                del self.capture_timer
            logging.info("Stopped capturing screenshots.")
        except (ValueError, RuntimeError, OSError) as e:
            QMessageBox.critical(self, "Error", f"Failed to stop capturing: {e}")
            logging.error("Failed to stop capturing: %s", e, exc_info=True)

    def capture_screenshot(self):
        """Capture a screenshot based on the selected mode."""
        try:
            mode = self.capture_mode_combo.currentText()
            capture_function = self._get_capture_function(mode)
            if capture_function is None:
                QMessageBox.warning(
                    self, "Capture Mode", f"No capture function for mode '{mode}'."
                )
                logging.warning("No capture function for mode '%s'.", mode)
                return
            result = self.screenshot_manager.capture_and_save(capture_function)
            if result:
                image_path, width, height, timestamp = result
                self.latest_timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                self.latest_dimensions = f"{width}x{height}"
                self.emitter.screenshot_signal.emit(
                    image_path, width, height, self.latest_timestamp
                )
        except ValueError as e:
            QMessageBox.critical(self, "Error", f"Invalid capture mode: {e}")
            logging.error("Invalid capture mode: %s", e)
        except (IOError) as e:
            QMessageBox.critical(self, "Error", f"Failed to capture screenshot: {e}")
            logging.error("Failed to capture screenshot: %s", e)
        except (mss.exception.ScreenShotError) as e:
            QMessageBox.critical(self, "Error", f"Error during screenshot capture: {e}")
            logging.error("Error during screenshot capture: %s", e, exc_info=True)

    def _get_capture_function(self, mode):
        """
        Get the appropriate capture function based on the capture mode.

        Args:
            mode (str): The selected capture mode.

        Returns:
            callable or None: The capture function or None if mode is invalid.
        """
        if mode == "Full Screen":
            return self._capture_full_screen
        if mode == "Specific Application":
            return self._capture_specific_application
        if mode == "Specific Monitor":
            return self._capture_specific_monitor
        if mode == "DirectX Game":
            return self._capture_directx_game
        if mode == "Specific Browser Tab":
            return self._capture_specific_browser_tab
        return None

    def _capture_full_screen(self):
        """Capture the full screen."""
        return capture_full_screen(self.screenshot_manager.file_path)

    def _capture_specific_application(self):
        """Capture a specific application window."""
        return capture_window("App Title", self.screenshot_manager.file_path)

    def _capture_specific_monitor(self):
        """Capture a specific monitor."""
        return capture_specific_monitor(self.screenshot_manager, self.screenshot_manager.file_path)

    def _capture_directx_game(self):
        """Capture a DirectX game window."""
        return capture_directx_game("Game Title", self.screenshot_manager.file_path)

    def _capture_specific_browser_tab(self):
        """Capture a specific browser tab."""
        return capture_browser_tab("Tab Title", self.screenshot_manager.file_path)


    def _update_image(self, image_path, width, height, timestamp):  # pylint: disable=unused-argument
        """
        Update the main window and floating window with the new image.

        Args:
            image_path (str): Path to the new image.
            width (int): Width of the image.
            height (int): Height of the image.
            timestamp (str): Timestamp of the capture.
        """
        if not os.path.exists(image_path):
            self.image_label.setText("No Screenshot")
            self.floating_window.update_image(image_path)
            return
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.image_label.setText("Failed to Load Image")
            self.floating_window.update_image(image_path)
        else:
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
            self.floating_window.update_image(image_path)

    def copy_to_clipboard(self):
        """Copy the latest screenshot to the clipboard."""
        target_path = self.screenshot_manager.file_path
        if not os.path.exists(target_path):
            QMessageBox.warning(
                self, "No Screenshot", "No screenshot available to copy."
            )
            return
        image = QPixmap(target_path)
        if image.isNull():
            QMessageBox.warning(
                self, "Invalid Image", "Failed to load the latest screenshot."
            )
            return
        clipboard = QApplication.instance().clipboard()
        clipboard.setPixmap(image)
        QMessageBox.information(
            self, "Copied", "Latest screenshot has been copied to the clipboard."
        )
        logging.info("Copied screenshot to clipboard.")

    def _init_system_tray(self):
        """Initialize the system tray icon and menu."""
        icon_path = "screenshot_icon.png"
        if os.path.exists(icon_path):
            tray_icon = QIcon(icon_path)
        else:
            tray_icon = QIcon.fromTheme("applications-system")
        self.tray_icon = QSystemTrayIcon(tray_icon, self)
        tray_menu = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show_window)
        start_action = QAction("Start Capturing", self)
        start_action.triggered.connect(
            lambda: self.toggle_capture_button.click() if not self.capturing else None
        )
        stop_action = QAction("Stop Capturing", self)
        stop_action.triggered.connect(
            lambda: self.toggle_capture_button.click() if self.capturing else None
        )
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
        self.tray_icon.activated.connect(self._on_tray_icon_activated)

    def show_window(self):
        """Show the main application window."""
        self.show()
        self.setWindowState(Qt.WindowActive)

    def _on_tray_icon_activated(self, reason):
        """
        Handle system tray icon activation.

        Args:
            reason (QSystemTrayIcon.ActivationReason): Reason for activation.
        """
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window()

    def closeEvent(self, event): # pylint: disable=invalid-name
        """
        Handle the window close event by minimizing to the system tray.

        Args:
            event (QCloseEvent): The close event.
        """
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Visualizer",
            "Application was minimized to Tray.",
            QSystemTrayIcon.Information,
            2000,
        )
        logging.info("Application minimized to system tray.")

    def show_about(self):
        """Show the About dialog."""
        QMessageBox.information(
            self, "About", "Visualizer\nVersion 1.0\nAdvanced Live Screenshot Viewer"
        )
        logging.info("Displayed About dialog.")

# =========================
# Main Application Logic
# =========================
def parse_arguments():
    """Parse command-line arguments for the application."""
    parser = argparse.ArgumentParser(
        description="Visualizer - Advanced Live Screenshot Viewer"
    )

    parser.add_argument(
        "--host",
        type=str,
        default=DEFAULT_FLASK_HOST,
        help="Flask server host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_FLASK_PORT,
        help="Flask server port (default: 5000)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=[
            "Full Screen",
            "Specific Application",
            "Specific Monitor",
            "DirectX Game",
            "Specific Browser Tab",
        ],
        default="Full Screen",
        help="Capture mode (default: Full Screen)",
    )
    parser.add_argument(
        "--start", action="store_true", help="Start capturing immediately upon launch"
    )
    parser.add_argument(
        "--no-reuse",
        action="store_false",
        dest="reuse",
        help="Disable reuse same image mode",
    )
    parser.add_argument(
        "--directory",
        type=str,
        default=os.getcwd(),
        help="Directory to save screenshots (default: current working directory)",
    )
    parser.set_defaults(reuse=True)
    args = parser.parse_args()
    return args

def main():
    """Main function to run the application."""
    # Parse command-line arguments
    args = parse_arguments()

    # Initialize the ScreenshotManager
    screenshot_manager = ScreenshotManager(
        reuse_same_image=args.reuse, directory=args.directory, selected_mode=args.mode
    )

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
    except Exception as e: # pylint: disable=broad-exception-caught
        logging.error("Failed to apply theme %s: %s", default_theme, e)
        QMessageBox.warning(
            None, "Theme Error", f"Could not apply default theme: {default_theme}"
        )

    # Create the main window and pass required arguments
    window = ScreenshotWindow(screenshot_manager, args)

    # Show the window
    window.show()

    # Execute the application event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
