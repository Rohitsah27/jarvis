import sys
import os
sys.path.insert(0, os.path.abspath("."))

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtCore import QTimer
from app.application import JarvisApplication
from ui.pages.home_page import HomePage

app = JarvisApplication(sys.argv)
w = QWidget()
l = QVBoxLayout(w)
hp = HomePage(w)
l.addWidget(hp)
w.resize(1300, 850)
w.show()

def check():
    view = hp.ai_core._view
    def cb(r):
        print("[CHECK HUD READY]:", r)
        # Capture screen of w!
        pix = w.grab()
        pix.save("tests/homepage_rendered_screenshot.png")
        print("Saved tests/homepage_rendered_screenshot.png")
        app.quit()
    view.page().runJavaScript("""
    ({
        hudReady: window.__hudReady,
        headMat: !!window.headMat,
        aiState: window.__aiState,
        canvasChildren: document.getElementById('canvas-container') ? document.getElementById('canvas-container').children.length : 0
    })
    """, cb)

QTimer.singleShot(2500, check)
app.exec()
