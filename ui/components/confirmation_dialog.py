"""
Real, modal confirmation dialog for CONFIRMATION_REQUIRED / HIGH_RISK tool
calls. This is the UI half of core/tools/confirmation.py's ConfirmationService
— the ENFORCEMENT lives there (a tool cannot execute without a decision);
this dialog is just how that decision gets made by an actual human.

Shown on the GUI thread (constructed and exec()'d from
JarvisMainWindow._on_confirmation_requested, itself connected to
ConfirmationService.confirmation_requested — Qt auto-queues that signal
delivery onto this thread when the request originates on a background
QThread, so this dialog is never created off the GUI thread).
"""
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QTextEdit,
)
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont

from ui.styles.theme import theme
from core.tools.confirmation import ConfirmationRequest

_RISK_COLORS = {
    "HIGH": "#ff4d4d",
    "MEDIUM": "#ffb800",
    "LOW": "#00d2ff",
}


class ToolConfirmationDialog(QDialog):
    """Modal Allow/Deny dialog for a single tool-execution request.

    approved starts False and is ONLY ever set True by the Allow button's
    own click handler — closing the dialog (X, Esc, Alt+F4) or letting the
    timeout fire both leave it False, matching ConfirmationService's own
    fail-closed default.
    """

    def __init__(self, request: ConfirmationRequest, parent=None):
        super().__init__(parent)
        self.request = request
        self.approved = False

        self.setWindowTitle("JARVIS — Confirmation Required")
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setStyleSheet(f"QDialog {{ background-color: {theme.BG_PANEL}; }}")

        risk_color = _RISK_COLORS.get(request.risk_level.upper(), theme.STATUS_WARNING)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)

        header = QHBoxLayout()
        icon = QLabel("⚠")
        icon.setFont(QFont(theme.FONT_FAMILY, 20))
        icon.setStyleSheet(f"color: {risk_color};")
        title = QLabel("JARVIS wants to perform an action")
        title.setFont(QFont(theme.FONT_FAMILY, 13, QFont.Bold))
        title.setStyleSheet("color: #ffffff;")
        header.addWidget(icon)
        header.addWidget(title, 1)

        risk_badge = QLabel(f"{request.risk_level.upper()} RISK")
        risk_badge.setFont(QFont(theme.FONT_MONO, 8, QFont.Bold))
        risk_badge.setStyleSheet(
            f"color: {risk_color}; border: 1px solid {risk_color}; border-radius: 4px; padding: 3px 8px;"
        )
        header.addWidget(risk_badge)
        layout.addLayout(header)

        tool_line = QLabel(f"Tool: {request.tool_name}")
        tool_line.setFont(QFont(theme.FONT_MONO, 9))
        tool_line.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
        layout.addWidget(tool_line)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(f"background-color: rgba(0, 210, 255, 0.15); max-height: 1px;")
        layout.addWidget(divider)

        desc = QTextEdit()
        desc.setReadOnly(True)
        desc.setPlainText(request.action_description or "(no description provided)")
        desc.setFont(QFont(theme.FONT_FAMILY, 10))
        desc.setStyleSheet(
            f"QTextEdit {{ background-color: {theme.BG_INPUT}; color: {theme.TEXT_PRIMARY}; "
            f"border: 1px solid rgba(0, 210, 255, 0.15); border-radius: 6px; padding: 8px; }}"
        )
        desc.setMaximumHeight(120)
        layout.addWidget(desc)

        if request.target:
            target_lbl = QLabel(f"Target: {request.target}")
            target_lbl.setFont(QFont(theme.FONT_FAMILY, 9))
            target_lbl.setWordWrap(True)
            target_lbl.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
            layout.addWidget(target_lbl)

        self.countdown_lbl = QLabel()
        self.countdown_lbl.setFont(QFont(theme.FONT_MONO, 8))
        self.countdown_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        layout.addWidget(self.countdown_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        deny_btn = QPushButton("Deny")
        deny_btn.setFixedHeight(36)
        deny_btn.setStyleSheet(
            "QPushButton { background: rgba(255, 77, 77, 0.12); border: 1px solid #ff4d4d; "
            "border-radius: 6px; color: #ff4d4d; font-weight: 600; }"
            "QPushButton:hover { background: #ff4d4d; color: #000; }"
        )
        deny_btn.clicked.connect(self._on_deny)

        allow_btn = QPushButton("Allow Once")
        allow_btn.setFixedHeight(36)
        allow_btn.setStyleSheet(
            f"QPushButton {{ background: {theme.CYAN_ACCENT}; border: none; border-radius: 6px; "
            f"color: #000; font-weight: 700; }}"
            f"QPushButton:hover {{ background: {theme.CYAN_BRIGHT}; }}"
        )
        allow_btn.clicked.connect(self._on_allow)
        allow_btn.setDefault(False)
        allow_btn.setAutoDefault(False)
        deny_btn.setDefault(True)  # Enter key defaults to the SAFE choice, not the risky one

        btn_row.addWidget(deny_btn, 1)
        btn_row.addWidget(allow_btn, 1)
        layout.addLayout(btn_row)

        # Belt-and-suspenders UI-level timeout mirroring
        # ConfirmationService's own timeout: even if this dialog somehow
        # never closes, ConfirmationService.request() will already have
        # unblocked the caller with a "timeout" denial once
        # request.timeout_seconds elapses. This timer just makes sure a
        # zombie dialog doesn't linger on screen after that has happened —
        # it does NOT do any of the actual security enforcement.
        self._remaining = max(1, int(request.timeout_seconds))
        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._tick)
        self._countdown_timer.start(1000)
        self._tick()

    def _tick(self):
        self._remaining -= 1
        if self._remaining <= 0:
            self.countdown_lbl.setText("Timed out — denying automatically...")
            self._countdown_timer.stop()
            self._on_deny()
            return
        self.countdown_lbl.setText(f"Auto-deny in {self._remaining}s if no response")

    def _on_allow(self):
        self.approved = True
        self._countdown_timer.stop()
        self.accept()

    def _on_deny(self):
        self.approved = False
        self._countdown_timer.stop()
        self.reject()

    def closeEvent(self, event):
        # X button / Alt+F4 — leave approved False (already its default).
        self._countdown_timer.stop()
        super().closeEvent(event)

    def reject(self):
        # Esc key routes here too — leave approved False (already its default).
        self.approved = False
        super().reject()
