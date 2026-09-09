"""Settings and System Configuration Page."""
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QComboBox,
    QCheckBox,
    QScrollArea,
    QProgressBar,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.styles.theme import theme
from app.config import config
from core.ai.manager import ai_manager
from core.voice.voice_engine import VoiceState, voice_engine


class SettingsPage(QWidget):
    """Configuration panel for AI providers, voice engines, and personal settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        voice_engine.audio_amplitude.connect(self._on_voice_amplitude)
        voice_engine.transcript_ready.connect(self._on_voice_transcript)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 16, 24, 16)
        main_layout.setSpacing(14)

        head = QLabel("SYSTEM CONFIGURATION & PREFERENCES")
        head.setFont(QFont(theme.FONT_DISPLAY, 11, QFont.Bold))
        head.setStyleSheet(f"color: {theme.CYAN_ACCENT}; letter-spacing: 1.5px;")
        main_layout.addWidget(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # 1. AI Provider Settings Card
        ai_card = QFrame()
        ai_card.setStyleSheet(
            f"background-color: {theme.BG_PANEL}; border: 1px solid rgba(0, 210, 255, 0.2); border-radius: 12px; padding: 16px;"
        )
        ai_l = QVBoxLayout(ai_card)
        ai_l.setSpacing(10)

        lbl_ai_sec = QLabel("AI PROVIDER & NEURAL ENGINE")
        lbl_ai_sec.setFont(QFont(theme.FONT_FAMILY, 9, QFont.Bold))
        lbl_ai_sec.setStyleSheet(f"color: {theme.CYAN_ACCENT};")
        ai_l.addWidget(lbl_ai_sec)

        # Provider Select
        row_prov = QHBoxLayout()
        lbl_p = QLabel("Default Model:")
        lbl_p.setStyleSheet("color: #ffffff;")
        self.combo_ai = QComboBox()
        self.combo_ai.addItems(config.AVAILABLE_PROVIDERS)
        self.combo_ai.setStyleSheet(
            f"background: {theme.BG_CARD}; color: #ffffff; border: 1px solid rgba(0,210,255,0.3); border-radius: 6px; padding: 6px;"
        )
        row_prov.addWidget(lbl_p)
        row_prov.addWidget(self.combo_ai, 1)
        ai_l.addLayout(row_prov)

        # Groq Cloud API Key (Free Llama 3.3 70B)
        row_groq = QHBoxLayout()
        lbl_groq = QLabel("Groq Cloud API Key (Free):")
        lbl_groq.setStyleSheet("color: #ffffff;")
        self.txt_groq_key = QLineEdit(config.GROQ_API_KEY)
        self.txt_groq_key.setPlaceholderText("gsk_... (Free 300 t/s Llama 3.3 from console.groq.com)")
        self.txt_groq_key.setEchoMode(QLineEdit.Password)
        self.txt_groq_key.setStyleSheet(
            f"background: {theme.BG_CARD}; color: #ffffff; border: 1px solid rgba(0,210,255,0.3); border-radius: 6px; padding: 6px;"
        )
        row_groq.addWidget(lbl_groq)
        row_groq.addWidget(self.txt_groq_key, 1)
        ai_l.addLayout(row_groq)

        # Google Gemini API Key (Free)
        row_gem = QHBoxLayout()
        lbl_gem = QLabel("Google Gemini API Key (Free):")
        lbl_gem.setStyleSheet("color: #ffffff;")
        self.txt_gemini_key = QLineEdit(config.GEMINI_API_KEY)
        self.txt_gemini_key.setPlaceholderText("AIzaSy... (Free key from aistudio.google.com)")
        self.txt_gemini_key.setEchoMode(QLineEdit.Password)
        self.txt_gemini_key.setStyleSheet(
            f"background: {theme.BG_CARD}; color: #ffffff; border: 1px solid rgba(0,210,255,0.3); border-radius: 6px; padding: 6px;"
        )
        row_gem.addWidget(lbl_gem)
        row_gem.addWidget(self.txt_gemini_key, 1)
        ai_l.addLayout(row_gem)

        # OpenAI API Key (GPT-4o)
        row_openai = QHBoxLayout()
        lbl_openai = QLabel("OpenAI API Key (GPT-4o):")
        lbl_openai.setStyleSheet("color: #ffffff;")
        self.txt_openai_key = QLineEdit(config.OPENAI_API_KEY)
        self.txt_openai_key.setPlaceholderText("sk-proj-... (OpenAI GPT-4o / GPT-4o Mini)")
        self.txt_openai_key.setEchoMode(QLineEdit.Password)
        self.txt_openai_key.setStyleSheet(
            f"background: {theme.BG_CARD}; color: #ffffff; border: 1px solid rgba(0,210,255,0.3); border-radius: 6px; padding: 6px;"
        )
        row_openai.addWidget(lbl_openai)
        row_openai.addWidget(self.txt_openai_key, 1)
        ai_l.addLayout(row_openai)

        # Anthropic API Key
        row_key = QHBoxLayout()
        lbl_k = QLabel("Anthropic API Key:")
        lbl_k.setStyleSheet("color: #ffffff;")
        self.txt_key = QLineEdit(config.ANTHROPIC_API_KEY)
        self.txt_key.setPlaceholderText("sk-ant-api03-... (Optional)")
        self.txt_key.setEchoMode(QLineEdit.Password)
        self.txt_key.setStyleSheet(
            f"background: {theme.BG_CARD}; color: #ffffff; border: 1px solid rgba(0,210,255,0.3); border-radius: 6px; padding: 6px;"
        )
        row_key.addWidget(lbl_k)
        row_key.addWidget(self.txt_key, 1)
        ai_l.addLayout(row_key)

        # Open-Source Ollama Settings
        row_ollama = QHBoxLayout()
        lbl_ol = QLabel("Ollama Server URL:")
        lbl_ol.setStyleSheet("color: #ffffff;")
        self.txt_ollama_url = QLineEdit(config.OPENSOURCE_LLM_URL)
        self.txt_ollama_url.setStyleSheet(
            f"background: {theme.BG_CARD}; color: #ffffff; border: 1px solid rgba(0,210,255,0.3); border-radius: 6px; padding: 6px;"
        )
        row_ollama.addWidget(lbl_ol)
        row_ollama.addWidget(self.txt_ollama_url, 1)
        ai_l.addLayout(row_ollama)

        row_ol_model = QHBoxLayout()
        lbl_ol_m = QLabel("Ollama Model:")
        lbl_ol_m.setStyleSheet("color: #ffffff;")
        self.txt_ollama_model = QLineEdit(config.OPENSOURCE_LLM_MODEL)
        self.txt_ollama_model.setPlaceholderText("llama3.2, mistral, qwen2.5, etc.")
        self.txt_ollama_model.setStyleSheet(
            f"background: {theme.BG_CARD}; color: #ffffff; border: 1px solid rgba(0,210,255,0.3); border-radius: 6px; padding: 6px;"
        )
        row_ol_model.addWidget(lbl_ol_m)
        row_ol_model.addWidget(self.txt_ollama_model, 1)
        ai_l.addLayout(row_ol_model)

        # Ollama Test Connection Button & Status
        row_ol_test = QHBoxLayout()
        self.btn_test_ollama = QPushButton("⚡ Test Ollama Connection")
        self.btn_test_ollama.setFixedHeight(30)
        self.btn_test_ollama.setCursor(Qt.PointingHandCursor)
        self.btn_test_ollama.setStyleSheet(
            f"background: rgba(0,210,255,0.15); color: {theme.CYAN_ACCENT}; border: 1px solid {theme.CYAN_ACCENT}; border-radius: 6px; padding: 4px 12px;"
        )
        self.lbl_ollama_status = QLabel("Status: Built-in Neural Engine Active")
        self.lbl_ollama_status.setStyleSheet("color: #38bdf8; font-size: 8.5pt;")
        self.btn_test_ollama.clicked.connect(self._test_ollama_connection)
        row_ol_test.addWidget(self.btn_test_ollama)
        row_ol_test.addWidget(self.lbl_ollama_status, 1)
        ai_l.addLayout(row_ol_test)

        layout.addWidget(ai_card)

        # 2. Text-to-Speech (TTS) & Voice Engines Card
        tts_card = QFrame()
        tts_card.setStyleSheet(
            f"background-color: {theme.BG_PANEL}; border: 1px solid rgba(0, 210, 255, 0.2); border-radius: 12px; padding: 16px;"
        )
        tts_l = QVBoxLayout(tts_card)
        tts_l.setSpacing(10)

        lbl_tts_sec = QLabel("SPEECH SYNTHESIS (TTS) & NEURAL VOICES")
        lbl_tts_sec.setFont(QFont(theme.FONT_FAMILY, 9, QFont.Bold))
        lbl_tts_sec.setStyleSheet(f"color: {theme.CYAN_ACCENT};")
        tts_l.addWidget(lbl_tts_sec)

        # TTS Engine Selector
        row_eng = QHBoxLayout()
        lbl_eng = QLabel("Active Voice Engine:")
        lbl_eng.setStyleSheet("color: #ffffff;")
        self.combo_tts_engine = QComboBox()
        self.combo_tts_engine.addItem("Kokoro Neural TTS (Free, Offline - Classic JARVIS)", "kokoro")
        self.combo_tts_engine.addItem("XTTS-v2 Coqui (High Quality / Voice Cloning - Slower, Offline)", "xtts")
        self.combo_tts_engine.addItem("ElevenLabs Studio API (Cloud / Brian)", "elevenlabs")
        self.combo_tts_engine.addItem("Windows Native SAPI (Offline System / David)", "sapi")
        self.combo_tts_engine.setStyleSheet(
            f"background: {theme.BG_CARD}; color: #ffffff; border: 1px solid rgba(0,210,255,0.3); border-radius: 6px; padding: 6px;"
        )
        # Select current engine
        for i in range(self.combo_tts_engine.count()):
            if self.combo_tts_engine.itemData(i) == getattr(config, "TTS_ENGINE", "kokoro"):
                self.combo_tts_engine.setCurrentIndex(i)
                break
        row_eng.addWidget(lbl_eng)
        row_eng.addWidget(self.combo_tts_engine, 1)
        tts_l.addLayout(row_eng)

        # Kokoro English Voice Selector
        row_en = QHBoxLayout()
        lbl_en = QLabel("English Voice (Kokoro):")
        lbl_en.setStyleSheet("color: #ffffff;")
        self.combo_kokoro_en = QComboBox()
        self.combo_kokoro_en.addItem("Kokoro bm_george (Deep, Authoritative British JARVIS - Recommended)", "bm_george")
        self.combo_kokoro_en.addItem("Kokoro bm_daniel (Calm, Polished British Assistant)", "bm_daniel")
        self.combo_kokoro_en.addItem("Kokoro bm_fable (Expressive British Male)", "bm_fable")
        self.combo_kokoro_en.addItem("Kokoro bm_lewis (Classic British Male)", "bm_lewis")
        self.combo_kokoro_en.setStyleSheet(
            f"background: {theme.BG_CARD}; color: #ffffff; border: 1px solid rgba(0,210,255,0.3); border-radius: 6px; padding: 6px;"
        )
        for i in range(self.combo_kokoro_en.count()):
            if self.combo_kokoro_en.itemData(i) == getattr(config, "KOKORO_ENGLISH_VOICE", "bm_george"):
                self.combo_kokoro_en.setCurrentIndex(i)
                break
        row_en.addWidget(lbl_en)
        row_en.addWidget(self.combo_kokoro_en, 1)
        tts_l.addLayout(row_en)

        # Kokoro Hindi Voice Selector
        row_hi = QHBoxLayout()
        lbl_hi = QLabel("Hindi Voice (Kokoro):")
        lbl_hi.setStyleSheet("color: #ffffff;")
        self.combo_kokoro_hi = QComboBox()
        self.combo_kokoro_hi.addItem("Kokoro hm_omega (Deep Resonant Hindi Male - Recommended)", "hm_omega")
        self.combo_kokoro_hi.addItem("Kokoro hm_psi (Calm Hindi Male)", "hm_psi")
        self.combo_kokoro_hi.setStyleSheet(
            f"background: {theme.BG_CARD}; color: #ffffff; border: 1px solid rgba(0,210,255,0.3); border-radius: 6px; padding: 6px;"
        )
        for i in range(self.combo_kokoro_hi.count()):
            if self.combo_kokoro_hi.itemData(i) == getattr(config, "KOKORO_HINDI_VOICE", "hm_omega"):
                self.combo_kokoro_hi.setCurrentIndex(i)
                break
        row_hi.addWidget(lbl_hi)
        row_hi.addWidget(self.combo_kokoro_hi, 1)
        tts_l.addLayout(row_hi)

        # Language Routing Info Badge
        lbl_route = QLabel("🌐 Auto Language Routing: English text vocalizes with George • Hindi text vocalizes with Omega")
        lbl_route.setStyleSheet("color: #38bdf8; font-size: 8.5pt; padding: 4px 8px; background: rgba(0,210,255,0.08); border-radius: 6px;")
        tts_l.addWidget(lbl_route)

        # ElevenLabs Key & Status (Preserved)
        row_eleven = QHBoxLayout()
        lbl_el_k = QLabel("ElevenLabs API Key:")
        lbl_el_k.setStyleSheet("color: #94a3b8;")
        self.txt_eleven_key = QLineEdit(getattr(config, "ELEVENLABS_API_KEY", ""))
        self.txt_eleven_key.setEchoMode(QLineEdit.Password)
        self.txt_eleven_key.setStyleSheet(
            f"background: {theme.BG_CARD}; color: #94a3b8; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 6px;"
        )
        row_eleven.addWidget(lbl_el_k)
        row_eleven.addWidget(self.txt_eleven_key, 1)
        tts_l.addLayout(row_eleven)

        lbl_el_status = QLabel("☁ ElevenLabs Status: Preserved. If API quota is reached (401), JARVIS auto-falls back to Kokoro.")
        lbl_el_status.setStyleSheet("color: #a78bfa; font-size: 8pt; margin-bottom: 4px;")
        tts_l.addWidget(lbl_el_status)

        # Audition / Test Voice Buttons
        row_audition = QHBoxLayout()
        self.btn_audition_en = QPushButton("▶ Audition English Voice")
        self.btn_audition_en.setFixedHeight(30)
        self.btn_audition_en.setCursor(Qt.PointingHandCursor)
        self.btn_audition_en.setStyleSheet(
            f"background: rgba(0,210,255,0.15); color: {theme.CYAN_ACCENT}; border: 1px solid {theme.CYAN_ACCENT}; border-radius: 6px; padding: 4px 12px; font-weight: bold;"
        )
        self.btn_audition_en.clicked.connect(self._audition_english)

        self.btn_audition_hi = QPushButton("▶ Audition Hindi Voice")
        self.btn_audition_hi.setFixedHeight(30)
        self.btn_audition_hi.setCursor(Qt.PointingHandCursor)
        self.btn_audition_hi.setStyleSheet(
            f"background: rgba(168,85,247,0.15); color: #c084fc; border: 1px solid #c084fc; border-radius: 6px; padding: 4px 12px; font-weight: bold;"
        )
        self.btn_audition_hi.clicked.connect(self._audition_hindi)

        row_audition.addWidget(self.btn_audition_en)
        row_audition.addWidget(self.btn_audition_hi)
        row_audition.addStretch(1)
        tts_l.addLayout(row_audition)

        layout.addWidget(tts_card)

        # 3. Voice & Microphone Sensitivity Card
        voice_card = QFrame()
        voice_card.setStyleSheet(
            f"background-color: {theme.BG_PANEL}; border: 1px solid rgba(0, 210, 255, 0.2); border-radius: 12px; padding: 16px;"
        )
        v_l = QVBoxLayout(voice_card)
        v_l.setSpacing(10)

        lbl_v_sec = QLabel("MICROPHONE & NOISE FILTERING")
        lbl_v_sec.setFont(QFont(theme.FONT_FAMILY, 9, QFont.Bold))
        lbl_v_sec.setStyleSheet(f"color: {theme.CYAN_ACCENT};")
        v_l.addWidget(lbl_v_sec)

        # Microphone Device Selector
        from core.voice.voice_engine import get_available_microphones, voice_engine
        row_mic_dev = QHBoxLayout()
        lbl_mdev = QLabel("Active Microphone:")
        lbl_mdev.setStyleSheet("color: #ffffff;")
        self.combo_mics = QComboBox()
        self.combo_mics.setStyleSheet(
            f"background: {theme.BG_CARD}; color: #ffffff; border: 1px solid rgba(0,210,255,0.3); border-radius: 6px; padding: 6px;"
        )
        mics = get_available_microphones()
        for idx, name in mics:
            self.combo_mics.addItem(name, idx)
        
        # Select current device if matches
        for i in range(self.combo_mics.count()):
            if self.combo_mics.itemData(i) == config.MIC_DEVICE_INDEX:
                self.combo_mics.setCurrentIndex(i)
                break

        row_mic_dev.addWidget(lbl_mdev)
        row_mic_dev.addWidget(self.combo_mics, 1)
        v_l.addLayout(row_mic_dev)

        row_thresh = QHBoxLayout()
        lbl_th = QLabel("Voice Sensitivity / Noise Gate:")
        lbl_th.setStyleSheet("color: #ffffff;")
        self.combo_noise = QComboBox()
        self.combo_noise.addItems([
            "Normal / Dynamic (Calibrated for Speech & Earbuds - Recommended)",
            "High Sensitivity (Quiet room / Soft Voice)",
            "Aggressive Filter (Loud Room / Heavy Fan)"
        ])
        self.combo_noise.setStyleSheet(
            f"background: {theme.BG_CARD}; color: #ffffff; border: 1px solid rgba(0,210,255,0.3); border-radius: 6px; padding: 6px;"
        )
        row_thresh.addWidget(lbl_th)
        row_thresh.addWidget(self.combo_noise, 1)
        v_l.addLayout(row_thresh)

        layout.addWidget(voice_card)

        # 3. User Profile Card
        user_card = QFrame()
        user_card.setStyleSheet(
            f"background-color: {theme.BG_PANEL}; border: 1px solid rgba(0, 210, 255, 0.2); border-radius: 12px; padding: 16px;"
        )
        u_l = QVBoxLayout(user_card)
        u_l.setSpacing(10)

        lbl_u_sec = QLabel("USER PROFILE & IDENTITY")
        lbl_u_sec.setFont(QFont(theme.FONT_FAMILY, 9, QFont.Bold))
        lbl_u_sec.setStyleSheet(f"color: {theme.CYAN_ACCENT};")
        u_l.addWidget(lbl_u_sec)

        row_u = QHBoxLayout()
        lbl_un = QLabel("User Display Name:")
        lbl_un.setStyleSheet("color: #ffffff;")
        self.txt_name = QLineEdit(config.USER_NAME)
        row_u.addWidget(lbl_un)
        row_u.addWidget(self.txt_name, 1)
        u_l.addLayout(row_u)

        row_loc = QHBoxLayout()
        lbl_loc = QLabel("Location / Timezone:")
        lbl_loc.setStyleSheet("color: #ffffff;")
        self.txt_loc = QLineEdit(config.USER_LOCATION)
        row_loc.addWidget(lbl_loc)
        row_loc.addWidget(self.txt_loc, 1)
        u_l.addLayout(row_loc)

        layout.addWidget(user_card)

        # Save Button & Confirmation Status
        save_btn = QPushButton("Save Preferences")
        save_btn.setFixedHeight(38)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet(
            f"background-color: {theme.CYAN_ACCENT}; color: #000; font-weight: bold; border-radius: 8px; font-size: 10pt;"
        )
        self.lbl_save_status = QLabel("")
        self.lbl_save_status.setAlignment(Qt.AlignCenter)
        self.lbl_save_status.setStyleSheet("color: #00ffea; font-size: 9pt;")
        save_btn.clicked.connect(self._save_preferences)
        layout.addWidget(save_btn)
        layout.addWidget(self.lbl_save_status)

        layout.addStretch(1)
        scroll.setWidget(container)
        main_layout.addWidget(scroll, 1)

    def _test_ollama_connection(self):
        url = self.txt_ollama_url.text().strip().rstrip("/")
        try:
            import urllib.request
            req = urllib.request.Request(f"{url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    self.lbl_ollama_status.setText("Status: Online! Connected to Ollama")
                    self.lbl_ollama_status.setStyleSheet("color: #22c55e; font-weight: bold;")
                    return
        except Exception:
            pass
        self.lbl_ollama_status.setText("Status: Ollama offline. Smart Neural Engine active.")
        self.lbl_ollama_status.setStyleSheet("color: #38bdf8;")

    def _audition_english(self):
        from core.voice.voice_engine import voice_engine
        config.KOKORO_ENGLISH_VOICE = self.combo_kokoro_en.currentData() or "bm_george"
        voice_engine.speak("Good morning, Sir. All JARVIS systems are fully operational and standing by.")

    def _audition_hindi(self):
        from core.voice.voice_engine import voice_engine
        config.KOKORO_HINDI_VOICE = self.combo_kokoro_hi.currentData() or "hm_omega"
        voice_engine.speak("नमस्ते रोहित सर, मैं जार्विस हूँ। सभी सिस्टम तैयार हैं।")

    def _save_preferences(self):
        config.USER_NAME = self.txt_name.text().strip() or config.USER_NAME
        config.USER_LOCATION = self.txt_loc.text().strip() or config.USER_LOCATION
        config.OPENSOURCE_LLM_URL = self.txt_ollama_url.text().strip()
        config.OPENSOURCE_LLM_MODEL = self.txt_ollama_model.text().strip()
        config.GROQ_API_KEY = self.txt_groq_key.text().strip()
        config.GEMINI_API_KEY = self.txt_gemini_key.text().strip()
        config.OPENAI_API_KEY = self.txt_openai_key.text().strip()
        config.ANTHROPIC_API_KEY = self.txt_key.text().strip()

        # Update active AI provider in manager AND config, so the choice
        # actually survives a restart instead of reverting to whatever
        # config.json already had.
        chosen_provider = self.combo_ai.currentText()
        ai_manager.set_provider(chosen_provider)
        config.DEFAULT_AI_PROVIDER = chosen_provider

        # Update TTS Engine & Kokoro Voices
        config.TTS_ENGINE = self.combo_tts_engine.currentData()
        config.KOKORO_ENGLISH_VOICE = self.combo_kokoro_en.currentData()
        config.KOKORO_HINDI_VOICE = self.combo_kokoro_hi.currentData()
        new_eleven_key = self.txt_eleven_key.text().strip()
        if new_eleven_key:
            config.ELEVENLABS_API_KEY = new_eleven_key

        # Update active microphone device
        selected_dev = self.combo_mics.currentData()
        config.MIC_DEVICE_INDEX = selected_dev
        from core.voice.voice_engine import voice_engine
        voice_engine.set_microphone_device(selected_dev)

        # Update noise gate
        noise_choice = self.combo_noise.currentIndex()
        if noise_choice == 0:
            config.MIC_ENERGY_THRESHOLD = 75    # Calibrated Normal / Dynamic
        elif noise_choice == 1:
            config.MIC_ENERGY_THRESHOLD = 50    # High Sensitivity / Soft Voice
        else:
            config.MIC_ENERGY_THRESHOLD = 160   # Aggressive Filter

        # Every field above must be set on `config` before this call — it's
        # what actually persists to config.json, so anything updated after it
        # silently only lasts until the app restarts.
        config.save_to_json()

        self.lbl_save_status.setText("✓ Preferences, Voice Engine, and Microphone settings saved!")

    def _on_voice_amplitude(self, amp: float):
        pass

    def _on_voice_transcript(self, text: str):
        pass
