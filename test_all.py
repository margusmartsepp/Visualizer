# test_all.py

import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add src/ to PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
src_path = os.path.join(parent_dir, 'src')
sys.path.insert(0, src_path)

from app import ScreenshotManager, capture_full_screen, ScreenshotWindow

# =========================
# Unit Tests
# =========================
class TestScreenshotManager(unittest.TestCase):
    def setUp(self):
        self.manager = ScreenshotManager(
            reuse_same_image=True,
            directory='test_images',
            selected_mode='Full Screen'
        )
        os.makedirs('test_images', exist_ok=True)

    def tearDown(self):
        for file in os.listdir('test_images'):
            file_path = os.path.join('test_images', file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir('test_images')

    @patch('app.capture_full_screen')
    def test_capture_and_save_reuse_true(self, mock_capture):
        mock_capture.return_value = 'test_images/FullScreen_temp.png'
        with open('test_images/FullScreen_temp.png', 'w') as f:
            f.write('dummy data')

        result = self.manager.capture_and_save(mock_capture)
        self.assertEqual(result[0], os.path.join('test_images', 'FullScreen.png'))

    @patch('app.capture_full_screen')
    def test_capture_and_save_reuse_false(self, mock_capture):
        self.manager.reuse_same_image = False
        mock_capture.return_value = 'test_images/FullScreen_temp.png'
        with open('test_images/FullScreen_temp.png', 'w') as f:
            f.write('dummy data')

        result = self.manager.capture_and_save(mock_capture)
        self.assertTrue(os.path.basename(result[0]).endswith('.png'))

# =========================
# Integration Tests
# =========================
class TestIntegrationFlow(unittest.TestCase):
    @patch('app.capture_full_screen')
    def test_full_flow(self, mock_capture):
        mock_capture.return_value = 'test_images/FullScreen.png'
        with open('test_images/FullScreen.png', 'w') as f:
            f.write('dummy data')

        manager = ScreenshotManager()
        result = manager.capture_and_save(mock_capture)
        self.assertIsNotNone(result)

if __name__ == '__main__':
    unittest.main()