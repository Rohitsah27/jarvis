"""
Chat conversation console component with user/JARVIS message bubbles,
typing/thinking indicators, timestamps, and history controls.
"""
from typing import Optional
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QFrame,
    QPushButton,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QColor
from ui.styles.theme import theme


class ChatMessageBubble(QFrame):
    """Futuristic console message bubble."""

    def __init__(self, role: str, text: str, timestamp: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.role = role
        self.timestamp = timestamp or datetime.now().strftime("%H:%M:%S")

        is_user = role.lower() == "user"

        if is_user:
            self.setStyleSheet(
                f"""
                QFrame {{
                    background-color: rgba(0, 210, 255, 0.08);
                    border: 1px solid rgba(0, 210, 255, 0.3);
                    border-radius: 12px;
                }}
                """
            )
        else:
            self.setStyleSheet(
                f"""
                QFrame {{
                    background-color: rgba(14, 23, 38, 0.9);
                    border: 1px solid rgba(0, 210, 255, 0.2);
                    border-left: 3px solid {theme.CYAN_ACCENT};
                    border-radius: 12px;
                }}
                """
            )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        # Header Row: Role & Timestamp
        header = QHBoxLayout()
        header.setSpacing(8)

        role_lbl = QLabel("USER" if is_user else "JARVIS")
        role_font = QFont(theme.FONT_FAMILY, 9, QFont.Bold)
        role_font.setLetterSpacing(QFont.AbsoluteSpacing, 1.0)
        role_lbl.setFont(role_font)
        role_lbl.setStyleSheet(
            f"color: {'#33dcff' if is_user else theme.CYAN_ACCENT}; background: transparent; border: none;"
        )

        time_lbl = QLabel(self.timestamp)
        time_font = QFont(theme.FONT_MONO, 8)
        time_lbl.setFont(time_font)
        time_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; background: transparent; border: none;")

        header.addWidget(role_lbl)
        header.addStretch(1)
        header.addWidget(time_lbl)
        layout.addLayout(header)

        # Content Text
        msg_lbl = QLabel(text)
        msg_lbl.setWordWrap(True)
        msg_font = QFont(theme.FONT_FAMILY, 10)
        msg_lbl.setFont(msg_font)
        msg_lbl.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; background: transparent; border: none; line-height: 1.4;")
        layout.addWidget(msg_lbl)


class ThinkingIndicator(QFrame):
    """Animated dots indicating JARVIS is processing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(38)
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: rgba(14, 23, 38, 0.7);
                border: 1px solid rgba(0, 210, 255, 0.15);
                border-radius: 10px;
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 4, 14, 4)
        layout.setSpacing(8)

        self.lbl_text = QLabel("JARVIS is analyzing request")
        self.lbl_text.setFont(QFont(theme.FONT_FAMILY, 9, QFont.DemiBold))
        self.lbl_text.setStyleSheet(f"color: {theme.CYAN_ACCENT}; background: transparent; border: none;")

        self.lbl_dots = QLabel("...")
        self.lbl_dots.setFont(QFont(theme.FONT_FAMILY, 12, QFont.Bold))
        self.lbl_dots.setStyleSheet("color: #ffffff; background: transparent; border: none;")

        layout.addWidget(self.lbl_text)
        layout.addWidget(self.lbl_dots)
        layout.addStretch(1)

        self._dot_count = 0
        self._timer = QTimer(self)
        self._timer.setInterval(350)
        self._timer.timeout.connect(self._update_dots)

    def start(self):
        self.show()
        self._timer.start()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _update_dots(self):
        self._dot_count = (self._dot_count + 1) % 4
        self.lbl_dots.setText("." * self._dot_count)


class ChatConsoleWidget(QWidget):
    """Full scrollable chat console with message feed and controls."""

    clear_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # Header with Clear button
        header = QHBoxLayout()
        header.setContentsMargins(8, 0, 8, 0)

        title = QLabel("CONVERSATION FEED")
        title.setFont(QFont(theme.FONT_FAMILY, 9, QFont.Bold))
        title.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; letter-spacing: 1px;")

        self.clear_btn = QPushButton("Clear Console")
        self.clear_btn.setFixedHeight(26)
        self.clear_btn.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid rgba(255, 255, 255, 0.15); "
            "color: #8da3c0; font-size: 10px; border-radius: 4px; padding: 2px 10px; }"
            "QPushButton:hover { border-color: #ff4d4d; color: #ff4d4d; }"
        )
        self.clear_btn.clicked.connect(self.clear_messages)

        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.clear_btn)
        main_layout.addLayout(header)

        # Scroll Area for Messages
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.msg_layout = QVBoxLayout(self.container)
        self.msg_layout.setContentsMargins(4, 4, 4, 4)
        self.msg_layout.setSpacing(10)
        self.msg_layout.addStretch(1)

        self.scroll_area.setWidget(self.container)
        main_layout.addWidget(self.scroll_area, 1)

        # Thinking indicator (hidden by default)
        self.thinking_indicator = ThinkingIndicator(self)
        self.thinking_indicator.hide()
        main_layout.addWidget(self.thinking_indicator)

    def add_message(self, role: str, text: str, timestamp: Optional[str] = None):
        bubble = ChatMessageBubble(role, text, timestamp, self)
        # Insert before the stretch at bottom
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, bubble)
        # Auto-scroll to bottom
        QTimer.singleShot(50, self._scroll_to_bottom)

    def show_thinking(self, show: bool = True):
        if show:
            self.thinking_indicator.start()
            QTimer.singleShot(50, self._scroll_to_bottom)
        else:
            self.thinking_indicator.stop()

    def clear_messages(self):
        # Remove all widgets except bottom stretch
        while self.msg_layout.count() > 1:
            item = self.msg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.clear_requested.emit()

    def _scroll_to_bottom(self):
        vbar = self.scroll_area.verticalScrollBar()
        vbar.setValue(vbar.maximum())
