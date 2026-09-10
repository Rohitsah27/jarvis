"""
Home Dashboard Page matching the JARVIS futuristic command center design mockup.
Contains Digital Clock/Weather, Central AI Core Orb, System Status Circular Gauges,
Quick Actions Grid, Interactive Suggestion Cards, Glowing Prompt Capsule, and HUD Footer.
"""
from typing import Optional
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QScrollArea,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, Signal, QRectF, QPointF, QSize
from PySide6.QtGui import QFont, QColor, QPainter, QPainterPath, QPen, QBrush, QPixmap, QIcon

from ui.styles.theme import theme
from ui.components.ai_core import AICoreState
from ui.components.ai_core_web import JarvisAICoreWeb as JarvisAICore
from ui.components.circular_gauge import CircularGaugeWidget
from ui.components.hud_frame import HudCornerFrame
from core.ai.manager import ai_manager
from ui.components.quick_actions import QuickActionsWidget
from ui.components.waveform_widget import WaveformWidget
from ui.components.audio_vibration import JarvisAudioVibrationWidget
from app.config import config
from core.system.monitor import SystemTelemetry


class SuggestionCard(QPushButton):
    """Interactive suggested prompt card."""

    def __init__(self, icon_str: str, text: str, parent=None):
        super().__init__(parent)
        self.prompt_text = text
        self.setFixedHeight(54)
        self.setCursor(Qt.PointingHandCursor)

        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {theme.BG_CARD};
                border: 1px solid rgba(0, 210, 255, 0.2);
                border-radius: 12px;
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                background-color: {theme.BG_CARD_HOVER};
                border: 1px solid {theme.CYAN_ACCENT};
            }}
            QPushButton:pressed {{
                background-color: rgba(0, 210, 255, 0.15);
            }}
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(10)

        # Icon box
        lbl_icon = QLabel(icon_str)
        lbl_icon.setFont(QFont(theme.FONT_FAMILY, 13))
        lbl_icon.setStyleSheet(f"color: {theme.CYAN_ACCENT}; background: transparent; border: none;")

        # Prompt text
        lbl_text = QLabel(text)
        lbl_text.setWordWrap(True)
        lbl_text.setFont(QFont(theme.FONT_FAMILY, 9))
        lbl_text.setStyleSheet("color: #e6f1ff; background: transparent; border: none;")

        layout.addWidget(lbl_icon)
        layout.addWidget(lbl_text)


def _make_sun_icon(color: str = "#ffb703", size: int = 16) -> QPixmap:
    """Crisp vector weather sun icon with glowing disc and radiating rays."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(color)))

    # Central sun disc
    painter.drawEllipse(QRectF(size * 0.28, size * 0.28, size * 0.44, size * 0.44))

    # 8 radiating rays
    painter.setPen(QPen(QColor(color), 1.5, Qt.SolidLine, Qt.RoundCap))
    import math
    cx, cy = size / 2.0, size / 2.0
    r1, r2 = size * 0.30, size * 0.46
    for a in range(0, 360, 45):
        rad = math.radians(a)
        painter.drawLine(
            QPointF(cx + r1 * math.cos(rad), cy + r1 * math.sin(rad)),
            QPointF(cx + r2 * math.cos(rad), cy + r2 * math.sin(rad)),
        )
    painter.end()
    return pm


def _make_clip_icon(color: str, size: int = 16) -> QPixmap:
    """Crisp vector paperclip attachment glyph."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    path = QPainterPath()
    path.moveTo(size * 0.40, size * 0.75)
    path.lineTo(size * 0.70, size * 0.45)
    path.arcTo(QRectF(size * 0.55, size * 0.25, size * 0.30, size * 0.30), 45, -180)
    path.lineTo(size * 0.32, size * 0.70)
    path.arcTo(QRectF(size * 0.18, size * 0.58, size * 0.28, size * 0.28), -135, -180)
    path.lineTo(size * 0.62, size * 0.38)
    p.strokePath(path, pen)
    p.end()
    return pm


def _make_mic_icon(color: str, size: int = 18) -> QPixmap:
    """Crisp vector microphone glyph with capsule and cradle."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)

    # Capsule
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor(color)))
    p.drawRoundedRect(QRectF(size * 0.36, size * 0.16, size * 0.28, size * 0.44), size * 0.14, size * 0.14)

    # U-cradle
    pen = QPen(QColor(color), 1.6, Qt.SolidLine, Qt.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawArc(QRectF(size * 0.24, size * 0.28, size * 0.52, size * 0.42), 0, -180 * 16)

    # Stand and base
    p.drawLine(QPointF(size * 0.5, size * 0.70), QPointF(size * 0.5, size * 0.85))
    p.drawLine(QPointF(size * 0.32, size * 0.85), QPointF(size * 0.68, size * 0.85))
    p.end()
    return pm


def _make_send_icon(color: str, size: int = 16) -> QPixmap:
    """Crisp vector command transmit arrow glyph."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)

    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor(color)))
    path = QPainterPath()
    path.moveTo(size * 0.25, size * 0.22)
    path.lineTo(size * 0.82, size * 0.50)
    path.lineTo(size * 0.25, size * 0.78)
    path.lineTo(size * 0.38, size * 0.50)
    path.closeSubpath()
    p.drawPath(path)
    p.end()
    return pm


def _make_terminal_icon(color: str, size: int = 16) -> QPixmap:
    """Crisp vector terminal command prompt icon '>_'."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    # Chevron '>'
    p.drawLine(QPointF(size * 0.22, size * 0.30), QPointF(size * 0.50, size * 0.50))
    p.drawLine(QPointF(size * 0.50, size * 0.50), QPointF(size * 0.22, size * 0.70))
    # Underscore '_'
    p.drawLine(QPointF(size * 0.56, size * 0.70), QPointF(size * 0.82, size * 0.70))
    p.end()
    return pm


class HomePage(QWidget):
    """Main futuristic dashboard."""

    prompt_submitted = Signal(str)
    voice_toggle_requested = Signal()
    quick_action_triggered = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

        # Digital Clock Timer
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start()
        self._update_clock()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 10)
        main_layout.setSpacing(12)

        # -------------------------------------------------------------
        # -------------------------------------------------------------
        # -------------------------------------------------------------
        # TOP ROW: Left Flank | AI Core (Center) | Right Flank
        # Left Flank: Greeting (Top) + Sloped Audio Vibration Wave (Bottom)
        # Right Flank: Time/Weather (Top) + Sloped Audio Vibration Wave (Bottom)
        # -------------------------------------------------------------
        top_row = QHBoxLayout()
        top_row.setSpacing(20)

        # 1. Left Flank: Greeting (Top) + Sloped Audio Vibration Wave (Bottom)
        left_flank = QVBoxLayout()
        left_flank.setContentsMargins(0, 0, 0, 0)
        left_flank.setSpacing(10)

        self.greet_widget = QWidget()
        self.greet_widget.setStyleSheet("background: transparent;")
        greet_layout = QVBoxLayout(self.greet_widget)
        greet_layout.setContentsMargins(4, 4, 4, 4)
        greet_layout.setSpacing(6)
        greet_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.lbl_greet_title = QLabel(f"HELLO {config.USER_NAME.split()[0].upper()}!")
        self.lbl_greet_title.setFont(QFont("Orbitron", 22, QFont.Bold))
        self.lbl_greet_title.setStyleSheet("color: #ffffff; background: transparent; letter-spacing: 2px;")

        self.lbl_greet_sub = QLabel("I'm JARVIS, your personal AI assistant.\nHow can I help you today?")
        self.lbl_greet_sub.setFont(QFont("Rajdhani", 11.5, QFont.Medium))
        self.lbl_greet_sub.setStyleSheet("color: #00d2ff; background: transparent; line-height: 1.4; letter-spacing: 0.5px;")
        self.lbl_greet_sub.setWordWrap(True)

        greet_layout.addWidget(self.lbl_greet_title)
        greet_layout.addWidget(self.lbl_greet_sub)
        left_flank.addWidget(self.greet_widget)

        left_flank.addStretch(1)

        # Bottom-Left Sloped Audio Vibration Visualizer
        self.left_vibration = JarvisAudioVibrationWidget(side="left", parent=self)
        self.left_vibration.setMinimumSize(220, 140)
        self.left_vibration.setMaximumHeight(200)
        left_flank.addWidget(self.left_vibration)

        top_row.addLayout(left_flank)

        # 2. Center: Holographic AI Core Orb — expands to occupy center
        self.ai_core = JarvisAICore(self)
        self.ai_core.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        top_row.addWidget(self.ai_core, 1)

        # 3. Right Flank: Time/Weather (Top) + Sloped Audio Vibration Wave (Bottom)
        right_flank = QVBoxLayout()
        right_flank.setContentsMargins(0, 0, 0, 0)
        right_flank.setSpacing(10)

        self.time_widget = QWidget()
        self.time_widget.setStyleSheet("background: transparent;")
        time_layout = QVBoxLayout(self.time_widget)
        time_layout.setContentsMargins(4, 4, 4, 4)
        time_layout.setSpacing(4)
        time_layout.setAlignment(Qt.AlignTop | Qt.AlignRight)

        self.lbl_time = QLabel("09:42 AM")
        self.lbl_time.setAlignment(Qt.AlignRight)
        self.lbl_time.setFont(QFont("Orbitron", 26, QFont.Bold))
        self.lbl_time.setStyleSheet("color: #ffffff; background: transparent; letter-spacing: 2px;")

        self.lbl_date = QLabel("Thursday, Sep 4, 2025")
        self.lbl_date.setAlignment(Qt.AlignRight)
        self.lbl_date.setFont(QFont("Rajdhani", 11, QFont.Bold))
        self.lbl_date.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; background: transparent; letter-spacing: 1px;")

        # Weather (Right-aligned)
        weather_row = QHBoxLayout()
        weather_row.setSpacing(6)
        weather_row.addStretch(1)
        lbl_sun = QLabel()
        lbl_sun.setPixmap(_make_sun_icon("#ffb703", 16))
        lbl_sun.setStyleSheet("background: transparent;")
        self.lbl_temp = QLabel("28°C")
        self.lbl_temp.setFont(QFont("Orbitron", 12, QFont.Bold))
        self.lbl_temp.setStyleSheet("color: #00d2ff; background: transparent;")

        self.lbl_loc = QLabel(f"• {config.USER_LOCATION}")
        self.lbl_loc.setFont(QFont("Rajdhani", 10))
        self.lbl_loc.setStyleSheet(f"color: {theme.TEXT_MUTED}; background: transparent;")

        weather_row.addWidget(lbl_sun)
        weather_row.addWidget(self.lbl_temp)
        weather_row.addWidget(self.lbl_loc)

        self.lbl_quote = QLabel('"A smarter you, every day."')
        self.lbl_quote.setAlignment(Qt.AlignRight)
        f_quote = QFont("Rajdhani", 9.5)
        f_quote.setItalic(True)
        self.lbl_quote.setFont(f_quote)
        self.lbl_quote.setStyleSheet(f"color: {theme.TEXT_MUTED}; background: transparent; padding-top: 4px;")

        time_layout.addWidget(self.lbl_time)
        time_layout.addWidget(self.lbl_date)
        time_layout.addLayout(weather_row)
        time_layout.addWidget(self.lbl_quote)
        right_flank.addWidget(self.time_widget)

        right_flank.addStretch(1)

        # Bottom-Right Sloped Audio Vibration Visualizer
        self.right_vibration = JarvisAudioVibrationWidget(side="right", parent=self)
        self.right_vibration.setMinimumSize(220, 140)
        self.right_vibration.setMaximumHeight(200)
        right_flank.addWidget(self.right_vibration)

        top_row.addLayout(right_flank)

        # 3. Right: System Status & Quick Actions Stack — wrapped in one
        # widget, hidden by default (toggled from the title bar's view-
        # options button), so the AI core can claim this space too.
        self.right_panel = QWidget()
        right_col = QVBoxLayout(self.right_panel)
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(10)

        # System Status Card with 4 Circular Gauges — collapsed to header
        # only by default (no setFixedHeight, so it sizes to whatever
        # content is actually visible; expanded height matches the old
        # fixed 132px automatically since the same content reappears). Width
        # IS fixed though — otherwise collapsing hides the gauges that used
        # to be the widest content, and the whole card (and the Quick
        # Actions card below it) visibly shrinks and truncates its own
        # title text when there's nothing left to imply the original width.
        self.sys_status_card = HudCornerFrame()
        self.sys_status_card.setObjectName("SysStatusCard")
        self.sys_status_card.setFixedWidth(440)
        self.sys_status_card.setStyleSheet(
            f"""
            QFrame#SysStatusCard {{
                background-color: {theme.BG_PANEL};
                border: 1px solid rgba(0, 210, 255, 0.18);
                border-radius: 12px;
            }}
            """
        )
        sys_layout = QVBoxLayout(self.sys_status_card)
        sys_layout.setContentsMargins(12, 8, 12, 8)
        sys_layout.setSpacing(4)

        self.sys_header_btn = QPushButton()
        self.sys_header_btn.setCursor(Qt.PointingHandCursor)
        self.sys_header_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; text-align: left; }"
            "QPushButton:hover { background: rgba(0, 210, 255, 0.05); border-radius: 6px; }"
        )
        sys_header = QHBoxLayout(self.sys_header_btn)
        sys_header.setContentsMargins(2, 2, 2, 2)
        sys_title = QLabel("System Status")
        sys_title.setFont(QFont(theme.FONT_FAMILY, 10, QFont.Bold))
        sys_title.setStyleSheet("color: #ffffff; background: transparent;")
        self.sys_chevron = QLabel("›")
        self.sys_chevron.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 13px; background: transparent;")
        sys_header.addWidget(sys_title)
        sys_header.addStretch(1)
        sys_header.addWidget(self.sys_chevron)
        sys_layout.addWidget(self.sys_header_btn)

        # Gauges Row, wrapped so it can be shown/hidden as a unit.
        self.sys_content_widget = QWidget()
        gauges_row = QHBoxLayout(self.sys_content_widget)
        gauges_row.setContentsMargins(0, 0, 0, 0)
        gauges_row.setSpacing(6)

        self.gauge_cpu = CircularGaugeWidget("CPU", initial_value=23, parent=self)
        self.gauge_ram = CircularGaugeWidget("RAM", initial_value=56, parent=self)
        self.gauge_disk = CircularGaugeWidget("Disk", initial_value=68, parent=self)
        self.gauge_net = CircularGaugeWidget("Online", initial_value=100, icon_str="📶", parent=self)

        gauges_row.addWidget(self.gauge_cpu)
        gauges_row.addWidget(self.gauge_ram)
        gauges_row.addWidget(self.gauge_disk)
        gauges_row.addWidget(self.gauge_net)
        sys_layout.addWidget(self.sys_content_widget)

        # Collapsed by default — click the header to expand.
        self.sys_content_widget.setVisible(False)
        self.sys_header_btn.clicked.connect(self._toggle_sys_status)

        right_col.addWidget(self.sys_status_card)

        # Quick Actions Grid
        self.quick_actions = QuickActionsWidget(self)
        self.quick_actions.setFixedWidth(440)
        self.quick_actions.action_triggered.connect(self.quick_action_triggered.emit)
        right_col.addWidget(self.quick_actions)

        top_row.addWidget(self.right_panel)
        # Hidden by default — the AI core expands into this space; toggled
        # from the title bar's view-options button (main_window.py).
        self.right_panel.setVisible(False)
        main_layout.addLayout(top_row, 1)

        # -------------------------------------------------------------
        # Always-visible toggle bar for the interaction panel below
        # (greeting + suggestions + input bar + status badges + voice HUD),
        # which is hidden by default for a cleaner initial view. Voice
        # commands work regardless of this panel's visibility — the mic
        # listens continuously independent of the UI — this only affects
        # typed input and the on-screen chat/status display. Placed near
        # the bottom of the page (added to the layout just before the
        # footer further down) rather than right under the AI core, so the
        # core has the whole middle of the screen to itself.
        # -------------------------------------------------------------
        self.interaction_toggle_btn = QPushButton("//  COMMAND & TELEMETRY CONSOLE  ▾")
        self.interaction_toggle_btn.setIcon(QIcon(_make_terminal_icon(theme.CYAN_ACCENT, 16)))
        self.interaction_toggle_btn.setIconSize(QSize(16, 16))
        self.interaction_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.interaction_toggle_btn.setFixedHeight(36)
        self.interaction_toggle_btn.setFont(QFont("Orbitron", 8.5, QFont.Bold))
        self.interaction_toggle_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: rgba(9, 18, 32, 0.75);
                border: 1px solid rgba(0, 210, 255, 0.25);
                border-radius: 12px;
                color: #8da3c0;
                letter-spacing: 1.5px;
                padding: 4px 18px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 210, 255, 0.12);
                border: 1px solid {theme.CYAN_ACCENT};
                color: #00d2ff;
            }}
            """
        )
        self.interaction_toggle_btn.clicked.connect(self._toggle_interaction_panel)
        # Not added to main_layout here — placed near the bottom of the page
        # (just above the footer) further down instead.

        self.interaction_panel = QWidget()
        interaction_layout = QVBoxLayout(self.interaction_panel)
        interaction_layout.setContentsMargins(0, 0, 0, 0)
        interaction_layout.setSpacing(12)

        # -------------------------------------------------------------
        # BOTTOM: Futuristic Cybernetic Prompt Input Capsule Bar
        # -------------------------------------------------------------
        input_container = QVBoxLayout()
        input_container.setSpacing(6)

        self.prompt_capsule = QFrame()
        self.prompt_capsule.setObjectName("PromptCapsule")
        self.prompt_capsule.setFixedHeight(54)
        self.prompt_capsule.setStyleSheet(
            f"""
            QFrame#PromptCapsule {{
                background-color: rgba(9, 18, 32, 0.85);
                border: 1.5px solid rgba(0, 210, 255, 0.40);
                border-radius: 27px;
            }}
            QFrame#PromptCapsule:hover {{
                border: 1.5px solid rgba(0, 210, 255, 0.75);
                background-color: rgba(12, 24, 42, 0.95);
            }}
            """
        )

        capsule_layout = QHBoxLayout(self.prompt_capsule)
        capsule_layout.setContentsMargins(12, 4, 8, 4)
        capsule_layout.setSpacing(10)

        # Professional Vector Attachment Clip Icon
        self.clip_btn = QPushButton()
        self.clip_btn.setIcon(QIcon(_make_clip_icon("#8da3c0", 18)))
        self.clip_btn.setIconSize(QSize(18, 18))
        self.clip_btn.setFixedSize(36, 36)
        self.clip_btn.setCursor(Qt.PointingHandCursor)
        self.clip_btn.setToolTip("Attach context or command script")
        self.clip_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 18px; }"
            "QPushButton:hover { background: rgba(0, 210, 255, 0.15); }"
        )

        # Text Input with Rajdhani display font & custom cyan selection
        self.input_edit = QLineEdit()
        self.input_edit.setFont(QFont("Rajdhani", 12.5, QFont.Medium))
        self.input_edit.setPlaceholderText("Type a command or ask JARVIS anything...")
        self.input_edit.setStyleSheet(
            "QLineEdit { background: transparent; border: none; color: #ffffff; font-size: 12.5pt; padding: 0px 4px; letter-spacing: 0.8px; selection-background-color: #00d2ff; selection-color: #060e18; }"
            "QLineEdit::placeholder { color: #5a718c; font-style: italic; }"
        )
        self.input_edit.returnPressed.connect(self._on_send_clicked)

        # Professional Vector Mic Toggle Button
        self.mic_btn = QPushButton()
        self.mic_btn.setIcon(QIcon(_make_mic_icon("#8da3c0", 18)))
        self.mic_btn.setIconSize(QSize(18, 18))
        self.mic_btn.setFixedSize(38, 38)
        self.mic_btn.setCursor(Qt.PointingHandCursor)
        self.mic_btn.setToolTip("Toggle Neural Voice Dictation")
        self.mic_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: rgba(0, 210, 255, 0.08);
                border: 1px solid rgba(0, 210, 255, 0.25);
                border-radius: 19px;
            }}
            QPushButton:hover {{
                background: rgba(0, 210, 255, 0.22);
                border: 1px solid {theme.CYAN_ACCENT};
            }}
            """
        )
        self.mic_btn.clicked.connect(self.voice_toggle_requested.emit)

        # Professional Vector Send Button (Angled Transmit Paperplane / Chevron)
        self.send_btn = QPushButton()
        self.send_btn.setObjectName("SendButton")
        self.send_btn.setIcon(QIcon(_make_send_icon("#060e18", 16)))
        self.send_btn.setIconSize(QSize(16, 16))
        self.send_btn.setFixedSize(38, 38)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setToolTip("Transmit Command (Enter)")
        self.send_btn.setStyleSheet(
            f"""
            QPushButton#SendButton {{
                background-color: {theme.CYAN_ACCENT};
                border: none;
                border-radius: 19px;
            }}
            QPushButton#SendButton:hover {{
                background-color: #38e1ff;
            }}
            QPushButton#SendButton:pressed {{
                background-color: #00b0d8;
            }}
            """
        )
        self.send_btn.clicked.connect(self._on_send_clicked)

        capsule_layout.addWidget(self.clip_btn)
        capsule_layout.addWidget(self.input_edit, 1)
        capsule_layout.addWidget(self.mic_btn)
        capsule_layout.addWidget(self.send_btn)

        input_container.addWidget(self.prompt_capsule)

        # Sub-bar: Status Badges & Keyboard Hint
        sub_bar = QHBoxLayout()
        sub_bar.setContentsMargins(12, 4, 12, 0)
        sub_bar.setSpacing(10)

        # Voice Status
        self.badge_voice = QLabel("● VOICE READY")
        self.badge_voice.setFixedHeight(24)
        self.badge_voice.setAlignment(Qt.AlignCenter)
        self.badge_voice.setFont(QFont("Rajdhani", 8.5, QFont.Bold))
        self.badge_voice.setStyleSheet(
            f"color: {theme.STATUS_ONLINE}; background: rgba(0, 255, 157, 0.08); "
            f"border: 1px solid rgba(0, 255, 157, 0.30); border-radius: 12px; padding: 2px 10px; letter-spacing: 0.8px;"
        )

        # Active AI Model
        self.badge_model = QLabel(f"⚡ {ai_manager.active_provider_name.upper()}")
        self.badge_model.setFixedHeight(24)
        self.badge_model.setAlignment(Qt.AlignCenter)
        self.badge_model.setFont(QFont("Rajdhani", 8.5, QFont.Bold))
        self.badge_model.setStyleSheet(
            f"color: {theme.CYAN_ACCENT}; background: rgba(0, 210, 255, 0.08); "
            f"border: 1px solid rgba(0, 210, 255, 0.25); border-radius: 12px; padding: 2px 10px; letter-spacing: 0.8px;"
        )

        # Desktop Control Active
        badge_ctrl = QLabel("◈ DESKTOP AUTOMATION ACTIVE")
        badge_ctrl.setFixedHeight(24)
        badge_ctrl.setAlignment(Qt.AlignCenter)
        badge_ctrl.setFont(QFont("Rajdhani", 8.5, QFont.Bold))
        badge_ctrl.setStyleSheet(
            f"color: {theme.TEXT_SECONDARY}; background: rgba(14, 23, 38, 0.85); "
            f"border: 1px solid rgba(0, 210, 255, 0.20); border-radius: 12px; padding: 2px 10px; letter-spacing: 0.8px;"
        )

        # Online Telemetry
        badge_online = QLabel("● NEURAL LINK ONLINE")
        badge_online.setFixedHeight(24)
        badge_online.setAlignment(Qt.AlignCenter)
        badge_online.setFont(QFont("Rajdhani", 8.5, QFont.Bold))
        badge_online.setStyleSheet(
            f"color: {theme.STATUS_ONLINE}; background: rgba(0, 255, 157, 0.08); "
            f"border: 1px solid rgba(0, 255, 157, 0.30); border-radius: 12px; padding: 2px 10px; letter-spacing: 0.8px;"
        )

        sub_bar.addWidget(self.badge_voice)
        sub_bar.addWidget(self.badge_model)
        sub_bar.addWidget(badge_ctrl)
        sub_bar.addWidget(badge_online)
        sub_bar.addStretch(1)

        # Hint
        hint_lbl = QLabel("PRESS ENTER ↵ TO TRANSMIT")
        hint_lbl.setFont(QFont("Rajdhani", 8.5, QFont.Bold))
        hint_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; letter-spacing: 1px;")
        sub_bar.addWidget(hint_lbl)

        input_container.addLayout(sub_bar)
        interaction_layout.addLayout(input_container)

        # -------------------------------------------------------------
        # LIVE SPEECH & SUBTITLES HUD BANNER (User Voice Display Area)
        # -------------------------------------------------------------
        self.live_speech_card = QFrame()
        self.live_speech_card.setObjectName("LiveSpeechCard")
        self.live_speech_card.setFixedHeight(44)
        self.live_speech_card.setStyleSheet(
            f"""
            QFrame#LiveSpeechCard {{
                background-color: rgba(9, 20, 36, 0.85);
                border: 1px solid rgba(0, 210, 255, 0.28);
                border-left: 3px solid {theme.CYAN_ACCENT};
                border-radius: 8px;
            }}
            """
        )
        speech_layout = QHBoxLayout(self.live_speech_card)
        speech_layout.setContentsMargins(14, 4, 14, 4)
        speech_layout.setSpacing(12)

        # Left Glowing Tag
        self.lbl_speech_tag = QLabel("[ VOICE TELEMETRY ]")
        self.lbl_speech_tag.setFont(QFont("Orbitron", 8, QFont.Bold))
        self.lbl_speech_tag.setStyleSheet(
            f"color: {theme.CYAN_ACCENT}; background: rgba(0, 210, 255, 0.12); "
            f"border: 1px solid rgba(0, 210, 255, 0.35); border-radius: 5px; padding: 4px 10px; letter-spacing: 1.2px;"
        )
        speech_layout.addWidget(self.lbl_speech_tag)

        # Center Subtitle Text
        self.lbl_live_speech = QLabel("Say something aloud (e.g. 'Open Chrome' or 'Take a screenshot')...")
        self.lbl_live_speech.setFont(QFont("Rajdhani", 10.5, QFont.Medium))
        self.lbl_live_speech.setStyleSheet("color: #7d94b0; background: transparent;")
        speech_layout.addWidget(self.lbl_live_speech, 1)

        # Right Mini Audio Activity Indicator
        self.speech_wave = WaveformWidget(bar_count=8, parent=self)
        self.speech_wave.setFixedSize(46, 16)
        speech_layout.addWidget(self.speech_wave)

        interaction_layout.addWidget(self.live_speech_card)

        main_layout.addWidget(self.interaction_panel)
        # Hidden by default — click interaction_toggle_btn to reveal.
        self.interaction_panel.setVisible(False)

        # Toggle bar lives at the bottom of the page (just above the
        # footer), not right under the AI core, so the core dominates the
        # middle of the screen.
        main_layout.addWidget(self.interaction_toggle_btn)

        # -------------------------------------------------------------
        # FOOTER HUD: Motto & Partner Waveform (Perfectly Centered)
        # -------------------------------------------------------------
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(12, 4, 12, 2)

        footer_motto = QLabel("T H I N K   •   C O M M A N D   •   A C C O M P L I S H")
        footer_motto.setFont(QFont(theme.FONT_DISPLAY, 8, QFont.Bold))
        footer_motto.setStyleSheet(f"color: {theme.TEXT_MUTED}; letter-spacing: 2px;")
        footer_motto.setAlignment(Qt.AlignCenter)

        footer_right_widget = QWidget()
        footer_right_widget.setStyleSheet("background: transparent;")
        footer_right = QHBoxLayout(footer_right_widget)
        footer_right.setContentsMargins(0, 0, 0, 0)
        footer_right.setSpacing(8)
        footer_right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.footer_wave = WaveformWidget(bar_count=8, parent=self)
        self.footer_wave.setFixedSize(50, 16)

        footer_partner = QLabel("MORE THAN AN ASSISTANT, A PARTNER.")
        footer_partner.setFont(QFont(theme.FONT_FAMILY, 7))
        footer_partner.setStyleSheet(f"color: {theme.TEXT_MUTED}; letter-spacing: 0.5px;")

        footer_right.addWidget(self.footer_wave)
        footer_right.addWidget(footer_partner)

        # Equalize left and right flank widths so the center motto sits at exact 50% horizontal center
        flank_width = max(240, footer_right_widget.sizeHint().width())
        footer_right_widget.setFixedWidth(flank_width)

        footer_left_widget = QWidget()
        footer_left_widget.setStyleSheet("background: transparent;")
        footer_left_widget.setFixedWidth(flank_width)

        footer_layout.addWidget(footer_left_widget)
        footer_layout.addStretch(1)
        footer_layout.addWidget(footer_motto)
        footer_layout.addStretch(1)
        footer_layout.addWidget(footer_right_widget)

        main_layout.addLayout(footer_layout)

    def _update_clock(self):
        now = datetime.now()
        self.lbl_date.setText(now.strftime("%A, %b %d, %Y"))
        self.lbl_time.setText(now.strftime("%I:%M %p"))

    def update_telemetry(self, t: SystemTelemetry):
        self.gauge_cpu.set_value(t.cpu_percent)
        self.gauge_ram.set_value(t.ram_percent)
        self.gauge_disk.set_value(t.disk_percent)
        self.gauge_net.set_value(100.0 if t.network_online else 0.0)

    def _toggle_interaction_panel(self):
        expanded = self.interaction_panel.isVisible()
        self.interaction_panel.setVisible(not expanded)
        if expanded:
            self.interaction_toggle_btn.setText("//  COMMAND & TELEMETRY CONSOLE  ▾")
            self.interaction_toggle_btn.setIcon(QIcon(_make_terminal_icon(theme.CYAN_ACCENT, 16)))
        else:
            self.interaction_toggle_btn.setText("//  COLLAPSE CONSOLE  ▴")
            self.interaction_toggle_btn.setIcon(QIcon(_make_terminal_icon("#ffffff", 16)))
            self.input_edit.setFocus()

    def _toggle_sys_status(self):
        expanded = self.sys_content_widget.isVisible()
        self.sys_content_widget.setVisible(not expanded)
        self.sys_chevron.setText("⌄" if not expanded else "›")

    def _on_suggestion_clicked(self, prompt: str):
        self.input_edit.setText(prompt)
        self._on_send_clicked()

    def _on_send_clicked(self):
        text = self.input_edit.text().strip()
        if text:
            self.prompt_submitted.emit(text)
            self.input_edit.clear()

    def set_ai_state(self, state: str):
        self.ai_core.set_state(state)

    def set_mic_active(self, active: bool):
        if hasattr(self, "left_vibration"):
            self.left_vibration.set_active(active)
        if hasattr(self, "right_vibration"):
            self.right_vibration.set_active(active)
        if active:
            self.mic_btn.setIcon(QIcon(_make_mic_icon("#070e1a", 18)))
            self.mic_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: {theme.CYAN_ACCENT};
                    border: 1px solid #ffffff;
                    border-radius: 19px;
                }}
                """
            )
            self.footer_wave.set_active(True)
            self.badge_voice.setText("● VOICE ACTIVE")
            self.badge_voice.setStyleSheet(
                "color: #00ffea; background: rgba(0, 255, 234, 0.15); "
                "border: 1px solid rgba(0, 255, 234, 0.40); border-radius: 12px; padding: 2px 10px; letter-spacing: 0.8px;"
            )
        else:
            self.mic_btn.setIcon(QIcon(_make_mic_icon("#8da3c0", 18)))
            self.mic_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: rgba(0, 210, 255, 0.08);
                    border: 1px solid rgba(0, 210, 255, 0.25);
                    border-radius: 19px;
                }}
                QPushButton:hover {{
                    background: rgba(0, 210, 255, 0.22);
                    border: 1px solid {theme.CYAN_ACCENT};
                }}
                """
            )
            self.footer_wave.set_active(False)
            self.badge_voice.setText("● VOICE READY")
            self.badge_voice.setStyleSheet(
                f"color: {theme.STATUS_ONLINE}; background: rgba(0, 255, 157, 0.08); "
                f"border: 1px solid rgba(0, 255, 157, 0.30); border-radius: 12px; padding: 2px 10px; letter-spacing: 0.8px;"
            )

    def set_audio_amplitude(self, amp: float):
        """Dispatches audio amplitude to AI core, footer wave, and left/right vibration visualizers."""
        self.ai_core.set_audio_amplitude(amp)
        self.footer_wave.set_amplitude(amp)
        self.speech_wave.set_amplitude(amp)
        if hasattr(self, "left_vibration"):
            self.left_vibration.set_amplitude(amp)
        if hasattr(self, "right_vibration"):
            self.right_vibration.set_amplitude(amp)

    def set_live_speech(self, text: str, is_user: bool = True):
        """Displays user voice transcript or JARVIS response in the marked place."""
        if not text:
            return
        if is_user:
            self.lbl_speech_tag.setText("[ USER SPEECH ]")
            self.lbl_speech_tag.setStyleSheet(
                "color: #00ffea; background: rgba(0, 255, 234, 0.15); "
                "border: 1px solid rgba(0, 255, 234, 0.4); border-radius: 5px; padding: 4px 10px; font-weight: bold; letter-spacing: 1.2px;"
            )
            self.lbl_live_speech.setText(f'"{text}"')
            self.lbl_live_speech.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 10.5pt; background: transparent;")
            self.live_speech_card.setStyleSheet(
                "QFrame#LiveSpeechCard { background-color: rgba(9, 25, 48, 0.92); border: 1.5px solid #00d2ff; border-left: 3px solid #00d2ff; border-radius: 8px; }"
            )
            self.speech_wave.set_active(True)
        else:
            self.lbl_speech_tag.setText("[ JARVIS VOICE ]")
            self.lbl_speech_tag.setStyleSheet(
                f"color: {theme.CYAN_ACCENT}; background: rgba(0, 210, 255, 0.15); "
                f"border: 1px solid {theme.CYAN_ACCENT}; border-radius: 5px; padding: 4px 10px; font-weight: bold; letter-spacing: 1.2px;"
            )
            self.lbl_live_speech.setText(f'"{text}"')
            self.lbl_live_speech.setStyleSheet("color: #e0f2fe; font-size: 10pt; background: transparent;")
            self.live_speech_card.setStyleSheet(
                "QFrame#LiveSpeechCard { background-color: rgba(9, 21, 38, 0.85); border: 1px solid rgba(0, 210, 255, 0.35); border-left: 3px solid #00d2ff; border-radius: 8px; }"
            )
            self.speech_wave.set_active(False)

    def set_listening_hint(self):
        self.lbl_speech_tag.setText("[ LISTENING ]")
        self.lbl_speech_tag.setStyleSheet(
            f"color: {theme.CYAN_ACCENT}; background: rgba(0, 210, 255, 0.12); "
            f"border: 1px solid rgba(0, 210, 255, 0.35); border-radius: 5px; padding: 4px 10px; letter-spacing: 1.2px;"
        )
        self.lbl_live_speech.setText("Listening... (Speak your command now)")
        self.lbl_live_speech.setStyleSheet("color: #38bdf8; font-size: 9.5pt; background: transparent;")
        self.live_speech_card.setStyleSheet(
            f"QFrame#LiveSpeechCard {{ background-color: rgba(9, 21, 38, 0.75); border: 1px solid rgba(0, 210, 255, 0.28); border-left: 3px solid {theme.CYAN_ACCENT}; border-radius: 8px; }}"
        )
        self.speech_wave.set_active(True)

    def set_processing_hint(self):
        self.lbl_speech_tag.setText("[ PROCESSING ]")
        self.lbl_speech_tag.setStyleSheet(
            "color: #f59e0b; background: rgba(245, 158, 11, 0.15); "
            "border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 5px; padding: 4px 10px; letter-spacing: 1.2px;"
        )
        self.lbl_live_speech.setText("Processing speech phonemes...")
        self.lbl_live_speech.setStyleSheet("color: #fbbf24; font-size: 9.5pt; background: transparent;")
        self.live_speech_card.setStyleSheet(
            "QFrame#LiveSpeechCard { background-color: rgba(9, 21, 38, 0.75); border: 1px solid rgba(245, 158, 11, 0.35); border-left: 3px solid #f59e0b; border-radius: 8px; }"
        )
        self.speech_wave.set_active(True)

    def set_mic_unavailable_hint(self):
        """Mic disconnected, permission revoked, or the listener thread
        crashed — previously the UI just stayed on 'Listening...' forever
        with no indication anything was wrong. Clicking the mic button
        while this is showing retries (voice_engine.toggle_listening()
        routes to retry_microphone() in this state)."""
        self.lbl_speech_tag.setText("[ MIC UNAVAILABLE ]")
        self.lbl_speech_tag.setStyleSheet(
            "color: #ff4d4d; background: rgba(255, 77, 77, 0.15); "
            "border: 1px solid rgba(255, 77, 77, 0.4); border-radius: 5px; padding: 4px 10px; letter-spacing: 1.2px;"
        )
        self.lbl_live_speech.setText("Microphone unavailable — click the mic button to retry")
        self.lbl_live_speech.setStyleSheet("color: #ff4d4d; font-size: 9.5pt; background: transparent;")
        self.live_speech_card.setStyleSheet(
            "QFrame#LiveSpeechCard { background-color: rgba(9, 21, 38, 0.75); border: 1px solid rgba(255, 77, 77, 0.35); border-left: 3px solid #ff4d4d; border-radius: 8px; }"
        )
        self.speech_wave.set_active(False)
