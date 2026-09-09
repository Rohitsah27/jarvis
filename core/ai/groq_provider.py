"""
Groq Cloud LPU Provider for JARVIS.
Delivers ultra-high speed (300+ tokens/sec) open-source LLM inference for FREE.
Powered by Qwen 3.8 (27B) / GPT-OSS on Groq's Tensor Streaming Processing (LPU) chips.
"""
import os
import threading
import time
from typing import List, Optional, Iterator

import requests

from app.config import config
from core.ai.base import BaseAIProvider, AIResponse, ChatMessage, ToolCallRequest
from core.ai.brain import jarvis_brain
from core.ai.tool_prompt import build_tools_system_prompt, parse_action_tags


class GroqProvider(BaseAIProvider):
    """Groq Cloud LPU AI Provider with zero-latency autonomous Windows tool execution."""

    def __init__(self, model: str = "qwen/qwen3.8-27b", api_key: Optional[str] = None):
        self._model = model
        self._api_key = api_key
        # A fresh urllib.request.urlopen() call pays a new TCP + TLS
        # handshake EVERY turn (100-400ms+ depending on network/region) —
        # a real, previously invisible chunk of the "gap" before JARVIS
        # even starts thinking. A persistent Session keeps the underlying
        # HTTPS connection to Groq alive (HTTP keep-alive) across the whole
        # app session, so only the very first request ever pays that cost.
        self._session = requests.Session()
        # requests.Session is documented as not thread-safe. Normal use is
        # sequential (one voice interaction after another), but
        # main_window.py's overlap guard for AIInferenceWorker is only a
        # best-effort 300ms wait, not a real guarantee — a slow LLM call
        # genuinely can still be in flight when the next one starts. This
        # lock just serializes actual network calls through the shared
        # session; it does not add latency in the normal non-overlapping
        # case since there's nothing to contend with.
        self._session_lock = threading.Lock()
        # Once per session, not on every single request — avoids repeating
        # the same notice on every reply for the rest of the day once the
        # free daily quota is hit. Resets on the next successful call, so a
        # later exhaustion (e.g. after the quota resets and fills up again)
        # is announced again.
        self._quota_notice_shown = False

    def warm_up(self) -> None:
        """
        Opens the HTTPS connection to Groq ahead of time (call this from a
        background thread at app startup, mirroring TTSPreloadWorker for
        Kokoro) so the very first real request reuses an already-established
        connection instead of paying the TCP+TLS handshake cost on the
        user's first command. Hits the cheap /models listing endpoint —
        no completion tokens spent. Best-effort: a failure here just means
        the first real request pays the handshake cost as before.
        """
        key = self.api_key
        if not key:
            return
        try:
            with self._session_lock:
                self._session.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=5,
                )
        except Exception as e:
            print(f"[GroqProvider] Connection warm-up warning: {e}")

    @property
    def api_key(self) -> str:
        return self._api_key or getattr(config, "GROQ_API_KEY", "") or os.environ.get("GROQ_API_KEY", "")

    @property
    def name(self) -> str:
        return "Groq Cloud (Free)"

    @property
    def model(self) -> str:
        return self._model

    def _build_system_prompt(self) -> str:
        return build_tools_system_prompt(getattr(config, "USER_NAME", "Sir"))

    def _parse_action_tags(self, text: str) -> tuple[str, List[ToolCallRequest]]:
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

        candidate_models = [self._model, "openai/gpt-oss-120b", "groq/compound"]
        saw_rate_limit = False

        for model_id in candidate_models:
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                messages = [{"role": "system", "content": self._build_system_prompt()}]

                if conversation_history:
                    for msg in conversation_history[-6:]:
                        role = "assistant" if msg.role == "assistant" else "user"
                        messages.append({"role": role, "content": msg.content})
                messages.append({"role": "user", "content": prompt})

                payload = {
                    "model": model_id,
                    "messages": messages,
                    "temperature": 0.2,
                    # Found via testing: 250 was too tight — a reply needing
                    # both conversational text AND an [ACTION: {...}] tag
                    # (or a reasoning model like gpt-oss-120b that spends
                    # tokens on hidden reasoning first) could hit this cap
                    # mid-JSON, leaving a broken/unparseable action tag in
                    # the spoken text, or an empty response entirely
                    # (finish_reason="length" observed in both cases).
                    # MAX_SPOKEN_CHARS already caps what actually gets
                    # spoken, so there's no downside to more headroom here.
                    "max_tokens": 500,
                }

                start_t = time.perf_counter()
                # Groq advertises 300+ tokens/sec, so a 500-max-token reply
                # should land well under 2s normally — 5s leaves generous
                # headroom for a genuinely slow response while bounding the
                # worst case (up to 3 candidate models tried sequentially on
                # rate limits/errors) to ~15s instead of the previous ~21s.
                with self._session_lock:
                    resp = self._session.post(
                        url,
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {key}",
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                        },
                        timeout=5,
                    )
                resp.raise_for_status()
                data = resp.json()
                raw_content = data["choices"][0]["message"]["content"]
                latency = (time.perf_counter() - start_t) * 1000.0

                clean_text, tool_calls = self._parse_action_tags(raw_content)
                if not tool_calls:
                    sim = jarvis_brain.think(prompt)
                    if sim.tool_calls:
                        tool_calls = sim.tool_calls

                self._quota_notice_shown = False
                return AIResponse(
                    content=clean_text,
                    provider_name="Groq Cloud (Free LPU)",
                    model_name=model_id,
                    latency_ms=latency,
                    tool_calls=tool_calls,
                )

            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response is not None else 0
                err_body = e.response.text if e.response is not None else ""
                if status == 429 and "rate_limit_exceeded" in err_body:
                    saw_rate_limit = True
                print(f"[GroqProvider] HTTP Error {status} on model {model_id}: {err_body}")
                continue

            except Exception as e:
                print(f"[GroqProvider] Request error on model {model_id}: {e}")
                continue

        # Fallback to local cognitive brain if all Groq candidate models fail
        fallback_resp = jarvis_brain.think(prompt)
        fallback_resp.provider_name = f"{self.name} (Offline Fallback)"
        fallback_resp.model_name = self.model

        # Quota exhaustion was previously silent — JARVIS would just get
        # noticeably dumber (dropped to the local regex brain) for the rest
        # of the day with no indication why. Announce it once per session
        # instead of leaving the user to guess.
        if saw_rate_limit and not self._quota_notice_shown:
            self._quota_notice_shown = True
            lang = jarvis_brain.detect_language(prompt)
            if lang == "hi":
                notice = "सर, Groq का आज का मुफ्त कोटा खत्म हो गया है, इसलिए अभी मैं ऑफ़लाइन मोड में जवाब दे रहा हूँ। "
            else:
                notice = "Sir, Groq's free daily quota is exhausted for today, so I'm answering in offline mode for now. "
            fallback_resp.content = notice + (fallback_resp.content or "")

        return fallback_resp

    def stream_response(
        self, prompt: str, conversation_history: Optional[List[ChatMessage]] = None
    ) -> Iterator[str]:
        response = self.generate_response(prompt, conversation_history)
        words = response.content.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            time.sleep(0.015)
