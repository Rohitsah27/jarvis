"""
Local-first voice command router: the layer between "STT produced some text"
and "a tool gets executed / the LLM gets asked". Voice Activity Detection and
STT stay exactly where they were (ContinuousMicListenerThread); this module
picks up from there and does transcript cleanup, custom-vocabulary
correction, local intent detection with confidence scoring, and routing —
so a voice command is understood locally whenever possible, and the LLM is
only ever consulted for genuinely unclear requests. Every stage is logged
(raw/cleaned/corrected transcript, intent, confidence, action) via the
existing core.telemetry pipeline logger.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from core.ai.base import ToolCallRequest
from core.ai.brain import jarvis_brain
from core.voice.transcript_processor import clean_transcript, correct_vocabulary
from core.voice import learning_memory
from core.telemetry import log_stage

# Below this, a fast-path match is treated as "not sure enough to act on" —
# JARVIS asks a short clarifying question instead of guessing.
LOW_CONFIDENCE_THRESHOLD = 0.45

# Acknowledgment/filler-only words that carry no real request content on
# their own. Word COUNT alone isn't the right signal here — "diagnostics
# report" is only two words but genuinely meaningful, while "okay okay" is
# two words of nothing — so thinness is judged by whether every remaining
# word is in this set, not by length.
_ACK_ONLY_WORDS = {
    "okay", "ok", "k", "hmm", "hm", "uh", "um", "yeah", "yes", "no",
    "haan", "nahi", "nahin", "acha", "accha", "achha", "thik", "theek",
}


def _is_thin_utterance(text: str) -> bool:
    words = [w.strip(".,!? ") for w in text.lower().split() if w.strip(".,!? ")]
    return not words or all(w in _ACK_ONLY_WORDS for w in words)


@dataclass
class RoutingDecision:
    raw_transcript: str
    cleaned_transcript: str
    corrected_transcript: str
    intent: str                                   # tool name, "conversation", or "escalate_to_llm"
    confidence: float                              # 0.0 - 1.0
    source: str                                    # "fast" | "llm" | "clarify"
    tool_calls: List[ToolCallRequest] = field(default_factory=list)
    response_content: str = ""
    needs_clarification: bool = False


def _score_fast_path(corrected: str, was_fuzzy: bool) -> float:
    """
    Heuristic confidence for a fast-path match, built from observable signals
    rather than a heavyweight model (keeps this fast and local):
    - a fuzzy vocabulary correction was needed -> we're guessing, lower it
    - the command is extremely short/thin -> less signal to be sure about
    """
    confidence = 0.9
    if was_fuzzy:
        confidence -= 0.2
    word_count = len(corrected.split())
    if word_count <= 1:
        confidence -= 0.25
    elif word_count == 2:
        confidence -= 0.1
    return max(0.0, min(1.0, confidence))


def _clarification_question(lang: str, user: str) -> str:
    if lang == "hi":
        return f"क्षमा करें {user} जी, मुझे ठीक से समझ नहीं आया। क्या आप दोबारा साफ़ तरीके से बता सकते हैं?"
    return f"Sorry {user}, I didn't quite catch that clearly. Could you repeat the command?"


def route(raw_transcript: str, pipeline_t0: Optional[float] = None) -> RoutingDecision:
    """
    Runs the full local pipeline: clean -> correct vocabulary -> local intent
    match with confidence -> low confidence gets a clarification question,
    otherwise a confident local match executes directly, and only a genuine
    miss escalates to the LLM (using the corrected transcript, not the raw
    one, so the cloud model also benefits from the vocabulary fixes).
    """
    raw_transcript = raw_transcript or ""
    cleaned = clean_transcript(raw_transcript)
    corrected, was_fuzzy = correct_vocabulary(cleaned)

    log_stage("TRANSCRIPT_RAW", pipeline_t0, text=raw_transcript[:60])
    log_stage("TRANSCRIPT_CLEANED", pipeline_t0, text=cleaned[:60])
    log_stage("TRANSCRIPT_CORRECTED", pipeline_t0, text=corrected[:60], fuzzy=was_fuzzy)

    # If a past utterance close to this one previously confused JARVIS and
    # was then resolved (user rephrased, or the LLM understood it), swap in
    # the phrasing that actually worked before running intent matching — so
    # a recurring misheard/misunderstood phrase is understood immediately
    # instead of asking to repeat it again every time.
    learned = learning_memory.get_learned_correction(corrected)
    if learned and learned.strip().lower() != corrected.strip().lower():
        log_stage("TRANSCRIPT_LEARNED", pipeline_t0, text=learned[:60])
        corrected = learned
        was_fuzzy = False

    fast = jarvis_brain.try_fast_path(corrected)
    if fast:
        confidence = _score_fast_path(corrected, was_fuzzy)
        if learned:
            confidence = max(confidence, 0.85)
        intent = fast.tool_calls[0].tool_name if fast.tool_calls else "conversation"

        # <= (not <): a fuzzily-corrected one-word command scores EXACTLY
        # LOW_CONFIDENCE_THRESHOLD (0.9 - 0.2 fuzzy - 0.25 single-word =
        # 0.45) via _score_fast_path — that's precisely the scenario most
        # likely to be a misrecognition, so the boundary must fall on the
        # "ask for clarification" side, not "confident enough to act".
        if confidence <= LOW_CONFIDENCE_THRESHOLD:
            lang = jarvis_brain.detect_language(corrected)
            user = getattr(jarvis_brain, "_user_name", "Sir").split()[0]
            question = _clarification_question(lang, user)
            log_stage("INTENT", pipeline_t0, intent=intent, confidence=round(confidence, 2), source="clarify")
            log_stage("ACTION", pipeline_t0, action="ask_clarification")
            learning_memory.mark_awaiting_clarification(raw_transcript, corrected)
            return RoutingDecision(
                raw_transcript, cleaned, corrected, intent, confidence, "clarify",
                response_content=question, needs_clarification=True,
            )

        log_stage("INTENT", pipeline_t0, intent=intent, confidence=round(confidence, 2), source="fast")
        log_stage("ACTION", pipeline_t0, action=intent, tools=[c.tool_name for c in fast.tool_calls])
        learning_memory.resolve_pending_clarification(corrected)
        return RoutingDecision(
            raw_transcript, cleaned, corrected, intent, confidence, "fast",
            tool_calls=fast.tool_calls, response_content=fast.content,
        )

    # No local tool/command match. A short, thin utterance ("okay", "hmm")
    # isn't a real question either — the LLM can't do anything useful with it
    # and it's wasted latency/quota. Only genuinely substantial text (a real
    # question or statement) is worth escalating; anything else gets a
    # clarification instead of a pointless round-trip.
    if _is_thin_utterance(corrected):
        lang = jarvis_brain.detect_language(corrected)
        user = getattr(jarvis_brain, "_user_name", "Sir").split()[0]
        question = _clarification_question(lang, user)
        log_stage("INTENT", pipeline_t0, intent="unclear", confidence=0.2, source="clarify")
        log_stage("ACTION", pipeline_t0, action="ask_clarification")
        learning_memory.mark_awaiting_clarification(raw_transcript, corrected)
        return RoutingDecision(
            raw_transcript, cleaned, corrected, "unclear", 0.2, "clarify",
            response_content=question, needs_clarification=True,
        )

    log_stage("INTENT", pipeline_t0, intent="unrecognized", confidence=0.3, source="llm")
    log_stage("ACTION", pipeline_t0, action="escalate_to_llm")
    return RoutingDecision(raw_transcript, cleaned, corrected, "escalate_to_llm", 0.3, "llm")


def resolve_llm_success(corrected_transcript: str) -> None:
    """Call after the LLM successfully handles an escalated command, so if it
    followed a clarification question, that resolution is remembered too."""
    learning_memory.resolve_pending_clarification(corrected_transcript)
