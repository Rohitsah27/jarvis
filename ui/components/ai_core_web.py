"""
Central Holographic AI Core — web-rendered variant.

Embeds ui/web/jarvis_hud.html (a Three.js scene: a real face-scan point
cloud loaded from a remote GLB, procedural anatomical eyes with gaze
tracking, CSS/SVG HUD rings and telemetry) inside a QWebEngineView. This
was supplied directly by the user as a reference implementation to match,
so it is embedded as-is rather than re-implemented natively.

Trade-offs versus the native QML Canvas version
(ui/components/ai_core_3d.py, still present and unused by default):
- Needs network access at startup to fetch Three.js, Google Fonts, and the
  face-scan GLB from their CDNs/GitHub — this widget will show only the
  static HUD chrome (no face) if offline.
- Runs a full Chromium process (QtWebEngine) for this one widget. It's
  already bundled with the installed PySide6 wheel (PySide6-Addons), so
  this doesn't add new disk footprint, but it is heavier at runtime than a
  native Qt Quick widget.

set_state()/set_audio_amplitude() call into the page via
page().runJavaScript() rather than a full QWebChannel, since only two
primitive values cross the boundary, once per animation tick.
"""
from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import QTimer, QUrl, QEvent, QObject
from PySide6.QtGui import QColor
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings

from ui.components.ai_core import AICoreState

_HTML_PATH = Path(__file__).resolve().parent.parent / "web" / "jarvis_hud.html"


class ZoomFilter(QObject):
    """Event filter that intercepts and blocks mouse wheel and pinch gestures on the web view."""

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Wheel, QEvent.NativeGesture):
            return True
        return super().eventFilter(watched, event)


class JarvisAICoreWeb(QWidget):
    """
    Drop-in replacement for JarvisAICore. Same public surface:
    set_state(), set_audio_amplitude(), constructor(parent).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 200)
        self.state = AICoreState.IDLE
        self._audio_amplitude = 0.0

        self.setStyleSheet("background: transparent;")

        self._view = QWebEngineView(self)
        self._view.setStyleSheet("background: transparent;")

        # Set transparent page background so jarvis_hud.html floats seamlessly without dark rectangular cutoffs
        self._view.page().setBackgroundColor(QColor(0, 0, 0, 0))

        # Configure WebEngine settings for WebGL, local models, and transparent background
        settings = self._view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)

        # Intercept and block all wheel/gesture zoom events at the Qt level
        self._zoom_filter = ZoomFilter(self)
        self._view.installEventFilter(self._zoom_filter)

        self._view.setUrl(QUrl.fromLocalFile(str(_HTML_PATH)))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._push_state)
        self._timer.start()

    def check_hud_ready(self, callback):
        """Asynchronously checks whether the 3D Web HUD and model have initialized."""
        page = self._view.page()
        if page is None:
            callback(False)
            return
        page.runJavaScript("!!(window.__hudReady || (window.faceRoot && window.faceRoot.children.length > 0))", callback)

    def showEvent(self, event):
        super().showEvent(event)
        self._view.setZoomFactor(1.0)
        self._install_zoom_filters()

    def _install_zoom_filters(self):
        """Install the zoom blocker on any internal render child widgets."""
        self._view.setZoomFactor(1.0)
        if self._view.focusProxy():
            self._view.focusProxy().installEventFilter(self._zoom_filter)
        for child in self._view.findChildren(QWidget):
            child.installEventFilter(self._zoom_filter)

    def set_state(self, state: str):
        self.state = state
        self._push_state()

    def set_audio_amplitude(self, amp: float):
        self._audio_amplitude = max(0.0, min(1.0, amp))

    def _push_state(self):
        page = self._view.page()
        if page is None:
            return
        if self._view.zoomFactor() != 1.0:
            self._view.setZoomFactor(1.0)
        page.runJavaScript(f"window.jarvisSetAmplitude && window.jarvisSetAmplitude({self._audio_amplitude});")
        page.runJavaScript(f"window.jarvisSetState && window.jarvisSetState('{self.state}');")
