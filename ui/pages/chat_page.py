"""
Dedicated Chat Console Page for JARVIS.
Includes full conversation history, model selector, prompt bar, and tool execution feedback.
"""
from typing import Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QFrame,
    QComboBox,
    QLabel,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ui.styles.theme import theme
from ui.components.chat_widget import ChatConsoleWidget
from app.config import config
from core.ai.manager import ai_manager


class ChatPage(QWidget):
    """Full-screen interactive AI conversation interface."""

    prompt_submitted = Signal(str)
    voice_toggle_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 14)
        main_layout.setSpacing(12)

        # Header Bar: Model Selector & Provider Status
        header_frame = QFrame()
        header_frame.setObjectName("ChatHeader")
        header_frame.setFixedHeight(48)
        header_frame.setStyleSheet(
            f"""
            QFrame#ChatHeader {{
                background-color: {theme.BG_PANEL};
                border: 1px solid rgba(0, 210, 255, 0.15);
                border-radius: 10px;
            }}
            """
        )
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(16, 6, 16, 6)
        h_layout.setSpacing(12)

        lbl_title = QLabel("NEURAL CONSOLE")
        lbl_title.setFont(QFont(theme.FONT_DISPLAY, 10, QFont.Bold))
        lbl_title.setStyleSheet(f"color: {theme.CYAN_ACCENT}; letter-spacing: 1.5px;")

        # AI Provider Selector
        lbl_model = QLabel("Model Engine:")
        lbl_model.setFont(QFont(theme.FONT_FAMILY, 9))
        lbl_model.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")

        self.combo_model = QComboBox()
        self.combo_model.addItems(config.AVAILABLE_PROVIDERS)
        self.combo_model.setStyleSheet(
            f"""
            QComboBox {{
                background-color: {theme.BG_CARD};
                color: #ffffff;
                border: 1px solid rgba(0, 210, 255, 0.25);
                border-radius: 6px;
                padding: 4px 10px;
                min-width: 180px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #0d1627;
                color: #ffffff;
                selection-background-color: {theme.CYAN_ACCENT};
                selection-color: #000000;
            }}
            """
        )
        self.combo_model.currentTextChanged.connect(self._on_model_changed)

        h_layout.addWidget(lbl_title)
        h_layout.addStretch(1)
        h_layout.addWidget(lbl_model)
        h_layout.addWidget(self.combo_model)

        main_layout.addWidget(header_frame)

        # Conversation History Panel
        self.chat_console = ChatConsoleWidget(self)
        main_layout.addWidget(self.chat_console, 1)

        # Bottom Input Capsule
        input_frame = QFrame()
        input_frame.setFixedHeight(48)
        input_frame.setStyleSheet(
            f"""
            QFrame {{
                background-color: {theme.BG_INPUT};
                border: 1.5px solid {theme.CYAN_ACCENT};
                border-radius: 24px;
            }}
            """
        )
        in_layout = QHBoxLayout(input_frame)
        in_layout.setContentsMargins(14, 4, 6, 4)
        in_layout.setSpacing(10)

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Command JARVIS or enter question...")
        self.input_edit.setStyleSheet(
            "QLineEdit { background: transparent; border: none; color: #ffffff; font-size: 11pt; padding: 0px; }"
        )
        self.input_edit.returnPressed.connect(self._on_send)

        self.mic_btn = QPushButton("🎙️")
        self.mic_btn.setFixedSize(34, 34)
        self.mic_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: rgba(0, 210, 255, 0.1);
                border: 1px solid rgba(0, 210, 255, 0.3);
                border-radius: 17px;
                color: #8da3c0;
            }}
            QPushButton:hover {{
                background: rgba(0, 210, 255, 0.25);
                color: {theme.CYAN_ACCENT};
            }}
            """
        )
        self.mic_btn.clicked.connect(self.voice_toggle_requested.emit)

        self.send_btn = QPushButton("➔")
        self.send_btn.setObjectName("SendButton")
        self.send_btn.setFixedSize(36, 36)
        self.send_btn.setFont(QFont(theme.FONT_FAMILY, 12, QFont.Bold))
        self.send_btn.setStyleSheet(
            f"""
            QPushButton#SendButton {{
                background-color: {theme.CYAN_ACCENT};
                color: #070e1a;
                border: none;
                border-radius: 18px;
            }}
            QPushButton#SendButton:hover {{
                background-color: #38e1ff;
            }}
            """
        )
        self.send_btn.clicked.connect(self._on_send)

        in_layout.addWidget(self.input_edit, 1)
        in_layout.addWidget(self.mic_btn)
        in_layout.addWidget(self.send_btn)

        main_layout.addWidget(input_frame)

        # Initial Welcome Message
        self.chat_console.add_message(
            "assistant",
            "Good day, sir. All neural channels are connected and ready for your directives."
        )

    def _on_model_changed(self, model_name: str):
        ai_manager.set_provider(model_name)

    def _on_send(self):
        text = self.input_edit.text().strip()
        if text:
            self.chat_console.add_message("user", text)
            self.prompt_submitted.emit(text)
            self.input_edit.clear()

    def receive_ai_message(self, text: str):
        self.chat_console.show_thinking(False)
        self.chat_console.add_message("assistant", text)

    def show_thinking(self, show: bool = True):
        self.chat_console.show_thinking(show)
