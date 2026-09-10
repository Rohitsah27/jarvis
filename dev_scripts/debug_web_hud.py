import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PySide6.QtCore import QUrl, QTimer

app = QApplication(sys.argv)

class CustomPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"[JS] line {lineNumber}: {message}")

view = QWebEngineView()
page = CustomPage(view)
view.setPage(page)

# Test with both attributes
view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)

hud_path = os.path.abspath("ui/web/jarvis_hud.html")
view.setUrl(QUrl.fromLocalFile(hud_path))
view.show()

def inspect():
    def cb(res):
        print("[INSPECT] Scene children count / state:", res)
        pix = view.grab()
        pix.save("tests/web_hud_debug_capture.png")
        print("[INSPECT] Saved capture to tests/web_hud_debug_capture.png")
        app.quit()
    view.page().runJavaScript(
        "(() => {"
        "  const hasLoader = !!document.getElementById('loader-tag');"
        "  const faceRootChildren = window.faceRoot ? window.faceRoot.children.length : -1;"
        "  const hasScene = !!window.scene;"
        "  return { hasLoader, faceRootChildren, hasScene };"
        "})()",
        cb
    )

QTimer.singleShot(2500, inspect)
sys.exit(app.exec())
