# JARVIS — Personal AI Desktop Assistant

A Windows desktop AI assistant built with **Python 3.12+** and **PySide6 (Qt for Python)**. It listens by voice (or accepts typed input), routes commands through a local fast-path matcher or a cloud/local LLM, and can act on your desktop — launching apps, controlling windows, browsing, and answering questions about what's on screen — behind an explicit, code-enforced human-confirmation gate.

This README describes what the app **actually does today**, not an aspirational roadmap. If a capability below isn't listed, it isn't implemented yet.

---

## Architecture

```
USER (voice or typed text)
   │
   ├─ voice ──► ContinuousMicListenerThread (PyAudio + WebRTC VAD)
   │              │  no wake word — see "Voice & privacy" below
   │              ▼
   │            stt_engine (Faster-Whisper local, primary; Google cloud, fallback)
   │              ▼
   ├─ typed ──► transcript_processor (vocabulary correction)
   │              ▼
   │            intent_router
   │              ├─ FAST PATH: local regex/keyword match → tool call directly
   │              └─ ESCALATE → ai_manager (Groq / Gemini / OpenAI / Claude / local Ollama)
   │                              — offline regex fallback ONLY on missing key or API failure,
   │                                and it is honestly labeled as such, never silently
   │                                substituted for a real model's own decision
   ▼
ToolManager.execute_tool()
   ├─ PermissionManager.check_permission() — the ONE enforcement point
   │     READ_ONLY / LOW_RISK           → runs immediately
   │     CONFIRMATION_REQUIRED / HIGH_RISK → blocks on a real modal dialog
   │                                          (ConfirmationService); denied by
   │                                          default if no UI is listening
   ▼
BaseTool.execute() — real Windows action (bounded by a per-tool timeout)
   ▼
Response delivery: TTS (Kokoro / XTTS / ElevenLabs / SAPI) + chat UI + Observe Mode
   (failures are recorded; a proposed fix always requires a second, explicit,
    code-enforced confirmation before core/tools/system_tools.py's
    run_claude_cli can modify this project's own source)
```

UI shell: `QMainWindow` + `QStackedWidget` with 12 pages, built from native Qt widgets. One page (the animated "AI core" on the Home page) is a `QWebEngineView` rendering a local three.js scene — this **is** a Chromium-based web view embedded in the app, not a pure-native-only UI.

---

## Key Features

- **Voice input**: Faster-Whisper (local, offline, primary) with Google Web Speech API as a cloud fallback. Hindi/Hinglish/English mixed speech supported.
- **No wake word**: there is no keyword-spotting stage. Listening is **off by default** (`ALWAYS_LISTEN=False`) — see [Voice & privacy](#voice--privacy) below before turning it on.
- **Text-to-speech**: Kokoro ONNX (local, default), with XTTS-v2, ElevenLabs, and Windows SAPI as selectable alternates in Settings.
- **Multi-provider LLM routing**: Groq, Google Gemini, OpenAI, Anthropic Claude, or a local Ollama model — switchable in Settings, with a deterministic offline fallback (honestly labeled "JARVIS Offline") if no key is configured or a call fails.
- **Local fast-path intent matching**: common commands (open/close an app, browser/tab control, volume, media, system status, screenshots) are recognized locally with zero network round-trip; only genuinely unclear requests escalate to an LLM.
- **Desktop automation tools**: launch/close applications, open files/folders, type text, press keys, click/scroll the screen, browser navigation and tab control, volume/media control, lock the workstation, and analyze what's on screen.
- **Real permission/confirmation gate**: every state-changing tool call is classified into one of five tiers (`READ_ONLY`, `LOW_RISK`, `CONFIRMATION_REQUIRED`, `HIGH_RISK`, `BLOCKED`) and anything above `LOW_RISK` blocks on an actual modal approval dialog before it runs — see [Permissions & confirmation](#permissions--confirmation).
- **Self-modifying code delegation**: `run_claude_cli` can hand a coding task to the Claude Code CLI, which can edit this project's own source. This is the single most sensitive capability in the app and has its own dedicated, unbypassable confirmation gate independent of everything else (see below).
- **Observe Mode**: runtime errors, failed tool calls, and voice failures are recorded (`core/observability/observer.py`) and explainable on request ("what problem did you observe"), with an optional, always-confirmed path to ask Claude to fix it.
- **Project Health dashboard**: a sidebar page showing STT/TTS status, Claude CLI reachability, the current/last fix task, and recent observed issues.

---

## Voice & privacy

There is **no wake-word/keyword-spotting model** in this app. If always-listening is turned on, the microphone is transcribed and reasoned about continuously the entire time JARVIS is running — not just after a trigger phrase.

Because of that:

- `ALWAYS_LISTEN` **defaults to `False`**. You opt in from **Settings → Privacy**, where this is disclosed in the toggle's own label.
- Pipeline debug logging (`DEBUG_PIPELINE_LOGGING`, on by default) writes truncated (~40–60 char) transcript fragments to `logs/jarvis_debug.log` for troubleshooting. This stays local and is never transmitted anywhere.
- `core/voice/learning_memory.py` locally remembers phrasings JARVIS previously misunderstood, to recognize them faster next time. It's bounded (`LEARNING_MEMORY_MAX_ENTRIES`), expires automatically (`LEARNING_MEMORY_TTL_DAYS`, default 90 days), and can be wiped at any time from **Settings → Privacy → Clear Learned Data**. A learned correction can only ever affect local routing confidence — it can never skip the confirmation gate below.
- Mic disconnect / OS permission revocation is detected and surfaced in the UI as "Microphone unavailable" with a one-click retry (clicking the mic button), instead of silently freezing on "Listening...".

### Screen analysis (`analyze_screen`)

Answering "what's on my screen" captures a screenshot. The screenshot itself is written to the OS temp directory (never your visible Desktop) and deleted immediately after use.

If the local window-title heuristic isn't enough to answer the question, the screenshot is uploaded to a cloud vision provider (Gemini or OpenAI). **This requires your explicit, one-time consent** — the first call shows a dialog disclosing the upload before it happens. Your answer is remembered (`SCREEN_ANALYSIS_CLOUD_CONSENT` in `config.json`) and revocable at any time from **Settings → Privacy**. Declining keeps screen analysis fully local (no pixels ever leave the machine) and it still answers from window-title heuristics.

---

## Permissions & confirmation

Every tool has one of five permission tiers (`core/tools/base.py`):

| Tier | Examples | Behavior |
|---|---|---|
| `READ_ONLY` | `get_system_status`, `search_files` | Always runs immediately |
| `LOW_RISK` | `scroll_screen`, `control_tabs`, `control_volume`, `open_browser` | Always runs immediately |
| `CONFIRMATION_REQUIRED` | `open_application`, `close_application`, `type_text`, `press_key`, `click_screen`, `create_folder`, `open_path`, `lock_screen` | Blocks on a real modal Allow/Deny dialog |
| `HIGH_RISK` | `analyze_screen` (cloud upload path), `run_claude_cli` | Always confirmed, never auto-allow-listed, elevated dialog styling |
| `BLOCKED` | (reserved) | Never executes |

This is enforced in **one place**, `core/tools/permission.py`, which every caller passes through — the normal LLM tool-calling loop, the local fast-path router, and any UI button. A tool call with no confirmation UI connected (e.g. a headless script) is **denied by default**, never silently approved.

`run_claude_cli` gets a second, independent hard-wall inside its own `execute()` method (`core/tools/system_tools.py`) — it calls the confirmation gate itself, unconditionally, regardless of how it was reached, and only one such job may run at a time (a second concurrent attempt is rejected outright). This means it stays gated even against a caller that bypasses `ToolManager` entirely (as `core/observability/auto_fix.py`'s own confirmed flow does — it now routes through the exact same tool call, so a Claude CLI run triggered by an accepted auto-fix proposal shows a second, explicit dialog with the literal task text before anything executes).

---

## API keys & secrets

API keys (Groq, Gemini, OpenAI, Anthropic, ElevenLabs) live in `config.json` at the project root, in **plaintext**. This file is git-ignored and has never been committed. It is not encrypted at rest — anyone with filesystem access to this machine (or a backup/sync tool pointed at this folder) can read it. `config.example.json` is a safe, secret-free template for a fresh setup.

---

## Getting Started

### 1. Prerequisites

- Windows 10 / 11 (64-bit)
- Python 3.12+ on your `PATH`

### 2. Installation

```powershell
cd C:\Users\pramo\Desktop\jarvis
pip install -r requirements.txt
```

`requirements.txt` covers every import the app actually needs at runtime for its default configuration (Faster-Whisper STT, Kokoro TTS, Groq as the default LLM). XTTS-v2 (`coqui-tts`, ~3GB) is commented out and optional — only needed if you switch `TTS_ENGINE` to `"xtts"` in Settings.

### 3. First run

```powershell
python main.py
```

On first launch you'll be asked (once) whether to consent to cloud screen analysis — see [Screen analysis](#screen-analysis-analyze_screen) above. Voice listening is off until you enable it in **Settings → Privacy**.

### 4. Configuring AI providers

Open **Settings** and paste an API key for whichever provider(s) you want (Groq's free tier is the default). With no key configured for the active provider, JARVIS falls back to a local, deterministic offline responder — clearly labeled "JARVIS Offline" in the UI, never presented as a real cloud model.

---

## Project Structure

```
jarvis/
├── main.py                          # Entry point: splash screen → main window
├── requirements.txt
├── config.example.json              # Secret-free settings template
│
├── app/
│   ├── application.py               # QApplication setup (High-DPI, shared GL contexts)
│   └── config.py                    # AppConfig — settings, API keys, atomic save/load
│
├── core/
│   ├── ai/                          # LLM provider layer
│   │   ├── base.py                  # BaseAIProvider / AIResponse / ChatMessage contracts
│   │   ├── manager.py               # AIProviderManager — routing, bounded history
│   │   ├── brain.py                 # Offline regex/keyword responder (fallback only)
│   │   ├── mock_provider.py         # Wraps brain.py, honestly labeled "JARVIS Offline"
│   │   ├── groq_provider.py / gemini_provider.py / openai_provider.py /
│   │   │   claude_provider.py / opensource_provider.py   # Real cloud/local LLM clients
│   │   └── tool_prompt.py           # Shared tool-calling system prompt + action-tag parsing
│   │
│   ├── voice/                       # STT/TTS/routing
│   │   ├── voice_engine.py          # Mic capture, VAD, TTS playback, state machine
│   │   ├── stt_engine.py            # Faster-Whisper (primary) / Google (fallback)
│   │   ├── kokoro_engine.py / xtts_engine.py   # Local TTS engines
│   │   ├── intent_router.py         # Fast-path matching + LLM escalation + confidence
│   │   ├── transcript_processor.py  # Vocabulary correction, Hinglish transliteration
│   │   └── learning_memory.py       # Bounded, expiring "learned correction" store
│   │
│   ├── tools/                       # Desktop automation + the security gate
│   │   ├── base.py                  # BaseTool, PermissionLevel (5 tiers)
│   │   ├── confirmation.py          # ConfirmationService — the actual enforcement
│   │   ├── permission.py            # PermissionManager — the one place tiers are checked
│   │   ├── tool_manager.py          # Registry + bounded, timed execution
│   │   └── system_tools.py          # All concrete tools (open_app, type_text, run_claude_cli, ...)
│   │
│   ├── observability/               # Observe Mode + permission-gated auto-fix
│   │   ├── observer.py              # Bounded, atomic issue log
│   │   ├── task_queue.py            # Bounded, atomic fix-task queue
│   │   └── auto_fix.py              # Voice-confirmed proposal → gated run_claude_cli call
│   │
│   └── system/
│       ├── monitor.py               # CPU/RAM/Disk/Battery telemetry (psutil)
│       └── screen_analyzer.py       # Screenshot capture (temp dir, auto-cleanup) + cloud vision
│
├── ui/
│   ├── main_window.py                     # Root window, pipeline orchestration, confirmation dialog wiring
│   ├── components/
│   │   ├── confirmation_dialog.py         # The real Allow/Deny modal
│   │   ├── tool_runner.py                 # Off-GUI-thread tool execution helper for UI buttons
│   │   ├── ai_core_web.py + ui/web/*      # QWebEngineView-hosted three.js "AI core" HUD
│   │   └── title_bar.py / sidebar.py / activity_log.py / ...
│   └── pages/                             # 12 sidebar pages (Home, Chat, Voice, System, Control,
│                                            Apps, Files, Browser, Automation, Skills, Health, Settings)
│
├── tests/                            # Real automated tests (pytest + the legacy standalone suite)
│   ├── conftest.py                   # Shared QApplication fixture, confirmation-gate helpers
│   ├── test_components.py            # Standalone regression suite (also pytest-collectible)
│   ├── test_permission_security.py   # Confirmation gate, permission tiers, run_claude_cli hard-wall
│   ├── test_ai_integrity.py          # No silent offline-brain override, honest provider labels
│   ├── test_screen_privacy.py        # Temp-file cleanup, cloud consent, YouTube URL validation
│   ├── test_tool_reliability.py      # Timeout enforcement, shell-injection rejection
│   ├── test_config_persistence.py    # Save/load round-trip, corrupted-file recovery
│   ├── test_task_queue_and_concurrency.py
│   └── test_voice_reliability.py
│
└── dev_scripts/                      # One-off 3D-HUD tuning/visual-verification scripts —
                                        # NOT automated tests, not collected by pytest
```

---

## Running Tests

```powershell
pip install pytest pytest-mock ruff
pytest tests/ -v
```

Also runnable standalone (same file, no pytest dependency):

```powershell
python tests\test_components.py
```

Lint (scoped to genuine-bug rules; the codebase has pre-existing style debt in files this pass didn't touch, so full-style linting isn't a CI gate yet):

```powershell
ruff check --select F821,F822,F823,F811 app/ core/ ui/ tests/
```

CI (`.github/workflows/ci.yml`) runs a fresh `pip install -r requirements.txt` on `windows-latest`, an import smoke test, the lint pass above, and the full test suite on every push/PR.

---

## Packaging

A PyInstaller path is documented but **has not been verified end-to-end** (no `.spec` file is committed, and packaging a `QWebEngineView`-using app correctly bundles extra Chromium resources PyInstaller doesn't include automatically). Treat "build a distributable `JARVIS.exe`" as unverified until someone actually runs this through and confirms the packaged build launches, the 3D HUD renders, and the TTS/STT model files are found at their expected paths:

```powershell
pip install pyinstaller
pyinstaller --noconsole --name "JARVIS" --clean main.py
```

---

## Known Limitations

- No wake word — see [Voice & privacy](#voice--privacy).
- No packaging verification — see [Packaging](#packaging).
- `AnalyzeScreenTool`/volume/media/lock-screen tools are hardcoded to their tiers above; there's no per-user customization of the permission model yet.
- The Automation and Skills pages describe planned capabilities (a real scheduler, macro recording, semantic document search, an encrypted credential vault) that are **not implemented** — they're clearly marked "Coming Soon" in the UI rather than showing fake status.
- API keys are stored in plaintext locally (see [API keys & secrets](#api-keys--secrets)) — no OS keychain/DPAPI integration yet.
- Pre-existing style-lint debt (unused imports, import ordering) exists in files outside the scope of the most recent hardening pass; `ruff check` with the full default ruleset will show these, but they're not correctness bugs and aren't a CI gate.
