"""
JARVIS - Personal AI Desktop Operating Console.
Entry point for launching the native Windows desktop application.
"""
import sys
import os

# Ensure standard output streams support UTF-8 on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.application import JarvisApplication
from ui.components.splash_screen import JarvisSplashScreen
from ui.main_window import JarvisMainWindow

_default_excepthook = sys.excepthook


def _observing_excepthook(exc_type, exc_value, exc_tb):
    """Observe Mode's safety net: records any exception that reaches here
    (i.e. wasn't already caught closer to where it happened) before still
    doing exactly what the default hook would — this never changes the
    app's actual error behavior, it only additionally remembers it."""
    try:
        from core.observability.observer import observer
        observer.record_exception(exc_value, category="unhandled_exception", source="global")
    except Exception:
        pass
    _default_excepthook(exc_type, exc_value, exc_tb)


sys.excepthook = _observing_excepthook


def main():
    """Initializes and runs the JARVIS desktop interface."""
    app = JarvisApplication(sys.argv)

    # 1. Display holographic cybernetic splash screen immediately (< 50ms)
    splash = JarvisSplashScreen()
    splash.show()
    splash.set_progress(10, "INITIALIZING CYBERNETIC DESKTOP OS...")
    app.processEvents()

    # 2. Pause microphone during boot to avoid false speech triggers while loading
    try:
        from core.voice.voice_engine import voice_engine
        voice_engine.pause_listening()
    except Exception:
        pass

    # 3. Construct main window with UI pages and 3D HUD WebEngine
    window = JarvisMainWindow(splash=splash)

    # 4. Asynchronously preload Neural TTS and Faster-Whisper while splash screen stays active
    def on_preload_complete():
        from PySide6.QtCore import QTimer
        def reveal():
            splash.finish(window)
            try:
                from core.voice.voice_engine import voice_engine
                voice_engine.resume_listening()
            except Exception:
                pass
        QTimer.singleShot(350, reveal)

    splash.start_preload(window, on_preload_complete)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
