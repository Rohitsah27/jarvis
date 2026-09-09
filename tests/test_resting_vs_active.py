"""
Capture two states of JARVIS:
1. Resting Quiet State (Listening, user saying nothing -> amplitude = 0.0)
2. Active Speaking State (Listening, user speaks -> amplitude = 0.85)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QTimer
from app.application import JarvisApplication
from ui.main_window import JarvisMainWindow
from ui.components.ai_core import AICoreState

artifact_dir = r"C:\Users\pramo\.gemini\antigravity-ide\brain\608a0a17-297b-4c84-9d1d-1656613173b3"

def test_states():
    app = JarvisApplication(sys.argv)
    window = JarvisMainWindow()
    window.show()

    # Step 1: Simulate Quiet Listening (user saying nothing)
    window.page_home.set_ai_state(AICoreState.LISTENING)
    window.title_bar.set_capsule_status("Listening...", "LISTENING")
    window.page_home.ai_core.set_audio_amplitude(0.0)
    window.title_bar.set_audio_amplitude(0.0)

    for _ in range(10):
        window.page_home.ai_core._animation_tick()

    quiet_path = os.path.join(artifact_dir, "resting_quiet_rendered.png")
    window.grab().save(quiet_path, "PNG")
    print(f"[OK] Resting quiet screenshot saved: {quiet_path}")

    # Step 2: Simulate Active Speech
    window.page_home.ai_core.set_audio_amplitude(0.85)
    window.title_bar.set_audio_amplitude(0.85)

    for _ in range(8):
        window.page_home.ai_core._animation_tick()

    speech_path = os.path.join(artifact_dir, "active_speech_rendered.png")
    window.grab().save(speech_path, "PNG")
    print(f"[OK] Active speech screenshot saved: {speech_path}")

    window.close()
    app.quit()

if __name__ == "__main__":
    test_states()
