"""
Computer Control and Security Gate Page.
Displays the permission architecture: AI -> Tool Manager -> Permission Check -> Action,
and provides controls for safe execution.
"""
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QCheckBox,
    QScrollArea,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.styles.theme import theme
from core.tools.tool_manager import tool_manager
from core.tools.permission import permission_manager


class ControlPage(QWidget):
    """Computer Control & Permission Architecture Console."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 16, 24, 16)
        main_layout.setSpacing(16)

        # Header
        lbl_head = QLabel("WINDOWS COMPUTER CONTROL & SECURITY CONSOLE")
        lbl_head.setFont(QFont(theme.FONT_DISPLAY, 11, QFont.Bold))
        lbl_head.setStyleSheet(f"color: {theme.CYAN_ACCENT}; letter-spacing: 1.5px;")
        main_layout.addWidget(lbl_head)

        # Security Architecture Banner
        sec_card = QFrame()
        sec_card.setStyleSheet(
            f"""
            QFrame {{
                background-color: {theme.BG_PANEL};
                border: 1px solid rgba(0, 210, 255, 0.25);
                border-radius: 12px;
            }}
            """
        )
        sec_layout = QVBoxLayout(sec_card)
        sec_layout.setContentsMargins(18, 14, 18, 14)
        sec_layout.setSpacing(8)

        lbl_sec_title = QLabel("🛡️ SECURITY ARCHITECTURE PIPELINE")
        lbl_sec_title.setFont(QFont(theme.FONT_FAMILY, 10, QFont.Bold))
        lbl_sec_title.setStyleSheet("color: #ffffff;")

        lbl_sec_desc = QLabel(
            "Every autonomous computer action flows through a strict verification gate:\n"
            "AI Inference  ➔  Tool Manager  ➔  Permission Gate  ➔  Windows Action Execution\n"
            "High-risk operations (file deletion, terminal execution, system modifications) require user consent."
        )
        lbl_sec_desc.setFont(QFont(theme.FONT_FAMILY, 9))
        lbl_sec_desc.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; line-height: 1.4;")

        # Toggle for requiring confirmation
        self.chk_confirm = QCheckBox("Enforce explicit user confirmation for state-modifying actions")
        self.chk_confirm.setChecked(True)
        self.chk_confirm.setStyleSheet(
            f"""
            QCheckBox {{
                color: #ffffff;
                font-weight: 500;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1.5px solid {theme.CYAN_ACCENT};
                border-radius: 4px;
                background-color: {theme.BG_CARD};
            }}
            QCheckBox::indicator:checked {{
                background-color: {theme.CYAN_ACCENT};
            }}
            """
        )
        self.chk_confirm.toggled.connect(self._on_confirmation_toggled)

        sec_layout.addWidget(lbl_sec_title)
        sec_layout.addWidget(lbl_sec_desc)
        sec_layout.addSpacing(6)
        sec_layout.addWidget(self.chk_confirm)
        main_layout.addWidget(sec_card)

        # Registered Tools List
        lbl_tools_title = QLabel("REGISTERED SYSTEM AUTOMATION TOOLS")
        lbl_tools_title.setFont(QFont(theme.FONT_FAMILY, 9, QFont.Bold))
        lbl_tools_title.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; letter-spacing: 1px;")
        main_layout.addWidget(lbl_tools_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(8)

        for name, tool in tool_manager._tools.items():
            row = QFrame()
            row.setStyleSheet(
                f"background-color: {theme.BG_CARD}; border: 1px solid rgba(0, 210, 255, 0.15); border-radius: 8px;"
            )
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(14, 10, 14, 10)

            t_name = QLabel(f"⚙️ {tool.name}")
            t_name.setFont(QFont(theme.FONT_FAMILY, 9, QFont.Bold))
            t_name.setStyleSheet("color: #ffffff;")

            t_desc = QLabel(tool.description)
            t_desc.setFont(QFont(theme.FONT_FAMILY, 9))
            t_desc.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")

            level_color = theme.STATUS_ONLINE if tool.permission_level.value == "SAFE" else theme.STATUS_WARNING
            t_level = QLabel(tool.permission_level.value)
            t_level.setFont(QFont(theme.FONT_MONO, 8, QFont.Bold))
            t_level.setStyleSheet(
                f"color: {level_color}; border: 1px solid {level_color}; border-radius: 4px; padding: 2px 6px;"
            )

            test_btn = QPushButton("Test Tool")
            test_btn.setFixedHeight(26)
            test_btn.setStyleSheet(
                f"QPushButton {{ background: rgba(0, 210, 255, 0.1); border: 1px solid {theme.CYAN_ACCENT}; "
                f"border-radius: 4px; color: {theme.CYAN_ACCENT}; font-size: 8pt; }} "
                f"QPushButton:hover {{ background: {theme.CYAN_ACCENT}; color: #000000; }}"
            )
            test_btn.clicked.connect(lambda _, tname=tool.name: tool_manager.execute_tool(tname))

            r_layout.addWidget(t_name)
            r_layout.addWidget(t_desc, 1)
            r_layout.addWidget(t_level)
            r_layout.addWidget(test_btn)

            c_layout.addWidget(row)

        c_layout.addStretch(1)
        scroll.setWidget(container)
        main_layout.addWidget(scroll, 1)

    def _on_confirmation_toggled(self, checked: bool):
        permission_manager.require_confirmations = checked
