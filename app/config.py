"""
Application configuration and global constants for JARVIS.
"""
import os
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
    # This app has no wake-word/keyword-spotting stage — when this is True,
    # the microphone is transcribed and reasoned about CONTINUOUSLY the
    # whole time JARVIS is running, with no trigger phrase required. That
    # is a real, materially-privacy-relevant default and must be an
    # explicit opt-in, not the out-of-box behavior. Toggle it on in
    # Settings > Voice if you want always-on listening; the UI clearly
    # discloses what turning it on means.
    ALWAYS_LISTEN: bool = True                        # Automatically listen continuously; standby after 15m inactivity
    VOICE_INACTIVITY_TIMEOUT_MINUTES: int = 15        # Inactivity timeout (minutes) before falling back to System Online
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
    STT_PAUSE_TIMEOUT_SECONDS: float = 1.0
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
    BARGE_IN_ENABLED: bool = True                     # Allow speaking over JARVIS to interrupt it mid-reply (Real-Time Duplex)
    BARGE_IN_ENERGY_MULTIPLIER: float = 1.4           # Energy multiplier for interruption threshold (with WebRTC VAD verification)
    ACTIVE_CONVERSATION_HISTORY_TURNS: int = 16       # Number of previous messages sent to LLM for rich context continuity

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
    TTS_ENGINE: str = "edge"                           # Primary: "edge" (Microsoft Edge Neural TTS - Swara Hindi Default), "kokoro" (Free/Local), "xtts" (Coqui XTTS-v2), "elevenlabs" (Cloud), "sapi" (Native)
    EDGE_TTS_VOICE: str = "hi-IN-SwaraNeural"          # Microsoft Swara - Natural Hindi India Female (Default)
    EDGE_TTS_HINDI_VOICE: str = "hi-IN-SwaraNeural"    # Microsoft Swara Neural (Hindi India)
    EDGE_TTS_ENGLISH_VOICE: str = "en-IN-NeerjaNeural" # Microsoft Neerja Neural (Indian English)
    EDGE_TTS_RATE: str = "+0%"                         # Edge TTS speech rate modifier
    EDGE_TTS_PITCH: str = "+0Hz"                       # Edge TTS speech pitch modifier
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
    DEFAULT_VOICE_MODEL: str = "Microsoft Edge TTS (hi-IN-SwaraNeural / Swara Hindi)"
    TTS_LOCAL_API_URL: str = ""                       # Optional local TTS server URL

    
    # LLM Cloud API Keys
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    # Anthropic periodically retires older dated model snapshots — kept
    # configurable (rather than hardcoded in claude_provider.py) so a stale
    # value can be corrected without a code change. Verify against
    # https://docs.anthropic.com/en/docs/about-claude/models periodically.
    ANTHROPIC_MODEL: str = "claude-3-7-sonnet-20250219"

    # Computer Control Settings
    COMPUTER_CONTROL_ACTIVE: bool = True
    # REQUIRE_CONFIRMATION_FOR_ACTIONS was removed (used to default False and
    # be the root cause of every CONFIRMATION_REQUIRED tool executing with
    # zero human approval — the flag itself was never even wired to a real
    # dialog). Confirmation is no longer optional or config-driven: it is a
    # hard property of each tool's PermissionLevel, enforced inside
    # core/tools/permission.py, and there is no setting anywhere that can
    # disable it for a CONFIRMATION_REQUIRED or HIGH_RISK tool.

    # First-run consent for analyze_screen's cloud vision upload path
    # (Gemini/OpenAI). None = not asked yet (asked on first use); True =
    # user allowed cloud screen analysis; False = user denied it (screen
    # analysis still works locally, just never uploads pixels anywhere).
    # Revocable from Settings > Privacy.
    SCREEN_ANALYSIS_CLOUD_CONSENT: Optional[bool] = None

    # Runtime testing/debug mode: logs every pipeline stage (mic start, STT
    # result, agent intent, tool chosen, tool success/error, TTS start, total
    # latency) to console + logs/jarvis_debug.log. Costs ~nothing when off,
    # negligible disk when on (log file capped at ~1MB). Transcript text
    # logged this way is truncated (~40-60 chars) and stays local, never
    # transmitted anywhere — see core/telemetry.py.
    DEBUG_PIPELINE_LOGGING: bool = True

    # Conversation history (core/ai/manager.py) is bounded to this many
    # most-recent messages in memory — without a cap it grew for the entire
    # process lifetime with no eviction. Each provider already only sends
    # the last 6-10 messages per call, so this only bounds RAM use over a
    # long session, not per-call token cost.
    MAX_CONVERSATION_HISTORY_MESSAGES: int = 200

    # core/voice/learning_memory.py's persisted vocabulary-correction store
    # is bounded and expires — see that module for how these are enforced.
    LEARNING_MEMORY_MAX_ENTRIES: int = 500
    LEARNING_MEMORY_TTL_DAYS: int = 90

    # Timers & Intervals (ms)
    SYSTEM_POLL_INTERVAL_MS: int = 1500
    ORB_ANIMATION_INTERVAL_MS: int = 33  # ~30-33 FPS
    CLOCK_UPDATE_INTERVAL_MS: int = 1000
    WAVEFORM_INTERVAL_MS: int = 40

    # Set to a human-readable message whenever the most recent load/save
    # attempt failed, so callers (Settings page, health dashboard) can
    # surface it instead of the user's changes silently vanishing with no
    # explanation. None means the last attempt succeeded (or none has run
    # yet).
    last_persistence_error: Optional[str] = None

    def load_from_json(self):
        json_path = ROOT_DIR / "config.json"
        if not json_path.exists():
            return
        try:
            import json
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            # A corrupt/unreadable config.json must not silently discard
            # the user's settings — logging.basicConfig may not be
            # configured this early (config.py is one of the very first
            # modules imported), so this also goes to stderr directly to
            # guarantee visibility even before logging is set up.
            msg = f"Could not read config.json ({type(e).__name__}: {e}) — using defaults for this session."
            # Instance attribute, NOT AppConfig.last_persistence_error —
            # this is a @dataclass field, so __init__ already gave this
            # instance its own last_persistence_error=None that would
            # otherwise permanently shadow a class-level assignment.
            self.last_persistence_error = msg
            try:
                import logging
                logging.getLogger("jarvis.config").error(msg)
            except Exception:
                pass
            print(f"[Config] {msg}")
            return

        applied, skipped = 0, []
        for k, v in data.items():
            # v is checked against None rather than truthiness — a
            # falsy-but-meaningful saved value (mic device index 0,
            # an intentionally cleared "" API key) must still load;
            # only a genuinely absent/null field should be skipped.
            if hasattr(self, k) and v is not None:
                try:
                    setattr(self, k, v)
                    applied += 1
                except Exception:
                    skipped.append(k)
            elif not hasattr(self, k):
                skipped.append(k)
        if skipped:
            # Not fatal — e.g. a field renamed/removed since this
            # config.json was written — but worth knowing about rather
            # than silently ignoring.
            print(f"[Config] Ignored {len(skipped)} unrecognized/invalid saved field(s): {skipped}")

    def save_to_json(self) -> bool:
        """Returns True on success. On failure, sets last_persistence_error
        to a human-readable message (never silently discards the failure)
        and returns False — callers that show a UI (Settings page) should
        check this and tell the user the save didn't happen."""
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
                "ANTHROPIC_MODEL": self.ANTHROPIC_MODEL,
                "TTS_ENGINE": self.TTS_ENGINE,
                "EDGE_TTS_VOICE": self.EDGE_TTS_VOICE,
                "EDGE_TTS_HINDI_VOICE": self.EDGE_TTS_HINDI_VOICE,
                "EDGE_TTS_ENGLISH_VOICE": self.EDGE_TTS_ENGLISH_VOICE,
                "EDGE_TTS_RATE": self.EDGE_TTS_RATE,
                "EDGE_TTS_PITCH": self.EDGE_TTS_PITCH,
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
                "ALWAYS_LISTEN": self.ALWAYS_LISTEN,
                "BARGE_IN_ENABLED": self.BARGE_IN_ENABLED,
                "ACTIVE_CONVERSATION_HISTORY_TURNS": self.ACTIVE_CONVERSATION_HISTORY_TURNS,
                "VOICE_INACTIVITY_TIMEOUT_MINUTES": self.VOICE_INACTIVITY_TIMEOUT_MINUTES,
                "TTS_LOCAL_API_URL": self.TTS_LOCAL_API_URL,
                "SCREEN_ANALYSIS_CLOUD_CONSENT": self.SCREEN_ANALYSIS_CLOUD_CONSENT,
                "MAX_CONVERSATION_HISTORY_MESSAGES": self.MAX_CONVERSATION_HISTORY_MESSAGES,
                "LEARNING_MEMORY_MAX_ENTRIES": self.LEARNING_MEMORY_MAX_ENTRIES,
                "LEARNING_MEMORY_TTL_DAYS": self.LEARNING_MEMORY_TTL_DAYS,
            }
            # Atomic write: a crash/power-loss mid-write must never leave
            # config.json half-written (which load_from_json would then
            # fail to parse, discarding EVERY setting, not just the one
            # being changed). Write to a temp file in the same directory
            # (so the rename is on the same filesystem/volume, guaranteeing
            # atomicity) and rename over the real path only once the full
            # write has succeeded.
            tmp_path = json_path.with_suffix(".json.tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, json_path)
            self.last_persistence_error = None
            return True
        except Exception as e:
            msg = f"Could not save settings ({type(e).__name__}: {e})."
            self.last_persistence_error = msg
            try:
                import logging
                logging.getLogger("jarvis.config").error(msg)
            except Exception:
                pass
            print(f"[Config] {msg}")
            # Best-effort: also record it as an observed issue so it shows
            # up in the Health dashboard / "what problem did you observe",
            # not just a console line nobody sees. Lazy import — by the
            # time save_to_json() is actually called (a UI action, well
            # after startup) this is always safe, but importing it at
            # config.py's own module level would risk a circular import
            # during the very early config = AppConfig(); config.load_from_json()
            # bootstrap in this same file.
            try:
                from core.observability.observer import observer
                observer.record_issue("config_error", summary=msg, source="AppConfig.save_to_json")
            except Exception:
                pass
            return False


# Global singleton instance
config = AppConfig()
config.load_from_json()
