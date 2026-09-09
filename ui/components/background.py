"""
High-Tech Cybernetic Background Widget for JARVIS HUD.
Renders ambient holographic radial core aura, cybernetic coordinate grid,
tactical corner reticles, and living ambient floating quantum particles.
"""
import random
import math
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPointF, QTimer
from PySide6.QtGui import QPainter, QRadialGradient, QColor, QPen, QBrush, QFont


class JarvisBackgroundWidget(QWidget):
    """
    Futuristic HUD background canvas providing dynamic ambient lighting,
    subtle cybernetic lattice grid, and floating particles.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CentralWidget")
        self.setAttribute(Qt.WA_StyledBackground, False)

        # Ambient floating particle simulation
        self.particles = []
        for _ in range(45):
            self.particles.append({
                "x": random.uniform(0, 1920),
                "y": random.uniform(0, 1080),
                "speed": random.uniform(0.18, 0.48),
                "size": random.uniform(1.2, 2.6),
                "alpha": random.uniform(0.14, 0.48),
                "phase": random.uniform(0, math.pi * 2),
            })

        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._animate_particles)
        self._timer.start()

    def _animate_particles(self):
        w = max(100, self.width())
        h = max(100, self.height())
        for pt in self.particles:
            pt["y"] -= pt["speed"]
            pt["phase"] += 0.035
            pt["x"] += math.sin(pt["phase"]) * 0.28
            if pt["y"] < 0:
                pt["y"] = h
                pt["x"] = random.uniform(0, w)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # 1. Base Dark Canvas
        painter.fillRect(self.rect(), QColor("#060a12"))

        # 2. Central Holographic Core Glow (Directly behind the 3D HUD AI Core)
        grad = QRadialGradient(w * 0.5, h * 0.44, max(w, h) * 0.62)
        grad.setColorAt(0.0, QColor(0, 160, 240, 38))
        grad.setColorAt(0.28, QColor(0, 75, 150, 22))
        grad.setColorAt(0.60, QColor(2, 20, 50, 9))
        grad.setColorAt(1.0, QColor(6, 10, 18, 0))
        painter.fillRect(self.rect(), QBrush(grad))

        # 3. Fine Cybernetic Grid
        grid_pen = QPen(QColor(0, 210, 255, 9), 1)
        painter.setPen(grid_pen)
        step = 64
        for x in range(0, w, step):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, step):
            painter.drawLine(0, y, w, y)

        # Micro crosshairs at 128px intersections
        cross_pen = QPen(QColor(0, 210, 255, 30), 1)
        painter.setPen(cross_pen)
        for x in range(step, w, step * 2):
            for y in range(step, h, step * 2):
                painter.drawLine(x - 3, y, x + 3, y)
                painter.drawLine(x, y - 3, x, y + 3)

        # 4. Living Ambient Floating Particles
        painter.setPen(Qt.NoPen)
        for pt in self.particles:
            px = pt["x"] % w
            py = pt["y"] % h
            alpha = int(255 * (pt["alpha"] * (0.8 + 0.2 * math.sin(pt["phase"]))))
            painter.setBrush(QBrush(QColor(0, 210, 255, alpha)))
            painter.drawEllipse(QPointF(px, py), pt["size"], pt["size"])

        # 5. Tactical Corner HUD Micro-Brackets
        hud_pen = QPen(QColor(0, 210, 255, 40), 1)
        painter.setPen(hud_pen)

        # Top-left micro-bracket (subtle corner accent)
        painter.drawLine(14, 54, 28, 54)
        painter.drawLine(14, 54, 14, 68)
        # Top-right micro-bracket
        painter.drawLine(w - 28, 54, w - 14, 54)
        painter.drawLine(w - 14, 54, w - 14, 68)
        # Bottom-left micro-bracket
        painter.drawLine(14, h - 16, 28, h - 16)
        painter.drawLine(14, h - 16, 14, h - 30)
        # Bottom-right micro-bracket
        painter.drawLine(w - 28, h - 16, w - 14, h - 16)
        painter.drawLine(w - 14, h - 16, w - 14, h - 30)

        # Bottom subtle telemetry coordinates
        painter.setFont(QFont("Rajdhani", 7, QFont.Bold))
        painter.setPen(QPen(QColor(0, 210, 255, 35)))
        painter.drawText(34, h - 19, "LOC // 28.61° N, 77.20° E")
        painter.drawText(w - 120, h - 19, "FREQ // 60.0 HZ")

        painter.end()
