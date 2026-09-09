"""
Speech-to-Text engine abstraction for JARVIS.

Two backends behind one interface:
- Faster-Whisper (local, offline, primary): runs a quantized Whisper model
  via ctranslate2 entirely on-device — no network round-trip, no per-call
  cloud quota, and noticeably more robust on Hindi/Hinglish and accented
  speech than Google's free API in testing.
- Google Web Speech API (cloud, fallback): the engine this app used
  exclusively before — kept as a safety net if Whisper fails to load
  (model not downloaded yet, disk/memory pressure) or errors on a
  particular utterance.

Engine selection and fallback are config-driven (config.STT_ENGINE /
config.STT_FALLBACK_ENGINE) so switching back to Google-only, or dropping
in a different local model size, never requires touching voice_engine.py.

WHY A SEPARATE MODULE
Mirrors the existing kokoro_engine.py / xtts_engine.py pattern: a lazily-
loaded singleton per engine, isolated here so voice_engine.py's
ContinuousMicListenerThread stays about mic capture and VAD, not model
plumbing — and so this is trivially unit-testable without a real
microphone or audio device.
"""
import time
from dataclasses import dataclass
from typing import Optional

try:
    from faster_whisper import WhisperModel
    HAS_FASTER_WHISPER = True
except Exception:
    HAS_FASTER_WHISPER = False

try:
    import speech_recognition as sr
    HAS_SR = True
except Exception:
    sr = None
    HAS_SR = False

import numpy as np

from app.config import config


@dataclass
class STTResult:
    """One transcription attempt's outcome — everything voice_engine.py
    needs to log and act on, in one object instead of scattered return
    values."""
    text: str
    success: bool
    engine_used: str            # "faster_whisper", "google", or "" if both failed
    duration_ms: float
    used_fallback: bool = False
    error: Optional[str] = None


class SpeechToTextEngine:
    """Local Faster-Whisper (primary) with Google Web Speech API (fallback)."""

    _instance: Optional["SpeechToTextEngine"] = None

    def __init__(self):
        self._whisper_model: Optional["WhisperModel"] = None
        self._whisper_loaded = False
        self._whisper_load_failed = False

    @classmethod
    def get_instance(cls) -> "SpeechToTextEngine":
        if cls._instance is None:
            cls._instance = SpeechToTextEngine()
        return cls._instance

    def is_whisper_available(self) -> bool:
        return HAS_FASTER_WHISPER

    def status_summary(self) -> str:
        """One-line human-readable status for the Project Health dashboard."""
        primary = getattr(config, "STT_ENGINE", "faster_whisper")
        if primary == "faster_whisper":
            if self._whisper_loaded:
                return f"Ready (Faster-Whisper '{getattr(config, 'STT_WHISPER_MODEL_SIZE', 'small')}')"
            if self._whisper_load_failed:
                return f"Degraded — using fallback ({getattr(config, 'STT_FALLBACK_ENGINE', 'google')})"
            return "Not loaded yet"
        return f"Ready ({primary})"

    def ensure_whisper_loaded(self) -> bool:
        """
        Loads the Whisper model once (first call downloads the model
        weights to the local Hugging Face cache if not already present —
        see STT_WHISPER_MODEL_SIZE for the size/disk tradeoff). Safe to
        call repeatedly; only does real work the first time. Called from a
        background preload worker at app startup (see main_window.py) so
        the first real command doesn't pay this cost mid-conversation.
        """
        if self._whisper_loaded and self._whisper_model:
            return True
        if self._whisper_load_failed:
            # Don't retry a heavy failed load on every single utterance —
            # once it's confirmed broken this session, fall back to Google
            # for the rest of it instead of stalling every mic capture.
            return False
        if not HAS_FASTER_WHISPER:
            return False

        try:
            model_size = getattr(config, "STT_WHISPER_MODEL_SIZE", "small")
            device = getattr(config, "STT_WHISPER_DEVICE", "cpu")
            compute_type = getattr(config, "STT_WHISPER_COMPUTE_TYPE", "int8")
            print(f"[STTEngine] Loading Faster-Whisper '{model_size}' model "
                  f"(device={device}, compute={compute_type}; first run downloads the weights)...")
            start_t = time.perf_counter()
            self._whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type)
            self._whisper_loaded = True
            load_time = (time.perf_counter() - start_t) * 1000.0
            print(f"[STTEngine] Faster-Whisper ready ({load_time:.1f}ms).")
            return True
        except Exception as e:
            print(f"[STTEngine] Failed to load Faster-Whisper: {e}")
            self._whisper_load_failed = True
            return False

    @staticmethod
    def _audio_to_float32(audio_data: "sr.AudioData") -> np.ndarray:
        """Converts SpeechRecognition's AudioData (raw PCM16 mono) into the
        normalized float32 numpy array Whisper expects, resampling to 16kHz
        if the mic captured at a different rate — Whisper is trained on
        16kHz audio and silently degrades on mismatched input."""
        raw = audio_data.get_raw_data(convert_rate=16000, convert_width=2)
        pcm16 = np.frombuffer(raw, dtype=np.int16)
        return pcm16.astype(np.float32) / 32768.0

    def _transcribe_faster_whisper(self, audio_data: "sr.AudioData") -> Optional[str]:
        if not self.ensure_whisper_loaded():
            return None
        audio_np = self._audio_to_float32(audio_data)
        if audio_np.size == 0:
            return None

        # "hi" hint (not auto-detect): this app's whole downstream pipeline
        # — Hindi-only TTS forcing, the Hinglish display transliteration,
        # jarvis_brain's language branching — keys off real Devanagari
        # text, and Whisper's "hi" mode outputs Devanagari by default, so
        # this keeps STT output in the script everything else expects.
        # Whisper still transcribes embedded English words/names correctly
        # under this hint, which is what actually matters for Hinglish.
        segments, _info = self._whisper_model.transcribe(
            audio_np,
            language="hi",
            vad_filter=False,  # webrtcvad already gated this clip before we got here
            beam_size=5,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text or None

    def _transcribe_google(self, audio_data: "sr.AudioData", recognizer: "sr.Recognizer") -> Optional[str]:
        """Unchanged from the app's original behavior: primary language
        first, then en-IN as a secondary attempt for English/Hinglish
        phrases the primary language model doesn't recognize."""
        if not HAS_SR or recognizer is None:
            return None
        try:
            text = recognizer.recognize_google(audio_data, language=config.VOICE_LANGUAGE)
            if text and text.strip():
                return text.strip()
        except Exception:
            pass
        try:
            text = recognizer.recognize_google(audio_data, language="en-IN")
            if text and text.strip():
                return text.strip()
        except Exception:
            pass
        return None

    def transcribe(self, audio_data: "sr.AudioData", recognizer: "sr.Recognizer" = None) -> STTResult:
        """
        Runs config.STT_ENGINE first; on failure/empty result, retries with
        config.STT_FALLBACK_ENGINE. Always returns an STTResult (never
        raises) so the mic thread's loop never dies on a single bad
        utterance — success=False with an empty engine_used just means
        both engines failed and the caller should treat it like silence.
        """
        engines = {
            "faster_whisper": lambda: self._transcribe_faster_whisper(audio_data),
            "google": lambda: self._transcribe_google(audio_data, recognizer),
        }

        primary = getattr(config, "STT_ENGINE", "faster_whisper")
        fallback = getattr(config, "STT_FALLBACK_ENGINE", "google")

        start_t = time.perf_counter()
        last_error: Optional[str] = None

        for engine_name, used_fallback in ((primary, False), (fallback, True)):
            if used_fallback and engine_name == primary:
                continue  # fallback is the same engine as primary — nothing new to try
            transcribe_fn = engines.get(engine_name)
            if transcribe_fn is None:
                continue
            try:
                text = transcribe_fn()
            except Exception as e:
                last_error = str(e)
                text = None
            if text:
                duration_ms = (time.perf_counter() - start_t) * 1000.0
                return STTResult(
                    text=text, success=True, engine_used=engine_name,
                    duration_ms=duration_ms, used_fallback=used_fallback,
                )

        duration_ms = (time.perf_counter() - start_t) * 1000.0
        return STTResult(
            text="", success=False, engine_used="", duration_ms=duration_ms,
            used_fallback=False, error=last_error,
        )


# Global singleton
stt_engine = SpeechToTextEngine.get_instance()
