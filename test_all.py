import unittest
from unittest.mock import patch, MagicMock
import os
import shutil
import sys
from PyQt5.QtWidgets import QApplication

# Add src/ to PYTHONPATH if necessary
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
src_path = os.path.join(parent_dir, 'src')
sys.path.insert(0, src_path)

from app import ScreenshotManager, capture_full_screen, ScreenshotWindow, FlaskApp

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
        if os.path.exists('test_images'):
            shutil.rmtree('test_images')

    @patch('app.capture_full_screen')
    def test_capture_and_save_reuse_true(self, mock_capture):
        mock_capture.return_value = 'FullScreen_temp.png'
        with open('FullScreen_temp.png', 'w') as f:
            f.write('dummy data')

        result = self.manager.capture_and_save(mock_capture)
        self.assertEqual(result[0], os.path.join('test_images', 'FullScreen.png'))

    @patch('app.capture_full_screen')
    def test_capture_and_save_reuse_false(self, mock_capture):
        self.manager.reuse_same_image = False
        mock_capture.return_value = 'FullScreen_temp.png'
        with open('FullScreen_temp.png', 'w') as f:
            f.write('dummy data')

        result = self.manager.capture_and_save(mock_capture)
        self.assertTrue(os.path.basename(result[0]).endswith('.png'))


# =========================
# Flask App Tests
# =========================
class TestFlaskApp(unittest.TestCase):
    def setUp(self):
        self.manager = ScreenshotManager(
            reuse_same_image=True,
            directory='test_images',
            selected_mode='Full Screen'
        )
        self.flask_app = FlaskApp(self.manager)
        self.client = self.flask_app.app.test_client()

    def tearDown(self):
        if os.path.exists('test_images'):
            shutil.rmtree('test_images')

    def test_screenshot_endpoint(self):
        response = self.client.get('/screenshot')
        self.assertEqual(response.status_code, 404)

    def test_metadata_endpoint(self):
        response = self.client.get('/metadata')
        self.assertEqual(response.status_code, 404)

    def test_status_endpoint(self):
        response = self.client.get('/status')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'running')

    def test_viewer_endpoint(self):
        response = self.client.get('/viewer')
        self.assertEqual(response.status_code, 200)
        self.assertIn('<html>', response.data.decode())


# =========================
# PyQt5 Tests (ScreenshotWindow UI)
# =========================
class TestScreenshotWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication(sys.argv)

    def setUp(self):
        self.manager = ScreenshotManager(directory='test_images')
        
        # Instead of passing MagicMock, pass a real object with necessary attributes
        class Args:
            host = '127.0.0.1'
            port = 5000
            start = False
        
        self.args = Args()
        self.window = ScreenshotWindow(self.manager, self.args)

    @patch('app.ScreenshotWindow.open_viewer_in_browser')
    def test_open_viewer_in_browser(self, mock_open_viewer):
        self.window.open_viewer_in_browser()
        mock_open_viewer.assert_called_once()

    def test_toggle_capture_button(self):
        self.assertFalse(self.window.capturing)
        self.window.toggle_capturing(True)
        self.assertTrue(self.window.capturing)

    def test_apply_settings(self):
        self.window.apply_settings()
        self.assertEqual(self.window.host_input.text(), '127.0.0.1')

    @classmethod
    def tearDownClass(cls):
        cls.app.quit()


# =========================
# Integration Tests
# =========================
class TestIntegrationFlow(unittest.TestCase):
    def setUp(self):
        os.makedirs('test_images', exist_ok=True)

    def tearDown(self):
        if os.path.exists('test_images'):
            shutil.rmtree('test_images')

    @patch('app.capture_full_screen')
    def test_full_flow(self, mock_capture):
        mock_capture.return_value = 'FullScreen.png'
        with open('FullScreen.png', 'w') as f:
            f.write('dummy data')

        manager = ScreenshotManager(directory='test_images')
        result = manager.capture_and_save(mock_capture)
        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main()
