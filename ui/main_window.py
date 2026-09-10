"""
Root QMainWindow for the JARVIS native Windows desktop assistant.
Assembles Frameless Title Bar, Navigation Sidebar, QStackedWidget Pages,
Background System Telemetry Thread, and AI/Voice/Tool Event Orchestration.
"""
import sys
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QIcon, QScreen, QGuiApplication

from ui.styles.theme import theme
from ui.styles.qss import get_application_stylesheet
from ui.components.title_bar import JarvisTitleBar
from ui.components.sidebar import JarvisSidebar
from ui.components.background import JarvisBackgroundWidget
from ui.components.ai_core import AICoreState
from ui.pages import (
    HomePage,
    ChatPage,
    SystemPage,
    VoicePage,
    ControlPage,
    AppsPage,
    FilesPage,
    BrowserPage,
    AutomationPage,
    SkillsPage,
    HealthPage,
    SettingsPage,
)
from app.config import config
from core.ai.manager import ai_manager
from core.voice import intent_router
from core.voice.voice_engine import voice_engine, VoiceState
from core.voice.transcript_processor import to_hinglish_display
from core.tools.tool_manager import tool_manager
from core.system.monitor import SystemMonitorWorker, SystemTelemetry
from core.telemetry import now as telemetry_now, log_stage
from core.observability.observer import observer
from core.observability.auto_fix import auto_fix_manager, AutoFixWorker
from core.tools.confirmation import confirmation_service, ConfirmationRequest
from ui.components.confirmation_dialog import ToolConfirmationDialog

# Hard cap on how much text is ever spoken aloud in one reply. Full detail
# still shows in the chat UI — this only bounds what goes to TTS, so a long
# LLM answer (e.g. a bulleted capability list) can't turn into a 30-60s
# monologue. Cuts at the nearest sentence boundary under the limit.
MAX_SPOKEN_CHARS = 400


def _clip_for_speech(text: str, limit: int = MAX_SPOKEN_CHARS) -> str:
    if len(text) <= limit:
        return text
    import re
    sentences = re.split(r"(?<=[.!?।])\s+", text)
    clipped = ""
    for s in sentences:
        if len(clipped) + len(s) + 1 > limit:
            break
        clipped = f"{clipped} {s}".strip()
    return clipped or text[:limit].rstrip() + "..."


class TTSPreloadWorker(QThread):
    """Warms up the Kokoro ONNX model at startup so the first spoken reply
    doesn't pay the one-time model-load cost mid-conversation."""

    def run(self):
        try:
            from core.voice.kokoro_engine import kokoro_engine
            kokoro_engine._ensure_loaded()
        except Exception as e:
            print(f"[TTSPreloadWorker] Warm-up warning: {e}")


class LLMWarmupWorker(QThread):
    """Opens the HTTPS connection to the active LLM provider at startup so
    the first real command doesn't pay a TCP+TLS handshake mid-conversation
    — the same idea as TTSPreloadWorker, one layer earlier in the pipeline."""

    def run(self):
        try:
            provider = ai_manager.active_provider
            warm_up = getattr(provider, "warm_up", None)
            if callable(warm_up):
                warm_up()
        except Exception as e:
            print(f"[LLMWarmupWorker] Warm-up warning: {e}")


class STTPreloadWorker(QThread):
    """Loads the Faster-Whisper model at startup, same idea as
    TTSPreloadWorker — without this, the FIRST voice command of the
    session would pay the full model-load cost (and, if the weights
    haven't been downloaded yet, the download itself) before JARVIS could
    transcribe anything."""

    def run(self):
        try:
            from core.voice.stt_engine import stt_engine
            stt_engine.ensure_whisper_loaded()
        except Exception as e:
            print(f"[STTPreloadWorker] Warm-up warning: {e}")


class ToolExecutionWorker(QThread):
    """
    Runs tool calls off the GUI thread. Several tools (opening an app, focusing
    a window) legitimately block for up to a few seconds while polling for a
    window to appear — running that on the Qt main thread would freeze the
    entire UI for that duration. Fires alongside speech instead of waiting for
    it, since there's no real reason to make the user wait through the full
    spoken confirmation before JARVIS actually acts.
    """

    tool_result_ready = Signal(object)

    def __init__(self, tool_calls, parent: Optional[QWidget] = None, pipeline_t0: Optional[float] = None):
        super().__init__(parent)
        self.tool_calls = tool_calls
        self.pipeline_t0 = pipeline_t0 if pipeline_t0 is not None else telemetry_now()

    def run(self):
        t0 = self.pipeline_t0
        for call in self.tool_calls:
            log_stage("TOOL_CHOSEN", t0, tool=call.tool_name, args=call.arguments)
            try:
                result = tool_manager.execute_tool(call.tool_name, **call.arguments)
            except Exception as e:
                from core.tools.base import ToolResult
                result = ToolResult(False, f"Execution failed: {str(e)}", call.tool_name, error=str(e))
            log_stage(
                "TOOL_RESULT", t0, tool=call.tool_name,
                success=result.success, error=(result.error or "") if not result.success else "",
            )
            self.tool_result_ready.emit(result)


class AIInferenceWorker(QThread):
    """
    Background thread for planning a response to the user's command. Every
    prompt (voice or typed) first goes through core.voice.intent_router,
    which cleans the transcript, corrects known STT mis-hearings of technical
    vocabulary (Jarvis, Claude, CLI, LLM, API, etc.), and attempts a local,
    zero-network intent match with a confidence score — these resolve
    instantly, no LLM round-trip. A low-confidence local match asks a short
    clarification question instead of guessing. Only a genuine local miss
    escalates to the real LLM planner (Groq/etc.), using the corrected
    transcript so it benefits from the same vocabulary fixes.
    """

    inference_completed = Signal(object)

    def __init__(self, prompt: str, parent: Optional[QWidget] = None, pipeline_t0: Optional[float] = None):
        super().__init__(parent)
        self.prompt = prompt
        self.pipeline_t0 = pipeline_t0 if pipeline_t0 is not None else telemetry_now()

    def run(self):
        t0 = self.pipeline_t0
        from core.ai.base import AIResponse
        try:
            decision = intent_router.route(self.prompt, pipeline_t0=t0)

            if decision.needs_clarification:
                self.inference_completed.emit(
                    AIResponse(
                        content=decision.response_content,
                        provider_name="JARVIS Local Router",
                        model_name="Confidence Gate",
                    )
                )
                return

            if decision.source == "fast":
                try:
                    ai_manager.record_interaction(self.prompt, decision.response_content)
                except Exception:
                    pass
                self.inference_completed.emit(
                    AIResponse(
                        content=decision.response_content,
                        provider_name="JARVIS Fast Path",
                        model_name="Local Intent Router",
                        tool_calls=decision.tool_calls,
                    )
                )
                return

            # Local match missed — ask the LLM, using the corrected transcript
            # (vocabulary-fixed) rather than the raw one.
            response = ai_manager.ask(decision.corrected_transcript)
            log_stage(
                "AGENT_INTENT", t0, path="llm",
                tools=[c.tool_name for c in response.tool_calls], reply=response.content[:40],
            )
            # If this followed a clarification question, the LLM understanding
            # it counts as a resolution too — remember it so the same phrasing
            # is recognized directly next time.
            intent_router.resolve_llm_success(decision.corrected_transcript)
            self.inference_completed.emit(response)
        except Exception as e:
            print(f"[AIInferenceWorker] Inference error: {e}")
            log_stage("AGENT_INTENT", t0, path="error", error=str(e))
            observer.record_exception(e, category="ai_error", source="AIInferenceWorker")
            self.inference_completed.emit(
                AIResponse(
                    content="सर, मैंने आपकी बात सुन ली है। आज्ञा दीजिए!",
                    provider_name="JARVIS",
                    model_name="Neural"
                )
            )


class JarvisMainWindow(QMainWindow):
    """JARVIS Main Desktop Window."""

    def __init__(self, splash=None):
        super().__init__()
        self._splash = splash

        if self._splash:
            self._splash.set_progress(15, "INITIALIZING CYBERNETIC FRAMEWORK...")

        self.setWindowTitle(f"{config.APP_NAME} - {config.APP_SUBTITLE}")
        self.resize(config.DEFAULT_WIDTH, config.DEFAULT_HEIGHT)
        self.setMinimumSize(config.MIN_WIDTH, config.MIN_HEIGHT)

        # Frameless window flags for modern sci-fi HUD appearance
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self.setStyleSheet(get_application_stylesheet())

        if self._splash:
            self._splash.set_progress(25, "ASSEMBLING CYBERNETIC HUD INTERFACE...")

        self._init_ui()

        if self._splash:
            self._splash.set_progress(75, "CALIBRATING SYSTEM MONITORS & TELEMETRY...")

        self._init_system_monitor()

        if self._splash:
            self._splash.set_progress(85, "WIRING NEURAL EVENT DISPATCHERS...")

        self._wire_events()
        self._center_on_screen()

        # Voice Inactivity Timer (15 minutes silence -> standby 'System Online')
        self._voice_inactivity_timer = QTimer(self)
        self._voice_inactivity_timer.setSingleShot(True)
        timeout_ms = int(getattr(config, "VOICE_INACTIVITY_TIMEOUT_MINUTES", 15) * 60 * 1000)
        self._voice_inactivity_timer.setInterval(timeout_ms)
        self._voice_inactivity_timer.timeout.connect(self._on_voice_inactivity_timeout)

        if not self._splash:
            # When running without splash screen (e.g. tests), start standard background preloaders
            self._tts_preload_worker = TTSPreloadWorker(self)
            self._tts_preload_worker.start()

            self._llm_warmup_worker = LLMWarmupWorker(self)
            self._llm_warmup_worker.start()

            self._stt_preload_worker = STTPreloadWorker(self)
            self._stt_preload_worker.start()

    def _init_ui(self):
        # Root central widget with animated cybernetic HUD background effect
        central = JarvisBackgroundWidget(self)
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Custom Title Bar
        self.title_bar = JarvisTitleBar(self)
        self.title_bar.minimize_requested.connect(self.showMinimized)
        self.title_bar.maximize_requested.connect(self._toggle_maximize)
        self.title_bar.close_requested.connect(self.close)
        self.title_bar.sidebar_toggle_requested.connect(self._toggle_sidebar)
        self.title_bar.view_options_toggle_requested.connect(self._toggle_view_options)
        root_layout.addWidget(self.title_bar)

        # 2. Main Body: Sidebar (Left) + Pages (Center/Right)
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Navigation Sidebar — hidden by default (maximizes dashboard space);
        # toggled via the hamburger button in the title bar. Hidden widgets
        # take no layout space in Qt, so the pages area simply expands to
        # fill it.
        self.sidebar = JarvisSidebar(self)
        self.sidebar.setVisible(False)
        body_layout.addWidget(self.sidebar)

        if self._splash:
            self._splash.set_progress(32, "LOADING 3D HOLOGRAPHIC HUD CORE...")

        # Stacked Pages
        self.pages_stack = QStackedWidget(self)

        self.page_home = HomePage(self)

        if self._splash:
            self._splash.set_progress(48, "INITIALIZING VOICE & CHAT MODULES...")

        self.page_chat = ChatPage(self)
        self.page_voice = VoicePage(self)
        self.page_system = SystemPage(self)

        if self._splash:
            self._splash.set_progress(62, "CONFIGURING SYSTEM CONTROL & DIAGNOSTICS...")

        self.page_control = ControlPage(self)
        self.page_apps = AppsPage(self)
        self.page_files = FilesPage(self)
        self.page_browser = BrowserPage(self)
        self.page_automation = AutomationPage(self)
        self.page_skills = SkillsPage(self)
        self.page_health = HealthPage(self)
        self.page_settings = SettingsPage(self)

        self.pages_stack.addWidget(self.page_home)        # 0
        self.pages_stack.addWidget(self.page_chat)        # 1
        self.pages_stack.addWidget(self.page_voice)       # 2
        self.pages_stack.addWidget(self.page_system)      # 3
        self.pages_stack.addWidget(self.page_control)     # 4
        self.pages_stack.addWidget(self.page_apps)        # 5
        self.pages_stack.addWidget(self.page_files)       # 6
        self.pages_stack.addWidget(self.page_browser)     # 7
        self.pages_stack.addWidget(self.page_automation)  # 8
        self.pages_stack.addWidget(self.page_skills)      # 9
        self.pages_stack.addWidget(self.page_health)      # 10
        self.pages_stack.addWidget(self.page_settings)    # 11


        body_layout.addWidget(self.pages_stack, 1)
        root_layout.addWidget(body, 1)

    def _init_system_monitor(self):
        """Starts the background psutil telemetry worker thread."""
        self.monitor_worker = SystemMonitorWorker(interval_sec=1.5, parent=self)
        self.monitor_worker.telemetry_updated.connect(self._on_telemetry_updated)
        self.monitor_worker.start()

    def _wire_events(self):
        # Sidebar page navigation
        self.sidebar.page_changed.connect(self.pages_stack.setCurrentIndex)

        # Prompt Submissions from Home & Chat
        self.page_home.prompt_submitted.connect(self._handle_user_prompt)
        self.page_chat.prompt_submitted.connect(self._handle_user_prompt)

        # Voice Recognition Pipeline (Continuous Microphone)
        voice_engine.transcript_ready.connect(self._on_voice_transcript_received)

        # Voice Toggles
        self.page_home.voice_toggle_requested.connect(voice_engine.toggle_listening)
        self.page_chat.voice_toggle_requested.connect(voice_engine.toggle_listening)

        # Quick Actions Triggered from Home Dashboard
        self.page_home.quick_action_triggered.connect(self._handle_quick_action)

        # Voice Engine state transitions
        voice_engine.state_changed.connect(self._on_voice_state_changed)
        voice_engine.audio_amplitude.connect(self._on_audio_amplitude)
        voice_engine.speech_completed.connect(self._on_speech_completed)
        voice_engine.speech_interrupted.connect(self._on_speech_interrupted)

        # Tool execution logging to activity log
        tool_manager.tool_started.connect(
            lambda name: self.page_system.activity_log.log_event(f"Executing: {name}", "TOOL")
        )
        tool_manager.tool_finished.connect(self._on_tool_finished)

        # The real confirmation gate's UI half: whenever ANY tool call needs
        # a human decision (from any calling thread — see
        # core/tools/confirmation.py for why this connection is safe
        # cross-thread), show a real modal dialog and report the answer
        # back. Without this connection, ConfirmationService has no
        # listener at all and every CONFIRMATION_REQUIRED/HIGH_RISK tool
        # call is denied by default (fail-closed, not fail-open).
        confirmation_service.attach_handler(self._on_confirmation_requested)

    def _on_confirmation_requested(self, request: ConfirmationRequest):
        """
        Runs on the GUI thread (Qt queues delivery here automatically when
        the request originated on a background QThread). Shows a real
        modal Allow/Deny dialog and reports the decision back to
        ConfirmationService — this IS the human decision the calling
        thread is blocked waiting for.
        """
        self.page_system.activity_log.log_event(
            f"Confirmation requested: {request.tool_name} ({request.risk_level} risk)", "SEC"
        )
        try:
            dlg = ToolConfirmationDialog(request, self)
            dlg.exec()
            approved = dlg.approved
        except Exception:
            # A crash in the dialog itself must still resolve the pending
            # request (fail closed) rather than leave the calling thread
            # blocked until ConfirmationService's own timeout.
            approved = False
        confirmation_service.resolve(
            request.request_id, approved, reason="user_approved" if approved else "user_denied"
        )
        self.page_system.activity_log.log_event(
            f"Confirmation {'approved' if approved else 'denied'}: {request.tool_name}", "SEC"
        )

    def _center_on_screen(self):
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            x = (screen_geo.width() - self.width()) // 2
            y = (screen_geo.height() - self.height()) // 2
            self.move(x, y)

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.title_bar.set_maximized_state(False)
        else:
            self.showMaximized()
            self.title_bar.set_maximized_state(True)

    def changeEvent(self, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.WindowStateChange:
            if hasattr(self, "title_bar"):
                self.title_bar.set_maximized_state(self.isMaximized())
        super().changeEvent(event)

    def _toggle_sidebar(self):
        self.sidebar.setVisible(not self.sidebar.isVisible())

    def _toggle_view_options(self):
        self.page_home.right_panel.setVisible(not self.page_home.right_panel.isVisible())

    def _on_telemetry_updated(self, t: SystemTelemetry):
        self.page_home.update_telemetry(t)
        self.page_system.update_telemetry(t)

    def _reset_voice_inactivity_timer(self):
        """Resets the 15-minute inactivity countdown while voice listening is active."""
        if getattr(config, "ALWAYS_LISTEN", True) or voice_engine.state == VoiceState.LISTENING:
            timeout_ms = int(getattr(config, "VOICE_INACTIVITY_TIMEOUT_MINUTES", 15) * 60 * 1000)
            self._voice_inactivity_timer.start(timeout_ms)

    def _on_voice_inactivity_timeout(self):
        """
        Triggered when there is no user input for 15 minutes while listening.
        Switches from active listening to standby ('System Online').
        """
        print("[VoiceEngine] 15 minutes of inactivity reached — entering standby ('System Online').")
        self.page_system.activity_log.log_event("15 mins inactivity — voice standby (System Online)", "INFO")
        voice_engine.stop_listening()
        self.title_bar.set_capsule_status("System Online", "ONLINE")
        self.page_home.set_ai_state(AICoreState.IDLE)
        self.page_home.set_mic_active(False)

    def _on_voice_state_changed(self, state: VoiceState):
        if state == VoiceState.LISTENING:
            self.title_bar.set_capsule_status("Listening...", "LISTENING")
            self.page_home.set_ai_state(AICoreState.LISTENING)
            self.page_home.set_mic_active(True)
            self.page_home.set_listening_hint()
            self.page_system.activity_log.log_event("Voice capture activated", "VOICE")
            self._reset_voice_inactivity_timer()
        elif state == VoiceState.PROCESSING:
            self._voice_inactivity_timer.stop()
            # Single anchor for the WHOLE interaction (mic -> STT -> agent ->
            # tool -> TTS), so "total latency" is honest about when the user
            # actually started speaking, not just when text became available.
            # PROCESSING is entered twice per turn: once when the mic detects
            # NEW speech (this must start a fresh anchor), and again when TTS
            # begins synthesizing the reply (voice_engine.speak() holds
            # PROCESSING until audio starts — this must NOT reset the anchor,
            # or "total latency" would only ever measure the TTS portion).
            # _is_processing_ai is True for exactly that second, reused entry
            # (set in _handle_user_prompt, cleared once the turn fully
            # completes) — gating on it, instead of "only if unset", is what
            # actually distinguishes the two. The previous "only if unset"
            # check set the anchor once for the entire app session and then
            # never again, so every later utterance's STT_RESULT/TOTAL_LATENCY
            # was measured against the FIRST utterance ever, not its own turn
            # — that's why those numbers grew into the minutes over a session.
            if not getattr(self, "_is_processing_ai", False):
                self._pipeline_t0 = telemetry_now()
                log_stage("MIC_INPUT_START", self._pipeline_t0)
            self.title_bar.set_capsule_status("Thinking...", "PROCESSING")
            self.page_home.set_ai_state(AICoreState.PROCESSING)
            self.page_home.set_processing_hint()
            self.page_system.activity_log.log_event("Speech processing phonemes", "VOICE")
        elif state == VoiceState.SPEAKING:
            self._voice_inactivity_timer.stop()
            self.title_bar.set_capsule_status("Vocalizing...", "SPEAKING")
            self.page_home.set_ai_state(AICoreState.SPEAKING)
            self.page_system.activity_log.log_event("Audio vocalization active", "VOICE")
        elif state == VoiceState.MIC_UNAVAILABLE:
            self._voice_inactivity_timer.stop()
            # Previously there was no such state — a dead mic thread left
            # the UI stuck showing "Listening..." forever. This is a clear,
            # distinct, recoverable state: click the mic button to retry.
            self.title_bar.set_capsule_status("Mic Unavailable", "WARN")
            self.page_home.set_ai_state(AICoreState.IDLE)
            self.page_home.set_mic_active(False)
            self.page_home.set_mic_unavailable_hint()
            self.page_system.activity_log.log_event(
                "Microphone unavailable — click the mic button to retry", "WARN"
            )
            try:
                observer.record_issue(
                    "mic_unavailable",
                    summary="Microphone became unavailable (disconnected, permission revoked, or listener crashed)",
                    source="voice_engine",
                )
            except Exception:
                pass
        else:
            self._voice_inactivity_timer.stop()
            self.title_bar.set_capsule_status("System Online", "ONLINE")
            self.page_home.set_ai_state(AICoreState.IDLE)
            self.page_home.set_mic_active(False)

    def _on_audio_amplitude(self, amp: float):
        self.page_home.set_audio_amplitude(amp)
        self.title_bar.set_audio_amplitude(amp)

    def _on_speech_completed(self):
        log_stage("TOTAL_LATENCY", getattr(self, "_pipeline_t0", None))
        self._is_processing_ai = False
        if config.ALWAYS_LISTEN:
            self.title_bar.set_capsule_status("Listening...", "LISTENING")
            self.page_home.set_ai_state(AICoreState.LISTENING)
            self.page_home.set_mic_active(True)
            self.page_home.set_listening_hint()
            self._reset_voice_inactivity_timer()
        else:
            self.title_bar.set_capsule_status("System Online", "ONLINE")
            self.page_home.set_ai_state(AICoreState.IDLE)
            self.page_home.set_mic_active(False)

    def _on_speech_interrupted(self):
        """User spoke over JARVIS's reply — same cleanup as a normal finish,
        since interruption bypasses speech_completed (must still clear
        _is_processing_ai or the anti-echo guard would ignore speech forever)."""
        self._is_processing_ai = False
        try:
            ai_manager.mark_last_assistant_message_interrupted()
        except Exception:
            pass
        self.page_system.activity_log.log_event("Speech interrupted by user — listening", "VOICE")
        if config.ALWAYS_LISTEN:
            self.title_bar.set_capsule_status("Listening...", "LISTENING")
            self.page_home.set_ai_state(AICoreState.LISTENING)
            self.page_home.set_mic_active(True)
            self.page_home.set_listening_hint()
            self._reset_voice_inactivity_timer()

    def _on_voice_transcript_received(self, text: str):
        """Called whenever speech recognition transcribes user speech."""
        if not text or not text.strip():
            return
        cleaned = text.strip()
        self._reset_voice_inactivity_timer()
        # Reuses the MIC_INPUT_START anchor set when PROCESSING began, so
        # STT_RESULT (and everything after it) reads as real elapsed time
        # since the user started speaking, not from an arbitrary later point.
        mic_t0 = getattr(self, "_pipeline_t0", None)
        log_stage("STT_RESULT", mic_t0, text=cleaned[:40])

        # Real-time duplex barge-in: If user speaks while JARVIS is actively speaking,
        # immediately halt active audio speech playback so the user's interruption takes precedence.
        if voice_engine.is_speaking():
            print(f"[Main] Real-time duplex barge-in: user spoke while JARVIS was speaking ('{cleaned}').")
            voice_engine._on_barge_in_detected()
        elif getattr(self, "_is_processing_ai", False):
            print(f"[Main] User interjected while AI is processing: '{cleaned}'")
            # Invalidate older processing turn so new prompt takes over
            self._ai_worker_generation = getattr(self, "_ai_worker_generation", 0) + 1

        # Romanized purely for what the user SEES — casual Hinglish spelling
        # (tum kya kar rahe ho) reads far more naturally here than formal
        # Sanskrit-style transliteration would. The actual AI pipeline below
        # still gets the original Devanagari `cleaned`: every downstream
        # language check (jarvis_brain, TTS segmentation, intent routing)
        # keys off the real Devanagari Unicode range, so romanizing before
        # that point would make Hindi speech silently misroute as English.
        display_text = to_hinglish_display(cleaned)

        # Display transcript in the marked HUD banner on HomePage
        self.page_home.set_live_speech(display_text, is_user=True)
        # Display transcript in input field and chat for immediate visual feedback
        self.page_home.input_edit.setText(display_text)
        self.page_chat.chat_console.add_message("user", display_text)
        self.page_system.activity_log.log_event(f"Voice recognized: '{cleaned}'", "VOICE")
        self._handle_user_prompt(cleaned, pipeline_t0=mic_t0)

    def _handle_user_prompt(self, prompt: str, pipeline_t0: Optional[float] = None):
        """
        Processes user command asynchronously via AIInferenceWorker for 0-lag
        60 FPS performance. Every command — voice or typed — is routed through
        here first: the agent (fast-path router or LLM planner) decides which
        tool to use, THEN ToolExecutionWorker runs it. There is no path that
        executes a tool without going through this selection step first.
        """
        # User supplied input: reset 15-minute voice inactivity countdown
        self._reset_voice_inactivity_timer()

        # Auto-fix confirmation takes priority over normal LLM routing: if
        # JARVIS just asked "Should I ask Claude to fix this?", THIS turn's
        # reply must be interpreted as answering that question, not sent
        # through the model as an ordinary new request (a bare "haan"/"yes"
        # would otherwise get answered conversationally and the pending
        # confirmation would sit there stale forever).
        if auto_fix_manager.is_awaiting_confirmation():
            self._handle_pending_fix_reply(prompt)
            return

        # pipeline_t0 is provided when this call continues a voice interaction
        # (reuses the MIC_INPUT_START anchor); typed input / quick actions
        # start a fresh timer here since there was no prior mic event.
        self._pipeline_t0 = pipeline_t0 if pipeline_t0 is not None else telemetry_now()
        log_stage("AGENT_START", self._pipeline_t0, prompt=prompt[:40])

        self._is_processing_ai = True
        self.title_bar.set_capsule_status("Thinking...", "THINKING")
        self.page_home.set_ai_state(AICoreState.THINKING)
        self.page_chat.show_thinking(True)
        self.page_system.activity_log.log_event(f"User directive: '{prompt}'", "AI")

        if hasattr(self, "_ai_worker") and self._ai_worker and self._ai_worker.isRunning():
            # A 300ms wait does NOT guarantee the previous worker is done —
            # a real LLM call routinely takes well over a second. Without
            # generation tracking below, that older worker's completion
            # (arriving late, possibly AFTER this newer one) would still be
            # processed as if it were the current answer: overwriting the
            # correct reply with a stale one, restarting TTS mid-conversation,
            # and stomping _pipeline_t0/_is_processing_ai out from under the
            # interaction actually in progress. This is what "ask a couple
            # of times and JARVIS stops answering" traced back to — the same
            # class of bug _tts_generation already guards against for speech.
            self._ai_worker.wait(300)

        self._ai_worker_generation = getattr(self, "_ai_worker_generation", 0) + 1
        my_generation = self._ai_worker_generation

        self._ai_worker = AIInferenceWorker(prompt, self, pipeline_t0=self._pipeline_t0)
        self._ai_worker.inference_completed.connect(
            lambda response: self._on_ai_inference_done(response, my_generation)
        )
        self._ai_worker.start()

    def _on_ai_inference_done(self, response, generation: Optional[int] = None):
        """Delivers AI response smoothly to UI and vocalizes without any GUI freeze."""
        if generation is not None and generation != getattr(self, "_ai_worker_generation", generation):
            print(f"[Main] Ignoring stale AI inference completion (gen {generation}, current {self._ai_worker_generation}).")
            return
        t0 = getattr(self, "_pipeline_t0", None) or telemetry_now()
        try:
            enc = sys.stdout.encoding or "utf-8"
            safe_text = str(response.content).encode(enc, errors="replace").decode(enc)
            print(f"[Main] AI Brain responded ({response.latency_ms:.1f}ms): '{safe_text}'")
        except Exception:
            pass
        # 1. Deliver response to chat, HUD banner, and event logs
        self.page_home.set_live_speech(response.content, is_user=False)
        self.page_chat.receive_ai_message(response.content)
        self.page_system.activity_log.log_event(f"AI response generated ({response.latency_ms:.1f}ms)", "AI")

        # 2. Speak the confirmation AND execute any actions in parallel — no reason
        # to make the user wait through the full spoken reply before JARVIS acts.
        # Spoken text is capped (MAX_SPOKEN_CHARS) so a verbose LLM answer can't
        # turn into a 30-60s monologue — the full text still shows in the chat.
        if config.SPEAK_RESPONSES and response.content and response.content.strip():
            log_stage("TTS_START", t0, chars=len(response.content))
            voice_engine.speak(_clip_for_speech(response.content), pipeline_t0=t0)
        else:
            # Action-only replies (the LLM emitted just a tool call, no
            # conversational text) legitimately clean down to an empty
            # string — nothing to speak, so skip TTS instead of pushing
            # blank text through the synthesis pipeline. Nothing else will
            # move the UI off "Thinking..." in this path (that normally
            # happens when speech_completed fires), so mirror that reset
            # here manually.
            self._is_processing_ai = False
            if config.ALWAYS_LISTEN:
                voice_engine.resume_listening()
                self.title_bar.set_capsule_status("Listening...", "LISTENING")
                self.page_home.set_ai_state(AICoreState.LISTENING)
                self.page_home.set_mic_active(True)
                self.page_home.set_listening_hint()
                self._reset_voice_inactivity_timer()
            else:
                self.title_bar.set_capsule_status("System Online", "ONLINE")
                self.page_home.set_ai_state(AICoreState.IDLE)
                self.page_home.set_mic_active(False)

        if response.tool_calls:
            if hasattr(self, "_tool_worker") and self._tool_worker and self._tool_worker.isRunning():
                self._tool_worker.wait(200)

            for call in response.tool_calls:
                self.page_system.activity_log.log_event(f"Executing confirmed tool: {call.tool_name}", "TOOL")

            self._tool_worker = ToolExecutionWorker(response.tool_calls, self, pipeline_t0=t0)
            self._tool_worker.tool_result_ready.connect(self._on_tool_result_ready)
            self._tool_worker.start()

    # Tools whose actual value IS the answer (vision, lookups) rather than a
    # side effect — their result must be spoken, not just logged, since the
    # AI's own placeholder reply ("let me look...") isn't the real answer.
    _SPEAK_TOOL_RESULTS = {"analyze_screen"}

    def _on_tool_result_ready(self, result):
        # Reuses the same pipeline_t0 anchor as the rest of this turn so
        # this speak() call's TTS_* telemetry reads as real elapsed time
        # since the user spoke, instead of logging "T+0ms" against its own
        # fresh anchor (which is what made the gap between the "one sec..."
        # placeholder and the actual spoken answer invisible in the logs).
        t0 = getattr(self, "_pipeline_t0", None)
        if result.success:
            self.page_chat.chat_console.add_message("assistant", f"⚡ {result.output}")
            self.page_system.activity_log.log_event(f"Tool execution succeeded: {result.output}", "TOOL")
            if result.tool_name in self._SPEAK_TOOL_RESULTS and config.SPEAK_RESPONSES:
                self.page_home.set_live_speech(result.output, is_user=False)
                voice_engine.speak(_clip_for_speech(result.output), pipeline_t0=t0)
        else:
            self.page_system.activity_log.log_event(f"Tool execution failed: {result.output}", "WARN")
            observer.record_issue(
                "tool_failure",
                summary=f"Tool '{result.tool_name}' failed: {result.output}",
                details=result.error or result.output,
                source=result.tool_name,
            )
            if result.tool_name in self._SPEAK_TOOL_RESULTS and config.SPEAK_RESPONSES:
                voice_engine.speak(_clip_for_speech(result.output), pipeline_t0=t0)

    def _handle_pending_fix_reply(self, text: str):
        """Answers a pending 'Should I ask Claude to fix this?' question.
        Never reaches the LLM — see the module docstring in auto_fix.py for
        why this has to be a hardcoded yes/no gate rather than a tool call."""
        outcome = auto_fix_manager.handle_reply(text)
        if outcome is None:
            return
        approved, task = outcome
        if not approved or task is None:
            reply = "ठीक है, मैं कोई बदलाव नहीं करूँगा।" if config.FORCE_HINDI_ONLY_SPEECH else "Okay, I won't make any changes."
            self.page_chat.receive_ai_message(reply)
            self.page_home.set_live_speech(reply, is_user=False)
            if config.SPEAK_RESPONSES:
                voice_engine.speak(_clip_for_speech(reply))
            return

        reply = "ठीक है, मैं Claude से यह ठीक करवाता हूँ। इसमें थोड़ा समय लगेगा।" if config.FORCE_HINDI_ONLY_SPEECH else "Okay, asking Claude to fix this now — this may take a little while."
        self.page_chat.receive_ai_message(reply)
        self.page_home.set_live_speech(reply, is_user=False)
        self.page_system.activity_log.log_event(f"Auto-fix approved: task {task.id}", "AUTOFIX")
        if config.SPEAK_RESPONSES:
            voice_engine.speak(_clip_for_speech(reply))

        if hasattr(self, "_fix_worker") and self._fix_worker and self._fix_worker.isRunning():
            self._fix_worker.wait(200)
        self._fix_worker = AutoFixWorker(task, self)
        self._fix_worker.finished_fix.connect(self._on_fix_finished)
        self._fix_worker.start()

    def _on_fix_finished(self, task, success: bool, report: str):
        self.page_system.activity_log.log_event(
            f"Auto-fix {'succeeded' if success else 'failed'} for task {task.id}: {report[:200]}",
            "AUTOFIX",
        )
        if success:
            reply = "सर, मैंने Claude से समस्या ठीक करवा दी है और टेस्ट पास हो गए हैं।" if config.FORCE_HINDI_ONLY_SPEECH else "Sir, Claude finished the fix and the test suite passed."
        else:
            reply = "सर, ठीक करने की कोशिश हुई, लेकिन यह पूरी तरह से सफल नहीं रहा। कृपया लॉग देख लें।" if config.FORCE_HINDI_ONLY_SPEECH else "Sir, the fix attempt didn't fully succeed — please check the logs."
        self.page_chat.receive_ai_message(reply)
        self.page_home.set_live_speech(reply, is_user=False)
        if config.SPEAK_RESPONSES:
            voice_engine.speak(_clip_for_speech(reply))

    def _handle_quick_action(self, action_id: str):
        self.page_system.activity_log.log_event(f"Quick action triggered: {action_id}", "SYS")

        action_prompts = {
            "vscode": "Open Visual Studio Code",
            "chrome": "Open Google Chrome",
            "screenshot": "Take a screenshot of the desktop",
            "notepad": "Open Notepad",
            "search_files": "Search files on desktop",
            "control_apps": "Control Applications",
            "system_info": "Show system status and diagnostics",
            "custom_action": "Open automation sequences",
        }

        if action_id in ["search_files", "control_apps", "system_info", "custom_action"]:

            if action_id == "search_files":
                self.sidebar.select_page(6)
                voice_engine.speak("सर, फाइल्स नेविगेटर खोला जा रहा है।")
            elif action_id == "control_apps":
                self.sidebar.select_page(5)
                voice_engine.speak("सर, एप्लिकेशन कंट्रोलर खोला जा रहा है।")
            elif action_id == "system_info":
                self.sidebar.select_page(3)
                voice_engine.speak("सर, सिस्टम स्थिति खोली जा रही है।")
            elif action_id == "custom_action":
                self.sidebar.select_page(8)
                voice_engine.speak("सर, टास्क ऑटोमेशन खोला जा रहा है।")
        else:

            prompt = action_prompts.get(action_id, f"Execute {action_id}")
            self.page_home.input_edit.setText(prompt)
            # Route through voice confirmation first -> then execute
            self._handle_user_prompt(prompt)

    def _on_tool_finished(self, result):
        status_tag = "TOOL" if result.success else "WARN"
        self.page_system.activity_log.log_event(f"Tool {result.tool_name}: {result.output}", status_tag)

    def showEvent(self, event):
        super().showEvent(event)
        # On launch, initialize speech greeting and continuous listening
        QTimer.singleShot(800, self._on_startup_greeting)

    def _on_startup_greeting(self):
        if config.ALWAYS_LISTEN:
            user = config.USER_NAME.split()[0] if config.USER_NAME else "सर"
            greeting = f"नमस्ते {user}, जार्विस ऑनलाइन है और आपकी बात सुन रहा है।"
            self.title_bar.set_capsule_status("Listening...", "LISTENING")
            self.page_home.set_ai_state(AICoreState.LISTENING)
            self.page_home.set_mic_active(True)
            self.page_home.set_live_speech(greeting, is_user=False)
            self._reset_voice_inactivity_timer()
            voice_engine.speak(greeting)


    def closeEvent(self, event):
        """Clean shutdown of background threads."""
        try:
            if hasattr(self, "_voice_inactivity_timer") and self._voice_inactivity_timer:
                self._voice_inactivity_timer.stop()
        except Exception:
            pass
        try:
            voice_engine.shutdown()
        except Exception:
            pass
        try:
            if hasattr(self, "monitor_worker") and self.monitor_worker:
                self.monitor_worker.stop()
                self.monitor_worker.wait(1000)
        except Exception:
            pass
        try:
            if hasattr(self, "_ai_worker") and self._ai_worker and self._ai_worker.isRunning():
                self._ai_worker.wait(1000)
        except Exception:
            pass
        try:
            if hasattr(self, "_tool_worker") and self._tool_worker and self._tool_worker.isRunning():
                self._tool_worker.wait(1000)
        except Exception:
            pass
        try:
            # Let the TTS, LLM, and STT preload workers finish cleanly rather than racing interpreter shutdown
            if hasattr(self, "_tts_preload_worker") and self._tts_preload_worker and self._tts_preload_worker.isRunning():
                self._tts_preload_worker.wait(2000)
        except Exception:
            pass
        try:
            if hasattr(self, "_llm_warmup_worker") and self._llm_warmup_worker and self._llm_warmup_worker.isRunning():
                self._llm_warmup_worker.wait(1000)
        except Exception:
            pass
        try:
            if hasattr(self, "_stt_preload_worker") and self._stt_preload_worker and self._stt_preload_worker.isRunning():
                self._stt_preload_worker.wait(1500)
        except Exception:
            pass
        event.accept()

