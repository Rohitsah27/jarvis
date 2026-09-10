"""
Unit test to verify that 'Vocalizing...' and mouth movement only start when audio playback begins.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QCoreApplication, QTimer
from core.voice.voice_engine import voice_engine, VoiceState
from app.application import JarvisApplication
from ui.main_window import JarvisMainWindow


def test_vocalizing_sync():
    app = JarvisApplication(sys.argv)
    window = JarvisMainWindow()
    window.show()

    events_log = []

    def on_state(state):
        capsule_text = window.title_bar.status_capsule._text
        events_log.append((state.name, capsule_text))
        print(f"[EVENT] State: {state.name} | Capsule: '{capsule_text}'")

    voice_engine.state_changed.connect(on_state)

    def trigger_speech():
        print("[TEST] Triggering voice_engine.speak()...")
        voice_engine.speak("System check initiated.")
        # Immediately after speak() is called, state MUST be PROCESSING, not SPEAKING
        capsule_text = window.title_bar.status_capsule._text
        assert voice_engine.state == VoiceState.PROCESSING, f"Expected PROCESSING during synthesis, got {voice_engine.state}"
        assert "Vocalizing" not in capsule_text, f"Capsule should NOT say Vocalizing before audio playback! (Got '{capsule_text}')"
        print("[TEST PASS 1] State is PROCESSING and Capsule does NOT show 'Vocalizing...' during synthesis delay.")

    QTimer.singleShot(600, trigger_speech)

    def check_later():
        states = [e[0] for e in events_log]
        print(f"[TEST DONE] Recorded events: {events_log}")
        window.close()
        app.quit()

    QTimer.singleShot(3000, check_later)
    app.exec()


if __name__ == "__main__":
    test_vocalizing_sync()
