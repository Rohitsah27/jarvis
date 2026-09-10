"""
Test script to verify WMPlayer.OCX in a background QThread.
"""
import sys
import os
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QCoreApplication, QThread
import win32com.client
import pythoncom


class PlayerThread(QThread):
    def __init__(self, mp3_path):
        super().__init__()
        self.mp3_path = mp3_path

    def run(self):
        pythoncom.CoInitialize()
        try:
            player = win32com.client.Dispatch("WMPlayer.OCX")
            player.settings.volume = 100
            player.URL = self.mp3_path
            player.controls.play()
            print("Playback started via WMPlayer...")
            
            # Wait for media to start
            time.sleep(0.3)
            while player.playState in [2, 3]: # 2=paused, 3=playing
                time.sleep(0.05)
                
            print("Playback finished successfully!")
        except Exception as e:
            print("WMPlayer error:", e)
        finally:
            pythoncom.CoUninitialize()


def main():
    app = QCoreApplication(sys.argv)
    mp3_path = os.path.join(tempfile.gettempdir(), "test_jarvis_hindi.mp3")
    if not os.path.exists(mp3_path):
        print("MP3 not found, exiting.")
        return

    thread = PlayerThread(mp3_path)
    thread.finished.connect(app.quit)
    thread.start()
    app.exec()


if __name__ == "__main__":
    main()
