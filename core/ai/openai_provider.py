"""
OpenAI API Provider for JARVIS.
Direct integration with OpenAI's official Chat Completions API (GPT-4o / GPT-4o Mini)
with zero heavy SDK dependencies and full desktop tool-calling support.
"""
import os
import json
import time
import urllib.request
import urllib.error
from typing import List, Optional, Iterator

from app.config import config
from core.ai.base import BaseAIProvider, AIResponse, ChatMessage, ToolCallRequest
from core.ai.brain import jarvis_brain
from core.ai.tool_prompt import build_tools_system_prompt, parse_action_tags


class OpenAIProvider(BaseAIProvider):
    """OpenAI GPT-4o / GPT-4o-mini Provider with autonomous Windows tool execution."""

    def __init__(self, model: str = "gpt-4o", api_key: Optional[str] = None):
        self._model = model
        self._api_key = api_key

    @property
    def api_key(self) -> str:
        return self._api_key or getattr(config, "OPENAI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")

    @property
    def name(self) -> str:
        return "OpenAI"

    @property
    def model(self) -> str:
        return self._model

    def _build_system_prompt(self) -> str:
        return build_tools_system_prompt(getattr(config, "USER_NAME", "Sir"))

    def _parse_action_tag(self, text: str) -> tuple[str, List[ToolCallRequest]]:
        return parse_action_tags(text)

    def generate_response(
        self, prompt: str, conversation_history: Optional[List[ChatMessage]] = None
    ) -> AIResponse:
        key = self.api_key
        if not key:
            # Fallback to zero-lag offline brain
            resp = jarvis_brain.think(prompt)
            resp.provider_name = f"{self.name} (Offline Engine)"
            resp.model_name = self.model
            return resp

        try:
            url = "https://api.openai.com/v1/chat/completions"
            messages = [{"role": "system", "content": self._build_system_prompt()}]

            if conversation_history:
                history_limit = max(6, int(getattr(config, "ACTIVE_CONVERSATION_HISTORY_TURNS", 16)))
                for msg in conversation_history[-history_limit:]:
                    role = "assistant" if msg.role == "assistant" else "user"
                    messages.append({"role": role, "content": msg.content})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self._model,
                "messages": messages,
                "temperature": 0.2,
                # 300 was found (via testing on another provider sharing this
                # same pattern) to risk truncating a reply that needs both
                # conversational text and an [ACTION: {...}] tag.
                "max_tokens": 500,
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            start_t = time.perf_counter()
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_content = data["choices"][0]["message"]["content"]
                latency = (time.perf_counter() - start_t) * 1000.0

                # The real model's own tool-call decision is final — never
                # replaced with the offline regex brain's own guess.
                clean_text, tool_calls = self._parse_action_tag(raw_content)

                return AIResponse(
                    content=clean_text,
                    provider_name=f"OpenAI ({self.model})",
                    model_name=self.model,
                    latency_ms=latency,
                    tool_calls=tool_calls,
                )

        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8")
            except Exception:
                pass
            print(f"[OpenAIProvider] HTTP Error {e.code}: {err_body}")

            # If quota/credit balance exhausted (429) or network issue, fall back smoothly to brain
            fallback_resp = jarvis_brain.think(prompt)
            fallback_resp.provider_name = f"OpenAI ({self.model} - Fallback)"
            fallback_resp.model_name = self.model
            return fallback_resp

        except Exception as e:
            print(f"[OpenAIProvider] API error: {e}, falling back to brain.")
            resp = jarvis_brain.think(prompt)
            resp.provider_name = f"OpenAI ({self.model} - Fallback)"
            resp.model_name = self.model
            return resp

    def stream_response(
        self, prompt: str, conversation_history: Optional[List[ChatMessage]] = None
    ) -> Iterator[str]:
        response = self.generate_response(prompt, conversation_history)
        words = response.content.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            time.sleep(0.015)
