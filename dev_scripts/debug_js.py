import sys
import os
sys.path.insert(0, os.path.abspath("."))

from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtCore import QUrl, QTimer
from pathlib import Path

class DebugPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, msg, line, source):
        print(f"[JS {level}] Line {line} ({source}): {msg}")

app = QApplication(sys.argv)
view = QWebEngineView()
page = DebugPage(view)
view.setPage(page)

settings = view.settings()
settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)

html_path = Path("ui/web/jarvis_hud.html").resolve()
view.setUrl(QUrl.fromLocalFile(str(html_path)))
view.resize(900, 700)
view.show()

def dump_state():
    def cb(res):
        print("[HUD State Result]:", res)
        app.quit()
    js = """
    (function() {
        return JSON.stringify({
            ready: window.__hudReady,
            hasThree: typeof THREE !== 'undefined',
            hasGLTF: typeof THREE !== 'undefined' && typeof THREE.GLTFLoader !== 'undefined',
            faceChildren: window.faceRoot ? window.faceRoot.children.length : -1,
            errors: window.__errors || []
        });
    })()
    """
    view.page().runJavaScript(js, cb)

QTimer.singleShot(2500, dump_state)
app.exec()
