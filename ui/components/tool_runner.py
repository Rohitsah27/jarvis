"""
Shared off-GUI-thread tool execution helper for simple UI buttons.

Several pages (Apps, Browser, Control) used to call
tool_manager.execute_tool(...) directly inside a button's clicked handler —
synchronously, on the GUI thread. For a SAFE tool that finishes instantly
this was harmless; for anything that polls for a window, makes a network
call, or (now that the real confirmation system exists) shows a modal
approval dialog, it freezes the whole window for the duration with zero
loading indicator and the result was silently discarded either way.

run_tool_async() runs the call on a short-lived QThread and reports the
ToolResult back via a callback invoked on the GUI thread (Qt queues the
signal delivery automatically), so the window stays responsive and the
caller can actually show success/failure instead of dropping it on the
floor.
"""
from typing import Any, Callable, Optional

from PySide6.QtCore import QThread, Signal, QObject

from core.tools.tool_manager import tool_manager
from core.tools.base import ToolResult


class _ToolRunnerWorker(QThread):
    finished_result = Signal(object)  # ToolResult

    def __init__(self, tool_name: str, kwargs: dict, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._tool_name = tool_name
        self._kwargs = kwargs

    def run(self):
        try:
            result = tool_manager.execute_tool(self._tool_name, **self._kwargs)
        except Exception as e:
            result = ToolResult(False, f"Execution failed: {e}", self._tool_name, error=str(e))
        self.finished_result.emit(result)


def run_tool_async(
    owner: QObject,
    tool_name: str,
    on_result: Optional[Callable[[ToolResult], None]] = None,
    **kwargs: Any,
) -> _ToolRunnerWorker:
    """
    Fires tool_name off the GUI thread. `owner` must be a long-lived QObject
    (typically the page instance) — the worker is parented to it AND held
    in owner._tool_runners so it isn't garbage-collected mid-run (a bare
    local QThread can be destroyed by Python's GC while Qt still considers
    it running, which aborts the thread silently). `on_result`, if given,
    is called with the ToolResult once execution finishes — safe to touch
    widgets from it, since Qt delivers the signal on the GUI thread.
    """
    worker = _ToolRunnerWorker(tool_name, kwargs, owner)

    if not hasattr(owner, "_tool_runners"):
        owner._tool_runners = []
    owner._tool_runners.append(worker)

    def _cleanup(result):
        try:
            if on_result:
                on_result(result)
        finally:
            if worker in owner._tool_runners:
                owner._tool_runners.remove(worker)

    worker.finished_result.connect(_cleanup)
    worker.start()
    return worker
