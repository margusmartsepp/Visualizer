# tests/unit/test_screenshot_manager.py

import unittest
from unittest.mock import patch, MagicMock
import os

# Suppress specific pywinauto warnings (Optional)
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module='pywinauto')

from screenshot_manager import ScreenshotManager
from config import INTERVAL_SECONDS

class TestScreenshotManager(unittest.TestCase):
    def setUp(self):
        self.manager = ScreenshotManager(
            reuse_same_image=True,
            directory='test_images',
            selected_mode='Full Screen'
        )
        os.makedirs('test_images', exist_ok=True)
    
    def tearDown(self):
        # Clean up the test_images directory after tests
        for file in os.listdir('test_images'):
            file_path = os.path.join('test_images', file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir('test_images')
    
    @patch('screenshot_manager.capture_full_screen')
    def test_capture_and_save_reuse_true(self, mock_capture):
        # Mock the capture function to return a path
        mock_capture.return_value = 'test_images/FullScreen.png'
        
        # Create a dummy file to simulate screenshot
        with open('test_images/FullScreen.png', 'w') as f:
            f.write('dummy data')
        
        result = self.manager.capture_and_save(mock_capture)
        
        # Assert that the returned path is the reused file
        self.assertEqual(result[0], os.path.join('test_images', 'FullScreen.png'))
        
        # Assert that no new file was created
        files = os.listdir('test_images')
        self.assertEqual(len(files), 1)
    
    @patch('screenshot_manager.capture_full_screen')
    def test_capture_and_save_reuse_false(self, mock_capture):
        # Update manager to not reuse the same image
        self.manager.reuse_same_image = False
        
        # Mock the capture function to return a path
        mock_capture.return_value = 'test_images/FullScreen.png'
        
        # Create a dummy file to simulate screenshot
        with open('test_images/FullScreen.png', 'w') as f:
            f.write('dummy data')
        
        result = self.manager.capture_and_save(mock_capture)
        
        # Assert that the returned path is unique
        self.assertTrue(os.path.basename(result[0]).endswith('.png'))
        
        # Assert that a new file was created
        files = os.listdir('test_images')
        self.assertEqual(len(files), 2)

if __name__ == '__main__':
    unittest.main()
