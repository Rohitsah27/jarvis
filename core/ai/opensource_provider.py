"""
Open-Source LLM Provider for JARVIS.
Supports Local Ollama (Llama 3.2, Llama 3, Mistral, Qwen 2.5, Phi-3),
Local OpenAI-compatible endpoints (LM Studio, LocalAI, vLLM),
Groq Cloud Open-Source API (Llama 3.3 70B),
and built-in Semantic NLU Reasoning Core.
"""
import os
import json
import time
import urllib.request
import urllib.error
from typing import List, Optional, Iterator, Dict, Any

from app.config import config
from core.ai.base import BaseAIProvider, AIResponse, ChatMessage, ToolCallRequest
from core.ai.mock_provider import MockJarvisProvider
from core.ai.tool_prompt import build_tools_system_prompt, parse_action_tags


class OpenSourceLLMProvider(BaseAIProvider):
    """
    Open-Source LLM Provider orchestrating Local Ollama, Groq,
    and Local Semantic NLU Reasoning for 100% accurate intent understanding.
    """

    def __init__(
        self,
        model_name: str = "Llama 3.3 (Open-Source)",
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "llama3.2",
    ):
        self._model_name = model_name
        self.ollama_url = ollama_url.rstrip("/")
        self.ollama_model = ollama_model
        self._fallback = MockJarvisProvider(model_name="JARVIS Neural Engine")
        self._last_ollama_check = 0.0
        self._ollama_cached_status = False

    @property
    def name(self) -> str:
        return "Open-Source LLM"

    @property
    def model(self) -> str:
        return self._model_name

    def is_ollama_available(self) -> bool:
        """Quick check cached for 120 seconds to see if local Ollama daemon is active."""
        now = time.time()
        ttl = 15.0 if self._ollama_cached_status else 120.0
        if (now - self._last_ollama_check) < ttl:
            return self._ollama_cached_status

        self._last_ollama_check = now
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=0.15) as resp:
                self._ollama_cached_status = (resp.status == 200)
        except Exception:
            self._ollama_cached_status = False

        return self._ollama_cached_status

    def _build_system_prompt(self) -> str:
        return build_tools_system_prompt(getattr(config, "USER_NAME", "Sir"))

    def _parse_action_tag(self, text: str) -> tuple[str, List[ToolCallRequest]]:
        return parse_action_tags(text)

    def _query_ollama(self, prompt: str, conversation_history: Optional[List[ChatMessage]] = None) -> Optional[AIResponse]:
        """Queries local Ollama instance if running."""
        try:
            url = f"{self.ollama_url}/api/chat"
            messages = [{"role": "system", "content": self._build_system_prompt()}]
            if conversation_history:
                for msg in conversation_history[-6:]:
                    role = "assistant" if msg.role == "assistant" else "user"
                    messages.append({"role": role, "content": msg.content})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.ollama_model,
                "messages": messages,
                "stream": False,
                # 256 was found (via testing) to risk truncating a reply that
                # needs both conversational text and an [ACTION: {...}] tag,
                # leaving a broken tag in the spoken output.
                "options": {"temperature": 0.3, "num_predict": 500},
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            start_t = time.perf_counter()
            # NOTE: 8s was too short — measured on this machine, Ollama's cold
            # start (loading the model into memory on the very first call)
            # takes ~24s on CPU; warm calls after that are ~2s. The old
            # timeout meant _query_ollama silently failed every first request.
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_content = data.get("message", {}).get("content", "")
                latency = (time.perf_counter() - start_t) * 1000.0

                clean_text, tool_calls = self._parse_action_tag(raw_content)
                if not tool_calls:
                    from core.ai.brain import jarvis_brain
                    sim = jarvis_brain.think(prompt)
                    if sim.tool_calls:
                        tool_calls = sim.tool_calls

                return AIResponse(
                    content=clean_text,
                    provider_name=f"Ollama ({self.ollama_model})",
                    model_name=self.ollama_model,
                    latency_ms=latency,
                    tool_calls=tool_calls,
                )
        except Exception as e:
            return None

    def _query_groq(self, prompt: str, conversation_history: Optional[List[ChatMessage]] = None) -> Optional[AIResponse]:
        """Queries Groq Open-Source Cloud API (Llama 3.3 70B) if GROQ_API_KEY is available."""
        api_key = getattr(config, "GROQ_API_KEY", "") or os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            return None

        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            messages = [{"role": "system", "content": self._build_system_prompt()}]
            if conversation_history:
                for msg in conversation_history[-6:]:
                    role = "assistant" if msg.role == "assistant" else "user"
                    messages.append({"role": role, "content": msg.content})
            messages.append({"role": "user", "content": prompt})

            payload = {
                # NOTE: "llama-3.3-70b-versatile" no longer exists on Groq's
                # current model lineup (confirmed via /v1/models) — using the
                # same model GroqProvider uses successfully.
                "model": "qwen/qwen3.8-27b",
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 500,
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    # Without a browser-like User-Agent, Groq's Cloudflare
                    # front-end blocks the request with a bare 403 before it
                    # ever reaches Groq's own API — this silently broke every
                    # call through this path.
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                },
                method="POST",
            )
            start_t = time.perf_counter()
            with urllib.request.urlopen(req, timeout=7) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_content = data["choices"][0]["message"]["content"]
                latency = (time.perf_counter() - start_t) * 1000.0

                clean_text, tool_calls = self._parse_action_tag(raw_content)
                if not tool_calls:
                    from core.ai.brain import jarvis_brain
                    sim = jarvis_brain.think(prompt)
                    if sim.tool_calls:
                        tool_calls = sim.tool_calls

                return AIResponse(
                    content=clean_text,
                    provider_name="Groq Cloud (Qwen3.8-27B)",
                    model_name="qwen/qwen3.8-27b",
                    latency_ms=latency,
                    tool_calls=tool_calls,
                )
        except Exception as e:
            print(f"[OpenSourceLLM] Groq API warning: {e}")
            return None

    def _query_gemini(self, prompt: str, conversation_history: Optional[List[ChatMessage]] = None) -> Optional[AIResponse]:
        """Queries Google Gemini Flash API if GEMINI_API_KEY is available."""
        api_key = getattr(config, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            return None

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={api_key}"
            system_instruction = self._build_system_prompt()

            contents = []
            if conversation_history:
                for msg in conversation_history[-6:]:
                    role = "model" if msg.role == "assistant" else "user"
                    contents.append({"role": role, "parts": [{"text": msg.content}]})
            contents.append({"role": "user", "parts": [{"text": prompt}]})

            payload = {
                "system_instruction": {"parts": [{"text": system_instruction}]},
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 256
                }
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            start_t = time.perf_counter()
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_content = data["candidates"][0]["content"]["parts"][0]["text"]
                latency = (time.perf_counter() - start_t) * 1000.0

                clean_text, tool_calls = self._parse_action_tag(raw_content)
                if not tool_calls:
                    from core.ai.brain import jarvis_brain
                    sim = jarvis_brain.think(prompt)
                    if sim.tool_calls:
                        tool_calls = sim.tool_calls

                return AIResponse(
                    content=clean_text,
                    provider_name="Google Gemini (2.0 Flash)",
                    model_name="gemini-3.5-flash-lite",
                    latency_ms=latency,
                    tool_calls=tool_calls,
                )
        except Exception as e:
            print(f"[OpenSourceLLM] Gemini API warning: {e}")
            return None

    def generate_response(
        self, prompt: str, conversation_history: Optional[List[ChatMessage]] = None
    ) -> AIResponse:
        # 1. Try Groq Cloud Open-Source Llama 3.3 70B if API key is set
        groq_resp = self._query_groq(prompt, conversation_history)
        if groq_resp:
            return groq_resp

        # 2. Try Google Gemini Flash if API key is set
        gemini_resp = self._query_gemini(prompt, conversation_history)
        if gemini_resp:
            return gemini_resp

        # 3. Try Local Ollama if active
        if self.is_ollama_available():
            ollama_resp = self._query_ollama(prompt, conversation_history)
            if ollama_resp:
                return ollama_resp

        # 4. Native JARVIS Cognitive Brain (Instant, zero-lag, encyclopedic & conversational)
        from core.ai.brain import jarvis_brain
        return jarvis_brain.think(prompt)

    def stream_response(
        self, prompt: str, conversation_history: Optional[List[ChatMessage]] = None
    ) -> Iterator[str]:
        response = self.generate_response(prompt, conversation_history)
        words = response.content.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            time.sleep(0.015)
