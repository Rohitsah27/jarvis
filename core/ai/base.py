"""
Abstract base class and models for AI providers in JARVIS.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime


@dataclass
class ChatMessage:
    role: str  # "user", "assistant", "system", "tool"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCallRequest:
    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    call_id: str = ""


@dataclass
class AIResponse:
    content: str
    provider_name: str
    model_name: str
    latency_ms: float = 0.0
    tool_calls: List[ToolCallRequest] = field(default_factory=list)


class BaseAIProvider(ABC):
    """
    Abstract interface for AI model backends (Claude, OpenAI, Ollama/Local, etc.).
    Decouples UI and business logic from specific LLM APIs.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider display name."""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """Model identifier."""
        pass

    @abstractmethod
    def generate_response(
        self, prompt: str, conversation_history: Optional[List[ChatMessage]] = None
    ) -> AIResponse:
        """Synchronously generate an AI response."""
        pass

    @abstractmethod
    def stream_response(
        self, prompt: str, conversation_history: Optional[List[ChatMessage]] = None
    ) -> Iterator[str]:
        """Stream response tokens for typewriter effect."""
        pass
