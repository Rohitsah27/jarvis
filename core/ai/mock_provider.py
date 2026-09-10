"""
Offline AI Provider — JARVIS's local, zero-network cognitive fallback.
Simulates tool execution decisions and persona responses using regex/keyword
pattern matching (core/ai/brain.py), used whenever a real cloud provider's
API key is unset or a call to it fails.

Previously this reported itself as "Anthropic Claude" regardless of which
real provider it was standing in for — misleading the user into thinking a
real cloud model produced the response when it was actually a local regex
engine. It now reports an honest, provider-specific label.
"""
import time
from typing import List, Optional, Iterator
from core.ai.base import BaseAIProvider, AIResponse, ChatMessage


class MockJarvisProvider(BaseAIProvider):
    """
    Offline fallback: parses intent to simulate system control tool calls
    and realistic persona responses without calling any external API.
    """

    def __init__(self, model_name: str = "JARVIS Offline Engine", provider_label: str = "JARVIS Offline"):
        self._model_name = model_name
        self._provider_label = provider_label

    @property
    def name(self) -> str:
        return self._provider_label

    @property
    def model(self) -> str:
        return self._model_name

    def generate_response(
        self, prompt: str, conversation_history: Optional[List[ChatMessage]] = None
    ) -> AIResponse:
        from core.ai.brain import jarvis_brain
        resp = jarvis_brain.think(prompt)
        resp.provider_name = self.name
        resp.model_name = self.model
        return resp

    def stream_response(
        self, prompt: str, conversation_history: Optional[List[ChatMessage]] = None
    ) -> Iterator[str]:
        response = self.generate_response(prompt, conversation_history)
        words = response.content.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            time.sleep(0.02)  # fast subtle typing latency
