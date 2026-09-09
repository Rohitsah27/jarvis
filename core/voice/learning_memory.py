"""
Lightweight persistent memory for voice misunderstandings.

When intent_router asks a clarification question because it didn't
understand an utterance well enough, and the user's very next utterance is
then understood successfully (fast-path or LLM), this remembers the mapping
from the failed phrasing to the one that worked. The next time the same (or
a close fuzzy match of the) failed phrasing comes in, it's substituted for
the already-proven phrasing before intent matching runs — so JARVIS
understands it immediately instead of asking to repeat it again.

Pure stdlib (json + difflib), one small JSON file on disk — no new
dependencies, no model, keeps the "fast and modular" local-first pipeline.
"""
import json
import time
import difflib
from typing import Optional

from app.config import ROOT_DIR

_MEMORY_PATH = ROOT_DIR / "data" / "learned_corrections.json"
_FUZZY_CUTOFF = 0.72
_PENDING_TTL_SECONDS = 25.0  # how long a clarification stays "awaiting" its answer

_pending: Optional[dict] = None  # {"raw": str, "cleaned": str, "ts": float}


def _load() -> dict:
    try:
        if _MEMORY_PATH.exists():
            with open(_MEMORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[LearningMemory] Load warning: {e}")
    return {}


def _save(data: dict) -> None:
    try:
        _MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[LearningMemory] Save warning: {e}")


def get_learned_correction(cleaned_text: str) -> Optional[str]:
    """Returns a previously-learned resolution for this transcript (exact or
    close fuzzy match against past failures), or None if nothing is known."""
    key = (cleaned_text or "").strip().lower()
    if not key:
        return None
    data = _load()
    if not data:
        return None
    if key in data:
        return data[key]["resolved_as"]
    close = difflib.get_close_matches(key, data.keys(), n=1, cutoff=_FUZZY_CUTOFF)
    if close:
        return data[close[0]]["resolved_as"]
    return None


def mark_awaiting_clarification(raw: str, cleaned: str) -> None:
    """Call whenever JARVIS asks a clarification question, so the very next
    utterance can be linked back as its resolution."""
    global _pending
    _pending = {"raw": raw, "cleaned": cleaned, "ts": time.time()}


def resolve_pending_clarification(resolved_text: str) -> None:
    """Call once a follow-up utterance is understood successfully. If it came
    shortly after a clarification question, remembers the mapping so the
    original phrasing is understood directly next time."""
    global _pending
    pending = _pending
    _pending = None
    if not pending:
        return
    if time.time() - pending["ts"] > _PENDING_TTL_SECONDS:
        return
    key = pending["cleaned"].strip().lower()
    resolved = (resolved_text or "").strip()
    if not key or not resolved or key == resolved.lower():
        return
    data = _load()
    data[key] = {
        "resolved_as": resolved,
        "raw_example": pending["raw"],
        "learned_at": time.time(),
    }
    _save(data)
    print(f"[LearningMemory] Learned: {key!r} -> {resolved!r}")
