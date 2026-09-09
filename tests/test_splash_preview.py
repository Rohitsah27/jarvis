import sys
import os
import math
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QLinearGradient, QRadialGradient,
    QFont, QPainterPath, QGuiApplication
)
from PySide6.QtWidgets import QWidget, QApplication, QGraphicsOpacityEffect

class JarvisSplashScreen(QWidget):
    """Futuristic Sci-Fi Holographic Splash Screen for JARVIS."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.SplashScreen
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.setFixedSize(620, 380)

        # Center on screen
        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            self.move(
                (geo.width() - self.width()) // 2,
                (geo.height() - self.height()) // 2
            )

        self._progress = 0
        self._status_text = "INITIALIZING CORE SUBSYSTEMS..."
        self._rotation_angle = 0.0
        self._pulse_phase = 0.0

        # Opacity effect for smooth fade out
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)
        self._fade_anim = None

        # Animation timer (30 FPS)
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

    def _on_tick(self):
        self._rotation_angle = (self._rotation_angle + 2.5) % 360.0
        self._pulse_phase = (self._pulse_phase + 0.08) % (2.0 * math.pi)
        self.update()

    def set_progress(self, percent: int, status: str = ""):
        self._progress = max(0, min(100, percent))
        if status:
            self._status_text = status.upper()
        self.update()
        QApplication.processEvents()

    def finish(self, window: QWidget):
        if window:
            window.show()
            window.raise_()
            window.activateWindow()

        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(450)
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._fade_anim.finished.connect(self._on_finished)
        self._fade_anim.start()

    def _on_finished(self):
        self._timer.stop()
        self.close()
        self.deleteLater()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        w, h = self.width(), self.height()

        # 1. Background Panel with Glassmorphism
        bg_path = QPainterPath()
        bg_path.addRoundedRect(QRectF(1, 1, w - 2, h - 2), 16, 16)

        # Deep sci-fi radial glow
        bg_grad = QRadialGradient(w / 2, h / 2 - 30, w * 0.7)
        bg_grad.setColorAt(0.0, QColor(9, 20, 36, 250))
        bg_grad.setColorAt(0.6, QColor(4, 10, 20, 252))
        bg_grad.setColorAt(1.0, QColor(2, 6, 12, 255))
        p.fillPath(bg_path, QBrush(bg_grad))

        # Glowing cyan border
        p.setPen(QPen(QColor(0, 210, 255, 70), 1.5))
        p.drawPath(bg_path)

        # Subtle scanline overlay
        p.setPen(QPen(QColor(0, 210, 255, 7), 1))
        for y_line in range(12, h - 12, 4):
            p.drawLine(14, y_line, w - 14, y_line)

        # 2. Cybernetic Corner Accents
        corner_len = 16
        c_pen = QPen(QColor(0, 217, 255, 230), 2.0)
        p.setPen(c_pen)
        # Top-Left
        p.drawLine(16, 28, 16, 16)
        p.drawLine(16, 16, 28, 16)
        # Top-Right
        p.drawLine(w - 28, 16, w - 16, 16)
        p.drawLine(w - 16, 16, w - 16, 28)
        # Bottom-Left
        p.drawLine(16, h - 28, 16, h - 16)
        p.drawLine(16, h - 16, 28, h - 16)
        # Bottom-Right
        p.drawLine(w - 28, h - 16, w - 16, h - 16)
        p.drawLine(w - 16, h - 16, w - 16, h - 28)

        # 3. Holographic Arc Reactor (Center x=w/2, y=105)
        cx, cy = w / 2, 105
        pulse = 0.5 + 0.5 * math.sin(self._pulse_phase)

        p.save()
        p.translate(cx, cy)

        # Ambient Core Glow
        glow_grad = QRadialGradient(0, 0, 65)
        glow_grad.setColorAt(0.0, QColor(0, 217, 255, int(40 + 35 * pulse)))
        glow_grad.setColorAt(0.5, QColor(0, 150, 255, int(15 + 15 * pulse)))
        glow_grad.setColorAt(1.0, QColor(0, 217, 255, 0))
        p.setBrush(QBrush(glow_grad))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(0, 0), 65, 65)

        # Outer Dashed Ring (Clockwise)
        p.save()
        p.rotate(self._rotation_angle)
        dash_pen = QPen(QColor(0, 217, 255, 180), 1.5, Qt.CustomDashLine)
        dash_pen.setDashPattern([5, 7])
        p.setPen(dash_pen)
        p.drawEllipse(QPointF(0, 0), 48, 48)
        p.restore()

        # Middle Segmented Ring (Counter-Clockwise)
        p.save()
        p.rotate(-self._rotation_angle * 1.4)
        arc_pen = QPen(QColor(104, 244, 255, 220), 2.2)
        p.setPen(arc_pen)
        for i in range(3):
            p.drawArc(QRectF(-36, -36, 72, 72), int((i * 120 + 15) * 16), int(75 * 16))
        p.restore()

        # Inner Accent Ring
        p.setPen(QPen(QColor(0, 217, 255, int(120 + 80 * pulse)), 1.2))
        p.drawEllipse(QPointF(0, 0), 24, 24)

        # Arc Reactor Spokes (3 triangular ticks)
        p.save()
        p.rotate(self._rotation_angle * 0.5)
        p.setPen(QPen(QColor(0, 217, 255, 200), 1.5))
        for _ in range(3):
            p.drawLine(0, -14, 0, -23)
            p.rotate(120)
        p.restore()

        # Center Reactor Core Light
        core_grad = QRadialGradient(0, 0, 14)
        core_grad.setColorAt(0.0, QColor(255, 255, 255, 255))
        core_grad.setColorAt(0.4, QColor(104, 244, 255, int(200 + 55 * pulse)))
        core_grad.setColorAt(1.0, QColor(0, 180, 255, 0))
        p.setBrush(QBrush(core_grad))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(0, 0), 13 + pulse * 2, 13 + pulse * 2)

        p.restore()

        # 4. Typography
        # Title "J . A . R . V . I . S"
        title_font = QFont("Orbitron", 22, QFont.Bold)
        title_font.setLetterSpacing(QFont.AbsoluteSpacing, 6)
        p.setFont(title_font)
        p.setPen(QColor(234, 248, 255))
        p.drawText(QRectF(0, 182, w, 32), Qt.AlignCenter, "J . A . R . V . I . S")

        # Subtitle
        sub_font = QFont("Rajdhani", 10, QFont.Bold)
        sub_font.setLetterSpacing(QFont.AbsoluteSpacing, 3)
        p.setFont(sub_font)
        p.setPen(QColor(0, 210, 255, 220))
        p.drawText(QRectF(0, 216, w, 20), Qt.AlignCenter, "MARK VII // NEURAL OPERATING SYSTEM")

        tag_font = QFont("Rajdhani", 8, QFont.Normal)
        tag_font.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
        p.setFont(tag_font)
        p.setPen(QColor(80, 101, 128))
        p.drawText(QRectF(0, 236, w, 18), Qt.AlignCenter, "JUST A RATHER VERY INTELLIGENT SYSTEM")

        # 5. Progress Status & Bar
        bar_x = 70
        bar_y = 282
        bar_w = w - 140
        bar_h = 5

        # Status text (left)
        stat_font = QFont("Rajdhani", 9, QFont.Bold)
        stat_font.setLetterSpacing(QFont.AbsoluteSpacing, 1)
        p.setFont(stat_font)
        p.setPen(QColor(141, 163, 192))
        p.drawText(QRectF(bar_x, bar_y - 20, bar_w - 70, 18), Qt.AlignLeft | Qt.AlignVCenter, f"> {self._status_text}")

        # Percentage (right)
        pct_font = QFont("Orbitron", 9, QFont.Bold)
        p.setFont(pct_font)
        p.setPen(QColor(0, 217, 255))
        p.drawText(QRectF(bar_x + bar_w - 70, bar_y - 20, 70, 18), Qt.AlignRight | Qt.AlignVCenter, f"[ {self._progress}% ]")

        # Bar Track
        track_path = QPainterPath()
        track_path.addRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), bar_h / 2, bar_h / 2)
        p.fillPath(track_path, QBrush(QColor(8, 19, 32)))
        p.setPen(QPen(QColor(0, 210, 255, 45), 1))
        p.drawPath(track_path)

        # Bar Fill
        fill_w = max(4.0, bar_w * (self._progress / 100.0))
        fill_path = QPainterPath()
        fill_path.addRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h), bar_h / 2, bar_h / 2)
        bar_grad = QLinearGradient(bar_x, 0, bar_x + fill_w, 0)
        bar_grad.setColorAt(0.0, QColor(0, 122, 153))
        bar_grad.setColorAt(0.7, QColor(0, 210, 255))
        bar_grad.setColorAt(1.0, QColor(104, 244, 255))
        p.fillPath(fill_path, QBrush(bar_grad))

        # Glow Head Dot
        head_x = bar_x + fill_w
        head_grad = QRadialGradient(head_x, bar_y + bar_h / 2, 7)
        head_grad.setColorAt(0.0, QColor(255, 255, 255, 255))
        head_grad.setColorAt(0.4, QColor(0, 217, 255, 220))
        head_grad.setColorAt(1.0, QColor(0, 217, 255, 0))
        p.setBrush(QBrush(head_grad))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(head_x, bar_y + bar_h / 2), 6, 6)

        # 6. Bottom System Badges
        footer_font = QFont("Rajdhani", 8, QFont.Medium)
        footer_font.setLetterSpacing(QFont.AbsoluteSpacing, 1)
        p.setFont(footer_font)
        p.setPen(QColor(58, 79, 102))
        p.drawText(QRectF(24, h - 28, 300, 16), Qt.AlignLeft | Qt.AlignVCenter, "KERNEL: v1.3.2-PROD  //  ENCRYPTION: AES-256")

        p.setPen(QColor(0, 255, 157, 220))
        p.drawText(QRectF(w - 200, h - 28, 176, 16), Qt.AlignRight | Qt.AlignVCenter, "CORE: ONLINE  ●")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    splash = JarvisSplashScreen()
    splash.show()
    
    # Simulate loading steps
    steps = [
        (15, "INITIALIZING NEURAL RUNTIME..."),
        (35, "LOADING KOKORO NEURAL TTS..."),
        (55, "CALIBRATING FASTER-WHISPER STT..."),
        (75, "SYNCHRONIZING CYBERNETIC HUD..."),
        (90, "CONNECTING SYSTEM TELEMETRY..."),
        (100, "ALL SYSTEMS OPERATIONAL. READY.")
    ]
    
    step_idx = 0
    def next_step():
        global step_idx
        if step_idx < len(steps):
            pct, msg = steps[step_idx]
            splash.set_progress(pct, msg)
            step_idx += 1
        else:
            timer.stop()
            print("Finished preview successfully!")
            splash.finish(None)
            QTimer.singleShot(600, app.quit)

    timer = QTimer()
    timer.timeout.connect(next_step)
    timer.start(400)

    sys.exit(app.exec())
