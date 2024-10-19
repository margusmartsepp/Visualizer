# Visualizer

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

## Features

- **Capture Modes:** Choose how and what to capture.
- **Toggle Capture:** Start and stop capturing with a single button.
- **Reuse Mode:** Save space by overwriting the same screenshot file.
- **Floating Display:** View the latest screenshot in real-time.
- **REST API:** Integrate with other applications or scripts.
- **Global Shortcuts:** Quick access to clipboard functionality.
- **System Tray:** Run the application unobtrusively in the background.
- **Customizable Themes:** Personalize the look and feel.

## Repository Structure

```
Visualizer/
├── main.py
├── screenshot_manager.py
├── flask_app.py
├── display_window.py
├── ui.py
├── requirements.txt
├── README.md
└── screenshot_icon.png  # (Optional) Custom icon for system tray
```

### File Descriptions:

- **`main.py`**
  - Entry point of the application.
  - Parses command-line arguments.
  - Initializes components and starts the application.

- **`screenshot_manager.py`**
  - Contains the `ScreenshotManager` class.
  - Handles all screenshot capturing and saving logic.

- **`flask_app.py`**
  - Contains the `FlaskApp` class.
  - Manages the Flask web server and its routes.

- **`display_window.py`**
  - Contains the `ScreenshotDisplayWindow` class.
  - Manages the floating window that displays the latest screenshot.

- **`ui.py`**
  - Contains the `ScreenshotWindow` class.
  - Manages the main PyQt5 UI.

- **`requirements.txt`**
  - Lists all Python dependencies required by the application.

- **`README.md`**
  - This documentation.

- **`screenshot_icon.png`**
  - (Optional) Custom icon for the system tray. If absent, a default system icon will be used.

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/Visualizer.git
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

   *Note: The script automatically installs missing packages, but it's good practice to install them manually.*

4. **Ensure `screenshot_icon.png` Exists:**

   - Place an icon file named `screenshot_icon.png` in the repository root for a custom system tray icon.
   - If absent, a default system icon will be used, and a warning will be logged.

## Usage

### Launching the Application

Navigate to the repository directory and run:

```bash
python main.py [OPTIONS]
```

### Command-Line Options

- `--host`: Flask server host (default: `127.0.0.1`)
- `--port`: Flask server port (default: `5000`)
- `--mode`: Capture mode. Choices:
  - `Full Screen`
  - `Specific Application`
  - `Specific Monitor`
  - `DirectX Game`
  - `Specific Browser Tab`
  
  *(default: `Full Screen`)*
  
- `--start`: Start capturing immediately upon launch.
- `--reuse`: Enable reuse same image mode.
- `--directory`: Directory to save screenshots (default: current working directory).

**Examples:**

- **Start Capturing Full Screen Immediately with Reuse Enabled:**

  ```bash
  python main.py --start --reuse --mode "Full Screen" --directory "C:\Screenshots"
  ```

- **Start Capturing Specific Application Without Reuse:**

  ```bash
  python main.py --start --mode "Specific Application" --directory "D:\MyScreenshots"
  ```

### Using the GUI

1. **Launch the Application:**

   ```bash
   python main.py
   ```

2. **Capture Tab:**

   - **Select Capture Mode:** Choose between "Full Screen", "Specific Application", "Specific Monitor", "DirectX Game", or "Specific Browser Tab".
   - **Dynamic Controls:** Depending on the selected mode, additional options appear to select the specific application, monitor, etc.
   - **Toggle Capturing:** Use the **Start Capturing** toggle button to begin taking screenshots at intervals defined by `INTERVAL_SECONDS`. The button text changes to **Stop Capturing** when active.
   - **Floating Screenshot Display:** The latest screenshot appears in a floating window on your screen, always on top. You can close this window by clicking the **X** button.

3. **Settings Tab:**

   - **Flask Configuration:** Set the host and port for the Flask web server.
   - **Reuse Same Image:** Enable this to overwrite the same screenshot file with each new capture.
   - **Select File Location:** Choose the directory where screenshots will be saved.
   - **Theme Selection:** Use the **Select Theme** dropdown to choose different Material Design themes. The theme changes immediately upon selection.

### Using the Terminal Client

The application is primarily GUI-based, but you can control it via command-line arguments. For more advanced terminal interactions, further development is required to implement a CLI interface.

**Basic Terminal Commands:**

- **Start Capturing with Specific Mode and Directory:**

  ```bash
  python main.py --start --mode "Full Screen" --directory "C:\Screenshots"
  ```

- **Start Capturing in Specific Application Mode:**

  ```bash
  python main.py --start --mode "Specific Application" --directory "D:\MyScreenshots"
  ```

**Note:**
Implementing a full terminal client requires additional code not covered in this scope. Future enhancements can include a dedicated CLI for more granular control.

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

---

## Configuration

### Command-Line Arguments

- **`--host`**
  - **Description:** Specifies the Flask server host.
  - **Default:** `127.0.0.1`
  - **Example:** `--host "192.168.1.100"`

- **`--port`**
  - **Description:** Specifies the Flask server port.
  - **Default:** `5000`
  - **Example:** `--port 8080`

- **`--mode`**
  - **Description:** Sets the screenshot capture mode.
  - **Choices:**
    - `Full Screen`
    - `Specific Application`
    - `Specific Monitor`
    - `DirectX Game`
    - `Specific Browser Tab`
  - **Default:** `Full Screen`
  - **Example:** `--mode "Specific Application"`

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
  python main.py --start --reuse --mode "Full Screen" --directory "C:\Screenshots"
  ```

- **Start Capturing Specific Application Without Reuse:**

  ```bash
  python main.py --start --mode "Specific Application" --directory "D:\MyScreenshots"
  ```

---

## System Tray

Visualizer integrates with the system tray, allowing it to run unobtrusively in the background.

### Tray Icon:

- **Custom Icon:**
  - Place an icon file named `screenshot_icon.png` in the repository root.
  - If absent, the application uses a default system icon, and a warning is logged.

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

### a. Missing Tray Icon Warning

- **Issue:** `QSystemTrayIcon::setVisible: No Icon set`
- **Solution:** Ensure that `screenshot_icon.png` exists in the repository root. If not, the application uses a default icon, and you can ignore the warning.

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
