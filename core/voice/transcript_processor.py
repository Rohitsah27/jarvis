"""
Transcript cleanup + custom-vocabulary correction for JARVIS's voice pipeline.
Runs entirely locally (regex + stdlib difflib fuzzy matching, zero new
dependencies, zero network calls) between STT output and intent detection —
fixes filler words and the specific technical terms Google's free speech API
routinely mangles in Hindi-English mixed speech, BEFORE anything is routed
to a tool or an LLM.
"""
import difflib
import re
from typing import Tuple

try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate as _sanscript_transliterate
    HAS_TRANSLITERATION = True
except Exception:
    HAS_TRANSLITERATION = False

# Filler words/sounds common in casual Hindi-English speech that add no
# intent signal and can confuse keyword matching if left in.
_FILLERS = {
    "um", "uh", "umm", "uhh", "matlab", "actually", "basically", "like",
    "you know", "haan", "toh", "na", "arre", "yaar",
}

# Canonical technical term -> known STT mis-hearings for that term. Checked
# as whole-phrase substitutions first (most reliable), longest phrases first
# so e.g. "local llm" matches before a bare "llm" inside it would.
_VOCAB_FIXES = {
    "JARVIS": ["jervis", "charvis", "jarvish", "jarvez", "jarvist", "jaarvis", "jaarvish"],
    "Claude": ["cloud", "clod", "clawd", "clode", "klod", "klaud"],
    "OpenClaw": ["open claw", "open clause", "open clock", "opencloud", "open cloud", "open klaw"],
    "CLI": ["see el eye", "seeli", "see-el-eye", "c l i"],
    "LLM": ["el el em", "ellum", "l l m", "elelem"],
    "TTS": ["tee tee es", "t t s", "teetees"],
    "STT": ["es tee tee", "s t t", "estitee"],
    "main.py": ["main dot pie", "main dot py", "main dot p y", "maine dot pie", "main daught pie", "main.pie"],
    "repository": ["repo zit ory", "reposatory", "repositry", "repazitory"],
    "Opus": ["oppus", "opas", "o p u s", "aupus"],
    "API": ["a p i", "eypeeai", "e p i", "a.p.i"],
    "local LLM": ["local el el em", "local ellum", "lokal llm"],
    "VS Code": ["vias code", "we as code", "visual code", "wiscode", "v s code", "vs cod", "visa code"],
    "cmd": ["see em dee", "c m d", "seemdee"],
    "Terminal": ["turminal", "terminel", "terminul", "termnal"],
}

# Longest-phrase-first so multi-word fixes (e.g. "local llm") take priority
# over any single-word fix that might also match part of the same phrase.
_VOCAB_FIXES_SORTED = sorted(
    ((canonical, variant) for canonical, variants in _VOCAB_FIXES.items() for variant in variants),
    key=lambda pair: len(pair[1]),
    reverse=True,
)

_ALL_CANONICAL_TERMS = list(_VOCAB_FIXES.keys())
_FUZZY_CANDIDATES = {term.lower(): term for term in _ALL_CANONICAL_TERMS}
_FUZZY_CANDIDATES_BARE = {re.sub(r"[^\w]", "", term).lower() for term in _ALL_CANONICAL_TERMS}


def clean_transcript(raw: str) -> str:
    """Strips filler words, normalizes whitespace/punctuation. Pure text
    hygiene — no vocabulary knowledge here, just noise removal."""
    if not raw:
        return ""
    text = raw.strip()
    # Remove filler words as whole words only (never mid-word).
    for filler in _FILLERS:
        text = re.sub(rf"\b{re.escape(filler)}\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def correct_vocabulary(text: str) -> Tuple[str, bool]:
    """
    Replaces known STT mis-hearings of technical terms with the correct
    spelling. Returns (corrected_text, was_fuzzy) — was_fuzzy is True when a
    correction relied on approximate word matching rather than an exact known
    mis-hearing, which callers can use as a signal to lower confidence
    slightly (we're less sure that guess was right).
    """
    if not text:
        return text, False

    corrected = text
    was_fuzzy = False

    # 1. Exact known mis-hearing phrases (highest confidence correction).
    lowered = corrected.lower()
    for canonical, variant in _VOCAB_FIXES_SORTED:
        pattern = r"\b" + re.escape(variant) + r"\b"
        if re.search(pattern, lowered):
            corrected = re.sub(pattern, canonical, corrected, flags=re.IGNORECASE)
            lowered = corrected.lower()

    # 2. Fuzzy fallback: catch novel mis-hearings not in the explicit list by
    # checking each word against the canonical vocabulary with a similarity
    # cutoff high enough to avoid over-correcting real, unrelated words.
    words = corrected.split()
    for i, word in enumerate(words):
        bare = re.sub(r"[^\w]", "", word).lower()
        # Skip words that are already an exact canonical term — comparing on
        # the punctuation-stripped form too, since e.g. "main.py" already
        # correct would otherwise strip to "mainpy" and not equal the
        # "main.py" dict key, causing an unnecessary (if harmless) fuzzy
        # re-match that wrongly flagged an already-exact correction as fuzzy.
        if len(bare) < 3 or bare in _FUZZY_CANDIDATES or bare in _FUZZY_CANDIDATES_BARE:
            continue
        matches = difflib.get_close_matches(bare, _FUZZY_CANDIDATES.keys(), n=1, cutoff=0.8)
        if matches:
            words[i] = _FUZZY_CANDIDATES[matches[0]]
            was_fuzzy = True
    corrected = " ".join(words)

    return corrected, was_fuzzy


# Devanagari has two distinct characters for the "candra" (nasalized/open)
# O and E sounds used almost exclusively to spell English loanwords in Hindi
# (ऑनलाइन "online", कॉफ़ी "coffee") — indic_transliteration's ITRANS table
# has no entry for them, so they pass through completely untransliterated
# and leak Devanagari characters into what should be pure Roman text.
# Folding them to the plain O/E matras first (a harmless approximation —
# both read the same in casual Hinglish spelling anyway) avoids that.
_CANDRA_VOWEL_FOLD = str.maketrans({
    "ॅ": "े",  # candra-E matra -> plain E matra
    "ॉ": "ो",  # candra-O matra -> plain O matra
    "ऍ": "ए",  # candra-E standalone -> plain E
    "ऑ": "ओ",  # candra-O standalone -> plain O
})

_DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")


def _delete_inherent_schwa(word: str) -> str:
    """
    ITRANS spells Hindi the way Sanskrit grammar says it should sound, not
    the way it's actually spoken — every consonant not followed by an
    explicit vowel sign gets a written-out 'a' (तुम -> "tuma", एक -> "eka"),
    even though Hindi speech drops most of those (tum, ek). ITRANS marks an
    EXPLICIT long-a matra as capital 'A' (क्या -> "kyA", a real vowel that
    must stay), so stripping only a trailing *lowercase* 'a' after a
    consonant removes just the silent grammatical one without touching a
    real vowel — a simple approximation of Hindi's schwa-deletion rule,
    not a full phonological model (it won't catch mid-word silent schwas).
    """
    if len(word) > 2 and word[-1] == "a" and word[-2].isalpha() and word[-2] not in "aeiouAEIOU":
        return word[:-1]
    return word


def to_hinglish_display(text: str) -> str:
    """
    Romanizes Devanagari Hindi text into casual "Hinglish" spelling — the
    way it's actually typed in WhatsApp/SMS (tum kya kar rahe ho), not
    formal Sanskrit-style transliteration (tuma kyA kara rahe ho). Display
    only: this is for showing a recognized voice command back to the user
    in a familiar, readable form, NOT for feeding into the AI pipeline —
    every language-detection path downstream (jarvis_brain, TTS
    segmentation, intent routing) keys off the real Devanagari Unicode
    range, so transliterating before that point would make Hindi speech
    silently misroute as English. Returns the input unchanged if it has no
    Devanagari at all, or if the transliteration library isn't installed.
    """
    if not text or not HAS_TRANSLITERATION or not _DEVANAGARI_RE.search(text):
        return text

    try:
        folded = text.translate(_CANDRA_VOWEL_FOLD)
        raw = _sanscript_transliterate(folded, sanscript.DEVANAGARI, sanscript.ITRANS)
    except Exception:
        return text

    parts = re.split(r"(\W+)", raw)
    parts = [_delete_inherent_schwa(p) if p.isalpha() else p for p in parts]
    out = "".join(parts)

    # ITRANS renders anusvara/chandrabindu (ं/ँ) as capital M or a ".N"
    # suffix — both read naturally as a plain "n" in casual spelling
    # (मैं -> "main", नहीं -> "nahin") once schwa-deletion above has run.
    out = out.replace(".N", "n").replace("~N", "n").replace("M", "n")
    out = out.lower()
    # ITRANS spells the danda (।) as "|"; WhatsApp-style text uses "." or
    # nothing — "." is closer to natural sentence punctuation than a pipe.
    out = out.replace("|", ".").replace("..", ".")
    out = re.sub(r"\s+([.,!?])", r"\1", out)
    return out.strip()
