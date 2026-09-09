"""
Master Qt StyleSheet (QSS) for the JARVIS desktop interface.
"""
from ui.styles.theme import theme


def get_application_stylesheet() -> str:
    return f"""
    /* Global Window Reset */
    QMainWindow {{
        background-color: {theme.BG_MAIN};
        color: {theme.TEXT_PRIMARY};
        font-family: {theme.FONT_FAMILY};
        font-size: 13px;
    }}

    QWidget#CentralWidget {{
        background: transparent;
        color: {theme.TEXT_PRIMARY};
    }}

    /* Futuristic Panels & Frames */
    QFrame.JarvisPanel {{
        background-color: {theme.BG_PANEL};
        border: 1px solid {theme.CYAN_BORDER};
        border-radius: 12px;
    }}

    QFrame.JarvisCard {{
        background-color: {theme.BG_CARD};
        border: 1px solid rgba(0, 210, 255, 0.18);
        border-radius: 10px;
    }}
    QFrame.JarvisCard:hover {{
        border: 1px solid rgba(0, 210, 255, 0.45);
        background-color: {theme.BG_CARD_HOVER};
    }}

    /* Scrollbars */
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(0, 210, 255, 0.3);
        min-height: 25px;
        border-radius: 3px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {theme.CYAN_ACCENT};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        height: 0px;
    }}

    /* Buttons */
    QPushButton {{
        background-color: {theme.BG_CARD};
        color: {theme.TEXT_PRIMARY};
        border: 1px solid rgba(0, 210, 255, 0.25);
        border-radius: 8px;
        padding: 6px 14px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {theme.BG_CARD_HOVER};
        border: 1px solid {theme.CYAN_ACCENT};
        color: #ffffff;
    }}
    QPushButton:pressed {{
        background-color: rgba(0, 210, 255, 0.2);
    }}

    /* Glow Action Button (Send / Primary) */
    QPushButton#SendButton {{
        background-color: {theme.CYAN_ACCENT};
        color: #050b14;
        border: none;
        border-radius: 20px;
        font-weight: bold;
    }}
    QPushButton#SendButton:hover {{
        background-color: #38e1ff;
    }}

    /* Text Inputs */
    QLineEdit {{
        background-color: {theme.BG_INPUT};
        color: {theme.TEXT_PRIMARY};
        border: 1px solid rgba(0, 210, 255, 0.25);
        border-radius: 8px;
        padding: 8px 14px;
        selection-background-color: {theme.CYAN_ACCENT};
        selection-color: #000000;
    }}
    QLineEdit:focus {{
        border: 1.5px solid {theme.CYAN_ACCENT};
        background-color: #0b1424;
    }}

    /* Glowing Prompt Input Capsule */
    QFrame#PromptCapsule {{
        background-color: #0a1220;
        border: 1.5px solid {theme.CYAN_ACCENT};
        border-radius: 24px;
    }}
    QFrame#PromptCapsule:focus-within {{
        border: 2px solid #4de5ff;
        background-color: #0c172a;
    }}

    /* Pill Badges */
    QFrame.PillBadge {{
        background-color: rgba(15, 25, 42, 0.7);
        border: 1px solid rgba(0, 210, 255, 0.2);
        border-radius: 14px;
        padding: 4px 10px;
    }}

    /* Tooltips */
    QToolTip {{
        background-color: #0f172a;
        color: {theme.TEXT_PRIMARY};
        border: 1px solid {theme.CYAN_ACCENT};
        padding: 5px 8px;
        border-radius: 4px;
    }}
    """
