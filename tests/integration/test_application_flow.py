# tests/integration/test_application_flow.py

import unittest
from unittest.mock import patch, MagicMock
import os
from PyQt5.QtWidgets import QApplication
import sys

# Suppress specific pywinauto warnings (Optional)
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module='pywinauto')

from screenshot_manager import ScreenshotManager
from ui import ScreenshotWindow

class TestApplicationFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize QApplication only once for all tests
        cls.app = QApplication(sys.argv)
    
    def setUp(self):
        self.manager = ScreenshotManager(
            reuse_same_image=True,
            directory='test_images',
            selected_mode='Full Screen'
        )
        os.makedirs('test_images', exist_ok=True)
        self.window = ScreenshotWindow(self.manager, MagicMock())
    
    def tearDown(self):
        self.window.close()
        # Clean up the test_images directory after tests
        for file in os.listdir('test_images'):
            file_path = os.path.join('test_images', file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir('test_images')
    
    @patch('screenshot_manager.capture_full_screen')
    def test_capture_process(self, mock_capture):
        # Mock the capture function to return a path
        mock_capture.return_value = 'test_images/FullScreen.png'
        
        # Create a dummy file to simulate screenshot
        with open('test_images/FullScreen.png', 'w') as f:
            f.write('dummy data')
        
        # Simulate capturing a screenshot
        result = self.manager.capture_and_save(mock_capture)
        
        # Update UI with the new image
        self.window.update_image(result[0])
        
        # Assert that the image label has the correct pixmap
        pixmap = self.window.image_label.pixmap()
        self.assertIsNotNone(pixmap)
        self.assertFalse(pixmap.isNull())

if __name__ == '__main__':
    unittest.main()
