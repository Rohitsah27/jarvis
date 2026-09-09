"""
Application initialization, High-DPI configuration, and Qt event loop setup.
"""
import sys
import os

# Ensure standard output and error streams support UTF-8 on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from app.config import config

# Must be set before the QApplication instance is constructed. The app mixes
# QQuickWidget (native Qt Quick HUD) with QWebEngineView (Chromium-based,
# used by the web-rendered AI core) in the same process — without shared GL
# contexts these two GPU-accelerated widget types can conflict/crash.
QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)


class JarvisApplication(QApplication):
    """Configured QApplication singleton for JARVIS."""

    def __init__(self, argv=None):
        if argv is None:
            argv = sys.argv

        # Configure High DPI scaling for modern 4K/retina Windows displays
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

        super().__init__(argv)

        from ui.styles.theme import theme
        theme.init_fonts()

        self.setApplicationName(config.APP_NAME)
        self.setApplicationDisplayName(f"{config.APP_NAME} - {config.APP_SUBTITLE}")
        self.setApplicationVersion(config.APP_VERSION)
        self.setOrganizationName("StarkIndustries")
        self.setOrganizationDomain("jarvis.ai")
