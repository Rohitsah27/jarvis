"""
ConfirmationService: the single, code-enforced gate every CONFIRMATION_REQUIRED
or HIGH_RISK tool call must pass through before core/tools/base.py's
BaseTool.execute() ever runs.

Design goal: the ENFORCEMENT lives here, not in the UI. The UI (a real Qt
dialog, wired in ui/components/confirmation_dialog.py + ui/main_window.py)
is just one possible answerer of a request this service issues — nothing
about the gate itself depends on a dialog existing. If no UI is ever wired
up (e.g. a headless test, or the app running before the main window exists),
every request times out and is DENIED by default — there is no code path
where "nobody answered" becomes an approval.

Thread-safety: tool execution happens on background QThreads
(ToolExecutionWorker). Qt dialogs must run on the GUI thread. This service
bridges the two using a plain threading.Event rather than Qt's
BlockingQueuedConnection machinery (which has PySide6 version quirks around
returning values across threads) — request() blocks the CALLING thread on
an Event; the GUI-thread handler calls resolve() once the user (or a test
double) has answered, which sets the Event. If request() and resolve() are
invoked from the same thread (e.g. a synchronous unit test, or a tool call
that happens to originate on the GUI thread itself), Qt's signal/slot
auto-connection resolves to a direct, synchronous call — the emit() call
itself runs the handler inline, before request() ever reaches event.wait(),
so there is no dependency on a running event loop for that case either.
"""
import threading
import uuid
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from PySide6.QtCore import QObject, Signal

DEFAULT_TIMEOUT_SECONDS = 30.0


@dataclass
class ConfirmationRequest:
    request_id: str
    tool_name: str
    action_description: str
    target: str
    important_args: str
    risk_level: str  # "LOW" | "MEDIUM" | "HIGH"
    timeout_seconds: float


@dataclass
class ConfirmationDecision:
    approved: bool
    # "user_approved" | "user_denied" | "dialog_closed" | "timeout" | "not_resolved"
    reason: str = "not_resolved"


class ConfirmationService(QObject):
    """Global singleton. Import `confirmation_service` from this module."""

    # Cross-thread safe: PySide6 auto-detects sender/receiver thread and
    # queues delivery onto the receiver's (GUI) thread's event loop when
    # they differ, or calls directly/synchronously when they're the same.
    confirmation_requested = Signal(object)  # ConfirmationRequest

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._pending: Dict[str, Tuple[threading.Event, list]] = {}
        self._lock = threading.Lock()
        self.timeout_seconds = DEFAULT_TIMEOUT_SECONDS
        # Explicit listener tracking, NOT QObject.receivers() — that method
        # requires an old-style C++ signal signature string in this PySide6
        # version and raises TypeError when passed a bound SignalInstance;
        # a naive `except Exception: return False` around it would silently
        # ALWAYS report "no listener", which would make every confirmation
        # request fail-closed even with a real dialog connected — safe
        # (fail-closed) but silently non-functional. Callers register via
        # attach_handler()/detach_handler() instead of connecting directly.
        self._listener_count = 0
        # If True, a request with no listener connected at all resolves
        # instantly to a denial instead of waiting out the full timeout —
        # avoids a needless 30s hang in contexts where no UI will ever
        # exist (e.g. a script importing this module directly). Tests that
        # want to exercise the real timeout path can call request() with an
        # explicit timeout_seconds override instead.
        self.deny_immediately_if_no_receivers = True

    def attach_handler(self, slot) -> None:
        """Connect a GUI-thread (or test) handler to confirmation_requested
        AND mark that a listener now exists. Use this instead of calling
        .confirmation_requested.connect(slot) directly — see has_listener()."""
        self.confirmation_requested.connect(slot)
        self._listener_count += 1

    def detach_handler(self, slot) -> None:
        try:
            self.confirmation_requested.disconnect(slot)
        finally:
            self._listener_count = max(0, self._listener_count - 1)

    def has_listener(self) -> bool:
        return self._listener_count > 0

    def request(
        self,
        tool_name: str,
        action_description: str,
        target: str = "",
        important_args: str = "",
        risk_level: str = "MEDIUM",
        timeout_seconds: Optional[float] = None,
    ) -> ConfirmationDecision:
        """
        Blocks the CALLING thread until a human decision is made, the
        request times out, or (if nothing is listening at all) an instant
        default denial is returned. Never raises — a bug in the
        confirmation plumbing itself must fail CLOSED (deny), never open.
        """
        effective_timeout = self.timeout_seconds if timeout_seconds is None else timeout_seconds

        if self.deny_immediately_if_no_receivers and not self.has_listener():
            return ConfirmationDecision(approved=False, reason="no_confirmation_ui")

        req_id = uuid.uuid4().hex
        event = threading.Event()
        box = [ConfirmationDecision(approved=False, reason="not_resolved")]
        with self._lock:
            self._pending[req_id] = (event, box)

        req = ConfirmationRequest(
            request_id=req_id,
            tool_name=tool_name,
            action_description=action_description,
            target=target,
            important_args=important_args,
            risk_level=risk_level,
            timeout_seconds=effective_timeout,
        )

        try:
            self.confirmation_requested.emit(req)
        except Exception:
            with self._lock:
                self._pending.pop(req_id, None)
            return ConfirmationDecision(approved=False, reason="dispatch_error")

        got_answer = event.wait(effective_timeout)

        with self._lock:
            _, box2 = self._pending.pop(req_id, (None, box))

        if not got_answer:
            return ConfirmationDecision(approved=False, reason="timeout")
        return box2[0]

    def resolve(self, request_id: str, approved: bool, reason: str = "") -> None:
        """
        Call this ONLY from the code that actually obtained a human (or,
        in tests, simulated) decision. A request_id that has already timed
        out or been resolved is a silent no-op — this is deliberate: a
        stale "Allow" click arriving after the calling thread already gave
        up and moved on must NOT retroactively approve anything.
        """
        with self._lock:
            entry = self._pending.get(request_id)
        if not entry:
            return
        event, box = entry
        if not reason:
            reason = "user_approved" if approved else "user_denied"
        box[0] = ConfirmationDecision(approved=bool(approved), reason=reason)
        event.set()


# Global singleton
confirmation_service = ConfirmationService()
