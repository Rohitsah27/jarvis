"""Automation Workflows and Macro Scheduler Page.

Previously showed hardcoded fake statuses ("Active (08:00 AM)",
"Scheduled (11:30 PM)") for workflows that don't actually exist, with a
"Run Now" button that had no click handler at all — it looked like a real,
working scheduler and was entirely a mockup. There is no scheduling engine
in this app yet, so this honestly shows these as not-yet-implemented
instead of pretending they run.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.styles.theme import theme


class AutomationPage(QWidget):
    """Workflow automation and scheduled routines — planned, not yet implemented."""

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

        notice = QLabel(
            "There is no scheduling/automation engine in JARVIS yet — the workflows below are "
            "planned, not running. Nothing here executes anything on your system."
        )
        notice.setWordWrap(True)
        notice.setFont(QFont(theme.FONT_FAMILY, 9))
        notice.setStyleSheet(
            f"color: {theme.STATUS_WARNING}; background: rgba(245, 158, 11, 0.1); "
            f"border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 8px; padding: 10px;"
        )
        layout.addWidget(notice)

        workflows = [
            ("🌅 Morning Briefing Sequence", "Fetches weather, checks battery, summarizes notifications."),
            ("💻 Workspace Initialization", "Opens VS Code, launches terminal, navigates to project repo."),
            ("🛡️ End-of-Day System Sanitization", "Clears cache, verifies backup, puts system in sleep mode."),
        ]

        for title, desc in workflows:
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

            status_lbl = QLabel("COMING SOON")
            status_lbl.setFont(QFont(theme.FONT_MONO, 8, QFont.Bold))
            status_lbl.setStyleSheet(
                f"color: {theme.TEXT_MUTED}; border: 1px solid rgba(255,255,255,0.15); border-radius: 6px; padding: 4px 8px;"
            )

            run_btn = QPushButton("Run Now")
            run_btn.setEnabled(False)
            run_btn.setToolTip("Not implemented yet")
            run_btn.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.15); "
                "border-radius: 6px; color: #506580; padding: 6px 14px; font-weight: bold; }"
            )

            c_layout.addLayout(info, 1)
            c_layout.addWidget(status_lbl)
            c_layout.addWidget(run_btn)

            layout.addWidget(card)

        layout.addStretch(1)
