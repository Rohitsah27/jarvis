"""
Tests for the screen-analysis privacy fixes: screenshots go to the OS temp
directory (never the visible Desktop), are always cleaned up, cloud upload
requires consent, and the YouTube URL resolver only ever fetches a real
YouTube URL (not a lookalike/substring match).
"""
import tempfile
from pathlib import Path

import pytest


def test_capture_screenshot_uses_temp_dir_not_desktop(qapp, monkeypatch):
    from core.system.screen_analyzer import ScreenAnalyzer

    saved_paths = []

    class _FakePixmap:
        def save(self, path, fmt):
            saved_paths.append(path)
            Path(path).write_bytes(b"fake-png-bytes")
            return True

    class _FakeScreen:
        def grabWindow(self, wid):
            return _FakePixmap()

    monkeypatch.setattr(
        "core.system.screen_analyzer.QGuiApplication.primaryScreen", staticmethod(lambda: _FakeScreen())
    )
    monkeypatch.setattr("core.system.screen_analyzer.HAS_QT_GUI", True)

    path = ScreenAnalyzer.capture_screenshot()
    assert path is not None
    assert str(Path(tempfile.gettempdir())) in path
    home_desktop = str(Path.home() / "Desktop")
    assert home_desktop not in path
    Path(path).unlink(missing_ok=True)


def test_cleanup_screenshot_removes_file(qapp, tmp_path):
    from core.system.screen_analyzer import ScreenAnalyzer

    f = tmp_path / "jarvis_vision_test.png"
    f.write_bytes(b"data")
    assert f.exists()
    ScreenAnalyzer._cleanup_screenshot(str(f))
    assert not f.exists()


def test_cleanup_screenshot_never_raises_on_missing_file(qapp):
    from core.system.screen_analyzer import ScreenAnalyzer
    # Must not raise even if the path never existed / was already deleted.
    ScreenAnalyzer._cleanup_screenshot("C:/does/not/exist/nope.png")
    ScreenAnalyzer._cleanup_screenshot(None)


def test_analyze_screen_screenshot_always_deleted(qapp, monkeypatch, tmp_path):
    """Whole analyze_screen() call, mocked at the capture/vision boundary —
    verifies the finally-block cleanup actually runs."""
    from core.system import screen_analyzer as sa

    fake_shot = tmp_path / "jarvis_vision_fake.png"
    fake_shot.write_bytes(b"data")

    monkeypatch.setattr(sa.ScreenAnalyzer, "get_foreground_window", staticmethod(lambda: None))
    monkeypatch.setattr(sa.ScreenAnalyzer, "get_visible_windows", classmethod(lambda cls: []))
    monkeypatch.setattr(sa.ScreenAnalyzer, "capture_screenshot", staticmethod(lambda save_path=None: str(fake_shot)))
    monkeypatch.setattr(sa, "_query_screen_vision", lambda path, q: "a fake vision answer")

    result = sa.ScreenAnalyzer.analyze_screen("what is on screen", allow_cloud=True)
    assert result["answer"] == "a fake vision answer"
    assert not fake_shot.exists()


def test_analyze_screen_no_cloud_call_without_consent(qapp, monkeypatch, tmp_path):
    """allow_cloud=False must mean _query_screen_vision is never invoked —
    no screenshot pixels reach any network call."""
    from core.system import screen_analyzer as sa

    fake_shot = tmp_path / "jarvis_vision_fake2.png"
    fake_shot.write_bytes(b"data")

    called = {"cloud": False}

    def _fake_vision(path, q):
        called["cloud"] = True
        return "should never be called"

    monkeypatch.setattr(sa.ScreenAnalyzer, "get_foreground_window", staticmethod(lambda: None))
    monkeypatch.setattr(sa.ScreenAnalyzer, "get_visible_windows", classmethod(lambda cls: []))
    monkeypatch.setattr(sa.ScreenAnalyzer, "capture_screenshot", staticmethod(lambda save_path=None: str(fake_shot)))
    monkeypatch.setattr(sa, "_query_screen_vision", _fake_vision)

    sa.ScreenAnalyzer.analyze_screen("what is on screen", allow_cloud=False)
    assert called["cloud"] is False
    assert not fake_shot.exists()


def test_analyze_screen_tool_asks_consent_once_then_persists(qapp, monkeypatch):
    """First call with no prior consent decision must ask via
    confirmation_service; the decision must be written to config and
    reused (not asked again) on a second call."""
    from core.tools.system_tools import AnalyzeScreenTool
    from core.tools.confirmation import confirmation_service
    from app.config import config
    from core.system import screen_analyzer as sa

    original_consent = config.SCREEN_ANALYSIS_CLOUD_CONSENT
    config.SCREEN_ANALYSIS_CLOUD_CONSENT = None
    monkeypatch.setattr(config, "save_to_json", lambda: True)

    asked = []

    def _approve(req):
        asked.append(req)
        confirmation_service.resolve(req.request_id, True)

    monkeypatch.setattr(sa.ScreenAnalyzer, "analyze_screen", classmethod(
        lambda cls, query="", allow_cloud=True: {"answer": "ok", "allow_cloud_seen": allow_cloud}
    ))

    try:
        confirmation_service.attach_handler(_approve)
        tool = AnalyzeScreenTool()
        tool.execute(query="what's on screen")
        assert len(asked) == 1  # consent was asked
        assert config.SCREEN_ANALYSIS_CLOUD_CONSENT is True

        result2 = tool.execute(query="what's on screen again")
        assert len(asked) == 1  # NOT asked a second time
        assert result2.success is True
    finally:
        confirmation_service.detach_handler(_approve)
        config.SCREEN_ANALYSIS_CLOUD_CONSENT = original_consent


# --- YouTube URL validation ------------------------------------------------

@pytest.mark.parametrize("url", [
    "https://www.youtube.com/results?search_query=test",
    "https://youtube.com/results?search_query=abc",
])
def test_youtube_url_validation_accepts_real_youtube(qapp, url):
    from core.tools.system_tools import _is_safe_youtube_search_url
    assert _is_safe_youtube_search_url(url) is True


@pytest.mark.parametrize("url", [
    "https://youtube.com.attacker.com/results?search_query=x",
    "https://attacker.com/?x=youtube.com/results?search_query=y",
    "http://169.254.169.254/?youtube.com/results?search_query=z",
    "https://evil.com/youtube.com/results?search_query=q",
    "ftp://www.youtube.com/results?search_query=q",
    "https://www.youtube.com/watch?v=abc123",  # real host, wrong path
])
def test_youtube_url_validation_rejects_lookalikes(qapp, url):
    from core.tools.system_tools import _is_safe_youtube_search_url
    assert _is_safe_youtube_search_url(url) is False


def test_resolve_youtube_direct_url_never_fetches_malicious_url(qapp, monkeypatch):
    from core.tools import system_tools as st

    fetched = []

    def _fake_urlopen(req, timeout=None):
        fetched.append(req.full_url if hasattr(req, "full_url") else str(req))
        raise AssertionError("should never be called for a non-YouTube URL")

    monkeypatch.setattr(st.urllib.request, "urlopen", _fake_urlopen)

    malicious = "https://attacker.com/?x=youtube.com/results?search_query=y"
    result = st._resolve_youtube_direct_url(malicious)
    assert result == malicious  # returned unchanged, never fetched
    assert fetched == []
