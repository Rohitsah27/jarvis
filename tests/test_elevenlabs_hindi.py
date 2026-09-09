"""
Direct test of VoiceEngine speaking Hindi with ElevenLabs.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QCoreApplication, QTimer
from core.voice.voice_engine import voice_engine


def main():
    app = QCoreApplication(sys.argv)

    def on_complete():
        print("[OK] JARVIS Hindi speech finished successfully!")
        app.quit()

    voice_engine.speech_completed.connect(on_complete)

    print("Speaking Hindi via ElevenLabs...")
    voice_engine.speak("नमस्ते रोहित सर, मैं जार्विस हूँ।")

    QTimer.singleShot(15000, lambda: (print("[!] Timeout"), app.quit()))
    app.exec()


if __name__ == "__main__":
    main()
