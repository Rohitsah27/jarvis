"""
Test verifying the splash screen initialization, progress updates,
and seamless transition to JarvisMainWindow.
"""
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtCore import QTimer
from app.application import JarvisApplication
from ui.components.splash_screen import JarvisSplashScreen
from ui.main_window import JarvisMainWindow

def test_splash_and_window_lifecycle():
    print("[TEST] Initializing JarvisApplication...")
    app = JarvisApplication(sys.argv)

    print("[TEST] Creating JarvisSplashScreen...")
    splash = JarvisSplashScreen()
    splash.show()
    splash.set_progress(10, "TEST: INITIALIZING...")
    app.processEvents()

    print("[TEST] Constructing JarvisMainWindow with splash...")
    window = JarvisMainWindow(splash=splash)

    print("[TEST] Finishing splash and showing window...")
    splash.finish(window)
    app.processEvents()

    print("[TEST] Successfully reached running state!")

    # Schedule clean shutdown
    def cleanup():
        print("[TEST] Closing window and exiting...")
        window.close()
        app.quit()

    QTimer.singleShot(1500, cleanup)
    sys.exit(app.exec())

if __name__ == "__main__":
    test_splash_and_window_lifecycle()
