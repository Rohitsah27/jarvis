"""
Security Permission Manager ensuring safe autonomous computer control.
Enforces the workflow: AI -> Tool Manager -> Permission Check -> Confirmation -> Windows Action.

This is the ONLY place a tool's permission tier is evaluated. Every caller of
ToolManager.execute_tool() — the normal LLM tool-calling loop, the
intent_router fast path, any provider-level fallback, AutoFix, or a UI
button calling execute_tool() directly — goes through this same check. There
is no way for a CONFIRMATION_REQUIRED or HIGH_RISK tool to run without a real
answer from ConfirmationService: previously this class could return True
without ever asking anyone (REQUIRE_CONFIRMATION_FOR_ACTIONS=False, or a
tool sitting in a hardcoded auto-allow set); now the tier itself decides
whether a human decision is required, and if it is, that decision is
actually obtained here, synchronously, before returning.
"""
import logging
from typing import Dict, Optional

from PySide6.QtCore import QObject, Signal

from core.tools.base import BaseTool, PermissionLevel, AUTO_ALLOWED_LEVELS
from core.tools.confirmation import confirmation_service, ConfirmationDecision

logger = logging.getLogger("jarvis.permission")


class PermissionManager(QObject):
    """
    Evaluates security risk of actions before execution and, for anything
    that isn't unconditionally safe, blocks on a real human confirmation
    decision via ConfirmationService before authorizing execution.
    """

    # Still emitted for observability/logging purposes (e.g. the activity
    # log can show "JARVIS asked for permission to X"), but nothing in this
    # class's own control flow depends on anyone being connected to these —
    # the actual gating happens synchronously inside check_permission()
    # itself via confirmation_service.request().
    confirmation_needed = Signal(str, str, object)  # tool_name, prompt_message, decision
    permission_denied = Signal(str, str)             # tool_name, reason

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        # NOTE: REQUIRE_CONFIRMATION_FOR_ACTIONS no longer has any way to
        # disable confirmation for CONFIRMATION_REQUIRED/HIGH_RISK tools —
        # that flag was the root cause of every tool in that tier executing
        # unconditionally. The permission TIER itself now decides whether a
        # human decision is required; there is no global override.
        pass

    def check_permission(self, tool: BaseTool, args: Dict) -> bool:
        """
        Determines whether a tool call is authorized to run. Returns True
        only if the tool's tier is unconditionally safe, OR a human
        explicitly approved this specific call via ConfirmationService.
        This call blocks (up to ConfirmationService's timeout) when a
        decision must actually be obtained — that is intentional: the
        calling thread genuinely should not proceed until the human has
        answered.
        """
        level = tool.permission_level_for(args)

        if level == PermissionLevel.BLOCKED:
            logger.warning("Blocked tool call rejected: %s", tool.name)
            self.permission_denied.emit(
                tool.name, f"Security protocol: '{tool.name}' is categorized as BLOCKED."
            )
            return False

        if level in AUTO_ALLOWED_LEVELS:
            return True

        if tool.self_confirms:
            # This tool's own execute() unconditionally gates itself via
            # confirmation_service — asking again here would show the user
            # two separate dialogs for one action. Trusting this requires
            # BaseTool.self_confirms's contract to actually hold; see its
            # docstring. Still logged for observability.
            logger.info("Deferring confirmation to self-confirming tool: %s", tool.name)
            return True

        # CONFIRMATION_REQUIRED or HIGH_RISK from here on — always ask.
        summary = tool.confirmation_summary(args)
        target = tool.confirmation_target(args)
        risk_str = "HIGH" if level == PermissionLevel.HIGH_RISK else "MEDIUM"
        important_args = ", ".join(f"{k}={v!r}" for k, v in args.items()) if args else ""

        decision: ConfirmationDecision = confirmation_service.request(
            tool_name=tool.name,
            action_description=summary,
            target=target,
            important_args=important_args,
            risk_level=risk_str,
        )

        if decision.approved:
            logger.info("Tool call approved: %s (reason=%s)", tool.name, decision.reason)
            self.confirmation_needed.emit(tool.name, summary, decision)
            return True

        logger.info("Tool call denied: %s (reason=%s)", tool.name, decision.reason)
        self.permission_denied.emit(tool.name, decision.reason)
        return False


# Global singleton instance
permission_manager = PermissionManager()
