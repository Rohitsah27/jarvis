"""
Futuristic Navigation Sidebar with glow-highlighted page buttons and user profile card.
"""
from typing import List, Tuple
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFrame,
    QButtonGroup,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QPainter, QBrush, QPen, QLinearGradient
from ui.styles.theme import theme
from app.config import config


class SidebarButton(QPushButton):
    """Futuristic navigation item with active indicator and hover styling."""

    def __init__(self, icon_str: str, text: str, page_index: int, parent=None):
        super().__init__(parent)
        self.icon_str = icon_str
        self.label_text = text
        self.page_index = page_index

        self.setCheckable(True)
        self.setFixedHeight(42)
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(12)

        # Icon Label
        self.lbl_icon = QLabel(icon_str)
        self.lbl_icon.setFixedSize(20, 20)
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        font_icon = QFont(theme.FONT_FAMILY, 11)
        self.lbl_icon.setFont(font_icon)
        self.lbl_icon.setStyleSheet("background: transparent; border: none; color: #8da3c0;")

        # Text Label
        self.lbl_text = QLabel(text)
        font_text = QFont(theme.FONT_FAMILY, 10)
        self.lbl_text.setFont(font_text)
        self.lbl_text.setStyleSheet("background: transparent; border: none; color: #8da3c0; font-weight: 500;")

        layout.addWidget(self.lbl_icon)
        layout.addWidget(self.lbl_text)
        layout.addStretch(1)

        self._update_appearance()

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._update_appearance()

    def _update_appearance(self):
        if self.isChecked():
            self.setStyleSheet(
                f"""
                SidebarButton {{
                    background-color: rgba(0, 210, 255, 0.12);
                    border: 1px solid rgba(0, 210, 255, 0.35);
                    border-radius: 10px;
                }}
                """
            )
            self.lbl_icon.setStyleSheet(f"background: transparent; border: none; color: {theme.CYAN_ACCENT};")
            self.lbl_text.setStyleSheet("background: transparent; border: none; color: #ffffff; font-weight: 600;")
        else:
            self.setStyleSheet(
                """
                SidebarButton {
                    background-color: transparent;
                    border: 1px solid transparent;
                    border-radius: 10px;
                }
                SidebarButton:hover {
                    background-color: rgba(255, 255, 255, 0.04);
                    border: 1px solid rgba(0, 210, 255, 0.15);
                }
                """
            )
            self.lbl_icon.setStyleSheet("background: transparent; border: none; color: #8da3c0;")
            self.lbl_text.setStyleSheet("background: transparent; border: none; color: #8da3c0; font-weight: 500;")


class UserProfileWidget(QFrame):
    """User profile badge at the bottom of the sidebar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(54)
        self.setStyleSheet(
            """
            QFrame {
                background-color: rgba(14, 22, 38, 0.7);
                border: 1px solid rgba(0, 210, 255, 0.15);
                border-radius: 12px;
            }
            QFrame:hover {
                border: 1px solid rgba(0, 210, 255, 0.3);
                background-color: rgba(18, 28, 48, 0.85);
            }
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        # Avatar circle with initials
        avatar = QLabel(config.USER_INITIALS)
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFont(QFont(theme.FONT_FAMILY, 10, QFont.Bold))
        avatar.setStyleSheet(
            f"""
            QLabel {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0055ff, stop:1 {theme.CYAN_ACCENT});
                color: #ffffff;
                border-radius: 18px;
                border: 1.5px solid {theme.CYAN_ACCENT};
            }}
            """
        )

        # Name & Tier
        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)
        info_layout.setAlignment(Qt.AlignVCenter)

        name_lbl = QLabel(config.USER_NAME)
        name_lbl.setFont(QFont(theme.FONT_FAMILY, 9, QFont.Bold))
        name_lbl.setStyleSheet("color: #ffffff; background: transparent; border: none;")

        tier_lbl = QLabel(config.USER_TIER)
        tier_lbl.setFont(QFont(theme.FONT_FAMILY, 8))
        tier_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; background: transparent; border: none;")

        info_layout.addWidget(name_lbl)
        info_layout.addWidget(tier_lbl)

        # More menu button
        more_btn = QPushButton("•••")
        more_btn.setFixedSize(24, 24)
        more_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #607b99; font-size: 11px; }"
            "QPushButton:hover { color: #ffffff; }"
        )

        layout.addWidget(avatar)
        layout.addLayout(info_layout)
        layout.addStretch(1)
        layout.addWidget(more_btn)


class JarvisSidebar(QWidget):
    """
    Main Navigation Sidebar containing all main pages:
    Home, Chat, Voice, Computer Control, Applications, Files, Browser, Automation, Skills, Memory, Settings.
    """

    page_changed = Signal(int)

    NAV_ITEMS: List[Tuple[str, str, int]] = [
        ("🏠", "Home", 0),
        ("💬", "Chat", 1),
        ("🎙️", "Voice", 2),
        ("📊", "System", 3),
        ("🖥️", "Computer Control", 4),
        ("⊞", "Applications", 5),
        ("📁", "Files & Folders", 6),
        ("🌐", "Browser", 7),
        ("⚡", "Automation", 8),
        ("✨", "Skills", 9),
        ("🩺", "Health", 10),
        ("⚙️", "Settings", 11),
    ]


    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(210)
        self.setObjectName("Sidebar")
        self.setStyleSheet(f"background-color: {theme.BG_SIDEBAR}; border-right: 1px solid rgba(0, 210, 255, 0.12);")

        self.buttons: List[SidebarButton] = []
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 14)
        main_layout.setSpacing(4)

        for icon_str, text, index in self.NAV_ITEMS:
            btn = SidebarButton(icon_str, text, index, self)
            btn.clicked.connect(lambda _, idx=index: self._on_button_clicked(idx))
            self.btn_group.addButton(btn, index)
            self.buttons.append(btn)
            main_layout.addWidget(btn)

        main_layout.addStretch(1)

        # Bottom user profile
        self.profile_widget = UserProfileWidget(self)
        main_layout.addWidget(self.profile_widget)

        # Set Home active by default
        if self.buttons:
            self.buttons[0].setChecked(True)

    def _on_button_clicked(self, index: int):
        for btn in self.buttons:
            btn._update_appearance()
        self.page_changed.emit(index)

    def select_page(self, index: int):
        if 0 <= index < len(self.buttons):
            self.buttons[index].setChecked(True)
            self._on_button_clicked(index)
