"""
Custom Frameless Window Title Bar with native drag, minimize, maximize, and close controls.
Features holographic branding, animated status capsule, and professional vector HUD controls.
"""
from typing import Optional
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QPoint, QPointF, QRectF, QSize, Signal, QTimer
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen, QFont, QBrush, QPixmap, QIcon
from ui.styles.theme import theme


def _make_hamburger_icon(color: str, size: int = 18) -> QPixmap:
    """Manually painted 3-line hamburger icon avoiding OS font glyph discrepancies."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 2.0)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    margin = size * 0.16
    for y in (size * 0.30, size * 0.52, size * 0.74):
        painter.drawLine(QPointF(margin, y), QPointF(size - margin, y))
    painter.end()
    return pm


def _make_panels_icon(color: str, size: int = 18) -> QPixmap:
    """2x2 grid glyph representing the dashboard's side panels (System
    Status / Quick Actions), for the view-options toggle button."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.6)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    gap = size * 0.14
    half = (size - gap) / 2.0
    painter.drawRoundedRect(QRectF(0, 0, half, half), 2, 2)
    painter.drawRoundedRect(QRectF(half + gap, 0, half, half), 2, 2)
    painter.drawRoundedRect(QRectF(0, half + gap, half, half), 2, 2)
    painter.drawRoundedRect(QRectF(half + gap, half + gap, half, half), 2, 2)
    painter.end()
    return pm


def _make_bell_icon(color: str, size: int = 16) -> QPixmap:
    """Crisp vector notification bell icon."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.4)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)

    # Top pin handle
    painter.drawLine(QPointF(size * 0.5, size * 0.16), QPointF(size * 0.5, size * 0.24))

    # Bell dome curve
    path = QPainterPath()
    path.moveTo(size * 0.5, size * 0.24)
    path.cubicTo(size * 0.34, size * 0.28, size * 0.26, size * 0.50, size * 0.22, size * 0.68)
    path.lineTo(size * 0.78, size * 0.68)
    path.cubicTo(size * 0.74, size * 0.50, size * 0.66, size * 0.28, size * 0.5, size * 0.24)
    painter.strokePath(path, pen)

    # Base rim line
    painter.drawLine(QPointF(size * 0.18, size * 0.68), QPointF(size * 0.82, size * 0.68))

    # Clapper
    painter.setBrush(QBrush(QColor(color)))
    painter.drawEllipse(QPointF(size * 0.5, size * 0.79), 1.5, 1.5)

    painter.end()
    return pm


def _make_wifi_icon(color: str, size: int = 16) -> QPixmap:
    """Crisp vector signal/telemetry indicator bars."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(color)))

    bar_w = 2.2
    spacing = 1.4
    heights = [3.5, 6.0, 8.5, 11.5]
    total_w = 4 * bar_w + 3 * spacing
    start_x = (size - total_w) / 2.0
    base_y = size * 0.82
    for i, h in enumerate(heights):
        x = start_x + i * (bar_w + spacing)
        painter.drawRoundedRect(QRectF(x, base_y - h, bar_w, h), 0.8, 0.8)
    painter.end()
    return pm


def _make_theme_icon(color: str, size: int = 16) -> QPixmap:
    """Crisp vector crescent moon / HUD dark mode icon."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(color)))

    moon_path = QPainterPath()
    moon_path.addEllipse(QRectF(size * 0.2, size * 0.2, size * 0.6, size * 0.6))
    cutout = QPainterPath()
    cutout.addEllipse(QRectF(size * 0.34, size * 0.14, size * 0.54, size * 0.54))
    shape = moon_path.subtracted(cutout)
    painter.drawPath(shape)
    painter.end()
    return pm


def _make_minimize_icon(color: str, size: int = 16) -> QPixmap:
    """Crisp vector minimize dash icon."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.6, Qt.SolidLine, Qt.RoundCap)
    painter.setPen(pen)
    painter.drawLine(QPointF(size * 0.24, size * 0.58), QPointF(size * 0.76, size * 0.58))
    painter.end()
    return pm


def _make_maximize_icon(color: str, size: int = 16, is_maximized: bool = False) -> QPixmap:
    """Crisp vector maximize / restore icon."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.4)
    pen.setJoinStyle(Qt.MiterJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)

    if not is_maximized:
        painter.drawRoundedRect(QRectF(size * 0.25, size * 0.25, size * 0.5, size * 0.5), 1.0, 1.0)
    else:
        # Restore double overlapping squares
        painter.drawRect(QRectF(size * 0.36, size * 0.22, size * 0.42, size * 0.42))
        painter.setBrush(QBrush(QColor("#070d18")))
        painter.drawRect(QRectF(size * 0.22, size * 0.36, size * 0.42, size * 0.42))
    painter.end()
    return pm


def _make_close_icon(color: str, size: int = 16) -> QPixmap:
    """Crisp vector close 'X' icon."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), 1.5, Qt.SolidLine, Qt.RoundCap)
    painter.setPen(pen)
    m = size * 0.28
    painter.drawLine(QPointF(m, m), QPointF(size - m, size - m))
    painter.drawLine(QPointF(size - m, m), QPointF(m, size - m))
    painter.end()
    return pm


def _make_reactor_logo(color: str, size: int = 32) -> QPixmap:
    """Glowing Iron Man Arc Reactor HUD logo icon."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)

    c = QColor(color)
    c_glow = QColor(c.red(), c.green(), c.blue(), 50)
    c_ring = QColor(c.red(), c.green(), c.blue(), 180)

    # Outer glow ring
    painter.setPen(QPen(c_ring, 1.5))
    painter.setBrush(QBrush(c_glow))
    painter.drawEllipse(QRectF(2, 2, size - 4, size - 4))

    # Inner segmented arc ring
    painter.setPen(QPen(c, 1.6, Qt.DashLine))
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(QRectF(6.5, 6.5, size - 13, size - 13))

    # Core energy dot
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor("#ffffff")))
    painter.drawEllipse(QRectF(size / 2.0 - 2.5, size / 2.0 - 2.5, 5.0, 5.0))

    painter.end()
    return pm


class HUDIconButton(QPushButton):
    """Futuristic HUD button that switches its vector QPixmap icon on hover and press."""

    def __init__(
        self,
        normal_pm: QPixmap,
        hover_pm: QPixmap,
        pressed_pm: Optional[QPixmap] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._normal_icon = QIcon(normal_pm)
        self._hover_icon = QIcon(hover_pm)
        self._pressed_icon = QIcon(pressed_pm) if pressed_pm else self._hover_icon
        self.setIcon(self._normal_icon)

    def set_icon_pixmaps(
        self,
        normal_pm: QPixmap,
        hover_pm: QPixmap,
        pressed_pm: Optional[QPixmap] = None,
    ):
        self._normal_icon = QIcon(normal_pm)
        self._hover_icon = QIcon(hover_pm)
        self._pressed_icon = QIcon(pressed_pm) if pressed_pm else self._hover_icon
        self.setIcon(self._hover_icon if self.underMouse() else self._normal_icon)

    def enterEvent(self, event):
        self.setIcon(self._hover_icon)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setIcon(self._normal_icon)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setIcon(self._pressed_icon)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setIcon(self._hover_icon if self.underMouse() else self._normal_icon)
        super().mouseReleaseEvent(event)


class MiniWaveformCapsule(QFrame):
    """Pill-shaped top status capsule with mini dynamic wave animation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusCapsule")
        self.setFixedHeight(30)
        self.setMinimumWidth(160)
        self._text = "System Online"
        self._state = "ONLINE"
        self._phase = 0.0
        self._amplitude = 0.0

        # Animation timer
        self._timer = QTimer(self)
        self._timer.setInterval(45)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def set_status(self, text: str, state: str = "ONLINE"):
        self._text = text
        self._state = state
        self.update()

    def set_audio_amplitude(self, amp: float):
        self._amplitude = max(0.0, min(1.0, amp))
        self.update()

    def _tick(self):
        self._phase += 0.25
        self.update()

    def mousePressEvent(self, event):
        event.ignore()

    def mouseMoveEvent(self, event):
        event.ignore()

    def mouseDoubleClickEvent(self, event):
        event.ignore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()

        # Draw capsule pill background with reactive glow border
        border_alpha = int(100 + 155 * self._amplitude) if self._state in ("LISTENING", "PROCESSING") else 100
        border_pen = QPen(
            QColor(0, 255, 235 if self._state in ("LISTENING", "PROCESSING") else 210, border_alpha),
            1.5 if self._state in ("LISTENING", "PROCESSING") else 1.2,
        )
        painter.setPen(border_pen)
        painter.setBrush(QBrush(QColor(10, 22, 38, 215)))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 14, 14)

        # Reactive bottom pop-up arc line under capsule (HUD accent ONLY when voice is active)
        if self._amplitude > 0.12:
            arc_pen = QPen(QColor(0, 255, 235, int(220 * self._amplitude)), 1.5)
            painter.setPen(arc_pen)
            painter.drawArc(rect.adjusted(20, rect.height() - 4, -20, 4), 190 * 16, 160 * 16)

        # Draw mini sound wave bars on left
        bar_count = 5
        start_x = 18
        center_y = rect.center().y()

        painter.setPen(Qt.NoPen)
        color = QColor(theme.CYAN_ACCENT) if self._state != "LISTENING" else QColor("#00ffea")
        painter.setBrush(QBrush(color))

        for i in range(bar_count):
            import math
            if self._amplitude > 0.08:
                h = min(20.0, 4.0 + (12.0 * self._amplitude + 4.0) * abs(math.sin(self._phase + i * 0.8)))
            else:
                h = 3.5  # Calm resting bar height when quiet
            bx = start_x + i * 4
            painter.drawRoundedRect(bx, center_y - h / 2, 2.5, h, 1, 1)

        # Draw status text
        painter.setPen(QPen(QColor(theme.TEXT_PRIMARY)))
        font = QFont("Rajdhani", 10, QFont.Bold)
        painter.setFont(font)
        painter.drawText(
            rect.adjusted(start_x + bar_count * 4 + 8, 0, -10, 0),
            Qt.AlignVCenter | Qt.AlignLeft,
            self._text,
        )


class JarvisTitleBar(QWidget):
    """
    Top frameless title bar supporting drag-to-move, double-click maximize,
    and futuristic HUD controls with professional vector geometry.
    """

    minimize_requested = Signal()
    maximize_requested = Signal()
    close_requested = Signal()
    sidebar_toggle_requested = Signal()
    view_options_toggle_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self._drag_pos = QPoint()
        self._is_maximized = False

        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(12)

        # Sidebar hamburger toggle
        self.sidebar_toggle_btn = HUDIconButton(
            _make_hamburger_icon(theme.CYAN_ACCENT, 18),
            _make_hamburger_icon("#ffffff", 18),
            parent=self,
        )
        self.sidebar_toggle_btn.setIconSize(QSize(18, 18))
        self.sidebar_toggle_btn.setFixedSize(32, 32)
        self.sidebar_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.sidebar_toggle_btn.setToolTip("Show/hide navigation")
        self.sidebar_toggle_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 16px; }"
            "QPushButton:hover { background: rgba(0, 210, 255, 0.15); }"
        )
        self.sidebar_toggle_btn.clicked.connect(self.sidebar_toggle_requested.emit)
        layout.addWidget(self.sidebar_toggle_btn)

        # View-options toggle (System Status & Quick Actions)
        self.view_options_btn = HUDIconButton(
            _make_panels_icon(theme.CYAN_ACCENT, 16),
            _make_panels_icon("#ffffff", 16),
            parent=self,
        )
        self.view_options_btn.setIconSize(QSize(16, 16))
        self.view_options_btn.setFixedSize(32, 32)
        self.view_options_btn.setCursor(Qt.PointingHandCursor)
        self.view_options_btn.setToolTip("Show/hide System Status & Quick Actions")
        self.view_options_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 16px; }"
            "QPushButton:hover { background: rgba(0, 210, 255, 0.15); }"
        )
        self.view_options_btn.clicked.connect(self.view_options_toggle_requested.emit)
        layout.addWidget(self.view_options_btn)

        # Left: Holographic Logo & Title
        logo_layout = QHBoxLayout()
        logo_layout.setSpacing(10)

        # Arc Reactor Logo
        self.logo_widget = QLabel()
        self.logo_widget.setFixedSize(32, 32)
        self.logo_widget.setPixmap(_make_reactor_logo(theme.CYAN_ACCENT, 32))
        self.logo_widget.setAlignment(Qt.AlignCenter)
        self.logo_widget.setStyleSheet("background: transparent; border: none;")

        title_col = QHBoxLayout()
        title_col.setSpacing(8)

        self.title_label = QLabel("JARVIS")
        font_title = QFont("Orbitron", 13, QFont.Bold)
        font_title.setLetterSpacing(QFont.AbsoluteSpacing, 2.0)
        self.title_label.setFont(font_title)
        self.title_label.setStyleSheet("color: #ffffff; background: transparent;")

        self.subtitle_label = QLabel("YOUR PERSONAL AI ASSISTANT")
        font_sub = QFont("Rajdhani", 8.5, QFont.Bold)
        font_sub.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
        self.subtitle_label.setFont(font_sub)
        self.subtitle_label.setStyleSheet(f"color: {theme.TEXT_MUTED}; background: transparent; padding-top: 2px;")

        title_col.addWidget(self.title_label)
        title_col.addWidget(self.subtitle_label)

        logo_layout.addWidget(self.logo_widget)
        logo_layout.addLayout(title_col)

        layout.addLayout(logo_layout)
        layout.addStretch(1)

        # Center: Animated Status Capsule pinned at exact 50% horizontal center
        self.status_capsule = MiniWaveformCapsule(self)
        self.status_capsule.setFixedSize(166, 30)

        # Right: Quick Controls & Window Actions
        right_layout = QHBoxLayout()
        right_layout.setSpacing(6)

        # Professional Vector Notification Bell Button
        self.bell_btn = HUDIconButton(
            _make_bell_icon("#8da3c0", 18),
            _make_bell_icon(theme.CYAN_ACCENT, 18),
            parent=self,
        )
        self.bell_btn.setIconSize(QSize(18, 18))
        self.bell_btn.setFixedSize(32, 32)
        self.bell_btn.setCursor(Qt.PointingHandCursor)
        self.bell_btn.setToolTip("System Notifications")
        self.bell_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 16px; }"
            "QPushButton:hover { background: rgba(0, 210, 255, 0.15); }"
        )

        # Professional Vector Wifi / Signal Indicator
        self.wifi_btn = HUDIconButton(
            _make_wifi_icon("#8da3c0", 18),
            _make_wifi_icon(theme.CYAN_ACCENT, 18),
            parent=self,
        )
        self.wifi_btn.setIconSize(QSize(18, 18))
        self.wifi_btn.setFixedSize(32, 32)
        self.wifi_btn.setCursor(Qt.PointingHandCursor)
        self.wifi_btn.setToolTip("Neural Telemetry: Connected (100% Signal)")
        self.wifi_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 16px; }"
            "QPushButton:hover { background: rgba(0, 210, 255, 0.15); }"
        )

        # Professional Vector Cyber Dark Theme / Mode Toggle
        self.theme_btn = HUDIconButton(
            _make_theme_icon("#8da3c0", 18),
            _make_theme_icon(theme.CYAN_ACCENT, 18),
            parent=self,
        )
        self.theme_btn.setIconSize(QSize(18, 18))
        self.theme_btn.setFixedSize(32, 32)
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.setToolTip("Cyber Dark HUD Mode")
        self.theme_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 16px; }"
            "QPushButton:hover { background: rgba(0, 210, 255, 0.15); }"
        )

        right_layout.addWidget(self.bell_btn)
        right_layout.addWidget(self.wifi_btn)
        right_layout.addWidget(self.theme_btn)

        # Sleek vertical separator before window control buttons
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFixedSize(1, 16)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.15); margin: 0 4px;")
        right_layout.addWidget(sep)

        # Window Controls: Minimize, Maximize/Restore, Close
        self.btn_min = HUDIconButton(
            _make_minimize_icon("#8da3c0", 16),
            _make_minimize_icon("#ffffff", 16),
            parent=self,
        )
        self.btn_min.setIconSize(QSize(16, 16))
        self.btn_min.setFixedSize(36, 28)
        self.btn_min.setCursor(Qt.PointingHandCursor)
        self.btn_min.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 4px; }"
            "QPushButton:hover { background-color: rgba(255, 255, 255, 0.12); }"
        )
        self.btn_min.clicked.connect(self.minimize_requested.emit)

        self.btn_max = HUDIconButton(
            _make_maximize_icon("#8da3c0", 16, False),
            _make_maximize_icon("#ffffff", 16, False),
            parent=self,
        )
        self.btn_max.setIconSize(QSize(16, 16))
        self.btn_max.setFixedSize(36, 28)
        self.btn_max.setCursor(Qt.PointingHandCursor)
        self.btn_max.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 4px; }"
            "QPushButton:hover { background-color: rgba(255, 255, 255, 0.12); }"
        )
        self.btn_max.clicked.connect(self.maximize_requested.emit)

        self.btn_close = HUDIconButton(
            _make_close_icon("#8da3c0", 16),
            _make_close_icon("#ffffff", 16),
            parent=self,
        )
        self.btn_close.setIconSize(QSize(16, 16))
        self.btn_close.setFixedSize(36, 28)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 4px; }"
            "QPushButton:hover { background-color: #e81123; }"
        )
        self.btn_close.clicked.connect(self.close_requested.emit)

        right_layout.addWidget(self.btn_min)
        right_layout.addWidget(self.btn_max)
        right_layout.addWidget(self.btn_close)

        layout.addLayout(right_layout)

    def set_maximized_state(self, is_maximized: bool):
        """Updates the maximize/restore icon geometry dynamically."""
        self._is_maximized = is_maximized
        self.btn_max.set_icon_pixmaps(
            _make_maximize_icon("#8da3c0", 16, is_maximized),
            _make_maximize_icon("#ffffff", 16, is_maximized),
        )

    def set_capsule_status(self, text: str, state: str = "ONLINE"):
        self.status_capsule.set_status(text, state)

    def set_audio_amplitude(self, amp: float):
        self.status_capsule.set_audio_amplitude(amp)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_capsule()

    def showEvent(self, event):
        super().showEvent(event)
        self._reposition_capsule()

    def _reposition_capsule(self):
        if hasattr(self, "status_capsule") and self.status_capsule:
            w = self.status_capsule.width()
            h = self.status_capsule.height()
            x = (self.width() - w) // 2
            y = (self.height() - h) // 2
            self.status_capsule.setGeometry(x, y, w, h)
            self.status_capsule.raise_()

    # Window Drag Handling
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            parent_window = self.window()
            if parent_window:
                self._drag_pos = event.globalPosition().toPoint() - parent_window.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self._drag_pos.isNull():
            parent_window = self.window()
            if parent_window and not parent_window.isMaximized():
                parent_window.move(event.globalPosition().toPoint() - self._drag_pos)
                event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.maximize_requested.emit()
            event.accept()
