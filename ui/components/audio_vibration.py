"""
Futuristic Cybernetic Audio Vibration Visualizer Widget.

Renders multi-band holographic equalizer spectrum bars, floating peak-hold laser
caps, dual-harmonic glowing oscilloscope ribbons, and HUD telemetry in the sloped
triangular spaces flanking the central JARVIS holographic dial (bottom-left & bottom-right).
Reacts dynamically in real-time to speech amplitude when speaking.
"""
import math
import random
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QLinearGradient,
    QPainterPath,
    QFont,
    QFontMetrics,
)
from ui.styles.theme import theme


class JarvisAudioVibrationWidget(QWidget):
    """
    Sloped cybernetic audio vibration visualizer.
    side='left':  Envelope peaks on the outer left edge and slopes down towards the dial on the right.
    side='right': Envelope slopes up from the dial on the left towards the outer right edge.
    """

    def __init__(self, side: str = "left", parent=None):
        super().__init__(parent)
        self.side = side.lower()
        self.setMinimumSize(220, 140)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self._active = False
        self._target_amp = 0.0
        self._current_amp = 0.0
        self._phase = random.uniform(0, 10)

        # 28 frequency equalizer bands
        self.num_bars = 28
        self._bar_heights = [0.0] * self.num_bars
        self._peak_heights = [0.0] * self.num_bars
        self._peak_decay = [0.0] * self.num_bars

        # Random resonance frequencies per band for organic FFT-like motion
        self._freq_seeds = [random.uniform(0.8, 1.4) for _ in range(self.num_bars)]
        self._phase_offsets = [random.uniform(0, math.pi * 2) for _ in range(self.num_bars)]

        # 60 FPS animation loop
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def set_active(self, active: bool):
        self._active = active
        self.update()

    def set_amplitude(self, amp: float):
        """Sets real-time audio amplitude (0.0 to 1.0)."""
        self._target_amp = max(0.0, min(1.0, float(amp)))

    def _tick(self):
        self._phase += 0.08

        # Asymmetric attack & decay for punchy, responsive voice reaction
        if self._target_amp > self._current_amp:
            self._current_amp += (self._target_amp - self._current_amp) * 0.60
        else:
            self._current_amp += (self._target_amp - self._current_amp) * 0.12
            self._target_amp *= 0.94

        # Damped clamp
        self._current_amp = max(0.0, min(1.0, self._current_amp))

        # Update each bar height with physical envelope and harmonic resonance
        for i in range(self.num_bars):
            t = i / float(self.num_bars - 1)

            # Asymmetric slope envelope matching user sketch
            if self.side == "left":
                # High on the left (t=0), slopes down towards dial on the right (t=1)
                env = 0.14 + 0.86 * math.pow(1.0 - t, 1.25)
            else:
                # Low near dial on left (t=0), rises to peak on the right (t=1)
                env = 0.14 + 0.86 * math.pow(t, 1.25)

            # Harmonic multi-frequency oscillation
            s1 = math.sin(self._phase * (14.0 * self._freq_seeds[i]) + self._phase_offsets[i])
            s2 = math.sin(self._phase * (24.0 / self._freq_seeds[i]) + i * 0.85)
            harmonic = 0.45 + 0.35 * s1 + 0.20 * s2

            # Idle baseline ripple (subtle 3px breathing wave when silent)
            idle_val = 0.05 + 0.03 * math.sin(self._phase * 1.5 + i * 0.4) * env

            # Speech dynamic vibration value
            voice_val = self._current_amp * harmonic * env

            target_h = max(idle_val, voice_val)
            self._bar_heights[i] += (target_h - self._bar_heights[i]) * 0.45

            # Peak hold indicator physics
            if self._bar_heights[i] >= self._peak_heights[i]:
                self._peak_heights[i] = self._bar_heights[i]
                self._peak_decay[i] = 0.002
            else:
                self._peak_heights[i] -= self._peak_decay[i]
                self._peak_decay[i] += 0.001
                if self._peak_heights[i] < self._bar_heights[i]:
                    self._peak_heights[i] = self._bar_heights[i]

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        w = float(self.width())
        h = float(self.height())

        pad_x = 10.0
        pad_y = 12.0
        avail_w = w - pad_x * 2.0
        avail_h = h - pad_y * 2.0

        # Base Y line where spectrum bars sit (above bottom telemetry text)
        base_y = h - 26.0
        max_bar_h = avail_h - 28.0

        # -------------------------------------------------------------
        # 1. Cybernetic Sloped Hull Background & Framing Reticles
        # -------------------------------------------------------------
        hull_path = QPainterPath()
        if self.side == "left":
            # Left side: high at x=pad_x, slopes down towards x=w-pad_x
            p_top_start = QPointF(pad_x + 14.0, pad_y + 4.0)
            p_top_peak = QPointF(pad_x + 38.0, pad_y + 4.0)
            p_top_slope = QPointF(w - pad_x - 8.0, base_y - max_bar_h * 0.18)
            p_bottom_right = QPointF(w - pad_x, base_y + 14.0)
            p_bottom_left = QPointF(pad_x, base_y + 14.0)

            hull_path.moveTo(pad_x, pad_y + 18.0)
            hull_path.lineTo(p_top_start)
            hull_path.lineTo(p_top_peak)
            hull_path.lineTo(p_top_slope)
            hull_path.lineTo(p_bottom_right)
            hull_path.lineTo(p_bottom_left)
            hull_path.closeSubpath()
        else:
            # Right side: slopes up from x=pad_x to high peak at x=w-pad_x
            p_top_slope = QPointF(pad_x + 8.0, base_y - max_bar_h * 0.18)
            p_top_peak = QPointF(w - pad_x - 38.0, pad_y + 4.0)
            p_top_end = QPointF(w - pad_x - 14.0, pad_y + 4.0)
            p_bottom_right = QPointF(w - pad_x, base_y + 14.0)
            p_bottom_left = QPointF(pad_x, base_y + 14.0)

            hull_path.moveTo(pad_x, base_y + 14.0)
            hull_path.lineTo(p_top_slope)
            hull_path.lineTo(p_top_peak)
            hull_path.lineTo(p_top_end)
            hull_path.lineTo(w - pad_x, pad_y + 18.0)
            hull_path.lineTo(p_bottom_right)
            hull_path.closeSubpath()

        # Background subtle ambient glow inside hull
        hull_grad = QLinearGradient(0, pad_y, 0, base_y + 14.0)
        is_speaking = self._current_amp > 0.03
        if is_speaking:
            hull_grad.setColorAt(0.0, QColor(0, 210, 255, 30))
            hull_grad.setColorAt(0.6, QColor(6, 18, 36, 65))
            hull_grad.setColorAt(1.0, QColor(4, 12, 24, 85))
        else:
            hull_grad.setColorAt(0.0, QColor(0, 210, 255, 12))
            hull_grad.setColorAt(0.6, QColor(4, 12, 24, 45))
            hull_grad.setColorAt(1.0, QColor(3, 8, 16, 60))

        painter.setBrush(QBrush(hull_grad))
        border_col = QColor(0, 210, 255, 95 if is_speaking else 45)
        painter.setPen(QPen(border_col, 1.0, Qt.DashLine if not is_speaking else Qt.SolidLine))
        painter.drawPath(hull_path)

        # Subtle Horizontal dB Guideline Ticks
        painter.setPen(QPen(QColor(0, 210, 255, 25), 1.0, Qt.DotLine))
        for frac in [0.25, 0.50, 0.75]:
            gy = base_y - max_bar_h * frac
            painter.drawLine(int(pad_x + 10), int(gy), int(w - pad_x - 10), int(gy))

        # -------------------------------------------------------------
        # 2. Equalizer Frequency Vibration Bars
        # -------------------------------------------------------------
        total_bar_w = avail_w - 20.0
        bar_w = max(3.0, (total_bar_w / float(self.num_bars)) - 3.0)
        gap = (total_bar_w - (bar_w * self.num_bars)) / float(self.num_bars - 1)
        start_x = pad_x + 10.0

        wave_pts = []

        painter.setPen(Qt.NoPen)
        for i in range(self.num_bars):
            bx = start_x + i * (bar_w + gap)
            val = self._bar_heights[i]
            bh = max(3.0, val * max_bar_h)
            by = base_y - bh

            center_x = bx + bar_w / 2.0
            wave_pts.append(QPointF(center_x, by))

            # Vertical bar gradient: deep cyan -> bright electric cyan -> white tip
            bar_grad = QLinearGradient(bx, base_y, bx, by)
            if is_speaking and val > 0.65:
                # Violet/magenta cyber surge at high amplitude
                bar_grad.setColorAt(0.0, QColor(0, 217, 255, 180))
                bar_grad.setColorAt(0.55, QColor(0, 240, 255, 230))
                bar_grad.setColorAt(0.85, QColor(192, 132, 252, 255))
                bar_grad.setColorAt(1.0, QColor(255, 255, 255, 255))
            else:
                bar_grad.setColorAt(0.0, QColor(0, 150, 255, 140))
                bar_grad.setColorAt(0.4, QColor(0, 210, 255, 200))
                bar_grad.setColorAt(0.85, QColor(104, 244, 255, 245))
                bar_grad.setColorAt(1.0, QColor(230, 255, 255, 255))

            painter.setBrush(QBrush(bar_grad))
            painter.drawRoundedRect(int(bx), int(by), int(bar_w), int(bh), 1.5, 1.5)

            # Peak-Hold Floating Laser Cap
            peak_val = self._peak_heights[i]
            peak_y = base_y - max(3.0, peak_val * max_bar_h) - 2.5
            cap_col = QColor(255, 255, 255, 230) if is_speaking else QColor(0, 240, 255, 160)
            painter.setBrush(QBrush(cap_col))
            painter.drawRoundedRect(int(bx), int(peak_y), int(bar_w), 1.8, 0.8, 0.8)

        # -------------------------------------------------------------
        # 3. Holographic Oscilloscope Waveform Ribbon Over Bars
        # -------------------------------------------------------------
        if len(wave_pts) >= 2:
            ribbon_path = QPainterPath()
            ribbon_path.moveTo(wave_pts[0])
            for i in range(1, len(wave_pts)):
                p0 = wave_pts[i - 1]
                p1 = wave_pts[i]
                cpx = (p0.x() + p1.x()) / 2.0
                ribbon_path.cubicTo(cpx, p0.y(), cpx, p1.y(), p1.x(), p1.y())

            # Subtle glow fill under the wave line
            fill_path = QPainterPath(ribbon_path)
            fill_path.lineTo(wave_pts[-1].x(), base_y)
            fill_path.lineTo(wave_pts[0].x(), base_y)
            fill_path.closeSubpath()

            wave_fill_grad = QLinearGradient(0, pad_y + 10, 0, base_y)
            fill_alpha = 45 if is_speaking else 18
            wave_fill_grad.setColorAt(0.0, QColor(0, 255, 234, fill_alpha))
            wave_fill_grad.setColorAt(0.8, QColor(0, 180, 255, int(fill_alpha * 0.4)))
            wave_fill_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(wave_fill_grad))
            painter.setPen(Qt.NoPen)
            painter.drawPath(fill_path)

            # Outer luminous neon stroke
            stroke_col = QColor(0, 255, 234, 240 if is_speaking else 120)
            painter.setPen(QPen(stroke_col, 1.8 if is_speaking else 1.2))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(ribbon_path)

            # Secondary harmonic wave (electric violet/sky cyan offset)
            if is_speaking:
                sec_path = QPainterPath()
                p0 = wave_pts[0]
                sec_path.moveTo(p0.x(), p0.y() + math.sin(self._phase * 3.0) * 4.0)
                for i in range(1, len(wave_pts)):
                    p = wave_pts[i]
                    offset = math.sin(self._phase * 3.5 + i * 0.6) * 6.0 * self._current_amp
                    sec_path.lineTo(p.x(), p.y() + offset)
                painter.setPen(QPen(QColor(168, 85, 247, 160), 1.2, Qt.DotLine))
                painter.drawPath(sec_path)

        # -------------------------------------------------------------
        # 4. HUD Telemetry & Frequency Markings
        # -------------------------------------------------------------
        font_badge = QFont("Orbitron", 7, QFont.Bold)
        font_badge.setStyleStrategy(QFont.PreferAntialias)
        painter.setFont(font_badge)

        # Baseline rule
        painter.setPen(QPen(QColor(0, 210, 255, 75), 1.0))
        painter.drawLine(int(pad_x + 8), int(base_y + 1), int(w - pad_x - 8), int(base_y + 1))

        # Bottom telemetry text
        font_sub = QFont("Rajdhani", 7.5, QFont.Bold)
        font_sub.setStyleStrategy(QFont.PreferAntialias)
        painter.setFont(font_sub)

        status_txt = "● VIBRATION ACTIVE" if is_speaking else "○ VIBRATION STANDBY"
        status_col = QColor(0, 255, 234) if is_speaking else QColor(100, 125, 155)

        if self.side == "left":
            # Top-left HUD badge
            painter.setFont(font_badge)
            painter.setPen(QColor(0, 210, 255, 200))
            painter.drawText(int(pad_x + 14), int(pad_y + 16), "∿ AUDIO SPECTRUM // CH-L")

            # Bottom info
            painter.setFont(font_sub)
            painter.setPen(status_col)
            painter.drawText(int(pad_x + 10), int(h - 8), status_txt)

            painter.setPen(QColor(120, 150, 180, 140))
            painter.drawText(int(w - pad_x - 80), int(h - 8), "88Hz — 4.2kHz")
        else:
            # Top-right HUD badge
            painter.setFont(font_badge)
            painter.setPen(QColor(0, 210, 255, 200))
            metrics = QFontMetrics(font_badge)
            tag = "CH-R // STEREO LINK ∿"
            tw = metrics.horizontalAdvance(tag)
            painter.drawText(int(w - pad_x - 14 - tw), int(pad_y + 16), tag)

            # Bottom info
            painter.setFont(font_sub)
            painter.setPen(QColor(120, 150, 180, 140))
            painter.drawText(int(pad_x + 10), int(h - 8), "4.2kHz — 22kHz")

            painter.setPen(status_col)
            metrics_sub = QFontMetrics(font_sub)
            sw = metrics_sub.horizontalAdvance(status_txt)
            painter.drawText(int(w - pad_x - 10 - sw), int(h - 8), status_txt)

        # High-tech Corner Accent Brackets
        painter.setPen(QPen(QColor(0, 210, 255, 180 if is_speaking else 80), 1.5))
        # Top-left bracket
        painter.drawLine(int(pad_x), int(pad_y + 6), int(pad_x + 8), int(pad_y + 6))
        painter.drawLine(int(pad_x), int(pad_y + 6), int(pad_x), int(pad_y + 14))

        # Bottom-right bracket
        painter.drawLine(int(w - pad_x - 8), int(h - pad_y), int(w - pad_x), int(h - pad_y))
        painter.drawLine(int(w - pad_x), int(h - pad_y - 8), int(w - pad_x), int(h - pad_y))
