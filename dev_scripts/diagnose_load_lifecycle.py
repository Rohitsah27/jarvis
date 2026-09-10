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
view = win.page_home.ai_core._view

class MyDebugPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, msg, line, source):
        print(f"[CONSOLE {level}] {source}:{line} -> {msg}")

page = MyDebugPage(view)
# Notice: what happens if setPage is called AFTER setUrl vs BEFORE?
# In ai_core_web.py:
# view.setUrl(...) was already called in JarvisAICoreWeb.__init__!
print("Initial view URL:", view.url().toString())

def on_load_started():
    print("[EVENT] loadStarted")

def on_load_progress(p):
    print(f"[EVENT] loadProgress: {p}%")

def on_load_finished(ok):
    print(f"[EVENT] loadFinished: {ok}")

view.loadStarted.connect(on_load_started)
view.loadProgress.connect(on_load_progress)
view.loadFinished.connect(on_load_finished)

win.resize(1300, 850)
win.show()

def check_after_5s():
    print("5s URL:", view.url().toString())
    def cb(html):
        print("HTML length:", len(html) if html else 0)
        print("HTML preview:", (html[:200] if html else "NONE"))
        app.quit()
    view.page().toHtml(cb)

QTimer.singleShot(5000, check_after_5s)
app.exec()
