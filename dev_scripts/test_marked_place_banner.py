"""
Test script to render user speech on the marked HUD banner location
and save screenshot for visual verification.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QTimer
from app.application import JarvisApplication
from ui.main_window import JarvisMainWindow

artifact_dir = r"C:\Users\pramo\.gemini\antigravity-ide\brain\608a0a17-297b-4c84-9d1d-1656613173b3"

def test_banner():
    app = JarvisApplication(sys.argv)
    window = JarvisMainWindow()
    window.show()

    # Write spoken speech on the marked place
    window.page_home.set_live_speech("open the chrome browser", is_user=True)

    out_path = os.path.join(artifact_dir, "marked_place_rendered.png")
    window.grab().save(out_path, "PNG")
    print(f"[OK] Marked place speech banner screenshot saved: {out_path}")

    window.close()
    app.quit()

if __name__ == "__main__":
    test_banner()
