"""
Central Holographic AI Core — dotted anatomical face variant.

Renders a circular HUD portal containing a dotted/wireframe frontal face
(eyebrows, eyes, nose, lips, jaw contour, ears) built from explicit facial
proportion anchor points, drawn via a Qt Quick Canvas (ui/qml/jarvis_face_scene.qml)
embedded in a QQuickWidget. This matches a reference "Iron Man style"
portrait more closely than a shaded 3D mesh does: that reference is a
precise 2D line-art face, and a shaded volumetric bust reads as a smooth
blob rather than crisp anatomy — so this is a 2D vector-art approach, not
a 3D one. An earlier iteration of this file rendered an actual glTF mesh
(tools/build_face_glb.py still builds that asset) via QtQuick3D; that
scene has been replaced but the exporter is left in place in case a
sourced/higher-fidelity 3D asset is swapped in later.

This is additive: ui.components.ai_core.JarvisAICore (the original
QPainter point-cloud version) is untouched, so anything importing it
directly keeps working exactly as before.
"""
import math
from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QColor
from PySide6.QtQuickWidgets import QQuickWidget

from ui.components.ai_core import AICoreState

_QML_PATH = Path(__file__).resolve().parent.parent / "qml" / "jarvis_face_scene.qml"

_STATE_COLORS = {
    AICoreState.IDLE: QColor(0, 210, 255),
    AICoreState.LISTENING: QColor(0, 255, 235),
    AICoreState.THINKING: QColor(190, 95, 255),
    AICoreState.SPEAKING: QColor(0, 230, 255),
    AICoreState.PROCESSING: QColor(0, 245, 255),
    AICoreState.OFFLINE: QColor(90, 110, 130),
}


class JarvisAICore3D(QWidget):
    """
    Drop-in replacement for JarvisAICore. Same public surface:
    set_state(), set_audio_amplitude(), constructor(parent).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 260)
        self.state = AICoreState.IDLE
        self._audio_amplitude = 0.0
        self._smoothed_amp = 0.0
        self._pulse_phase = 0.0
        self._scan_phase = 0.0

        self._quick_widget = QQuickWidget(self)
        self._quick_widget.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self._quick_widget.setSource(QUrl.fromLocalFile(str(_QML_PATH)))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._quick_widget)

        self._root_obj = self._quick_widget.rootObject()

        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._animation_tick)
        self._timer.start()

    def set_state(self, state: str):
        self.state = state

    def set_audio_amplitude(self, amp: float):
        self._audio_amplitude = max(0.0, min(1.0, amp))

    def _ring_speed(self) -> float:
        if self.state in (AICoreState.THINKING, AICoreState.PROCESSING):
            return 2.4
        elif self.state in (AICoreState.LISTENING, AICoreState.SPEAKING):
            return 1.5 * (1.0 + self._smoothed_amp * 1.5)
        elif self.state == AICoreState.OFFLINE:
            return 0.15
        return 1.0

    def _glow_mult(self, pulse: float) -> float:
        if self.state == AICoreState.IDLE:
            return 0.7 + 0.3 * pulse + self._smoothed_amp * 0.5
        elif self.state == AICoreState.LISTENING:
            return 0.9 + 0.25 * pulse + self._smoothed_amp * 0.7
        elif self.state == AICoreState.THINKING:
            return 0.85 + 0.3 * pulse
        elif self.state == AICoreState.SPEAKING:
            return 0.8 + self._smoothed_amp * 0.75
        elif self.state == AICoreState.PROCESSING:
            return 0.95
        return 0.2

    def _animation_tick(self):
        if self._audio_amplitude > self._smoothed_amp:
            self._smoothed_amp = self._audio_amplitude
        else:
            self._smoothed_amp = max(0.0, self._smoothed_amp * 0.82 - 0.01)

        ring_speed = self._ring_speed()
        self._pulse_phase += 0.045
        pulse = (math.sin(self._pulse_phase) + 1.0) / 2.0
        scan_speed = 0.006 * ring_speed if self.state != AICoreState.OFFLINE else 0.0015
        self._scan_phase = (self._scan_phase + scan_speed) % 1.0

        if self._root_obj is not None:
            scale_mod = 1.0 + 0.015 * math.sin(self._pulse_phase) + 0.03 * self._smoothed_amp
            color = _STATE_COLORS.get(self.state, QColor(0, 210, 255))
            self._root_obj.setProperty("pulseScale", scale_mod)
            self._root_obj.setProperty("accentColor", color.name())
            self._root_obj.setProperty("ringSpeedFactor", ring_speed)
            self._root_obj.setProperty("glowMult", self._glow_mult(pulse))
            self._root_obj.setProperty("scanPhase", self._scan_phase)
            self._root_obj.setProperty("aiState", self.state)
            self._root_obj.setProperty("smoothedAmp", self._smoothed_amp)
