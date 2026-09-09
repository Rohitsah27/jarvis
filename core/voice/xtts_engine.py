"""
Coqui XTTS-v2 High-Quality Neural Text-to-Speech Engine for JARVIS.
Opt-in "cinematic quality" voice mode — closest open-source match to ElevenLabs
naturalness, with native multilingual support (including Hindi) and optional
voice cloning from a short reference sample. Runs on CPU by default (slower
than Kokoro, several seconds per reply) so it is selected explicitly in
Settings rather than used as the always-on default.
"""
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Optional

# Auto-accept the Coqui model license non-interactively (personal/non-commercial use).
os.environ.setdefault("COQUI_TOS_AGREED", "1")

try:
    from TTS.api import TTS
    HAS_XTTS = True
except Exception:
    HAS_XTTS = False

from app.config import config

_XTTS_LANG_MAP = {
    "hi": "hi", "en": "en", "es": "es", "fr": "fr", "de": "de", "it": "it",
    "pt": "pt", "pl": "pl", "tr": "tr", "ru": "ru", "nl": "nl", "cs": "cs",
    "ar": "ar", "zh": "zh-cn", "ja": "ja", "hu": "hu", "ko": "ko",
}


class XTTSEngine:
    """Local Coqui XTTS-v2 speech synthesizer (opt-in high-quality mode)."""

    _instance: Optional["XTTSEngine"] = None

    def __init__(self):
        self._tts: Optional["TTS"] = None
        self._loaded = False
        self._load_failed = False

    @classmethod
    def get_instance(cls) -> "XTTSEngine":
        if cls._instance is None:
            cls._instance = XTTSEngine()
        return cls._instance

    def is_available(self) -> bool:
        """Checks if the coqui-tts package is installed."""
        return HAS_XTTS

    def status_summary(self) -> str:
        """One-line human-readable status for the Project Health dashboard."""
        if self._loaded:
            return "Ready (XTTS)"
        if not self.is_available():
            return "Not installed (coqui-tts missing)"
        return "Not loaded yet"

    def _ensure_loaded(self) -> bool:
        if self._loaded and self._tts:
            return True
        if self._load_failed:
            # Don't retry a heavy failed load on every single utterance.
            return False
        if not HAS_XTTS:
            return False

        try:
            print("[XTTSEngine] Loading Coqui XTTS-v2 model (first run downloads ~1.9GB)...")
            start_t = time.perf_counter()
            self._tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False).to("cpu")
            self._loaded = True
            load_time = (time.perf_counter() - start_t) * 1000.0
            print(f"[XTTSEngine] XTTS-v2 ready ({load_time:.1f}ms).")
            return True
        except Exception as e:
            print(f"[XTTSEngine] Failed to initialize XTTS-v2: {e}")
            self._load_failed = True
            return False

    @staticmethod
    def detect_language(text: str) -> str:
        """Determines whether text is predominantly Hindi or English."""
        if re.search(r"[ऀ-ॿ]", text):
            return "hi"
        return "en"

    def _resolve_speaker(self) -> dict:
        """Returns kwargs selecting a voice: cloned from a sample wav, or a built-in speaker."""
        speaker_wav = getattr(config, "XTTS_SPEAKER_WAV", "") or ""
        if speaker_wav and Path(speaker_wav).exists():
            return {"speaker_wav": speaker_wav}

        try:
            speakers = list(self._tts.speakers or [])
        except Exception:
            speakers = []

        if not speakers:
            return {}

        preferred = getattr(config, "XTTS_SPEAKER_NAME", "") or ""
        if preferred and preferred in speakers:
            return {"speaker": preferred}
        return {"speaker": speakers[0]}

    def synthesize(self, text: str, speed: Optional[float] = None) -> Optional[str]:
        """
        Synthesizes text into a temporary WAV file using XTTS-v2.
        Returns the absolute filepath of the generated audio, or None on failure.
        """
        if not self._ensure_loaded():
            return None

        cleaned_text = text.strip()
        if not cleaned_text:
            return None

        cleaned_text = re.sub(r"```.*?```", "", cleaned_text, flags=re.DOTALL)
        cleaned_text = re.sub(r"[\*\_#`]", "", cleaned_text).strip()
        if not cleaned_text:
            cleaned_text = text.strip()

        lang = self.detect_language(cleaned_text)
        xtts_lang = _XTTS_LANG_MAP.get(lang, "en")

        try:
            voice_kwargs = self._resolve_speaker()
            tmp_wav = os.path.join(tempfile.gettempdir(), f"jarvis_xtts_{int(time.time() * 1000)}.wav")
            self._tts.tts_to_file(
                text=cleaned_text,
                language=xtts_lang,
                file_path=tmp_wav,
                speed=speed or 1.0,
                **voice_kwargs,
            )
            if os.path.exists(tmp_wav):
                return tmp_wav
            return None
        except Exception as e:
            print(f"[XTTSEngine] Synthesis error for '{cleaned_text[:30]}...': {e}")
            return None


# Global singleton
xtts_engine = XTTSEngine.get_instance()
