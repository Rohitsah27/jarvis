"""Applications Manager and Launcher Page."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from ui.styles.theme import theme
from ui.components.tool_runner import run_tool_async


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
            launch_btn.clicked.connect(lambda _, cmd=app_cmd, btn=launch_btn: self._launch(cmd, btn))

            c_layout.addWidget(lbl_icon)
            c_layout.addWidget(lbl_name)
            c_layout.addWidget(launch_btn)

            grid.addWidget(card, i // 3, i % 3)

        layout.addLayout(grid)

        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 8.5pt;")
        layout.addWidget(self.lbl_status)

        layout.addStretch(1)

    def _launch(self, app_cmd: str, btn: QPushButton):
        # open_application is CONFIRMATION_REQUIRED — this now correctly
        # shows a real approval dialog (previously the click just silently
        # launched with no gate). Running off the GUI thread means the
        # window stays responsive while that dialog is up and while the
        # tool polls for the launched window, instead of the whole app
        # freezing for however long that takes with zero indication
        # anything was happening — and the actual outcome is now shown
        # instead of being discarded.
        btn.setEnabled(False)
        btn.setText("Launching...")
        self.lbl_status.setText(f"Requesting launch: {app_cmd}...")
        self.lbl_status.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 8.5pt;")

        def _on_result(result):
            btn.setEnabled(True)
            btn.setText("Launch Application")
            if result.success:
                self.lbl_status.setText(f"✓ {result.output}")
                self.lbl_status.setStyleSheet(f"color: {theme.STATUS_ONLINE}; font-size: 8.5pt;")
            else:
                self.lbl_status.setText(f"✗ {result.output}")
                self.lbl_status.setStyleSheet(f"color: {theme.STATUS_ERROR}; font-size: 8.5pt;")

        run_tool_async(self, "open_application", on_result=_on_result, app=app_cmd)
