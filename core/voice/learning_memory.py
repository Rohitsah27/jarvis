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

Bounded and expiring: previously this store grew forever with no cap, no
TTL, and no way for the user to clear it — a single bad learned mapping
(the follow-up utterance itself was misheard) would be replayed
indefinitely with no correction path except manually editing the JSON file.
It's also privacy-relevant: raw_example stores the user's verbatim failed
utterance. See clear_all() for a user-facing "forget everything" action.

Security note: a learned correction can only ever influence which text
intent_router treats as the transcript, and how confident the resulting
fast-path match is — it can NEVER skip core/tools/permission.py's
confirmation gate. Even a maximally-confident fast-path match still routes
through ToolManager.execute_tool() -> PermissionManager.check_permission(),
same as any other tool call, so a poisoned memory entry cannot escalate
into an unconfirmed action.
"""
import json
import os
import time
import difflib
from typing import Optional

from app.config import ROOT_DIR, config

_MEMORY_PATH = ROOT_DIR / "data" / "learned_corrections.json"
_FUZZY_CUTOFF = 0.72
_PENDING_TTL_SECONDS = 25.0  # how long a clarification stays "awaiting" its answer

_pending: Optional[dict] = None  # {"raw": str, "cleaned": str, "ts": float}


def _max_entries() -> int:
    return max(1, int(getattr(config, "LEARNING_MEMORY_MAX_ENTRIES", 500)))


def _ttl_seconds() -> float:
    return max(1, int(getattr(config, "LEARNING_MEMORY_TTL_DAYS", 90))) * 86400.0


def _is_valid_entry(value) -> bool:
    """Guards against a malformed/hand-edited entry crashing a caller —
    every field this module reads must actually be present and the right
    type before it's trusted."""
    return (
        isinstance(value, dict)
        and isinstance(value.get("resolved_as"), str) and value.get("resolved_as")
        and isinstance(value.get("learned_at"), (int, float))
    )


def _load() -> dict:
    try:
        if not _MEMORY_PATH.exists():
            return {}
        with open(_MEMORY_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            print("[LearningMemory] Ignoring corrupt store (not a JSON object) — starting fresh.")
            return {}
    except Exception as e:
        print(f"[LearningMemory] Load warning: {e}")
        return {}

    now = time.time()
    ttl = _ttl_seconds()
    cleaned = {
        k: v for k, v in raw.items()
        if _is_valid_entry(v) and (now - v["learned_at"]) <= ttl
    }
    return cleaned


def _save(data: dict) -> None:
    # Bound BEFORE writing — evict the oldest entries first (by
    # learned_at) so the file can never grow past this cap regardless of
    # how many corrections accumulate over the life of the install.
    if len(data) > _max_entries():
        ordered = sorted(data.items(), key=lambda kv: kv[1].get("learned_at", 0))
        data = dict(ordered[-_max_entries():])

    try:
        _MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: a crash/power-loss mid-write must not corrupt the
        # store (which _load() would then have to discard wholesale).
        tmp_path = _MEMORY_PATH.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, _MEMORY_PATH)
    except Exception as e:
        print(f"[LearningMemory] Save warning: {e}")


def clear_all() -> bool:
    """User-facing 'forget everything JARVIS has learned from misheard
    commands' action (wired from Settings). Returns True on success."""
    global _pending
    _pending = None
    try:
        if _MEMORY_PATH.exists():
            _MEMORY_PATH.unlink()
        return True
    except Exception as e:
        print(f"[LearningMemory] Could not clear store: {e}")
        return False


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
