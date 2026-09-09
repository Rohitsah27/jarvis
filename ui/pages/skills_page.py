"""Modular AI Skills Directory Page."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.styles.theme import theme


class SkillsPage(QWidget):
    """Modular AI skills directory for extending JARVIS capabilities."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(14)

        head = QLabel("MODULAR SKILLS & CAPABILITIES")
        head.setFont(QFont(theme.FONT_DISPLAY, 11, QFont.Bold))
        head.setStyleSheet(f"color: {theme.CYAN_ACCENT}; letter-spacing: 1.5px;")
        layout.addWidget(head)

        grid = QGridLayout()
        grid.setSpacing(12)

        skills = [
            ("🧠 Vision & Screen Analysis", "Analyzes screenshots and monitors using multimodal models.", True),
            ("🎙️ Whisper Speech Engine", "High-accuracy local audio transcription and phoneme parsing.", True),
            ("⌨️ Keyboard & Mouse Macro", "Automated input simulation for complex repetitive actions.", False),
            ("🌐 Web Scraping & Synthesis", "Extracts structured data and summaries from web pages.", True),
            ("📁 Smart Document Indexer", "Semantic search across PDF, DOCX, and text repositories.", True),
            ("🔐 Credential Vault Manager", "Secure local token and API key storage with Windows DPAPI.", False),
        ]

        for i, (name, desc, enabled) in enumerate(skills):
            card = QFrame()
            card.setStyleSheet(
                f"background-color: {theme.BG_CARD}; border: 1px solid rgba(0, 210, 255, 0.18); border-radius: 10px; padding: 12px;"
            )
            c_layout = QVBoxLayout(card)
            c_layout.setSpacing(6)

            t_lbl = QLabel(name)
            t_lbl.setFont(QFont(theme.FONT_FAMILY, 10, QFont.Bold))
            t_lbl.setStyleSheet("color: #ffffff;")

            d_lbl = QLabel(desc)
            d_lbl.setFont(QFont(theme.FONT_FAMILY, 9))
            d_lbl.setWordWrap(True)
            d_lbl.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")

            status_btn = QPushButton("Enabled" if enabled else "Install / Enable")
            status_btn.setStyleSheet(
                f"background: {'rgba(0, 255, 157, 0.15)' if enabled else 'rgba(0, 210, 255, 0.1)'}; "
                f"border: 1px solid {'#00ff9d' if enabled else theme.CYAN_ACCENT}; "
                f"color: {'#00ff9d' if enabled else theme.CYAN_ACCENT}; border-radius: 4px; padding: 4px;"
            )

            c_layout.addWidget(t_lbl)
            c_layout.addWidget(d_lbl)
            c_layout.addWidget(status_btn)

            grid.addWidget(card, i // 2, i % 2)

        layout.addLayout(grid)
        layout.addStretch(1)
