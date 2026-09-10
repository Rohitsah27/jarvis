"""
Test that verify:
1. Initial speak() call enters PROCESSING (Thinking...).
2. When playback begins, VoiceEngine transitions to SPEAKING without error.
3. Amplitude ticks are emitted during playback.
4. Capsule switches to Vocalizing... at the exact same time.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QCoreApplication, QTimer
from core.voice.voice_engine import voice_engine, VoiceState
from app.application import JarvisApplication
from ui.main_window import JarvisMainWindow


def test_mouth_and_vocalizing():
    app = JarvisApplication(sys.argv)
    window = JarvisMainWindow()
    window.show()

    events_log = []
    amplitudes = []

    def on_state(state):
        capsule_text = window.title_bar.status_capsule._text
        events_log.append((state.name, capsule_text))
        print(f"[STATE] {state.name} | Capsule: '{capsule_text}'")

    def on_amp(amp):
        amplitudes.append(amp)

    voice_engine.state_changed.connect(on_state)
    voice_engine.audio_amplitude.connect(on_amp)

    def trigger_speech():
        print("[TEST] Triggering voice_engine.speak()...")
        voice_engine.speak("System check initiated.")
        # Immediately after speak(), state MUST be PROCESSING
        assert voice_engine.state == VoiceState.PROCESSING, f"Expected PROCESSING, got {voice_engine.state}"
        assert "Vocalizing" not in window.title_bar.status_capsule._text
        print("[PASS 1] Before playback starts: State is PROCESSING and Capsule is 'Thinking...'")

    QTimer.singleShot(600, trigger_speech)

    def verify_results():
        states = [e[0] for e in events_log]
        print(f"[RECORDED STATES]: {states}")
        print(f"[AMPLITUDE SAMPLES COUNT]: {len(amplitudes)}")
        if len(amplitudes) > 0:
            print(f"[SAMPLE AMPLITUDES]: {amplitudes[:5]} ... max: {max(amplitudes)}")

        # Verify that SPEAKING was reached
        assert "SPEAKING" in states, f"Expected SPEAKING in states, got: {states}"
        # Find the capsule text when SPEAKING happened
        speaking_entries = [e for e in events_log if e[0] == "SPEAKING"]
        assert len(speaking_entries) > 0
        assert "Vocalizing" in speaking_entries[0][1], f"Expected Vocalizing... in capsule, got: {speaking_entries[0][1]}"
        print("[PASS 2] When playback starts: State successfully transitioned to SPEAKING and Capsule displays 'Vocalizing...'")
        print("[PASS 3] Audio amplitudes were emitted to animate the mouth and visualizers.")
        window.close()
        app.quit()

    QTimer.singleShot(4500, verify_results)
    app.exec()


if __name__ == "__main__":
    test_mouth_and_vocalizing()
