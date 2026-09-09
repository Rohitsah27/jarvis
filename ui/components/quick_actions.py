"""
Quick Actions grid component matching the JARVIS dashboard mockup.
Provides one-click execution for frequent tasks and tools.
"""
from typing import List, Tuple
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QLabel,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from ui.styles.theme import theme


class ActionCard(QPushButton):
    """Slick dark card button with icon and label."""

    def __init__(self, icon_str: str, title: str, action_id: str, parent=None):
        super().__init__(parent)
        self.action_id = action_id
        self.setFixedHeight(64)
        self.setCursor(Qt.PointingHandCursor)

        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {theme.BG_CARD};
                border: 1px solid rgba(0, 210, 255, 0.15);
                border-radius: 8px;
                padding: 4px;
            }}
            QPushButton:hover {{
                background-color: {theme.BG_CARD_HOVER};
                border: 1px solid rgba(0, 210, 255, 0.45);
            }}
            QPushButton:pressed {{
                background-color: rgba(0, 210, 255, 0.15);
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        # Icon
        self.lbl_icon = QLabel(icon_str)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setFont(QFont(theme.FONT_FAMILY, 13))
        self.lbl_icon.setStyleSheet("color: #00d2ff; background: transparent; border: none;")

        # Title
        self.lbl_title = QLabel(title)
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setFont(QFont(theme.FONT_FAMILY, 8, QFont.DemiBold))
        self.lbl_title.setStyleSheet("color: #e6f1ff; background: transparent; border: none;")

        layout.addWidget(self.lbl_icon)
        layout.addWidget(self.lbl_title)


class QuickActionsWidget(QFrame):
    """Panel containing the 2x4 Quick Action grid."""

    action_triggered = Signal(str)  # Emits action_id

    ACTIONS: List[Tuple[str, str, str]] = [
        ("💻", "VS Code", "vscode"),
        ("🌐", "Chrome", "chrome"),
        ("📷", "Screenshot", "screenshot"),
        ("📝", "Notepad", "notepad"),
        ("🔍", "Search Files", "search_files"),
        ("🪟", "Control Apps", "control_apps"),
        ("ℹ️", "System Info", "system_info"),
        ("➕", "Custom Action", "custom_action"),
    ]


    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("QuickActionsPanel")
        self.setStyleSheet(
            f"""
            QFrame#QuickActionsPanel {{
                background-color: {theme.BG_PANEL};
                border: 1px solid rgba(0, 210, 255, 0.18);
                border-radius: 12px;
            }}
            """
        )

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(10)

        # Header Row — a flat QPushButton (not a plain label) so the whole
        # row is clickable to collapse/expand, same pattern ActionCard below
        # already uses for a button with a custom child layout.
        self.header_btn = QPushButton()
        self.header_btn.setCursor(Qt.PointingHandCursor)
        self.header_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; text-align: left; }"
            "QPushButton:hover { background: rgba(0, 210, 255, 0.05); border-radius: 6px; }"
        )
        header = QHBoxLayout(self.header_btn)
        header.setContentsMargins(2, 2, 2, 2)
        title_lbl = QLabel("Quick Actions")
        title_lbl.setFont(QFont(theme.FONT_FAMILY, 11, QFont.Bold))
        title_lbl.setStyleSheet("color: #ffffff; background: transparent;")

        self.chevron_lbl = QLabel("›")
        self.chevron_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 14px; background: transparent;")

        header.addWidget(title_lbl)
        header.addStretch(1)
        header.addWidget(self.chevron_lbl)
        main_layout.addWidget(self.header_btn)

        # Grid of cards: 2 rows x 4 columns, wrapped in one widget so the
        # whole grid can be shown/hidden as a unit.
        self.content_widget = QWidget()
        grid = QGridLayout(self.content_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)

        for i, (icon, title, action_id) in enumerate(self.ACTIONS):
            row = i // 4
            col = i % 4
            card = ActionCard(icon, title, action_id, self)
            card.clicked.connect(lambda _, act=action_id: self.action_triggered.emit(act))
            grid.addWidget(card, row, col)

        main_layout.addWidget(self.content_widget)

        # Collapsed by default — click the header to expand.
        self.content_widget.setVisible(False)
        self.header_btn.clicked.connect(self._toggle_collapsed)

    def _toggle_collapsed(self):
        expanded = self.content_widget.isVisible()
        self.content_widget.setVisible(not expanded)
        self.chevron_lbl.setText("⌄" if not expanded else "›")
