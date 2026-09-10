import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout
from PySide6.QtGui import QPixmap
from PySide6.QtCore import QTimer

from app.application import JarvisApplication
from ui.components.ai_core import JarvisAICore, AICoreState

def capture_dot_face():
    app = JarvisApplication(sys.argv)
    container = QWidget()
    container.setStyleSheet("background-color: #070e1a;")
    container.setFixedSize(650, 320)
    layout = QHBoxLayout(container)
    layout.setContentsMargins(10, 10, 10, 10)

    core = JarvisAICore(container)
    core.set_state(AICoreState.LISTENING)
    core.set_audio_amplitude(0.4)
    layout.addWidget(core)

    container.show()
    app.processEvents()

    out_path = Path(__file__).parent / "test_dot_face_rendered.png"
    pix = container.grab()
    pix.save(str(out_path), "PNG")
    print(f"Captured to: {out_path}")
    container.close()

if __name__ == "__main__":
    capture_dot_face()
