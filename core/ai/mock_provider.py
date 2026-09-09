"""
Mock AI Provider simulating JARVIS's cognitive reasoning, tool execution decisions, and persona.
"""
import time
from typing import List, Optional, Iterator
from core.ai.base import BaseAIProvider, AIResponse, ChatMessage


class MockJarvisProvider(BaseAIProvider):
    """
    Simulates Claude Opus 4.8 / JARVIS intelligent core.
    Parses intent to simulate system control tool calls and realistic persona responses.
    """

    def __init__(self, model_name: str = "Claude Opus 4.8"):
        self._model_name = model_name

    @property
    def name(self) -> str:
        return "Anthropic Claude"

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
