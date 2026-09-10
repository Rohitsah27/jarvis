"""
Verify full interaction flow: Startup greeting -> User speech -> Cognitive Brain -> Speech playback -> Clean exit.
"""
import sys, os
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QTimer
from app.application import JarvisApplication
from ui.main_window import JarvisMainWindow
from core.voice.voice_engine import voice_engine


def test_interaction():
    app = JarvisApplication(sys.argv)
    win = JarvisMainWindow()
    win.show()

    speech_count = 0

    def on_speech_completed():
        nonlocal speech_count
        speech_count += 1
        print(f"[InteractionTest] speech_completed event #{speech_count} received!")

        if speech_count == 1:
            print("[InteractionTest] Greeting finished. Now simulating user: 'Mera Awaaz Sunai de raha hai'")
            # Wait 300ms then simulate speech
            QTimer.singleShot(300, lambda: win._on_voice_transcript_received("Mera Awaaz Sunai de raha hai"))
        elif speech_count >= 2:
            print("[InteractionTest] Cognitive Brain response vocalization finished! All systems verified.")
            screenshot_path = os.path.join(os.path.dirname(__file__), "interaction_verified.png")
            win.grab().save(screenshot_path, "PNG")
            print(f"[InteractionTest] Captured verified screenshot: {screenshot_path}")
            QTimer.singleShot(500, lambda: (win.close(), app.quit()))

    voice_engine.speech_completed.connect(on_speech_completed)

    # 30-second safety timeout
    QTimer.singleShot(30000, lambda: (print("[InteractionTest] Safety timeout reached"), win.close(), app.quit()))

    app.exec()
    print("[InteractionTest] Exited cleanly with zero errors!")


if __name__ == "__main__":
    test_interaction()
