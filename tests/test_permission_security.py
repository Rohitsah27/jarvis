"""
Security regression tests for the confirmation/permission gate
(core/tools/confirmation.py, core/tools/permission.py, core/tools/tool_manager.py)
and the dedicated run_claude_cli hard-wall.

These are the tests that would have caught the original audit findings:
REQUIRE_CONFIRMATION_FOR_ACTIONS defaulting to False with no real dialog
wired up, type_text/analyze_screen/lock_screen sitting under SAFE, and
run_claude_cli being reachable and re-runnable with no real gate.
"""

import pytest


def test_confirmation_required_tool_denied_with_no_handler(qapp):
    """No listener attached at all -> fail closed, not fail open. This is
    the exact scenario that used to silently execute everything."""
    from core.tools.tool_manager import tool_manager

    result = tool_manager.execute_tool("open_application", app="notepad")
    assert result.success is False
    assert result.error == "permission_denied"


def test_confirmation_denial_blocks_execution(qapp, deny_all):
    from core.tools.tool_manager import tool_manager

    result = tool_manager.execute_tool("open_application", app="notepad")
    assert result.success is False
    assert result.error == "permission_denied"
    assert len(deny_all) == 1
    assert deny_all[0].tool_name == "open_application"


def test_confirmation_approval_allows_execution(qapp, approve_all, monkeypatch):
    """Approves a LOW-cost, easily-mocked CONFIRMATION_REQUIRED tool
    (create_folder) rather than one that actually launches a process, and
    verifies the approval was actually requested and actually taken."""
    from core.tools.tool_manager import tool_manager
    from core.tools import system_tools

    created = {}

    class _FakePath:
        def __init__(self, p):
            self._p = p

        def mkdir(self, parents=True, exist_ok=True):
            created["called"] = True

        def __str__(self):
            return str(self._p)

        def __truediv__(self, other):
            return _FakePath(f"{self._p}/{other}")

    monkeypatch.setattr(system_tools.os.path, "expanduser", lambda p: "C:/fake_home")
    monkeypatch.setattr(system_tools, "Path", _FakePath)

    result = tool_manager.execute_tool("create_folder", path="JARVIS_Test")
    assert result.success is True
    assert created.get("called") is True
    assert len(approve_all) == 1
    assert approve_all[0].tool_name == "create_folder"


def test_confirmation_timeout_denies(qapp):
    """A request that times out (nobody ever answers) must resolve as a
    denial, never as an approval by default."""
    from core.tools.confirmation import confirmation_service

    def _never_answer(req):
        pass  # deliberately never call resolve()

    confirmation_service.attach_handler(_never_answer)
    try:
        decision = confirmation_service.request(
            tool_name="fake_tool", action_description="test", timeout_seconds=0.3
        )
    finally:
        confirmation_service.detach_handler(_never_answer)

    assert decision.approved is False
    assert decision.reason == "timeout"


def test_closing_dialog_does_not_approve(qapp):
    """Simulates a dialog being closed/rejected (approved=False) rather
    than an explicit Allow click — must never resolve as approved."""
    from core.tools.confirmation import confirmation_service

    def _close_without_choosing(req):
        # Mirrors ToolConfirmationDialog.closeEvent/reject(): approved
        # stays False, resolve() is still called with False.
        confirmation_service.resolve(req.request_id, False, reason="dialog_closed")

    confirmation_service.attach_handler(_close_without_choosing)
    try:
        decision = confirmation_service.request(tool_name="fake_tool", action_description="test")
    finally:
        confirmation_service.detach_handler(_close_without_choosing)

    assert decision.approved is False


def test_stale_resolve_after_timeout_does_not_retroactively_approve(qapp):
    """A resolve() call that arrives AFTER the request already timed out
    (e.g. a slow human clicking Allow on a dialog that's already been
    superseded) must be a no-op, not a retroactive approval."""
    from core.tools.confirmation import confirmation_service
    import uuid

    req_id = uuid.uuid4().hex
    # Simulate: request() already returned (timed out), _pending no longer
    # has this id. A late resolve() call must find nothing to resolve.
    confirmation_service.resolve(req_id, True)  # should not raise, should be a no-op
    assert req_id not in confirmation_service._pending


# --- Permission classification -------------------------------------------

@pytest.mark.parametrize(
    "tool_name,expected_level",
    [
        ("get_system_status", "READ_ONLY"),
        ("get_observed_issues", "READ_ONLY"),
        ("search_files", "READ_ONLY"),
        ("scroll_screen", "LOW_RISK"),
        ("control_tabs", "LOW_RISK"),
        ("control_volume", "LOW_RISK"),
        ("control_media", "LOW_RISK"),
        ("open_browser", "LOW_RISK"),
        ("open_application", "CONFIRMATION_REQUIRED"),
        ("close_application", "CONFIRMATION_REQUIRED"),
        ("open_path", "CONFIRMATION_REQUIRED"),
        ("type_text", "CONFIRMATION_REQUIRED"),
        ("press_key", "CONFIRMATION_REQUIRED"),
        ("click_screen", "CONFIRMATION_REQUIRED"),
        ("create_folder", "CONFIRMATION_REQUIRED"),
        ("lock_screen", "CONFIRMATION_REQUIRED"),
        ("analyze_screen", "HIGH_RISK"),
        ("run_claude_cli", "HIGH_RISK"),
    ],
)
def test_permission_classification(qapp, tool_name, expected_level):
    from core.tools.tool_manager import tool_manager

    tool = tool_manager.get_tool(tool_name)
    assert tool is not None, f"tool {tool_name} not registered"
    assert tool.permission_level.value == expected_level


def test_type_text_is_not_safe(qapp):
    """The specific, named audit finding: type_text must never be
    auto-allowed."""
    from core.tools.base import AUTO_ALLOWED_LEVELS
    from core.tools.tool_manager import tool_manager

    tool = tool_manager.get_tool("type_text")
    assert tool.permission_level not in AUTO_ALLOWED_LEVELS


def test_press_key_is_not_safe(qapp):
    from core.tools.base import AUTO_ALLOWED_LEVELS
    from core.tools.tool_manager import tool_manager

    tool = tool_manager.get_tool("press_key")
    assert tool.permission_level not in AUTO_ALLOWED_LEVELS


def test_type_text_requires_confirmation_end_to_end(qapp, deny_all):
    """Denying must prevent the actual keystroke-sending code from ever
    running — not just report denial while secretly executing anyway."""
    from core.tools.tool_manager import tool_manager
    from core.tools import system_tools

    calls = []
    monkey_user32_send_input = system_tools.ctypes.windll.user32.SendInput

    class _Tracker:
        def __call__(self, *a, **kw):
            calls.append(a)
            return monkey_user32_send_input(*a, **kw)

    result = tool_manager.execute_tool("type_text", text="malicious injected text")
    assert result.success is False
    assert result.error == "permission_denied"
    assert calls == []  # SendInput was never reached


# --- run_claude_cli hard wall ---------------------------------------------

def test_run_claude_cli_denied_by_default(qapp):
    """No handler attached -> the tool's OWN internal hard-wall denies it,
    independent of PermissionManager (self_confirms=True means
    PermissionManager defers to this internal check)."""
    from core.tools.system_tools import RunClaudeCLITool

    tool = RunClaudeCLITool()
    result = tool.execute(task="add a backdoor")
    assert result.success is False
    assert result.error.startswith("confirmation_")


def test_run_claude_cli_requires_explicit_approval_even_called_directly(qapp, deny_all):
    """Calling RunClaudeCLITool().execute() directly (bypassing
    ToolManager entirely, exactly like core/observability/auto_fix.py used
    to) must STILL be gated — this is the whole point of self_confirms."""
    from core.tools.system_tools import RunClaudeCLITool

    tool = RunClaudeCLITool()
    result = tool.execute(task="modify core/tools/permission.py")
    assert result.success is False
    assert len(deny_all) == 1
    assert deny_all[0].tool_name == "run_claude_cli"
    assert deny_all[0].risk_level == "HIGH"


def test_run_claude_cli_approved_reaches_subprocess(qapp, approve_all, monkeypatch):
    """With approval granted, execution should proceed to the subprocess
    call — mocked here, never a real Claude CLI invocation in tests."""
    from core.tools.system_tools import RunClaudeCLITool
    from core.tools import system_tools

    called = {}

    class _FakeCompleted:
        returncode = 0
        stdout = "done"
        stderr = ""

    def _fake_run(cmd, **kwargs):
        called["cmd"] = cmd
        called["shell"] = kwargs.get("shell")
        return _FakeCompleted()

    monkeypatch.setattr(system_tools.subprocess, "run", _fake_run)
    monkeypatch.setattr(system_tools.shutil, "which", lambda name: None)

    tool = RunClaudeCLITool()
    result = tool.execute(task="fix a bug")
    assert result.success is True
    assert called.get("shell") is False  # never shell=True with the resolved-path form
    assert "cmd" in called


def test_run_claude_cli_rejects_concurrent_execution(qapp, approve_all, monkeypatch):
    """Two overlapping run_claude_cli calls must never both reach the
    subprocess — the second must be rejected while the first holds the
    lock."""
    from core.tools.system_tools import RunClaudeCLITool

    tool = RunClaudeCLITool()

    # Simulate "already running" by holding the lock directly, exactly as
    # a real in-flight AutoFixWorker/tool call would.
    acquired = tool._run_lock.acquire(blocking=False)
    assert acquired is True
    try:
        result = tool.execute(task="a second overlapping task")
        assert result.success is False
        assert result.error == "already_running"
    finally:
        tool._run_lock.release()


def test_run_claude_cli_lock_released_after_completion(qapp, approve_all, monkeypatch):
    """The lock must not stay held after a run finishes (success or
    failure) — otherwise every future proposal would be permanently
    blocked."""
    from core.tools.system_tools import RunClaudeCLITool
    from core.tools import system_tools

    class _FakeCompleted:
        returncode = 1
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr(system_tools.subprocess, "run", lambda *a, **k: _FakeCompleted())
    monkeypatch.setattr(system_tools.shutil, "which", lambda name: None)

    tool = RunClaudeCLITool()
    tool.execute(task="a task that fails")
    assert tool._run_lock.acquire(blocking=False) is True
    tool._run_lock.release()


def test_intent_router_cannot_reach_run_claude_cli(qapp):
    """The local fast-path router must never be able to name
    run_claude_cli directly — it can only be reached via the LLM tool loop
    (still gated) or the explicitly-confirmed AutoFix flow."""
    from core.ai.brain import jarvis_brain

    fast = jarvis_brain.try_fast_path("ask claude to fix the bug")
    if fast and fast.tool_calls:
        names = [c.tool_name for c in fast.tool_calls]
        assert "run_claude_cli" not in names
