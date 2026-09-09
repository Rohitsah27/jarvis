# JARVIS — Personal AI Desktop Operating Console

A native Windows desktop application built with **Python 3.12+** and **PySide6 (Qt for Python)**. Designed with a futuristic cyber-HUD aesthetic inspired by advanced AI consoles, featuring a real-time holographic animated AI Core, live hardware telemetry, interactive voice HUD, conversational chat console, and a modular architecture ready for full autonomous Windows computer control.

---

## Key Features

- **Native Windows Desktop UI**: 100% native PySide6/Qt — strictly NO Electron, NO Chromium wrappers, NO web views.
- **ElevenLabs Neural Voice & Simple Hindi**: Powered by ElevenLabs `eleven_multilingual_v2` with human-like studio quality speech, speaking and understanding simple, natural Hindi and English with seamless Windows SAPI fallback.
- **Futuristic Holographic AI Core**: Custom `QPainter` double-buffered animated orb with rotating segmented HUD techno-rings, cyber wireframe globe, energetic central core, and reactive operational states (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `PROCESSING`, `OFFLINE`).

- **Live Hardware Diagnostics**: Non-blocking background worker thread sampling real-time CPU %, RAM %, Disk %, Network throughput, and Battery status via `psutil`.
- **Conversational Chat Console**: Neural console interface with message stream, typing/thinking indicator, timestamps, and model switching.
- **Voice Subsystem**: Audio waveform visualizer reacting dynamically to voice capture and speech synthesis, with architecture ready for local Whisper STT and Neural TTS.
- **Security & Permission Gate**: Four-stage autonomous execution pipeline:
  $$\text{AI Inference} \longrightarrow \text{Tool Manager} \longrightarrow \text{Permission Gate} \longrightarrow \text{Windows Action}$$
  Prevents unauthorized system modifications and supports user approval confirmation.
- **Custom Frameless Window**: Native borderless HUD frame with custom drag-to-move, maximize/restore, minimize, and close controls.

---

## Project Structure

```
jarvis/
│
├── main.py                          # Application entry point
├── requirements.txt                 # Dependencies (PySide6, psutil, pywin32)
├── README.md                        # Documentation & setup guide
│
├── app/                             # Application layer
│   ├── __init__.py
│   ├── application.py               # High-DPI Qt application setup & lifecycle
│   └── config.py                    # Global settings, user profile, defaults
│
├── core/                            # Core engine logic (separated from UI)
│   ├── ai/                          # AI Provider Subsystem
│   │   ├── base.py                  # BaseAIProvider, ChatMessage, ToolCallRequest
│   │   ├── mock_provider.py         # Realistic JARVIS persona & tool intent detection
│   │   ├── claude_provider.py       # Anthropic Claude API integration stub
│   │   └── manager.py               # AIProviderManager (provider switching & history)
│   │
│   ├── voice/                       # Voice Subsystem
│   │   ├── voice_engine.py          # VoiceEngine interface, states & audio simulator
│   │   └── waveform_generator.py    # Amplitude generation math
│   │
│   ├── tools/                       # System Automation & Tooling
│   │   ├── base.py                  # BaseTool and PermissionLevel abstractions
│   │   ├── permission.py            # PermissionManager security gate
│   │   ├── system_tools.py          # Safe desktop tools (Screenshot, App launch, etc.)
│   │   └── tool_manager.py          # Tool registry & execution pipeline
│   │
│   └── system/                      # Hardware Telemetry
│       └── monitor.py               # Background QThread monitoring CPU/RAM/Disk via psutil
│
├── ui/                              # Native Desktop Presentation Layer
│   ├── main_window.py               # Root QMainWindow assembling header, sidebar, and pages
│   ├── styles/
│   │   ├── theme.py                 # Cyberpunk & futuristic color tokens
│   │   └── qss.py                   # Master Qt StyleSheet (QSS)
│   ├── components/
│   │   ├── title_bar.py             # Custom frameless title bar with drag & controls
│   │   ├── sidebar.py               # Sleek left navigation sidebar & user badge
│   │   ├── ai_core.py               # Custom QPainter animated holographic AI orb
│   │   ├── circular_gauge.py        # Circular progress gauges with smooth interpolation
│   │   ├── quick_actions.py         # 2x4 Quick Action grid buttons
│   │   ├── waveform_widget.py       # Live audio waveform visualizer
│   │   ├── chat_widget.py           # Message bubbles & typing indicator
│   │   └── activity_log.py          # Live scrolling event telemetry stream
│   └── pages/
│       ├── home_page.py             # Main dashboard matching design vision
│       ├── chat_page.py             # Dedicated AI conversation interface
│       ├── system_page.py           # In-depth system hardware diagnostics
│       ├── voice_page.py            # Voice HUD & speech transcript viewer
│       ├── control_page.py          # Computer control security console
│       ├── apps_page.py             # Application launcher & manager
│       ├── files_page.py            # File explorer & quick search
│       ├── browser_page.py          # Browser automation controls
│       ├── automation_page.py       # Macro workflow sequences
│       ├── skills_page.py           # Modular skills directory
│       └── settings_page.py         # App & AI provider configuration
│
└── tests/                           # Verification & Unit Tests
    ├── test_components.py           # Automated tests for all core modules & UI
    └── verify_launch.py             # Headless rendering & screenshot grabber
```

---

## Getting Started

### 1. Prerequisites

- **Windows 10 / 11** (64-bit)
- **Python 3.12+** installed and available in your `PATH`

### 2. Installation

Navigate to the project directory and install the required dependencies:

```powershell
cd c:\Users\pramo\Desktop\jarvis
pip install -r requirements.txt
```

### 3. Launching the Application

Run the application with Python:

```powershell
python main.py
```

---

## How to Build `JARVIS.exe`

To package JARVIS as a standalone Windows executable using **PyInstaller**:

1. Install PyInstaller:
   ```powershell
   pip install pyinstaller
   ```

2. Generate the single-file executable:
   ```powershell
   pyinstaller --noconsole --name "JARVIS" --clean main.py
   ```

3. The generated `JARVIS.exe` will be located inside the `dist/JARVIS/` directory, ready to run without requiring a Python installation.

---

## Architecture Integration Points

### 1. Where to Integrate Real AI Providers

All AI model interactions are decoupled through the `BaseAIProvider` protocol in [`core/ai/base.py`](file:///c:/Users/pramo/Desktop/jarvis/core/ai/base.py).

- **Anthropic Claude**: An API client is already structured in [`core/ai/claude_provider.py`](file:///c:/Users/pramo/Desktop/jarvis/core/ai/claude_provider.py). Simply supply your `ANTHROPIC_API_KEY` in your environment or via the Settings page.
- **OpenAI (GPT-4o) / Local LLM (Ollama)**: Create a new class subclassing `BaseAIProvider`:
  ```python
  from core.ai.base import BaseAIProvider, AIResponse

  class OllamaProvider(BaseAIProvider):
      @property
      def name(self) -> str:
          return "Ollama Llama 3"

      def generate_response(self, prompt, history=None) -> AIResponse:
          # Call http://localhost:11434/api/generate
          ...
  ```
  Register it in [`core/ai/manager.py`](file:///c:/Users/pramo/Desktop/jarvis/core/ai/manager.py) via `AIProviderManager`.

### 2. Where to Integrate Windows Automation Tools

Automation capabilities are managed through the `BaseTool` interface in [`core/tools/base.py`](file:///c:/Users/pramo/Desktop/jarvis/core/tools/base.py).

To add a new Windows control tool:
1. Define a tool class in [`core/tools/system_tools.py`](file:///c:/Users/pramo/Desktop/jarvis/core/tools/system_tools.py):
   ```python
   from core.tools.base import BaseTool, PermissionLevel, ToolResult

   class CloseAppTool(BaseTool):
       @property
       def name(self) -> str:
           return "close_application"

       @property
       def description(self) -> str:
           return "Terminates an active Windows process."

       @property
       def permission_level(self) -> PermissionLevel:
           return PermissionLevel.CONFIRMATION_REQUIRED

       def execute(self, **kwargs) -> ToolResult:
           # Windows process termination logic
           return ToolResult(True, "Process closed", self.name)
   ```
2. Register the tool with `tool_manager.register_tool(...)` in [`core/tools/tool_manager.py`](file:///c:/Users/pramo/Desktop/jarvis/core/tools/tool_manager.py).
3. The security gate automatically checks permissions in [`core/tools/permission.py`](file:///c:/Users/pramo/Desktop/jarvis/core/tools/permission.py) before any execution occurs.

### 3. Where to Integrate Voice (Whisper / Neural TTS)

The voice system is encapsulated in [`core/voice/voice_engine.py`](file:///c:/Users/pramo/Desktop/jarvis/core/voice/voice_engine.py):
- **Whisper STT**: Replace the `transcribe()` stub with `openai-whisper` or `faster-whisper`.
- **Text-to-Speech**: Replace the `speak()` stub with `pyttsx3`, `edge-tts`, or `kokoro`.

---

## Running Verification Tests

Run the included test suites to verify that all modules, offscreen Qt renderers, and system metrics are functioning correctly:

```powershell
python tests\test_components.py
python tests\verify_launch.py
```
