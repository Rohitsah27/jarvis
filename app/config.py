"""
Application configuration and global constants for JARVIS.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Paths
APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
ASSETS_DIR = ROOT_DIR / "assets"
ICONS_DIR = ASSETS_DIR / "icons"


@dataclass
class AppConfig:
    # App identity
    APP_NAME: str = "JARVIS"
    APP_SUBTITLE: str = "PERSONAL AI SYSTEM"
    APP_VERSION: str = "1.0.0"
    
    # User Profile
    USER_NAME: str = "Rohit Kumar"
    USER_INITIALS: str = "RK"
    USER_TIER: str = "JARVIS Pro"
    USER_LOCATION: str = "New Delhi, India"
    
    # Window dimensions
    DEFAULT_WIDTH: int = 1380
    DEFAULT_HEIGHT: int = 880
    MIN_WIDTH: int = 1100
    MIN_HEIGHT: int = 720
    
    # AI Provider Defaults
    DEFAULT_AI_PROVIDER: str = "Groq Cloud (Free LPU / 300 t/s)"
    # Must match core/ai/manager.py's _providers dict keys exactly — the
    # Settings dropdown is populated straight from this tuple. Previously
    # included "Claude Opus 4.8" (fake — backed by the local mock brain, not
    # real Claude) and duplicate/rebranded entries; removed so every option
    # here maps to one distinct, real backend.
    AVAILABLE_PROVIDERS: tuple = (
        "Groq Cloud (Free LPU / 300 t/s)",
        "Google Gemini (2.0 Flash / Live API)",
        "Google Gemini (Flash-Lite / Fast)",
        "OpenAI GPT-4o (Live API)",
        "OpenAI GPT-4o Mini",
        "Claude Live API",
        "Local LLM (Llama 3 / Ollama)",
    )
    OPENSOURCE_LLM_URL: str = "http://localhost:11434"
    OPENSOURCE_LLM_MODEL: str = "llama3.2"
    
    # Voice Settings
    VOICE_ENABLED: bool = True
    ALWAYS_LISTEN: bool = True                        # Automatically listen continuously on launch
    VOICE_CONFIRMATION_BEFORE_EXECUTE: bool = True     # Talk first and confirm command via voice before executing
    SPEAK_RESPONSES: bool = True                      # Vocalize responses through Windows speakers
    MIC_ENERGY_THRESHOLD: int = 75                    # Calibrated speech floor (speech: 80-350+, ambient silence: 0-35)
    MIC_PAUSE_THRESHOLD: float = 0.6                  # Rapid response when user finishes speaking
    MIC_PHRASE_LIMIT: int = 7                         # Prevents long recordings on noise
    MIC_DEVICE_INDEX: Optional[int] = None            # Selected microphone index (None = System Default)
    BARGE_IN_ENABLED: bool = False                    # Allow speaking over JARVIS to interrupt it mid-reply.
                                                        # Off by default: in testing, energy-threshold barge-in
                                                        # false-triggered on nearly every reply (ambient noise/own
                                                        # voice bleed crossed the bar), cutting JARVIS off mid-
                                                        # sentence. The VAD gate added alongside this makes it much
                                                        # more reliable if you want to turn it back on.
    BARGE_IN_ENERGY_MULTIPLIER: float = 1.6           # How much louder than normal speech is required to interrupt
                                                        # (higher = fewer false triggers from JARVIS's own voice
                                                        # bleeding into the mic through speakers, but requires
                                                        # speaking up more to interrupt; headphones avoid this tradeoff)

    # Optional PIN to a specific playback device name (substring match) for
    # JARVIS's own speech, regardless of whatever Windows currently has as
    # default. Leave empty (default/recommended): JARVIS dynamically follows
    # Windows' actual current default device every time it speaks — so it
    # automatically switches between speakers and a Bluetooth headset exactly
    # as Windows does, instead of being stuck on whichever one was hardcoded.
    # Only set this if you specifically want to IGNORE the Windows default
    # and always use one fixed device no matter what.
    PREFERRED_TTS_OUTPUT_DEVICE: str = ""

    # Text-to-Speech Engine Configuration
    TTS_ENGINE: str = "kokoro"                         # Primary: "kokoro" (Free/Local), "xtts" (Coqui XTTS-v2, High Quality/Slower), "elevenlabs" (Cloud), "sapi" (Native)
    KOKORO_ENGLISH_VOICE: str = "bm_george"           # Deep, authoritative British English (Classic JARVIS feel)
    KOKORO_HINDI_VOICE: str = "hm_omega"              # Deep resonant Hindi male
    FORCE_HINDI_ONLY_SPEECH: bool = True              # Speak everything with the Hindi voice — no English-segment voice switching
    KOKORO_SPEED: float = 1.05                        # Clear, natural speech cadence with optimal articulation
    VOICE_LANGUAGE: str = "hi-IN"                     # Speech recognition primary language (Hindi by default)

    # XTTS-v2 (Coqui) High-Quality Voice Mode — opt-in, runs on CPU (slower, ~ElevenLabs-tier naturalness)
    XTTS_SPEAKER_WAV: str = ""                        # Optional path to a reference voice sample (.wav) for cloning
    XTTS_SPEAKER_NAME: str = ""                       # Optional built-in XTTS speaker name; blank = use first available

    # ElevenLabs Neural Voice API (Preserved for Cloud Switching)
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = "nPczCjzI2devNBz1zQrb"  # Brian - Deep, Resonant & Natural
    ELEVENLABS_MODEL_ID: str = "eleven_multilingual_v2"
    
    # Windows SAPI Fallback Settings
    SAPI_VOICE_RATE: int = 1                          # Voice speed cadence (-10 to 10)
    SAPI_VOICE_VOLUME: int = 100                      # Volume (0 to 100)
    DEFAULT_VOICE_MODEL: str = "Kokoro Neural TTS (bm_george / hm_omega)"

    
    # LLM Cloud API Keys
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Computer Control Settings
    COMPUTER_CONTROL_ACTIVE: bool = True
    REQUIRE_CONFIRMATION_FOR_ACTIONS: bool = False

    # Runtime testing/debug mode: logs every pipeline stage (mic start, STT
    # result, agent intent, tool chosen, tool success/error, TTS start, total
    # latency) to console + logs/jarvis_debug.log. Costs ~nothing when off,
    # negligible disk when on (log file capped at ~1MB).
    DEBUG_PIPELINE_LOGGING: bool = True

    # Timers & Intervals (ms)
    SYSTEM_POLL_INTERVAL_MS: int = 1500
    ORB_ANIMATION_INTERVAL_MS: int = 33  # ~30-33 FPS
    CLOCK_UPDATE_INTERVAL_MS: int = 1000
    WAVEFORM_INTERVAL_MS: int = 40

    def load_from_json(self):
        json_path = ROOT_DIR / "config.json"
        if json_path.exists():
            try:
                import json
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for k, v in data.items():
                    # v is checked against None rather than truthiness — a
                    # falsy-but-meaningful saved value (mic device index 0,
                    # an intentionally cleared "" API key) must still load;
                    # only a genuinely absent/null field should be skipped.
                    if hasattr(self, k) and v is not None:
                        setattr(self, k, v)
            except Exception:
                pass

    def save_to_json(self):
        json_path = ROOT_DIR / "config.json"
        try:
            import json
            data = {
                "USER_NAME": self.USER_NAME,
                "USER_LOCATION": self.USER_LOCATION,
                "DEFAULT_AI_PROVIDER": self.DEFAULT_AI_PROVIDER,
                "OPENSOURCE_LLM_URL": self.OPENSOURCE_LLM_URL,
                "OPENSOURCE_LLM_MODEL": self.OPENSOURCE_LLM_MODEL,
                "GROQ_API_KEY": self.GROQ_API_KEY,
                "GEMINI_API_KEY": self.GEMINI_API_KEY,
                "OPENAI_API_KEY": self.OPENAI_API_KEY,
                "ANTHROPIC_API_KEY": self.ANTHROPIC_API_KEY,
                "TTS_ENGINE": self.TTS_ENGINE,
                "KOKORO_ENGLISH_VOICE": self.KOKORO_ENGLISH_VOICE,
                "KOKORO_HINDI_VOICE": self.KOKORO_HINDI_VOICE,
                "FORCE_HINDI_ONLY_SPEECH": self.FORCE_HINDI_ONLY_SPEECH,
                "KOKORO_SPEED": self.KOKORO_SPEED,
                "XTTS_SPEAKER_WAV": self.XTTS_SPEAKER_WAV,
                "XTTS_SPEAKER_NAME": self.XTTS_SPEAKER_NAME,
                "ELEVENLABS_API_KEY": self.ELEVENLABS_API_KEY,
                "MIC_ENERGY_THRESHOLD": self.MIC_ENERGY_THRESHOLD,
                "MIC_DEVICE_INDEX": self.MIC_DEVICE_INDEX,
            }
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass


# Global singleton instance
config = AppConfig()
config.load_from_json()
