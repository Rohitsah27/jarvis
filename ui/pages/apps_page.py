"""Applications Manager and Launcher Page."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from ui.styles.theme import theme
from core.tools.tool_manager import tool_manager


class AppsPage(QWidget):
    """Application launcher and process controller."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(16)

        head = QLabel("APPLICATIONS & LAUNCHER")
        head.setFont(QFont(theme.FONT_DISPLAY, 11, QFont.Bold))
        head.setStyleSheet(f"color: {theme.CYAN_ACCENT}; letter-spacing: 1.5px;")
        layout.addWidget(head)

        grid = QGridLayout()
        grid.setSpacing(12)

        apps = [
            ("💻", "Visual Studio Code", "code"),
            ("🌐", "Google Chrome", "chrome"),
            ("📝", "Windows Notepad", "notepad"),
            ("🧮", "Calculator", "calc"),
            ("📂", "File Explorer", "explorer"),
            ("⚡", "Command Prompt", "cmd"),
        ]

        for i, (icon, name, app_cmd) in enumerate(apps):
            card = QFrame()
            card.setStyleSheet(
                f"background-color: {theme.BG_CARD}; border: 1px solid rgba(0, 210, 255, 0.2); border-radius: 12px; padding: 12px;"
            )
            c_layout = QVBoxLayout(card)
            c_layout.setSpacing(8)

            lbl_icon = QLabel(icon)
            lbl_icon.setFont(QFont(theme.FONT_FAMILY, 20))
            lbl_icon.setAlignment(Qt.AlignCenter)

            lbl_name = QLabel(name)
            lbl_name.setFont(QFont(theme.FONT_FAMILY, 10, QFont.Bold))
            lbl_name.setAlignment(Qt.AlignCenter)
            lbl_name.setStyleSheet("color: #ffffff;")

            launch_btn = QPushButton("Launch Application")
            launch_btn.setStyleSheet(
                f"QPushButton {{ background: rgba(0, 210, 255, 0.15); border: 1px solid {theme.CYAN_ACCENT}; "
                f"border-radius: 6px; color: {theme.CYAN_ACCENT}; font-size: 9pt; }} "
                f"QPushButton:hover {{ background: {theme.CYAN_ACCENT}; color: #000000; }}"
            )
            launch_btn.clicked.connect(lambda _, cmd=app_cmd: tool_manager.execute_tool("open_application", app=cmd))

            c_layout.addWidget(lbl_icon)
            c_layout.addWidget(lbl_name)
            c_layout.addWidget(launch_btn)

            grid.addWidget(card, i // 3, i % 3)

        layout.addLayout(grid)
        layout.addStretch(1)
