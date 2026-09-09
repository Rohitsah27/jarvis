"""
Dynamic Audio Waveform Visualizer.
Draws animated multi-frequency audio bars reacting to VoiceEngine activity.
"""
import math
import random
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient
from ui.styles.theme import theme


class WaveformWidget(QWidget):
    """Audio visualizer widget showing oscillating spectral bars."""

    def __init__(self, bar_count: int = 16, parent=None):
        super().__init__(parent)
        self.bar_count = bar_count
        self.setFixedHeight(36)
        self.setMinimumWidth(80)

        self._active = False
        self._amplitude = 0.1
        self._phase = 0.0

        # Animation timer
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def set_active(self, active: bool):
        self._active = active
        self.update()

    def set_amplitude(self, amp: float):
        self._amplitude = max(0.05, min(1.0, amp))
        self.update()

    def _tick(self):
        self._phase += 0.2
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cy = h / 2.0

        bar_w = max(2.5, (w - (self.bar_count * 3.0)) / float(self.bar_count))
        gap = 3.0

        painter.setPen(Qt.NoPen)

        for i in range(self.bar_count):
            if self._active:
                # Dynamic sinusoidal motion scaled by amplitude
                freq = math.sin(self._phase + i * 0.45)
                bar_h = max(4.0, (h * 0.8) * abs(freq) * (0.3 + 0.7 * self._amplitude))
            else:
                # Idle subtle breathing
                bar_h = 3.0 + 2.0 * math.sin(self._phase * 0.5 + i * 0.3)

            x = i * (bar_w + gap)
            y = cy - (bar_h / 2.0)

            # Gradient from electric cyan to blue
            grad = QLinearGradient(x, y, x, y + bar_h)
            grad.setColorAt(0.0, QColor(theme.CYAN_BRIGHT))
            grad.setColorAt(1.0, QColor("#0066ff"))

            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(x, y, bar_w, bar_h, 1.5, 1.5)
