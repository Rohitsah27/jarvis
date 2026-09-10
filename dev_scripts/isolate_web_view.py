import sys
import os
sys.path.insert(0, os.path.abspath("."))

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QStackedWidget
from PySide6.QtCore import QTimer
from app.application import JarvisApplication
from ui.components.ai_core_web import JarvisAICoreWeb
from ui.pages.home_page import HomePage

app = JarvisApplication(sys.argv)

# Test 1: JarvisAICoreWeb in a simple QWidget
w1 = QWidget()
l1 = QVBoxLayout(w1)
core1 = JarvisAICoreWeb(w1)
l1.addWidget(core1)
w1.resize(800, 600)
w1.setWindowTitle("Test 1: Simple Widget")
w1.show()

# Test 2: HomePage directly in a QWidget (no main window)
w2 = QWidget()
l2 = QVBoxLayout(w2)
hp2 = HomePage(w2)
l2.addWidget(hp2)
w2.resize(1200, 800)
w2.setWindowTitle("Test 2: HomePage Widget")
w2.show()

# Test 3: HomePage inside QStackedWidget
w3 = QWidget()
l3 = QVBoxLayout(w3)
stack3 = QStackedWidget(w3)
hp3 = HomePage(w3)
stack3.addWidget(hp3)
l3.addWidget(stack3)
w3.resize(1200, 800)
w3.setWindowTitle("Test 3: Stacked HomePage")
w3.show()

def inspect_all():
    print("Test 1 view url:", core1._view.url().toString())
    print("Test 2 view url:", hp2.ai_core._view.url().toString())
    print("Test 3 view url:", hp3.ai_core._view.url().toString())
    
    # Check JS inside each
    def on_js1(r): print("Test 1 JS:", r)
    def on_js2(r): print("Test 2 JS:", r)
    def on_js3(r): print("Test 3 JS:", r)
    
    core1._view.page().runJavaScript("!!window.scene", on_js1)
    hp2.ai_core._view.page().runJavaScript("!!window.scene", on_js2)
    hp3.ai_core._view.page().runJavaScript("!!window.scene", on_js3)
    
    QTimer.singleShot(1000, app.quit)

QTimer.singleShot(2500, inspect_all)
app.exec()
