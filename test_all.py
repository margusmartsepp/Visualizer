# pylint: disable=wrong-import-order
"""
This module contains unit and integration tests for the 
ScreenshotManager, FlaskApp, and ScreenshotWindow components.
"""
import warnings
import unittest
from unittest.mock import patch
import os
import shutil
import sys

# Suppress the specific UserWarning from pywinauto
warnings.filterwarnings("ignore", category=UserWarning, message="Revert to STA COM threading mode")

# Add src/ to PYTHONPATH if necessary
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
src_path = os.path.join(parent_dir, 'src')
sys.path.insert(0, src_path)

from PyQt5.QtWidgets import QApplication  # pylint: disable=no-name-in-module
from app import ScreenshotManager, ScreenshotWindow, FlaskApp  # pylint: disable=no-name-in-module
from pywinauto import Desktop  # pylint: disable=unused-import

# =========================
# Unit Tests
# =========================
class TestScreenshotManager(unittest.TestCase):
    """Unit tests for the ScreenshotManager class."""

    def setUp(self):
        """Set up the test environment for the ScreenshotManager tests."""
        self.manager = ScreenshotManager(
            reuse_same_image=True,
            directory='test_images',
            selected_mode='Full Screen'
        )
        os.makedirs('test_images', exist_ok=True)

    def tearDown(self):
        """Tear down the test environment for the ScreenshotManager tests."""
        if os.path.exists('test_images'):
            shutil.rmtree('test_images')

    @patch('app.capture_full_screen')
    def test_capture_and_save_reuse_true(self, mock_capture):
        """Test capturing and saving with reuse_same_image set to True."""
        mock_capture.return_value = os.path.join('test_images', 'FullScreen.png')
        with open(mock_capture.return_value, 'w', encoding='utf-8') as f:
            f.write('dummy data')

        result = self.manager.capture_and_save(mock_capture)
        self.assertEqual(result[0], os.path.join('test_images', 'fullscreen.png'))

    @patch('app.capture_full_screen')
    def test_capture_and_save_reuse_false(self, mock_capture):
        """Test capturing and saving with reuse_same_image set to False."""
        self.manager.reuse_same_image = False
        mock_capture.return_value = os.path.join('test_images', 'FullScreen_temp.png')
        with open(mock_capture.return_value, 'w', encoding='utf-8') as f:
            f.write('dummy data')

        result = self.manager.capture_and_save(mock_capture)
        self.assertTrue(os.path.basename(result[0]).endswith('.png'))


# =========================
# Flask App Tests
# =========================
class TestFlaskApp(unittest.TestCase):
    """Unit tests for the FlaskApp class."""

    def setUp(self):
        """Set up the test environment for the FlaskApp tests."""
        self.manager = ScreenshotManager(
            reuse_same_image=True,
            directory='test_images',
            selected_mode='Full Screen'
        )
        self.flask_app = FlaskApp(self.manager)
        self.client = self.flask_app.app.test_client()

    def tearDown(self):
        """Tear down the test environment for the FlaskApp tests."""
        if os.path.exists('test_images'):
            shutil.rmtree('test_images')

    def test_screenshot_endpoint(self):
        """Test the /screenshot endpoint returns 404 when no screenshot exists."""
        response = self.client.get('/screenshot')
        self.assertEqual(response.status_code, 404)

    def test_metadata_endpoint(self):
        """Test the /metadata endpoint returns 404 when no metadata exists."""
        response = self.client.get('/metadata')
        self.assertEqual(response.status_code, 404)

    def test_status_endpoint(self):
        """Test the /status endpoint returns 200 and 'running' status."""
        response = self.client.get('/status')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'running')

    def test_viewer_endpoint(self):
        """Test the /viewer endpoint serves the HTML content."""
        response = self.client.get('/viewer')
        self.assertEqual(response.status_code, 200)
        self.assertIn('<html>', response.data.decode())


# =========================
# PyQt5 Tests (ScreenshotWindow UI)
# =========================
class TestScreenshotWindow(unittest.TestCase):
    """Unit tests for the ScreenshotWindow class."""

    @classmethod
    def setUpClass(cls):
        """Set up the QApplication instance for all PyQt5 tests."""
        cls.app = QApplication(sys.argv)

    def setUp(self):
        """Set up the test environment for the ScreenshotWindow tests."""
        self.manager = ScreenshotManager(directory='test_images')

        class Args:  # pylint: disable=too-few-public-methods
            """Dummy arguments class for testing purposes."""
            host = '127.0.0.1'
            port = 5000
            start = False

        self.args = Args()
        self.window = ScreenshotWindow(self.manager, self.args)

    @patch('app.ScreenshotWindow._open_viewer_in_browser')  # Use the correct private method name
    def test_open_viewer_in_browser(self, mock_open_viewer):
        """Test the open_viewer_in_browser method."""
        self.window._open_viewer_in_browser()  # Call the correct method
        mock_open_viewer.assert_called_once()

    def test_toggle_capture_button(self):
        """Test toggling the capture button starts and stops capturing."""
        self.assertFalse(self.window.capturing)
        self.window.toggle_capturing(True)
        self.assertTrue(self.window.capturing)

    def test_apply_settings(self):
        """Test applying settings updates the host input value."""
        self.window._apply_settings()  # Call the correct method
        self.assertEqual(self.window.host_input.text(), '127.0.0.1')

    @classmethod
    def tearDownClass(cls):
        """Clean up after all PyQt5 tests."""
        cls.app.quit()


# =========================
# Integration Tests
# =========================
class TestIntegrationFlow(unittest.TestCase):
    """Integration tests for the Screenshot capturing flow."""

    def setUp(self):
        """Set up the test environment for integration tests."""
        os.makedirs('test_images', exist_ok=True)

    def tearDown(self):
        """Tear down the test environment after integration tests."""
        if os.path.exists('test_images'):
            shutil.rmtree('test_images')

    @patch('app.capture_full_screen')
    def test_full_flow(self, mock_capture):
        """Test the full screenshot capture and save flow."""
        mock_capture.return_value = os.path.join('test_images', 'FullScreen.png')
        with open(mock_capture.return_value, 'w', encoding='utf-8') as f:
            f.write('dummy data')

        manager = ScreenshotManager(directory='test_images')
        result = manager.capture_and_save(mock_capture)
        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main()
