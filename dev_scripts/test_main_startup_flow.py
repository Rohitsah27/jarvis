import sys
import os
import time
sys.path.insert(0, os.path.abspath("."))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from app.application import JarvisApplication
from ui.components.splash_screen import JarvisSplashScreen
from ui.main_window import JarvisMainWindow

app = JarvisApplication(sys.argv)
print(f"[{time.strftime('%X')}] App created")

splash = JarvisSplashScreen()
splash.show()
splash.set_progress(10, "INITIALIZING CYBERNETIC DESKTOP OS...")
app.processEvents()
print(f"[{time.strftime('%X')}] Splash shown")

from core.voice.voice_engine import voice_engine
voice_engine.pause_listening()
print(f"[{time.strftime('%X')}] Voice engine paused. State: {voice_engine.state.value}")

window = JarvisMainWindow(splash=splash)
print(f"[{time.strftime('%X')}] Main window constructed")

def on_preload_complete():
    print(f"[{time.strftime('%X')}] PRELOAD COMPLETE SIGNAL RECEIVED!")
    def reveal():
        print(f"[{time.strftime('%X')}] Revealing window and finishing splash...")
        splash.finish(window)
        voice_engine.resume_listening()
        print(f"[{time.strftime('%X')}] Voice engine resumed. State: {voice_engine.state.value}")

        # Check HUD ready after 1 second
        def verify():
            print(f"[{time.strftime('%X')}] Verifying HUD ready...")
            def cb(ready):
                print(f"[{time.strftime('%X')}] VERIFICATION RESULT: HUD ready={ready}")
                app.quit()
            window.page_home.ai_core.check_hud_ready(cb)
        QTimer.singleShot(1000, verify)

    QTimer.singleShot(350, reveal)

splash.start_preload(window, on_preload_complete)
print(f"[{time.strftime('%X')}] Preload started")

# Auto-exit after 20s if something hangs
QTimer.singleShot(20000, lambda: (print("TIMEOUT 20s!"), app.quit()))
app.exec()
