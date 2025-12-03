import sys
import os
import json
import platform
from datetime import datetime
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
    QStyledItemDelegate,
    QStyle,
)
from PyQt6.QtCore import Qt, QTimer, QSize, QRect
from PyQt6.QtGui import (
    QIcon,
    QFont,
    QGuiApplication,
    QAction,
    QPixmap,
    QPainter,
    QColor,
    QFontMetrics,
    QPen,
)
import keyboard  # For global hotkeys


# ============== Custom Delegate for Clipboard Items ==============
class ClipboardItemDelegate(QStyledItemDelegate):
    """Custom delegate for rendering clipboard items with truncation and timestamp."""

    def __init__(self, parent=None, dark_mode=False):
        super().__init__(parent)
        self.padding = 12
        self.item_height = 36  # Reduced height for compact look
        self.dark_mode = dark_mode
        self.time_column_width = 140  # Width for time column

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), self.item_height)

    def paint(self, painter, option, index):
        painter.save()

        # Get the data - can be dict with text and timestamp or just text
        data = index.data(Qt.ItemDataRole.UserRole)
        text = index.data(Qt.ItemDataRole.DisplayRole) or ""

        # Get timestamp if available
        if isinstance(data, dict):
            timestamp = data.get("timestamp", "")
        else:
            timestamp = ""

        if not text:
            painter.restore()
            return

        # Clean up text - replace newlines with spaces for single line display
        display_text = " ".join(text.split())

        # Define colors based on theme
        if self.dark_mode:
            bg_normal = QColor("#2b2b2b")
            bg_hover = QColor("#3a3a3a")
            bg_selected = QColor("#455A64")
            text_color = QColor("#ffffff")
            time_color = QColor("#888888")
            border_color = QColor("#444444")
            icon_color = QColor("#888888")
        else:
            bg_normal = QColor("#ffffff")
            bg_hover = QColor("#f0f7ff")
            bg_selected = QColor("#e3f2fd")
            text_color = QColor("#1a1a1a")
            time_color = QColor("#666666")
            border_color = QColor("#e8e8e8")
            icon_color = QColor("#999999")

        # Determine background color
        if option.state & QStyle.StateFlag.State_Selected:
            bg_color = bg_selected
        elif option.state & QStyle.StateFlag.State_MouseOver:
            bg_color = bg_hover
        else:
            bg_color = bg_normal

        # Draw background
        painter.fillRect(option.rect, bg_color)

        # Draw bottom border for separation
        painter.setPen(QPen(border_color, 1))
        painter.drawLine(
            option.rect.left(),
            option.rect.bottom(),
            option.rect.right(),
            option.rect.bottom(),
        )

        # Draw clipboard icon on the left
        icon_rect = QRect(
            option.rect.left() + 8,
            option.rect.top() + (self.item_height - 16) // 2,
            16,
            16,
        )
        painter.setPen(icon_color)
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, "📋")

        # Calculate text area (leave room for timestamp on right)
        text_rect = QRect(
            option.rect.left() + 32,  # After icon
            option.rect.top(),
            option.rect.width() - 32 - self.time_column_width - self.padding,
            self.item_height,
        )

        # Setup font for text
        font = QFont("Segoe UI", 9)
        painter.setFont(font)
        painter.setPen(text_color)

        # Truncate text with ellipsis
        metrics = QFontMetrics(font)
        elided_text = metrics.elidedText(
            display_text, Qt.TextElideMode.ElideRight, text_rect.width()
        )

        # Draw text
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided_text,
        )

        # Draw timestamp on the right
        if timestamp:
            time_rect = QRect(
                option.rect.right() - self.time_column_width - self.padding,
                option.rect.top(),
                self.time_column_width,
                self.item_height,
            )
            time_font = QFont("Segoe UI", 8)
            painter.setFont(time_font)
            painter.setPen(time_color)
            painter.drawText(
                time_rect,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                timestamp,
            )

        painter.restore()


# ============== Copy Notification Overlay ==============
class CopyNotificationOverlay(QWidget):
    """A small overlay that appears in the bottom-right corner when text is copied."""

    def __init__(self, text, parent=None):
        super().__init__(None)

        # Frameless, always on top, tool window (no taskbar entry)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self.setup_ui(text)
        self.position_on_screen()

        # Auto-close after 2 seconds
        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.close)
        self.close_timer.start(2000)

    def setup_ui(self, text):
        self.setFixedSize(320, 70)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Container with styling
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 6px;
            }
        """)
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(12, 10, 12, 10)
        container_layout.setSpacing(12)

        # Clipboard icon
        icon_label = QLabel("📋")
        icon_label.setStyleSheet(
            "font-size: 24px; background: transparent; border: none;"
        )
        icon_label.setFixedWidth(32)
        container_layout.addWidget(icon_label)

        # Text content
        text_container = QVBoxLayout()
        text_container.setSpacing(2)

        title = QLabel("Copied to clipboard")
        title.setStyleSheet(
            "color: #ffffff; font-weight: bold; font-size: 11px; background: transparent; border: none;"
        )
        text_container.addWidget(title)

        # Preview of copied text (truncated)
        preview_text = text.replace("\n", " ").strip()
        if len(preview_text) > 40:
            preview_text = preview_text[:40] + "..."

        preview = QLabel(preview_text)
        preview.setStyleSheet(
            "color: #aaaaaa; font-size: 10px; background: transparent; border: none;"
        )
        text_container.addWidget(preview)

        container_layout.addLayout(text_container)
        container_layout.addStretch()

        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #888888;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        container_layout.addWidget(close_btn)

        layout.addWidget(container)

    def position_on_screen(self):
        """Position the overlay in the bottom-right corner of the screen."""
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x = screen.right() - self.width() - 20
        y = screen.bottom() - self.height() - 20
        self.move(x, y)


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
                    exe_path = f'"{python_exe}" "{exe_path}" --minimized'
                else:
                    exe_path = f'"{sys.executable}" "{exe_path}" --minimized'
            else:
                exe_path = f'"{exe_path}" --minimized'

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
                exe_path = f"{sys.executable} {exe_path} --minimized"
            else:
                exe_path = f"{exe_path} --minimized"

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
                padding: 0px;
                margin: 0px;
            }
        """)
        # Apply custom delegate for better item rendering (dark mode for overlay)
        self.list_widget.setItemDelegate(
            ClipboardItemDelegate(self.list_widget, dark_mode=True)
        )
        self.list_widget.itemDoubleClicked.connect(self.on_item_selected)
        self.list_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        container_layout.addWidget(self.list_widget)

        # Hint label
        hint = QLabel("Release Ctrl to paste • Keep pressing Q to cycle • Esc to close")
        hint.setStyleSheet("color: #888; padding: 5px; font-size: 11px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(hint)

        layout.addWidget(container)

        # Populate list
        self.populate_list()

    def populate_list(self):
        self.list_widget.clear()
        for item_data in self.clipboard_items:
            # Handle both dict format and plain text
            if isinstance(item_data, dict):
                text = item_data.get("text", "")
                item = QListWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, item_data)
            else:
                item = QListWidgetItem(item_data)
                item.setData(
                    Qt.ItemDataRole.UserRole, {"text": item_data, "timestamp": ""}
                )
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
        self.setFixedSize(400, 400)

        layout = QVBoxLayout()
        layout.setSpacing(15)

        # header
        header = QLabel("SETTINGS")
        header.setStyleSheet(
            "font-weight: bold; color: white; background-color: #455A64; padding: 10px;"
        )
        header.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(header)

        # Theme selection
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme"))
        self.chk_dark_mode = QCheckBox("Dark Mode")
        self.chk_dark_mode.setChecked(False)
        theme_layout.addWidget(self.chk_dark_mode)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)

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
        self.swap_hotkey = saved_settings.get("swap_hotkey", "ctrl+q")
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
        self.swap_key = "q"

        # Overlay window reference
        self.overlay = None

        # Copy notification overlay reference
        self.copy_notification = None

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

        # Load theme setting
        self.dark_mode = saved_settings.get("dark_mode", False)

        # search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search")
        self.search_bar.textChanged.connect(self.filter_list)
        main_layout.addWidget(self.search_bar)

        # Column header row (Text | Time)
        self.header_row = QWidget()
        header_layout = QHBoxLayout(self.header_row)
        header_layout.setContentsMargins(32, 5, 12, 5)
        header_layout.setSpacing(0)

        lbl_text = QLabel("Text")
        lbl_text.setFont(QFont("Segoe UI", 9))

        lbl_time = QLabel("Time")
        lbl_time.setFont(QFont("Segoe UI", 9))
        lbl_time.setFixedWidth(140)
        lbl_time.setAlignment(Qt.AlignmentFlag.AlignRight)

        header_layout.addWidget(lbl_text)
        header_layout.addStretch()
        header_layout.addWidget(lbl_time)
        main_layout.addWidget(self.header_row)

        # list widget
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(False)  # We handle this in delegate
        self.list_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.list_widget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        main_layout.addWidget(self.list_widget)

        # Apply theme
        self.apply_theme()

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
            for item_data in saved_items:
                # Handle both old format (string) and new format (dict)
                if isinstance(item_data, dict):
                    text = item_data.get("text", "")
                    timestamp = item_data.get("timestamp", "")
                else:
                    text = item_data
                    timestamp = ""

                item = QListWidgetItem(text)
                item.setData(
                    Qt.ItemDataRole.UserRole, {"text": text, "timestamp": timestamp}
                )
                self.list_widget.addItem(item)
        else:
            # First run - populate with dummy data
            self.populate_dummy_data()

    def save_clipboard_history(self):
        """Save current clipboard history to storage."""
        items = []
        for i in range(self.list_widget.count()):
            list_item = self.list_widget.item(i)
            data = list_item.data(Qt.ItemDataRole.UserRole)
            if isinstance(data, dict):
                items.append(data)
            else:
                # Old format item, save with empty timestamp
                items.append({"text": list_item.text(), "timestamp": ""})
        self.storage.max_size = self.max_stack_size
        self.storage.save_history(items)

    def apply_theme(self):
        """Apply the current theme (light or dark) to the UI."""
        if self.dark_mode:
            # Dark theme
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #1e1e1e;
                }
            """)
            self.search_bar.setStyleSheet("""
                QLineEdit {
                    padding: 8px 12px;
                    margin: 4px 8px;
                    font-size: 11px;
                    border: 1px solid #444;
                    border-radius: 4px;
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QLineEdit:focus {
                    border-color: #0078d4;
                }
            """)
            self.header_row.setStyleSheet("""
                QWidget {
                    background-color: #2b2b2b;
                    border-bottom: 1px solid #444;
                }
                QLabel {
                    color: #aaaaaa;
                }
            """)
            self.list_widget.setStyleSheet("""
                QListWidget {
                    background-color: #1e1e1e;
                    border: none;
                    outline: none;
                }
                QListWidget::item {
                    padding: 0px;
                    margin: 0px;
                }
            """)
            self.list_widget.setItemDelegate(
                ClipboardItemDelegate(self.list_widget, dark_mode=True)
            )
        else:
            # Light theme
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #ffffff;
                }
            """)
            self.search_bar.setStyleSheet("""
                QLineEdit {
                    padding: 8px 12px;
                    margin: 4px 8px;
                    font-size: 11px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    background-color: #ffffff;
                    color: #1a1a1a;
                }
                QLineEdit:focus {
                    border-color: #0078d4;
                    background-color: #fff;
                }
            """)
            self.header_row.setStyleSheet("""
                QWidget {
                    background-color: #f8f8f8;
                    border-bottom: 1px solid #e0e0e0;
                }
                QLabel {
                    color: #666666;
                }
            """)
            self.list_widget.setStyleSheet("""
                QListWidget {
                    background-color: #ffffff;
                    border: none;
                    outline: none;
                }
                QListWidget::item {
                    padding: 0px;
                    margin: 0px;
                }
            """)
            self.list_widget.setItemDelegate(
                ClipboardItemDelegate(self.list_widget, dark_mode=False)
            )

    def save_settings(self):
        """Save current settings to storage."""
        settings = {
            "swap_hotkey": self.swap_hotkey,
            "type_hotkey": self.type_hotkey,
            "run_at_startup": self.run_at_startup,
            "show_notifications": self.show_notifications,
            "max_stack_size": self.max_stack_size,
            "dark_mode": self.dark_mode,
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

            # Check if exists elsewhere - if so, just move to top (reorder)
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item and item.text() == text:
                    # Take the existing item and reinsert at top (keeps original timestamp)
                    taken_item = self.list_widget.takeItem(i)
                    self.list_widget.insertItem(0, taken_item)
                    self.save_clipboard_history()
                    return  # Done - just reordered, no new copy needed

            # New item - add to top of list with current timestamp
            timestamp = datetime.now().strftime("%d %b  %I:%M:%S %p")
            new_item = QListWidgetItem(text)
            new_item.setData(
                Qt.ItemDataRole.UserRole, {"text": text, "timestamp": timestamp}
            )
            self.list_widget.insertItem(0, new_item)

            # Show copy notification
            self.show_copy_notification(text)

            # Trim to max size
            while self.list_widget.count() > self.max_stack_size:
                self.list_widget.takeItem(self.list_widget.count() - 1)

            # Auto-save
            self.save_clipboard_history()

    def show_copy_notification(self, text):
        """Show a brief overlay notification when something is copied."""
        if self.show_notifications:
            # Close existing notification if any
            if (
                hasattr(self, "copy_notification")
                and self.copy_notification is not None
            ):
                self.copy_notification.close()

            # Show new notification overlay
            self.copy_notification = CopyNotificationOverlay(text)
            self.copy_notification.show()

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
        # sample data with timestamps
        items = [
            {"text": "redeem.nvidia.com", "timestamp": "26 Nov  11:57:44 PM"},
            {"text": "2012-07-10", "timestamp": "26 Nov  11:21:47 PM"},
            {"text": "INTERVAL '1 month - 1 day'", "timestamp": "26 Nov  10:06:20 PM"},
            {
                "text": "DATE_TRUNC('month', month + INTERVAL '1 month - 1 day')",
                "timestamp": "26 Nov  10:04:12 PM",
            },
            {
                "text": "SELECT GENERATE_SERIES(TIMESTAMP '2012-01-01', TIMESTAMP '2012-12-31', INTERVAL '1 month - 1 day') as month) t1",
                "timestamp": "26 Nov  10:02:35 PM",
            },
            {"text": "'2012-08-31 01:00:00'", "timestamp": "26 Nov  07:39:05 PM"},
            {"text": "'2012-09-02 00:00:00'", "timestamp": "26 Nov  07:38:46 PM"},
            {"text": "TIMESTAMP", "timestamp": "26 Nov  07:33:36 PM"},
            {
                "text": "select generate_series(timestamp '2012-10-01', timestamp '2012-10-31', interval '1 day') as ts;",
                "timestamp": "26 Nov  07:33:15 PM",
            },
        ]

        for item_data in items:
            item = QListWidgetItem(item_data["text"])
            item.setData(Qt.ItemDataRole.UserRole, item_data)
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

        # Get current clipboard items from main list (with timestamps)
        items = []
        for i in range(self.list_widget.count()):
            list_item = self.list_widget.item(i)
            data = list_item.data(Qt.ItemDataRole.UserRole)
            if isinstance(data, dict):
                items.append(data)
            else:
                items.append({"text": list_item.text(), "timestamp": ""})

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
        dlg.chk_dark_mode.setChecked(self.dark_mode)

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

            # Update theme if changed
            new_dark_mode = dlg.chk_dark_mode.isChecked()
            if new_dark_mode != self.dark_mode:
                self.dark_mode = new_dark_mode
                self.apply_theme()

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

    # Check if --minimized flag is passed or if run at startup is enabled
    if "--minimized" in sys.argv or window.run_at_startup:
        # Start minimized to tray
        window.hide()
    else:
        window.show()

    sys.exit(app.exec())
