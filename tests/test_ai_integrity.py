"""
Tests for the AI decision-integrity fixes: no silent offline-brain
override of a real provider's tool decision, honest provider labeling,
and bounded conversation history. No real network calls — providers are
exercised via monkeypatched HTTP layers.
"""
import json



def test_mock_provider_not_labeled_anthropic_claude(qapp):
    from core.ai.mock_provider import MockJarvisProvider

    provider = MockJarvisProvider()
    assert provider.name != "Anthropic Claude"
    assert provider.name == "JARVIS Offline"


def test_claude_provider_fallback_honest_label(qapp):
    """When no Anthropic key is configured, the fallback must not claim to
    BE Anthropic Claude."""
    from core.ai.claude_provider import ClaudeProvider
    from app.config import config

    original = config.ANTHROPIC_API_KEY
    config.ANTHROPIC_API_KEY = ""
    try:
        provider = ClaudeProvider(api_key="")
        response = provider.generate_response("hello", [])
        assert response.provider_name != "Anthropic Claude"
    finally:
        config.ANTHROPIC_API_KEY = original


def test_opensource_provider_fallback_honest_label(qapp, monkeypatch):
    """Same bug existed independently in OpenSourceLLMProvider's fallback
    — its MockJarvisProvider instance also used to inherit the hardcoded
    'Anthropic Claude' label before mock_provider.py was fixed."""
    from core.ai.opensource_provider import OpenSourceLLMProvider

    provider = OpenSourceLLMProvider()
    monkeypatch.setattr(provider, "is_ollama_available", lambda: False)
    monkeypatch.setattr(provider, "_query_groq", lambda *a, **k: None)
    monkeypatch.setattr(provider, "_query_gemini", lambda *a, **k: None)

    response = provider.generate_response("hello", [])
    assert response.provider_name != "Anthropic Claude"


def test_gemini_no_tool_call_stays_no_tool_call(qapp, monkeypatch):
    """The core fix: when the real model's response has no [ACTION:...]
    tag, tool_calls must stay empty — never silently replaced by the
    offline regex brain's own guess."""
    from core.ai import gemini_provider as gp

    class _FakeResp:
        def __init__(self, payload):
            self._payload = payload

        def read(self):
            return json.dumps(self._payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    fake_payload = {
        "candidates": [{"content": {"parts": [{"text": "Sure, here is some information with no action."}]}}]
    }

    monkeypatch.setattr(gp.urllib.request, "urlopen", lambda req, timeout=7: _FakeResp(fake_payload))

    provider = gp.GeminiProvider(api_key="fake-key-for-test")
    # A prompt that the offline brain WOULD normally map to a tool call —
    # if the override were still present, this test would catch it.
    response = provider.generate_response("take a screenshot of my screen", [])
    assert response.tool_calls == []


def test_gemini_real_action_tag_still_parsed(qapp, monkeypatch):
    """Sanity check the fix didn't also break the legitimate path — when
    the model DOES emit an action tag, it must still be parsed."""
    from core.ai import gemini_provider as gp

    class _FakeResp:
        def __init__(self, payload):
            self._payload = payload

        def read(self):
            return json.dumps(self._payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    fake_payload = {
        "candidates": [{"content": {"parts": [{
            "text": 'Sure! [ACTION: {"tool": "take_screenshot", "args": {}}]'
        }]}}]
    }
    monkeypatch.setattr(gp.urllib.request, "urlopen", lambda req, timeout=7: _FakeResp(fake_payload))

    provider = gp.GeminiProvider(api_key="fake-key-for-test")
    response = provider.generate_response("take a screenshot", [])
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].tool_name == "take_screenshot"


def test_manager_conversation_history_is_bounded(qapp):
    from core.ai.manager import AIProviderManager
    from app.config import config

    original_max = getattr(config, "MAX_CONVERSATION_HISTORY_MESSAGES", 200)
    config.MAX_CONVERSATION_HISTORY_MESSAGES = 10
    try:
        mgr = AIProviderManager()
        for i in range(50):
            mgr.add_message("user", f"message {i}")
        assert len(mgr.conversation_history) <= 10
        # Must keep the MOST RECENT messages, not the oldest.
        assert mgr.conversation_history[-1].content == "message 49"
    finally:
        config.MAX_CONVERSATION_HISTORY_MESSAGES = original_max


def test_no_duplicate_gemini_provider_entries(qapp):
    """Regression test for the audit-found duplicate: two dropdown entries
    that silently called the exact same model under different labels."""
    from core.ai.manager import AIProviderManager

    mgr = AIProviderManager()
    models_seen = [(name, getattr(p, "model", None)) for name, p in mgr._providers.items() if "Gemini" in name]
    model_values = [m for _, m in models_seen]
    assert len(model_values) == len(set(model_values)), f"duplicate Gemini model entries: {models_seen}"
