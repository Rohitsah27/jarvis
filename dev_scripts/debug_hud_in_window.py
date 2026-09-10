import sys
import os
sys.path.insert(0, os.path.abspath("."))
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtCore import QTimer
from ui.main_window import JarvisMainWindow

app = QApplication(sys.argv)
window = JarvisMainWindow()

class DebugPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"[CONSOLE] line {lineNumber}: {message} (source: {sourceID})")

view = window.page_home.ai_core._view
# Replace page with debug page, keeping URL
url = view.url()
dbg_page = DebugPage(view)
view.setPage(dbg_page)
view.setUrl(url)

window.show()

def check_dom():
    def on_js(res):
        print("[DOM CHECK]", res)
        app.quit()
    view.page().runJavaScript("""
    (() => {
        return {
            title: document.title,
            hasThree: typeof THREE !== 'undefined',
            hasGLTFLoader: typeof THREE !== 'undefined' && typeof THREE.GLTFLoader !== 'undefined',
            sceneExists: typeof scene !== 'undefined',
            sceneChildren: typeof scene !== 'undefined' ? scene.children.length : -1,
            faceRootExists: typeof faceRoot !== 'undefined',
            faceRootChildren: typeof faceRoot !== 'undefined' ? faceRoot.children.length : -1,
            loaderTagText: document.getElementById('loader-tag') ? document.getElementById('loader-tag').innerText : 'NO_TAG',
            bodyWidth: document.body ? document.body.clientWidth : 0,
            bodyHeight: document.body ? document.body.clientHeight : 0,
        };
    })()
    """, on_js)

QTimer.singleShot(4000, check_dom)
sys.exit(app.exec())
