import sys
import os
sys.path.insert(0, os.path.abspath("."))
from PySide6.QtWidgets import QApplication
from ui.main_window import JarvisMainWindow

app = QApplication(sys.argv)
try:
    window = JarvisMainWindow()
    window.show()
    hp = window.page_home
    print("HomePage size:", hp.size())
    print("ai_core size:", hp.ai_core.size())
    print("ai_core rect:", hp.ai_core.geometry())
    print("ai_core view size:", hp.ai_core._view.size())
    print("ai_core view rect:", hp.ai_core._view.geometry())
    print("ai_core view isVisible:", hp.ai_core._view.isVisible())
except Exception as e:
    print("ERROR:", e)
finally:
    app.quit()
