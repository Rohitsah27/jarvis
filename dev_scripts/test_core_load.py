import sys
import os
sys.path.insert(0, os.path.abspath("."))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from app.application import JarvisApplication
from ui.components.ai_core_web import JarvisAICoreWeb

app = JarvisApplication(sys.argv)
core = JarvisAICoreWeb()
core.resize(600, 600)
core.show()

def on_finished(ok):
    print("AI CORE LOAD FINISHED:", ok)
    def cb(res):
        print("HTML TITLE/READY:", res)
        app.quit()
    core._view.page().runJavaScript("document.title + ' | ready=' + window.__hudReady", cb)

core._view.loadFinished.connect(on_finished)

QTimer.singleShot(5000, lambda: (print("TIMEOUT!"), app.quit()))
app.exec()
