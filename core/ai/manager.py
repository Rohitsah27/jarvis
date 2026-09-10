"""
AI Provider Manager orchestrating model selection, routing, and conversation history.
"""
from typing import Dict, List, Optional, Iterator
from app.config import config
from core.ai.base import BaseAIProvider, AIResponse, ChatMessage
from core.ai.claude_provider import ClaudeProvider
from core.ai.opensource_provider import OpenSourceLLMProvider
from core.ai.gemini_provider import GeminiProvider
from core.ai.openai_provider import OpenAIProvider
from core.ai.groq_provider import GroqProvider

_FALLBACK_PROVIDER_KEY = "Groq Cloud (Free LPU / 300 t/s)"


class AIProviderManager:
    """Manages available AI providers and routes requests to the active one."""

    def __init__(self):
        # Previously also listed "Claude Opus 4.8" (silently backed by
        # MockJarvisProvider — not a real Claude call at all, just the local
        # regex brain wearing a fake label) plus three duplicate/rebranded
        # entries ("Open-Source LLM" == "Local LLM", "GPT-4o Omniscient" ==
        # "OpenAI GPT-4o"). Removed all of those — every remaining entry here
        # is a distinct, real backend.
        #
        # A later audit found ANOTHER duplicate that slipped in after that
        # cleanup: "Google Gemini (2.0 Flash / Live API)" used
        # GeminiProvider()'s default model, which is "gemini-3.5-flash-lite"
        # (see gemini_provider.py) — the exact same model as the
        # "Flash-Lite" entry right below it, just under a label claiming a
        # different ("2.0 Flash") model that was never actually called.
        # Collapsed to one honestly-labeled entry.
        self._providers: Dict[str, BaseAIProvider] = {
            "Groq Cloud (Free LPU / 300 t/s)": GroqProvider(),
            "Google Gemini (Flash-Lite / Fast)": GeminiProvider(model="gemini-3.5-flash-lite"),
            "OpenAI GPT-4o (Live API)": OpenAIProvider("gpt-4o"),
            "OpenAI GPT-4o Mini": OpenAIProvider("gpt-4o-mini"),
            "Claude Live API": ClaudeProvider(),
            "Local LLM (Llama 3 / Ollama)": OpenSourceLLMProvider("Llama 3.3 (Local)"),
        }
        # Was previously hardcoded, silently ignoring config.DEFAULT_AI_PROVIDER
        # (and whatever the user picked in Settings) every time the app
        # restarted. Falls back to Groq (free, fast, no credits required) if
        # the saved value doesn't match a known provider.
        default_key = getattr(config, "DEFAULT_AI_PROVIDER", "") or _FALLBACK_PROVIDER_KEY
        self._active_provider_key: str = default_key if default_key in self._providers else _FALLBACK_PROVIDER_KEY
        self._history: List[ChatMessage] = []

    @property
    def active_provider(self) -> BaseAIProvider:
        return self._providers.get(self._active_provider_key, self._providers[_FALLBACK_PROVIDER_KEY])

    @property
    def active_provider_name(self) -> str:
        return self._active_provider_key

    @property
    def conversation_history(self) -> List[ChatMessage]:
        return self._history

    def set_provider(self, name: str) -> bool:
        if name in self._providers:
            self._active_provider_key = name
            return True
        return False

    def list_providers(self) -> List[str]:
        return list(self._providers.keys())

    def add_message(self, role: str, content: str) -> ChatMessage:
        msg = ChatMessage(role=role, content=content)
        self._history.append(msg)
        # Bounded: previously this grew for the entire process lifetime
        # with no eviction. Each provider already only sends the last 6-10
        # messages per call (see e.g. core/ai/groq_provider.py), so this
        # cap only matters for RAM use over a very long-running session,
        # not per-call token cost.
        max_len = max(2, int(getattr(config, "MAX_CONVERSATION_HISTORY_MESSAGES", 200)))
        if len(self._history) > max_len:
            self._history = self._history[-max_len:]
        return msg

    def clear_history(self) -> None:
        self._history.clear()

    def ask(self, prompt: str) -> AIResponse:
        self.add_message("user", prompt)
        response = self.active_provider.generate_response(prompt, self._history)
        self.add_message("assistant", response.content)
        return response

    def ask_stream(self, prompt: str) -> Iterator[str]:
        self.add_message("user", prompt)
        return self.active_provider.stream_response(prompt, self._history)


# Global AI Manager instance
ai_manager = AIProviderManager()
