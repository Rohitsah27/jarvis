"""
Observe Mode: structured capture of runtime errors, failed tool actions, AI
errors, STT/TTS failures, and unhandled exceptions — plus a way to explain
the most recent one in plain language when asked ("what problem did you
observe").

Storage is a JSON-lines file (logs/observed_issues.jsonl), matching the
project's existing preference for simple, inspectable, stdlib-only storage
(core/telemetry.py's rotating log, app/config.py's config.json) rather than
introducing a database dependency for what is, in practice, a small,
append-mostly log a human might also want to read directly.

This module only OBSERVES and EXPLAINS — it never modifies code or takes
action on its own. See core/observability/auto_fix.py for the explicit,
user-confirmed path that can request a code change.
"""
import json
import time
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QObject, Signal

_LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
_ISSUES_FILE = _LOG_DIR / "observed_issues.jsonl"

# Caps the file at a few hundred KB max — old issues are still useful
# history, but this is a debugging aid, not an audit log that needs to
# grow forever, and disk space on this machine is not to be spent lightly.
_MAX_ISSUES_KEPT = 500


@dataclass
class ObservedIssue:
    id: str
    timestamp: float
    category: str          # "unhandled_exception" | "tool_failure" | "ai_error" | "stt_error" | "tts_error" | "ui_issue"
    summary: str            # one-line, human-readable
    details: str = ""       # traceback / raw error text, may be long
    severity: str = "error"  # "info" | "warning" | "error" | "critical"
    source: str = ""        # module/function/tool name that raised it

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def readable_time(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp))


class ObserverService(QObject):
    """Global singleton. Import `observer` from this module — don't
    instantiate ObserverService directly, same convention as the other
    engine singletons in this project (kokoro_engine, stt_engine, ...)."""

    issue_observed = Signal(object)  # ObservedIssue — dashboard listens to this

    _instance: Optional["ObserverService"] = None

    def __init__(self):
        super().__init__()
        self._issues: List[ObservedIssue] = []
        self._next_id = 1
        self._load_existing()

    @classmethod
    def get_instance(cls) -> "ObserverService":
        if cls._instance is None:
            cls._instance = ObserverService()
        return cls._instance

    def _load_existing(self):
        """Reads prior issues back in at startup so 'last observed issue'
        survives a restart, capped to the most recent _MAX_ISSUES_KEPT."""
        if not _ISSUES_FILE.exists():
            return
        try:
            lines = _ISSUES_FILE.read_text(encoding="utf-8").splitlines()
            for line in lines[-_MAX_ISSUES_KEPT:]:
                if not line.strip():
                    continue
                data = json.loads(line)
                self._issues.append(ObservedIssue(**data))
            if self._issues:
                self._next_id = max(int(i.id) for i in self._issues) + 1
        except Exception as e:
            print(f"[ObserverService] Could not load prior issues: {e}")

    def record_issue(
        self, category: str, summary: str, details: str = "",
        severity: str = "error", source: str = "",
    ) -> ObservedIssue:
        """
        Records one observed problem. Never raises — a bug in the observer
        itself must not take down whatever called it (often already inside
        an exception handler). Returns the recorded issue so callers can
        reference its id (e.g. to later request a fix for it specifically).
        """
        issue = ObservedIssue(
            id=str(self._next_id), timestamp=time.time(), category=category,
            summary=summary[:300], details=details[:8000], severity=severity, source=source,
        )
        self._next_id += 1
        try:
            self._issues.append(issue)
            self._issues = self._issues[-_MAX_ISSUES_KEPT:]
            _LOG_DIR.mkdir(parents=True, exist_ok=True)
            with open(_ISSUES_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(issue.to_dict(), ensure_ascii=False) + "\n")
            print(f"[ObserverService] Observed [{severity}] {category}: {summary[:120]}")
            self.issue_observed.emit(issue)
        except Exception as e:
            print(f"[ObserverService] Failed to persist issue (still tracked in-memory): {e}")
        return issue

    def record_exception(self, exc: BaseException, category: str = "unhandled_exception", source: str = "") -> ObservedIssue:
        """Convenience wrapper: formats a caught exception's traceback for record_issue()."""
        summary = f"{type(exc).__name__}: {exc}"
        details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        return self.record_issue(category, summary, details, severity="error", source=source)

    def get_recent_issues(self, n: int = 10) -> List[ObservedIssue]:
        return list(reversed(self._issues[-n:]))

    def get_issue_by_id(self, issue_id: str) -> Optional[ObservedIssue]:
        for issue in self._issues:
            if issue.id == issue_id:
                return issue
        return None

    def get_last_issue(self) -> Optional[ObservedIssue]:
        return self._issues[-1] if self._issues else None

    def explain_last_issue(self) -> str:
        """
        Plain-language explanation + suggested fix for the most recent
        observed issue, in whatever language the app is currently
        configured to speak (Hindi by default, per FORCE_HINDI_ONLY_SPEECH)
        — generated on demand via the active LLM provider rather than for
        every recorded issue, since most issues are never asked about.
        """
        issue = self.get_last_issue()
        if issue is None:
            return self._no_issues_message()

        from app.config import config
        from core.ai.manager import ai_manager

        hindi_only = getattr(config, "FORCE_HINDI_ONLY_SPEECH", False)
        language_instruction = (
            "Reply in simple, conversational Hindi (Devanagari)."
            if hindi_only else
            "Reply in simple, plain English."
        )
        prompt = (
            f"{language_instruction} A desktop assistant app observed this problem:\n\n"
            f"Category: {issue.category}\n"
            f"Summary: {issue.summary}\n"
            f"Details:\n{issue.details[:2000]}\n\n"
            "In 2-4 short sentences: explain what likely went wrong in plain, "
            "non-technical language, and suggest one concrete fix or next step. "
            "Do not use code blocks or technical jargon a non-programmer wouldn't know."
        )
        try:
            response = ai_manager.active_provider.generate_response(prompt, [])
            explanation = (response.content or "").strip()
            if explanation:
                return explanation
        except Exception as e:
            print(f"[ObserverService] Explanation generation failed: {e}")

        # Fallback if the LLM call itself fails — still answer with something
        # concrete rather than silence.
        if hindi_only:
            return f"सर, मैंने एक समस्या देखी थी: {issue.summary}। इसे ठीक करने के लिए मुझसे कहें।"
        return f"Sir, I observed an issue: {issue.summary}. Ask me to look into a fix if you'd like."

    def _no_issues_message(self) -> str:
        from app.config import config
        if getattr(config, "FORCE_HINDI_ONLY_SPEECH", False):
            return "सर, अभी तक मुझे कोई समस्या नहीं दिखी है। सब कुछ सामान्य रूप से काम कर रहा है।"
        return "Sir, I haven't observed any problems yet. Everything looks normal."


# Global singleton
observer = ObserverService.get_instance()
