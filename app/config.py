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
    # Renamed from MIC_PAUSE_THRESHOLD (was 0.6s) — that was the actual bug
    # behind "if I pause briefly, it finalizes too early": 0.6s of silence
    # is well within a normal thinking-pause mid-sentence. 2.0s only
    # finalizes once the user has genuinely stopped talking, while still
    # merging brief pauses into the same utterance (this IS how
    # SpeechRecognition's own pause_threshold works — it doesn't cut on
    # every silent frame, only once silence has been continuous for this
    # long, which already gives the "merge short pauses" behavior asked
    # for without needing a separate buffering layer).
    STT_PAUSE_TIMEOUT_SECONDS: float = 2.0
    MIC_PHRASE_LIMIT: int = 15                        # Max seconds per utterance (raised from 7 now that pauses
                                                        # up to STT_PAUSE_TIMEOUT_SECONDS no longer end it early —
                                                        # a real multi-clause sentence with a couple of pauses could
                                                        # otherwise get cut off before the user finishes)
    MIC_DEVICE_INDEX: Optional[int] = None            # Selected microphone index (None = System Default)

    # Speech-to-Text Engine Configuration
    STT_ENGINE: str = "faster_whisper"                # Primary: "faster_whisper" (local, offline) or "google" (cloud)
    STT_FALLBACK_ENGINE: str = "google"               # Used if the primary engine fails to load or errors on a call
    STT_WHISPER_MODEL_SIZE: str = "small"             # tiny(~75MB)/base(~145MB)/small(~484MB)/medium(~1.5GB)/large-v3(~3GB)
                                                        # "small" chosen as the minimum size with solid Hindi accuracy —
                                                        # tiny/base are noticeably worse on Hindi specifically. Raise this
                                                        # if disk space allows; lower it if it doesn't.
    STT_WHISPER_DEVICE: str = "cpu"                   # "cpu" or "cuda" (only if you have a compatible NVIDIA GPU + CUDA)
    STT_WHISPER_COMPUTE_TYPE: str = "int8"            # Quantized for CPU speed/memory; use "float16" only with STT_WHISPER_DEVICE="cuda"
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
                "STT_PAUSE_TIMEOUT_SECONDS": self.STT_PAUSE_TIMEOUT_SECONDS,
                "MIC_PHRASE_LIMIT": self.MIC_PHRASE_LIMIT,
                "STT_ENGINE": self.STT_ENGINE,
                "STT_FALLBACK_ENGINE": self.STT_FALLBACK_ENGINE,
                "STT_WHISPER_MODEL_SIZE": self.STT_WHISPER_MODEL_SIZE,
                "STT_WHISPER_DEVICE": self.STT_WHISPER_DEVICE,
                "STT_WHISPER_COMPUTE_TYPE": self.STT_WHISPER_COMPUTE_TYPE,
            }
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass


# Global singleton instance
config = AppConfig()
config.load_from_json()
