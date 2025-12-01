import sys
import os
import json
import platform
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QListWidget,
    QListWidgetItem,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QLineEdit,
    QSpinBox,
    QPushButton,
    QWidget,
    QAbstractItemView,
    QMessageBox,
    QSystemTrayIcon,
    QMenu,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QIcon,
    QFont,
    QGuiApplication,
    QAction,
    QPixmap,
    QPainter,
    QColor,
)
import keyboard  # For global hotkeys


# ============== Startup Manager ==============
class StartupManager:
    """Manages run-at-startup functionality for Windows and Linux."""

    APP_NAME = "SmartClip"

    @staticmethod
    def get_executable_path():
        """Get the path to the current executable or script."""
        if getattr(sys, "frozen", False):
            # Running as compiled executable
            return sys.executable
        else:
            # Running as script
            return os.path.abspath(sys.argv[0])

    @staticmethod
    def is_windows():
        return platform.system() == "Windows"

    @staticmethod
    def is_linux():
        return platform.system() == "Linux"

    @classmethod
    def enable_startup(cls):
        """Enable run at startup."""
        if cls.is_windows():
            return cls._enable_startup_windows()
        elif cls.is_linux():
            return cls._enable_startup_linux()
        return False

    @classmethod
    def disable_startup(cls):
        """Disable run at startup."""
        if cls.is_windows():
            return cls._disable_startup_windows()
        elif cls.is_linux():
            return cls._disable_startup_linux()
        return False

    @classmethod
    def is_startup_enabled(cls):
        """Check if startup is enabled."""
        if cls.is_windows():
            return cls._is_startup_enabled_windows()
        elif cls.is_linux():
            return cls._is_startup_enabled_linux()
        return False

    # Windows implementation
    @classmethod
    def _enable_startup_windows(cls):
        try:
            import winreg

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            exe_path = cls.get_executable_path()

            # If running as script, use pythonw to run without console
            if exe_path.endswith(".py"):
                python_exe = sys.executable.replace("python.exe", "pythonw.exe")
                if os.path.exists(python_exe):
                    exe_path = f'"{python_exe}" "{exe_path}"'
                else:
                    exe_path = f'"{sys.executable}" "{exe_path}"'
            else:
                exe_path = f'"{exe_path}"'

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, cls.APP_NAME, 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Failed to enable startup on Windows: {e}")
            return False

    @classmethod
    def _disable_startup_windows(cls):
        try:
            import winreg

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
            )
            try:
                winreg.DeleteValue(key, cls.APP_NAME)
            except FileNotFoundError:
                pass  # Value doesn't exist
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Failed to disable startup on Windows: {e}")
            return False

    @classmethod
    def _is_startup_enabled_windows(cls):
        try:
            import winreg

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(key, cls.APP_NAME)
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except Exception:
            return False

    # Linux implementation
    @classmethod
    def _get_linux_autostart_path(cls):
        autostart_dir = Path.home() / ".config" / "autostart"
        autostart_dir.mkdir(parents=True, exist_ok=True)
        return autostart_dir / f"{cls.APP_NAME}.desktop"

    @classmethod
    def _enable_startup_linux(cls):
        try:
            desktop_file = cls._get_linux_autostart_path()
            exe_path = cls.get_executable_path()

            # If running as script, use python to run
            if exe_path.endswith(".py"):
                exe_path = f"{sys.executable} {exe_path}"

            content = f"""[Desktop Entry]
Type=Application
Name={cls.APP_NAME}
Exec={exe_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=Smart Clipboard Manager
"""
            desktop_file.write_text(content)
            return True
        except Exception as e:
            print(f"Failed to enable startup on Linux: {e}")
            return False

    @classmethod
    def _disable_startup_linux(cls):
        try:
            desktop_file = cls._get_linux_autostart_path()
            if desktop_file.exists():
                desktop_file.unlink()
            return True
        except Exception as e:
            print(f"Failed to disable startup on Linux: {e}")
            return False

    @classmethod
    def _is_startup_enabled_linux(cls):
        return cls._get_linux_autostart_path().exists()


# ============== Clipboard History Storage ==============
class ClipboardStorage:
    """Manages persistent storage of clipboard history."""

    def __init__(self, max_size=1000):
        self.max_size = max_size
        self.data_dir = self._get_data_dir()
        self.data_file = self.data_dir / "clipboard_history.json"
        self.settings_file = self.data_dir / "settings.json"
        self._ensure_data_dir()

    def _get_data_dir(self):
        """Get the appropriate data directory for the OS."""
        if platform.system() == "Windows":
            base = Path(os.environ.get("APPDATA", Path.home()))
        else:
            base = Path.home() / ".config"
        return base / "SmartClip"

    def _ensure_data_dir(self):
        """Ensure the data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save_history(self, items: list):
        """Save clipboard history to file."""
        try:
            # Limit to max_size
            items = items[: self.max_size]
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save clipboard history: {e}")

    def load_history(self) -> list:
        """Load clipboard history from file."""
        try:
            if self.data_file.exists():
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Failed to load clipboard history: {e}")
        return []

    def save_settings(self, settings: dict):
        """Save application settings to file."""
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def load_settings(self) -> dict:
        """Load application settings from file."""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Failed to load settings: {e}")
        return {}


class ClipboardOverlay(QWidget):
    """Overlay window that appears when hotkey is pressed."""

    def __init__(self, parent=None, clipboard_items=None):
        super().__init__(None)  # No parent - independent window
        self.clipboard_items = clipboard_items or []
        self.parent_window = parent

        # Make it a frameless, always-on-top overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self.setFixedSize(500, 400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Container with styling
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border: 2px solid #455A64;
                border-radius: 10px;
            }
        """)
        container_layout = QVBoxLayout(container)

        # Header
        header = QLabel("CLIPBOARD HISTORY")
        header.setStyleSheet("""
            font-weight: bold; 
            color: white; 
            background-color: #455A64; 
            padding: 10px;
            border-radius: 8px 8px 0 0;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(header)

        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search clipboard...")
        self.search_bar.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                margin: 5px;
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
            }
        """)
        self.search_bar.textChanged.connect(self.filter_list)
        container_layout.addWidget(self.search_bar)

        # List widget
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                color: white;
                border: none;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #3c3c3c;
            }
            QListWidget::item:selected {
                background-color: #455A64;
            }
            QListWidget::item:hover {
                background-color: #3c3c3c;
            }
        """)
        self.list_widget.itemDoubleClicked.connect(self.on_item_selected)
        self.list_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        container_layout.addWidget(self.list_widget)

        # Hint label
        hint = QLabel("Release Ctrl to paste • Keep pressing G to cycle • Esc to close")
        hint.setStyleSheet("color: #888; padding: 5px; font-size: 11px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(hint)

        layout.addWidget(container)

        # Populate list
        self.populate_list()

    def populate_list(self):
        self.list_widget.clear()
        for text in self.clipboard_items:
            item = QListWidgetItem(text)
            self.list_widget.addItem(item)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def filter_list(self, text):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def on_item_selected(self, item):
        """Copy selected item to clipboard and close."""
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(item.text())
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            current = self.list_widget.currentItem()
            if current:
                self.on_item_selected(current)
        elif event.key() == Qt.Key.Key_Down:
            current_row = self.list_widget.currentRow()
            if current_row < self.list_widget.count() - 1:
                self.list_widget.setCurrentRow(current_row + 1)
        elif event.key() == Qt.Key.Key_Up:
            current_row = self.list_widget.currentRow()
            if current_row > 0:
                self.list_widget.setCurrentRow(current_row - 1)
        else:
            super().keyPressEvent(event)

    def showEvent(self, event):
        # Center on screen
        screen = QGuiApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

        # Focus search bar
        self.search_bar.setFocus()
        super().showEvent(event)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(400, 350)

        layout = QVBoxLayout()
        layout.setSpacing(15)

        # header
        header = QLabel("SETTINGS")
        header.setStyleSheet(
            "font-weight: bold; color: white; background-color: #455A64; padding: 10px;"
        )
        header.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(header)

        # checkboxes
        self.chk_startup = QCheckBox("Run the program when Windows starts")
        self.chk_startup.setChecked(True)
        self.chk_notify = QCheckBox("Show the clipboard change notifications")
        self.chk_notify.setChecked(True)

        layout.addWidget(self.chk_startup)
        layout.addWidget(self.chk_notify)

        # hotkey grid
        hotkey_layout = QVBoxLayout()

        # swap hotkey
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Swap hotkey"))
        self.txt_swap = QLineEdit("Ctrl + Q")
        row1.addWidget(self.txt_swap)
        hotkey_layout.addLayout(row1)

        # type hotkey
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Type hotkey"))
        self.txt_type = QLineEdit("None")
        row2.addWidget(self.txt_type)
        hotkey_layout.addLayout(row2)

        layout.addLayout(hotkey_layout)

        # mouse option
        self.chk_mouse = QCheckBox(
            "Copy to the clipboard by moving the mouse to the top left corner."
        )
        layout.addWidget(self.chk_mouse)

        # stack size
        stack_layout = QHBoxLayout()
        stack_layout.addWidget(QLabel("Clipboard stack size"))
        self.spin_size = QSpinBox()
        self.spin_size.setRange(1, 9999)
        self.spin_size.setValue(1000)
        stack_layout.addWidget(self.spin_size)
        stack_layout.addStretch()
        layout.addLayout(stack_layout)

        # OK button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_ok = QPushButton("OK")
        self.btn_ok.setFixedWidth(80)
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)
        layout.addStretch()
        self.setLayout(layout)


class SmartClipUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Clip")
        self.resize(500, 600)

        # Set window icon
        self.set_window_icon()

        # Initialize storage
        self.storage = ClipboardStorage()

        # Load saved settings
        saved_settings = self.storage.load_settings()

        # Store current hotkey settings
        self.swap_hotkey = saved_settings.get("swap_hotkey", "ctrl+g")
        self.type_hotkey = saved_settings.get("type_hotkey", "")
        self.run_at_startup = saved_settings.get("run_at_startup", False)
        self.show_notifications = saved_settings.get("show_notifications", True)
        self.max_stack_size = saved_settings.get("max_stack_size", 1000)

        # Store hotkey hooks to allow removal
        self.swap_hook = None
        self.type_hook = None
        self.ctrl_release_hook = None

        # Track modifier key for the hotkey (e.g., "ctrl" from "ctrl+g")
        self.swap_modifier = "ctrl"
        self.swap_key = "g"

        # Overlay window reference
        self.overlay = None

        # central widget setup
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # top bar (History label + Settings button)
        top_bar = QWidget()
        top_bar.setStyleSheet("background-color: #455A64; color: white;")
        top_layout = QHBoxLayout(top_bar)

        lbl_history = QLabel("HISTORY")
        lbl_history.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))

        btn_settings = QPushButton("Settings")
        btn_settings.setStyleSheet("border: none; color: white; font-weight: bold;")
        btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_settings.clicked.connect(self.open_settings)

        top_layout.addWidget(lbl_history)
        top_layout.addStretch()
        top_layout.addWidget(btn_settings)
        main_layout.addWidget(top_bar)

        # search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search")
        self.search_bar.setStyleSheet("padding: 5px; margin: 5px;")
        self.search_bar.textChanged.connect(self.filter_list)
        main_layout.addWidget(self.search_bar)

        # list widget
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        main_layout.addWidget(self.list_widget)

        # Load saved clipboard history
        self.load_clipboard_history()

        # setup keyboard shortcuts
        self.setup_shortcuts()

        # Monitor clipboard changes
        self.setup_clipboard_monitor()

        # Apply startup setting
        self.apply_startup_setting()

        # Setup system tray
        self.setup_system_tray()

    def load_clipboard_history(self):
        """Load clipboard history from storage."""
        saved_items = self.storage.load_history()
        if saved_items:
            for text in saved_items:
                item = QListWidgetItem(text)
                self.list_widget.addItem(item)
        else:
            # First run - populate with dummy data
            self.populate_dummy_data()

    def save_clipboard_history(self):
        """Save current clipboard history to storage."""
        items = []
        for i in range(self.list_widget.count()):
            items.append(self.list_widget.item(i).text())
        self.storage.max_size = self.max_stack_size
        self.storage.save_history(items)

    def save_settings(self):
        """Save current settings to storage."""
        settings = {
            "swap_hotkey": self.swap_hotkey,
            "type_hotkey": self.type_hotkey,
            "run_at_startup": self.run_at_startup,
            "show_notifications": self.show_notifications,
            "max_stack_size": self.max_stack_size,
        }
        self.storage.save_settings(settings)

    def apply_startup_setting(self):
        """Apply the run-at-startup setting."""
        if self.run_at_startup:
            StartupManager.enable_startup()
        else:
            StartupManager.disable_startup()

    def setup_clipboard_monitor(self):
        """Setup clipboard monitoring to capture new clips."""
        self.clipboard = QGuiApplication.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_changed)

    def on_clipboard_changed(self):
        """Called when clipboard content changes."""
        text = self.clipboard.text()
        if text and text.strip():
            # Check if already exists at top
            if self.list_widget.count() > 0:
                first_item = self.list_widget.item(0)
                if first_item and first_item.text() == text:
                    return  # Already at top, skip

            # Remove duplicate if exists elsewhere
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item and item.text() == text:
                    self.list_widget.takeItem(i)
                    break

            # Add to top of list
            new_item = QListWidgetItem(text)
            self.list_widget.insertItem(0, new_item)

            # Trim to max size
            while self.list_widget.count() > self.max_stack_size:
                self.list_widget.takeItem(self.list_widget.count() - 1)

            # Auto-save
            self.save_clipboard_history()

    def closeEvent(self, event):
        """Called when window close button is clicked - minimize to tray."""
        # Save state before hiding
        self.save_clipboard_history()
        self.save_settings()

        # Hide to tray instead of closing
        event.ignore()
        self.hide()

        # Show tray notification on first minimize
        if self.tray_icon and self.show_notifications:
            self.tray_icon.showMessage(
                "Smart Clip",
                "Application minimized to tray. Right-click tray icon to exit.",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )

    def quit_application(self):
        """Actually quit the application."""
        # Save everything before quitting
        self.save_clipboard_history()
        self.save_settings()

        # Remove tray icon
        if self.tray_icon:
            self.tray_icon.hide()

        # Quit the application
        QApplication.quit()

    def setup_system_tray(self):
        """Setup the system tray icon and menu."""
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)

        # Create a simple icon (clipboard icon)
        icon = self.create_tray_icon()
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Smart Clip - Clipboard Manager")

        # Create context menu
        tray_menu = QMenu()

        # Show/Hide action
        show_action = QAction("Show Smart Clip", self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)

        # Separator
        tray_menu.addSeparator()

        # Settings action
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        tray_menu.addAction(settings_action)

        # Separator
        tray_menu.addSeparator()

        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)

        # Double-click to show window
        self.tray_icon.activated.connect(self.on_tray_activated)

        # Show tray icon
        self.tray_icon.show()

    def create_tray_icon(self):
        """Create tray icon from file or programmatically."""
        # Try to load icon from file
        icon_paths = [
            Path(__file__).parent / "icon.png",  # Same directory as script
            Path(sys.executable).parent / "icon.png",  # Same directory as exe
            Path("icon.png"),  # Current working directory
        ]

        # For frozen executable, also check _MEIPASS
        if getattr(sys, "frozen", False):
            icon_paths.insert(0, Path(sys._MEIPASS) / "icon.png")

        for icon_path in icon_paths:
            if icon_path.exists():
                return QIcon(str(icon_path))

        # Fallback: Create icon programmatically
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("transparent"))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw clipboard shape
        painter.setBrush(QColor("#455A64"))
        painter.setPen(QColor("#455A64"))

        # Clipboard body
        painter.drawRoundedRect(4, 6, 24, 22, 3, 3)

        # Clipboard clip at top
        painter.setBrush(QColor("#37474F"))
        painter.drawRoundedRect(10, 2, 12, 6, 2, 2)

        # Lines on clipboard (representing text)
        painter.setPen(QColor("white"))
        painter.drawLine(8, 14, 24, 14)
        painter.drawLine(8, 18, 20, 18)
        painter.drawLine(8, 22, 22, 22)

        painter.end()

        return QIcon(pixmap)

    def show_window(self):
        """Show and activate the main window."""
        self.show()
        self.raise_()
        self.activateWindow()

    def set_window_icon(self):
        """Set the window icon from file."""
        icon_paths = [
            Path(__file__).parent / "icon.png",
            Path(sys.executable).parent / "icon.png",
            Path("icon.png"),
        ]

        if getattr(sys, "frozen", False):
            icon_paths.insert(0, Path(sys._MEIPASS) / "icon.png")

        for icon_path in icon_paths:
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
                return

    def on_tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single click - also show on Windows
            self.show_window()

    def populate_dummy_data(self):
        # sample data from your image
        items = [
            "redeem.nvidia.com",
            "2012-07-10",
            "INTERVAL '1 month - 1 day'",
            "DATE_TRUNC('month', month + INTERVAL '1 month')",
            "SELECT GENERATE_SERIES(TIMESTAMP '2012-01-01', ...)",
            "'2012-08-31 01:00:00'",
            "'2012-09-02 00:00:00'",
            "TIMESTAMP",
            "select generate_series(timestamp '2012-10-01', ...)",
        ]

        for text in items:
            item = QListWidgetItem(text)
            # icon placeholder code (would need actual file)
            # item.setIcon(QIcon("icon.png"))
            self.list_widget.addItem(item)

    def filter_list(self, text):
        """Filter list items based on search text."""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            # Case-insensitive search
            item.setHidden(text.lower() not in item.text().lower())

    def setup_shortcuts(self):
        """Setup keyboard shortcuts based on current settings."""
        self.update_shortcuts()

    def update_shortcuts(self):
        """Update global hotkeys based on current hotkey settings."""
        # Remove existing hotkeys if they exist
        if self.swap_hook is not None:
            try:
                keyboard.remove_hotkey(self.swap_hook)
            except Exception:
                pass
            self.swap_hook = None

        if self.type_hook is not None:
            try:
                keyboard.remove_hotkey(self.type_hook)
            except Exception:
                pass
            self.type_hook = None

        if self.ctrl_release_hook is not None:
            try:
                keyboard.unhook(self.ctrl_release_hook)
            except Exception:
                pass
            self.ctrl_release_hook = None

        # Create swap hotkey (global)
        if self.swap_hotkey and self.swap_hotkey.lower() != "none":
            # Normalize format for keyboard library (e.g., "Ctrl + G" -> "ctrl+g")
            normalized = self.swap_hotkey.replace(" ", "").lower()

            # Parse modifier and key (e.g., "ctrl+g" -> modifier="ctrl", key="g")
            parts = normalized.split("+")
            if len(parts) >= 2:
                self.swap_modifier = "+".join(
                    parts[:-1]
                )  # e.g., "ctrl" or "ctrl+shift"
                self.swap_key = parts[-1]  # e.g., "g"
            else:
                self.swap_modifier = ""
                self.swap_key = normalized

            self.swap_hook = keyboard.add_hotkey(
                normalized, self.on_swap_hotkey_pressed
            )

        # Create type hotkey (global)
        if self.type_hotkey and self.type_hotkey.lower() != "none":
            normalized = self.type_hotkey.replace(" ", "").lower()
            self.type_hook = keyboard.add_hotkey(
                normalized, self.on_type_hotkey_pressed
            )

    def on_swap_hotkey_pressed(self):
        """Handle swap hotkey - show overlay or cycle to next item."""
        # Use QTimer to safely call from hotkey thread (different thread)
        QTimer.singleShot(0, self.handle_swap_hotkey)

    def handle_swap_hotkey(self):
        """Handle the swap hotkey press."""
        if self.overlay is None or not self.overlay.isVisible():
            # First press - show overlay
            self.show_overlay()
        else:
            # Subsequent press while overlay is open - cycle to next item
            self.cycle_next_item()

    def cycle_next_item(self):
        """Cycle to the next item in the overlay list."""
        if self.overlay and self.overlay.isVisible():
            current_row = self.overlay.list_widget.currentRow()
            next_row = (current_row + 1) % self.overlay.list_widget.count()
            self.overlay.list_widget.setCurrentRow(next_row)

    def show_overlay(self):
        """Show the clipboard overlay."""
        # Close existing overlay if open
        if self.overlay is not None:
            self.overlay.close()
            self.overlay = None

        # Get current clipboard items from main list
        items = []
        for i in range(self.list_widget.count()):
            items.append(self.list_widget.item(i).text())

        # Create and show overlay
        self.overlay = ClipboardOverlay(self, items)
        self.overlay.show()
        self.overlay.activateWindow()
        self.overlay.raise_()

        # Start listening for modifier key release
        self.start_modifier_release_listener()

    def start_modifier_release_listener(self):
        """Start listening for the modifier key (Ctrl) release."""
        # Remove existing hook if any
        if self.ctrl_release_hook is not None:
            try:
                keyboard.unhook(self.ctrl_release_hook)
            except Exception:
                pass

        # Get the primary modifier (first part, e.g., "ctrl" from "ctrl+shift")
        primary_modifier = (
            self.swap_modifier.split("+")[0] if self.swap_modifier else "ctrl"
        )

        # Hook to detect key release
        self.ctrl_release_hook = keyboard.on_release_key(
            primary_modifier, self.on_modifier_released
        )

    def on_modifier_released(self, event):
        """Called when the modifier key is released - paste selected item."""
        QTimer.singleShot(0, self.paste_and_close_overlay)

    def paste_and_close_overlay(self):
        """Paste the selected item and close the overlay."""
        if self.overlay and self.overlay.isVisible():
            current_item = self.overlay.list_widget.currentItem()
            if current_item:
                # Copy to clipboard
                clipboard = QGuiApplication.clipboard()
                clipboard.setText(current_item.text())

                # Close overlay
                self.overlay.close()
                self.overlay = None

                # Remove the release hook
                if self.ctrl_release_hook is not None:
                    try:
                        keyboard.unhook(self.ctrl_release_hook)
                    except Exception:
                        pass
                    self.ctrl_release_hook = None

                # Simulate Ctrl+V to paste (small delay to ensure clipboard is ready)
                QTimer.singleShot(100, self.simulate_paste)

    def simulate_paste(self):
        """Simulate Ctrl+V to paste."""
        keyboard.send("ctrl+v")

    def on_type_hotkey_pressed(self):
        """Handle type hotkey - placeholder for type functionality."""
        # Add your type functionality here
        print("Type hotkey pressed")

    def open_settings(self):
        dlg = SettingsDialog(self)
        # Pre-fill with current settings (format for display: "Ctrl + G")
        display_swap = (
            self.swap_hotkey.replace("+", " + ").title() if self.swap_hotkey else "None"
        )
        display_type = (
            self.type_hotkey.replace("+", " + ").title() if self.type_hotkey else "None"
        )
        dlg.txt_swap.setText(display_swap)
        dlg.txt_type.setText(display_type)
        dlg.chk_startup.setChecked(self.run_at_startup)
        dlg.chk_notify.setChecked(self.show_notifications)
        dlg.spin_size.setValue(self.max_stack_size)

        if dlg.exec():
            # User clicked OK - update hotkey settings
            new_swap = dlg.txt_swap.text().strip()
            new_type = dlg.txt_type.text().strip()

            # Convert to keyboard library format (lowercase, no spaces)
            self.swap_hotkey = (
                new_swap.replace(" ", "").lower() if new_swap.lower() != "none" else ""
            )
            self.type_hotkey = (
                new_type.replace(" ", "").lower() if new_type.lower() != "none" else ""
            )

            # Update other settings
            self.run_at_startup = dlg.chk_startup.isChecked()
            self.show_notifications = dlg.chk_notify.isChecked()
            self.max_stack_size = dlg.spin_size.value()

            # Update the shortcuts with new settings
            self.update_shortcuts()

            # Apply startup setting
            self.apply_startup_setting()

            # Save settings
            self.save_settings()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # set fusion style to look more like standard desktop apps
    app.setStyle("Fusion")

    window = SmartClipUI()
    window.show()

    sys.exit(app.exec())
