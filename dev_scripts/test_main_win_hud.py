import sys
import os
sys.path.insert(0, os.path.abspath("."))

from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtCore import QTimer

from app.application import JarvisApplication
from ui.main_window import JarvisMainWindow

app = JarvisApplication(sys.argv)
win = JarvisMainWindow()

# Let's inspect the HomePage and ai_core
home_page = win.page_home
ai_core = home_page.ai_core
view = ai_core._view

class DebugPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, msg, line, source):
        print(f"[MainWin JS {level}] Line {line} ({source}): {msg}")

# Let's see if the view has a page
print("ai_core view size:", view.size(), "visible:", view.isVisible())
win.resize(1300, 850)
win.show()

def check_win():
    print("AFTER SHOW ai_core view size:", view.size(), "visible:", view.isVisible())
    def cb(res):
        print("[HUD in MainWin State]:", res)
        # Capture grab
        pix = win.grab()
        pix.save("tests/main_win_grab.png")
        print("Saved tests/main_win_grab.png")
        app.quit()
    js = """
    (function() {
        const c = document.getElementById('canvas-container');
        return JSON.stringify({
            ready: window.__hudReady,
            containerWidth: c ? c.clientWidth : -1,
            containerHeight: c ? c.clientHeight : -1,
            canvasCount: c ? c.children.length : -1,
            bodyWidth: document.body.clientWidth,
            bodyHeight: document.body.clientHeight
        });
    })()
    """
    view.page().runJavaScript(js, cb)

QTimer.singleShot(3000, check_win)
app.exec()
