"""
Base tool abstractions, execution results, and safety permission levels.
"""
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


class PermissionLevel(Enum):
    SAFE = "SAFE"                                   # Read-only or benign actions (take screenshot, read stats)
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED" # Actions altering system state (launch app, modify files)
    BLOCKED = "BLOCKED"                             # Unsafe or disallowed system destructive actions


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
        return PermissionLevel.SAFE

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool action."""
        pass
