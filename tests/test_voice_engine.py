"""
Test script to verify VoiceEngine speech output directly.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PySide6.QtCore import QCoreApplication, QTimer
from core.voice.voice_engine import voice_engine



def main():
    app = QCoreApplication(sys.argv)

    def on_complete():
        print("[OK] VoiceEngine.speech_completed signal received!")
        app.quit()

    voice_engine.speech_completed.connect(on_complete)

    print("Testing VoiceEngine.speak()...")
    voice_engine.speak("Good day, sir. JARVIS speech synthesis is now loud and clear.")

    # Timeout safety
    QTimer.singleShot(8000, lambda: (print("[!] Timeout"), app.quit()))

    app.exec()


if __name__ == "__main__":
    main()
