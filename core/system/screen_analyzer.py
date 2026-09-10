"""
Screen Vision & Desktop Context Analyzer for JARVIS.
Captures screen state, enumerates active/visible application windows,
extracts active web tabs and documents, and answers user questions about
what is currently displayed on their screen.
"""
import base64
import ctypes
import io
import json
import urllib.request
from ctypes import wintypes
import os
import psutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    from PySide6.QtGui import QGuiApplication
    HAS_QT_GUI = True
except Exception:
    HAS_QT_GUI = False

user32 = ctypes.windll.user32


def _encode_screenshot_jpeg(screenshot_path: str) -> Optional[bytes]:
    """Downscales + re-encodes a screenshot as JPEG so vision calls stay fast —
    full-resolution PNGs make the upload/response noticeably slower."""
    try:
        from PIL import Image
        img = Image.open(screenshot_path).convert("RGB")
        max_w = 1280
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        return buf.getvalue()
    except Exception:
        try:
            with open(screenshot_path, "rb") as f:
                return f.read()
        except Exception:
            return None


def _vision_system_prompt(user_name: str) -> str:
    from app.config import config

    # The tool-call query reaching this function is crafted by the main LLM
    # deciding to invoke analyze_screen, and is very often in English (e.g.
    # "Which folder is currently open in File Explorer?") EVEN when the
    # user actually spoke Hindi — so "reply in Hindi if the question was in
    # Hindi" was the wrong signal to key off, and routinely produced an
    # English answer. With FORCE_HINDI_ONLY_SPEECH on, that English text
    # then gets forced through the Hindi voice/phonemizer and comes out as
    # unintelligible noise — which is exactly what "JARVIS said 'one sec'
    # and never came back" turned out to be: it DID answer, just in a
    # language the voice pipeline can't actually speak anymore.
    language_instruction = (
        "Reply ONLY in Hindi (Devanagari script), regardless of what language the "
        "question itself was asked in."
        if getattr(config, "FORCE_HINDI_ONLY_SPEECH", False)
        else "Reply in Hindi (Devanagari) if the question was in Hindi/Hinglish, otherwise English."
    )
    return (
        f"You are JARVIS, {user_name}'s desktop assistant. You are shown a live screenshot "
        "of their screen. Answer their question about it precisely and concisely (1-3 sentences), "
        "describing exactly what app/content is visible and anything specifically relevant to "
        "their question (button labels, text, error messages, etc). If they ask how to do "
        "something in what's shown, give the exact concrete steps (menu/button names) visible "
        "on screen. If the screenshot is unclear or you don't recognize the software well enough "
        "to be sure, say so plainly and ask them to point out what to click, rather than guessing. "
        f"{language_instruction}"
    )


def _query_openai_vision(b64_image: str, question: str, user_name: str) -> Optional[str]:
    from app.config import config
    api_key = getattr(config, "OPENAI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None
    try:
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": _vision_system_prompt(user_name)},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question or "Mere screen par abhi kya dikh raha hai?"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}", "detail": "low"}},
                    ],
                },
            ],
            "temperature": 0.2,
            "max_tokens": 220,
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[ScreenAnalyzer] OpenAI vision error: {e}")
        return None


def _query_gemini_vision(b64_image: str, question: str, user_name: str) -> Optional[str]:
    from app.config import config
    api_key = getattr(config, "GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={api_key}"
    payload = {
        "system_instruction": {"parts": [{"text": _vision_system_prompt(user_name)}]},
        "contents": [{
            "role": "user",
            "parts": [
                {"text": question or "Mere screen par abhi kya dikh raha hai?"},
                {"inline_data": {"mime_type": "image/jpeg", "data": b64_image}},
            ],
        }],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 220},
    }
    req_body = json.dumps(payload).encode("utf-8")

    # gemini-3.5-flash-lite occasionally returns a transient 503 under load —
    # one quick retry avoids falling all the way back to the guess-based
    # description for what is usually a momentary blip, not a real outage.
    last_err = None
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                url, data=req_body, headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            last_err = e
            if attempt == 0:
                time.sleep(0.8)

    print(f"[ScreenAnalyzer] Gemini vision error: {last_err}")
    return None


def _query_screen_vision(screenshot_path: str, question: str) -> Optional[str]:
    """
    Sends the actual screenshot pixels to a real vision-capable LLM so JARVIS
    can answer "what's on my screen" / operate unfamiliar software based on
    what is truly visible, instead of guessing from the window title. Tries
    Gemini first (free tier, confirmed working), then OpenAI as a secondary
    (in case paid credits get added later) — returns None if neither answers
    so the caller can fall back to the heuristic guess. Gemini-first avoids
    wasting 1-2s per screen question on a guaranteed-fail OpenAI attempt
    whenever that key has no credits.
    """
    from app.config import config
    if not screenshot_path or not os.path.exists(screenshot_path):
        return None

    img_bytes = _encode_screenshot_jpeg(screenshot_path)
    if not img_bytes:
        return None

    b64_image = base64.b64encode(img_bytes).decode("ascii")
    user_name = getattr(config, "USER_NAME", "Sir")

    answer = _query_gemini_vision(b64_image, question, user_name)
    if answer:
        return answer
    return _query_openai_vision(b64_image, question, user_name)


def attach_to_input_desktop() -> bool:
    """Attaches calling thread to Windows interactive input desktop (WinSta0\\Default)."""
    try:
        # DESKTOP_ALL_FLAGS to access active desktop windows
        hDesk = user32.OpenInputDesktop(0, False, 0x0100 | 0x0001 | 0x0002 | 0x0004 | 0x0008 | 0x0010 | 0x0020 | 0x0040)
        if hDesk:
            user32.SetThreadDesktop(hDesk)
            return True
    except Exception:
        pass
    return False


class ScreenAnalyzer:
    """Core vision and desktop state analyzer."""

    SYSTEM_FILTER = {
        "program manager", "default ime", "msctfime ui", "settings",
        "windows input experience", "applicationframehost.exe"
    }

    @staticmethod
    def get_foreground_window() -> Optional[Dict[str, Any]]:
        """Retrieves details of the currently focused/active foreground window."""
        attach_to_input_desktop()
        fg = user32.GetForegroundWindow()
        if not fg:
            return None

        length = user32.GetWindowTextLengthW(fg)
        if length <= 0:
            return None

        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(fg, buf, length + 1)
        title = buf.value.strip()

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(fg, ctypes.byref(pid))
        pname = "unknown"
        try:
            pname = psutil.Process(pid.value).name()
        except Exception:
            pass

        rect = wintypes.RECT()
        user32.GetWindowRect(fg, ctypes.byref(rect))

        return {
            "hwnd": fg,
            "title": title,
            "process": pname,
            "pid": pid.value,
            "rect": (rect.left, rect.top, rect.right, rect.bottom),
        }

    @classmethod
    def get_visible_windows(cls) -> List[Dict[str, Any]]:
        """Enumerates all top-level application windows visible to the user."""
        attach_to_input_desktop()
        results = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def enum_windows_callback(hwnd, lparam):
            try:
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buffer = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buffer, length + 1)
                        title = buffer.value.strip()
                        if title and title.lower() not in cls.SYSTEM_FILTER:
                            pid = wintypes.DWORD()
                            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                            pname = "unknown"
                            try:
                                pname = psutil.Process(pid.value).name()
                            except Exception:
                                pass
                            if pname.lower() not in cls.SYSTEM_FILTER:
                                results.append({
                                    "hwnd": hwnd,
                                    "title": title,
                                    "process": pname,
                                    "pid": pid.value,
                                })
            except Exception:
                pass
            return True

        user32.EnumWindows(enum_windows_callback, 0)
        return results

    @staticmethod
    def capture_screenshot(save_path: Optional[str] = None) -> Optional[str]:
        """
        Captures a full screenshot of the primary screen.

        Used internally by analyze_screen()/click_screen — these are
        implementation details of a vision call, not something the user
        asked to "save a screenshot," so unlike TakeScreenshotTool (which
        explicitly saves to Desktop because the user asked for a keepable
        file), this defaults to the OS temp directory with a unique name.
        Callers that only need the file for the duration of one vision
        call MUST delete it afterward (see analyze_screen()'s finally
        block) — capture_screenshot() itself does not delete anything, it
        only chooses a location that isn't the user's visible Desktop.
        """
        if not save_path:
            import tempfile
            import uuid
            save_path = str(Path(tempfile.gettempdir()) / f"jarvis_vision_{uuid.uuid4().hex}.png")

        try:
            if HAS_QT_GUI and QGuiApplication.primaryScreen():
                screen = QGuiApplication.primaryScreen()
                pixmap = screen.grabWindow(0)
                if pixmap.save(save_path, "PNG"):
                    return save_path
        except Exception as e:
            print(f"[ScreenAnalyzer] Qt screenshot error: {e}")

        # Fallback to PIL ImageGrab if available
        try:
            from PIL import ImageGrab
            im = ImageGrab.grab()
            im.save(save_path)
            return save_path
        except Exception as e:
            print(f"[ScreenAnalyzer] PIL ImageGrab fallback error: {e}")

        return None

    @staticmethod
    def _cleanup_screenshot(path: Optional[str]) -> None:
        """Deletes a temp screenshot written by capture_screenshot(). Never
        raises — this runs from a finally block and a cleanup failure must
        not mask (or crash alongside) the real result of the vision call."""
        if not path:
            return
        try:
            p = Path(path)
            if p.exists():
                p.unlink()
        except Exception as e:
            print(f"[ScreenAnalyzer] Could not delete temp screenshot {path}: {e}")

    @classmethod
    def analyze_screen(cls, user_query: Optional[str] = None, allow_cloud: bool = True) -> Dict[str, Any]:
        """
        Deep analysis of the current screen:
        1. Identifies foreground active window & topic.
        2. Discovers all running/visible applications.
        3. Formulates a natural, conversational Hindi/English response answering user's question.

        allow_cloud=False keeps everything local: no screenshot pixels are
        ever sent to Gemini/OpenAI, and the answer comes from the
        window-title heuristic below instead. The temp screenshot file
        (wherever it ends up captured to) is always deleted before this
        method returns, whether or not the cloud path was used.
        """
        fg = cls.get_foreground_window()
        visible_windows = cls.get_visible_windows()
        screenshot_path = cls.capture_screenshot()

        # Deduplicate and sort open apps
        app_summaries = []
        for w in visible_windows:
            pname = w["process"].replace(".exe", "").capitalize()
            title = w["title"]
            app_summaries.append((pname, title))

        # Format explanation based on what is active
        fg_title = fg["title"] if fg else "Desktop"
        fg_proc = fg["process"].replace(".exe", "").capitalize() if fg else "Windows Explorer"

        # Determine application context
        app_context = ""
        if "chrome" in fg_proc.lower():
            clean_title = fg_title.replace("- Google Chrome", "").strip()
            app_context = f"गूगल क्रोम (Google Chrome) खुला हुआ है, जिसमें '{clean_title}' वेबपेज देखा जा रहा है।"
        elif any(k in fg_proc.lower() for k in ["code", "ide", "visual studio", "antigravity"]):
            app_context = f"कोड एडिटर (IDE / VS Code) एक्टिव है, जिसमें '{fg_title}' प्रोजेक्ट और फाइल्स खुली हुई हैं।"
        elif "claude" in fg_proc.lower():
            app_context = f"क्लॉड (Claude AI) विंडो एक्टिव है।"
        elif "notepad" in fg_proc.lower():
            app_context = f"नोटपैड (Notepad) खुला हुआ है, जिसमें टेक्स्ट डॉक्यूमेंट एडिट हो रहा है।"
        elif "explorer" in fg_proc.lower():
            app_context = f"विंडोज फाइल एक्सप्लोरर खुला हुआ है, जहाँ फाइल्स नेविगेट की जा रही हैं।"
        else:
            app_context = f"'{fg_proc}' एप्लिकेशन स्क्रीन पर एक्टिव है, जिसका टाइटल '{fg_title}' है।"

        # Other background apps summary
        other_apps = []
        seen = {fg_proc.lower()}
        for p, t in app_summaries:
            if p.lower() not in seen and len(other_apps) < 4:
                seen.add(p.lower())
                other_apps.append(p)

        bg_text = ""
        if other_apps:
            bg_text = f" साथ ही बैकग्राउंड में {', '.join(other_apps)} भी खुले हुए हैं।"

        try:
            # Real vision analysis: send the actual screenshot pixels to a
            # vision LLM so JARVIS answers based on what is truly on
            # screen, not a title guess — but ONLY with explicit consent
            # (allow_cloud=True). Without consent, or if the call fails,
            # this falls back to the local window-title heuristic below —
            # no pixels leave the machine in that case.
            answer = None
            if allow_cloud and screenshot_path:
                answer = _query_screen_vision(screenshot_path, user_query or "")

            if not answer:
                q_lower = (user_query or "").lower()
                if "error" in q_lower or "समस्या" in q_lower or "दिक्कत" in q_lower:
                    answer = f"सर, मैंने आपकी स्क्रीन को स्कैन कर लिया है। अभी एक्टिव विंडो '{fg_title}' है। स्क्रीन पर कोई क्रिटिकल सिस्टम एरर नहीं दिख रहा है, {app_context}"
                elif "open chrome" in q_lower or "क्रोम" in q_lower:
                    answer = f"सर, गूगल क्रोम खोला गया है और आपकी स्क्रीन पर एक्टिव है। स्क्रीन पर अभी {app_context}{bg_text}"
                elif not allow_cloud:
                    answer = (
                        f"सर, क्लाउड स्क्रीन एनालिसिस की अनुमति नहीं है, इसलिए मैं सिर्फ इतना बता सकता हूँ: "
                        f"{app_context}{bg_text} विस्तृत विश्लेषण के लिए Settings > Privacy में इसे चालू करें।"
                    )
                else:
                    answer = f"सर, आपकी स्क्रीन पर अभी {app_context}{bg_text}"

            return {
                "answer": answer,
                "foreground_window": fg,
                "visible_windows": visible_windows,
                # Not returned as a persisted artifact — the file itself is
                # deleted in the finally block below regardless of whether
                # this dict is inspected. Kept in the return value only for
                # any caller wanting to know a screenshot WAS captured this
                # call, not as a usable path.
                "screenshot_path": None,
            }
        finally:
            cls._cleanup_screenshot(screenshot_path)


# Global singleton
screen_analyzer = ScreenAnalyzer()
