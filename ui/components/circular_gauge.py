"""
Custom QPainter Circular Gauge Meter for System Status (CPU, RAM, Disk, Network).
Features smooth gradient stroke, track background, centered metric, and bottom label.
"""
import math
from typing import Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRectF, QPointF, QTimer
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QFont,
    QConicalGradient,
    QRadialGradient,
)
from ui.styles.theme import theme


class CircularGaugeWidget(QWidget):
    """Circular progress meter with percentage and label."""

    def __init__(
        self,
        label: str,
        initial_value: float = 0.0,
        unit: str = "%",
        icon_str: Optional[str] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.label = label
        self.unit = unit
        self.icon_str = icon_str

        self._current_value = initial_value
        self._target_value = initial_value
        self._glow_phase = 0.0

        self.setFixedSize(76, 96)

        # Smooth interpolation timer
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(30)
        self._anim_timer.timeout.connect(self._interpolate_value)

        # Always-on subtle breathing glow + leading-edge cursor, independent
        # of value changes so the gauge feels "alive" even at rest instead
        # of only animating when a new reading comes in.
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(33)
        self._pulse_timer.timeout.connect(self._pulse_tick)
        self._pulse_timer.start()

    def set_value(self, val: float):
        self._target_value = max(0.0, min(100.0, float(val)))
        if not self._anim_timer.isActive():
            self._anim_timer.start()

    def _interpolate_value(self):
        diff = self._target_value - self._current_value
        if abs(diff) < 0.3:
            self._current_value = self._target_value
            self._anim_timer.stop()
        else:
            self._current_value += diff * 0.25
        self.update()

    def _pulse_tick(self):
        self._glow_phase = (self._glow_phase + 0.05) % (math.pi * 2)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        gauge_size = 62.0
        x_offset = (w - gauge_size) / 2.0
        y_offset = 4.0
        gauge_rect = QRectF(x_offset, y_offset, gauge_size, gauge_size)
        center = QPointF(gauge_rect.center().x(), gauge_rect.center().y())
        ring_rect = gauge_rect.adjusted(3, 3, -3, -3)
        ring_radius = ring_rect.width() / 2.0

        val = self._current_value
        if val > 85:
            arc_color = QColor(theme.STATUS_ERROR)
        elif val > 70:
            arc_color = QColor(theme.STATUS_WARNING)
        else:
            arc_color = QColor(theme.CYAN_ACCENT)

        breathe = 0.75 + 0.25 * ((math.sin(self._glow_phase) + 1.0) / 2.0)

        # 1. Soft outer glow halo behind the whole dial, matching arc color
        glow_grad = QRadialGradient(center, ring_radius * 1.55)
        glow_grad.setColorAt(0.55, QColor(arc_color.red(), arc_color.green(), arc_color.blue(), int(26 * breathe)))
        glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(glow_grad))
        painter.drawEllipse(center, ring_radius * 1.55, ring_radius * 1.55)

        # 2. Fine tick marks around the dial, like an instrument bezel
        tick_count = 30
        for i in range(tick_count):
            a = math.radians(i * (360.0 / tick_count) - 90)
            is_major = (i % 5 == 0)
            tick_len = 4.5 if is_major else 2.0
            r1 = ring_radius + 4.0
            r2 = r1 + tick_len
            x1, y1 = center.x() + r1 * math.cos(a), center.y() + r1 * math.sin(a)
            x2, y2 = center.x() + r2 * math.cos(a), center.y() + r2 * math.sin(a)
            tick_color = QColor(theme.CYAN_ACCENT) if is_major else QColor(70, 95, 125)
            tick_color.setAlpha(150 if is_major else 90)
            painter.setPen(QPen(tick_color, 1.1 if is_major else 0.8))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # 3. Background Track Arc (Darker Ring)
        track_pen = QPen(QColor(18, 30, 50), 5.0)
        track_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(track_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(ring_rect)

        # 4. Dynamic Progress Arc (conical gradient for an "energy flow" look
        # instead of a single flat color)
        start_angle = 90 * 16
        span_deg = (val / 100.0) * 360.0
        span_angle = int(-span_deg * 16)

        arc_gradient = QConicalGradient(center, 90)
        dim = QColor(arc_color.red(), arc_color.green(), arc_color.blue(), 90)
        bright = QColor(arc_color.red(), arc_color.green(), arc_color.blue(), 255)
        arc_gradient.setColorAt(0.0, dim)
        arc_gradient.setColorAt(min(1.0, max(0.001, span_deg / 360.0)), bright)
        arc_gradient.setColorAt(1.0, dim)

        progress_pen = QPen(QBrush(arc_gradient), 5.0)
        progress_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(progress_pen)
        painter.drawArc(ring_rect, start_angle, span_angle)

        # 5. Bright pulsing cursor dot at the arc's leading edge
        if val > 0.5:
            end_angle_rad = math.radians(90 - span_deg)
            cx = center.x() + ring_radius * math.cos(end_angle_rad)
            cy = center.y() - ring_radius * math.sin(end_angle_rad)
            cursor_glow = QRadialGradient(QPointF(cx, cy), 6.0 * breathe)
            cursor_glow.setColorAt(0.0, QColor(255, 255, 255, int(230 * breathe)))
            cursor_glow.setColorAt(0.4, QColor(arc_color.red(), arc_color.green(), arc_color.blue(), int(180 * breathe)))
            cursor_glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(cursor_glow))
            painter.drawEllipse(QPointF(cx, cy), 6.0 * breathe, 6.0 * breathe)

        # 6. Center Value Text
        painter.setPen(QPen(QColor("#ffffff")))
        val_font = QFont(theme.FONT_FAMILY, 10, QFont.Bold)
        painter.setFont(val_font)

        if self.icon_str and val >= 99.0:
            # Special icon display (e.g. WiFi)
            painter.drawText(gauge_rect, Qt.AlignCenter, self.icon_str)
        else:
            painter.drawText(gauge_rect, Qt.AlignCenter, f"{int(round(val))}{self.unit}")

        # 4. Bottom Label
        painter.setPen(QPen(QColor(theme.TEXT_SECONDARY)))
        lbl_font = QFont(theme.FONT_FAMILY, 9)
        painter.setFont(lbl_font)
        label_rect = QRectF(0, gauge_size + 8, w, 20)
        painter.drawText(label_rect, Qt.AlignCenter, self.label)
