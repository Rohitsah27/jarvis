"""
Tests for ToolManager's uniform execution timeout and OpenAppTool's
shell-injection defenses. Never runs a real destructive payload against the
machine — subprocess/os.startfile calls are mocked.
"""
import time

import pytest


def test_tool_manager_enforces_timeout(qapp, monkeypatch):
    from core.tools.tool_manager import tool_manager
    from core.tools.base import BaseTool, PermissionLevel, ToolResult

    class _SlowTool(BaseTool):
        @property
        def name(self):
            return "slow_test_tool"

        @property
        def description(self):
            return "sleeps forever for timeout testing"

        @property
        def permission_level(self):
            return PermissionLevel.READ_ONLY

        @property
        def default_timeout_seconds(self):
            return 0.3

        def execute(self, **kwargs):
            time.sleep(5)
            return ToolResult(True, "should never get here", self.name)

    tool_manager.register_tool(_SlowTool())
    try:
        start = time.perf_counter()
        result = tool_manager.execute_tool("slow_test_tool")
        elapsed = time.perf_counter() - start
        assert result.success is False
        assert result.error == "timeout"
        assert elapsed < 2.0  # bounded by the tool's 0.3s timeout, not the 5s sleep
    finally:
        tool_manager._tools.pop("slow_test_tool", None)


def test_tool_manager_survives_tool_exception(qapp):
    """A tool that raises must produce a normal failed ToolResult, never
    take down the caller."""
    from core.tools.tool_manager import tool_manager
    from core.tools.base import BaseTool, PermissionLevel

    class _BrokenTool(BaseTool):
        @property
        def name(self):
            return "broken_test_tool"

        @property
        def description(self):
            return "always raises"

        @property
        def permission_level(self):
            return PermissionLevel.READ_ONLY

        def execute(self, **kwargs):
            raise RuntimeError("boom")

    tool_manager.register_tool(_BrokenTool())
    try:
        result = tool_manager.execute_tool("broken_test_tool")
        assert result.success is False
        assert "boom" in (result.error or "") or "boom" in result.output
    finally:
        tool_manager._tools.pop("broken_test_tool", None)


def test_unknown_tool_returns_error_not_exception(qapp):
    from core.tools.tool_manager import tool_manager

    result = tool_manager.execute_tool("this_tool_does_not_exist")
    assert result.success is False
    assert result.error == "ToolNotFound"


# --- OpenAppTool shell-injection defenses ---------------------------------

@pytest.mark.parametrize("malicious_name", [
    "notepad & calc",
    "notepad && del C:\\important",
    "notepad | calc",
    "notepad %USERPROFILE%",
    "notepad^&calc",
    'notepad" & calc & echo "',
])
def test_open_app_rejects_shell_metacharacters(qapp, malicious_name, monkeypatch, approve_all):
    from core.tools.system_tools import OpenAppTool
    from core.tools import system_tools as st

    subprocess_calls = []
    startfile_calls = []
    monkeypatch.setattr(st.subprocess, "Popen", lambda *a, **k: subprocess_calls.append((a, k)))
    monkeypatch.setattr(st.os, "startfile", lambda target: startfile_calls.append(target))
    monkeypatch.setattr(st, "_wait_for_window_and_focus", lambda *a, **k: False)

    tool = OpenAppTool()
    result = tool.execute(app=malicious_name)

    assert result.success is False
    assert result.error == "unsafe_characters"
    # Neither launch path was ever reached with the malicious string.
    assert subprocess_calls == []
    assert startfile_calls == []


def test_open_app_shell_is_never_true(qapp, monkeypatch):
    """Even on the fallback path (os.startfile fails), the cmd invocation
    must use shell=False."""
    from core.tools.system_tools import OpenAppTool
    from core.tools import system_tools as st

    calls = []

    def _fake_startfile(target):
        raise OSError("not found")

    def _fake_popen(cmd, **kwargs):
        calls.append(kwargs)
        class _P:
            pass
        return _P()

    monkeypatch.setattr(st.os, "startfile", _fake_startfile)
    monkeypatch.setattr(st.subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(st, "_wait_for_window_and_focus", lambda *a, **k: False)

    tool = OpenAppTool()
    tool.execute(app="notepad")

    assert len(calls) == 1
    assert calls[0].get("shell") is False
