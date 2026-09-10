import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PySide6.QtWidgets import QApplication
    from ui.components.title_bar import JarvisTitleBar

    app = QApplication([])
    tb = JarvisTitleBar()
    for w in (1000, 1200, 1400, 1536):
        tb.resize(w, 50)
        tb.show()
        app.processEvents()
        c_x = tb.status_capsule.x() + tb.status_capsule.width() / 2
        win_center = w / 2
        print(f"Width {w}: Capsule Center = {c_x} | TitleBar Center = {win_center} | Diff = {abs(c_x - win_center)}")
        assert abs(c_x - win_center) <= 1.0, f"Capsule not centered: diff={abs(c_x - win_center)}"
    print("SUCCESS! ALL WIDTHS PERFECTLY CENTERED!")
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
