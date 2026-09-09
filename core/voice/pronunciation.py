"""
Engine-independent TTS text preprocessing for JARVIS's Hindi/Hinglish speech
output — language detection, pronunciation correction, and mixed-language
segmentation, all as pure text-in/text-out functions with zero dependency on
Kokoro or any other specific synthesis engine.

WHY THIS EXISTS
Any TTS engine's phonemizer (Kokoro's eSpeak-NG-based one included) forces a
single language's phoneme rules onto an entire utterance. This app's own
vocabulary is full of English technical terms and app names embedded in
Hindi sentences (JARVIS, WhatsApp, API, Chrome...) — this is a constant,
predictable class of mispronunciation, not an occasional edge case.

TWO LAYERS, IN ORDER
1. A pronunciation dictionary (pronunciation_dictionary.json, loaded once at
   import time) rewrites known recurring English terms to a Devanagari
   spelling the Hindi voice pronounces correctly — the mirror image of
   transcript_processor.py's STT-side correction table for the exact same
   vocabulary, running in the opposite direction (TTS output instead of STT
   input).
2. For anything else not covered by the dictionary, segment_for_speech()
   splits the text into runs of one script, so each run gets synthesized
   with the correct voice + language code instead of forcing one language
   over an entire reply. Short/stray runs (< 3 words) are folded into their
   neighbor rather than triggering a jarring voice switch for a single
   leftover word the dictionary didn't already catch.

HOW TO INTEGRATE A NEW/FUTURE TTS ENGINE
Call preprocess_for_speech(text) as the FIRST step of that engine's
synthesis method, before its own language detection or voice selection:

    from core.voice.pronunciation import preprocess_for_speech
    for segment_text, segment_lang in preprocess_for_speech(llm_reply_text):
        voice = pick_voice_for(segment_lang)   # engine's own voice mapping
        audio = my_new_engine.synthesize(segment_text, voice=voice)
        play(audio)

That's the entire integration surface — no engine needs its own copy of the
dictionary, language detection, or segmentation logic. See kokoro_engine.py
for a real usage example (both its blocking and streaming synthesis paths
call this exact function).
"""
import json
import re
from pathlib import Path
from typing import List, Tuple

from app.config import config

_DICT_PATH = Path(__file__).resolve().parent / "pronunciation_dictionary.json"
_USER_DICT_PATH = Path(__file__).resolve().parent / "user_dictionary.json"


def _load_overrides() -> dict:
    """Flattens pronunciation_dictionary.json's categorized entries and
    user_dictionary.json's custom entries into a single lowercase-keyed lookup
    table. Failing open (empty dict, not a crash) if files are missing/corrupt —
    pronunciation quality degrades gracefully rather than breaking speech entirely."""
    lookup = {}
    # 1. Built-in dictionary
    try:
        if _DICT_PATH.exists():
            with open(_DICT_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for entries in data.get("categories", {}).values():
                for entry in entries:
                    term = entry.get("term", "")
                    devanagari = entry.get("devanagari", "")
                    if term and devanagari:
                        lookup[term.lower()] = devanagari
    except Exception as e:
        print(f"[Pronunciation] Could not load {_DICT_PATH.name}: {e}")

    # 2. User custom dictionary (overrides built-in if duplicated)
    try:
        if _USER_DICT_PATH.exists():
            with open(_USER_DICT_PATH, "r", encoding="utf-8") as f:
                user_data = json.load(f)
            for entry in user_data.get("words", []):
                term = entry.get("term", "")
                devanagari = entry.get("devanagari", "")
                if term and devanagari:
                    lookup[term.lower()] = devanagari
    except Exception as e:
        print(f"[Pronunciation] Could not load {_USER_DICT_PATH.name}: {e}")

    return lookup


_LOOKUP = _load_overrides()
_OVERRIDE_PATTERN = (
    re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(_LOOKUP, key=len, reverse=True)) + r")\b", re.IGNORECASE)
    if _LOOKUP else None
)


def reload_dictionary() -> int:
    """Re-reads pronunciation_dictionary.json and user_dictionary.json from disk
    without restarting the app — useful after hand-editing or adding words via UI.
    Returns the total number of terms loaded."""
    global _LOOKUP, _OVERRIDE_PATTERN
    _LOOKUP = _load_overrides()
    _OVERRIDE_PATTERN = (
        re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(_LOOKUP, key=len, reverse=True)) + r")\b", re.IGNORECASE)
        if _LOOKUP else None
    )
    return len(_LOOKUP)


def add_custom_word(term: str, devanagari: str, category: str = "custom") -> bool:
    """Adds or updates a custom pronunciation override in user_dictionary.json,
    persists it, and reloads the engine lookup table immediately."""
    try:
        t = term.strip()
        d = devanagari.strip()
        if not t or not d:
            return False

        data = {"_meta": {"description": "User-defined custom pronunciation overrides"}, "words": []}
        if _USER_DICT_PATH.exists():
            try:
                with open(_USER_DICT_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass

        words = data.get("words", [])
        updated = False
        for w in words:
            if w.get("term", "").lower() == t.lower():
                w["devanagari"] = d
                w["category"] = category
                updated = True
                break
        if not updated:
            words.append({"term": t, "devanagari": d, "category": category})
        data["words"] = words

        with open(_USER_DICT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        reload_dictionary()
        return True
    except Exception as e:
        print(f"[Pronunciation] Failed to add custom word '{term}': {e}")
        return False


def remove_custom_word(term: str) -> bool:
    """Removes a custom pronunciation override from user_dictionary.json and reloads lookup."""
    try:
        if not _USER_DICT_PATH.exists():
            return False
        with open(_USER_DICT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        t_low = term.strip().lower()
        words = [w for w in data.get("words", []) if w.get("term", "").lower() != t_low]
        data["words"] = words
        with open(_USER_DICT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        reload_dictionary()
        return True
    except Exception as e:
        print(f"[Pronunciation] Failed to remove custom word '{term}': {e}")
        return False


def get_custom_words() -> list:
    """Returns the list of custom words defined in user_dictionary.json."""
    if not _USER_DICT_PATH.exists():
        return []
    try:
        with open(_USER_DICT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("words", [])
    except Exception:
        return []


def get_dictionary_stats() -> dict:
    """Returns statistics about currently loaded pronunciation dictionaries."""
    return {
        "total_terms": len(_LOOKUP),
        "custom_terms": len(get_custom_words()),
    }


def apply_pronunciation_overrides(text: str, lang: str = "hi") -> str:
    """Only meaningful for Hindi text — these overrides exist specifically
    to fix English words embedded IN a Hindi sentence. A fully-English reply
    already pronounces these words correctly through the English voice, so
    nothing is rewritten there."""
    if lang != "hi" or not text or _OVERRIDE_PATTERN is None:
        return text
    return _OVERRIDE_PATTERN.sub(lambda m: _LOOKUP[m.group(1).lower()], text)


_DEVANAGARI_UNICODE_RE = re.compile(r"[ऀ-ॿ]")

# Romanized Hindi/Hinglish markers for whole-text language detection (used
# when there's no Devanagari script at all, e.g. "kholo notepad"). This is
# the TTS-side keyword list; kokoro_engine.py's own near-duplicate copy was
# consolidated into this one. core/ai/brain.py has a separate, independently
# tuned list for a different job (see detect_language()'s docstring below)
# and deliberately keeps its own.
_HINGLISH_MARKERS = {
    "mera", "meri", "mere", "awaaz", "aawaz", "sunai", "de", "raha", "rahi", "rahe",
    "hai", "hain", "kya", "batao", "kholo", "khol", "dikhao", "dikh", "kaun", "kaise", "kaisa",
    "karo", "kar", "kariye", "tum", "aap", "namaste", "shukriya", "dhanyawad", "chalao", "roko",
    "samay", "aaj", "din", "kitna", "kitni", "bataiye", "bolo", "bol", "main", "hum", "mujhe",
    "usmein", "usme", "ismein", "isme", "sakte", "sakta", "sakti", "ho", "hoon", "hun",
    "gana", "gaana", "gaane", "bajao", "lagao", "sunao", "accha", "achha", "koi", "kuch",
}


def detect_language(text: str) -> str:
    """Determines whether text is predominantly Hindi or English: direct
    Devanagari Unicode presence first, then a romanized-Hindi keyword count
    (>=2 matches) for fully Latin-script Hinglish. Canonical implementation
    for the TTS/speech-output side, shared by every TTS engine. Note:
    core/ai/brain.py has its own separate detect_language() for a different
    job (choosing which language to COMPOSE a local reply in, from the
    user's utterance) — deliberately left independent since it's tuned
    differently (lower 1-match threshold, larger keyword set) for that
    purpose; not something this pronunciation pipeline should change."""
    if _DEVANAGARI_UNICODE_RE.search(text):
        return "hi"
    words = set(re.findall(r"\b[a-zA-Z]+\b", text.lower()))
    if len(words & _HINGLISH_MARKERS) >= 2:
        return "hi"
    return "en"


def strip_markdown_for_speech(text: str) -> str:
    """Removes code fences and stray markdown emphasis characters that read
    aloud as noise ('asterisk asterisk bold asterisk asterisk'). Engine-
    independent text hygiene, applied before language detection."""
    cleaned = text.strip()
    if not cleaned:
        return ""
    cleaned = re.sub(r"```.*?```", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"[\*\_#`]", "", cleaned).strip()
    return cleaned or text.strip()


_LATIN_RE = re.compile(r"[A-Za-z]")

# A stray run shorter than this many words is folded into its neighbor
# instead of triggering a full voice/language switch — TTS synthesis has
# real per-call overhead, and switching voices every couple of words would
# sound choppier than just accepting the dictionary didn't catch a rare
# term. The dictionary is the primary fix for short embedded terms; this
# segmentation is the secondary net for anything longer it doesn't cover (a
# whole English clause or sentence inside a Hindi reply, etc).
_MIN_RUN_WORDS = 3


def _classify_word(word: str, fallback_lang: str) -> str:
    if _DEVANAGARI_UNICODE_RE.search(word):
        return "hi"
    if _LATIN_RE.search(word):
        return "en"
    return fallback_lang  # pure digits/punctuation inherit context


def segment_for_speech(text: str) -> List[Tuple[str, str]]:
    """Splits `text` into [(segment_text, lang), ...] runs of one script,
    merging short stray runs into their neighbor. A single-language input
    (the common case) returns exactly one segment, so this adds no overhead
    or behavior change for ordinary replies."""
    words = text.split(" ")
    if not words:
        return [(text, "en")]

    tagged = []
    last_lang = "en"
    for w in words:
        lang = _classify_word(w, last_lang)
        tagged.append((w, lang))
        last_lang = lang

    runs: List[List] = []
    for w, lang in tagged:
        if runs and runs[-1][1] == lang:
            runs[-1][0].append(w)
        else:
            runs.append([[w], lang])

    if len(runs) <= 1:
        return [(text, runs[0][1] if runs else "en")]

    merged: List[List] = []
    for words_list, lang in runs:
        if merged and len(words_list) < _MIN_RUN_WORDS:
            merged[-1][0].extend(words_list)
        else:
            merged.append([words_list, lang])

    # A stray run at the very START has no earlier segment to fold into —
    # fold it forward into the next one instead.
    if len(merged) > 1 and len(merged[0][0]) < _MIN_RUN_WORDS:
        merged[1][0] = merged[0][0] + merged[1][0]
        merged.pop(0)

    return [(" ".join(words_list), lang) for words_list, lang in merged]


_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?।])\s+")


def split_into_sentences(text: str) -> List[str]:
    """
    Splits one segment's text into individual sentences on [.!?।] boundaries
    (the same boundary set main_window.py's _clip_for_speech already cuts
    on). Used only by the streaming TTS path: kokoro-onnx's own internal
    batching only splits when a segment exceeds ~510 phonemes, so a typical
    single-sentence-or-few reply (well under that, especially after the
    app's own MAX_SPOKEN_CHARS cap) becomes exactly ONE batch — meaning
    "streaming" plays no audio at all until the ENTIRE reply has finished
    synthesizing, which is most of the dead air users perceive as lag.
    Splitting per sentence here lets the first sentence start playing while
    later ones are still being synthesized in the background.
    """
    text = text.strip()
    if not text:
        return []
    parts = [p.strip() for p in _SENTENCE_BOUNDARY_RE.split(text) if p.strip()]
    return parts or [text]


_CLAUSE_BOUNDARY_RE = re.compile(r"(?<=[,،])\s+")
_MIN_LEAD_CLAUSE_CHARS = 2  # a shorter first piece is the whole point — only guard against a truly empty/degenerate split


def split_leading_clause(text: str, min_total_chars: int = 55) -> List[str]:
    """
    Splits off just the FIRST comma-bounded clause of `text`, leaving the
    rest as one piece — e.g. "Sir, the diagnostics are complete and
    everything looks healthy" -> ["Sir,", "the diagnostics are complete
    and everything looks healthy"]. Only used on the very first sentence of
    a reply, and only when that sentence is long enough
    (>= min_total_chars) that the split meaningfully helps: Kokoro must
    finish synthesizing the first sentence before ANY audio plays (see
    split_into_sentences), so for a long opening sentence, shrinking just
    that first piece is what actually determines how soon JARVIS starts
    speaking — everything after the first piece is already covered by the
    per-sentence streaming and background prefetch.
    """
    text = text.strip()
    if len(text) < min_total_chars:
        return [text]
    parts = _CLAUSE_BOUNDARY_RE.split(text, maxsplit=1)
    if len(parts) != 2:
        return [text]
    lead, rest = parts[0].strip(), parts[1].strip()
    if len(lead) < _MIN_LEAD_CLAUSE_CHARS or not rest:
        return [text]
    return [lead, rest]


def preprocess_for_speech(text: str) -> List[Tuple[str, str]]:
    """
    THE single entry point any TTS engine should call, before its own
    language detection or voice selection. Runs the full pipeline in order:
    markdown stripping -> preliminary pronunciation overrides (if Hindi/Hinglish)
    -> mixed-language segmentation -> per-segment pronunciation overrides.
    Returns [(segment_text, lang), ...] ready to hand to that engine's synthesis
    call, one call per segment, in order.

    Applying overrides upfront for Hindi context converts embedded English loanwords
    and names (e.g. 'Rohit', 'Chrome', 'open', 'WhatsApp') to Devanagari immediately,
    preventing them from triggering an accidental switch to the British English voice.
    """
    cleaned = strip_markdown_for_speech(text)
    if not cleaned:
        return []

    if getattr(config, "FORCE_HINDI_ONLY_SPEECH", False):
        # No English-voice branch at all: apply the loanword overrides
        # unconditionally (not just when the text already reads as Hindi
        # context) and skip segment_for_speech's language-run splitting —
        # the whole reply goes out as a single Hindi segment, so every word
        # is spoken by the Hindi voice with Hindi phonemization rules.
        # Sentence-level splitting for streaming still happens downstream
        # in kokoro_engine.py.
        return [(apply_pronunciation_overrides(cleaned, "hi"), "hi")]

    overall_lang = detect_language(cleaned)
    is_hindi_context = (overall_lang == "hi") or bool(_DEVANAGARI_UNICODE_RE.search(cleaned))

    # If the utterance is overall Hindi or contains Devanagari/Hinglish, apply
    # pronunciation overrides BEFORE segmentation so English loanwords (e.g.
    # "Rohit", "Chrome", "open", "WhatsApp", "system") are turned into Devanagari
    # upfront. This keeps the whole utterance unified under the natural Hindi voice.
    if is_hindi_context:
        cleaned = apply_pronunciation_overrides(cleaned, "hi")

    segments = segment_for_speech(cleaned)

    # Per-segment pass to catch any segment-level overrides
    processed = []
    for seg_text, seg_lang in segments:
        seg_text = seg_text.strip()
        if not seg_text:
            continue
        if is_hindi_context and seg_lang == "hi":
            seg_text = apply_pronunciation_overrides(seg_text, "hi")
        processed.append((seg_text, seg_lang))

    return processed

