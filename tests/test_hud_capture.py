import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtCore import QTimer
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor

def capture():
    app = QApplication(sys.argv)
    html_path = Path(__file__).resolve().parent.parent / "ui" / "web" / "jarvis_hud.html"
    
    view = QWebEngineView()
    view.setFixedSize(700, 700)
    view.setStyleSheet("background: #02070e;")
    view.page().setBackgroundColor(QColor(2, 7, 14))
    view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
    view.setUrl(QUrl.fromLocalFile(str(html_path)))
    view.show()

    def do_capture():
        out_path = Path(__file__).parent / "hud_face_preview.png"
        pix = view.grab()
        pix.save(str(out_path), "PNG")
        print(f"[OK] Captured HUD preview to: {out_path}")
        view.close()
        app.quit()

    # Wait 3 seconds for Three.js and GLB model to load and render
    QTimer.singleShot(3000, do_capture)
    app.exec()

if __name__ == "__main__":
    capture()
