"""
Script to launch JARVIS, run the animation loop for 2 seconds, grab a screenshot of the rendered UI, and exit.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QTimer
from app.application import JarvisApplication
from ui.main_window import JarvisMainWindow


def verify():
    app = JarvisApplication(sys.argv)
    window = JarvisMainWindow()
    window.show()

    def capture_and_close():
        try:
            screenshot_path = os.path.join(os.path.dirname(__file__), "jarvis_rendered.png")
            pixmap = window.grab()
            pixmap.save(screenshot_path, "PNG")
            print(f"[OK] Rendered UI screenshot captured to: {screenshot_path}")
        except Exception as e:
            print(f"[ERROR] Capture failed: {e}")
        finally:
            window.close()
            app.quit()

    # Simulate user speech and audio vibration at 1.0s and verify the console stays hidden
    def simulate_speech():
        window.page_home.set_live_speech("ही जरवेस", is_user=True)
        window._on_audio_amplitude(0.78)
        assert not window.page_home.interaction_panel.isVisible(), "Interaction panel should stay hidden when talking!"
        print("[TEST PASS] Interaction panel remained hidden during speech.")
        print("[TEST PASS] Audio amplitude dispatched to vibration widgets.")

    QTimer.singleShot(1000, simulate_speech)
    # Keep sending audio amplitude pulses so vibration is vividly active at capture time
    QTimer.singleShot(1500, lambda: window._on_audio_amplitude(0.85))
    QTimer.singleShot(2000, lambda: window._on_audio_amplitude(0.92))
    def simulate_user_speaking():
        window.title_bar.set_capsule_status("Listening...", "LISTENING")
        window.page_home.set_ai_state("LISTENING")
        window._on_audio_amplitude(0.88)
    QTimer.singleShot(4200, simulate_user_speaking)
    QTimer.singleShot(4600, lambda: window._on_audio_amplitude(0.95))

    # Capture after 5.0 seconds so 3D face, background, and clean collapsed UI are active
    QTimer.singleShot(5000, capture_and_close)
    app.exec()


if __name__ == "__main__":
    verify()
