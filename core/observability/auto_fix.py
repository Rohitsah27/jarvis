"""
Permission-Based Auto-Update flow.

The only path in this app that can change JARVIS's own code, and it is
DELIBERATELY NOT reachable through the normal LLM tool-calling loop — it
never runs because a model "decided" to. It only ever runs because:
  1. An issue was observed, AND
  2. JARVIS explicitly asked "Should I ask Claude to fix this?", AND
  3. THIS turn's user reply is a plain yes to THAT specific question.

Any other input while a confirmation is pending cancels it rather than
guessing — see AutoFixManager.handle_reply().

After Claude Code runs, "verify the fix" means literally re-running this
project's own regression suite (tests/test_components.py) and reporting
whether it still passes — not just trusting Claude's own summary of what
it did.
"""
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

from PySide6.QtCore import QThread, Signal

from core.observability.observer import ObservedIssue, observer
from core.observability.task_queue import FixTask, task_queue

_PROJECT_DIR = Path(__file__).resolve().parent.parent.parent

_AFFIRMATIVE = {
    "yes", "yeah", "yep", "sure", "ok", "okay", "go ahead", "do it", "please do",
    "haan", "han", "haanji", "theek hai", "thik hai", "kar do", "kar dijiye", "kar de",
    "chalo", "बिल्कुल", "हां", "हाँ", "ठीक है", "कर दो", "कर दीजिए",
}
_NEGATIVE = {
    "no", "nope", "don't", "dont", "cancel", "stop", "nahi", "nahin", "mat karo",
    "रहने दो", "नहीं", "मत करो", "रुको",
}


def _is_affirmative(text: str) -> bool:
    t = text.strip().lower().strip(".!?")
    return t in _AFFIRMATIVE or any(t == a or t.startswith(a + " ") for a in _AFFIRMATIVE)


def _is_negative(text: str) -> bool:
    t = text.strip().lower().strip(".!?")
    return t in _NEGATIVE or any(t == n or t.startswith(n + " ") for n in _NEGATIVE)


class AutoFixWorker(QThread):
    """Runs the actual Claude CLI call + verification off the GUI thread —
    this can legitimately take from several seconds to a few minutes."""

    finished_fix = Signal(object, bool, str)  # FixTask, success, report_text

    def __init__(self, task: FixTask, parent=None):
        super().__init__(parent)
        self.task = task

    def run(self):
        task_queue.set_status(self.task.id, "running")
        success, report = AutoFixManager.execute_fix(self.task)
        task_queue.set_status(self.task.id, "completed" if success else "failed", report)
        self.finished_fix.emit(self.task, success, report)


class AutoFixManager:
    """Not a QObject itself — holds the one piece of conversational state
    (which issue, if any, is awaiting a yes/no) and the logic to act on a
    reply. main_window.py owns creating/connecting the AutoFixWorker."""

    def __init__(self):
        self._pending_issue_id: Optional[str] = None
        self._pending_task_id: Optional[str] = None

    def is_awaiting_confirmation(self) -> bool:
        return self._pending_issue_id is not None

    def propose_fix(self, issue: ObservedIssue) -> str:
        """Call this to ask the user about the most recently observed
        issue. Returns the exact question to speak/display — does NOT
        touch any code yet."""
        description = self.build_task_description(issue)
        task = task_queue.create_task(issue_id=issue.id, description=description)
        self._pending_issue_id = issue.id
        self._pending_task_id = task.id
        return "Should I ask Claude to fix this?"

    def cancel_pending(self, reason: str = "declined"):
        if self._pending_task_id:
            task_queue.set_status(self._pending_task_id, "rejected", reason)
        self._pending_issue_id = None
        self._pending_task_id = None

    def handle_reply(self, text: str) -> Optional[Tuple[bool, Optional[FixTask]]]:
        """
        Call this with the user's very next utterance while a confirmation
        is pending. Returns:
          - None if the reply isn't a clear yes/no (caller should treat
            this as a cancellation — see the note in the module docstring:
            anything other than a plain yes does NOT proceed).
          - (True, task) if approved — caller should start an AutoFixWorker
            on `task`.
          - (False, None) if declined.
        Clears the pending state either way (a stale "yes" answering last
        week's question would be exactly the kind of silent, un-asked-for
        code change this whole design exists to prevent).
        """
        if not self.is_awaiting_confirmation():
            return None

        task_id = self._pending_task_id
        approved: Optional[bool]
        if _is_affirmative(text):
            approved = True
        elif _is_negative(text):
            approved = False
        else:
            approved = None  # ambiguous — treated as decline, not a guess

        self._pending_issue_id = None
        self._pending_task_id = None

        if approved is True:
            task_queue.set_status(task_id, "approved")
            task = next((t for t in task_queue.get_recent_tasks(50) if t.id == task_id), None)
            return (True, task)

        task_queue.set_status(task_id, "rejected", "user declined" if approved is False else "unclear reply, treated as decline")
        return (False, None)

    @staticmethod
    def build_task_description(issue: ObservedIssue) -> str:
        """A task description Claude Code can act on without needing the
        conversation history — includes exactly what was observed."""
        details = issue.details[:1500]
        return (
            f"JARVIS (this project) observed a real runtime problem during normal use. "
            f"Investigate the root cause and fix it — do not just silence or catch the "
            f"symptom.\n\n"
            f"Category: {issue.category}\n"
            f"Summary: {issue.summary}\n"
            f"Source: {issue.source or 'unknown'}\n"
            f"Details/traceback:\n{details}\n\n"
            f"After fixing, make sure `python tests/test_components.py` still passes."
        )

    @staticmethod
    def execute_fix(task: FixTask) -> Tuple[bool, str]:
        """
        BLOCKING — run this from AutoFixWorker, never on the GUI thread.
        Invokes the existing RunClaudeCLITool directly (bypassing the LLM's
        own tool-selection — this call site is the only thing deciding to
        run it, per the module's safety design), then re-runs this
        project's regression suite as the actual verification step.
        """
        from core.tools.system_tools import RunClaudeCLITool

        start_t = time.perf_counter()
        cli_result = RunClaudeCLITool().execute(task=task.description)
        claude_elapsed = time.perf_counter() - start_t

        if not cli_result.success:
            return False, f"Claude CLI call failed: {cli_result.output}"

        verify_ok, verify_output = AutoFixManager._verify_with_test_suite()
        elapsed_total = time.perf_counter() - start_t

        if verify_ok:
            return True, (
                f"Claude finished in {claude_elapsed:.1f}s. Verification (test suite) passed. "
                f"Total time: {elapsed_total:.1f}s.\nClaude's summary: {cli_result.output[:400]}"
            )
        return False, (
            f"Claude made changes in {claude_elapsed:.1f}s, but the regression suite "
            f"failed afterward — treat this fix as NOT verified.\n"
            f"Test output (tail): {verify_output[-800:]}"
        )

    @staticmethod
    def _verify_with_test_suite() -> Tuple[bool, str]:
        """Runs the project's existing regression suite as the objective
        'did this actually work' check — not just trusting Claude's own
        report of what it changed."""
        try:
            result = subprocess.run(
                [sys.executable, "tests/test_components.py"],
                cwd=str(_PROJECT_DIR), capture_output=True, text=True,
                timeout=120, encoding="utf-8", errors="replace",
            )
            output = (result.stdout or "") + (result.stderr or "")
            passed = result.returncode == 0 and "ALL AUTOMATED TESTS PASSED" in output
            return passed, output
        except Exception as e:
            return False, f"Could not run verification suite: {e}"


# Global singleton
auto_fix_manager = AutoFixManager()
