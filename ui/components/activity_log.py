"""
Live Activity & Event Stream panel displaying timestamped operational logs.
"""
from typing import Optional
from datetime import datetime
from collections import deque
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QFrame,
    QPushButton,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor
from ui.styles.theme import theme


class ActivityLogRow(QFrame):
    """Single row in the live activity monitor."""

    TAG_COLORS = {
        "VOICE": theme.CYAN_ACCENT,
        "AI": "#be5fff",
        "TOOL": "#00ff9d",
        "SYS": "#38bdf8",
        "WARN": theme.STATUS_WARNING,
        "SEC": "#ff4d4d",
    }

    def __init__(self, message: str, tag: str = "SYS", timestamp: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)
        self.setStyleSheet("background: transparent; border: none;")

        time_str = timestamp or datetime.now().strftime("%H:%M:%S")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 1, 4, 1)
        layout.setSpacing(8)

        # Timestamp
        lbl_time = QLabel(time_str)
        lbl_time.setFont(QFont(theme.FONT_MONO, 8))
        lbl_time.setStyleSheet(f"color: {theme.TEXT_MUTED}; background: transparent;")

        # Tag badge
        color = self.TAG_COLORS.get(tag, theme.CYAN_ACCENT)
        lbl_tag = QLabel(f"[{tag}]")
        lbl_tag.setFont(QFont(theme.FONT_MONO, 8, QFont.Bold))
        lbl_tag.setStyleSheet(f"color: {color}; background: transparent;")

        # Event Description
        lbl_msg = QLabel(message)
        lbl_msg.setFont(QFont(theme.FONT_FAMILY, 9))
        lbl_msg.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; background: transparent;")

        layout.addWidget(lbl_time)
        layout.addWidget(lbl_tag)
        layout.addWidget(lbl_msg)
        layout.addStretch(1)


class ActivityLogWidget(QFrame):
    """Scrolling Activity Log component."""

    def __init__(self, parent=None, max_entries: int = 100):
        super().__init__(parent)
        self.max_entries = max_entries
        self._rows = deque(maxlen=max_entries)


        self.setObjectName("ActivityLogPanel")
        self.setStyleSheet(
            f"""
            QFrame#ActivityLogPanel {{
                background-color: {theme.BG_PANEL};
                border: 1px solid rgba(0, 210, 255, 0.18);
                border-radius: 12px;
            }}
            """
        )

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 10, 14, 10)
        main_layout.setSpacing(6)

        # Header
        header = QHBoxLayout()
        title = QLabel("SYSTEM ACTIVITY LOG")
        title.setFont(QFont(theme.FONT_FAMILY, 9, QFont.Bold))
        title.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; letter-spacing: 1px; background: transparent;")

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #506580; font-size: 10px; }"
            "QPushButton:hover { color: #ff4d4d; }"
        )
        clear_btn.clicked.connect(self.clear_logs)

        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(clear_btn)
        main_layout.addLayout(header)

        # Scroll Area
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.rows_layout = QVBoxLayout(self.container)
        self.rows_layout.setContentsMargins(2, 2, 2, 2)
        self.rows_layout.setSpacing(2)
        self.rows_layout.addStretch(1)

        self.scroll_area.setWidget(self.container)
        main_layout.addWidget(self.scroll_area, 1)

    def log_event(self, message: str, tag: str = "SYS"):
        row = ActivityLogRow(message, tag, parent=self)
        self._rows.append(row)
        self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def clear_logs(self):
        while self.rows_layout.count() > 1:
            item = self.rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._rows.clear()

    def _scroll_to_bottom(self):
        vbar = self.scroll_area.verticalScrollBar()
        vbar.setValue(vbar.maximum())
