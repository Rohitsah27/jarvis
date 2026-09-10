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
from ui.components.tool_runner import run_tool_async


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

        # This used to be a live toggle that could disable confirmation
        # entirely (permission_manager.require_confirmations = checked) —
        # that was itself the security hole: a single UI checkbox could
        # silently turn off human approval for every state-changing tool.
        # Confirmation for CONFIRMATION_REQUIRED/HIGH_RISK tools is now a
        # hard property of each tool's permission tier, enforced inside
        # PermissionManager, and is not something any UI control can
        # disable — so this is shown locked-on rather than removed, to be
        # honest about that being a deliberate, non-negotiable boundary.
        self.chk_confirm = QCheckBox("Explicit user confirmation is enforced for all state-modifying actions (always on)")
        self.chk_confirm.setChecked(True)
        self.chk_confirm.setEnabled(False)
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

            _level_colors = {
                "READ_ONLY": theme.STATUS_ONLINE,
                "LOW_RISK": theme.STATUS_ONLINE,
                "CONFIRMATION_REQUIRED": theme.STATUS_WARNING,
                "HIGH_RISK": theme.STATUS_ERROR,
                "BLOCKED": theme.STATUS_ERROR,
            }
            level_color = _level_colors.get(tool.permission_level.value, theme.STATUS_WARNING)
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
            # A CONFIRMATION_REQUIRED/HIGH_RISK tool tested here now
            # correctly shows a real approval dialog (previously it just
            # executed unconditionally) — off the GUI thread so the window
            # doesn't freeze while that dialog (or the tool itself, e.g.
            # window polling) runs.
            test_btn.clicked.connect(lambda _, tname=tool.name: run_tool_async(self, tname))

            r_layout.addWidget(t_name)
            r_layout.addWidget(t_desc, 1)
            r_layout.addWidget(t_level)
            r_layout.addWidget(test_btn)

            c_layout.addWidget(row)

        c_layout.addStretch(1)
        scroll.setWidget(container)
        main_layout.addWidget(scroll, 1)

