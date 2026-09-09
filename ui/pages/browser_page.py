"""Browser Automation and Web Search Page."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.styles.theme import theme
from core.tools.tool_manager import tool_manager


class BrowserPage(QWidget):
    """Browser controller and web automation interface."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(14)

        head = QLabel("BROWSER AUTOMATION & TELEMETRY")
        head.setFont(QFont(theme.FONT_DISPLAY, 11, QFont.Bold))
        head.setStyleSheet(f"color: {theme.CYAN_ACCENT}; letter-spacing: 1.5px;")
        layout.addWidget(head)

        # Quick Navigation Bar
        nav_card = QFrame()
        nav_card.setStyleSheet(
            f"background-color: {theme.BG_PANEL}; border: 1px solid rgba(0, 210, 255, 0.2); border-radius: 12px; padding: 16px;"
        )
        c_layout = QVBoxLayout(nav_card)
        c_layout.setSpacing(12)

        lbl_desc = QLabel("Command JARVIS to launch browser, navigate URLs, or synthesize web content:")
        lbl_desc.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
        c_layout.addWidget(lbl_desc)

        in_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL or search query (e.g. google.com or 'latest AI developments')...")
        self.btn_go = QPushButton("Open in Browser")
        self.btn_go.setStyleSheet(
            f"background-color: {theme.CYAN_ACCENT}; color: #000; font-weight: bold; border-radius: 6px; padding: 8px 18px;"
        )
        self.btn_go.clicked.connect(self._on_navigate)
        in_row.addWidget(self.url_input, 1)
        in_row.addWidget(self.btn_go)
        c_layout.addLayout(in_row)

        layout.addWidget(nav_card)

        # Browser Tab Controller Card
        tab_frame = QFrame()
        tab_frame.setStyleSheet(
            f"background-color: {theme.BG_CARD}; border: 1px solid rgba(0, 210, 255, 0.2); border-radius: 10px; padding: 14px;"
        )
        t_layout = QVBoxLayout(tab_frame)
        t_layout.setSpacing(10)

        lbl_tab = QLabel("BROWSER TAB CONTROLS (SWITCH & MANAGE TABS)")
        lbl_tab.setFont(QFont(theme.FONT_FAMILY, 9, QFont.Bold))
        lbl_tab.setStyleSheet(f"color: {theme.CYAN_ACCENT};")
        t_layout.addWidget(lbl_tab)

        t_row = QHBoxLayout()
        t_row.setSpacing(10)

        tab_actions = [
            ("⏭️ Next Tab", "next", "Ctrl + Tab"),
            ("⏮️ Prev Tab", "previous", "Ctrl + Shift + Tab"),
            ("➕ New Tab", "new", "Ctrl + T"),
            ("❌ Close Tab", "close", "Ctrl + W"),
            ("🔄 Reopen Tab", "reopen", "Ctrl + Shift + T"),
        ]

        for label, action, shortcut in tab_actions:
            t_btn = QPushButton(f"{label}\n({shortcut})")
            t_btn.setStyleSheet(
                f"QPushButton {{ background: rgba(0, 210, 255, 0.08); border: 1px solid rgba(0, 210, 255, 0.25); "
                f"color: #d0e8ff; border-radius: 6px; padding: 8px; font-weight: 500; text-align: center; }}"
                f"QPushButton:hover {{ background: rgba(0, 210, 255, 0.22); color: #00d2ff; border-color: {theme.CYAN_ACCENT}; }}"
            )
            t_btn.clicked.connect(lambda _, act=action: tool_manager.execute_tool("control_tabs", action=act))
            t_row.addWidget(t_btn)

        t_layout.addLayout(t_row)
        layout.addWidget(tab_frame)

        # Preset Quick Bookmarks
        bookmarks = [
            ("🌐 Google Search", "https://google.com"),
            ("💻 GitHub", "https://github.com"),
            ("🤖 Anthropic Claude", "https://claude.ai"),
            ("📰 Tech News", "https://news.ycombinator.com"),
        ]

        b_frame = QFrame()
        b_frame.setStyleSheet(
            f"background-color: {theme.BG_CARD}; border: 1px solid rgba(0, 210, 255, 0.15); border-radius: 10px; padding: 14px;"
        )
        b_layout = QVBoxLayout(b_frame)
        b_layout.setSpacing(8)

        lbl_bm = QLabel("QUICK ACCESS PORTALS")
        lbl_bm.setFont(QFont(theme.FONT_FAMILY, 9, QFont.Bold))
        lbl_bm.setStyleSheet(f"color: {theme.CYAN_ACCENT};")
        b_layout.addWidget(lbl_bm)

        for title, url in bookmarks:
            btn = QPushButton(f"{title}  ➔  {url}")
            btn.setStyleSheet(
                "QPushButton { text-align: left; background: transparent; border: none; color: #8da3c0; padding: 6px; }"
                "QPushButton:hover { color: #00d2ff; background: rgba(0, 210, 255, 0.08); border-radius: 4px; }"
            )
            btn.clicked.connect(lambda _, u=url: tool_manager.execute_tool("open_browser", url=u))
            b_layout.addWidget(btn)

        layout.addWidget(b_frame)
        layout.addStretch(1)

    def _on_navigate(self):
        text = self.url_input.text().strip()
        if text:
            if "." in text and " " not in text:
                tool_manager.execute_tool("open_browser", url=text)
            else:
                tool_manager.execute_tool("open_browser", query=text)
