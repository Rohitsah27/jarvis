"""
Microsoft Edge TTS Neural Voice Engine for JARVIS.
Provides high-fidelity, free cloud speech synthesis using Microsoft Azure
Server Speech voices, featuring:
- Default Hindi: Microsoft Swara Neural (hi-IN-SwaraNeural)
- Alternative Hindi: Microsoft Madhur Neural (hi-IN-MadhurNeural)
- Indian English: Microsoft Neerja Neural (en-IN-NeerjaNeural)
- Standard English: Microsoft Jenny (en-US) / Sonia (en-GB)
Seamlessly integrates with core.voice.pronunciation preprocessing for natural
Devanagari, Hindi, and Hinglish pronunciation.
"""
import asyncio
import os
import tempfile
import threading
import time
import uuid
from typing import Dict, List, Optional, Tuple

try:
    import edge_tts
    HAS_EDGE_TTS = True
except Exception:
    edge_tts = None
    HAS_EDGE_TTS = False

from app.config import config
from core.voice.pronunciation import (
    detect_language,
    preprocess_for_speech,
    strip_markdown_for_speech,
)


# Popular Edge TTS voices available out of the box
AVAILABLE_EDGE_VOICES: Dict[str, Dict[str, str]] = {
    "hi-IN-SwaraNeural": {
        "name": "Swara",
        "gender": "Female",
        "locale": "hi-IN",
        "label": "Swara — Natural Hindi Female (Default & Recommended)",
    },
    "hi-IN-MadhurNeural": {
        "name": "Madhur",
        "gender": "Male",
        "locale": "hi-IN",
        "label": "Madhur — Natural Hindi Male",
    },
    "en-IN-NeerjaNeural": {
        "name": "Neerja",
        "gender": "Female",
        "locale": "en-IN",
        "label": "Neerja — Indian English Female",
    },
    "en-IN-PrabhatNeural": {
        "name": "Prabhat",
        "gender": "Male",
        "locale": "en-IN",
        "label": "Prabhat — Indian English Male",
    },
    "en-US-JennyNeural": {
        "name": "Jenny",
        "gender": "Female",
        "locale": "en-US",
        "label": "Jenny — US English Female",
    },
    "en-US-GuyNeural": {
        "name": "Guy",
        "gender": "Male",
        "locale": "en-US",
        "label": "Guy — US English Male",
    },
    "en-GB-SoniaNeural": {
        "name": "Sonia",
        "gender": "Female",
        "locale": "en-GB",
        "label": "Sonia — British English Female",
    },
    "en-GB-RyanNeural": {
        "name": "Ryan",
        "gender": "Male",
        "locale": "en-GB",
        "label": "Ryan — British English Male",
    },
}


class EdgeTTSEngine:
    """Microsoft Edge TTS speech synthesizer singleton."""

    _instance: Optional["EdgeTTSEngine"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._available = HAS_EDGE_TTS

    @classmethod
    def get_instance(cls) -> "EdgeTTSEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = EdgeTTSEngine()
            return cls._instance

    def is_available(self) -> bool:
        """Returns True if the edge_tts module is installed and functional."""
        return HAS_EDGE_TTS and edge_tts is not None

    def status_summary(self) -> str:
        """One-line human-readable status for the Project Health dashboard."""
        if not self.is_available():
            return "Not installed (edge-tts package missing)"
        hindi_voice = getattr(config, "EDGE_TTS_HINDI_VOICE", "hi-IN-SwaraNeural")
        voice_info = AVAILABLE_EDGE_VOICES.get(hindi_voice, {})
        voice_name = voice_info.get("name", hindi_voice)
        return f"Ready (Edge TTS: {voice_name} Hindi)"

    @staticmethod
    def detect_language(text: str) -> str:
        return detect_language(text)

    def _voice_for(self, lang: str, voice_override: Optional[str] = None) -> str:
        if voice_override:
            return voice_override
        if getattr(config, "FORCE_HINDI_ONLY_SPEECH", False):
            return getattr(config, "EDGE_TTS_HINDI_VOICE", "hi-IN-SwaraNeural") or "hi-IN-SwaraNeural"
        if lang == "hi":
            return getattr(config, "EDGE_TTS_HINDI_VOICE", "hi-IN-SwaraNeural") or "hi-IN-SwaraNeural"
        return getattr(config, "EDGE_TTS_ENGLISH_VOICE", "en-IN-NeerjaNeural") or "en-IN-NeerjaNeural"

    def _format_rate(self, speed: Optional[float] = None) -> str:
        """Converts speed multiplier (e.g. 1.05) to Edge TTS rate string (e.g. '+5%')."""
        eff_speed = speed if speed is not None else getattr(config, "KOKORO_SPEED", 1.05)
        if eff_speed is None:
            eff_speed = 1.0
        pct = int(round((eff_speed - 1.0) * 100))
        return f"{pct:+d}%"

    async def _synthesize_async(
        self,
        segments: List[Tuple[str, str]],
        voice_override: Optional[str] = None,
        speed: Optional[float] = None,
    ) -> Optional[bytes]:
        """Synthesizes all segments concurrently or sequentially and concatenates MP3 byte streams."""
        rate_str = self._format_rate(speed)
        pitch_str = getattr(config, "EDGE_TTS_PITCH", "+0Hz") or "+0Hz"

        audio_parts: List[bytes] = []
        for seg_text, seg_lang in segments:
            seg_text = seg_text.strip()
            if not seg_text:
                continue
            chosen_voice = self._voice_for(seg_lang, voice_override)
            try:
                communicator = edge_tts.Communicate(
                    text=seg_text,
                    voice=chosen_voice,
                    rate=rate_str,
                    pitch=pitch_str,
                )
                seg_bytes = b""
                async for chunk in communicator.stream():
                    if chunk["type"] == "audio":
                        seg_bytes += chunk["data"]
                if seg_bytes:
                    audio_parts.append(seg_bytes)
            except Exception as e:
                print(f"[EdgeTTSEngine] Error synthesizing segment '{seg_text[:30]}...' with {chosen_voice}: {e}")
                raise

        if not audio_parts:
            return None
        return b"".join(audio_parts)

    def synthesize(
        self,
        text: str,
        voice_override: Optional[str] = None,
        speed: Optional[float] = None,
    ) -> Optional[str]:
        """
        Synthesizes text into an MP3 audio file.
        Returns the absolute filepath of the generated audio file, or None on failure.
        """
        if not self.is_available():
            print("[EdgeTTSEngine] edge-tts is not available.")
            return None

        if voice_override:
            cleaned_text = strip_markdown_for_speech(text)
            if not cleaned_text:
                return None
            segments = [(cleaned_text, detect_language(cleaned_text))]
        else:
            segments = preprocess_for_speech(text)
            if not segments:
                return None

        # Execute async synthesis within worker thread event loop
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                audio_bytes = loop.run_until_complete(
                    self._synthesize_async(segments, voice_override=voice_override, speed=speed)
                )
            finally:
                loop.close()

            if not audio_bytes:
                return None

            tmp_filename = f"jarvis_swara_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}.mp3"
            tmp_path = os.path.join(tempfile.gettempdir(), tmp_filename)
            with open(tmp_path, "wb") as f:
                f.write(audio_bytes)

            return tmp_path
        except Exception as e:
            print(f"[EdgeTTSEngine] Speech synthesis error: {e}")
            return None


# Global singleton instance
edge_tts_engine = EdgeTTSEngine.get_instance()
