"""
Unit tests for Microsoft Edge TTS Engine and Swara Hindi voice integration.
"""
import os
import pytest
from app.config import config
from core.voice.edge_tts_engine import EdgeTTSEngine, edge_tts_engine


def test_edge_tts_singleton_and_availability():
    """Verifies EdgeTTSEngine is a valid singleton and edge-tts is available."""
    engine = EdgeTTSEngine.get_instance()
    assert engine is edge_tts_engine
    assert engine.is_available() is True


def test_default_config_is_swara_hindi():
    """Verifies default TTS engine and voice are set to Edge TTS with Swara Hindi."""
    assert getattr(config, "TTS_ENGINE", "") in ("edge", "edge_tts")
    assert getattr(config, "EDGE_TTS_HINDI_VOICE", "") == "hi-IN-SwaraNeural"
    assert getattr(config, "EDGE_TTS_VOICE", "") == "hi-IN-SwaraNeural"


def test_edge_tts_status_summary():
    """Verifies health check status summary correctly identifies Swara Hindi."""
    summary = edge_tts_engine.status_summary()
    assert "Ready" in summary
    assert "Swara" in summary


def test_edge_tts_voice_routing(monkeypatch):
    """Verifies voice selection for Hindi and English segments."""
    monkeypatch.setattr(config, "EDGE_TTS_HINDI_VOICE", "hi-IN-SwaraNeural")
    monkeypatch.setattr(config, "EDGE_TTS_ENGLISH_VOICE", "en-IN-NeerjaNeural")

    # With FORCE_HINDI_ONLY_SPEECH = True (default)
    monkeypatch.setattr(config, "FORCE_HINDI_ONLY_SPEECH", True)
    assert edge_tts_engine._voice_for("en") == "hi-IN-SwaraNeural"
    assert edge_tts_engine._voice_for("hi") == "hi-IN-SwaraNeural"

    # With FORCE_HINDI_ONLY_SPEECH = False
    monkeypatch.setattr(config, "FORCE_HINDI_ONLY_SPEECH", False)
    assert edge_tts_engine._voice_for("hi") == "hi-IN-SwaraNeural"
    assert edge_tts_engine._voice_for("en") == "en-IN-NeerjaNeural"

    # Explicit override
    assert edge_tts_engine._voice_for("hi", voice_override="hi-IN-MadhurNeural") == "hi-IN-MadhurNeural"


def test_edge_tts_synthesize_hindi():
    """Verifies that EdgeTTSEngine produces a playable MP3 file for Hindi text."""
    test_phrase = "नमस्ते, यह स्वरा हिंदी आवाज़ का परीक्षण है।"
    audio_file = edge_tts_engine.synthesize(test_phrase)
    try:
        assert audio_file is not None
        assert os.path.exists(audio_file)
        assert audio_file.endswith(".mp3")
        assert os.path.getsize(audio_file) > 1000
    finally:
        if audio_file and os.path.exists(audio_file):
            try:
                os.remove(audio_file)
            except Exception:
                pass


def test_edge_tts_config_persistence(tmp_path, monkeypatch):
    """Verifies Edge TTS settings round-trip through json persistence."""
    import importlib
    config_module = importlib.import_module("app.config")
    monkeypatch.setattr(config_module, "ROOT_DIR", tmp_path)

    cfg = config_module.AppConfig()
    cfg.TTS_ENGINE = "edge"
    cfg.EDGE_TTS_VOICE = "hi-IN-SwaraNeural"
    cfg.EDGE_TTS_HINDI_VOICE = "hi-IN-SwaraNeural"
    cfg.EDGE_TTS_ENGLISH_VOICE = "en-IN-NeerjaNeural"

    assert cfg.save_to_json() is True
    assert (tmp_path / "config.json").exists()

    reloaded = config_module.AppConfig()
    reloaded.load_from_json()

    assert reloaded.TTS_ENGINE == "edge"
    assert reloaded.EDGE_TTS_VOICE == "hi-IN-SwaraNeural"
    assert reloaded.EDGE_TTS_HINDI_VOICE == "hi-IN-SwaraNeural"
    assert reloaded.EDGE_TTS_ENGLISH_VOICE == "en-IN-NeerjaNeural"
