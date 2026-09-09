"""Files and Storage Browser Page."""
import os
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.styles.theme import theme
from core.tools.tool_manager import tool_manager


class FilesPage(QWidget):
    """File indexer and Desktop directory browser."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(14)

        head = QLabel("FILES & FOLDERS NAVIGATOR")
        head.setFont(QFont(theme.FONT_DISPLAY, 11, QFont.Bold))
        head.setStyleSheet(f"color: {theme.CYAN_ACCENT}; letter-spacing: 1.5px;")
        layout.addWidget(head)

        # Search Bar
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search local documents and desktop files...")
        self.search_btn = QPushButton("Search")
        self.search_btn.setStyleSheet(
            f"background-color: {theme.CYAN_ACCENT}; color: #000; font-weight: bold; border-radius: 6px; padding: 6px 16px;"
        )
        self.search_btn.clicked.connect(self._on_search)
        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(self.search_btn)
        layout.addLayout(search_row)

        # File List
        self.file_list = QListWidget()
        self.file_list.setStyleSheet(
            f"""
            QListWidget {{
                background-color: {theme.BG_PANEL};
                border: 1px solid rgba(0, 210, 255, 0.2);
                border-radius: 10px;
                padding: 8px;
                color: #ffffff;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }}
            QListWidget::item:hover {{
                background-color: rgba(0, 210, 255, 0.15);
                border-radius: 6px;
            }}
            """
        )
        layout.addWidget(self.file_list, 1)

        self._populate_desktop_files()

    def _populate_desktop_files(self):
        self.file_list.clear()
        desktop = Path(os.path.expanduser("~")) / "Desktop"
        if desktop.exists():
            for item in list(desktop.iterdir())[:30]:
                icon = "📁 " if item.is_dir() else "📄 "
                self.file_list.addItem(f"{icon}{item.name}")

    def _on_search(self):
        query = self.search_input.text().strip().lower()
        if not query:
            self._populate_desktop_files()
            return

        self.file_list.clear()
        desktop = Path(os.path.expanduser("~")) / "Desktop"
        if desktop.exists():
            for item in desktop.iterdir():
                if query in item.name.lower():
                    icon = "📁 " if item.is_dir() else "📄 "
                    self.file_list.addItem(f"{icon}{item.name}")
