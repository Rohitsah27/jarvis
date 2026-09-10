"""
Anthropic Claude API Provider integration.
Can be activated by providing an ANTHROPIC_API_KEY environment variable or setting in Settings.
"""
import os
import time
from typing import List, Optional, Iterator
from app.config import config
from core.ai.base import BaseAIProvider, AIResponse, ChatMessage, ToolCallRequest
from core.ai.mock_provider import MockJarvisProvider
from core.ai.tool_prompt import build_tools_system_prompt, parse_action_tags

# NOTE: Anthropic periodically retires older dated model snapshots. This
# default has not been independently re-verified against Anthropic's
# current model list as part of this fix — rather than silently guessing a
# replacement string that might not exist (which would 404 and get masked
# by the broad except below, exactly the failure mode that made the old
# value's staleness invisible), the model is now a config field so it can
# be corrected without a code change. Verify at
# https://docs.anthropic.com/en/docs/about-claude/models before relying on
# this in production, and update app/config.py's ANTHROPIC_MODEL if stale.
_DEFAULT_MODEL = "claude-3-7-sonnet-20250219"


class ClaudeProvider(BaseAIProvider):
    """
    Claude provider connecting to Anthropic's Messages API.
    Falls back to MockJarvisProvider when no API key is set.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self._api_key = api_key
        self._model = model or getattr(config, "ANTHROPIC_MODEL", None) or _DEFAULT_MODEL
        self._fallback = MockJarvisProvider(model_name="Offline Simulation", provider_label="JARVIS Offline")

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
            start_t = time.perf_counter()
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = "".join(
                    block["text"] for block in data.get("content", []) if block.get("type") == "text"
                )
                latency = (time.perf_counter() - start_t) * 1000.0
                # The real model's own tool-call decision is final — this
                # provider never had the offline-brain-override bug the
                # others did, but keep it that way explicitly.
                clean_text, tool_calls = parse_action_tags(text)
                return AIResponse(
                    content=clean_text,
                    provider_name=self.name,
                    model_name=self.model,
                    latency_ms=latency,
                    tool_calls=tool_calls,
                )
        except Exception as e:
            # Graceful error handling — degrades to the offline fallback
            # rather than a bare error string, consistent with the other
            # providers, and honestly labeled as such (see mock_provider.py).
            resp = self._fallback.generate_response(prompt, conversation_history)
            resp.content = (
                f"Sir, direct link to Claude API encountered an exception: {str(e)}. "
                f"Reverting to offline mode. {resp.content}"
            )
            return resp

    def stream_response(
        self, prompt: str, conversation_history: Optional[List[ChatMessage]] = None
    ) -> Iterator[str]:
        # Fallback to token stream generator
        return self._fallback.stream_response(prompt, conversation_history)
