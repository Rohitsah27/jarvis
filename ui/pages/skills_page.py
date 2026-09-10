"""Modular AI Skills Directory Page.

Previously claimed "Web Scraping & Synthesis" and "Smart Document Indexer"
were Enabled (green) when no such capability exists anywhere in the
codebase — there is no web-scraping/summarization tool and no semantic
document index (search_files does a plain filename substring match, not
semantic search). "Install / Enable" buttons for the not-yet-built skills
also had no click handler at all. Statuses now reflect what's actually
implemented; unimplemented items are clearly marked and their buttons
disabled rather than pretending a click would do something.
"""
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

        # (name, description, actually implemented today)
        skills = [
            ("🧠 Vision & Screen Analysis", "Analyzes screenshots and monitors using multimodal models (analyze_screen). Requires one-time cloud-upload consent — see Settings > Privacy.", True),
            ("🎙️ Whisper Speech Engine", "High-accuracy local audio transcription via Faster-Whisper.", True),
            ("⌨️ Keyboard & Mouse Macro Recorder", "Record and replay a sequence of clicks/keystrokes as one saved macro.", False),
            ("🌐 Web Scraping & Synthesis", "Extracts structured data and summaries from web pages.", False),
            ("📁 Smart Document Indexer", "Semantic search across PDF, DOCX, and text repositories.", False),
            ("🔐 Credential Vault Manager", "Encrypted local token/API key storage with Windows DPAPI (currently plaintext in config.json).", False),
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

            status_btn = QPushButton("Enabled" if enabled else "Coming Soon")
            if enabled:
                status_btn.setStyleSheet(
                    "background: rgba(0, 255, 157, 0.15); border: 1px solid #00ff9d; "
                    "color: #00ff9d; border-radius: 4px; padding: 4px;"
                )
            else:
                status_btn.setEnabled(False)
                status_btn.setToolTip("Not implemented yet")
                status_btn.setStyleSheet(
                    "background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.15); "
                    "color: #506580; border-radius: 4px; padding: 4px;"
                )

            c_layout.addWidget(t_lbl)
            c_layout.addWidget(d_lbl)
            c_layout.addWidget(status_btn)

            grid.addWidget(card, i // 2, i % 2)

        layout.addLayout(grid)
        layout.addStretch(1)
