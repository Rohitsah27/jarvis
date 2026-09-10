import sys
import os
import time

sys.path.insert(0, os.path.abspath("."))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QThread, Signal
from app.application import JarvisApplication
from ui.components.splash_screen import JarvisSplashScreen
from ui.main_window import JarvisMainWindow
from core.voice.voice_engine import voice_engine

class StartupPreloader(QThread):
    progress = Signal(int, str)
    complete = Signal()

    def run(self):
        t0 = time.perf_counter()
        
        # 1. Kokoro TTS
        self.progress.emit(35, "LOADING NEURAL VOICE SYNTHESIS (KOKORO)...")
        try:
            from core.voice.kokoro_engine import kokoro_engine
            kokoro_engine._ensure_loaded()
            print(f"[Preload] Kokoro loaded ({time.perf_counter() - t0:.2f}s)")
        except Exception as e:
            print(f"[Preload] Kokoro error: {e}")

        # 2. Faster-Whisper STT
        t_w = time.perf_counter()
        self.progress.emit(65, "LOADING SPEECH RECOGNITION (FASTER-WHISPER)...")
        try:
            from core.voice.stt_engine import stt_engine
            stt_engine.ensure_whisper_loaded()
            print(f"[Preload] Faster-Whisper loaded ({time.perf_counter() - t_w:.2f}s)")
        except Exception as e:
            print(f"[Preload] Whisper error: {e}")

        # 3. LLM Warmup
        self.progress.emit(88, "INITIALIZING AI BRAIN CONNECTION...")
        try:
            from core.ai.manager import ai_manager
        except Exception:
            pass

        self.progress.emit(100, "ALL SYSTEMS OPERATIONAL. READY.")
        self.complete.emit()

def test():
    app = JarvisApplication(sys.argv)
    splash = JarvisSplashScreen()
    splash.show()
    splash.set_progress(10, "INITIALIZING CYBERNETIC ENVIRONMENT...")
    app.processEvents()

    # Pause mic listener during boot
    voice_engine.pause_listening()

    # Construct window (builds all UI pages & starts 3D HUD loading)
    window = JarvisMainWindow(splash=splash)

    preloader = StartupPreloader()
    preloader.progress.connect(splash.set_progress)

    def on_ready():
        print("[Preload] Everything ready! Revealing main window...")
        # Brief pause to show 100%
        QTimer.singleShot(500, lambda: (
            splash.finish(window),
            voice_engine.resume_listening(),
            print("[Preload] Window shown, mic resumed!"),
            # Capture state after 2 seconds
            QTimer.singleShot(2500, lambda: (
                window.grab().save("tests/full_preloaded_window.png"),
                print("Captured tests/full_preloaded_window.png"),
                app.quit()
            ))
        ))

    preloader.complete.connect(on_ready)
    preloader.start()

    sys.exit(app.exec())

if __name__ == "__main__":
    test()
