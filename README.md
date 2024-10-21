# Visualizer
[![Linter](./linter-badge.md)](https://github.com/margusmartsepp/Visualizer/actions)
[![Tests](./test-badge.md)](https://github.com/margusmartsepp/Visualizer/actions)

![Visualizer Icon](screenshot_icon.png) 

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Repository Structure](#repository-structure)
- [Installation](#installation)
- [Usage](#usage)
  - [Launching the Application](#launching-the-application)
  - [Using the GUI](#using-the-gui)
  - [Using the Terminal Client](#using-the-terminal-client)
  - [REST API](#rest-api)
- [Configuration](#configuration)
- [System Tray](#system-tray)
- [Global Shortcuts](#global-shortcuts)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Introduction

**Visualizer** is a Python-based application designed to capture screenshots at regular intervals based on user-defined modes. It offers both a graphical user interface (GUI) and a REST API, providing flexibility for various usage scenarios. Key features include:

- **Multiple Capture Modes:** Full Screen, Specific Application, Specific Monitor, DirectX Game, Specific Browser Tab.
- **Reusable Image Mode:** Overwrite the same image file with each new capture.
- **Floating Screenshot Display:** Always-on-top window displaying the latest screenshot.
- **REST API:** Access screenshots and metadata programmatically.
- **Global Shortcuts:** Copy the latest screenshot to the clipboard using `Ctrl + Shift + C`.
- **System Tray Integration:** Minimize the application to the system tray with quick access controls.
- **Theming:** Customize the application's appearance using Material Design themes.
- **Enhanced Error Handling:** Improved logging and error messages for better troubleshooting.

## Features

- **Capture Modes:** Choose how and what to capture.
- **Toggle Capture:** Start and stop capturing with a single button.
- **Reuse Mode:** Save space by overwriting the same screenshot file.
- **Floating Display:** View the latest screenshot in real-time.
- **REST API:** Integrate with other applications or scripts.
- **Global Shortcuts:** Quick access to clipboard functionality.
- **System Tray:** Run the application unobtrusively in the background.
- **Customizable Themes:** Personalize the look and feel.
- **Improved User Experience:** Streamlined GUI for easier navigation and control.

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/margusmartsepp/Visualizer.git
   cd Visualizer
   ```

2. **Set Up a Virtual Environment (Optional but Recommended):**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

   *Note: The script automatically installs missing packages, but it's good practice to install them manually. Ensure you have the latest version of `Flask` and `PyQt5`.*
   *Note: use following command to update requirements.txt*
   ```bash
   pip-chill > requirements.txt
   ```
## Usage

### Launching the Application

Navigate to the repository directory and run:

```bash
python app.py
```

### Command-Line Arguments:

- **`--host`**
  - **Description:** Flask server host (default: 127.0.0.1).
  - **Default:** `127.0.0.1`

- **`--port`**
  - **Description:** Flask server port (default: 5000).
  - **Default:** `5000`

- **`--mode`**
  - **Description:** Capture mode (default: Full Screen).
  - **Choices:** Full Screen, Specific Application, Specific Monitor, DirectX Game, Specific Browser Tab.
  - **Default:** `Full Screen`

- **`--start`**
  - **Description:** Starts capturing immediately upon launch.
  - **Default:** `False`

- **`--reuse`**
  - **Description:** Enables reuse same image mode (overwrites the same file).
  - **Default:** `False`

- **`--directory`**
  - **Description:** Specifies the directory to save screenshots.
  - **Default:** Current working directory.
  - **Example:** `--directory "C:\Screenshots"`

### Example Usage:

- **Start Capturing Full Screen Immediately with Reuse Enabled:**

  ```bash
  python app.py --start --reuse --mode "Full Screen" --directory "C:\Screenshots"
  ```

- **Start Capturing Specific Application Without Reuse:**

  ```bash
  python app.py --start --mode "Specific Application" --directory "D:\MyScreenshots"
  ```

---
### REST API

Visualizer provides a REST API via Flask to access screenshots and their metadata.

#### **Available Endpoints:**

1. **Get Latest Screenshot**

   - **URL:** `/screenshot`
   - **Method:** `GET`
   - **Description:** Returns the latest screenshot image.
   - **Parameters:**
     - `timestamp` (optional): Used for cache-busting.
   - **Example:**
     ```bash
     curl http://127.0.0.1:5000/screenshot
     ```

2. **Get Screenshot Metadata**

   - **URL:** `/metadata`
   - **Method:** `GET`
   - **Description:** Returns metadata of the latest screenshot.
   - **Response:**
     - `timestamp`: When the screenshot was taken.
     - `dimensions`: Width x Height of the screenshot.
   - **Example:**
     ```bash
     curl http://127.0.0.1:5000/metadata
     ```

3. **Get Server Status**

   - **URL:** `/status`
   - **Method:** `GET`
   - **Description:** Returns the running status of the server.
   - **Response:**
     - `status`: "running"
   - **Example:**
     ```bash
     curl http://127.0.0.1:5000/status
     ```

4. **Viewer Page**

   - **URL:** `/viewer`
   - **Method:** `GET`
   - **Description:** Serves an HTML page that displays the latest screenshot and auto-refreshes it at intervals.
   - **Example:**
     Open your browser and navigate to `http://127.0.0.1:5000/viewer`.

5. **Shutdown Server**

   - **URL:** `/shutdown`
   - **Method:** `POST`
   - **Description:** Shuts down the Flask server.
   - **Example:**
     ```bash
     curl -X POST http://127.0.0.1:5000/shutdown
     ```

#### **Accessing the Viewer:**

Navigate to `http://127.0.0.1:5000/viewer` in your web browser to view the live-updating screenshot.

## System Tray

Visualizer integrates with the system tray, allowing it to run unobtrusively in the background.

### Tray Menu Actions:

1. **Show**
   - Restores the main window.

2. **Start Capturing**
   - Starts the screenshot capturing process.

3. **Stop Capturing**
   - Stops the screenshot capturing process.

4. **About**
   - Displays information about the application.

5. **Quit**
   - Exits the application.

### Minimizing to Tray:

- Closing the main window minimizes the application to the system tray instead of exiting.
- A notification message appears indicating that the application has been minimized.

---

## Global Shortcuts

### Copy to Clipboard:

- **Shortcut:** `Ctrl + Shift + C`
- **Functionality:** Copies the latest screenshot to the system clipboard.
- **Usage:** Press the shortcut combination anywhere in the system to copy the latest screenshot.

---

## Troubleshooting



### b. pywinauto STA Warning

- **Issue:**
  ```
  UserWarning: Revert to STA COM threading mode
  ```
- **Solution:** This warning is benign and can be safely ignored. Alternatively, ensure COM is initialized in STA mode at the start of your application.

### c. Attribute Errors

- **Issue:** `NameError: name 'ScreenshotDisplayWindow' is not defined. Did you mean: 'ScreenshotWindow'?`
- **Solution:** Ensure that all modules are correctly imported and that the `ScreenshotDisplayWindow` class is defined in `display_window.py` and imported into `ui.py`.

### d. General Errors

- **Solution:** Check the `screenshot_viewer.log` file for detailed error messages and stack traces. Ensure all dependencies are installed and that the application has the necessary permissions to capture screenshots.

---
## Running Tests with `pytest`

### 1. Install Dependencies

Ensure all dependencies are installed by running:

```bash
pip install -r requirements.txt
```
### 2. Run Specific Tests
To run tests
```bash
pytest
```

You can also target a specific test function by appending the function name:
```bash
python -m pytest test_all.py::TestIntegrationFlow::test_full_flow
```
### 3. Test Coverage (Optional)
If you want to measure code coverage run:
```bash
pytest --cov=app
```
You can use the --cov-report flag with pytest to generate a more detailed coverage report that shows exactly which lines of code are missing coverage:
```bash
pytest --cov=app --cov-report term-missing
```
---

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your enhancements or bug fixes.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Final Notes

By following this structured approach, your **Visualizer** application is now more robust, maintainable, and user-friendly. The separation of business logic from the UI not only makes the codebase cleaner but also facilitates testing and future enhancements.

Feel free to reach out if you encounter further issues or need additional features!

---

**Happy Screenshot Capturing!**
