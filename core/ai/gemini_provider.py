"""
Google Gemini API Provider for JARVIS.
Connects directly to Google's official Gemini REST API (gemini-3.5-flash-lite / gemini-1.5-flash)
with zero SDK dependency.
"""
import os
import json
import time
import urllib.request
from typing import List, Optional, Iterator

from app.config import config
from core.ai.base import BaseAIProvider, AIResponse, ChatMessage, ToolCallRequest
from core.ai.brain import jarvis_brain
from core.ai.tool_prompt import build_tools_system_prompt, parse_action_tags


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI Provider with autonomous Windows tool calling."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3.5-flash-lite"):
        self._api_key = api_key
        self._model = model

    @property
    def api_key(self) -> str:
        return self._api_key or getattr(config, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")

    @property
    def name(self) -> str:
        return "Google Gemini"

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
            resp.provider_name = self.name
            resp.model_name = self.model
            return resp

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}:generateContent?key={key}"
            contents = []
            if conversation_history:
                history_limit = max(6, int(getattr(config, "ACTIVE_CONVERSATION_HISTORY_TURNS", 16)))
                for msg in conversation_history[-history_limit:]:
                    role = "model" if msg.role == "assistant" else "user"
                    contents.append({"role": role, "parts": [{"text": msg.content}]})
            contents.append({"role": "user", "parts": [{"text": prompt}]})

            payload = {
                "system_instruction": {"parts": [{"text": self._build_system_prompt()}]},
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.2,
                    # 256 was found (via testing on another provider sharing
                    # this same pattern) to risk truncating a reply that
                    # needs both conversational text and an [ACTION: {...}]
                    # tag, leaving a broken tag in the spoken output.
                    "maxOutputTokens": 500
                }
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            start_t = time.perf_counter()
            with urllib.request.urlopen(req, timeout=7) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_content = data["candidates"][0]["content"]["parts"][0]["text"]
                latency = (time.perf_counter() - start_t) * 1000.0

                # The real model's own tool-call decision is final — it is
                # never replaced by asking the offline regex brain for a
                # second opinion. That override used to let an action
                # execute that neither the human nor the selected AI model
                # actually approved: if Gemini's response contains no
                # [ACTION:...] tag, that means "no tool", full stop.
                clean_text, tool_calls = self._parse_action_tag(raw_content)

                return AIResponse(
                    content=clean_text,
                    provider_name=self.name,
                    model_name=self.model,
                    latency_ms=latency,
                    tool_calls=tool_calls,
                )
        except Exception as e:
            print(f"[Gemini] API error: {e}, falling back to brain.")
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
            time.sleep(0.015)
