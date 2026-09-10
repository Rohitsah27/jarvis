"""
Base tool abstractions, execution results, and safety permission levels.
"""
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


class PermissionLevel(Enum):
    """
    Authoritative risk classification for every tool. Replaces the old
    three-tier SAFE/CONFIRMATION_REQUIRED/BLOCKED model, which let several
    genuinely state-changing or privacy-sensitive tools (type_text,
    analyze_screen, lock_screen) hide under "SAFE" with zero human gate.

    READ_ONLY              Never touches system state or sends data anywhere
                            (get_system_status, search_files). Always allowed.
    LOW_RISK                Minor, easily-reversible, low-blast-radius state
                            change (scroll, switch tab, volume). Always allowed,
                            but distinct from READ_ONLY for auditing/logging.
    CONFIRMATION_REQUIRED   Real state change on the user's system. Requires
                            an explicit human decision via ConfirmationService
                            before every execution.
    HIGH_RISK                Sensitive, hard-to-reverse, or privacy-impacting
                            (uploads screen content to a cloud API, modifies
                            JARVIS's own source code). ALWAYS requires
                            confirmation — never eligible for any auto-allow
                            path, fast-path bypass, or config-based disable.
    BLOCKED                  Never executable, unconditionally.
    """
    READ_ONLY = "READ_ONLY"
    LOW_RISK = "LOW_RISK"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    HIGH_RISK = "HIGH_RISK"
    BLOCKED = "BLOCKED"


# Tiers that may execute without asking a human. Anything NOT in this set
# must go through ConfirmationService before BaseTool.execute() runs — this
# set is the single source of truth PermissionManager consults, so adding a
# new PermissionLevel value here is a deliberate, reviewable decision rather
# than something that can drift silently.
AUTO_ALLOWED_LEVELS = frozenset({PermissionLevel.READ_ONLY, PermissionLevel.LOW_RISK})

# Tiers that must NEVER be added to any "remember for session" / auto-allow
# list, regardless of future UI features — a HIGH_RISK tool is confirmed
# every single time, no exceptions.
ALWAYS_CONFIRM_LEVELS = frozenset({PermissionLevel.CONFIRMATION_REQUIRED, PermissionLevel.HIGH_RISK})


@dataclass
class ToolResult:
    success: bool
    output: str
    tool_name: str
    needs_confirmation: bool = False
    confirmation_prompt: str = ""
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    """Abstract interface for system control tools in JARVIS."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        pass

    @property
    def permission_level(self) -> PermissionLevel:
        """Default security safety level."""
        return PermissionLevel.READ_ONLY

    @property
    def self_confirms(self) -> bool:
        """
        True ONLY for a tool whose own execute() unconditionally performs
        its own confirmation_service.request() call before doing anything
        else, regardless of who calls it. When True, PermissionManager
        skips its own confirmation prompt for this tool (avoiding a
        duplicate dialog) and trusts the tool's execute() to be a real,
        unbypassable gate on its own — this is deliberately opt-in and
        used by exactly one tool today (run_claude_cli), which needs to
        stay gated even if invoked by a caller that bypasses ToolManager
        entirely (e.g. core/observability/auto_fix.py). A tool setting
        this to True without actually gating inside execute() would be a
        real security hole — treat this as a strong contract, not a
        convenience flag.
        """
        return False

    def permission_level_for(self, args: Dict[str, Any]) -> PermissionLevel:
        """
        Argument-aware override of `permission_level` — most tools don't need
        this (a single static level is enough), but a tool whose risk depends
        on WHICH action it's asked to perform (e.g. control_window's
        "close" vs. "minimize") can override this to return a stricter level
        for the dangerous branch without needing a separate tool class.
        Defaults to the static `permission_level`.
        """
        return self.permission_level

    def confirmation_summary(self, args: Dict[str, Any]) -> str:
        """
        Human-readable one-line description of what this specific
        invocation will do, shown in the confirmation dialog. Default
        falls back to `description`; tools taking risk-relevant arguments
        (a file path, an app name, text to type) should override this to
        surface the actual argument values, not just the tool's generic
        description — the whole point of the dialog is to show the user
        *this exact action* before it runs.
        """
        return self.description

    def confirmation_target(self, args: Dict[str, Any]) -> str:
        """Optional 'target' shown in the confirmation dialog (app/window/
        path this action applies to). Empty string if not applicable."""
        return ""

    @property
    def default_timeout_seconds(self) -> float:
        """
        Upper bound ToolManager enforces on this tool's execute() call.
        Most tools finish in well under a second; 15s covers slower ones
        (window-polling, a short network call) with margin. A tool whose
        own execute() also blocks on a human confirmation decision
        (self_confirms=True) must override this to also cover that wait —
        see RunClaudeCLITool/AnalyzeScreenTool.
        """
        return 15.0

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool action."""
        pass


class ToolTimeoutError(Exception):
    """Raised (internally, by ToolManager) when a tool's execute() exceeds
    its default_timeout_seconds. Never propagates out of ToolManager —
    it's converted into a normal, user-visible ToolResult failure."""
    pass
