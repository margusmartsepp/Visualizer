# src/main.py

import sys
import argparse
import os
import logging

from PyQt5.QtWidgets import QApplication
from ui import ScreenshotWindow
from screenshot_manager import ScreenshotManager

from config import DEFAULT_FLASK_HOST, DEFAULT_FLASK_PORT, INTERVAL_SECONDS  # Import from config.py

# Configure logging
logging.basicConfig(
    filename='screenshot_viewer.log',
    level=logging.DEBUG,
    format='%(asctime)s:%(levelname)s:%(message)s'
)

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
    """Main function to run the application."""
    # Configure logging
    logging.basicConfig(
        filename='screenshot_viewer.log',
        level=logging.INFO,
        format='%(asctime)s:%(levelname)s:%(message)s'
    )
    logging.info("Application started.")

    # Parse command-line arguments
    args = parse_arguments()

    # Initialize ScreenshotManager with parsed arguments
    reuse_mode = args.reuse  # 'reuse' is True by default unless '--no-reuse' is specified
    screenshot_manager = ScreenshotManager(
        reuse_same_image=reuse_mode,
        directory=args.directory,
        selected_mode=args.mode
    )

    # Create the Qt Application
    app = QApplication(sys.argv)

    # Create and show the main window with ScreenshotManager and parsed arguments
    window = ScreenshotWindow(screenshot_manager, args)
    window.show()

    # Execute the application
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
