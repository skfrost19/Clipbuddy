# SmartClip

A lightweight, cross-platform clipboard manager with global hotkey support, system tray integration, and persistent history.

Made with ❤️ using AI (Claude Sonnet 4.5).

## Features

### Core Functionality
- **Clipboard History**: Automatically captures and stores everything you copy
- **Global Hotkeys**: Access your clipboard history from any application
- **Alt+Tab Style Navigation**: Hold modifier key and press hotkey repeatedly to cycle through items
- **Instant Paste**: Release the modifier key to paste the selected item immediately
- **Search**: Quickly filter through your clipboard history

### System Integration
- **System Tray**: Runs quietly in the background, accessible from the system tray
- **Run at Startup**: Optionally start with your operating system
- **Persistent Storage**: Clipboard history survives application restarts and system reboots
- **Cross-Platform**: Works on Windows and Linux

### User Experience
- **Dark Theme Overlay**: Clean, modern overlay interface
- **Configurable Hotkeys**: Customize keyboard shortcuts to your preference
- **Adjustable History Size**: Control how many items to keep in history
- **Notification Control**: Toggle system notifications on or off


## Installation

### Option 1: Download Pre-built Executable

Download the latest release from the [Releases](https://github.com/skfrost19/Clipbuddy/releases) page:
- Windows: `SmartClip.exe`
- Linux: `SmartClip`

### Option 2: Run from Source

**Prerequisites:**
- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended)

**Steps:**

```bash
# Clone the repository
git clone https://github.com/skfrost19/Clipbuddy.git
cd Clipbuddy

# Install dependencies
uv sync

# Run the application
uv run main.py
```


## Usage

### Default Hotkeys

| Action | Hotkey |
|--------|--------|
| Open clipboard overlay | `Ctrl+Q` |
| Cycle to next item | `Ctrl+Q` (while overlay is open) |
| Paste selected item | Release `Ctrl` |
| Close overlay | `Esc` |
| Navigate items | Arrow keys |
| Select and paste | `Enter` |

### Workflow Example

1. Copy several items normally using `Ctrl+C`
2. Press `Ctrl+Q` to open the clipboard overlay
3. While holding `Ctrl`, press `Q` repeatedly to cycle through items
4. Release `Ctrl` to paste the highlighted item
5. The selected text is automatically pasted into your active application

### System Tray

- **Single/Double click**: Show the main window
- **Right-click menu**:
  - Show Smart Clip: Open the main window
  - Settings: Configure the application
  - Exit: Close the application completely

### Settings

Access settings through the main window or system tray menu:

| Setting | Description |
|---------|-------------|
| Run at startup | Launch SmartClip when your system starts |
| Show notifications | Display tray notifications |
| Swap hotkey | Global hotkey to open clipboard overlay |
| Type hotkey | Alternative hotkey (optional) |
| Clipboard stack size | Maximum number of items to store |


## Building from Source

### Prerequisites

```bash
# Install development dependencies
uv sync --dev
```

### Build Commands

**Simple build:**
```bash
uv run python build.py
```

**Clean build (removes previous artifacts):**
```bash
uv run python build.py --clean
```

**Using PyInstaller directly:**
```bash
uv run pyinstaller SmartClip.spec
```

### Build Output

| Platform | Output Location |
|----------|-----------------|
| Windows | `dist/SmartClip.exe` |
| Linux | `dist/SmartClip` |
| Linux AppImage | `dist/SmartClip-1.0.0-x86_64.AppImage` |

### Building Linux AppImage

AppImage is a portable format that works on most Linux distributions without installation:

```bash
# Make the script executable
chmod +x build_appimage.sh

# Build the AppImage (must be run on Linux)
./build_appimage.sh
```

The script will:
1. Download appimagetool if not present
2. Build the application with PyInstaller
3. Create the AppDir structure with all required files
4. Generate the AppImage

### Cleanup

To remove all build artifacts:

```bash
chmod +x cleanup.sh
./cleanup.sh
```

### Cross-Platform Notes

PyInstaller cannot cross-compile. To build for a specific platform, you must build on that platform:

- Build Windows executable on Windows
- Build Linux executable/AppImage on Linux


## Data Storage

SmartClip stores its data in platform-appropriate locations:

| Platform | Location |
|----------|----------|
| Windows | `%APPDATA%\SmartClip\` |
| Linux | `~/.config/SmartClip/` |

**Files:**
- `clipboard_history.json`: Your clipboard history
- `settings.json`: Application configuration


## Requirements

- Python 3.10+
- PyQt6
- keyboard

Note: The `keyboard` library may require administrator/root privileges for global hotkeys to work system-wide.


## Troubleshooting

### Hotkeys not working

- **Windows**: Try running the application as Administrator
- **Linux**: Run with `sudo` or add your user to the `input` group

### Application not starting at login

- Verify the "Run at startup" option is enabled in Settings
- **Windows**: Check `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run` in Registry Editor
- **Linux**: Check `~/.config/autostart/SmartClip.desktop`

### Clipboard not being captured

- Ensure the application is running (check system tray)
- Some applications use non-standard clipboard mechanisms that may not be captured


## Project Structure

```
Clipbuddy/
├── main.py              # Main application source
├── build.py             # Build script for creating executables
├── SmartClip.spec       # PyInstaller configuration
├── icon.png             # Application icon
├── README.md            # This file
├── pyproject.toml       # Project dependencies
└── dist/                # Built executables (after building)
```


## License

MIT License (c) 2025 Shahil Kumar. See [LICENSE](LICENSE) for details.


## Contributing

Contributions are welcome. Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
