import sys
import os
sys.path.insert(0, os.path.abspath("."))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from app.application import JarvisApplication
from ui.components.ai_core_web import JarvisAICoreWeb

app = JarvisApplication(sys.argv)
core = JarvisAICoreWeb()
# Note: we do NOT call core.show()!

def on_start():
    print("HIDDEN VIEW: loadStarted")

def on_finish(ok):
    print("HIDDEN VIEW: loadFinished:", ok)
    def cb(res):
        print("HIDDEN VIEW: HUD ready inside hidden widget:", res)
        app.quit()
    core.check_hud_ready(cb)

core._view.loadStarted.connect(on_start)
core._view.loadFinished.connect(on_finish)

QTimer.singleShot(6000, lambda: (print("TIMEOUT!"), app.quit()))
app.exec()
