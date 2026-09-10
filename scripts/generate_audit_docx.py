"""
One-off generator for the JARVIS Production Audit Report .docx.
Not part of the app itself - run manually, produces the report at repo root.
"""
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

doc = Document()

# ---------- base style ----------
style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(10.5)

RED = RGBColor(0xC0, 0x00, 0x00)
ORANGE = RGBColor(0xC5, 0x5A, 0x00)
DARKBLUE = RGBColor(0x1F, 0x3B, 0x57)
GREY = RGBColor(0x55, 0x55, 0x55)


def set_cell_shading(cell, hex_color):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    cell._tc.get_or_add_tcPr().append(shd)


def add_title(text, subtitle=None):
    h = doc.add_heading(text, level=0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if subtitle:
        p = doc.add_paragraph(subtitle)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.runs[0].italic = True
        p.runs[0].font.color.rgb = GREY


def h1(text):
    doc.add_heading(text, level=1)


def h2(text):
    doc.add_heading(text, level=2)


def h3(text):
    doc.add_heading(text, level=3)


def p(text, bold=False, italic=False, color=None, size=None):
    para = doc.add_paragraph()
    run = para.add_run(text)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = color
    if size:
        run.font.size = Pt(size)
    return para


def bullet(text, bold_prefix=None):
    para = doc.add_paragraph(style="List Bullet")
    if bold_prefix:
        r = para.add_run(bold_prefix)
        r.bold = True
        para.add_run(text)
    else:
        para.add_run(text)
    return para


def numbered(text):
    para = doc.add_paragraph(style="List Number")
    para.add_run(text)
    return para


def code_block(text):
    para = doc.add_paragraph()
    run = para.add_run(text)
    run.font.name = "Consolas"
    run.font.size = Pt(8.5)
    para.paragraph_format.left_indent = Inches(0.25)
    return para


def table_from_rows(headers, rows, col_widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_cells = t.rows[0].cells
    for i, htext in enumerate(headers):
        hdr_cells[i].text = ""
        run = hdr_cells[i].paragraphs[0].add_run(htext)
        run.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        set_cell_shading(hdr_cells[i], "1F3B57")
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in t.rows:
                row.cells[i].width = Inches(w)
    doc.add_paragraph()
    return t


def sev_color(sev_text):
    s = sev_text.upper()
    if "P0" in s or "CRITICAL" in s:
        return RED
    if "P1" in s or "HIGH" in s:
        return ORANGE
    return None


# =====================================================================
# TITLE PAGE
# =====================================================================
add_title("JARVIS PROJECT AUDIT", "Production-Grade Codebase, Security, AI/Agent & Reliability Audit")
p("")
meta = doc.add_paragraph()
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
meta_run = meta.add_run(
    "Repository: C:\\Users\\pramo\\Desktop\\jarvis  |  Prepared as a full end-to-end audit combining direct\n"
    "code tracing of the AI\u2192Tool\u2192System boundary with five parallel deep-dive investigations covering the\n"
    "voice subsystem, AI/LLM providers & memory, UI/3D-HUD frontend, testing/config/dependencies/git hygiene,\n"
    "and cross-cutting code quality, reliability, and performance."
)
meta_run.italic = True
meta_run.font.size = Pt(9.5)
meta_run.font.color.rgb = GREY
doc.add_page_break()

# =====================================================================
# 1. EXECUTIVE SUMMARY
# =====================================================================
h1("1. Executive Summary")

score_p = doc.add_paragraph()
r = score_p.add_run("Overall Health Score: 34 / 100")
r.bold = True
r.font.size = Pt(16)
r.font.color.rgb = RED

table_from_rows(
    ["Readiness", "Status"],
    [
        ["Production readiness", "NO"],
        ["Security readiness", "NO"],
        ["Reliability readiness", "NO"],
        ["Test readiness", "NO"],
    ],
    col_widths=[3.5, 2.5],
)

p("Biggest reasons:", bold=True)
bullet("The app cannot run on a fresh install. requests (used unconditionally by the default Groq provider) "
       "and kokoro_onnx/soundfile (the default TTS engine) are imported in code but absent from requirements.txt. "
       "A clean pip install -r requirements.txt && python main.py crashes at import time. Confirmed independently "
       "by two separate audits.")
bullet("The permission/confirmation system is fake. REQUIRE_CONFIRMATION_FOR_ACTIONS defaults to False, and the "
       "Qt signals meant to show an approval dialog (confirmation_needed, permission_denied, tool_requires_approval) "
       "are never connected to anything anywhere in the codebase. Every tool marked \u201crequires confirmation\u201d "
       "\u2014 launching/closing apps, clicking the screen, pressing keys, creating folders, and delegating code "
       "changes to the Claude CLI \u2014 executes immediately, unconditionally.")
bullet("JARVIS silently uploads the user\u2019s screen to third-party cloud APIs and litters their Desktop with "
       "permanent screenshots, with zero consent prompt or disclosure, every time a screen question is asked.")
bullet("The AI decision layer can be silently overridden. When the selected cloud LLM decides not to call a tool, "
       "several providers ask an unrelated offline regex engine for its own opinion and execute that instead \u2014 "
       "an action neither the human nor the chosen AI approved.")
bullet("No wake word. With the shipped default (ALWAYS_LISTEN=True), JARVIS transcribes and reasons about "
       "everything picked up by the microphone, continuously, with no trigger phrase.")
bullet("Zero automated test coverage of anything security- or reliability-critical \u2014 no tests for permission "
       "enforcement, tool execution correctness, API failure handling, or concurrency. Of ~74 files in tests/, only "
       "one (test_components.py) is a real, if superficial, regression suite; ~65 are one-off 3D-model-tuning or "
       "manual-visual scripts that don\u2019t belong in a test directory.")
bullet("Underlying engineering quality is genuinely uneven, not uniformly bad \u2014 the STT/TTS pipeline, "
       "generation-tracking for stale async results, and the telemetry/observability layer show real craftsmanship "
       "and thoughtful comments. The problems are concentrated at the safety boundary (confirmation gate, tool "
       "permissions) and in fresh-install/documentation hygiene, not throughout.")

doc.add_page_break()

# =====================================================================
# 2. ARCHITECTURE SUMMARY
# =====================================================================
h1("2. Architecture Summary")
p("JARVIS is a native PySide6/Qt6 Windows desktop application (not a client-server web app \u2014 most traditional "
  "web-audit categories like CORS/CSRF/SQL injection/session auth don\u2019t apply). It has one embedded exception: "
  "a Chromium-based QWebEngineView hosting a local three.js 3D face (ui/web/jarvis_hud.html), despite the README "
  "explicitly claiming \u201cNO web views.\u201d")

diagram = (
"USER (voice or typed text)\n"
"   |\n"
"   |-- voice --------------------------+-- typed -----------------+\n"
"   v                                   |                          |\n"
"ContinuousMicListenerThread            |                          |\n"
"  (QThread, always-listening,          |                          |\n"
"   PyAudio + WebRTC VAD, NO wake word) |                          |\n"
"   v                                   |                          |\n"
"stt_engine                             |                          |\n"
"  Faster-Whisper (primary, local)      |                          |\n"
"  Google Web Speech (fallback)         |                          |\n"
"   v                                   |                          |\n"
"transcript_processor                   |                          |\n"
"  vocabulary correction (bug: 'cloud' -> 'Claude')                 |\n"
"   v                                   |                          |\n"
"   +-----------------------------------+--------------------------+\n"
"   v\n"
"intent_router (core/voice/intent_router.py)\n"
"  - FAST PATH: local regex/keyword match -> tool_calls directly,\n"
"    ZERO LLM involvement (open_app, close window, volume, media,\n"
"    browser, screenshot ...)\n"
"  - ESCALATE -> ai_manager.ask()\n"
"   v\n"
"AIProviderManager (core/ai/manager.py)\n"
"  active provider: Groq / Gemini / OpenAI / Claude / Ollama\n"
"  in-memory, UNBOUNDED conversation history\n"
"  NO retry/backoff; single attempt, then degrade to offline regex\n"
"  brain (MockJarvisProvider, mislabeled 'Anthropic Claude' when no\n"
"  Claude key is set)\n"
"  BUG: some providers substitute the offline brain's own tool guess\n"
"  even when the REAL LLM chose not to act\n"
"   v\n"
"ToolManager.execute_tool() (core/tools/tool_manager.py)\n"
"  -> PermissionManager.check_permission()\n"
"     BROKEN: confirmation dialog is never wired up.\n"
"     Every CONFIRMATION_REQUIRED tool runs immediately.\n"
"  -> BaseTool.execute() -- REAL Windows system action:\n"
"     open/close apps, click screen, type keystrokes (SAFE, always\n"
"     ungated), press keys, browser control, run_claude_cli (can\n"
"     modify JARVIS's own source with acceptEdits), analyze_screen\n"
"     (uploads screenshot to Gemini/OpenAI, saves permanent PNG to\n"
"     Desktop, never cleaned up)\n"
"  NO TIMEOUT on generic tool execution -- a hang blocks the whole\n"
"  worker thread indefinitely.\n"
"   v\n"
"Response delivery: TTS (voice_engine.speak -> Kokoro/XTTS/\n"
"ElevenLabs/SAPI cascade) + Chat UI + Observe Mode\n"
"(core/observability/observer.py records failures -> optional\n"
"user-confirmed auto-fix via Claude CLI, core/observability/\n"
"auto_fix.py -- but reachable WITHOUT confirmation via the normal\n"
"tool-calling loop too, see Sections 5/6)\n\n"
"UI shell: QMainWindow + QStackedWidget, 12 pages, native Qt widgets\n"
"+ one QWebEngineView-hosted three.js 3D 'AI core' HUD (2 other\n"
"'AI core' implementations exist in the repo, fully wired but\n"
"dead/unreachable -- ~600 lines of unused code)"
)
code_block(diagram)

p("Entry point: main.py \u2192 splash screen \u2192 JarvisMainWindow. State: almost entirely in-process/in-memory "
  "singletons (ai_manager, tool_manager, observer, task_queue, auto_fix_manager, permission_manager) constructed "
  "once at import time. Persistent state: config.json (settings + plaintext API keys), "
  "data/learned_corrections.json (unbounded), logs/observed_issues.jsonl (append-only, unboundedly growing on disk "
  "despite an in-memory cap), logs/fix_task_queue.json (whole-file overwrite, no atomicity). No database. No "
  "network server/API of its own \u2014 it\u2019s a pure client of external LLM/vision/TTS APIs.")
p("Architectural inconsistency worth flagging: three parallel \u201cAI core\u201d visualization components exist "
  "(ai_core.py, ai_core_3d.py+QML, ai_core_web.py) with only the third wired up \u2014 this is unnecessary "
  "complexity/dead-code burden, not a functional problem.")

doc.add_page_break()

# =====================================================================
# 3. FEATURE STATUS
# =====================================================================
h1("3. Feature Status")
feature_rows = [
    ["Speech-to-text (Faster-Whisper + Google fallback)", "PARTIAL", "P2", "Both engines failing is silently indistinguishable from silence; VOICE_LANGUAGE dead for primary engine"],
    ["Wake word / trigger phrase", "NOT IMPLEMENTED", "P1", "No keyword-spotting model anywhere; ALWAYS_LISTEN=True by default"],
    ["Text-to-speech (Kokoro/XTTS/ElevenLabs/SAPI)", "PARTIAL", "P2", "Kokoro deps not in requirements.txt \u2014 broken out-of-box on fresh install"],
    ["Barge-in (interrupt JARVIS mid-reply)", "PARTIAL", "P1", "Implemented but BARGE_IN_ENABLED=False by default"],
    ["LLM tool-calling / agent loop", "PARTIAL", "P1", "Real LLM's tool decision can be silently overridden by offline regex fallback"],
    ["Permission/confirmation gate", "FAIL", "P0", "Signals never connected anywhere; default config disables it anyway"],
    ["Tool execution \u2014 desktop automation", "PARTIAL", "P1", "No confirmation, no execution timeout, type_text misclassified always-safe"],
    ["Delegated self-code-modification (run_claude_cli)", "FAIL (unsafe)", "P0", "Reachable with zero human confirmation; two concurrent runs possible"],
    ["Screen vision (analyze_screen)", "FAIL (privacy)", "P1", "Silently uploads screenshots to cloud APIs; permanent copies left on Desktop"],
    ["Observe Mode / issue tracking", "PARTIAL", "P2", "Most of 195 except blocks never report to it; on-disk log grows unboundedly"],
    ["Auto-fix / task queue dashboard", "PARTIAL", "P2", "fix_task_queue.json uses unsafe whole-file overwrite, no atomicity"],
    ["Health dashboard (UI)", "PASS", "\u2014", "Verified working in a prior session of this audit trail; read-only, low risk"],
    ["Learning/vocabulary memory", "PARTIAL", "P2", "Stores verbatim raw utterances unbounded/unencrypted; poisoning risk"],
    ["3D HUD (QWebEngineView / three.js)", "PARTIAL", "P2", "Undisclosed remote-fallback fetch; no crash-fallback if QtWebEngine fails to init"],
    ["Automation page (scheduled tasks)", "NOT IMPLEMENTED", "P2", "Entirely mock UI, hardcoded fake status, unwired buttons"],
    ["Skills page", "NOT IMPLEMENTED", "P3", "Unwired buttons, static demo content"],
    ["Multi-provider LLM switching", "PARTIAL", "P2", "Duplicate Gemini entry; stale Claude model snapshot; mislabeled mock fallback"],
    ["Settings persistence (config.json)", "PARTIAL", "P2", "Load/save failures caught with bare except: pass \u2014 silent data loss"],
    ["Concurrent/rapid requests", "UNTESTABLE (by design gaps)", "P2", "No test exercises this; code tracing shows real races"],
    ["App restart / persistence", "PARTIAL", "P2", "Config/logs persist; conversation history and confidence boosts don't reset cleanly"],
    ["Packaging / distribution (PyInstaller)", "FAIL", "P2", "Documented in README but unverified and would fail today"],
]
table_from_rows(["Feature", "Status", "Severity", "Evidence"], feature_rows, col_widths=[1.9, 1.1, 0.6, 3.0])

doc.add_page_break()

# =====================================================================
# 4. CRITICAL FINDINGS
# =====================================================================
h1("4. Critical Findings")

critical_findings = [
    ("#1 \u2014 Confirmation system is completely non-functional", "P0",
     "app/config.py:136, core/tools/permission.py:19-53, core/tools/tool_manager.py:41,98",
     "REQUIRE_CONFIRMATION_FOR_ACTIONS: bool = False by default, and the three signals meant to trigger a real "
     "approval UI (confirmation_needed, permission_denied, tool_requires_approval) have zero .connect() call sites "
     "anywhere in the repo (verified by repo-wide grep).",
     "Every PermissionLevel.CONFIRMATION_REQUIRED tool \u2014 including one that can rewrite JARVIS's own source "
     "code \u2014 executes with no human in the loop, regardless of what the docstrings claim.",
     "The confirmation UI was designed (signals exist, dialog concept documented) but never actually built/wired.",
     "Implement a real modal/toast confirmation UI connected to these signals, flip the default to True, and add a "
     "regression test asserting a CONFIRMATION_REQUIRED tool call blocks without it."),
    ("#2 \u2014 type_text misclassified as always-safe; ungated keystroke-injection primitive", "P0",
     "core/tools/system_tools.py:299-312",
     "TypeTextTool.permission_level returns PermissionLevel.SAFE. Combined with press_key (which sends Enter) "
     "having its confirmation gate broken per Finding #1, JARVIS can type arbitrary text into whatever window has "
     "focus and press Enter, completely ungated.",
     "If a terminal, browser address bar, or password field happens to have focus, this is a functional "
     "keystroke-injection/command-execution primitive triggerable by any voice command the AI decides to act on.",
     "Incorrect permission classification.",
     "Reclassify type_text as CONFIRMATION_REQUIRED at minimum; consider a stricter \u201crequires visible "
     "confirmation of destination window\u201d model."),
    ("#3 \u2014 Real LLM's tool decision can be silently overridden by an offline regex engine", "P1",
     "core/ai/gemini_provider.py:89-92, groq_provider.py:152-155, openai_provider.py:91-94, opensource_provider.py:109-113,171-175,227-231",
     "When the real cloud LLM's response contains no [ACTION:...] tag, the code asks the offline regex brain "
     "(jarvis_brain) for its own guess on the same prompt and substitutes that tool call.",
     "An action can execute that neither the human nor the actual selected AI model approved \u2014 decouples the "
     "visible AI reasoning from what actually runs.",
     "A \u201csecond opinion\u201d fallback pattern added independently across providers.",
     "Remove this override entirely, or make it an explicit, logged, lower-confidence path that still requires "
     "confirmation."),
    ("#4 \u2014 run_claude_cli reachable with zero confirmation, and can run concurrently with itself", "P1",
     "core/tools/system_tools.py:530-602, core/observability/auto_fix.py:83-97,125-126, ui/main_window.py",
     "Registered as an ordinary tool the LLM planner can call directly (Finding #1 applies), and AutoFixManager "
     "clears its \u201cpending\u201d state as soon as a fix is approved, before the worker finishes \u2014 a second "
     "issue can be approved and a second AutoFixWorker started (only a 200ms grace wait, not a real block) while "
     "the first is still running --permission-mode acceptEdits file edits against the same project directory.",
     "Two unsupervised, auto-approving Claude CLI invocations can race against each other's file edits and "
     "verification runs in the same codebase.",
     "No code-level gate enforcing the tool's own documented safety design; state cleared too early.",
     "Gate run_claude_cli behind a real, code-enforced confirmation (not just a prompt-level instruction); make "
     "AutoFixManager reject/queue a new proposal while one is in flight."),
    ("#5 \u2014 Screen content silently uploaded to cloud APIs and permanently littered on Desktop", "P1",
     "core/system/screen_analyzer.py:81-182 (cloud upload), :278-306 (Desktop write, never cleaned up)",
     "analyze_screen (permission level SAFE, always ungated) captures a full screenshot, saves it permanently to "
     "the user's visible Desktop (JARVIS_Screen_<timestamp>.png, confirmed never deleted anywhere in the codebase), "
     "and separately base64-encodes and POSTs it to Gemini and/or OpenAI with no consent prompt or disclosure.",
     "Whatever is on screen \u2014 passwords, private messages, financial data \u2014 leaves the machine and "
     "accumulates as permanent local files, with no user awareness this is happening.",
     "No consent/cleanup logic was ever added to what is effectively a cloud-vision implementation detail.",
     "Add an explicit one-time consent flow disclosing cloud upload before first use; delete the temp screenshot "
     "after the vision call completes (or use an actual OS temp directory with cleanup, not the visible Desktop)."),
    ("#6 \u2014 Fresh install cannot run", "P1",
     "requirements.txt (missing requests, kokoro_onnx, soundfile), core/ai/groq_provider.py:11, core/voice/kokoro_engine.py:17-18",
     "requests is imported unconditionally by groq_provider.py (Groq is instantiated unconditionally in manager.py:27 "
     "and is the hardcoded fallback provider) but not declared; kokoro_onnx/soundfile back the default TTS engine "
     "and are likewise undeclared.",
     "pip install -r requirements.txt && python main.py on a clean machine crashes with ModuleNotFoundError before "
     "the app can even show a window; even if requests happened to be present transitively, the default voice "
     "engine would silently do nothing.",
     "Dependency manifest not kept in sync with actual imports.",
     "Add both to requirements.txt; add a fresh-venv smoke test to whatever CI gets set up."),
    ("#7 \u2014 No wake word; always-listening is the shipped default", "P1",
     "app/config.py:55 (ALWAYS_LISTEN: bool = True), core/voice/voice_engine.py:713-855",
     "ContinuousMicListenerThread transcribes every VAD-passing utterance with no keyword-spotting gate.",
     "A real, undisclosed privacy characteristic of the default configuration \u2014 everything spoken near a "
     "running JARVIS instance gets transcribed and reasoned about.",
     "No wake-word stage was ever implemented; always-listening chosen as the default.",
     "Implement a lightweight wake-word gate (or at minimum, prominently disclose the always-listening default to "
     "the user), and make ALWAYS_LISTEN=False the shipped default."),
    ("#8 \u2014 Real UI crash: theme.RED_ALERT does not exist", "P1",
     "ui/pages/voice_page.py:483,501",
     "_on_add_dictionary_word references theme.RED_ALERT, a field that doesn't exist on the JarvisTheme dataclass "
     "(ui/styles/theme.py).",
     "Submitting the \u201cAdd Word\u201d form with a blank field, or any failed add_custom_word() call, raises an "
     "uncaught AttributeError inside the Qt slot \u2014 silently, with no visible error to the user (the form just "
     "appears to do nothing).",
     "Referenced a theme token that was never defined.",
     "Add the missing theme token or use an existing error color; add a smoke test that exercises this form's "
     "error path."),
    ("#9 \u2014 Mic disconnect leaves the UI stuck on \u201cListening...\u201d forever", "P1",
     "core/voice/voice_engine.py:644 (listening_active signal, never connected), ui/main_window.py:411-416",
     "On mic loss/permission revoke, the listener thread dies and emits a signal nothing listens to; UI state is "
     "never told the thread is gone.",
     "The app shows \u201cListening...\u201d indefinitely with a dead mic thread and no automatic recovery path "
     "\u2014 the user has no indication anything is wrong.",
     "Signal defined but never wired to a UI handler.",
     "Connect listening_active to a UI handler that shows a clear \u201cmicrophone unavailable\u201d state and "
     "offers a retry."),
    ("#10 \u2014 No timeout on generic tool execution", "P1",
     "core/tools/tool_manager.py:80-110, ui/main_window.py:112-142",
     "tool.execute(**kwargs) has no wrapping timeout; only RunClaudeCLITool has its own internal "
     "subprocess.run(timeout=180). Every other tool can hang the single-threaded ToolExecutionWorker loop "
     "indefinitely, blocking every subsequently queued tool call in that batch.",
     "A single hung tool (network call with no timeout, etc.) stalls all queued tool execution with no recovery.",
     "No uniform timeout enforcement at the ToolManager layer.",
     "Wrap tool execution in a uniform timeout (e.g., concurrent.futures with a deadline) at the ToolManager layer, "
     "independent of individual tool implementations."),
]

for title, sev, file_, problem, impact, root_cause, fix in critical_findings:
    h2(title)
    meta_p = doc.add_paragraph()
    r = meta_p.add_run(f"Severity: {sev}")
    r.bold = True
    r.font.color.rgb = sev_color(sev) or DARKBLUE
    bullet(file_, bold_prefix="File: ")
    bullet(problem, bold_prefix="Problem: ")
    bullet(impact, bold_prefix="Impact: ")
    bullet(root_cause, bold_prefix="Root cause: ")
    bullet(fix, bold_prefix="Fix: ")
    doc.add_paragraph()

doc.add_page_break()

# =====================================================================
# 5. SECURITY FINDINGS
# =====================================================================
h1("5. Security Findings")
security_rows = [
    ["CRITICAL", "app/config.py:136; core/tools/permission.py", "Confirmation gate non-functional by default and unwired", "Any tool incl. code-modifying/system-altering ones runs with zero human approval", "Build and wire the confirmation UI; default to True"],
    ["CRITICAL", "core/tools/system_tools.py:312", "type_text classified SAFE", "Ungated keystroke injection into focused window (incl. terminal)", "Reclassify CONFIRMATION_REQUIRED"],
    ["HIGH", "core/ai/gemini_provider.py:89-92 +3 others", "Offline regex brain's tool guess silently substituted for real LLM's non-action", "Unapproved actions can execute", "Remove override or gate behind explicit confirmation"],
    ["HIGH", "core/tools/system_tools.py:530-602; auto_fix.py:83-97", "run_claude_cli reachable w/o confirmation; concurrent runs possible", "Unsupervised, auto-approved edits to JARVIS's own source; race between two runs", "Code-enforced gate; reject overlapping proposals"],
    ["HIGH", "core/system/screen_analyzer.py:81-182,278-306", "Screenshot uploaded to cloud + saved permanently, no consent", "PII/privacy exposure (passwords, private data visible on screen)", "Consent prompt; delete temp file after use"],
    ["MEDIUM", "core/tools/system_tools.py:160", "OpenAppTool passes unsanitized LLM/voice-controlled string into subprocess.Popen(shell=True)", "LIKELY Windows shell-metacharacter injection (not exploit-confirmed \u2014 destructive testing intentionally not performed)", "Avoid shell=True; use os.startfile()/shell=False with explicit path"],
    ["MEDIUM", "tool_prompt.py; screen_analyzer.py:375-376", "No instruction-hierarchy language distrusting tool-result/screen content; vision output becomes spoken reply same-turn", "Indirect prompt injection via malicious on-screen text (confirmed single-turn only \u2014 not persisted into history)", "Add explicit \u201ctreat tool output as data, not instructions\u201d language to system prompt"],
    ["MEDIUM", "intent_router.py; brain.py:342-346,609-629", "Generic \u201cclose app\u201d/\u201cclose window\u201d phrases bypass known-app guard, close foreground window w/ no LLM review", "A misheard phrase can close an app with unsaved work", "Require explicit app name or LLM escalation for generic close phrases"],
    ["MEDIUM", "system_tools.py:777-873 (_resolve_youtube_direct_url)", "Naive substring check doesn't validate actual host before fetching URL", "Confirmed code defect enabling SSRF-style fetch of attacker/injection-controlled URL", "Validate parsed URL's actual host/scheme, not a substring"],
    ["MEDIUM", "core/ai/mock_provider.py:19-20", "Offline regex fallback labeled provider_name=\u201cAnthropic Claude\u201d", "Misleads user about which \u201cAI\u201d is responding when no Claude key configured", "Use an honest label, e.g. \u201cJARVIS Offline\u201d"],
    ["LOW", "system_tools.py:1095-1304", "AnalyzeScreenTool/VolumeControlTool/MediaControlTool/LockScreenTool hardcoded SAFE", "Bypass confirmation even if global gate were fixed", "Reconsider classification, at least for AnalyzeScreenTool"],
    ["LOW", "system_tools.py:248-296", "open_path executes (not just opens) any existing file via os.startfile, unrestricted to any directory", "Broader capability than the tool's description suggests", "Document/restrict scope if unintended"],
    ["INFO", "app/config.py:118-207", "API keys stored in plaintext local JSON, no OS keychain", "Local-only exposure; correctly gitignored and never committed to history (verified)", "Consider Windows DPAPI/keyring for at-rest encryption"],
    ["INFO", "core/voice/learning_memory.py", "Verbatim raw failed-utterance speech stored permanently, unencrypted, unbounded", "Local PII persistence with no user-facing delete/expire control", "Add TTL/size cap and a \u201cclear my data\u201d action"],
]
table_from_rows(["Severity", "File", "Issue", "Risk", "Recommendation"], security_rows, col_widths=[0.7, 1.6, 1.9, 1.9, 1.5])

doc.add_page_break()

# =====================================================================
# 6. AI / AGENT FINDINGS
# =====================================================================
h1("6. AI / Agent Findings")

h2("Prompt Architecture")
p("A single shared system prompt (core/ai/tool_prompt.py) is built once per call and injected identically across "
  "all five providers via build_tools_system_prompt(). It documents 18 tools with usage examples and "
  "compound-command guidance, and correctly instructs the model on Hindi/Hinglish/English handling. It has no "
  "instruction-hierarchy language separating \u201cthe user's own words\u201d from \u201ccontent observed via a "
  "tool\u201d (screen vision, file contents) \u2014 a real gap for an agent that acts autonomously on what it sees "
  "(Rule 6 explicitly tells the model to click/type based on analyze_screen output).")

h2("Tool Architecture")
p("18 tools registered through a single BaseTool ABC with three permission tiers (SAFE / CONFIRMATION_REQUIRED / "
  "BLOCKED). The abstraction itself is reasonable; the enforcement behind it is not (see Sections 4/5). Roughly a "
  "third of tools that intuitively feel state-changing or sensitive (type_text, analyze_screen, volume/media/"
  "lock-screen controls) are hardcoded SAFE regardless of the global confirmation setting.")

h2("Recommended Permission Model")
code_block(
"READ_ONLY          -> get_system_status, get_observed_issues, search_files\n"
"LOW_RISK            -> scroll_screen, control_tabs, control_volume/media (confirm-optional)\n"
"CONFIRM_REQUIRED    -> open/close app, click_screen, press_key, type_text,\n"
"                       create_folder, open_path\n"
"HIGH_RISK           -> analyze_screen (cloud upload -- explicit one-time consent,\n"
"                       then confirm-optional), run_claude_cli (ALWAYS confirm,\n"
"                       no exceptions, even from fast-path or provider fallback)\n"
"BLOCKED             -> (already exists conceptually; currently no tool uses it)"
)
p("The critical missing piece is not the taxonomy \u2014 it's that none of it is actually enforced today because "
  "the UI-side confirmation dialog was never built.")

h2("Memory Architecture")
p("Two independent, unconnected memory stores: (1) ai_manager._history \u2014 in-memory only, unbounded, lost on "
  "restart, sliced to the last 6-10 messages per provider call (so no runaway token cost, but genuine unbounded "
  "memory growth over a long session); (2) core/voice/learning_memory.py \u2014 persistent, unbounded, "
  "unencrypted, and critically capable of forcing a fuzzy-matched future utterance's confidence to \u22650.85, "
  "which lets a single bad learned correction bypass the normal fast-path confidence gating indefinitely (a "
  "genuine memory-poisoning-to-direct-tool-execution path, confirmed in code, no correction mechanism except "
  "manually editing the JSON file). No vector/embedding store exists anywhere.")

h2("Prompt Injection Risks")
p("Real but narrow and currently single-turn \u2014 confirmed that analyze_screen's vision-model output is never "
  "written back into ai_manager._history, so a malicious on-screen payload can influence the current spoken reply "
  "but doesn't (today) poison future turns via the AI layer's own memory. It could still influence a later turn "
  "indirectly if the user reacts to what JARVIS says. This is unmitigated at the prompt level (no defensive "
  "instruction exists) even though the blast radius happens to be limited by current architecture, not by design.")

h2("Autonomous-Action Risks")
p("The single most important recommendation in this entire audit \u2014 run_claude_cli must be made impossible to "
  "reach without an explicit, code-enforced, per-invocation human confirmation, independent of the general "
  "permission system, because it is the one tool that can rewrite the application's own source. Everything else "
  "in the tool catalog is bounded to the current session/machine state; this one is not.")

doc.add_page_break()

# =====================================================================
# 7. VOICE FINDINGS
# =====================================================================
h1("7. Voice Findings")
bullet("STT: Faster-Whisper (local, primary) + Google (cloud fallback) \u2014 solid design, hardcoded to "
       "language=\"hi\" (making VOICE_LANGUAGE config dead for the primary path), and both-engines-failing "
       "degrades silently to \u201cuser said nothing\u201d with zero diagnostic signal.")
bullet("Wake word: does not exist. Always-listening (ALWAYS_LISTEN=True default) + VAD + STT is the entire "
       "gating mechanism.")
bullet("TTS: Kokoro ONNX (primary, streaming-first architecture, genuinely reduces time-to-first-audio), with "
       "XTTS/ElevenLabs/SAPI as reachable-but-untested fallbacks. Barge-in exists but is off by default; a stuck "
       "TTS worker recovers only via a 45-second watchdog.")
bullet("Latency: cold start pays roughly Whisper-load (~11-13s) + Kokoro-load (~1-3s) sequentially on one thread "
       "rather than in parallel, costing several extra seconds every cold start for no functional reason. "
       "(Per-utterance pipeline latency telemetry was independently audited and fixed earlier in this engagement "
       "\u2014 the fix confirmed working.)")
bullet("Audio lifecycle: output streams are consistently closed in finally blocks (good pattern). Mic thread "
       "stop()'s 1.5s join can be shorter than an in-flight 15-second phrase capture, meaning shutdown can proceed "
       "before the thread/PyAudio stream is actually gone.")
bullet("Reliability: mic disconnect/permission loss leaves the UI stuck showing \u201cListening...\u201d forever "
       "with no recovery path (see Finding #9).")
bullet("Correctness bug: the vocabulary-correction dictionary maps \u201ccloud\u201d \u2192 \u201cClaude\u201d "
       "unconditionally, silently mangling any genuine sentence containing the common English word \u201ccloud."
       "\u201d")
bullet("Privacy: transcript fragments (truncated) are logged to disk by default (DEBUG_PIPELINE_LOGGING=True), "
       "and learning_memory.py persists verbatim raw failed utterances permanently and unencrypted.")

doc.add_page_break()

# =====================================================================
# 8. PERFORMANCE FINDINGS
# =====================================================================
h1("8. Performance Findings")
perf_rows = [
    ["P1", "No wake word means continuous STT processing of everything the mic hears \u2014 sustained CPU cost with no idle state"],
    ["P1", "No timeout on generic tool execution \u2014 a hung tool can stall the entire tool queue indefinitely"],
    ["P2", "Kokoro + Faster-Whisper models load sequentially at startup instead of in parallel \u2014 costs several extra seconds of cold-start latency"],
    ["P2", "Multiple UI pages (apps_page.py, browser_page.py, control_page.py) call tool execution synchronously on the GUI thread, freezing the whole window"],
    ["P2", "Up to ~18s blocking network calls on the GUI thread for Ollama/ElevenLabs connection tests"],
    ["P2", "analyze_screen's cloud vision call chain can take up to ~30s worst-case (sequential Gemini retry + OpenAI fallback, both with 10s timeouts)"],
    ["P3", "ai_manager._history grows unbounded in memory over a long session (bounded per-call token cost via slicing, but real memory growth)"],
    ["P3", "logs/observed_issues.jsonl grows unboundedly on disk despite a docstring claiming a size cap \u2014 the cap only applies to what's reloaded into memory"],
    ["P4", "core/tools/system_tools.py at 1,305 lines holding ~20 tool classes is a maintainability, not performance, concern worth noting since it's central to the hot path"],
]
table_from_rows(["Priority", "Finding"], perf_rows, col_widths=[0.8, 5.7])
p("No premature-optimization recommendations are made \u2014 none of the above are proposals to micro-optimize "
  "working code; all are either genuine blocking-call bugs or measured/reasoned bottlenecks with concrete "
  "evidence.")

doc.add_page_break()

# =====================================================================
# 9. RELIABILITY FINDINGS
# =====================================================================
h1("9. Reliability Findings")
h2("Crash Scenarios (Confirmed)")
bullet("theme.RED_ALERT AttributeError crashes the dictionary-word form's error path silently (Finding #8).")
bullet("A missing dependency crashes the entire app on fresh install (Finding #6).")

h2("Recovery Gaps")
bullet("Mic disconnect (stuck \u201cListening...\u201d forever, Finding #9).")
bullet("Both-STT-engines-failing (silent, indistinguishable from silence).")
bullet("LLM API failure (generic misleading fallback message that never tells the user something actually "
       "failed \u2014 no retry/backoff at any provider layer except Groq's own model-fallback, which isn't a "
       "true retry).")

h2("Race Conditions")
bullet("AutoFixManager allows two concurrent Claude-CLI self-modification runs against the same project "
       "directory (Finding #4).")
bullet("observer.py/task_queue.py's _next_id counters use a non-atomic read-modify-write from potentially "
       "concurrent QThreads \u2014 can produce duplicate record IDs.")
bullet("task_queue.json is overwritten whole-file on every single status change with no atomic write (no "
       "temp+rename) and no lock \u2014 a crash mid-write leaves invalid JSON, and the entire task history is "
       "silently discarded on next load (caught by a bare except Exception: print(...), not even surfaced to the "
       "observer).")

h2("Corrupted State Paths")
p("app/config.py's load_from_json/save_to_json catch Exception: pass with no print at all \u2014 a corrupt "
  "config.json or a disk-full/permission error on save silently discards the user's settings changes with zero "
  "surfacing anywhere in the app.")

h2("Silent Failure Swallowing")
p("195 except Exception blocks repo-wide, ~65 of them bare except Exception: pass. No logging module usage "
  "anywhere except core/telemetry.py \u2014 349 print() calls are the de facto error-reporting mechanism, "
  "invisible once the app runs without an attached console.")

h2("Duplicate Actions")
p("Not directly observed, but the concurrent-AutoFixWorker finding (Finding #4) is exactly this failure class "
  "applied to code-modifying actions.")

doc.add_page_break()

# =====================================================================
# 10. TESTING GAPS
# =====================================================================
h1("10. Testing Gaps")
testing_rows = [
    ["Core assistant flow", "Superficial (imports work, tool call parsed, UI pages instantiate)", "Result-value correctness (does screenshot tool write a valid file, does close_application kill the right PID)", "P1"],
    ["Permission/confirmation enforcement", "None", "Assert a CONFIRMATION_REQUIRED tool is blocked without approval; assert confirmation UI fires", "P1"],
    ["Tool execution \u2014 file/system ops", "One SAFE, read-only tool tested (get_system_status)", "Every CONFIRMATION_REQUIRED/state-changing tool untested", "P1"],
    ["API failure handling (per provider)", "None", "Timeout, 401, 429, empty body, malformed JSON for each of Groq/Gemini/OpenAI/Claude/Ollama", "P1"],
    ["Concurrency", "None", "Rapid/overlapping prompts, dual AutoFixWorkers, concurrent observer/task_queue writes", "P2"],
    ["Config load/save round-trip", "None", "Every persisted field survives reload; corrupt-file recovery behavior", "P2"],
    ["Memory/observability persistence", "None", "observer.py/task_queue.py/learning_memory.py \u2014 nothing exercises these", "P2"],
    ["Voice engine failure cascades", "Manual/visual scripts only, not in real suite", "STT fallback chain, TTS engine cascade, mic-disconnect recovery", "P2"],
    ["Security boundaries", "None", "Shell-injection surface in OpenAppTool; SSRF substring bug; prompt-injection resistance", "P2"],
    ["Fresh-install smoke test", "None", "Would have caught the missing requests/kokoro_onnx dependency issue immediately", "P3"],
]
table_from_rows(["Area", "Current Coverage", "Missing Tests", "Priority"], testing_rows, col_widths=[1.4, 1.8, 2.7, 0.6])

p("tests/ directory reality: of ~74 files, only 1 (test_components.py) is a real, if narrow, regression suite. ~8 "
  "more have genuine assertions but probe single narrow behaviors. ~65 files are one-off 3D-face-model tuning "
  "scripts or manual/visual verification tools that write PNGs for a human to eyeball \u2014 these do not belong "
  "in a production tests/ directory and should move to a dev_scripts/ or tools/hud_tuning/ location, with a real "
  "pytest-based suite (currently: no pytest, mypy, ruff, flake8, or pylint installed anywhere in the environment) "
  "taking their place.")

doc.add_page_break()

# =====================================================================
# 11. TECHNICAL DEBT
# =====================================================================
h1("11. Technical Debt")

h2("Must Fix (blocks safe/functional operation)")
for item in [
    "Missing requests/kokoro_onnx/soundfile in requirements.txt (app doesn't run fresh)",
    "Non-functional confirmation gate (Finding #1)",
    "type_text misclassified as SAFE (Finding #2)",
    "run_claude_cli reachable without confirmation + concurrent-run race (Finding #4)",
    "theme.RED_ALERT crash (Finding #8)",
    "Screenshot cloud-upload with no consent (Finding #5)",
]:
    bullet(item)

h2("Should Fix (real risk, not yet catastrophic)")
for item in [
    "Cross-provider tool-decision override by offline regex brain",
    "SSRF-adjacent substring-check bug in YouTube URL resolver",
    "OpenAppTool's shell=True with unsanitized input",
    "No timeout on generic tool execution",
    "task_queue.json unsafe whole-file overwrite",
    "Mic-disconnect stuck-UI, no wake word, barge-in off by default",
    "warm_up/warmup typo silently disabling LLM pre-warm",
    "Multiple GUI-thread-blocking tool/network calls in UI pages",
    "learning_memory.py unbounded, unencrypted, poisoning-capable store",
]:
    bullet(item)

h2("Nice to Fix")
for item in [
    "~600 lines of dead \u201cAI core\u201d visualization code",
    "README accuracy (materially out of date on architecture)",
    "319MB dangling git blob (confirmed never pushed, safe to git gc)",
    "Automation/Skills pages being non-functional mockups",
    "Consolidating tests/ into real tests vs. dev scripts",
    "Splitting system_tools.py (1,305 lines, ~20 classes) into submodules",
    "Structured logging (logging module) instead of 349 scattered print() calls",
    "Duplicated card-styling CSS across ~8 UI pages instead of centralized theme classes",
]:
    bullet(item)

doc.add_page_break()

# =====================================================================
# 12. RECOMMENDED ARCHITECTURE
# =====================================================================
h1("12. Recommended Architecture")
p("The current architecture (native Qt UI \u2192 intent router with LLM fast-path escape hatch \u2192 tool "
  "manager \u2192 permission check \u2192 real system action \u2192 observability layer) is fundamentally sound "
  "and does not need a rewrite. The problems are almost entirely in enforcement, not design:")
numbered("Build the confirmation UI that was designed but never wired. The signals (confirmation_needed, "
         "permission_denied) already exist with the right shape \u2014 connect them to an actual modal/toast, "
         "default REQUIRE_CONFIRMATION_FOR_ACTIONS=True, and add a dedicated, code-enforced (not prompt-level) "
         "gate specifically for run_claude_cli that cannot be bypassed by any fallback path (fast-path router, "
         "offline-brain override, or provider substitution).")
numbered("Centralize tool-execution safety at the ToolManager layer: a uniform timeout wrapper, and a single "
         "source of truth for which permission tier each tool belongs to (audit the current SAFE "
         "classifications, several look wrong on inspection).")
numbered("Add a wake-word gate as a first-class pipeline stage before STT, off the always-on VAD path, or at "
         "minimum make ALWAYS_LISTEN=False the shipped default with wake-word/always-listening as an explicit "
         "opt-in.")
numbered("Consolidate to one \u201cAI core\u201d visualization and delete the other two.")
numbered("Fix the dependency manifest and add a fresh-venv CI smoke test so this class of \u201cdoesn't even "
         "start\u201d bug can't recur silently.")
numbered("Everything else (STT/TTS engine abstraction, telemetry, observability/auto-fix concept, "
         "intent-router fast-path design) is worth keeping as-is.")

doc.add_page_break()

# =====================================================================
# 20. PRIORITIZED FIX ROADMAP
# =====================================================================
h1("20. Prioritized Fix Roadmap")

def roadmap_table(rows, col_widths=(1.5, 0.55, 1.5, 0.85, 1.85, 0.85)):
    table_from_rows(["Task", "Priority", "File(s)", "Complexity", "Why it matters", "Dependencies"], rows, col_widths=list(col_widths))

h2("Phase 1 \u2014 Emergency Fixes")
roadmap_table([
    ["Add requests, kokoro_onnx, soundfile to requirements.txt", "P0", "requirements.txt", "Trivial", "App doesn't run fresh", "None"],
    ["Wire real confirmation UI to permission signals; default REQUIRE_CONFIRMATION_FOR_ACTIONS=True", "P0", "core/tools/permission.py; app/config.py; new dialog in ui/", "Medium", "Root cause of most security findings", "None"],
    ["Reclassify type_text as CONFIRMATION_REQUIRED", "P0", "core/tools/system_tools.py:312", "Trivial", "Closes ungated-keystroke-injection primitive", "Confirmation UI"],
    ["Code-enforce confirmation specifically for run_claude_cli; reject overlapping fix proposals", "P0", "system_tools.py; auto_fix.py", "Medium", "Only tool that can rewrite the app's own source", "Confirmation UI"],
    ["Fix theme.RED_ALERT crash", "P0", "ui/pages/voice_page.py:483,501; ui/styles/theme.py", "Trivial", "Live crash bug", "None"],
    ["Add consent disclosure + delete-after-use for analyze_screen screenshots", "P0", "core/system/screen_analyzer.py:81-182,278-306", "Small", "Undisclosed PII exfiltration to cloud APIs", "None"],
])

h2("Phase 2 \u2014 Stability")
roadmap_table([
    ["Remove cross-provider offline-brain tool-decision override", "P1", "core/ai/*_provider.py", "Small", "Unapproved actions can currently execute", "None"],
    ["Add uniform tool-execution timeout", "P1", "core/tools/tool_manager.py", "Medium", "Hung tool blocks entire queue forever", "None"],
    ["Fix _resolve_youtube_direct_url host validation", "P1", "system_tools.py:777-873", "Small", "SSRF-adjacent confirmed defect", "None"],
    ["Replace shell=True unsanitized subprocess in OpenAppTool", "P1", "system_tools.py:160", "Small", "Likely shell-injection risk", "None"],
    ["Atomic write for task_queue.json; surface load failures to observer", "P2", "core/observability/task_queue.py", "Small", "Silent task-history loss on crash", "None"],
    ["Surface config.json load/save failures (stop bare except: pass)", "P2", "app/config.py:164,201", "Trivial", "Silent settings loss", "None"],
    ["Fix listening_active signal wiring for mic-loss recovery", "P2", "voice_engine.py:644; main_window.py", "Small", "Stuck \u201cListening...\u201d UI forever", "None"],
    ["Real test suite for permission enforcement, tool results, API failures", "P2", "new tests/", "Large", "Zero coverage of anything security/reliability-critical today", "Phase 1"],
])

h2("Phase 3 \u2014 Architecture")
roadmap_table([
    ["Delete unused ai_core.py/ai_core_3d.py/QML", "P2", "ui/components/; ui/qml/", "Small", "~600 lines dead code", "None"],
    ["Split system_tools.py into per-domain submodules", "P3", "core/tools/system_tools.py", "Medium", "1,305-line file in the security-critical hot path", "None"],
    ["Move ~65 dev/tuning scripts out of tests/", "P3", "tests/ \u2192 new dev_scripts/", "Small", "Test-directory hygiene", "None"],
    ["Fix warm_up/warmup attribute typo", "P2", "splash_screen.py:51", "Trivial", "Silently disables documented LLM pre-warm", "None"],
    ["Re-audit and correct PermissionLevel.SAFE classifications", "P2", "system_tools.py", "Small", "Several look wrong on inspection", "Confirmation UI"],
])

h2("Phase 4 \u2014 Performance")
roadmap_table([
    ["Parallelize Kokoro + Faster-Whisper cold-start loading", "P2", "splash_screen.py", "Small", "Several seconds of avoidable cold-start latency", "None"],
    ["Move apps_page/browser_page/control_page tool calls off the GUI thread", "P1", "those files", "Medium", "Whole-window freezes today", "None"],
    ["Move Ollama/ElevenLabs connection tests off the GUI thread", "P2", "settings_page.py; voice_page.py", "Small", "Up to 18s UI freeze", "None"],
    ["Bound ai_manager._history growth", "P3", "core/ai/manager.py", "Small", "Unbounded in-memory growth over long sessions", "None"],
])

h2("Phase 5 \u2014 UX")
roadmap_table([
    ["Add wake word or make ALWAYS_LISTEN=False default", "P1", "core/voice/; app/config.py", "Medium-Large", "Undisclosed always-listening privacy characteristic", "None"],
    ["Enable barge-in by default", "P2", "app/config.py:84", "Trivial", "Can't interrupt JARVIS out of the box today", "None"],
    ["Fix \u201ccloud\u201d\u2192\u201cClaude\u201d vocabulary correction", "P2", "transcript_processor.py:32", "Trivial", "Mangles real speech containing \u201ccloud\u201d", "None"],
    ["Replace misleading generic LLM-failure fallback message", "P2", "ui/main_window.py:208-214", "Small", "Currently masks real failures as normal", "None"],
    ["Wire up or remove non-functional Automation/Skills pages", "P2", "automation_page.py; skills_page.py", "Medium", "Currently misleading mockups", "None"],
    ["Relabel offline-brain fallback honestly", "P3", "core/ai/mock_provider.py:19-20", "Trivial", "User-facing deception about which AI is responding", "None"],
])

h2("Phase 6 \u2014 Production Hardening")
roadmap_table([
    ["Introduce real logging module, retire ad hoc print()", "P2", "repo-wide", "Large", "349 print() calls, no log levels/filtering in production", "None"],
    ["Set up CI with fresh-venv install + test_components.py", "P2", "new .github/workflows/", "Medium", "Would have caught missing-dependency bug automatically", "Phase 1"],
    ["Update README to match actual architecture", "P2", "README.md", "Medium", "Currently claims \u201cno web views,\u201d omits most real features", "None"],
    ["git gc to reclaim the 319MB dangling blob", "P4", "repo", "Trivial", "Local disk bloat (relevant given critical low-disk-space situation)", "None"],
    ["Add API-key-at-rest encryption (DPAPI/keyring)", "P3", "app/config.py", "Medium", "Plaintext local secret storage", "None"],
    ["Add TTL/size cap + user-facing delete for learning_memory.json", "P2", "core/voice/learning_memory.py", "Small", "Unbounded raw-speech PII persistence", "None"],
])

doc.add_page_break()

# =====================================================================
# TOP 10
# =====================================================================
h1("Top 10 Things to Fix")

top10 = [
    ("#1 \u2014 The permission/confirmation system is completely fake", "P0 / CRITICAL",
     "app/config.py:136, core/tools/permission.py:19-53",
     "Confirmation UI signals were designed but never connected to any handler; default config disables the check anyway",
     "Every \u201crequires confirmation\u201d tool, including one that rewrites the app's own source code, runs with zero human approval",
     "Build and wire a real confirmation dialog to confirmation_needed/permission_denied; flip REQUIRE_CONFIRMATION_FOR_ACTIONS to True",
     "It is the root cause underlying nearly every other security finding in this audit \u2014 fixing it alone eliminates most of the CRITICAL/HIGH severity items"),
    ("#2 \u2014 type_text is an ungated keystroke-injection primitive", "P0",
     "core/tools/system_tools.py:312",
     "Misclassified as PermissionLevel.SAFE",
     "Combined with #1, JARVIS can type and submit arbitrary text into whatever window has focus, including a terminal",
     "Reclassify CONFIRMATION_REQUIRED",
     "It's the single most direct path from \u201cAI decided to act\u201d to \u201carbitrary input reaches a potentially privileged surface\u201d"),
    ("#3 \u2014 Fresh install cannot run", "P1",
     "requirements.txt, core/ai/groq_provider.py:11, core/voice/kokoro_engine.py:17-18",
     "requests, kokoro_onnx, soundfile used in code but never declared as dependencies",
     "The app crashes on any clean pip install \u2014 it isn't a \u201chardening\u201d gap, it's non-functional out of the box",
     "Add the three packages to requirements.txt; add a CI smoke test in a fresh venv",
     "Nothing else in this report matters if the app can't start"),
    ("#4 \u2014 The AI's tool decision can be silently overridden by an unrelated regex engine", "P1",
     "core/ai/gemini_provider.py:89-92, groq_provider.py:152-155, openai_provider.py:91-94, opensource_provider.py",
     "A \u201csecond opinion\u201d fallback that substitutes the offline brain's tool guess when the real LLM chose not to act",
     "Actions can execute that neither the human nor the selected AI model approved",
     "Remove the override, or make it an explicit lower-confidence path requiring confirmation",
     "It breaks the basic trust assumption that \u201cthe AI you picked is the AI deciding what happens\u201d"),
    ("#5 \u2014 run_claude_cli can modify JARVIS's own source with no confirmation, and can race itself", "P1",
     "core/tools/system_tools.py:530-602, core/observability/auto_fix.py:83-97,125-126",
     "Reachable through the normal tool-calling loop (contradicting its own documented safety design); pending-state cleared before the worker actually finishes",
     "Unsupervised, auto-approved file edits to the app's own codebase, potentially two at once",
     "Dedicated, code-enforced confirmation specific to this tool; reject a second proposal while one is in flight",
     "It's the one tool with the power to change everything else in this list"),
    ("#6 \u2014 Screenshots are silently uploaded to the cloud and left permanently on the Desktop", "P1",
     "core/system/screen_analyzer.py:81-182,278-306",
     "No consent flow, no cleanup of the saved PNG",
     "Real PII exfiltration risk and permanent local data accumulation",
     "Add explicit consent disclosure; delete the temp screenshot after the vision call",
     "The clearest, most concrete privacy violation found \u2014 and the default, ungated behavior of a SAFE-classified tool"),
    ("#7 \u2014 No wake word; always-listening by default", "P1",
     "app/config.py:55, core/voice/voice_engine.py:713-855",
     "No keyword-spotting stage exists; ALWAYS_LISTEN=True is the shipped default",
     "Undisclosed continuous transcription of everything near the microphone",
     "Add a wake-word gate, or default to ALWAYS_LISTEN=False with clear opt-in messaging",
     "Privacy characteristic that materially affects every user of this software, not just an edge case"),
    ("#8 \u2014 Live crash bug in the voice dictionary UI", "P1",
     "ui/pages/voice_page.py:483,501",
     "References a nonexistent theme.RED_ALERT field",
     "AttributeError on a routine form submission, silently",
     "Add the missing theme token",
     "A guaranteed, reproducible crash in a user-facing feature, trivial to fix, currently live"),
    ("#9 \u2014 Mic disconnect leaves the UI permanently stuck", "P1",
     "core/voice/voice_engine.py:644, ui/main_window.py:411-416",
     "listening_active signal is emitted but never connected",
     "No automatic recovery or user-facing indication when the microphone becomes unavailable",
     "Connect the signal to a UI handler with a clear \u201cmic unavailable, retry\u201d state",
     "Turns a routine hardware hiccup into an apparently-frozen application"),
    ("#10 \u2014 Zero meaningful test coverage of anything security- or reliability-critical", "P1",
     "tests/ (74 files, 1 real regression suite)",
     "No permission, tool-result, API-failure, or concurrency tests exist anywhere; ~65 files are unrelated dev-tuning scripts",
     "Every finding in this report could have shipped silently and would ship again the same way tomorrow",
     "Build a real pytest-based suite targeting permission enforcement, tool execution results, and provider failure handling; wire it into CI",
     "It's the structural reason the other nine items exist uncaught"),
]

for title, sev, file_, root_cause, impact, fix, why in top10:
    h2(title)
    meta_p = doc.add_paragraph()
    r = meta_p.add_run(f"Severity: {sev}")
    r.bold = True
    r.font.color.rgb = sev_color(sev) or DARKBLUE
    bullet(file_, bold_prefix="File: ")
    bullet(root_cause, bold_prefix="Root cause: ")
    bullet(impact, bold_prefix="Impact: ")
    bullet(fix, bold_prefix="Exact fix: ")
    bullet(why, bold_prefix="Why this comes first: ")
    doc.add_paragraph()

doc.add_page_break()

# =====================================================================
# OVERALL VERDICT
# =====================================================================
h1("Overall Verdict")
verdict_p = doc.add_paragraph()
vr = verdict_p.add_run("\U0001F534 Not Safe / Not Production Ready")
vr.bold = True
vr.font.size = Pt(20)
vr.font.color.rgb = RED

numbered("The app does not run on a clean install \u2014 a blocking, unconditional failure, not a hardening gap.")
numbered("The permission/confirmation system that every safety claim in the codebase's own comments depends on "
         "does not exist at runtime \u2014 it's designed but never wired.")
numbered("There is at least one live, reproducible crash bug in a routine user-facing form.")
numbered("JARVIS uploads live screen content to third-party cloud APIs with no consent and permanently litters "
         "the Desktop with screenshots as a side effect of a \u201csafe\u201d tool.")
numbered("The AI decision layer can be silently overridden by an unrelated offline engine, breaking the basic "
         "guarantee that the chosen model is what decides what happens.")
numbered("The one tool capable of modifying the application's own source code is reachable with zero "
         "confirmation and can run concurrently with itself.")
numbered("No wake word \u2014 always-listening is the shipped default, an undisclosed privacy characteristic.")
numbered("Test coverage of every security- and reliability-critical path is effectively zero.")
numbered("That said \u2014 the underlying engineering in the areas that do work (STT/TTS pipeline design, "
         "generation-tracking for stale async state, the observability/telemetry layer, the overall Qt "
         "architecture) shows real skill and is worth preserving; this is a fixable, not a \u201cstart over,"
         "\u201d situation.")
numbered("None of the fixes required are architecturally invasive \u2014 nearly everything in the roadmap above "
         "is \u201cconnect a signal that already exists,\u201d \u201creclassify a permission level,\u201d "
         "\u201cadd a missing dependency line,\u201d or \u201cadd a confirmation check\u201d \u2014 a focused "
         "Phase 1 pass would move this from Not Safe to Needs Hardening in a realistic, bounded effort.")

out_path = r"C:\Users\pramo\Desktop\jarvis\JARVIS_Production_Audit_Report.docx"
doc.save(out_path)
print(f"Saved: {out_path}")
