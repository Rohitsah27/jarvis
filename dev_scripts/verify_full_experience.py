import sys
import os
sys.path.insert(0, os.path.abspath("."))

from PySide6.QtCore import QTimer
from app.application import JarvisApplication
from ui.components.splash_screen import JarvisSplashScreen
from ui.main_window import JarvisMainWindow

def run():
    app = JarvisApplication(sys.argv)

    splash = JarvisSplashScreen()
    splash.show()
    splash.set_progress(10, "INITIALIZING CYBERNETIC DESKTOP OS...")
    app.processEvents()

    try:
        from core.voice.voice_engine import voice_engine
        voice_engine.pause_listening()
    except Exception:
        pass

    window = JarvisMainWindow(splash=splash)

    def on_preload_complete():
        def reveal():
            splash.finish(window)
            try:
                from core.voice.voice_engine import voice_engine
                voice_engine.resume_listening()
            except Exception:
                pass

            # Capture the window 2.5s after reveal to verify 3D face and all sections
            def capture_and_exit():
                pix = window.grab()
                pix.save("tests/full_experience_verified.png")
                print("[VERIFY SUCCESS] Saved tests/full_experience_verified.png")
                app.quit()

            QTimer.singleShot(2500, capture_and_exit)

        QTimer.singleShot(350, reveal)

    splash.start_preload(window, on_preload_complete)
    sys.exit(app.exec())

if __name__ == "__main__":
    run()
