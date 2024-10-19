# screenshot_manager.py

import os
import shutil
from datetime import datetime
import mss
import mss.tools
from PIL import Image
import dxcam
from pywinauto import Desktop
import logging
from .config import INTERVAL_SECONDS  # Import INTERVAL_SECONDS

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

class ScreenshotManager:
    """
    Manages screenshot capturing and saving.
    Separates business logic from UI.
    """
    def __init__(self, reuse_same_image=True, directory=".", selected_mode="Full Screen"):
        self.reuse_same_image = reuse_same_image
        self.custom_directory = directory
        self.selected_mode = selected_mode
        self.file_name = self.get_base_filename()
        self.file_path = os.path.join(self.custom_directory, self.file_name)
        self.INTERVAL_SECONDS = INTERVAL_SECONDS  # Set from config.py
        logging.info(f"ScreenshotManager initialized with path: {self.file_path} and interval: {self.INTERVAL_SECONDS} seconds.")

        # Ensure the directory exists
        os.makedirs(self.custom_directory, exist_ok=True)

    def get_base_filename(self):
        """Generate base file name based on capture mode."""
        # Remove spaces and special characters from mode name
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
                    # Save to the custom file path
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
