"""
Security Permission Manager ensuring safe autonomous computer control.
Enforces the workflow: AI -> Tool Manager -> Permission Check -> Windows Action.
"""
from typing import Dict, Optional, Callable
from PySide6.QtCore import QObject, Signal
from core.tools.base import BaseTool, PermissionLevel, ToolResult


from app.config import config


class PermissionManager(QObject):
    """
    Evaluates security risk of actions before execution.
    Can request explicit user confirmation via dialog or toast notification.
    """

    confirmation_needed = Signal(str, str, object)  # tool_name, prompt_message, callback_fn
    permission_denied = Signal(str, str)             # tool_name, reason

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._require_confirmations = config.REQUIRE_CONFIRMATION_FOR_ACTIONS
        self._auto_allowed_tools = {"get_system_status", "take_screenshot"}

    @property
    def require_confirmations(self) -> bool:
        return self._require_confirmations

    @require_confirmations.setter
    def require_confirmations(self, val: bool) -> None:
        self._require_confirmations = val

    def check_permission(self, tool: BaseTool, args: Dict) -> bool:
        """
        Determines whether tool can run immediately or requires user approval.
        Returns True if authorized immediately, False if blocked or pending.
        """
        if tool.permission_level == PermissionLevel.BLOCKED:
            self.permission_denied.emit(
                tool.name, f"Security protocol: '{tool.name}' is categorized as BLOCKED."
            )
            return False

        if tool.permission_level == PermissionLevel.SAFE or tool.name in self._auto_allowed_tools:
            return True

        # If confirmation is disabled globally
        if not self._require_confirmations:
            return True

        return False


# Global singleton instance
permission_manager = PermissionManager()
