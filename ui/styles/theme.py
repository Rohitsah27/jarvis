from pathlib import Path
from dataclasses import dataclass
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QColor, QFontDatabase

_FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
_fonts_initialized = False


def init_fonts():
    global _fonts_initialized
    if _fonts_initialized or QCoreApplication.instance() is None:
        return
    if _FONTS_DIR.exists():
        for _font_file in _FONTS_DIR.glob("*.ttf"):
            try:
                QFontDatabase.addApplicationFont(str(_font_file))
            except Exception:
                pass
    _fonts_initialized = True


@dataclass(frozen=True)
class JarvisTheme:
    # Backgrounds
    BG_MAIN: str = "#070b12"
    BG_PANEL: str = "#0c1322"
    BG_CARD: str = "#111b2e"
    BG_CARD_HOVER: str = "#16243d"
    BG_INPUT: str = "#0a111d"
    BG_SIDEBAR: str = "#090e19"
    
    # Accents & Cyans
    CYAN_ACCENT: str = "#00d2ff"
    CYAN_BRIGHT: str = "#33dcff"
    CYAN_DIM: str = "#007a99"
    CYAN_GLOW: str = "rgba(0, 210, 255, 0.25)"
    CYAN_BORDER: str = "rgba(0, 210, 255, 0.35)"
    
    # Text
    TEXT_PRIMARY: str = "#e6f1ff"
    TEXT_SECONDARY: str = "#8da3c0"
    TEXT_MUTED: str = "#506580"
    
    # Status
    STATUS_ONLINE: str = "#00ff9d"
    STATUS_WARNING: str = "#ffb800"
    STATUS_ERROR: str = "#ff4d4d"
    STATUS_SPEAKING: str = "#00d2ff"
    STATUS_LISTENING: str = "#00f0ff"
    STATUS_THINKING: str = "#b366ff"
    
    # Font Families (Authentic futuristic AI aesthetics)
    FONT_FAMILY: str = "Rajdhani"
    FONT_MONO: str = "Consolas"
    FONT_DISPLAY: str = "Orbitron"
    FONT_AI: str = "Orbitron"
    FONT_BODY: str = "Rajdhani"

    def init_fonts(self):
        init_fonts()


theme = JarvisTheme()
