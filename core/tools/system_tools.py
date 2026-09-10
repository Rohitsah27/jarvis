"""
Built-in safe system tools for Windows desktop automation.
"""
import logging
import os
import re
import shutil
import subprocess
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from PySide6.QtGui import QGuiApplication
import psutil

from core.tools.base import BaseTool, PermissionLevel, ToolResult
from core.tools.confirmation import confirmation_service

logger = logging.getLogger("jarvis.tools")


class TakeScreenshotTool(BaseTool):
    """Captures the primary monitor and saves to Desktop."""

    @property
    def name(self) -> str:
        return "take_screenshot"

    @property
    def description(self) -> str:
        return "Captures a screenshot of the Windows desktop and saves it."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.LOW_RISK

    def execute(self, **kwargs) -> ToolResult:
        try:
            screen = QGuiApplication.primaryScreen()
            if not screen:
                return ToolResult(False, "No primary screen detected", self.name)

            desktop_path = Path(os.path.expanduser("~")) / "Desktop"
            if not desktop_path.exists():
                desktop_path = Path(os.path.expanduser("~"))

            filename = f"JARVIS_Capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            target = desktop_path / filename

            pixmap = screen.grabWindow(0)
            success = pixmap.save(str(target), "PNG")

            if success:
                return ToolResult(
                    True,
                    f"Screenshot saved successfully to: {target.name}",
                    self.name,
                    data={"filepath": str(target)},
                )
            else:
                return ToolResult(False, "Failed to save screenshot image buffer", self.name)
        except Exception as e:
            return ToolResult(False, f"Screenshot error: {str(e)}", self.name, error=str(e))


class OpenAppTool(BaseTool):
    """Launches any installed Windows application, best-effort resolving friendly names."""

    @property
    def name(self) -> str:
        return "open_application"

    @property
    def description(self) -> str:
        return "Launches any Windows desktop application by name (VS Code, Notepad, Calculator, Spotify, WhatsApp, Word, Excel, Settings, etc.)."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.CONFIRMATION_REQUIRED

    def confirmation_summary(self, args) -> str:
        return f"Launch application '{args.get('app', '')}'"

    def confirmation_target(self, args) -> str:
        return str(args.get("app", ""))

    # Friendly-name aliases for apps whose process/AppX name doesn't match what users say
    _ALIASES = {
        "notepad": "notepad.exe",
        "calc": "calc.exe",
        "calculator": "calc.exe",
        "code": "code",
        "vscode": "code",
        "vs code": "code",
        "visual studio code": "code",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "files": "explorer.exe",
        "cmd": "cmd.exe",
        "command prompt": "cmd.exe",
        "terminal": "wt.exe",
        "powershell": "powershell.exe",
        "chrome": "chrome",
        "google chrome": "chrome",
        "edge": "msedge",
        "microsoft edge": "msedge",
        "firefox": "firefox",
        "word": "winword",
        "microsoft word": "winword",
        "excel": "excel",
        "microsoft excel": "excel",
        "powerpoint": "powerpnt",
        "paint": "mspaint.exe",
        "settings": "ms-settings:",
        "windows settings": "ms-settings:",
        "task manager": "taskmgr.exe",
        "control panel": "control.exe",
        "spotify": "spotify:",
        "whatsapp": "whatsapp:",
        "camera": "microsoft.windows.camera:",
        "store": "ms-windows-store:",
        "mail": "outlookmail:",
        "outlook": "outlook",
    }

    # Expected process image name(s) to wait for once launched, so a chained
    # follow-up action (type_text, press_key) targets the right window instead
    # of racing the app's startup time. Left out for protocol/UWP launches
    # (ms-settings:, spotify:, etc.) whose real host process name is unpredictable.
    _EXPECTED_PROCESS = {
        "notepad": ["notepad.exe"],
        "calc": ["calc.exe", "calculatorapp.exe"],
        "calculator": ["calc.exe", "calculatorapp.exe"],
        "code": ["code.exe"],
        "vscode": ["code.exe"],
        "vs code": ["code.exe"],
        "visual studio code": ["code.exe"],
        "explorer": ["explorer.exe"],
        "file explorer": ["explorer.exe"],
        "files": ["explorer.exe"],
        "cmd": ["cmd.exe"],
        "command prompt": ["cmd.exe"],
        "terminal": ["windowsterminal.exe", "wt.exe"],
        "powershell": ["powershell.exe", "pwsh.exe"],
        "chrome": ["chrome.exe"],
        "google chrome": ["chrome.exe"],
        "edge": ["msedge.exe"],
        "microsoft edge": ["msedge.exe"],
        "firefox": ["firefox.exe"],
        "word": ["winword.exe"],
        "microsoft word": ["winword.exe"],
        "excel": ["excel.exe"],
        "microsoft excel": ["excel.exe"],
        "powerpoint": ["powerpnt.exe"],
        "paint": ["mspaint.exe"],
        "task manager": ["taskmgr.exe"],
        "control panel": ["control.exe"],
    }

    # Characters that carry special meaning to cmd.exe's own command-line
    # parser (&, |, <, >, ^ chain/redirect commands; % expands variables;
    # quotes/newlines can terminate or re-open tokens). `target` here can
    # originate directly from LLM tool-call output or a misheard voice
    # transcript — an unrecognized name skips the fixed `_ALIASES` map
    # entirely and reaches this string verbatim, so it must never be handed
    # to cmd.exe's `/c start` unsanitized (that's what made this a
    # command-injection surface: `cmd /c start "" "<target>"` still lets
    # cmd.exe split on `&`/`|` even though target is individually quoted by
    # list2cmdline, because cmd.exe re-tokenizes the *whole* line itself).
    _SHELL_METACHARACTERS = set("&|<>^%\n\r\"")

    def execute(self, **kwargs) -> ToolResult:
        raw_name = str(kwargs.get("app", "notepad")).strip()
        app_name = raw_name.lower().strip()
        target = self._ALIASES.get(app_name, raw_name)

        try:
            if target.endswith(":"):
                # UWP/protocol launch (ms-settings:, spotify:, whatsapp:, etc.)
                os.startfile(target)
                return ToolResult(True, f"Application '{raw_name}' launched successfully.", self.name)

            if any(ch in target for ch in self._SHELL_METACHARACTERS):
                return ToolResult(
                    False,
                    f"Rejected: application name contains unsafe characters: '{raw_name}'",
                    self.name,
                    error="unsafe_characters",
                )

            # os.startfile() calls ShellExecuteEx directly — it does NOT
            # invoke cmd.exe and does not re-parse the string for shell
            # metacharacters, unlike `cmd /c start`. It resolves bare
            # executable names via the same PATH/App-Paths-registry lookup
            # `start` would use, so this covers the overwhelming majority of
            # cases safely. `cmd /c start` is kept only as a fallback for the
            # rare bare command ShellExecute can't resolve on its own — and
            # by this point `target` has already passed the metacharacter
            # check above, so the fallback is safe too.
            try:
                os.startfile(target)
            except OSError:
                subprocess.Popen(["cmd", "/c", "start", "", target], shell=False)

            # Neither os.startfile() nor `cmd /c start` reliably raises for a
            # nonexistent app — launching "successfully" is not proof
            # anything actually opened. Found via testing: an app name with
            # no window ever appearing (`focused` stays False) was previously
            # still reported as a successful launch every time. For a KNOWN
            # app (in _EXPECTED_PROCESS) that's kept as a soft "may still be
            # loading" note, since a real app can just be slow to start — but
            # for a name we don't recognize at all, treat "no window ever
            # appeared" as the strong signal it actually is: the app probably
            # doesn't exist or is named differently.
            is_known_app = app_name in self._EXPECTED_PROCESS
            expected = self._EXPECTED_PROCESS.get(app_name, [f"{target}.exe" if not target.lower().endswith(".exe") else target])
            focused = _wait_for_window_and_focus(expected, timeout=6.0)

            if not focused and not is_known_app:
                return ToolResult(
                    False,
                    f"Could not confirm '{raw_name}' launched — it may not exist on this system or may be named differently.",
                    self.name,
                    error=f"No process matching {expected} appeared within the timeout.",
                )

            note = "" if focused else " (window may still be loading)"
            return ToolResult(True, f"Application '{raw_name}' launched successfully.{note}", self.name)
        except Exception as e:
            return ToolResult(False, f"Failed to launch application '{raw_name}': {str(e)}", self.name, error=str(e))


class CloseApplicationTool(BaseTool):
    """Terminates a running application by process name."""

    @property
    def name(self) -> str:
        return "close_application"

    @property
    def description(self) -> str:
        return "Terminates a running application/process by name (e.g. 'chrome', 'notepad', 'spotify')."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.CONFIRMATION_REQUIRED

    _PROCESS_ALIASES = {
        "chrome": "chrome.exe",
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "code": "Code.exe",
        "vscode": "Code.exe",
        "edge": "msedge.exe",
        "firefox": "firefox.exe",
        "word": "winword.exe",
        "excel": "excel.exe",
        "spotify": "Spotify.exe",
        "whatsapp": "WhatsApp.exe",
        "paint": "mspaint.exe",
        "explorer": "explorer.exe",
    }

    def execute(self, **kwargs) -> ToolResult:
        raw_name = str(kwargs.get("app", "")).strip()
        if not raw_name:
            return ToolResult(False, "No application name provided to close.", self.name)

        image_name = self._PROCESS_ALIASES.get(raw_name.lower(), raw_name)
        if not image_name.lower().endswith(".exe"):
            image_name += ".exe"

        try:
            killed = 0
            for proc in psutil.process_iter(["pid", "name"]):
                if (proc.info.get("name") or "").lower() == image_name.lower():
                    try:
                        proc.terminate()
                        killed += 1
                    except Exception:
                        pass
            if killed:
                return ToolResult(True, f"Closed {killed} running instance(s) of '{raw_name}'.", self.name)
            return ToolResult(False, f"No running process found matching '{raw_name}'.", self.name)
        except Exception as e:
            return ToolResult(False, f"Failed to close '{raw_name}': {str(e)}", self.name, error=str(e))


class OpenPathTool(BaseTool):
    """Opens an existing file or folder with its default Windows application."""

    @property
    def name(self) -> str:
        return "open_path"

    @property
    def description(self) -> str:
        return "Opens an existing file or folder on disk with its default application (e.g. Desktop, Downloads, a document)."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.CONFIRMATION_REQUIRED

    _SHORTCUTS = {
        "desktop": "Desktop",
        "documents": "Documents",
        "downloads": "Downloads",
        "pictures": "Pictures",
        "music": "Music",
        "videos": "Videos",
    }

    def execute(self, **kwargs) -> ToolResult:
        raw_path = str(kwargs.get("path", "")).strip()
        if not raw_path:
            return ToolResult(False, "No path provided to open.", self.name)

        home = Path(os.path.expanduser("~"))
        candidate = self._SHORTCUTS.get(raw_path.lower())
        target = (home / candidate) if candidate else Path(raw_path)

        if not target.exists():
            # Try resolving relative to common user folders
            for base in (home / "Desktop", home / "Documents", home / "Downloads", home):
                guess = base / raw_path
                if guess.exists():
                    target = guess
                    break

        if not target.exists():
            return ToolResult(False, f"Path not found: '{raw_path}'.", self.name)

        try:
            os.startfile(str(target))
            return ToolResult(True, f"Opened: {target}", self.name)
        except Exception as e:
            return ToolResult(False, f"Failed to open '{raw_path}': {str(e)}", self.name, error=str(e))


class TypeTextTool(BaseTool):
    """Types text at the current cursor position in the focused window/field."""

    @property
    def name(self) -> str:
        return "type_text"

    @property
    def description(self) -> str:
        return "Types the given text into whatever field/app currently has focus (dictation)."

    @property
    def permission_level(self) -> PermissionLevel:
        # Previously SAFE — combined with press_key (which can send Enter),
        # an unconfirmed type_text is a de facto keystroke-injection
        # primitive into whatever window currently has focus, including a
        # terminal, browser address bar, or password field. Every call now
        # requires explicit human approval, with the exact text and target
        # window shown in the confirmation dialog (see confirmation_summary
        # / confirmation_target below).
        return PermissionLevel.CONFIRMATION_REQUIRED

    @staticmethod
    def _focused_window_title() -> str:
        try:
            from core.system.screen_analyzer import screen_analyzer
            fg = screen_analyzer.get_foreground_window()
            if fg:
                proc = fg.get("process", "") or "unknown"
                title = fg.get("title", "") or ""
                return f"{proc} — {title}" if title else proc
        except Exception:
            pass
        return "the currently focused window"

    def confirmation_summary(self, args) -> str:
        text = str(args.get("text", ""))
        preview = text if len(text) <= 200 else text[:200] + "..."
        return f"Type this text:\n\n    {preview}"

    def confirmation_target(self, args) -> str:
        return self._focused_window_title()

    def execute(self, **kwargs) -> ToolResult:
        text = str(kwargs.get("text", ""))
        if not text:
            return ToolResult(False, "No text provided to type.", self.name)

        try:
            import ctypes
            user32 = ctypes.windll.user32

            # Correct 64-bit-safe INPUT layout: the real Win32 INPUT struct is a
            # DWORD type tag followed by a UNION of {MOUSEINPUT, KEYBDINPUT,
            # HARDWAREINPUT} — not a plain struct with manual padding. Getting
            # this wrong still "works" (SendInput doesn't error) but silently
            # corrupts/drops keystrokes at essentially random positions, because
            # cbSize no longer matches the real struct size the kernel expects.
            PUL = ctypes.POINTER(ctypes.c_ulong)

            class KEYBDINPUT(ctypes.Structure):
                _fields_ = [
                    ("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                    ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                    ("dwExtraInfo", PUL),
                ]

            class MOUSEINPUT(ctypes.Structure):
                _fields_ = [
                    ("dx", ctypes.c_long), ("dy", ctypes.c_long),
                    ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                    ("time", ctypes.c_ulong), ("dwExtraInfo", PUL),
                ]

            class HARDWAREINPUT(ctypes.Structure):
                _fields_ = [
                    ("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_short), ("wParamH", ctypes.c_ushort),
                ]

            class INPUT_UNION(ctypes.Union):
                _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]

            class INPUT(ctypes.Structure):
                _fields_ = [("type", ctypes.c_ulong), ("union", INPUT_UNION)]

            INPUT_KEYBOARD = 1
            KEYEVENTF_UNICODE = 0x0004
            KEYEVENTF_KEYUP = 0x0002

            # Small settle delay in case this runs right after a window switch/launch —
            # the very first keystrokes sent immediately after a focus change are
            # often dropped before the target window's input queue is ready.
            time.sleep(0.25)

            for ch in text:
                code = ord(ch)
                down = INPUT(type=INPUT_KEYBOARD, union=INPUT_UNION(ki=KEYBDINPUT(0, code, KEYEVENTF_UNICODE, 0, None)))
                up = INPUT(type=INPUT_KEYBOARD, union=INPUT_UNION(ki=KEYBDINPUT(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, None)))
                sent1 = user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT))
                sent2 = user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT))
                if sent1 == 0 or sent2 == 0:
                    print(f"[TypeTextTool] SendInput rejected a keystroke for '{ch}' (GetLastError={ctypes.get_last_error()})")
                time.sleep(0.012)

            return ToolResult(True, "Text typed successfully.", self.name)
        except Exception as e:
            return ToolResult(False, f"Failed to type text: {str(e)}", self.name, error=str(e))


class PressKeyTool(BaseTool):
    """Simulates a keyboard shortcut or single key press (e.g. 'ctrl+s', 'enter', 'alt+tab')."""

    @property
    def name(self) -> str:
        return "press_key"

    @property
    def description(self) -> str:
        return "Presses a key or key combination (e.g. 'ctrl+s', 'ctrl+c', 'ctrl+v', 'enter', 'esc', 'alt+tab')."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.CONFIRMATION_REQUIRED

    def confirmation_summary(self, args) -> str:
        return f"Press key combination: {args.get('keys', '')}"

    def confirmation_target(self, args) -> str:
        return TypeTextTool._focused_window_title()

    _VK_MAP = {
        "ctrl": 0x11, "control": 0x11, "shift": 0x10, "alt": 0x12, "win": 0x5B,
        "enter": 0x0D, "return": 0x0D, "esc": 0x1B, "escape": 0x1B, "tab": 0x09,
        "space": 0x20, "backspace": 0x08, "delete": 0x2E, "del": 0x2E,
        "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
        "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    }

    def _vk_for(self, key: str) -> Optional[int]:
        key = key.strip().lower()
        if key in self._VK_MAP:
            return self._VK_MAP[key]
        if len(key) == 1:
            return ord(key.upper())
        if key.startswith("f") and key[1:].isdigit():
            n = int(key[1:])
            if 1 <= n <= 24:
                return 0x70 + (n - 1)
        return None

    def execute(self, **kwargs) -> ToolResult:
        combo = str(kwargs.get("keys", "")).strip()
        if not combo:
            return ToolResult(False, "No key combination provided.", self.name)

        parts = [p for p in combo.replace(" ", "").split("+") if p]
        vks = [self._vk_for(p) for p in parts]
        if not vks or any(v is None for v in vks):
            return ToolResult(False, f"Unrecognized key combination: '{combo}'.", self.name)

        try:
            _send_shortcut(*vks)
            return ToolResult(True, f"Pressed '{combo}'.", self.name)
        except Exception as e:
            return ToolResult(False, f"Failed to press '{combo}': {str(e)}", self.name, error=str(e))


class ClickScreenTool(BaseTool):
    """Clicks at exact coordinates, or locates and clicks a described on-screen element via vision."""

    @property
    def name(self) -> str:
        return "click_screen"

    @property
    def description(self) -> str:
        return "Clicks at (x, y) screen coordinates, or finds and clicks a described UI element (e.g. 'the Save button', 'the search box') using screen vision when no coordinates are given."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.CONFIRMATION_REQUIRED

    def confirmation_summary(self, args) -> str:
        desc = args.get("description")
        if desc:
            return f"Click on: {desc}"
        return f"Click at screen coordinates ({args.get('x')}, {args.get('y')})"

    def _locate_element(self, description: str):
        """
        Asks the vision model for the approximate pixel location of a
        described element — this ALSO uploads a screenshot to a cloud
        vision API, same as analyze_screen, so it respects the same
        SCREEN_ANALYSIS_CLOUD_CONSENT gate (no separate prompt here: this
        tool call already showed its own CONFIRMATION_REQUIRED dialog for
        the click itself; without prior cloud consent it simply can't
        resolve a description to coordinates and returns None, which
        execute() already turns into a clear "couldn't find it" result).
        """
        from app.config import config
        if not getattr(config, "SCREEN_ANALYSIS_CLOUD_CONSENT", None):
            return None

        screenshot_path = None
        try:
            from core.system.screen_analyzer import screen_analyzer, _query_screen_vision
            screenshot_path = screen_analyzer.capture_screenshot()
            if not screenshot_path:
                return None
            question = (
                f'Find the exact pixel location of: "{description}". '
                "Reply with ONLY coordinates in this exact format: X,Y (e.g. 512,340). No other words."
            )
            raw = _query_screen_vision(screenshot_path, question)
            if not raw:
                return None
            m = re.search(r"(\d+)\s*,\s*(\d+)", raw)
            if not m:
                return None
            return int(m.group(1)), int(m.group(2))
        except Exception:
            return None
        finally:
            if screenshot_path:
                from core.system.screen_analyzer import screen_analyzer
                screen_analyzer._cleanup_screenshot(screenshot_path)

    def execute(self, **kwargs) -> ToolResult:
        x = kwargs.get("x")
        y = kwargs.get("y")
        description = str(kwargs.get("description", "")).strip()

        if (x is None or y is None) and description:
            located = self._locate_element(description)
            if not located:
                return ToolResult(
                    False,
                    f"Sir, mujhe screen par '{description}' nahi mil paaya — kripya bataiye ki kahan click karna hai.",
                    self.name,
                )
            x, y = located

        if x is None or y is None:
            return ToolResult(False, "No coordinates or element description provided to click.", self.name)

        try:
            x, y = int(x), int(y)
            _user32.SetCursorPos(x, y)
            time.sleep(0.05)
            MOUSEEVENTF_LEFTDOWN = 0x0002
            MOUSEEVENTF_LEFTUP = 0x0004
            _user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            _user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            return ToolResult(True, f"Clicked at ({x}, {y}).", self.name)
        except Exception as e:
            return ToolResult(False, f"Click failed: {str(e)}", self.name, error=str(e))


class ScrollScreenTool(BaseTool):
    """Scrolls the mouse wheel up or down."""

    @property
    def name(self) -> str:
        return "scroll_screen"

    @property
    def description(self) -> str:
        return "Scrolls up or down on whatever window currently has focus."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.LOW_RISK

    def execute(self, **kwargs) -> ToolResult:
        direction = str(kwargs.get("direction", "down")).lower().strip()
        amount = int(kwargs.get("amount", 3))
        MOUSEEVENTF_WHEEL = 0x0800
        WHEEL_DELTA = 120
        delta = WHEEL_DELTA * amount * (1 if direction in ("up", "उप") else -1)

        try:
            _user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
            return ToolResult(True, f"Scrolled {direction}.", self.name)
        except Exception as e:
            return ToolResult(False, f"Scroll failed: {str(e)}", self.name, error=str(e))


class RunClaudeCLITool(BaseTool):
    """
    Delegates an actual coding/development task on the JARVIS project to the
    Claude Code CLI — e.g. "ask Claude to fix the volume bug", "get Claude to
    add a dark mode toggle". This can genuinely change files in the project.

    Safety design (deliberately NOT --dangerously-skip-permissions):
    - --permission-mode acceptEdits: file edits are auto-approved (the
      whole point — there's no human present to click "yes" when this fires
      from a voice command), but this does NOT bypass permissions in general.
    - --permission-prompts none: anything that WOULD still need a human's
      explicit approval (running shell commands, git push, installs, etc.)
      is auto-DENIED rather than silently allowed or left hanging forever.
      Net effect: Claude can read/write files in the project, but can't run
      arbitrary commands unsupervised.
    - --add-dir scopes file access to the JARVIS project folder specifically.
    - --max-budget-usd caps runaway spend from one voice-triggered call.
    """

    PROJECT_DIR = str(Path(__file__).resolve().parent.parent.parent)

    # Only one Claude CLI modification job may run at a time, no matter
    # which caller triggers it (the normal LLM tool-calling loop, or
    # core/observability/auto_fix.py's AutoFixWorker) — a second concurrent
    # attempt is rejected outright rather than silently queued, so the
    # caller gets an immediate, honest answer instead of racing file edits
    # against an in-flight run. Class-level so it's shared across every
    # instance regardless of who constructs one.
    _run_lock = threading.Lock()

    @property
    def name(self) -> str:
        return "run_claude_cli"

    @property
    def description(self) -> str:
        return (
            "Delegates a coding/development task on the JARVIS project itself to the Claude Code CLI "
            "(e.g. 'fix the volume bug', 'add a settings toggle for X'). File edits are auto-approved; "
            "shell/command execution is not, for safety. Takes a few seconds to a few minutes. ALWAYS "
            "requires an explicit human confirmation shown right before it runs — this cannot be skipped."
        )

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.HIGH_RISK

    @property
    def self_confirms(self) -> bool:
        return True

    @property
    def default_timeout_seconds(self) -> float:
        # Must cover the confirmation wait (up to confirmation_service's
        # timeout, 30s) PLUS the actual subprocess run (up to 180s) with
        # margin for process startup/teardown.
        return 240.0

    def confirmation_summary(self, args) -> str:
        task = str(args.get("task", ""))
        preview = task if len(task) <= 300 else task[:300] + "..."
        return (
            "JARVIS wants to delegate a CODE-MODIFYING task to the Claude Code CLI. "
            "File edits inside the JARVIS project folder will be auto-approved without "
            "further prompts.\n\nTask:\n    " + preview
        )

    def confirmation_target(self, args) -> str:
        return self.PROJECT_DIR

    def execute(self, **kwargs) -> ToolResult:
        task = str(kwargs.get("task", "")).strip()
        if not task:
            return ToolResult(False, "No task description provided for Claude CLI.", self.name)

        # HARD WALL — deliberately independent of PermissionManager and of
        # whoever called execute(). This is the single most sensitive tool
        # in JARVIS (it can modify JARVIS's own source code), so it must
        # never run without an explicit human decision obtained RIGHT HERE,
        # regardless of call path: the normal LLM tool-calling loop, the
        # intent-router fast path (verified it cannot even name this tool),
        # a provider-level fallback, AutoFix's own separate voice-confirmed
        # flow, or any future caller. There is no flag, config value, or
        # prompt instruction anywhere that can skip this call.
        decision = confirmation_service.request(
            tool_name=self.name,
            action_description=self.confirmation_summary(kwargs),
            target=self.confirmation_target(kwargs),
            important_args=f"task={task!r}",
            risk_level="HIGH",
        )
        if not decision.approved:
            logger.info("run_claude_cli denied (%s): %s", decision.reason, task[:80])
            return ToolResult(
                False,
                f"Claude CLI task was not approved ({decision.reason}) — no changes were made.",
                self.name,
                error=f"confirmation_{decision.reason}",
            )

        if not self._run_lock.acquire(blocking=False):
            logger.warning("run_claude_cli rejected: another job already running")
            return ToolResult(
                False,
                "Another Claude CLI task is already running against this project. "
                "Please wait for it to finish before starting another.",
                self.name,
                error="already_running",
            )

        try:
            # `claude` is an npm-installed shim — on Windows that's a
            # claude.cmd BATCH FILE, not a native .exe, and CreateProcess
            # (what subprocess uses with shell=False) cannot launch a .cmd
            # directly; only cmd.exe can. The previous code used
            # shell=True, which works, but wraps the ENTIRE list2cmdline-
            # joined command line in one shared pair of quotes
            # (`cmd /c "claude -p "task" ..."`) — cmd.exe's special-cased
            # handling of that single-quoted-blob form re-scans the whole
            # thing for &, |, %VAR% etc. even across what were meant to be
            # separate, individually-quoted arguments, which is the actual
            # injection surface. Resolving the real .cmd path once via
            # shutil.which() and invoking it as `cmd /c <path> <args...>`
            # with shell=False keeps each argument as its own
            # list2cmdline-quoted token instead of one merged string,
            # which is meaningfully safer (cmd.exe does not treat &/| as
            # separators INSIDE an individually quoted token) — though `%`
            # variable expansion and `^` escaping inside a free-text task
            # string are still cmd.exe behaviors this doesn't fully
            # neutralize. The mandatory confirmation above, which shows the
            # literal task text to a human before this ever runs, is the
            # primary defense; this is defense-in-depth on top of it, not
            # a claim that shell metacharacters are impossible here.
            claude_path = shutil.which("claude")
            if claude_path and claude_path.lower().endswith((".cmd", ".bat")):
                cmd = [
                    "cmd", "/c", claude_path, "-p", task,
                    "--add-dir", self.PROJECT_DIR,
                    "--permission-mode", "acceptEdits",
                    "--permission-prompts", "none",
                    "--max-budget-usd", "1.00",
                    "--output-format", "text",
                ]
            else:
                cmd = [
                    claude_path or "claude", "-p", task,
                    "--add-dir", self.PROJECT_DIR,
                    "--permission-mode", "acceptEdits",
                    "--permission-prompts", "none",
                    "--max-budget-usd", "1.00",
                    "--output-format", "text",
                ]
            try:
                result = subprocess.run(
                    cmd, cwd=self.PROJECT_DIR, capture_output=True, text=True,
                    timeout=180, encoding="utf-8", errors="replace", shell=False,
                )
                if result.returncode == 0:
                    output = (result.stdout or "").strip()
                    if not output:
                        output = "Claude CLI completed the task with no text output."
                    logger.info("run_claude_cli completed: %s", task[:80])
                    return ToolResult(True, output[:2000], self.name, data={"full_output": result.stdout})
                err = (result.stderr or result.stdout or "").strip()[:500]
                logger.error("run_claude_cli exited non-zero: %s", err[:200])
                return ToolResult(False, f"Claude CLI exited with an error: {err}", self.name, error=err)
            except subprocess.TimeoutExpired:
                logger.error("run_claude_cli timed out: %s", task[:80])
                return ToolResult(False, "Claude CLI task timed out after 3 minutes.", self.name, error="timeout")
            except FileNotFoundError:
                logger.error("run_claude_cli: claude executable not found")
                return ToolResult(False, "Claude CLI ('claude' command) was not found on this system.", self.name, error="not_found")
            except Exception as e:
                logger.exception("run_claude_cli unexpected error")
                return ToolResult(False, f"Claude CLI error: {str(e)}", self.name, error=str(e))
        finally:
            self._run_lock.release()


import ctypes
import urllib.parse
from ctypes import wintypes

_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32

_kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
_kernel32.GlobalAlloc.restype = ctypes.c_void_p
_kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
_kernel32.GlobalLock.restype = ctypes.c_void_p
_kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
_user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
_user32.SetClipboardData.restype = ctypes.c_void_p
_user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
_user32.AttachThreadInput.restype = wintypes.BOOL
_kernel32.GetCurrentThreadId.restype = wintypes.DWORD


def _set_clipboard(text: str) -> bool:
    """Sets system clipboard text via Qt clipboard or 64-bit safe Win32 API."""
    try:
        if QGuiApplication.instance():
            cb = QGuiApplication.clipboard()
            if cb:
                cb.setText(text)
                return True
    except Exception:
        pass

    try:
        GMEM_MOVEABLE = 0x0002
        CF_UNICODETEXT = 13
        if not _user32.OpenClipboard(0):
            return False
        try:
            _user32.EmptyClipboard()
            text_bytes = (text + "\0").encode("utf-16le")
            h_mem = _kernel32.GlobalAlloc(GMEM_MOVEABLE, len(text_bytes))
            ptr = _kernel32.GlobalLock(h_mem)
            ctypes.memmove(ptr, text_bytes, len(text_bytes))
            _kernel32.GlobalUnlock(h_mem)
            _user32.SetClipboardData(CF_UNICODETEXT, h_mem)
            return True
        finally:
            _user32.CloseClipboard()
    except Exception:
        return False


def _find_browser_window() -> Tuple[Optional[int], Optional[str]]:
    """Finds active Google Chrome, Edge, Brave, or Firefox window."""
    try:
        from core.system.screen_analyzer import screen_analyzer
        visible = screen_analyzer.get_visible_windows()
        # 1. Prefer Google Chrome
        for w in visible:
            proc = w.get("process", "").lower()
            if "chrome" in proc:
                return w["hwnd"], "chrome"
        # 2. Other Chromium / browser engines
        for w in visible:
            proc = w.get("process", "").lower()
            title = w.get("title", "").lower()
            if any(b in proc for b in ["msedge", "brave", "firefox", "opera"]):
                return w["hwnd"], proc
            if any(b in title for b in ["chrome", "edge", "brave", "firefox"]):
                return w["hwnd"], proc
    except Exception:
        pass
    return None, None


def _focus_browser_window(hwnd: int) -> bool:
    """
    Brings a window to the foreground reliably from a background/tool-invoked
    process. A plain SetForegroundWindow (even with the classic Alt-key trick)
    is frequently silently blocked by Windows' foreground-lock protection when
    the caller isn't the process that most recently received user input — which
    is exactly JARVIS's situation when executing a voice command. AttachThreadInput
    temporarily merges input state with the target window's thread, which is the
    standard reliable workaround.
    """
    if not hwnd or not _user32.IsWindow(hwnd):
        return False

    current_thread = _kernel32.GetCurrentThreadId()
    target_thread = _user32.GetWindowThreadProcessId(hwnd, None)
    fg_hwnd = _user32.GetForegroundWindow()
    fg_thread = _user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0

    attached_target = False
    attached_fg = False
    try:
        _user32.ShowWindow(hwnd, 9)  # SW_RESTORE

        if target_thread and target_thread != current_thread:
            attached_target = bool(_user32.AttachThreadInput(current_thread, target_thread, True))
        if fg_thread and fg_thread not in (current_thread, target_thread):
            attached_fg = bool(_user32.AttachThreadInput(current_thread, fg_thread, True))

        _user32.BringWindowToTop(hwnd)
        _user32.SetForegroundWindow(hwnd)
        _user32.SetActiveWindow(hwnd)
        _user32.SetFocus(hwnd)

        time.sleep(0.15)
        return _user32.GetForegroundWindow() == hwnd
    except Exception:
        return False
    finally:
        if attached_target:
            _user32.AttachThreadInput(current_thread, target_thread, False)
        if attached_fg:
            _user32.AttachThreadInput(current_thread, fg_thread, False)


def _wait_for_window_and_focus(candidate_process_names, timeout: float = 6.0, poll_interval: float = 0.25) -> bool:
    """
    Polls for a top-level window belonging to one of the candidate process names
    and brings it to the foreground once found. Used after launching an app so a
    chained follow-up action (type_text, press_key) targets the right window
    instead of racing the app's startup time.
    """
    from core.system.screen_analyzer import screen_analyzer
    normalized = {c.lower() for c in candidate_process_names if c}
    if not normalized:
        return False

    deadline = time.time() + timeout
    found_hwnd = None
    while time.time() < deadline:
        try:
            for w in screen_analyzer.get_visible_windows():
                if w.get("process", "").lower() in normalized:
                    found_hwnd = w["hwnd"]
                    if _focus_browser_window(found_hwnd):
                        # Freshly-launched windows need extra time to finish activating
                        # and accepting input, not just a focus-switch settle delay.
                        time.sleep(0.6)
                        return True
                    break  # retry focusing the same window on the next poll tick
        except Exception:
            pass
        time.sleep(poll_interval)

    # Last-ditch attempt even if we couldn't confirm focus succeeded — better
    # than silently giving up and letting the next action fire blind.
    if found_hwnd:
        _focus_browser_window(found_hwnd)
        time.sleep(0.4)
    return False


def _send_shortcut(*keys: int) -> None:
    """Sends key combination down in forward order, and up in reverse order."""
    for k in keys:
        _user32.keybd_event(k, 0, 0, 0)
        time.sleep(0.015)
    time.sleep(0.02)
    for k in reversed(keys):
        _user32.keybd_event(k, 0, 2, 0)
        time.sleep(0.015)


def _send_key(vk: int) -> None:
    """Taps a single virtual key."""
    _user32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.015)
    _user32.keybd_event(vk, 0, 2, 0)


# Exact hostnames this app will ever fetch on the user's behalf without
# explicit confirmation. A substring check like `"youtube.com..." in url`
# (the previous implementation) matches lookalikes such as
# "youtube.com.attacker.com" or "attacker.com/?x=youtube.com/results?..." —
# parsing the URL and comparing the actual hostname closes that.
_YOUTUBE_ALLOWED_HOSTS = frozenset({"www.youtube.com", "youtube.com", "m.youtube.com"})


def _is_safe_youtube_search_url(url: str) -> bool:
    """True only if `url` is genuinely an http(s) request to a YouTube host
    with a /results search path — not merely a string that contains that
    substring somewhere."""
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False
    return (
        parsed.scheme in ("http", "https")
        and parsed.hostname is not None
        and parsed.hostname.lower() in _YOUTUBE_ALLOWED_HOSTS
        and parsed.path.startswith("/results")
        and "search_query=" in (parsed.query or "")
    )


def _resolve_youtube_direct_url(url_or_query: str) -> str:
    """If the URL is a genuine YouTube search-results URL (verified by
    parsed hostname/scheme/path, not a substring match), resolves it to the
    first playable watch?v= URL. Anything else is returned unchanged —
    this function must never fetch an arbitrary caller-supplied URL."""
    if _is_safe_youtube_search_url(url_or_query):
        try:
            req = urllib.request.Request(
                url_or_query,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                matches = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
                if not matches:
                    matches = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
                if matches:
                    return f"https://www.youtube.com/watch?v={matches[0]}"
        except Exception:
            pass
    return url_or_query


class OpenBrowserTool(BaseTool):
    """Opens a web page or searches for a query in the active tab (or new tab if requested)."""

    @property
    def name(self) -> str:
        return "open_browser"

    @property
    def description(self) -> str:
        return "Navigates browser to URL/query. Navigates active tab by default; opens new tab only if new_tab=True."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.LOW_RISK

    def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        url = kwargs.get("url", "")
        new_tab = bool(kwargs.get("new_tab", False))

        try:
            if url:
                target_url = url if url.startswith("http") else f"https://{url}"
            elif query:
                target_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            else:
                target_url = "https://www.google.com"

            # Auto-resolve YouTube search URLs into direct playable videos —
            # gated by a real parsed-hostname check, not a substring match.
            if _is_safe_youtube_search_url(target_url):
                target_url = _resolve_youtube_direct_url(target_url)

            # Check if a browser window is already open
            hwnd, proc = _find_browser_window()
            if hwnd:
                _focus_browser_window(hwnd)

                if new_tab:
                    # User EXPLICITLY requested a new tab: Ctrl + T
                    _send_shortcut(0x11, 0x54)  # Ctrl + T
                    time.sleep(0.12)
                    _set_clipboard(target_url)
                    _send_shortcut(0x11, 0x56)  # Ctrl + V
                    time.sleep(0.05)
                    _send_key(0x0D)             # VK_RETURN
                    return ToolResult(True, f"New tab opened and navigated to: {target_url}", self.name)
                else:
                    # Execute in the CURRENT ACTIVE TAB: Ctrl + L -> paste -> Enter
                    _send_shortcut(0x11, 0x4C)  # Ctrl + L (focus Omnibox in active tab)
                    time.sleep(0.08)
                    _set_clipboard(target_url)
                    _send_shortcut(0x11, 0x56)  # Ctrl + V
                    time.sleep(0.05)
                    _send_key(0x0D)             # VK_RETURN
                    return ToolResult(True, f"Current active tab navigated to: {target_url}", self.name)

            # If no browser window is open, launch fresh browser
            chrome_candidates = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            ]
            chrome_exe = None
            for p in chrome_candidates:
                if os.path.exists(p):
                    chrome_exe = p
                    break

            if chrome_exe:
                subprocess.Popen([chrome_exe, target_url])
                return ToolResult(True, f"Google Chrome launched at: {target_url}", self.name)
            else:
                webbrowser.open(target_url)
                return ToolResult(True, f"Browser launched at: {target_url}", self.name)
        except Exception as e:
            return ToolResult(False, f"Failed to open browser: {str(e)}", self.name, error=str(e))


class ControlBrowserTabsTool(BaseTool):
    """Controls browser tabs (switch to next tab, previous tab, close tab, new tab, switch by index)."""

    @property
    def name(self) -> str:
        return "control_tabs"

    @property
    def description(self) -> str:
        return "Switches, closes, or creates browser tabs ('next', 'previous', 'close', 'new', 'reopen', 'index')."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.LOW_RISK

    def execute(self, **kwargs) -> ToolResult:
        action = kwargs.get("action", "next").lower().strip()
        index = kwargs.get("index", 0)

        hwnd, proc = _find_browser_window()
        if not hwnd:
            if action in ("new", "naya", "open"):
                # If no browser is open and user says new tab, launch browser
                webbrowser.open("https://www.google.com")
                return ToolResult(True, "Browser launched with a new tab.", self.name)
            return ToolResult(False, "No active browser window found to control tabs.", self.name)

        try:
            _focus_browser_window(hwnd)

            # Next tab: Ctrl + Tab
            if action in ("next", "switch", "अगला", "बदलो", "change", "forward"):
                _send_shortcut(0x11, 0x09)  # Ctrl + Tab
                return ToolResult(True, "Switched to next tab.", self.name)

            # Previous tab: Ctrl + Shift + Tab
            elif action in ("previous", "prev", "पिछला", "back"):
                _send_shortcut(0x11, 0x10, 0x09)  # Ctrl + Shift + Tab
                return ToolResult(True, "Switched to previous tab.", self.name)

            # Close tab: Ctrl + W
            elif action in ("close", "बंद", "क्लोज़", "exit"):
                _send_shortcut(0x11, 0x57)  # Ctrl + W
                return ToolResult(True, "Current tab closed.", self.name)

            # New tab: Ctrl + T
            elif action in ("new", "naya", "open", "create", "नया"):
                _send_shortcut(0x11, 0x54)  # Ctrl + T
                return ToolResult(True, "New blank tab opened.", self.name)

            # Reopen closed tab: Ctrl + Shift + T
            elif action in ("reopen", "undo", "restore", "wapas"):
                _send_shortcut(0x11, 0x10, 0x54)  # Ctrl + Shift + T
                return ToolResult(True, "Recently closed tab reopened.", self.name)

            # Tab by index: Ctrl + 1..8, or Ctrl + 9 for last
            elif action == "index" or (isinstance(index, int) and 1 <= index <= 9):
                idx = int(index) if index else 1
                if idx < 1:
                    idx = 1
                if idx > 9:
                    idx = 9
                vk_key = 0x30 + idx  # 0x31 is '1', 0x39 is '9'
                _send_shortcut(0x11, vk_key)
                return ToolResult(True, f"Switched to tab #{idx}.", self.name)

            else:
                return ToolResult(False, f"Unknown tab action: {action}", self.name)
        except Exception as e:
            return ToolResult(False, f"Tab control error: {str(e)}", self.name, error=str(e))


class GetSystemStatusTool(BaseTool):
    """Returns quick system diagnostics."""

    @property
    def name(self) -> str:
        return "get_system_status"

    @property
    def description(self) -> str:
        return "Retrieves real-time CPU, RAM, Disk, and Battery diagnostics."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.READ_ONLY

    def execute(self, **kwargs) -> ToolResult:
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage("/").percent if os.path.exists("/") else 0
            battery = psutil.sensors_battery()
            bat_pct = f"{battery.percent}%" if battery else "N/A (AC Power)"

            summary = f"CPU: {cpu}% | RAM: {ram}% | Disk: {disk}% | Battery: {bat_pct}"
            return ToolResult(True, summary, self.name, data={"cpu": cpu, "ram": ram, "disk": disk})
        except Exception as e:
            return ToolResult(False, f"System diagnostic error: {str(e)}", self.name, error=str(e))


class GetObservedIssuesTool(BaseTool):
    """
    Answers 'what problem did you observe' — reads from Observe Mode's
    recorded issues (core/observability/observer.py), it does not run any
    new diagnostics itself. Read-only: this tool only explains, it never
    changes anything. If the user then wants it fixed, that goes through
    the separate, explicitly-confirmed auto-fix flow (core/observability/
    auto_fix.py), never through this tool call.
    """

    @property
    def name(self) -> str:
        return "get_observed_issues"

    @property
    def description(self) -> str:
        return (
            "Explains the most recently observed runtime problem (error, failed action, "
            "STT/TTS failure) in plain language with a suggested fix. Use this whenever the "
            "user asks what problem/issue/error JARVIS has noticed, seen, or observed. "
            "Read-only — does not change or fix anything."
        )

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.READ_ONLY

    def execute(self, **kwargs) -> ToolResult:
        try:
            from core.observability.observer import observer
            from core.observability.auto_fix import auto_fix_manager

            explanation = observer.explain_last_issue()
            last_issue = observer.get_last_issue()

            # Offering to fix HERE (as part of answering "what problem did
            # you observe") rather than proactively the moment an issue is
            # recorded is deliberate — an issue is only worth interrupting
            # the user about once they've actually asked; recording every
            # transient hiccup (a VAD false positive, one flaky network
            # call) is useful history, not something worth nagging about.
            if last_issue is not None and not auto_fix_manager.is_awaiting_confirmation():
                question = auto_fix_manager.propose_fix(last_issue)
                explanation = f"{explanation} {question}"

            data = {"issue_id": last_issue.id} if last_issue else {}
            return ToolResult(True, explanation, self.name, data=data)
        except Exception as e:
            return ToolResult(False, f"Could not retrieve observed issues: {str(e)}", self.name, error=str(e))


class CreateFolderTool(BaseTool):
    """Creates a new folder in user's Desktop or specified location."""

    @property
    def name(self) -> str:
        return "create_folder"

    @property
    def description(self) -> str:
        return "Creates a new folder on the Windows desktop."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.CONFIRMATION_REQUIRED

    def execute(self, **kwargs) -> ToolResult:
        rel_path = kwargs.get("path", "JARVIS_Workspace")
        try:
            desktop = Path(os.path.expanduser("~")) / "Desktop"
            target = desktop / rel_path
            target.mkdir(parents=True, exist_ok=True)
            return ToolResult(True, f"Folder created at: {target}", self.name)
        except Exception as e:
            return ToolResult(False, f"Failed to create folder: {str(e)}", self.name, error=str(e))


class SearchFilesTool(BaseTool):
    """Searches common user folders for files matching a query."""

    @property
    def name(self) -> str:
        return "search_files"

    @property
    def description(self) -> str:
        return "Searches Desktop, Documents, Downloads, and Pictures for files matching a name."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.READ_ONLY

    def execute(self, **kwargs) -> ToolResult:
        query = str(kwargs.get("query", "")).lower()
        location = str(kwargs.get("location", "")).strip().lower()
        results = []
        try:
            home = Path(os.path.expanduser("~"))
            folder_map = {
                "desktop": home / "Desktop",
                "documents": home / "Documents",
                "downloads": home / "Downloads",
                "pictures": home / "Pictures",
            }
            search_dirs = [folder_map[location]] if location in folder_map else list(folder_map.values())

            for folder in search_dirs:
                if not folder.exists():
                    continue
                for item in list(folder.iterdir())[:100]:
                    if query in item.name.lower():
                        results.append(f"{item.name} ({folder.name})")

            msg = f"Found {len(results)} matches: {', '.join(results[:5])}" if results else "No matching files found."
            return ToolResult(True, msg, self.name, data={"matches": results})
        except Exception as e:
            return ToolResult(False, f"File search error: {str(e)}", self.name, error=str(e))


class AnalyzeScreenTool(BaseTool):
    """
    Deep visual and application analysis of what is currently on the screen.

    Privacy-sensitive: when a cloud vision provider (Gemini/OpenAI) actually
    answers the question, a screenshot of the user's live screen is uploaded
    to that provider. This tool asks for explicit, persisted consent before
    the FIRST such upload ever happens (see app/config.py's
    SCREEN_ANALYSIS_CLOUD_CONSENT, revocable from Settings) — a denial does
    not block screen analysis entirely, it just keeps everything local (no
    screenshot pixels leave the machine) and answers from window-title
    heuristics instead.
    """

    @property
    def name(self) -> str:
        return "analyze_screen"

    @property
    def description(self) -> str:
        return (
            "Analyzes what is currently showing on the screen, active window, and answers user "
            "questions. May upload a screenshot to a cloud vision provider — requires one-time "
            "user consent, see Settings > Privacy."
        )

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.HIGH_RISK

    @property
    def self_confirms(self) -> bool:
        return True

    @property
    def default_timeout_seconds(self) -> float:
        # Confirmation wait (up to 30s, only on the first-ever call) plus
        # the cloud vision call chain's own worst-case (~30s: Gemini +
        # retry + OpenAI fallback, each with a 10s timeout).
        return 65.0

    def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        try:
            from app.config import config
            from core.system.screen_analyzer import screen_analyzer

            consent = getattr(config, "SCREEN_ANALYSIS_CLOUD_CONSENT", None)
            if consent is None:
                decision = confirmation_service.request(
                    tool_name=self.name,
                    action_description=(
                        "Screen analysis sends a screenshot of your screen to a cloud AI "
                        "provider (Google Gemini / OpenAI) so JARVIS can answer questions "
                        "about what's on screen.\n\n"
                        "Your screen may contain private information such as passwords, "
                        "messages, or financial details.\n\n"
                        "Allow cloud screen analysis? You can change this later in "
                        "Settings > Privacy."
                    ),
                    target="Cloud vision API (Gemini/OpenAI)",
                    risk_level="HIGH",
                )
                consent = bool(decision.approved)
                try:
                    config.SCREEN_ANALYSIS_CLOUD_CONSENT = consent
                    config.save_to_json()
                except Exception:
                    logger.exception("Failed to persist screen-analysis consent decision")
                logger.info("Screen analysis cloud consent decided: %s (%s)", consent, decision.reason)

            analysis = screen_analyzer.analyze_screen(query, allow_cloud=consent)
            return ToolResult(
                True,
                analysis["answer"],
                self.name,
                data=analysis,
            )
        except Exception as e:
            logger.exception("Screen analysis error")
            return ToolResult(False, f"Screen analysis error: {str(e)}", self.name, error=str(e))


class ControlWindowTool(BaseTool):
    """Minimizes, maximizes, restores, or closes application windows."""

    @property
    def name(self) -> str:
        return "control_window"

    @property
    def description(self) -> str:
        return "Controls active or named windows (minimize, maximize, restore, close)."

    # "close" can lose unsaved work, so it needs a real human decision;
    # minimize/maximize/restore are trivially reversible and don't.
    _CLOSE_ACTIONS = frozenset({"close", "बंद", "क्लोज़"})

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.CONFIRMATION_REQUIRED

    def permission_level_for(self, args) -> PermissionLevel:
        action = str(args.get("action", "minimize")).lower().strip()
        if action in self._CLOSE_ACTIONS:
            return PermissionLevel.CONFIRMATION_REQUIRED
        return PermissionLevel.LOW_RISK

    def confirmation_summary(self, args) -> str:
        action = str(args.get("action", "")).strip()
        app = str(args.get("app", "")).strip()
        return f"Close window: {app}" if app else f"Close the currently focused window ({action})"

    def execute(self, **kwargs) -> ToolResult:
        import ctypes
        action = kwargs.get("action", "minimize").lower().strip()
        app = kwargs.get("app", "").lower().strip()
        user32 = ctypes.windll.user32

        # Window command constants
        SW_MINIMIZE = 6
        SW_MAXIMIZE = 3
        SW_RESTORE = 9
        WM_CLOSE = 0x0010

        try:
            from core.system.screen_analyzer import screen_analyzer
            target_hwnd = None

            if app:
                # Search for window matching app name in process or title
                for w in screen_analyzer.get_visible_windows():
                    if app in w["process"].lower() or app in w["title"].lower():
                        target_hwnd = w["hwnd"]
                        break
            
            if not target_hwnd:
                fg = screen_analyzer.get_foreground_window()
                if fg:
                    target_hwnd = fg["hwnd"]

            if not target_hwnd:
                return ToolResult(False, "No active window detected to control.", self.name)

            if action in ("minimize", "मिनिमाइज़", "छोटा"):
                user32.ShowWindow(target_hwnd, SW_MINIMIZE)
                return ToolResult(True, "विंडो को सफलतापूर्वक मिनिमाइज़ कर दिया गया है।", self.name)
            elif action in ("maximize", "मैक्सिमाइज", "बड़ा"):
                user32.ShowWindow(target_hwnd, SW_MAXIMIZE)
                return ToolResult(True, "विंडो को मैक्सिमाइज़ कर दिया गया है।", self.name)
            elif action in ("restore", "रीस्टोर"):
                user32.ShowWindow(target_hwnd, SW_RESTORE)
                return ToolResult(True, "विंडो को रीस्टोर कर दिया गया है।", self.name)
            elif action in ("close", "बंद", "क्लोज़"):
                user32.PostMessageW(target_hwnd, WM_CLOSE, 0, 0)
                return ToolResult(True, "विंडो को बंद कर दिया गया है।", self.name)
            else:
                return ToolResult(False, f"अज्ञात विंडो एक्शन: '{action}'", self.name)
        except Exception as e:
            return ToolResult(False, f"Window control error: {str(e)}", self.name, error=str(e))


class VolumeControlTool(BaseTool):
    """Controls master system volume using Windows media virtual keys."""

    @property
    def name(self) -> str:
        return "control_volume"

    @property
    def description(self) -> str:
        return "Controls system audio volume (up, down, mute, unmute)."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.LOW_RISK

    def execute(self, **kwargs) -> ToolResult:
        import ctypes
        action = kwargs.get("action", "up").lower().strip()
        user32 = ctypes.windll.user32

        VK_VOLUME_MUTE = 0xAD
        VK_VOLUME_DOWN = 0xAE
        VK_VOLUME_UP = 0xAF

        def tap_key(code, times=1):
            for _ in range(times):
                user32.keybd_event(code, 0, 0, 0)
                user32.keybd_event(code, 0, 2, 0)
                ctypes.windll.kernel32.Sleep(15)

        try:
            if action in ("up", "increase", "बढ़ाओ", "ज्यादा"):
                tap_key(VK_VOLUME_UP, 4)
                return ToolResult(True, "सिस्टम वॉल्यूम बढ़ा दिया गया है।", self.name)
            elif action in ("down", "decrease", "कम करो", "घटाओ"):
                tap_key(VK_VOLUME_DOWN, 4)
                return ToolResult(True, "सिस्टम वॉल्यूम कम कर दिया गया है।", self.name)
            elif action in ("mute", "unmute", "म्यूट"):
                tap_key(VK_VOLUME_MUTE, 1)
                return ToolResult(True, "ऑडियो म्यूट / अनम्यूट टॉगल कर दिया गया है।", self.name)
            else:
                return ToolResult(False, f"Unknown volume action: {action}", self.name)
        except Exception as e:
            return ToolResult(False, f"Volume error: {str(e)}", self.name, error=str(e))


class MediaControlTool(BaseTool):
    """Controls playback of media (YouTube, Spotify, Media Player)."""

    @property
    def name(self) -> str:
        return "control_media"

    @property
    def description(self) -> str:
        return "Controls media playback (play/pause, next track, previous track)."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.LOW_RISK

    def execute(self, **kwargs) -> ToolResult:
        import ctypes
        action = kwargs.get("action", "play_pause").lower().strip()
        user32 = ctypes.windll.user32

        VK_MEDIA_NEXT_TRACK = 0xB0
        VK_MEDIA_PREV_TRACK = 0xB1
        VK_MEDIA_STOP = 0xB2
        VK_MEDIA_PLAY_PAUSE = 0xB3

        def tap_key(code):
            user32.keybd_event(code, 0, 0, 0)
            user32.keybd_event(code, 0, 2, 0)

        try:
            if action in ("play", "pause", "play_pause", "प्ले", "पॉज"):
                tap_key(VK_MEDIA_PLAY_PAUSE)
                return ToolResult(True, "मीडिया प्ले / पॉज टॉगल किया गया।", self.name)
            elif action in ("next", "अगला"):
                tap_key(VK_MEDIA_NEXT_TRACK)
                return ToolResult(True, "अगला ट्रैक प्ले किया जा रहा है।", self.name)
            elif action in ("previous", "prev", "पिछला"):
                tap_key(VK_MEDIA_PREV_TRACK)
                return ToolResult(True, "पिछला ट्रैक प्ले किया जा रहा है।", self.name)
            elif action in ("stop", "स्टॉप"):
                tap_key(VK_MEDIA_STOP)
                return ToolResult(True, "मीडिया बंद कर दिया गया है।", self.name)
            else:
                return ToolResult(False, f"Unknown media action: {action}", self.name)
        except Exception as e:
            return ToolResult(False, f"Media control error: {str(e)}", self.name, error=str(e))


class LockScreenTool(BaseTool):
    """Locks the Windows workstation instantly."""

    @property
    def name(self) -> str:
        return "lock_screen"

    @property
    def description(self) -> str:
        return "Locks the Windows workstation for security."

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.CONFIRMATION_REQUIRED

    def confirmation_summary(self, args) -> str:
        return "Lock the Windows workstation now"

    def execute(self, **kwargs) -> ToolResult:
        import ctypes
        try:
            ctypes.windll.user32.LockWorkStation()
            return ToolResult(True, "विंडोज वर्कस्टेशन को सुरक्षित रूप से लॉक कर दिया गया है।", self.name)
        except Exception as e:
            return ToolResult(False, f"Lock workstation error: {str(e)}", self.name, error=str(e))

