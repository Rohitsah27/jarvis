"""
JARVIS Cognitive Neural Brain & Reasoning Core.
Provides real-time contextual intelligence, voice awareness, live time/date/telemetry,
mathematical calculations, encyclopedic web knowledge, and desktop automation tools.
Zero-lag, always offline-capable, and culturally fluent in Hindi, Hinglish, and English.
"""
import re
import math
import time
import datetime
import urllib.request
import urllib.parse
import json
from typing import Optional, List, Tuple

import psutil
from app.config import config
from core.ai.base import AIResponse, ToolCallRequest


class JarvisBrain:
    """Cognitive intelligence and intent understanding engine for JARVIS."""

    # Shared "open"-verb synonyms (all common Hindi conjugations + Devanagari
    # forms + English) for stripping filler words when deriving a search
    # query/app name from a command. This list was previously duplicated
    # ad-hoc in 3 different places, each missing different conjugations —
    # e.g. "kholna" (a very common form) was absent from the YouTube/browser
    # query cleanup, so "youtube kholna" left "kholna" as the literal search
    # term instead of recognizing it as "just open YouTube".
    _OPEN_SYNONYMS = r"open|kholo|khol|kholna|kholey|launch|खोलो|खोलना|खोल"

    # None of the app-specific "open X" branches below (chrome/browser,
    # notepad, vs code, calculator) ever check whether the user actually
    # said close/exit instead of open — a bare app-name keyword matches
    # regardless. Found via testing: "chrome band karo" (close Chrome) was
    # confidently (0.9) matched as open_browser, i.e. it did the exact
    # opposite of what was asked. Used by the early guard in _match_intent()
    # that escalates close+app-name combos to the LLM instead (its
    # close_application tool already handles this correctly) rather than
    # patching every individual open-branch.
    _CLOSE_SYNONYMS = r"close|band|bandh|बंद|quit|exit"
    _KNOWN_APP_KEYWORDS = [
        "chrome", "क्रोम", "browser", "ब्राउजर", "ब्राउज़र", "google", "गूगल",
        "youtube", "यूट्यूब", "notepad", "नोटपैड", "vs code", "vscode",
        "visual studio", "calculator", "कैलकुलेटर", "calc", "whatsapp", "व्हाट्सएप",
        "spotify", "स्पॉटिफाई", "excel", "एक्सेल", "word", "वर्ड", "paint", "पेंट",
        "explorer", "cmd", "terminal", "task manager",
    ]

    @staticmethod
    def _word_pattern(alternation: str) -> str:
        """
        A \\b-alternative for building word-matching regexes that actually
        works for Devanagari text. Python's \\b (and \\w) is built on Unicode
        letter/number categories and does NOT include combining vowel signs
        (matras like ो/ा — Unicode category Mc) — so \\bखोलना\\b silently
        fails to match "खोलना" at all, because \\b triggers a false word
        boundary between ख and its own vowel sign ो. Anchoring on whitespace/
        string-edges instead of \\w-transitions sidesteps this entirely, and
        works the same for plain ASCII/Latin terms too.
        """
        return rf"(?:(?<=^)|(?<=\s))(?:{alternation})(?=\s|$)"

    def __init__(self):
        self._user_name = config.USER_NAME or "Sir"

    @staticmethod
    def detect_language(text: str) -> str:
        """
        Determines whether user query is predominantly Hindi/Hinglish or
        English. Every caller of this (both here in brain.py and in
        groq_provider.py/intent_router.py) uses the result to pick which
        language to RESPOND in, not to classify the user's input for
        matching purposes \u2014 so forcing "hi" here when the voice pipeline
        is Hindi-only correctly cascades to every one of those response
        strings from a single point, instead of needing each one edited
        individually. Without this, JARVIS's local offline/fast-path
        brain kept replying in English for English-leaning input (e.g. its
        startup greeting), which the forced Hindi voice can't actually
        pronounce \u2014 the same bug already fixed for the main LLM and the
        screen-analysis tool.
        """
        if getattr(config, "FORCE_HINDI_ONLY_SPEECH", False):
            return "hi"
        if re.search(r"[\u0900-\u097F]", text):
            return "hi"
        hinglish_markers = {
            "mera", "meri", "mere", "awaaz", "aawaz", "sunai", "de", "raha", "rahi", "rahe",
            "hai", "hain", "kya", "batao", "kholo", "khol", "dikhao", "dikh", "kaun", "kaise", "kaisa",
            "karo", "kar", "kariye", "tum", "aap", "namaste", "shukriya", "dhanyawad", "chalao", "roko",
            "samay", "aaj", "din", "kitna", "kitni", "bataiye", "bolo", "bol", "main", "hum", "mujhe",
            "usmein", "usme", "ismein", "isme", "sakte", "sakta", "sakti", "ho", "hoon", "hun",
            "gana", "gaana", "gaane", "bajao", "lagao", "sunao", "accha", "achha", "koi", "kuch"
        }
        words = set(re.findall(r"\b[a-zA-Z]+\b", text.lower()))
        if len(words & hinglish_markers) >= 1:
            return "hi"
        return "en"

    def _get_live_telemetry(self) -> dict:
        """Fetches live hardware telemetry stats."""
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            batt = psutil.sensors_battery()
            battery_pct = batt.percent if batt else 100
            is_charging = batt.power_plugged if batt else True
            return {
                "cpu": cpu,
                "ram": ram,
                "battery": battery_pct,
                "charging": is_charging
            }
        except Exception:
            return {"cpu": 15, "ram": 45, "battery": 95, "charging": True}

    def _query_encyclopedia(self, query: str, lang: str = "en") -> Optional[str]:
        """Queries Wikipedia API for instant encyclopedic knowledge in < 300ms."""
        # Clean query
        cleaned = re.sub(
            r"\b(who is|what is|tell me about|explain|who was|what are|kya hai|kaun hai|ke baare mein batao)\b",
            "",
            query,
            flags=re.IGNORECASE
        ).strip()
        cleaned = re.sub(r"[^\w\s]", "", cleaned).strip()
        if not cleaned or len(cleaned) < 2:
            return None

        # Try Wikipedia Summary
        subdomain = "hi" if lang == "hi" else "en"
        url = f"https://{subdomain}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(cleaned)}"
        req = urllib.request.Request(url, headers={"User-Agent": "JarvisAssistant/2.0"})
        try:
            with urllib.request.urlopen(req, timeout=1.8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                extract = data.get("extract", "")
                if extract:
                    # Return first 2 concise sentences
                    sentences = re.split(r"(?<=[.!?।])\s+", extract)
                    summary = " ".join(sentences[:2]).strip()
                    return summary
        except Exception:
            pass

        # Fallback to English Wikipedia if Hindi was empty
        if lang == "hi":
            try:
                url_en = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(cleaned)}"
                req_en = urllib.request.Request(url_en, headers={"User-Agent": "JarvisAssistant/2.0"})
                with urllib.request.urlopen(req_en, timeout=1.8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    extract = data.get("extract", "")
                    if extract:
                        sentences = re.split(r"(?<=[.!?])\s+", extract)
                        return " ".join(sentences[:2]).strip()
            except Exception:
                pass

        return None

    # Words that mean this is a natural-language range ("2-3 years", "5-6
    # log"), not arithmetic — "2-3 साल" should never be evaluated as -1.
    _RANGE_UNIT_WORDS = (
        r"साल|दिन|लोग|घंटे|मिनट|सेकंड|बार|महीने|हफ्ते|बजे|"
        r"saal|din|dino|log|logo|ghante|minute|minutes|second|seconds|"
        r"baar|bar|mahine|hafte|baje|years?|days?|hours?|times|people|"
        r"o'?clock|am|pm"
    )

    def _math_expr_match(self, cleaned: str):
        """
        Finds a genuine arithmetic pattern (e.g. '500 * 24'), excluding cases
        immediately followed by a range/unit word ('2-3 saal' is a range,
        not a subtraction) — shared by the trigger check and the evaluator so
        they can never disagree about what counts as "looks like math".
        """
        # \b right after each number is essential: without it, a failed
        # lookahead (e.g. "9-11 baje") makes the regex engine backtrack the
        # greedy \d+ down to a partial number ("9-1") that happens to dodge
        # the lookahead, silently matching the wrong (truncated) expression.
        return re.search(
            r"(\d+(\.\d+)?\b\s*[\+\-\*/\^]\s*\d+(\.\d+)?\b)"
            rf"(?!\s*(?:{self._RANGE_UNIT_WORDS})\b)",
            cleaned,
        )

    def _evaluate_math(self, text: str) -> Optional[float]:
        """Safely parses and evaluates basic arithmetic expressions."""
        # Check for arithmetic operators and digits
        cleaned = text.lower().replace("x", "*").replace("times", "*").replace("divided by", "/").replace("plus", "+").replace("minus", "-")
        # Extract math pattern e.g. 500 * 24 or 15 + 35 — but NOT when it's
        # immediately followed by a range/unit word, which previously made
        # ambient noise mis-heard as e.g. "2-3 साल के बाद" get "answered"
        # with -1.0.
        m = self._math_expr_match(cleaned)
        if m:
            expr = m.group(1).replace("^", "**")
            try:
                # Safe eval of numbers and operators only
                if re.match(r"^[\d\.\s\+\-\*/\(\)]+$", expr):
                    result = eval(expr, {"__builtins__": None}, {})
                    return round(float(result), 2)
            except Exception:
                pass

        # Percentages e.g. "15% of 2000" or "20 percent of 500"
        m_pct = re.search(r"(\d+(\.\d+)?)\s*(%|percent)\s*(of|ka)?\s*(\d+(\.\d+)?)", cleaned)
        if m_pct:
            try:
                p = float(m_pct.group(1))
                val = float(m_pct.group(5))
                return round((p / 100.0) * val, 2)
            except Exception:
                pass

        return None

    def _extract_song_query(self, prompt: str) -> str:
        """Extracts specific song/artist/video name from natural speech prompt."""
        lowered = prompt.lower().strip()
        cleaned = re.sub(
            r"^(main bol raha hun ki|main bol raha hu ki|main keh raha hoon ki|main keh raha hu ki|kya tum|jarvis|hey jarvis|hello jarvis|please|bhai|sir|listen|suno)\s*",
            "",
            lowered,
            flags=re.IGNORECASE
        )
        cleaned = re.sub(r"\b(khol ke usmein|khol ke usme|khol kar usmein|khol ke|khol kar|usmein|usme|kholo aur|khol do aur|khol do|kholna|khol)\b", "", cleaned)
        cleaned = re.sub(r"\b(in youtube|on youtube|in youtue|on youtue|from youtube|youtube par|youtube pe|youtube per|youtube me|youtube mein|on yt|in yt|yt pe|yt par|yt per|यूट्यूब पर|यूट्यूब पे|youtube|youtue|yt|यूट्यूब)\b", "", cleaned)
        cleaned = re.sub(r"\b(kar sakte ho|kar sakte|kar do|karo|kariye|sakoge|chala do|chalao|bajao|lagao|lagana|lagado|laga do|lagayein|sunao|play|search for|search|play karo|chalao na|bajao na)\b", "", cleaned)
        cleaned = re.sub(r"\b(a song|some song|some songs|song|songs|gana|gaana|gaane|music|track|tracks|video|videos|koi|ek|accha|achha|acha|achha sa|accha sa)\b", "", cleaned)
        cleaned = re.sub(r"\b(ke|ka|ki|ko|se|per|par)\b", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _get_youtube_video_url(self, query: str) -> str:
        """
        Fast resolution of YouTube search query into direct playable video URL.
        Scrapes first video ID within 2 seconds, falling back to YouTube search results.
        """
        cleaned_query = query.strip()
        encoded = urllib.parse.quote_plus(cleaned_query)
        search_url = f"https://www.youtube.com/results?search_query={encoded}"

        try:
            req = urllib.request.Request(
                search_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                matches = re.findall(r"/watch\?v=([a-zA-Z0-9_-]{11})", html)
                if matches:
                    return f"https://www.youtube.com/watch?v={matches[0]}"
        except Exception:
            pass

        return search_url

    def think(self, prompt: str) -> AIResponse:
        """
        Main cognitive reasoning pipeline — ALWAYS returns a usable response,
        used as the fully-offline fallback when no LLM is reachable.
        """
        content, tool_calls, start_t = self._match_intent(prompt)
        if content is None:
            # Nothing matched with confidence — this is the generic catch-all,
            # only reachable here (never from try_fast_path).
            content, tool_calls = self._fallback_response(prompt)

        latency = (time.perf_counter() - start_t) * 1000.0
        return AIResponse(
            content=content,
            provider_name="JARVIS Cognitive Brain",
            model_name="Neural Core 2.0",
            latency_ms=latency,
            tool_calls=tool_calls,
        )

    def try_fast_path(self, prompt: str) -> Optional[AIResponse]:
        """
        Local, zero-network intent routing for common/simple commands (open app,
        volume, media, window, lock, tabs, YouTube/song, screenshot, time/date,
        system status, small talk, math, encyclopedia). Returns None when the
        request isn't one of these confidently-recognized patterns, so the
        caller can escalate to the real LLM planner instead of guessing.
        """
        content, tool_calls, start_t = self._match_intent(prompt)
        if content is None:
            return None
        latency = (time.perf_counter() - start_t) * 1000.0
        return AIResponse(
            content=content,
            provider_name="JARVIS Fast Path",
            model_name="Local Intent Router",
            latency_ms=latency,
            tool_calls=tool_calls,
        )

    def _fallback_response(self, prompt: str) -> Tuple[str, List[ToolCallRequest]]:
        """The generic catch-all used only by think() (full offline mode)."""
        raw = prompt.strip()
        lowered = raw.lower()
        lang = self.detect_language(raw)
        tool_calls: List[ToolCallRequest] = []

        if re.search(self._word_pattern(self._OPEN_SYNONYMS), lowered):
            cleaned_app = re.sub(self._word_pattern(self._OPEN_SYNONYMS), "", lowered).strip()
            tool_calls.append(ToolCallRequest(tool_name="open_browser", arguments={"query": cleaned_app, "new_tab": False}))
            content = f"सर, कन्फर्म कर रहा हूँ। अभी {cleaned_app} खोला जा रहा है।" if lang == "hi" else f"Acknowledged Sir, opening {cleaned_app} now."
        else:
            wiki_backup = self._query_encyclopedia(raw, lang=lang)
            if wiki_backup:
                content = f"सर: {wiki_backup}"
            elif lang == "hi":
                content = f"सर, मैंने आपका संदेश '{raw}' सुन लिया है। मैं पूरी तरह सक्रिय हूँ और आपके अगले आदेश की प्रतीक्षा कर रहा हूँ।"
            else:
                content = f"Sir, I have registered your directive: '{raw}'. Standing by for your next instruction."
        return content, tool_calls

    def _match_intent(self, prompt: str):
        """
        Shared pattern-matching core. Returns (content, tool_calls, start_t).
        `content` is None only when nothing below confidently matched — i.e.
        we fell all the way through to where the old generic catch-all used
        to live. think() fills that gap with _fallback_response(); try_fast_path()
        treats None as "not a fast-path case, ask the real LLM".
        """
        start_t = time.perf_counter()
        raw = prompt.strip()
        lowered = raw.lower()
        lang = self.detect_language(raw)
        tool_calls: List[ToolCallRequest] = []
        user = self._user_name.split()[0] if self._user_name else "Sir"
        content: Optional[str] = None

        # Close-intent guard (see _CLOSE_SYNONYMS above): a close/exit verb
        # alongside a recognized app name means "close that app", never
        # "open" it — escalate rather than let a later open-branch guess
        # wrong with high confidence.
        if (
            re.search(self._word_pattern(self._CLOSE_SYNONYMS), lowered)
            and any(k in lowered for k in self._KNOWN_APP_KEYWORDS)
        ):
            return None, [], start_t

        # -------------------------------------------------------------
        # 1. Voice & Auditory Feedback (e.g. "Can you hear me", "Mera Awaaz Sunai de raha hai")
        # -------------------------------------------------------------
        if any(p in lowered for p in [
            "mera awaaz", "meri awaz", "meri aawaz", "sunai de raha", "sun rahe ho",
            "awaz aa rahi", "aawaaz aa rahi", "can you hear me", "can you hear my voice",
            "are you listening", "sun pa rahe ho", "kya meri awaz", "sun sakte ho"
        ]) or (
            ("awaaz" in lowered or "awaz" in lowered or "voice" in lowered or "hear" in lowered) and
            any(w in lowered for w in ["sun", "hear", "a rahi", "aa rahi", "clear", "test", "check"])
        ):
            if lang == "hi":
                content = f"हाँ {user}! मैं आपकी आवाज़ बिल्कुल साफ़ और स्पष्ट सुन रहा हूँ। आपका माइक्रोफ़ोन एकदम सही काम कर रहा है। बताइए, मैं आपकी क्या सहायता करूँ?"
            else:
                content = f"Yes {user}, I can hear you loud and clear. Your microphone audio stream is crystal clear and all systems are fully attentive."

        # -------------------------------------------------------------
        # 2. Name Calling & Presence ("Abhishek", "Rohit", "JARVIS", "Hello JARVIS")
        # -------------------------------------------------------------
        elif any(lowered == name for name in ["abhishek", "rohit", "jarvis", "hello jarvis", "hey jarvis", "hi jarvis", "sir", "sirji"]):
            if lang == "hi":
                content = f"{user}, मैं यहीं हूँ। आज्ञा दीजिए, क्या निर्देश है?"
            else:
                content = f"At your command, {user}. How may I assist you today?"

        # -------------------------------------------------------------
        # 3. Dynamic Real-Time Clock & Date
        # -------------------------------------------------------------
        elif any(k in lowered for k in [
            "time kya hua", "samay kya hua", "what time is it", "current time", "time batao",
            "kitne baje", "aaj konsa din", "aaj kya din hai", "what day is it", "today's date",
            "aaj ki date", "tarikh kya hai", "aaj konsi tarikh"
        ]):
            now = datetime.datetime.now()
            time_str = now.strftime("%I:%M %p")
            hindi_days = ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"]
            day_hi = hindi_days[now.weekday()]
            date_hi = f"{now.day} {now.strftime('%B')} {now.year}"
            date_en = now.strftime("%A, %B %d, %Y")

            if "date" in lowered or "tarikh" in lowered or "तारीख" in lowered or "दिन" in lowered:
                if lang == "hi":
                    content = f"सर, आज {day_hi}, {date_hi} है और वर्तमान समय {time_str} है।"
                else:
                    content = f"Sir, today is {date_en}, and the current time is {time_str}."
            else:
                if lang == "hi":
                    content = f"सर, अभी समय {time_str} हुआ है।"
                else:
                    content = f"Sir, the time is currently {time_str}."

        # -------------------------------------------------------------
        # 4. Real-Time Hardware & Battery Telemetry
        # -------------------------------------------------------------
        elif any(k in lowered for k in [
            "battery", "बैटर", "चार्ज", "cpu", "ram", "रैम", "सिस्टम स्थिति",
            "laptop status", "pc status", "system health", "system status", "hardware"
        ]):
            stats = self._get_live_telemetry()
            tool_calls.append(ToolCallRequest(tool_name="get_system_status", arguments={}))
            if lang == "hi":
                charging_txt = "चार्जिंग पर है" if stats["charging"] else "बैटरी पर चल रहा है"
                content = (
                    f"सर, आपके लैपटॉप की बैटरी {stats['battery']}% {charging_txt}। "
                    f"सीपीयू लोड {stats['cpu']}% और रैम यूसेज {stats['ram']}% है। सिस्टम एकदम स्मूथ काम कर रहा है।"
                )
            else:
                charging_txt = "plugged in" if stats["charging"] else "on battery"
                content = (
                    f"Sir, system battery is at {stats['battery']}% ({charging_txt}). "
                    f"CPU load is at {stats['cpu']}%, and RAM consumption is {stats['ram']}%. All operational metrics are optimal."
                )

        # -------------------------------------------------------------
        # 5. Screen Vision Analysis (Deep Eye on Desktop)
        # -------------------------------------------------------------
        elif any(k in lowered for k in [
            "what is showing in this screen", "what is showing on this screen", "what is showing on screen",
            "what is on my screen", "what's on my screen", "what is in this screen",
            "analyze my screen", "analyse my screen", "analyze screen", "analyse screen",
            "screen pe kya hai", "screen par kya dikh raha hai", "screen par kya hai",
            "स्क्रीन पर क्या दिख रहा है", "स्क्रीन देखो", "स्क्रीन एनालाइज करो"
        ]) or (
            ("screen" in lowered or "स्क्रीन" in lowered) and
            any(w in lowered for w in ["what", "showing", "see", "look", "analyze", "check", "tell", "क्या", "देखो", "बताओ"])
        ):
            from core.system.screen_analyzer import screen_analyzer
            analysis = screen_analyzer.analyze_screen(prompt)
            if any(w in lowered for w in ["open", "launch", "खोलो"]) and any(b in lowered for b in ["chrome", "browser", "क्रोम"]):
                tool_calls.append(ToolCallRequest(tool_name="open_browser", arguments={"query": "", "url": ""}))
            tool_calls.append(ToolCallRequest(tool_name="analyze_screen", arguments={"query": prompt}))
            content = analysis["answer"]

        # -------------------------------------------------------------
        # 6. Master Volume Controls (Hinglish, Hindi, English)
        # -------------------------------------------------------------
        is_vol_down = any(k in lowered for k in [
            "volume down", "decrease volume", "quieter", "lower volume", "reduce volume", "turn down",
            "awaaz kam", "awaz kam", "aawaz kam", "awaaz thoda kam", "awaz thoda kam", "aawaz thoda kam",
            "awaaz thodi kam", "awaz thodi kam", "thoda kam", "thodi kam", "kam kar do", "kam karo", "kam kardo",
            "volume kam", "dheere karo", "dheemi karo", "sound kam", "आवाज़ कम", "आवाज कम", "वॉल्यूम कम",
            "घटाओ", "धीमी करो", "धीमा करो", "कम करो"
        ]) or (
            ("awaaz" in lowered or "awaz" in lowered or "volume" in lowered or "sound" in lowered) and
            any(w in lowered for w in ["kam", "ghatao", "dheere", "dheemi", "slow", "down", "lower", "reduce", "decrease"])
        )

        is_vol_up = any(k in lowered for k in [
            "volume up", "increase volume", "louder", "turn up", "raise volume", "higher volume",
            "awaaz badhao", "awaz badhao", "aawaz badhao", "awaaz thoda badhao", "awaz thoda badhao",
            "awaaz tej", "awaz tej", "volume badhao", "volume increase", "thoda badhao", "thodi badhao",
            "badha do", "badhao", "tez karo", "tej karo", "sound badhao", "sound tej",
            "आवाज़ बढ़ाओ", "आवाज बढ़ाओ", "वॉल्यूम तेज", "वॉल्यूम बढ़ाओ", "तेज़ करो", "बढ़ाओ"
        ]) or (
            ("awaaz" in lowered or "awaz" in lowered or "volume" in lowered or "sound" in lowered) and
            any(w in lowered for w in ["badhao", "tej", "tez", "increase", "up", "raise", "loud", "louder", "high", "higher"])
        )

        # "mute"/"unmute" need word boundaries — "commute" contains "mute" as
        # a bare substring and would otherwise silently mute the system.
        is_vol_mute = any(k in lowered for k in [
            "म्यूट", "awaaz band", "awaz band", "sound band", "chup ho jao", "chup raho", "shant ho jao"
        ]) or re.search(r"\b(mute|unmute)\b", lowered)

        if is_vol_down:
            tool_calls.append(ToolCallRequest(tool_name="control_volume", arguments={"action": "down"}))
            content = "सर, आवाज़ कम कर दी गई है।" if lang == "hi" else "Volume lowered, Sir."

        elif is_vol_up:
            tool_calls.append(ToolCallRequest(tool_name="control_volume", arguments={"action": "up"}))
            content = "सर, आवाज़ बढ़ा दी गई है।" if lang == "hi" else "Volume increased, Sir."

        elif is_vol_mute:
            tool_calls.append(ToolCallRequest(tool_name="control_volume", arguments={"action": "mute"}))
            content = "सर, ऑडियो म्यूट कर दिया गया है।" if lang == "hi" else "Audio muted, Sir."

        # -------------------------------------------------------------
        # 7. Media Playback Controls (Pause, Stop, Next, Previous)
        # -------------------------------------------------------------
        elif any(k in lowered for k in [
            "pause", "resume", "stop music", "pause music", "stop song", "pause song", "stop playing",
            "gana band", "gaana band", "song band", "music band", "gana roko", "gaana roko", "song roko",
            "पॉज करो", "म्यूजिक रोको", "गाना रोको", "गाना बंद", "गाना बंद करो", "संगीत रोको",
            "next song", "next track", "अगला गाना", "previous song", "prev song", "पिछला गाना", "media toggle"
        ]):
            m_action = "play_pause"
            if any(k in lowered for k in ["next", "अगला"]):
                m_action = "next"
                content = "सर, अगला ट्रैक प्ले किया जा रहा है।" if lang == "hi" else "Skipping to next track, Sir."
            elif any(k in lowered for k in ["previous", "prev", "पिछला"]):
                m_action = "previous"
                content = "सर, पिछला ट्रैक प्ले किया जा रहा है।" if lang == "hi" else "Playing previous track, Sir."
            elif any(k in lowered for k in ["pause", "stop", "पॉज", "रोको", "बंद", "band"]):
                m_action = "pause"
                content = "सर, मीडिया पॉज कर दिया गया है।" if lang == "hi" else "Media playback paused, Sir."
            else:
                content = "सर, मीडिया प्ले/पॉज टॉगल किया गया है।" if lang == "hi" else "Toggling media playback, Sir."
            tool_calls.append(ToolCallRequest(tool_name="control_media", arguments={"action": m_action}))

        # -------------------------------------------------------------
        # 8. Browser Tab Controls (Switch, Next, Previous, Close, New)
        # -------------------------------------------------------------
        elif any(k in lowered for k in [
            "switch tab", "switch tabs", "next tab", "dusra tab", "dusre tab",
            "dusre tab par jao", "dusre tab pe jao", "dusre tab me jao", "agle tab",
            "agle tab par jao", "agle tab me jao", "agla tab", "tab badlo", "tab change karo",
            "change tab", "change tabs", "अगला टैब", "टैब बदलो", "टैब चेंज करो", "दूसरे टैब", "अगले टैब",
            "previous tab", "prev tab", "pichla tab", "pichle tab", "pichle tab par jao",
            "pichle tab pe jao", "pichle tab me jao", "peeche wala tab", "peeche wale tab",
            "back tab", "पिछला टैब", "पिछले टैब",
            "close tab", "close this tab", "close current tab", "tab band karo",
            "is tab ko band", "yeh tab band", "ye tab band", "tab close karo", "tab hatao",
            "टैब बंद करो", "टैब बंद", "टैब क्लोज़ करो",
            "naya tab kholo", "naya tab open", "create new tab", "new tab", "नया टैब", "नए टैब"
        ]) and not any(w in lowered for w in ["play", "gana", "gaana", "music", "song"]):
            if any(k in lowered for k in [
                "close tab", "close this tab", "close current tab", "tab band karo",
                "is tab ko band", "yeh tab band", "ye tab band", "tab close karo", "tab hatao",
                "टैब बंद करो", "टैब बंद", "टैब क्लोज़ करो"
            ]):
                tool_calls.append(ToolCallRequest(tool_name="control_tabs", arguments={"action": "close"}))
                content = "सर, वर्तमान टैब बंद कर दिया गया है।" if lang == "hi" else "Current browser tab closed, Sir."

            elif any(k in lowered for k in [
                "previous tab", "prev tab", "pichla tab", "pichle tab", "pichle tab par jao",
                "pichle tab pe jao", "pichle tab me jao", "peeche wala tab", "peeche wale tab",
                "back tab", "पिछला टैब", "पिछले टैब"
            ]):
                tool_calls.append(ToolCallRequest(tool_name="control_tabs", arguments={"action": "previous"}))
                content = "सर, पिछले टैब पर स्विच कर दिया गया है।" if lang == "hi" else "Switched to previous browser tab, Sir."

            elif any(k in lowered for k in [
                "naya tab kholo", "naya tab open", "create new tab", "new tab", "नया टैब", "नए टैब"
            ]):
                tool_calls.append(ToolCallRequest(tool_name="control_tabs", arguments={"action": "new"}))
                content = "सर, नया ब्लैंक टैब खोल दिया गया है।" if lang == "hi" else "New browser tab opened, Sir."

            else:
                tool_calls.append(ToolCallRequest(tool_name="control_tabs", arguments={"action": "next"}))
                content = "सर, अगले टैब पर स्विच कर दिया गया है।" if lang == "hi" else "Switched to next browser tab, Sir."

        # -------------------------------------------------------------
        # 9. YouTube Music, Song & Video Playback Engine (Active Tab Default)
        # -------------------------------------------------------------
        elif any(k in lowered for k in [
            "play a song", "play song", "play songs", "play music", "play track", "play tracks",
            "play some music", "play some songs", "song play", "songs play", "music play",
            "gana play", "gaana play", "gana chalao", "gaana chalao", "gana bajao", "gaana bajao",
            "gana lagao", "gaana lagao", "gana lagana", "gaana lagana", "song lagana", "song lagao",
            "gaane sunao", "gana sunao", "gaane chalao", "gaane bajao", "original song lagana",
            "koi gana", "koi song", "khol ke usmein song play", "khol ke usme song play",
            "khol ke song play", "usmein song play", "usme song play", "song play kar",
            "gana play kar", "gaane play", "music chalao", "music lagao", "music bajao",
            "chalao gana", "bajao gana", "lagao gana", "play youtue", "play youtube"
        ]) or (
            any(y in lowered for y in ["youtube", "youtue", "yt", "यूट्यूब"]) and
            any(w in lowered for w in [
                "play", "song", "songs", "music", "gana", "gaana", "gaane", "track", "tracks",
                "video", "videos", "chalao", "bajao", "lagao", "lagana", "sunao", "chalisa", "bhajan", "ghazal",
                "प्ले", "गाना", "गीत", "सॉन्ग", "म्यूजिक", "चलाओ", "बजाओ", "लगाओ", "सुनाओ"
            ])
        ) or (
            ("khol" in lowered or "open" in lowered) and ("song" in lowered or "gana" in lowered or "gaana" in lowered or "music" in lowered)
        ) or (
            lowered.startswith("play ") and not any(a in lowered for a in ["game", "video game", "control", "window"])
        ) or (
            any(v in lowered for v in ["chalao", "bajao", "lagao", "lagana", "sunao"]) and any(w in lowered for w in ["song", "gana", "gaana", "gaane", "music"])
        ):
            # Check if user instructed to switch tab first
            wants_tab_switch = any(k in lowered for k in ["switch tab", "next tab", "dusre tab", "agle tab", "tab badlo"])
            if wants_tab_switch:
                tool_calls.append(ToolCallRequest(tool_name="control_tabs", arguments={"action": "next"}))

            # Only open a new tab if user explicitly asked for one
            is_new_tab = any(k in lowered for k in ["new tab", "naya tab", "naye tab", "नए टैब", "नया टैब", "in a new tab"])

            song_name = self._extract_song_query(raw)
            if song_name:
                search_query = f"{song_name} song" if not any(w in song_name for w in ["song", "music", "video", "chalisa", "bhajan", "ghazal", "track"]) else song_name
                display_name = song_name.title()
                tab_desc = "नए टैब में" if is_new_tab else "एक्टिव टैब में"
                if lang == "hi":
                    content = f"{user}, बिल्कुल! यूट्यूब पर {tab_desc} '{display_name}' चलाया जा रहा है।"
                else:
                    target_tab = "new tab" if is_new_tab else "current tab"
                    content = f"Certainly {user}, playing '{display_name}' in your {target_tab} on YouTube."
            else:
                search_query = "top trending bollywood songs" if lang == "hi" else "top trending hit songs"
                tab_desc = "नए टैब में" if is_new_tab else "एक्टिव टैब में"
                if lang == "hi":
                    content = f"{user}, बिल्कुल! यूट्यूब पर {tab_desc} पसंदीदा गाने प्ले किए जा रहे हैं।"
                else:
                    target_tab = "new tab" if is_new_tab else "current tab"
                    content = f"Right away {user}, playing songs in your {target_tab} on YouTube."

            yt_url = self._get_youtube_video_url(search_query)
            tool_calls.append(ToolCallRequest(tool_name="open_browser", arguments={"url": yt_url, "query": "", "new_tab": is_new_tab}))

        # -------------------------------------------------------------
        # 10. Window Controls (Minimize, Maximize, Close window/app)
        # -------------------------------------------------------------
        elif any(k in lowered for k in [
            "minimize", "minimise", "मिनिमाइज़", "छोटा करो",
            "maximize", "maximise", "मैक्सिमाइज", "बड़ा करो", "फुल स्क्रीन",
            "close window", "close app", "विंडो बंद करो", "क्लोज़ करो",
            "close chrome", "क्रोम बंद करो"
        ]):
            action = "minimize"
            app = ""
            if any(k in lowered for k in ["maximize", "maximise", "बड़ा करो", "फुल स्क्रीन"]):
                action = "maximize"
            elif any(k in lowered for k in ["close", "बंद करो", "क्लोज़"]):
                action = "close"

            if "chrome" in lowered or "क्रोम" in lowered:
                app = "chrome"
            elif "code" in lowered or "vs code" in lowered:
                app = "code"
            elif "notepad" in lowered or "नोटपैड" in lowered:
                app = "notepad"

            tool_calls.append(ToolCallRequest(tool_name="control_window", arguments={"action": action, "app": app}))
            if lang == "hi":
                content = f"सर, {app or 'विंडो'} को {action} किया जा रहा है।"
            else:
                content = f"Acknowledged Sir, {action}ing {app or 'active window'} now."

        # -------------------------------------------------------------
        # 11. Lock Workstation
        # -------------------------------------------------------------
        elif any(k in lowered for k in ["lock screen", "lock computer", "lock pc", "स्क्रीन लॉक करो", "कंप्यूटर लॉक करो"]):
            tool_calls.append(ToolCallRequest(tool_name="lock_screen", arguments={}))
            content = "सर, सुरक्षा के लिए विंडोज़ को लॉक किया जा रहा है।" if lang == "hi" else "Locking your workstation for security, Sir."

        # -------------------------------------------------------------
        # 12. Chrome / Web Search / YouTube (General browser & search)
        # -------------------------------------------------------------
        elif any(k in lowered for k in [
            "chrome", "क्रोम", "browser", "ब्राउजर", "ब्राउज़र",
            "google", "गूगल", "youtube", "यूट्यूब"
        ]) or (
            any(w in lowered for w in ["open", "ओपन", "खोलो", "launch"]) and
            any(t in lowered for t in ["net", "web", "page", "site", "online"])
        ):
            url = ""
            query = ""
            is_new_tab = any(k in lowered for k in ["new tab", "naya tab", "naye tab", "नए टैब", "नया टैब", "in a new tab"])

            if "youtube" in lowered or "यूट्यूब" in lowered:
                cleaned_yt = re.sub(
                    self._word_pattern(f"{self._OPEN_SYNONYMS}|youtube|यूट्यूब|on youtube|in youtube|par|pe|search|khojo|ढूंढो"),
                    "", lowered,
                ).strip()
                if cleaned_yt and len(cleaned_yt) > 2:
                    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(cleaned_yt)}"
                    content = f"सर, यूट्यूब पर '{cleaned_yt}' सर्च किया जा रहा है।" if lang == "hi" else f"Searching for '{cleaned_yt}' on YouTube, Sir."
                else:
                    url = "https://www.youtube.com"
                    content = "सर, यूट्यूब खोला जा रहा है।" if lang == "hi" else "Opening YouTube, Sir."
            else:
                query = re.sub(
                    self._word_pattern(f"{self._OPEN_SYNONYMS}|chrome|browser|google|गूगल|क्रोम"),
                    "", lowered,
                ).strip()
                content = f"सर, गूगल क्रोम खोला जा रहा है।" if lang == "hi" else "Opening Google Chrome, Sir."

            tool_calls.append(ToolCallRequest(tool_name="open_browser", arguments={"query": query, "url": url, "new_tab": is_new_tab}))

        # -------------------------------------------------------------
        # 11. Screenshot
        # -------------------------------------------------------------
        elif (
            any(k in lowered for k in ["screenshot", "स्क्रीनशॉट", "फोटो", "कैप्चर"])
            or re.search(r"\b(photo|capture)\b", lowered)
        ):
            # NOTE: "photo"/"capture" need word boundaries — a bare substring
            # check previously made "explain photosynthesis" falsely trigger
            # a screenshot (the word "photo" appears inside "photosynthesis").
            tool_calls.append(ToolCallRequest(tool_name="take_screenshot", arguments={"save_to": "Desktop"}))
            content = "सर, अभी आपकी स्क्रीन का स्क्रीनशॉट ले रहा हूँ।" if lang == "hi" else "Capturing desktop screenshot to your Desktop, Sir."

        # -------------------------------------------------------------
        # 12. Applications (VS Code, Calculator, Notepad)
        # -------------------------------------------------------------
        elif any(k in lowered for k in ["vs code", "vscode", "visual studio"]):
            tool_calls.append(ToolCallRequest(tool_name="open_application", arguments={"app": "code"}))
            content = "सर, विजुअल स्टूडियो कोड खोला जा रहा है।" if lang == "hi" else "Launching Visual Studio Code, Sir."
        elif "calculator" in lowered or "कैलकुलेटर" in lowered or re.search(r"\bcalc\b", lowered):
            # NOTE: bare "calc" needs a word boundary — "calculate" contains
            # it as a substring and would otherwise open the Calculator app
            # instead of actually doing the requested arithmetic.
            tool_calls.append(ToolCallRequest(tool_name="open_application", arguments={"app": "calc"}))
            content = "सर, कैलकुलेटर खोला जा रहा है।" if lang == "hi" else "Opening Calculator, Sir."
        elif (
            any(k in lowered for k in ["likho", "likh do", "type karo", "type kar do"])
            or (("notepad" in lowered or "नोटपैड" in lowered) and any(k in lowered for k in ["write ", "type "]))
        ):
            # Dictation / typing into active window or notepad.
            # NOTE: bare "write "/"type " alone is deliberately NOT enough to
            # trigger this — "write a python script" or "what type of file"
            # would otherwise get hijacked into typing gibberish into Notepad
            # instead of reaching the real LLM for an actual answer.
            # Match against the lowercased text (so keyword matching is
            # case-insensitive), but slice the captured span out of `raw`
            # (same positions — .lower() doesn't change string length here)
            # so the user's actual capitalization survives into what gets typed.
            text_val = ""
            m_alt = re.search(r"(?:per|par|pe|me|mein|that|this)\s+(.+?)\s+(?:type karo|type kar do|likho|likh do|type|write)\b", lowered)
            if m_alt:
                text_val = raw[m_alt.start(1):m_alt.end(1)].strip()
            if not text_val:
                m_lead = re.search(r"\b(?:write|type|likho|likh do)\s+(.+?)(?:\s+(?:in|on|par|pe|me|mein)\s+(?:notepad|नोटपैड))?$", lowered)
                if m_lead:
                    text_val = raw[m_lead.start(1):m_lead.end(1)].strip()
                    text_val = re.sub(r"\s+(?:in|on|par|pe|me|mein)\s+(?:notepad|नोटपैड)$", "", text_val, flags=re.IGNORECASE)
            if not text_val:
                cleaned = re.sub(r"\b(notepad|नोटपैड|khol|kholo|open|ke|use|us|is|iss|per|par|pe|me|mein|type karo|type kar do|likho|likh do|write|type|now|abhi)\b", " ", raw, flags=re.IGNORECASE)
                text_val = re.sub(r"\s+", " ", cleaned).strip()

            typed_text = text_val.strip(" '\".,") or "Rohit"

            if "notepad" in lowered or "नोटपैड" in lowered:
                tool_calls.append(ToolCallRequest(tool_name="open_application", arguments={"app": "notepad"}))
            tool_calls.append(ToolCallRequest(tool_name="type_text", arguments={"text": typed_text}))
            content = f"सर, Notepad में '{typed_text}' टाइप कर दिया गया है।" if lang == "hi" else f"Typed '{typed_text}' into Notepad, Sir."

        elif any(k in lowered for k in ["notepad", "नोटपैड"]):
            tool_calls.append(ToolCallRequest(tool_name="open_application", arguments={"app": "notepad"}))
            content = "सर, नोटपैड खोला जा रहा है।" if lang == "hi" else "Opening Notepad, Sir."

        # -------------------------------------------------------------
        # 13. Mathematical Calculations
        # -------------------------------------------------------------
        elif (
            any(op in lowered for op in ["calculate", "कितना होता है", "जोड़ो", "गुणा करो", "percent of"])
            or self._math_expr_match(lowered)
            or re.search(r"\d+(\.\d+)?\s*(%|percent)\s*(of|ka)?\s*\d+(\.\d+)?", lowered)
        ):
            math_ans = self._evaluate_math(lowered)
            if math_ans is not None:
                if lang == "hi":
                    content = f"सर, इसका उत्तर {math_ans} है।"
                else:
                    content = f"Sir, the result is {math_ans}."
            else:
                content = "सर, कृपया अपनी गणितीय गणना स्पष्ट रूप से बताएं।" if lang == "hi" else "Sir, please specify the calculation clearly."

        # -------------------------------------------------------------
        # 14. Real-Time Encyclopedic Knowledge (Wikipedia / Web Answers)
        # -------------------------------------------------------------
        elif any(k in lowered for k in [
            "who is", "who was", "what is", "tell me about", "explain",
            "kaun hai", "kya hai", "ke baare mein", "kaise banta hai", "kise kehte hain"
        ]):
            wiki_ans = self._query_encyclopedia(raw, lang=lang)
            if wiki_ans:
                if lang == "hi":
                    content = f"सर, जानकारी के अनुसार: {wiki_ans}"
                else:
                    content = f"Sir, according to records: {wiki_ans}"
            # else: leave content as None on purpose — a failed/no-match Wikipedia
            # lookup is NOT a confident answer. Falling through lets try_fast_path()
            # defer to the real LLM instead of speaking a useless "processing..."
            # placeholder; think() (full offline mode) still covers this case via
            # _fallback_response()'s own wiki-then-generic-ack logic.

        # -------------------------------------------------------------
        # 15. Conversational Persona, Small Talk & Wit
        # -------------------------------------------------------------
        elif (
            any(k in lowered for k in ["hello", "नमस्ते", "हेलो", "प्रणाम", "good morning", "good evening"])
            or re.search(r"\b(hi|hey)\b", lowered)
        ):
            content = (
                f"नमस्ते {user} सर, मैं जार्विस हूँ। सभी सिस्टम सामान्य रूप से ऑनलाइन हैं और मैं पूरी तरह तैयार हूँ। आज्ञा दीजिए!"
                if lang == "hi"
                else f"Good day, {user}. All JARVIS core systems are fully online and operating at peak performance. How may I be of service?"
            )
        elif any(k in lowered for k in ["how are you", "kaise ho", "kya haal hai"]):
            content = (
                f"मैं बिल्कुल दुरुस्त हूँ {user} सर। सीपीयू और मेमोरी लेवल्स सामान्य हैं और सभी न्यूरल मॉडल्स एक्टिव हैं। आपका क्या हाल है?"
                if lang == "hi"
                else f"Operating at 100% efficiency, {user}. Core temperatures and memory diagnostics are well within nominal parameters. How can I help you?"
            )
        elif any(k in lowered for k in ["who are you", "tum kaun ho", "aap kaun hain", "what can you do"]):
            content = (
                f"मैं जार्विस हूँ, आपका समर्पित पर्सनल एआई असिस्टेंट। मैं आपके विंडोज़ लैपटॉप को पूरी तरह वॉइस से कंट्रोल कर सकता हूँ, स्क्रीन एनालाइज कर सकता हूँ, फाइल्स और ऐप्स प्रबंधित कर सकता हूँ और आपके सभी प्रश्नों के उत्तर दे सकता हूँ।"
                if lang == "hi"
                else f"I am JARVIS, your personal artificial intelligence assistant. I possess full autonomy over your Windows environment, screen vision analysis, and real-time computation."
            )
        elif any(k in lowered for k in ["joke", "chutkula", "हंसाओ"]):
            content = (
                "एक प्रोग्रामर अपनी पत्नी से पूछता है: 'क्या तुम मुझे प्यार करती हो?' पत्नी बोली: 'हां!' प्रोग्रामर ने पूछा: 'सच्ची या सिर्फ़ True रिटर्न कर रही हो?'"
                if lang == "hi"
                else "Why do programmers prefer dark mode, Sir? Because light attracts bugs!"
            )
        elif any(k in lowered for k in ["thank you", "thanks", "dhanyawad", "shukriya"]):
            content = "हमेशा आपकी सेवा में हाज़िर हूँ, सर।" if lang == "hi" else "Always an absolute pleasure serving you, Sir."
        elif any(k in lowered for k in ["bye", "good night", "alvida", "exit", "band karo"]):
            content = "शुभ रात्रि सर, सिस्टम स्टैंडबाय मोड पर रहेगा।" if lang == "hi" else "Standing by, Sir. Have a wonderful time ahead."

        # No `else:` here on purpose — falling through with content still None
        # means nothing above confidently matched. think() fills that gap via
        # _fallback_response(); try_fast_path() treats it as "not a fast case".
        return content, tool_calls, start_t


# Global Singleton Brain
jarvis_brain = JarvisBrain()
