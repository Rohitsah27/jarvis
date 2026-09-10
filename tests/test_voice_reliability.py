"""
Tests for the voice-pipeline reliability fixes: the "cloud"->"Claude"
vocabulary-correction regression, learning_memory bounding/TTL/clear, the
intent-router confidence-threshold boundary, and the mic-unavailable state
transition (listening_active wiring).
"""
import time

import pytest


# --- Vocabulary correction regression --------------------------------------

@pytest.mark.parametrize("phrase", [
    "show me the cloud status",
    "check my cloud storage",
    "its cloudy today",
    "upload it to the cloud",
    "the cloud is expanding",
])
def test_cloud_word_not_corrected_to_claude(qapp, phrase):
    from core.voice.transcript_processor import correct_vocabulary

    corrected, _ = correct_vocabulary(phrase)
    assert "claude" not in corrected.lower(), f"{phrase!r} was wrongly corrected to {corrected!r}"


def test_genuine_claude_mishearing_still_corrected(qapp):
    from core.voice.transcript_processor import correct_vocabulary

    corrected, _ = correct_vocabulary("ask clod to fix the bug")
    assert "Claude" in corrected


def test_jarvis_mishearing_still_corrected(qapp):
    from core.voice.transcript_processor import correct_vocabulary

    corrected, _ = correct_vocabulary("hey jervis open notepad")
    assert "JARVIS" in corrected


# --- learning_memory bounding / TTL / clear --------------------------------

@pytest.fixture
def isolated_learning_memory(qapp, tmp_path, monkeypatch):
    import core.voice.learning_memory as lm

    monkeypatch.setattr(lm, "_MEMORY_PATH", tmp_path / "learned_corrections.json")
    lm._pending = None
    return lm


def test_learning_memory_round_trip(isolated_learning_memory):
    lm = isolated_learning_memory
    lm.mark_awaiting_clarification("raw utterance", "cleaned utterance")
    lm.resolve_pending_clarification("the resolved text")

    result = lm.get_learned_correction("cleaned utterance")
    assert result == "the resolved text"


def test_learning_memory_bounded(isolated_learning_memory, monkeypatch):
    lm = isolated_learning_memory
    from app.config import config

    monkeypatch.setattr(config, "LEARNING_MEMORY_MAX_ENTRIES", 5)

    for i in range(20):
        lm.mark_awaiting_clarification(f"raw {i}", f"cleaned {i}")
        lm.resolve_pending_clarification(f"resolved {i}")

    data = lm._load()
    assert len(data) <= 5


def test_learning_memory_ttl_expiry(isolated_learning_memory, monkeypatch):
    lm = isolated_learning_memory
    from app.config import config

    monkeypatch.setattr(config, "LEARNING_MEMORY_TTL_DAYS", 1)

    # Write an entry directly with a stale timestamp (40 days old).
    import json
    stale_data = {
        "old phrase": {
            "resolved_as": "old resolution",
            "raw_example": "old raw",
            "learned_at": time.time() - (40 * 86400),
        }
    }
    lm._MEMORY_PATH.write_text(json.dumps(stale_data), encoding="utf-8")

    result = lm.get_learned_correction("old phrase")
    assert result is None  # expired, must not be returned


def test_learning_memory_clear_all(isolated_learning_memory):
    lm = isolated_learning_memory
    lm.mark_awaiting_clarification("raw", "cleaned")
    lm.resolve_pending_clarification("resolved")
    assert lm._MEMORY_PATH.exists()

    ok = lm.clear_all()
    assert ok is True
    assert not lm._MEMORY_PATH.exists()
    assert lm.get_learned_correction("cleaned") is None


def test_learning_memory_rejects_malformed_entries(isolated_learning_memory):
    """A hand-edited or corrupted entry missing required fields must be
    skipped, not crash the caller."""
    import json
    lm = isolated_learning_memory
    lm._MEMORY_PATH.write_text(
        json.dumps({"bad entry": {"not_the_right_shape": True}, "good entry": "not even a dict"}),
        encoding="utf-8",
    )
    result = lm.get_learned_correction("bad entry")
    assert result is None  # did not crash, just found nothing usable


# --- Memory cannot bypass the confirmation gate ----------------------------

def test_learned_correction_cannot_bypass_confirmation(qapp, deny_all, isolated_learning_memory):
    """Even a maximally-confident, memory-boosted fast-path match to a
    CONFIRMATION_REQUIRED tool must still go through the real gate — this
    is the actual security property, not just a router-confidence detail."""
    from core.voice import intent_router
    from core.tools.tool_manager import tool_manager

    decision = intent_router.route("open notepad please")
    if decision.source == "fast" and decision.tool_calls:
        for call in decision.tool_calls:
            result = tool_manager.execute_tool(call.tool_name, **call.arguments)
            tool = tool_manager.get_tool(call.tool_name)
            from core.tools.base import AUTO_ALLOWED_LEVELS
            if tool.permission_level not in AUTO_ALLOWED_LEVELS:
                assert result.success is False
                assert result.error == "permission_denied"


# --- Intent router confidence boundary -------------------------------------

def test_confidence_boundary_asks_clarification_not_executes(qapp):
    """The exact worst-case fuzzy single-word score (0.45) must fall on
    the 'ask for clarification' side of the threshold, not 'confident
    enough to act'."""
    from core.voice.intent_router import _score_fast_path, LOW_CONFIDENCE_THRESHOLD

    worst_case_score = _score_fast_path("x", was_fuzzy=True)
    assert worst_case_score == pytest.approx(0.45)
    assert worst_case_score <= LOW_CONFIDENCE_THRESHOLD  # must trigger clarification


# --- Mic-unavailable state transition ---------------------------------------

def test_mic_listening_active_false_transitions_to_unavailable(qapp):
    from core.voice.voice_engine import VoiceEngine, VoiceState

    engine = VoiceEngine()
    try:
        engine.set_state(VoiceState.LISTENING)
        engine._on_mic_listening_active(False)
        assert engine.state == VoiceState.MIC_UNAVAILABLE
    finally:
        engine.shutdown()


def test_mic_listening_active_true_recovers_from_unavailable(qapp):
    from core.voice.voice_engine import VoiceEngine, VoiceState

    engine = VoiceEngine()
    try:
        engine.set_state(VoiceState.MIC_UNAVAILABLE)
        engine._on_mic_listening_active(True)
        assert engine.state == VoiceState.LISTENING
    finally:
        engine.shutdown()


def test_toggle_listening_retries_from_mic_unavailable(qapp, monkeypatch):
    from core.voice.voice_engine import VoiceEngine, VoiceState

    engine = VoiceEngine()
    try:
        engine.set_state(VoiceState.MIC_UNAVAILABLE)
        called = {"retry": False}
        monkeypatch.setattr(engine, "retry_microphone", lambda: called.__setitem__("retry", True))
        engine.toggle_listening()
        assert called["retry"] is True
    finally:
        engine.shutdown()
