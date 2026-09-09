"""
Verify settings page rendering with Kokoro TTS engine options and audition buttons.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QTimer
from app.application import JarvisApplication
from ui.main_window import JarvisMainWindow
from core.voice.voice_engine import voice_engine


def verify():
    app = JarvisApplication(sys.argv)
    window = JarvisMainWindow()
    # Switch to Settings page (index 11)
    window.sidebar.select_page(11)
    window.show()

    def capture_and_close():
        screenshot_path = os.path.join(os.path.dirname(__file__), "settings_rendered.png")
        pixmap = window.grab()
        pixmap.save(screenshot_path, "PNG")
        print(f"[OK] Settings UI screenshot captured to: {screenshot_path}")

        # Also grab a scrolled screenshot showing audition buttons & save
        from PySide6.QtWidgets import QScrollArea
        scrolls = window.page_settings.findChildren(QScrollArea)
        if scrolls:
            scrolls[0].verticalScrollBar().setValue(340)
            scrolled_path = os.path.join(os.path.dirname(__file__), "settings_scrolled_rendered.png")
            window.grab().save(scrolled_path, "PNG")
            print(f"[OK] Scrolled screenshot captured to: {scrolled_path}")

        voice_engine.shutdown()
        window.close()
        app.quit()

    QTimer.singleShot(1500, capture_and_close)
    app.exec()


if __name__ == "__main__":
    verify()
