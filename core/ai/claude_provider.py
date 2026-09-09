"""
Anthropic Claude API Provider integration.
Can be activated by providing an ANTHROPIC_API_KEY environment variable or setting in Settings.
"""
import os
from typing import List, Optional, Iterator
from app.config import config
from core.ai.base import BaseAIProvider, AIResponse, ChatMessage, ToolCallRequest
from core.ai.mock_provider import MockJarvisProvider
from core.ai.tool_prompt import build_tools_system_prompt, parse_action_tags


class ClaudeProvider(BaseAIProvider):
    """
    Claude provider connecting to Anthropic's Messages API.
    Falls back to MockJarvisProvider when no API key is set.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-7-sonnet-20250219"):
        self._api_key = api_key
        self._model = model
        self._fallback = MockJarvisProvider(model_name="Offline Simulation")

    @property
    def api_key(self) -> str:
        # Was previously captured once from the environment at construction
        # time, so a key saved in Settings (config.ANTHROPIC_API_KEY) was
        # never picked up — this now checks live, same pattern as
        # Groq/OpenAI/Gemini: explicit override > Settings > env var.
        return self._api_key or getattr(config, "ANTHROPIC_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")

    @property
    def name(self) -> str:
        return "Anthropic Claude"

    @property
    def model(self) -> str:
        return self._model

    def generate_response(
        self, prompt: str, conversation_history: Optional[List[ChatMessage]] = None
    ) -> AIResponse:
        if not self.api_key:
            # Clean fallback when API key is unconfigured
            return self._fallback.generate_response(prompt, conversation_history)

        try:
            import urllib.request
            import json

            # Standard lightweight HTTP request without requiring heavy anthropic SDK
            url = "https://api.anthropic.com/v1/messages"
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }

            messages = []
            if conversation_history:
                for msg in conversation_history[-10:]:
                    role = "assistant" if msg.role == "assistant" else "user"
                    messages.append({"role": role, "content": msg.content})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self._model,
                "max_tokens": 1024,
                "system": build_tools_system_prompt(),
                "messages": messages,
            }

            req = urllib.request.Request(
                url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = "".join(
                    block["text"] for block in data.get("content", []) if block.get("type") == "text"
                )
                clean_text, tool_calls = parse_action_tags(text)
                return AIResponse(
                    content=clean_text,
                    provider_name=self.name,
                    model_name=self.model,
                    tool_calls=tool_calls,
                )
        except Exception as e:
            # Graceful error handling
            return AIResponse(
                content=f"Sir, direct link to Claude API encountered an exception: {str(e)}. Reverting to neural simulation.",
                provider_name=self.name,
                model_name=self.model,
            )

    def stream_response(
        self, prompt: str, conversation_history: Optional[List[ChatMessage]] = None
    ) -> Iterator[str]:
        # Fallback to token stream generator
        return self._fallback.stream_response(prompt, conversation_history)
