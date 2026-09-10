import sys
import os
sys.path.insert(0, os.path.abspath("."))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from app.application import JarvisApplication
from ui.main_window import JarvisMainWindow

app = JarvisApplication(sys.argv)
win = JarvisMainWindow()
view = win.page_home.ai_core._view

win.resize(1300, 850)
win.show()

def check_html():
    print("URL is:", view.url().toString())
    def cb(res):
        print("[HUD HTML len]:", len(res) if res else 0)
        print("[HUD HTML snippet]:", repr(res[:300]) if res else "NONE")
        app.quit()
    view.page().runJavaScript("document.documentElement.outerHTML", cb)

QTimer.singleShot(3000, check_html)
app.exec()
