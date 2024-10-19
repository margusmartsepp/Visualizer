# flask_app.py

import os
from flask import Flask, send_file, jsonify, request
from PIL import Image
from datetime import datetime
import logging
import threading

from screenshot_manager import ScreenshotManager  # Ensure correct import path
from config import INTERVAL_SECONDS  # Import INTERVAL_SECONDS

def run_flask_app(flask_app):
    """Run the Flask app."""
    logging.info(f"Starting Flask server on {flask_app.host}:{flask_app.port}")
    # Suppress Flask's default logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    flask_app.app.run(host=flask_app.host, port=flask_app.port, threaded=True)

class FlaskApp:
    """Class to handle the Flask web server."""

    def __init__(self, screenshot_manager, host='127.0.0.1', port=5000):
        self.app = Flask(__name__)
        self.screenshot_manager = screenshot_manager
        self.host = host
        self.port = port
        self.setup_routes()

    def setup_routes(self):
        """Define the routes for the Flask app."""

        @self.app.route('/screenshot', methods=['GET'])
        def get_screenshot():
            """Endpoint to get the latest screenshot."""
            screenshot_path = self.screenshot_manager.file_path
            if os.path.exists(screenshot_path):
                try:
                    # Retrieve 'timestamp' from query parameters for cache-busting
                    timestamp = request.args.get('timestamp', '')
                    # Log the request
                    logging.info("Screenshot requested via /screenshot endpoint.")
                    return send_file(
                        screenshot_path,
                        mimetype='image/png',
                        as_attachment=False,
                        download_name=os.path.basename(screenshot_path)  # Updated parameter
                    )
                except Exception as e:
                    logging.error(f"Error in /screenshot endpoint: {e}")
                    return jsonify({'error': str(e)}), 500
            else:
                logging.warning("No screenshot available for /screenshot endpoint.")
                return jsonify({'error': 'No screenshot available.'}), 404

        @self.app.route('/metadata', methods=['GET'])
        def get_metadata():
            """Endpoint to get metadata of the latest screenshot."""
            screenshot_path = self.screenshot_manager.file_path
            if os.path.exists(screenshot_path):
                try:
                    # Get file modification time
                    timestamp = datetime.fromtimestamp(os.path.getmtime(screenshot_path)).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    # Get image dimensions
                    with Image.open(screenshot_path) as img:
                        width, height = img.size
                    logging.info("Metadata requested via /metadata endpoint.")
                    return jsonify({
                        'timestamp': timestamp,
                        'dimensions': f"{width}x{height}"
                    }), 200
                except Exception as e:
                    logging.error(f"Error in /metadata endpoint: {e}")
                    return jsonify({'error': str(e)}), 500
            else:
                logging.warning("No screenshot available for /metadata endpoint.")
                return jsonify({'error': 'No screenshot available.'}), 404

        @self.app.route('/status', methods=['GET'])
        def get_status():
            """Endpoint to get the status of the application."""
            logging.info("Status requested via /status endpoint.")
            return jsonify({'status': 'running'}), 200

        @self.app.route('/viewer', methods=['GET'])
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
                <img id="screenshot" src="/screenshot?timestamp={int(datetime.now().timestamp() * 1000)}" alt="Latest Screenshot">
                
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

        @self.app.route('/shutdown', methods=['POST'])
        def shutdown_server():
            """Endpoint to shutdown the Flask server."""
            func = request.environ.get('werkzeug.server.shutdown')
            if func is None:
                logging.error("Shutdown attempted, but not running with the Werkzeug Server.")
                return jsonify({'error': 'Not running with the Werkzeug Server'}), 500
            func()
            logging.info("Server shutting down via /shutdown endpoint.")
            return jsonify({'message': 'Server shutting down...'}), 200

class FlaskAppThread(threading.Thread):
    """Thread to run the Flask server."""
    def __init__(self, flask_app):
        super().__init__()
        self.flask_app = flask_app
        self.daemon = True

    def run(self):
        run_flask_app(self.flask_app)
