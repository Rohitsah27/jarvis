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


def main():
    """Initializes and runs the JARVIS desktop interface."""
    app = JarvisApplication(sys.argv)

    window = JarvisMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
