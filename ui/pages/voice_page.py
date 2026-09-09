"""
Voice Interface Page providing a large-scale audio waveform visualizer,
microphone controls, speech-to-text transcript logs, and voice settings.
"""
import json
import urllib.request
import urllib.error

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QLineEdit,
    QComboBox,
    QSlider,
    QApplication,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.config import config
from ui.styles.theme import theme
from ui.components.waveform_widget import WaveformWidget
from ui.components.hud_frame import HudCornerFrame
from core.voice.voice_engine import VoiceState, voice_engine

_SLIDER_STYLE_TEMPLATE = """
QSlider::groove:horizontal {{
    height: 6px;
    background: rgba(0, 210, 255, 0.15);
    border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    background: {accent};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {accent};
    border: 2px solid #ffffff;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 8px;
}}
"""


class VoicePage(QWidget):
    """Futuristic Voice Command & Audio Spectrum interface."""

    voice_command_emitted = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

        # Connect to voice engine
        voice_engine.state_changed.connect(self._on_voice_state_changed)
        voice_engine.audio_amplitude.connect(self._on_audio_amplitude)
        voice_engine.transcript_ready.connect(self._on_transcript_ready)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(20)

        # Header
        lbl_title = QLabel("NEURAL VOICE INTERFACE")
        lbl_title.setFont(QFont(theme.FONT_DISPLAY, 12, QFont.Bold))
        lbl_title.setStyleSheet(f"color: {theme.CYAN_ACCENT}; letter-spacing: 1.5px;")
        main_layout.addWidget(lbl_title)

        # Main Audio HUD Card
        hud_card = HudCornerFrame()
        hud_card.setObjectName("VoiceHudCard")
        hud_card.setStyleSheet(
            f"""
            QFrame#VoiceHudCard {{
                background-color: {theme.BG_PANEL};
                border: 1px solid rgba(0, 210, 255, 0.25);
                border-radius: 16px;
            }}
            """
        )
        hud_layout = QVBoxLayout(hud_card)
        hud_layout.setContentsMargins(30, 30, 30, 30)
        hud_layout.setSpacing(20)
        hud_layout.setAlignment(Qt.AlignCenter)

        # Status Label
        self.lbl_status = QLabel("MIC READY")
        self.lbl_status.setFont(QFont(theme.FONT_DISPLAY, 16, QFont.Bold))
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet(f"color: {theme.CYAN_ACCENT}; letter-spacing: 2px;")
        hud_layout.addWidget(self.lbl_status)

        # Large Waveform
        self.large_wave = WaveformWidget(bar_count=32, parent=self)
        self.large_wave.setFixedHeight(60)
        hud_layout.addWidget(self.large_wave)

        # Big Circular Mic Button
        self.btn_mic = QPushButton("🎙️")
        self.btn_mic.setFixedSize(72, 72)
        self.btn_mic.setCursor(Qt.PointingHandCursor)
        self.btn_mic.setFont(QFont(theme.FONT_FAMILY, 24))
        self.btn_mic.setStyleSheet(
            f"""
            QPushButton {{
                background: rgba(0, 210, 255, 0.15);
                border: 2px solid {theme.CYAN_ACCENT};
                border-radius: 36px;
                color: #ffffff;
            }}
            QPushButton:hover {{
                background: rgba(0, 210, 255, 0.35);
            }}
            """
        )
        self.btn_mic.clicked.connect(voice_engine.toggle_listening)
        hud_layout.addWidget(self.btn_mic, alignment=Qt.AlignCenter)

        # Subtitle
        self.lbl_hint = QLabel("Click to activate neural acoustic recognition")
        self.lbl_hint.setFont(QFont(theme.FONT_FAMILY, 9))
        self.lbl_hint.setStyleSheet(f"color: {theme.TEXT_SECONDARY};")
        hud_layout.addWidget(self.lbl_hint, alignment=Qt.AlignCenter)

        # Test Voice Button
        self.btn_test_voice = QPushButton("🔊 Test JARVIS Speech")
        self.btn_test_voice.setFixedHeight(34)
        self.btn_test_voice.setCursor(Qt.PointingHandCursor)
        self.btn_test_voice.setStyleSheet(
            f"""
            QPushButton {{
                background: rgba(0, 210, 255, 0.15);
                border: 1px solid {theme.CYAN_ACCENT};
                border-radius: 6px;
                color: {theme.CYAN_ACCENT};
                font-weight: bold;
                padding: 6px 18px;
            }}
            QPushButton:hover {{
                background: {theme.CYAN_ACCENT};
                color: #070e1a;
            }}
            """
        )
        self.btn_test_voice.clicked.connect(
            lambda: voice_engine.speak(
                "सर, जार्विस स्पीच सिंथेसिस पूरी क्षमता से काम कर रहा है। मैं आपकी क्या मदद कर सकता हूँ?"
                if getattr(config, "FORCE_HINDI_ONLY_SPEECH", False)
                else "Good day, sir. JARVIS speech synthesis is operating at full fidelity. How may I assist you?"
            )
        )
        hud_layout.addWidget(self.btn_test_voice, alignment=Qt.AlignCenter)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 8, 0)
        c_layout.setSpacing(16)

        c_layout.addWidget(hud_card)

        # Voice Customization Card — lets you tune how JARVIS sounds and how
        # sensitively it listens, without digging through the general
        # Settings page. Engine/voice/speed apply live on the very next
        # reply; mic sensitivity needs a restart to take effect (the
        # continuous listener only recalibrates once at thread start).
        c_layout.addWidget(self._build_customization_card())

        # Pronunciation & Word Clarity Dictionary Card — manage phonetic
        # word replacements and add custom vocabulary for clean Hindi/Hinglish speech.
        c_layout.addWidget(self._build_dictionary_card())

        # ElevenLabs Cloud Voice Card — paste a key, it's validated against
        # ElevenLabs' own API (also fetching remaining character quota in the
        # same call), and on success becomes JARVIS's active voice
        # immediately. A failed/invalid key never gets saved or switched to.
        c_layout.addWidget(self._build_elevenlabs_card())

        # Bottom: Last Recognized Transcript Box
        transcript_box = QFrame()
        transcript_box.setStyleSheet(
            f"background-color: {theme.BG_CARD}; border: 1px solid rgba(0, 210, 255, 0.15); border-radius: 10px;"
        )
        t_layout = QVBoxLayout(transcript_box)
        t_layout.setContentsMargins(16, 12, 16, 12)
        t_layout.setSpacing(6)

        t_head = QLabel("LATEST TRANSCRIBED SPEECH")
        t_head.setFont(QFont(theme.FONT_FAMILY, 8, QFont.Bold))
        t_head.setStyleSheet(f"color: {theme.CYAN_ACCENT};")

        self.lbl_transcript = QLabel("No speech detected yet. Press the microphone or say a command.")
        self.lbl_transcript.setFont(QFont(theme.FONT_FAMILY, 10))
        self.lbl_transcript.setWordWrap(True)
        self.lbl_transcript.setStyleSheet("color: #ffffff;")

        t_layout.addWidget(t_head)
        t_layout.addWidget(self.lbl_transcript)

        c_layout.addWidget(transcript_box)

        scroll.setWidget(container)
        main_layout.addWidget(scroll, 1)

    def _dropdown_style(self) -> str:
        return (
            f"background: {theme.BG_CARD}; color: #ffffff; "
            f"border: 1px solid rgba(0,210,255,0.3); border-radius: 6px; padding: 6px;"
        )

    def _build_customization_card(self) -> QFrame:
        card = HudCornerFrame()
        card.setObjectName("VoiceCustomCard")
        card.setStyleSheet(
            f"""
            QFrame#VoiceCustomCard {{
                background-color: {theme.BG_PANEL};
                border: 1px solid rgba(0, 210, 255, 0.2);
                border-radius: 12px;
            }}
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        head = QLabel("VOICE CUSTOMIZATION")
        head.setFont(QFont(theme.FONT_FAMILY, 9, QFont.Bold))
        head.setStyleSheet(f"color: {theme.CYAN_ACCENT}; letter-spacing: 1px;")
        layout.addWidget(head)

        slider_qss = _SLIDER_STYLE_TEMPLATE.format(accent=theme.CYAN_ACCENT)

        # --- TTS Engine ---
        row_engine = QHBoxLayout()
        lbl_engine = QLabel("Voice Engine:")
        lbl_engine.setStyleSheet("color: #ffffff;")
        lbl_engine.setFixedWidth(150)
        # XTTS-v2 deliberately excluded here: it's a heavy (~3GB) CPU model
        # documented as "selected explicitly in Settings, not the always-on
        # default" precisely because it's an occasional advanced choice, not
        # a quick-access one. Confirmed via a real crash (Python-uncatchable
        # native segfault, likely PyTorch allocation failure under this
        # machine's memory pressure) that making it this easy to reach here
        # was actually dangerous — it stays reachable from the full Settings
        # page for anyone who wants it deliberately.
        self.combo_engine = QComboBox()
        self.combo_engine.addItem("Kokoro Neural TTS (Free, Offline)", "kokoro")
        self.combo_engine.addItem("Windows Native SAPI (Offline)", "sapi")
        self.combo_engine.addItem("ElevenLabs Studio API (Cloud)", "elevenlabs")
        self.combo_engine.setStyleSheet(self._dropdown_style())
        for i in range(self.combo_engine.count()):
            if self.combo_engine.itemData(i) == getattr(config, "TTS_ENGINE", "kokoro"):
                self.combo_engine.setCurrentIndex(i)
                break
        row_engine.addWidget(lbl_engine)
        row_engine.addWidget(self.combo_engine, 1)
        layout.addLayout(row_engine)

        # --- English Voice ---
        row_en = QHBoxLayout()
        lbl_en = QLabel("English Voice:")
        lbl_en.setStyleSheet("color: #ffffff;")
        lbl_en.setFixedWidth(150)
        self.combo_voice_en = QComboBox()
        self.combo_voice_en.addItem("bm_george — Deep, Authoritative (Recommended)", "bm_george")
        self.combo_voice_en.addItem("bm_daniel — Calm, Polished", "bm_daniel")
        self.combo_voice_en.addItem("bm_fable — Expressive", "bm_fable")
        self.combo_voice_en.addItem("bm_lewis — Classic British Male", "bm_lewis")
        self.combo_voice_en.setStyleSheet(self._dropdown_style())
        for i in range(self.combo_voice_en.count()):
            if self.combo_voice_en.itemData(i) == getattr(config, "KOKORO_ENGLISH_VOICE", "bm_george"):
                self.combo_voice_en.setCurrentIndex(i)
                break
        row_en.addWidget(lbl_en)
        row_en.addWidget(self.combo_voice_en, 1)
        layout.addLayout(row_en)

        # --- Hindi Voice ---
        row_hi = QHBoxLayout()
        lbl_hi = QLabel("Hindi Voice:")
        lbl_hi.setStyleSheet("color: #ffffff;")
        lbl_hi.setFixedWidth(150)
        self.combo_voice_hi = QComboBox()
        self.combo_voice_hi.addItem("hm_omega — Deep Resonant (Recommended)", "hm_omega")
        self.combo_voice_hi.addItem("hm_psi — Calm", "hm_psi")
        self.combo_voice_hi.setStyleSheet(self._dropdown_style())
        for i in range(self.combo_voice_hi.count()):
            if self.combo_voice_hi.itemData(i) == getattr(config, "KOKORO_HINDI_VOICE", "hm_omega"):
                self.combo_voice_hi.setCurrentIndex(i)
                break
        row_hi.addWidget(lbl_hi)
        row_hi.addWidget(self.combo_voice_hi, 1)
        layout.addLayout(row_hi)

        # --- Speech Speed --- (config.KOKORO_SPEED is already read live by
        # kokoro_engine.synthesize() on every call — it just had no UI control
        # anywhere until now, so this applies immediately, no restart needed.)
        row_speed = QHBoxLayout()
        lbl_speed = QLabel("Speech Speed:")
        lbl_speed.setStyleSheet("color: #ffffff;")
        lbl_speed.setFixedWidth(150)
        self.slider_speed = QSlider(Qt.Horizontal)
        self.slider_speed.setMinimum(70)
        self.slider_speed.setMaximum(160)
        self.slider_speed.setValue(int(round(getattr(config, "KOKORO_SPEED", 1.05) * 100)))
        self.slider_speed.setStyleSheet(slider_qss)
        self.lbl_speed_value = QLabel(f"{self.slider_speed.value() / 100:.2f}x")
        self.lbl_speed_value.setStyleSheet(f"color: {theme.CYAN_ACCENT}; font-weight: bold;")
        self.lbl_speed_value.setFixedWidth(45)
        self.slider_speed.valueChanged.connect(
            lambda v: self.lbl_speed_value.setText(f"{v / 100:.2f}x")
        )
        row_speed.addWidget(lbl_speed)
        row_speed.addWidget(self.slider_speed, 1)
        row_speed.addWidget(self.lbl_speed_value)
        layout.addLayout(row_speed)

        # --- Mic Sensitivity --- (needs a restart to take effect — the
        # continuous listener only calibrates once when its thread starts)
        row_mic = QHBoxLayout()
        lbl_mic = QLabel("Mic Sensitivity:")
        lbl_mic.setStyleSheet("color: #ffffff;")
        lbl_mic.setFixedWidth(150)
        self.slider_mic = QSlider(Qt.Horizontal)
        self.slider_mic.setMinimum(30)
        self.slider_mic.setMaximum(250)
        self.slider_mic.setValue(int(getattr(config, "MIC_ENERGY_THRESHOLD", 75)))
        self.slider_mic.setStyleSheet(slider_qss)
        self.lbl_mic_value = QLabel(str(self.slider_mic.value()))
        self.lbl_mic_value.setStyleSheet(f"color: {theme.CYAN_ACCENT}; font-weight: bold;")
        self.lbl_mic_value.setFixedWidth(45)
        self.slider_mic.valueChanged.connect(lambda v: self.lbl_mic_value.setText(str(v)))
        row_mic.addWidget(lbl_mic)
        row_mic.addWidget(self.slider_mic, 1)
        row_mic.addWidget(self.lbl_mic_value)
        layout.addLayout(row_mic)

        lbl_mic_note = QLabel("Lower = more sensitive (picks up softer speech, more ambient noise). Applies after restart.")
        lbl_mic_note.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 8pt;")
        lbl_mic_note.setWordWrap(True)
        layout.addWidget(lbl_mic_note)

        # --- Save & Test row ---
        row_actions = QHBoxLayout()
        self.btn_save_voice = QPushButton("💾 Save & Apply")
        self.btn_save_voice.setFixedHeight(32)
        self.btn_save_voice.setCursor(Qt.PointingHandCursor)
        self.btn_save_voice.setStyleSheet(
            f"background-color: {theme.CYAN_ACCENT}; color: #000; font-weight: bold; "
            f"border-radius: 6px; padding: 4px 16px;"
        )
        self.btn_save_voice.clicked.connect(self._save_voice_customization)

        self.lbl_voice_save_status = QLabel("")
        self.lbl_voice_save_status.setStyleSheet(f"color: {theme.STATUS_ONLINE}; font-size: 8.5pt;")

        row_actions.addWidget(self.btn_save_voice)
        row_actions.addWidget(self.lbl_voice_save_status, 1)
        layout.addLayout(row_actions)

        return card

    def _save_voice_customization(self):
        """Applies every control on this card to the live config immediately
        (engine/voice/speed take effect on JARVIS's very next reply — Kokoro
        params are read fresh on each synth call) and persists them to
        config.json so they survive a restart."""
        config.TTS_ENGINE = self.combo_engine.currentData()
        config.KOKORO_ENGLISH_VOICE = self.combo_voice_en.currentData()
        config.KOKORO_HINDI_VOICE = self.combo_voice_hi.currentData()
        config.KOKORO_SPEED = self.slider_speed.value() / 100.0
        config.MIC_ENERGY_THRESHOLD = self.slider_mic.value()
        config.save_to_json()

        self.lbl_voice_save_status.setText("✓ Saved — engine/voice/speed active now, mic sensitivity after restart.")
        # Immediate audible confirmation using the freshly-applied settings.
        voice_engine.speak(
            "आवाज़ सेटिंग्स अपडेट हो गई हैं। अब मैं ऐसे बोलूंगा।"
            if getattr(config, "FORCE_HINDI_ONLY_SPEECH", False)
            else "Voice settings updated. This is how I sound now."
        )

    def _build_dictionary_card(self) -> QFrame:
        card = HudCornerFrame()
        card.setObjectName("DictionaryCard")
        card.setStyleSheet(
            f"""
            QFrame#DictionaryCard {{
                background-color: {theme.BG_PANEL};
                border: 1px solid rgba(0, 210, 255, 0.2);
                border-radius: 12px;
            }}
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        head = QLabel("PRONUNCIATION & WORD CLARITY DICTIONARY")
        head.setFont(QFont(theme.FONT_FAMILY, 9, QFont.Bold))
        head.setStyleSheet(f"color: {theme.CYAN_ACCENT}; letter-spacing: 1px;")
        layout.addWidget(head)

        from core.voice.pronunciation import get_dictionary_stats
        stats = get_dictionary_stats()
        self.lbl_dict_stats = QLabel(
            f"Active vocabulary: {stats['total_terms']} terms and names mapped to clean Devanagari. "
            "Prevents slurred speech and avoids mid-sentence British voice switches."
        )
        self.lbl_dict_stats.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 8.5pt;")
        self.lbl_dict_stats.setWordWrap(True)
        layout.addWidget(self.lbl_dict_stats)

        # Inputs row: Word (English) + Pronunciation (Devanagari) + Add Button
        row_inputs = QHBoxLayout()
        row_inputs.setSpacing(10)

        self.txt_dict_term = QLineEdit()
        self.txt_dict_term.setPlaceholderText("English Word (e.g. Rohit, WhatsApp, Chrome)")
        self.txt_dict_term.setStyleSheet(self._dropdown_style())

        self.txt_dict_deva = QLineEdit()
        self.txt_dict_deva.setPlaceholderText("Pronounce As (e.g. रोहित, व्हाट्सएप, क्रोम)")
        self.txt_dict_deva.setStyleSheet(self._dropdown_style())
        self.txt_dict_deva.returnPressed.connect(self._on_add_dictionary_word)

        self.btn_add_word = QPushButton("➕ Add Word")
        self.btn_add_word.setCursor(Qt.PointingHandCursor)
        self.btn_add_word.setFixedHeight(34)
        self.btn_add_word.setStyleSheet(
            f"background-color: {theme.CYAN_ACCENT}; color: #000; font-weight: bold; "
            f"border-radius: 6px; padding: 4px 16px;"
        )
        self.btn_add_word.clicked.connect(self._on_add_dictionary_word)

        row_inputs.addWidget(self.txt_dict_term, 2)
        row_inputs.addWidget(self.txt_dict_deva, 2)
        row_inputs.addWidget(self.btn_add_word, 1)
        layout.addLayout(row_inputs)

        # Action & feedback row
        row_feedback = QHBoxLayout()
        self.lbl_dict_feedback = QLabel("")
        self.lbl_dict_feedback.setStyleSheet(f"color: {theme.STATUS_ONLINE}; font-size: 8.5pt;")

        btn_test_clarity = QPushButton("🔊 Test Hindi Speech")
        btn_test_clarity.setCursor(Qt.PointingHandCursor)
        btn_test_clarity.setFixedHeight(28)
        btn_test_clarity.setStyleSheet(
            f"background: rgba(0, 210, 255, 0.15); border: 1px solid {theme.CYAN_ACCENT}; "
            f"border-radius: 5px; color: {theme.CYAN_ACCENT}; font-size: 8.5pt; font-weight: bold; padding: 2px 12px;"
        )
        btn_test_clarity.clicked.connect(
            lambda: voice_engine.speak(
                f"नमस्ते {config.USER_NAME.split()[0] if config.USER_NAME else 'Rohit'}! "
                f"आपका सिस्टम पूरी तरह से तैयार और साफ़ आवाज़ में सक्रिय है।"
            )
        )

        row_feedback.addWidget(self.lbl_dict_feedback, 1)
        row_feedback.addWidget(btn_test_clarity)
        layout.addLayout(row_feedback)

        return card

    def _on_add_dictionary_word(self):
        term = self.txt_dict_term.text().strip()
        deva = self.txt_dict_deva.text().strip()
        if not term or not deva:
            self.lbl_dict_feedback.setStyleSheet(f"color: {theme.RED_ALERT}; font-size: 8.5pt;")
            self.lbl_dict_feedback.setText("Please enter both the English term and its Devanagari pronunciation.")
            return

        from core.voice.pronunciation import add_custom_word, get_dictionary_stats
        ok = add_custom_word(term, deva)
        if ok:
            stats = get_dictionary_stats()
            self.lbl_dict_stats.setText(
                f"Active vocabulary: {stats['total_terms']} terms and names mapped to clean Devanagari. "
                "Prevents slurred speech and avoids mid-sentence British voice switches."
            )
            self.lbl_dict_feedback.setStyleSheet(f"color: {theme.STATUS_ONLINE}; font-size: 8.5pt;")
            self.lbl_dict_feedback.setText(f"✓ Added '{term}' → '{deva}'! Words are now fixed when speaking.")
            self.txt_dict_term.clear()
            self.txt_dict_deva.clear()
            voice_engine.speak(f"शब्द {deva} डिक्शनरी में जोड़ दिया गया है।")
        else:
            self.lbl_dict_feedback.setStyleSheet(f"color: {theme.RED_ALERT}; font-size: 8.5pt;")
            self.lbl_dict_feedback.setText("Could not add word. Please check inputs.")

    def _build_elevenlabs_card(self) -> QFrame:
        card = HudCornerFrame()
        card.setObjectName("ElevenLabsCard")
        card.setStyleSheet(
            f"""
            QFrame#ElevenLabsCard {{
                background-color: {theme.BG_PANEL};
                border: 1px solid rgba(0, 210, 255, 0.2);
                border-radius: 12px;
            }}
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        head = QLabel("ELEVENLABS CLOUD VOICE")
        head.setFont(QFont(theme.FONT_FAMILY, 9, QFont.Bold))
        head.setStyleSheet(f"color: {theme.CYAN_ACCENT}; letter-spacing: 1px;")
        layout.addWidget(head)

        hint = QLabel("Paste your ElevenLabs API key and connect — a valid key becomes JARVIS's active voice immediately.")
        hint.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 8.5pt;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        row_key = QHBoxLayout()
        self.txt_eleven_key = QLineEdit(getattr(config, "ELEVENLABS_API_KEY", ""))
        self.txt_eleven_key.setPlaceholderText("sk_... (from elevenlabs.io/app/settings/api-keys)")
        self.txt_eleven_key.setEchoMode(QLineEdit.Password)
        self.txt_eleven_key.setStyleSheet(self._dropdown_style())
        self.txt_eleven_key.returnPressed.connect(lambda: self._connect_elevenlabs())

        self.btn_eleven_connect = QPushButton("🔗 Connect")
        self.btn_eleven_connect.setCursor(Qt.PointingHandCursor)
        self.btn_eleven_connect.setStyleSheet(
            f"background-color: {theme.CYAN_ACCENT}; color: #000; font-weight: bold; "
            f"border-radius: 6px; padding: 6px 16px;"
        )
        self.btn_eleven_connect.clicked.connect(self._connect_elevenlabs)

        row_key.addWidget(self.txt_eleven_key, 1)
        row_key.addWidget(self.btn_eleven_connect)
        layout.addLayout(row_key)

        self.lbl_eleven_status = QLabel(
            "Not connected." if not getattr(config, "ELEVENLABS_API_KEY", "") else "Key saved — click Connect to verify and check credits."
        )
        self.lbl_eleven_status.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 8.5pt;")
        self.lbl_eleven_status.setWordWrap(True)
        layout.addWidget(self.lbl_eleven_status)

        return card

    @staticmethod
    def _check_elevenlabs_key(api_key: str):
        """Validates the key against ElevenLabs' own API, reads back the
        remaining character quota, AND confirms the account can actually
        synthesize speech right now with a tiny real test call. Found via
        testing: a key can be valid and show full quota on the account-info
        endpoint while ElevenLabs' own anti-abuse system still blocks it from
        generating any real audio ("Unusual activity has been detected...
        Free Tier access has been disabled") — the account check alone can't
        catch that, so without this second call "Connect" would falsely
        report success while every real reply silently fell back to Kokoro.
        Returns (ok, message, remaining_or_None)."""
        try:
            req = urllib.request.Request(
                "https://api.elevenlabs.io/v1/user/subscription",
                headers={"xi-api-key": api_key},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            used = int(data.get("character_count", 0))
            limit = int(data.get("character_limit", 0))
            remaining = max(0, limit - used)
            tier = data.get("tier", "").strip()
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return False, "✗ Invalid API key — ElevenLabs rejected it (401 Unauthorized).", None
            return False, f"✗ ElevenLabs error (HTTP {e.code}).", None
        except Exception as e:
            return False, f"✗ Could not reach ElevenLabs: {e}", None

        try:
            voice_id = getattr(config, "ELEVENLABS_VOICE_ID", "") or "nPczCjzI2devNBz1zQrb"
            model_id = getattr(config, "ELEVENLABS_MODEL_ID", "") or "eleven_multilingual_v2"
            test_req = urllib.request.Request(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                data=json.dumps({
                    "text": "Hi",
                    "model_id": model_id,
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
                }).encode("utf-8"),
                headers={"xi-api-key": api_key, "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(test_req, timeout=10) as resp:
                resp.read()
        except urllib.error.HTTPError as e:
            try:
                detail = json.loads(e.read().decode("utf-8")).get("detail", {})
                reason = detail.get("message") if isinstance(detail, dict) else str(detail)
            except Exception:
                reason = f"HTTP {e.code}"
            return False, f"✗ Key is valid but ElevenLabs blocked real speech generation: {reason}", remaining
        except Exception as e:
            return False, f"✗ Key is valid but a live speech test failed: {e}", remaining

        tier_note = f" ({tier})" if tier else ""
        return True, f"✓ Connected{tier_note} — verified real speech works. {remaining:,} / {limit:,} characters remaining this cycle.", remaining

    def _connect_elevenlabs(self):
        key = self.txt_eleven_key.text().strip()
        if not key:
            self.lbl_eleven_status.setText("⚠ Please paste your ElevenLabs API key first.")
            self.lbl_eleven_status.setStyleSheet(f"color: {theme.STATUS_WARNING}; font-size: 8.5pt;")
            return

        self.btn_eleven_connect.setEnabled(False)
        self.btn_eleven_connect.setText("Connecting...")
        self.lbl_eleven_status.setText("Checking key and credits with ElevenLabs...")
        self.lbl_eleven_status.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 8.5pt;")
        QApplication.processEvents()

        ok, message, _remaining = self._check_elevenlabs_key(key)

        self.btn_eleven_connect.setEnabled(True)
        self.btn_eleven_connect.setText("🔗 Connect")

        if ok:
            # A validated key becomes the active voice right away — this is
            # the whole point of "Connect", not a separate manual step.
            config.ELEVENLABS_API_KEY = key
            config.TTS_ENGINE = "elevenlabs"
            config.save_to_json()

            for i in range(self.combo_engine.count()):
                if self.combo_engine.itemData(i) == "elevenlabs":
                    self.combo_engine.setCurrentIndex(i)
                    break

            self.lbl_eleven_status.setText(message)
            self.lbl_eleven_status.setStyleSheet(f"color: {theme.STATUS_ONLINE}; font-size: 8.5pt; font-weight: bold;")
            voice_engine.speak(
                "सर, ElevenLabs जुड़ गया है। यह मेरी नई आवाज़ है।"
                if getattr(config, "FORCE_HINDI_ONLY_SPEECH", False)
                else "ElevenLabs connected. This is my new voice, Sir."
            )
        else:
            # Never persist or switch to an unverified/invalid key.
            self.lbl_eleven_status.setText(message)
            self.lbl_eleven_status.setStyleSheet(f"color: {theme.STATUS_ERROR}; font-size: 8.5pt;")

    def _on_voice_state_changed(self, state: VoiceState):
        self.lbl_status.setText(state.value)
        if state == VoiceState.LISTENING:
            self.lbl_status.setStyleSheet("color: #00ffea; letter-spacing: 2px;")
            self.lbl_hint.setText("Listening... Speak your command clearly.")
            self.large_wave.set_active(True)
            self.btn_mic.setStyleSheet(
                f"background: {theme.CYAN_ACCENT}; border: 2px solid #ffffff; border-radius: 36px; color: #070e1a;"
            )
        elif state == VoiceState.SPEAKING:
            self.lbl_status.setStyleSheet("color: #38bdf8; letter-spacing: 2px;")
            self.lbl_hint.setText("JARVIS is synthesizing vocal output.")
            self.large_wave.set_active(True)
        elif state == VoiceState.PROCESSING:
            self.lbl_status.setStyleSheet("color: #be5fff; letter-spacing: 2px;")
            self.lbl_hint.setText("Processing acoustic phonemes...")
            self.large_wave.set_active(False)
        else:
            self.lbl_status.setStyleSheet(f"color: {theme.CYAN_ACCENT}; letter-spacing: 2px;")
            self.lbl_hint.setText("Click to activate neural acoustic recognition")
            self.large_wave.set_active(False)
            self.btn_mic.setStyleSheet(
                f"""
                QPushButton {{
                    background: rgba(0, 210, 255, 0.15);
                    border: 2px solid {theme.CYAN_ACCENT};
                    border-radius: 36px;
                    color: #ffffff;
                }}
                QPushButton:hover {{
                    background: rgba(0, 210, 255, 0.35);
                }}
                """
            )

    def _on_audio_amplitude(self, amp: float):
        self.large_wave.set_amplitude(amp)

    def _on_transcript_ready(self, text: str):
        self.lbl_transcript.setText(f'"{text}"')
        self.voice_command_emitted.emit(text)
