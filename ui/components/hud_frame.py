"""
HudCornerFrame — a drop-in QFrame replacement that adds sci-fi HUD-style
corner brackets on top of whatever QSS background/border styling is already
applied via setStyleSheet(). Used to give the dashboard's card panels the
same "targeting frame" look as the central AI core widget, without changing
any existing layout or styling code — just swap QFrame() for
HudCornerFrame() and everything else (setStyleSheet, layouts, child widgets)
works exactly as before.
"""
from PySide6.QtWidgets import QFrame
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QColor, QPen

from ui.styles.theme import theme


class HudCornerFrame(QFrame):
    """QFrame with animated-free corner brackets drawn over its own
    QSS-styled background. Bracket color/opacity can be tuned via
    set_accent_color(); defaults to the theme's cyan accent."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._accent = QColor(theme.CYAN_ACCENT)
        self._arm = 14.0
        self._margin = 1.0

    def set_accent_color(self, color: QColor):
        self._accent = color
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        m = self._margin
        arm = self._arm

        pen = QPen(QColor(self._accent.red(), self._accent.green(), self._accent.blue(), 190), 1.6)
        pen.setCapStyle(Qt.FlatCap)
        painter.setPen(pen)

        corners = [
            (m, m, 1, 1),
            (w - m, m, -1, 1),
            (m, h - m, 1, -1),
            (w - m, h - m, -1, -1),
        ]
        for cx, cy, dx, dy in corners:
            painter.drawLine(QPointF(cx, cy), QPointF(cx + arm * dx, cy))
            painter.drawLine(QPointF(cx, cy), QPointF(cx, cy + arm * dy))
