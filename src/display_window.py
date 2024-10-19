# display_window.py

import os
from PyQt5.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QPushButton, QWidget
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import logging

class ScreenshotDisplayWindow(QMainWindow):
    """A floating window to display the latest screenshot."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Latest Screenshot")
        self.setGeometry(1500, 100, 400, 300)  # Position it to the right side; adjust as needed
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Central widget and layout
        central_widget = QWidget()
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Image label
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid black; background-color: white;")
        layout.addWidget(self.image_label)

        # Close button
        close_button = QPushButton("X")
        close_button.setFixedSize(30, 30)
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button, alignment=Qt.AlignRight)

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
        self.image_label.setPixmap(pixmap.scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        ))
        logging.info(f"Displayed screenshot: {image_path}")

