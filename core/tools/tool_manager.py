"""
Tool Manager orchestrating registration, security checks, and execution.
"""
import concurrent.futures
import logging
from typing import Dict, Optional
from PySide6.QtCore import QObject, Signal

from core.tools.base import BaseTool, ToolResult
from core.tools.permission import permission_manager
from core.tools.system_tools import (
    TakeScreenshotTool,
    OpenAppTool,
    CloseApplicationTool,
    OpenPathTool,
    TypeTextTool,
    PressKeyTool,
    ClickScreenTool,
    ScrollScreenTool,
    OpenBrowserTool,
    GetSystemStatusTool,
    GetObservedIssuesTool,
    CreateFolderTool,
    SearchFilesTool,
    AnalyzeScreenTool,
    ControlWindowTool,
    VolumeControlTool,
    MediaControlTool,
    LockScreenTool,
    ControlBrowserTabsTool,
    RunClaudeCLITool,
)

logger = logging.getLogger("jarvis.tools")


class ToolManager(QObject):
    """
    Central registry for system automation tools.
    Enforces security gate: Tool Manager -> Permission Check -> Confirmation -> Execution.

    Every caller MUST go through execute_tool() — the normal LLM
    tool-calling loop, the intent-router fast path, any provider-level
    fallback, AutoFix, and manually-triggered UI buttons all call this same
    method, which is the only place permission_manager.check_permission()
    is invoked. There is no supported way to run a registered tool's
    execute() without passing through this gate (the one deliberate,
    documented exception — RunClaudeCLITool's own internal hard-wall via
    self_confirms — still requires its own confirmation regardless of how
    it's reached, see core/tools/system_tools.py).
    """

    tool_started = Signal(str)           # tool_name
    tool_finished = Signal(object)       # ToolResult
    tool_requires_approval = Signal(str, dict)  # tool_name, kwargs — informational only now;
                                                  # the actual approval already happened (or was
                                                  # denied) synchronously inside check_permission().

    # Tools whose execute() can legitimately take a while (window polling,
    # a network call, a human confirmation dialog) still need SOME upper
    # bound so one hung tool can't block every subsequently queued tool
    # call on the same worker thread forever. Each execute() call runs in
    # this pool so a timeout can actually be enforced from the outside —
    # Python has no safe way to force-kill a thread, so a timed-out call's
    # underlying thread may keep running in the background, but the CALLER
    # is never blocked past the deadline and always gets a clear result.
    _MAX_CONCURRENT_TOOL_EXECUTIONS = 4

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self._MAX_CONCURRENT_TOOL_EXECUTIONS, thread_name_prefix="ToolExec"
        )

    def _register_default_tools(self) -> None:
        defaults = [
            TakeScreenshotTool(),
            OpenAppTool(),
            CloseApplicationTool(),
            OpenPathTool(),
            TypeTextTool(),
            PressKeyTool(),
            ClickScreenTool(),
            ScrollScreenTool(),
            OpenBrowserTool(),
            ControlBrowserTabsTool(),
            GetSystemStatusTool(),
            GetObservedIssuesTool(),
            CreateFolderTool(),
            SearchFilesTool(),
            AnalyzeScreenTool(),
            ControlWindowTool(),
            VolumeControlTool(),
            MediaControlTool(),
            LockScreenTool(),
            RunClaudeCLITool(),
        ]
        for tool in defaults:
            self.register_tool(tool)

    def register_tool(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def execute_tool(self, name: str, **kwargs) -> ToolResult:
        tool = self.get_tool(name)
        if not tool:
            res = ToolResult(False, f"Tool '{name}' not found.", name, error="ToolNotFound")
            self.tool_finished.emit(res)
            return res

        # 1. Permission + Confirmation Gate (blocks synchronously until a
        #    real decision exists, for anything not unconditionally safe).
        has_permission = permission_manager.check_permission(tool, kwargs)
        if not has_permission:
            res = ToolResult(
                False,
                f"Action '{name}' was denied — it requires explicit user confirmation, "
                f"which was not granted.",
                name,
                needs_confirmation=False,  # the confirmation already happened (or timed out/was denied) above
                confirmation_prompt=f"Allow JARVIS to execute: {tool.description}?",
                error="permission_denied",
            )
            self.tool_requires_approval.emit(name, kwargs)
            self.tool_finished.emit(res)
            return res

        # 2. Bounded Execution
        self.tool_started.emit(name)
        try:
            future = self._executor.submit(tool.execute, **kwargs)
            try:
                result = future.result(timeout=tool.default_timeout_seconds)
            except concurrent.futures.TimeoutError:
                logger.error("Tool '%s' exceeded its %.0fs timeout", name, tool.default_timeout_seconds)
                result = ToolResult(
                    False,
                    f"Action '{name}' timed out after {tool.default_timeout_seconds:.0f}s.",
                    name,
                    error="timeout",
                )
        except Exception as e:
            logger.exception("Tool '%s' raised during execution", name)
            result = ToolResult(False, f"Execution failed: {str(e)}", name, error=str(e))

        self.tool_finished.emit(result)
        return result

    def shutdown(self) -> None:
        """Best-effort cleanup at app exit — does not forcibly kill any
        still-running tool thread (Python can't do that safely), just stops
        accepting new work."""
        try:
            self._executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass


# Global ToolManager instance
tool_manager = ToolManager()
