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

    window = JarvisMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
