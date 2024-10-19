# ui.py
import os
# ui.py

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QMessageBox, QLineEdit, QFormLayout,
    QFileDialog, QCheckBox, QTabWidget, QSystemTrayIcon, QMenu,
    QAction, QWidget, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
import logging
import os
import qt_material  # Import qt_material for applying Material Design

from screenshot_manager import ScreenshotManager, capture_full_screen, capture_specific_monitor, capture_window, capture_directx_game, capture_browser_tab
from flask_app import FlaskApp, FlaskAppThread
from display_window import ScreenshotDisplayWindow

from config import DEFAULT_FLASK_HOST, DEFAULT_FLASK_PORT, INTERVAL_SECONDS  # Import from config.py

class ScreenshotEmitter(QObject):
    """Custom signals for screenshot updates."""
    screenshot_signal = pyqtSignal(str, int, int, str)  # path, width, height, timestamp
    copy_to_clipboard_signal = pyqtSignal()

class ScreenshotWindow(QMainWindow):
    def __init__(self, screenshot_manager, args):
        super().__init__()
        
        # Initialize COM in STA mode to prevent pywinauto warnings
        import pythoncom
        pythoncom.CoInitialize()
        
        # Initialize business logic manager
        self.screenshot_manager = screenshot_manager
        
        # Initialize attributes
        self.emitter = ScreenshotEmitter()
        self.emitter.screenshot_signal.connect(self.update_image)
        self.emitter.copy_to_clipboard_signal.connect(self.copy_to_clipboard)
        self.capturing = False
        self.current_subscription = None
        self.flask_app = None  # To manage Flask server
        self.flask_thread = None
        self.host = args.host
        self.port = args.port
        self.latest_timestamp = ""
        self.latest_dimensions = ""
        self.listener_thread = None  # Thread for global shortcuts
        self.listener = None  # pynput listener
        
        # Floating window for displaying screenshots
        self.floating_window = ScreenshotDisplayWindow()
        self.floating_window.hide()  # Initially hidden

        # Initialize the UI
        self.init_ui()
        
        # Apply initial configurations based on arguments
        self.apply_initial_configurations(args)

        # Initialize System Tray
        self.init_system_tray()

    def init_ui(self):
        """Initialize the UI components."""
        self.setWindowTitle("Visualizer - Live Screenshot Viewer")
        self.setGeometry(100, 100, 800, 600)  # Width x Height

        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # --- Capture Controls Layout ---
        capture_controls_layout = QHBoxLayout()

        # Capture Mode ComboBox
        self.capture_mode_combo = QComboBox()
        self.capture_mode_combo.addItems([
            "Full Screen",
            "Specific Application",
            "Specific Monitor",
            "DirectX Game",
            "Specific Browser Tab"
        ])
        capture_controls_layout.addWidget(QLabel("Capture Mode:"))
        capture_controls_layout.addWidget(self.capture_mode_combo)

        # Spacer to separate Capture Mode and Start Button
        capture_controls_layout.addStretch()

        # Start Capturing Toggle Button
        self.toggle_capture_button = QPushButton("Start Capturing")
        self.toggle_capture_button.setCheckable(True)
        self.toggle_capture_button.clicked.connect(self.toggle_capturing)
        capture_controls_layout.addWidget(self.toggle_capture_button)

        # Add Capture Controls to Main Layout
        main_layout.addLayout(capture_controls_layout)

        # --- Image Display Area ---
        self.image_label = QLabel("No Screenshot")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #eee; border: 1px solid #ccc;")
        
        # Set fixed size or maximum size to prevent resizing
        self.image_label.setFixedSize(780, 400)  # Adjust as needed
        # Alternatively, set a maximum size
        # self.image_label.setMaximumSize(780, 400)
        
        # Set size policy to fixed to prevent resizing
        self.image_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        main_layout.addWidget(self.image_label)

        # --- Settings Tab ---
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

        # Host Input
        self.host_input = QLineEdit(DEFAULT_FLASK_HOST)
        config_form.addRow("Flask Host:", self.host_input)

        # Port Input
        self.port_input = QLineEdit(str(DEFAULT_FLASK_PORT))
        config_form.addRow("Flask Port:", self.port_input)

        # Reuse Same Image Checkbox (Checked by default)
        self.reuse_checkbox = QCheckBox("Reuse Same Image")
        self.reuse_checkbox.setChecked(True)  # Enabled by default
        config_form.addRow("Reuse Image:", self.reuse_checkbox)

        # Directory Input
        self.directory_input = QLineEdit(os.getcwd())
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_directory)
        directory_layout = QHBoxLayout()
        directory_layout.addWidget(self.directory_input)
        directory_layout.addWidget(browse_button)
        config_form.addRow("Save Directory:", directory_layout)

        settings_layout.addLayout(config_form)

        # Theme Selection
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Select Theme:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(qt_material.list_themes())
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        settings_layout.addLayout(theme_layout)

        # Apply Configurations Button
        apply_button = QPushButton("Apply Settings")
        apply_button.clicked.connect(self.apply_settings)
        settings_layout.addWidget(apply_button)

        # Add Settings Tab to Tabs
        self.tabs.addTab(settings_tab, "Settings")

        # --- Set Default Theme to light_blue ---
        default_theme = "light_blue.xml"
        if default_theme in qt_material.list_themes():
            index = self.theme_combo.findText(default_theme, Qt.MatchFixedString)
            if index >= 0:
                self.theme_combo.setCurrentIndex(index)
                # Apply the default theme
                qt_material.apply_stylesheet(QApplication.instance(), theme=default_theme)
                logging.info(f"Applied default theme: {default_theme}")
        else:
            logging.warning(f"Theme '{default_theme}' not found in qt_material themes.")

    def apply_initial_configurations(self, args):
        """
        Apply initial configurations to the UI based on command-line arguments.
        
        :param args: Parsed command-line arguments
        """
        # --- Apply Host and Port Settings ---
        self.host_input.setText(self.host)
        self.port_input.setText(str(self.port))
        logging.info(f"Applied initial host: {self.host}, port: {self.port}")

        # --- Apply Reuse Mode ---
        self.reuse_checkbox.setChecked(self.screenshot_manager.reuse_same_image)
        if self.screenshot_manager.reuse_same_image:
            logging.info("Reuse same image mode enabled.")
        else:
            logging.info("Reuse same image mode disabled.")

        # --- Apply Directory Settings ---
        self.directory_input.setText(self.screenshot_manager.custom_directory)
        logging.info(f"Applied initial directory: {self.screenshot_manager.custom_directory}")

        # --- Start Capturing Immediately if --start Flag is Set ---
        if args.start:
            self.toggle_capture_button.setChecked(True)
            self.toggle_capture_button.setText("Stop Capturing")
            self.start_capturing()
            logging.info("Started capturing immediately based on --start flag.")

    def apply_settings(self):
        """Apply settings from the Settings tab."""
        try:
            # Update Flask host and port
            new_host = self.host_input.text()
            new_port = int(self.port_input.text())
            self.host = new_host
            self.port = new_port
            logging.info(f"Updated Flask host to: {self.host}, port to: {self.port}")

            # Update Reuse mode
            self.screenshot_manager.reuse_same_image = self.reuse_checkbox.isChecked()
            logging.info(f"Reuse same image mode set to: {self.screenshot_manager.reuse_same_image}")

            # Update Directory
            new_directory = self.directory_input.text()
            self.screenshot_manager.custom_directory = new_directory
            self.screenshot_manager.file_path = os.path.join(new_directory, self.screenshot_manager.file_name)
            os.makedirs(new_directory, exist_ok=True)
            logging.info(f"Updated save directory to: {new_directory}")

            # Apply Theme
            selected_theme = self.theme_combo.currentText()
            if selected_theme in qt_material.list_themes():
                qt_material.apply_stylesheet(QApplication.instance(), theme=selected_theme)
                logging.info(f"Applied theme: {selected_theme}")
            else:
                logging.warning(f"Selected theme '{selected_theme}' is not available.")
                QMessageBox.warning(self, "Theme Not Found", f"The selected theme '{selected_theme}' is not available.")

            QMessageBox.information(self, "Settings Applied", "Settings have been successfully applied.")
        except Exception as e:
            logging.error(f"Failed to apply settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to apply settings: {e}")

    def browse_directory(self):
        """Open a dialog to browse and select the save directory."""
        directory = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.directory_input.text())
        if directory:
            self.directory_input.setText(directory)

    def change_theme(self, theme_name):
        """Change the application theme."""
        try:
            if theme_name in qt_material.list_themes():
                qt_material.apply_stylesheet(QApplication.instance(), theme=theme_name)
                logging.info(f"Changed theme to: {theme_name}")
            else:
                logging.warning(f"Theme '{theme_name}' is not available.")
                QMessageBox.warning(self, "Theme Not Found", f"The selected theme '{theme_name}' is not available.")
        except Exception as e:
            logging.error(f"Failed to change theme to {theme_name}: {e}")
            QMessageBox.critical(self, "Error", f"Failed to change theme: {e}")

    def toggle_capturing(self, checked):
        """Start or stop capturing based on the toggle button state."""
        if checked:
            self.toggle_capture_button.setText("Stop Capturing")
            # Start capturing logic...
            self.start_capturing()
        else:
            self.toggle_capture_button.setText("Start Capturing")
            # Stop capturing logic...
            self.stop_capturing()

    def start_capturing(self):
        """Logic to start capturing screenshots."""
        try:
            self.capturing = True
            # Initialize and start capturing thread or timer
            # Example using QTimer:
            self.capture_timer = QTimer()
            self.capture_timer.timeout.connect(self.capture_screenshot)
            self.capture_timer.start(self.screenshot_manager.INTERVAL_SECONDS * 1000)
            logging.info("Started capturing screenshots.")
        except Exception as e:
            logging.error(f"Failed to start capturing: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start capturing: {e}")
            self.toggle_capture_button.setChecked(False)
            self.toggle_capture_button.setText("Start Capturing")

    def stop_capturing(self):
        """Logic to stop capturing screenshots."""
        try:
            self.capturing = False
            # Stop capturing thread or timer
            if hasattr(self, 'capture_timer'):
                self.capture_timer.stop()
                del self.capture_timer
            logging.info("Stopped capturing screenshots.")
        except Exception as e:
            logging.error(f"Failed to stop capturing: {e}")
            QMessageBox.critical(self, "Error", f"Failed to stop capturing: {e}")

    def capture_screenshot(self):
        """Capture a screenshot and update the image display area."""
        try:
            # Determine the capture mode and perform capturing
            mode = self.capture_mode_combo.currentText()
            capture_function = None

            if mode == "Full Screen":
                capture_function = lambda: capture_full_screen(self.screenshot_manager.file_path)
            elif mode == "Specific Application":
                # Replace 'App Title' with actual application window title
                capture_function = lambda: capture_window("App Title", self.screenshot_manager.file_path)
            elif mode == "Specific Monitor":
                # Replace '1' with desired monitor index
                capture_function = lambda: capture_specific_monitor(1, self.screenshot_manager.file_path)
            elif mode == "DirectX Game":
                # Replace 'Game Title' with actual game window title
                capture_function = lambda: capture_directx_game("Game Title", self.screenshot_manager.file_path)
            elif mode == "Specific Browser Tab":
                # Replace 'Tab Title' with actual browser tab title
                capture_function = lambda: capture_browser_tab("Tab Title", self.screenshot_manager.file_path)
            else:
                logging.warning(f"Unknown capture mode selected: {mode}")
                return

            result = self.screenshot_manager.capture_and_save(capture_function)
            if result:
                image_path, width, height, timestamp = result
                self.latest_timestamp = timestamp
                self.latest_dimensions = f"{width}x{height}"
                self.update_image(image_path)
        except Exception as e:
            logging.error(f"Error capturing screenshot: {e}")
            QMessageBox.critical(self, "Error", f"Failed to capture screenshot: {e}")

    def update_image(self, image_path):
        """Update the image displayed in the main window."""
        if not image_path or not os.path.exists(image_path):
            logging.warning(f"Image path invalid for main window: {image_path}")
            self.image_label.setText("No Screenshot")
            return

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            logging.warning(f"Failed to load image for main window from {image_path}")
            self.image_label.setText("Failed to Load Image")
            return

        # Scale pixmap to fit the label while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)
        logging.info(f"Displayed screenshot: {image_path}")

    def resizeEvent(self, event):
        """Handle the window resize event to update the image display."""
        super().resizeEvent(event)
        # Since image_label has fixed size, no need to adjust
        # If you set maximum size instead, you can adjust scaling here

    def copy_to_clipboard(self):
        """Copy the latest screenshot to the system clipboard."""
        logging.info("Attempting to copy latest screenshot to clipboard.")
        target_path = self.screenshot_manager.file_path if self.screenshot_manager.reuse_same_image else self.screenshot_manager.file_path

        if not os.path.exists(target_path):
            QMessageBox.warning(self, "No Screenshot", "No screenshot available to copy.")
            logging.warning("No screenshot available to copy to clipboard.")
            return

        clipboard = QApplication.instance().clipboard()
        image = QPixmap(target_path)
        if image.isNull():
            QMessageBox.warning(self, "Invalid Image", "Failed to load the latest screenshot.")
            logging.error("Failed to load the latest screenshot for clipboard.")
            return

        clipboard.setPixmap(image)
        QMessageBox.information(self, "Copied", "Latest screenshot has been copied to the clipboard.")
        logging.info(f"Copied screenshot from {target_path} to clipboard.")

    def init_system_tray(self):
        """Initialize the system tray icon and menu."""
        # Path to your custom icon
        icon_path = 'screenshot_icon.png'
        
        if os.path.exists(icon_path):
            tray_icon = QIcon(icon_path)
        else:
            # Use a default system icon if the specified one doesn't exist
            tray_icon = QIcon.fromTheme("applications-system")
            logging.warning(f"Icon file '{icon_path}' not found. Using default system icon.")
        
        self.tray_icon = QSystemTrayIcon(tray_icon, self)

        # Create the tray menu
        tray_menu = QMenu()

        # Create actions
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show_window)

        start_action = QAction("Start Capturing", self)
        start_action.triggered.connect(lambda: self.toggle_capture_button.click() if not self.capturing else None)

        stop_action = QAction("Stop Capturing", self)
        stop_action.triggered.connect(lambda: self.toggle_capture_button.click() if self.capturing else None)

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)  # Ensure QApplication is imported

        # Add actions to the tray menu
        tray_menu.addAction(show_action)
        tray_menu.addAction(start_action)
        tray_menu.addAction(stop_action)
        tray_menu.addSeparator()
        tray_menu.addAction(about_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        # Set the context menu to the tray icon
        self.tray_icon.setContextMenu(tray_menu)

        # Show the tray icon
        self.tray_icon.show()

        # Handle double-click to show the window
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def show_window(self):
        """Show the main window."""
        self.show()
        self.setWindowState(Qt.WindowActive)
        logging.info("Main window shown from system tray.")

    def on_tray_icon_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window()

    def closeEvent(self, event):
        """Handle the window close event to minimize to tray."""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Visualizer",
            "Application was minimized to Tray.",
            QSystemTrayIcon.Information,
            2000
        )
        logging.info("Application minimized to system tray.")

    def show_about(self):
        """Show the About dialog."""
        QMessageBox.information(self, "About", "Visualizer\nVersion 1.0\nAdvanced Live Screenshot Viewer")
        logging.info("About dialog shown.")
