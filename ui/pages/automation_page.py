"""Automation Workflows and Macro Scheduler Page."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.styles.theme import theme


class AutomationPage(QWidget):
    """Workflow automation and scheduled routines."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(14)

        head = QLabel("TASK AUTOMATION & SEQUENCES")
        head.setFont(QFont(theme.FONT_DISPLAY, 11, QFont.Bold))
        head.setStyleSheet(f"color: {theme.CYAN_ACCENT}; letter-spacing: 1.5px;")
        layout.addWidget(head)

        workflows = [
            ("🌅 Morning Briefing Sequence", "Fetches weather, checks battery, summarizes notifications.", "Active (08:00 AM)"),
            ("💻 Workspace Initialization", "Opens VS Code, launches terminal, navigates to project repo.", "Manual Trigger"),
            ("🛡️ End-of-Day System Sanitization", "Clears cache, verifies backup, puts system in sleep mode.", "Scheduled (11:30 PM)"),
        ]

        for title, desc, status in workflows:
            card = QFrame()
            card.setStyleSheet(
                f"background-color: {theme.BG_CARD}; border: 1px solid rgba(0, 210, 255, 0.18); border-radius: 12px; padding: 14px;"
            )
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(14, 10, 14, 10)

            info = QVBoxLayout()
            t_lbl = QLabel(title)
            t_lbl.setFont(QFont(theme.FONT_FAMILY, 10, QFont.Bold))
            t_lbl.setStyleSheet("color: #ffffff;")

            d_lbl = QLabel(desc)
            d_lbl.setFont(QFont(theme.FONT_FAMILY, 9))
            d_lbl.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")

            info.addWidget(t_lbl)
            info.addWidget(d_lbl)

            status_lbl = QLabel(status)
            status_lbl.setFont(QFont(theme.FONT_MONO, 8))
            status_lbl.setStyleSheet(f"color: {theme.CYAN_ACCENT}; border: 1px solid rgba(0, 210, 255, 0.3); border-radius: 6px; padding: 4px 8px;")

            run_btn = QPushButton("Run Now")
            run_btn.setStyleSheet(
                f"QPushButton {{ background: rgba(0, 210, 255, 0.15); border: 1px solid {theme.CYAN_ACCENT}; "
                f"border-radius: 6px; color: {theme.CYAN_ACCENT}; padding: 6px 14px; font-weight: bold; }} "
                f"QPushButton:hover {{ background: {theme.CYAN_ACCENT}; color: #000; }}"
            )

            c_layout.addLayout(info, 1)
            c_layout.addWidget(status_lbl)
            c_layout.addWidget(run_btn)

            layout.addWidget(card)

        layout.addStretch(1)
