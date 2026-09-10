"""
Script to simulate active speech amplitude on JARVIS AI Core,
trigger pop-up circle lines and shockwaves, capture rendered image, and save to artifact directory.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QTimer
from app.application import JarvisApplication
from ui.main_window import JarvisMainWindow
from ui.components.ai_core import AICoreState


def test_popup_rendering():
    app = JarvisApplication(sys.argv)
    window = JarvisMainWindow()
    window.show()

    # Simulate active listening and speech amplitude
    window.page_home.set_ai_state(AICoreState.LISTENING)
    window.title_bar.set_capsule_status("Listening...", "LISTENING")
    window.page_home.ai_core.set_audio_amplitude(0.85)
    window.title_bar.set_audio_amplitude(0.85)

    def on_tick():
        # Trigger multiple animation ticks to let shockwave rings expand
        for _ in range(8):
            window.page_home.ai_core._animation_tick()

        artifact_dir = r"C:\Users\pramo\.gemini\antigravity-ide\brain\608a0a17-297b-4c84-9d1d-1656613173b3"
        out_path = os.path.join(artifact_dir, "popup_circles_rendered.png")
        pix = window.grab()
        pix.save(out_path, "PNG")
        print(f"[OK] Rendered pop-up circle lines screenshot saved: {out_path}")
        window.close()
        app.quit()

    QTimer.singleShot(500, on_tick)
    app.exec()


if __name__ == "__main__":
    test_popup_rendering()
