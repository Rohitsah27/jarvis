import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtGui import QColor

app = QApplication(sys.argv)
html_path = Path("ui/web/jarvis_hud.html").resolve()
view = QWebEngineView()
view.setFixedSize(700, 700)
view.setStyleSheet("background: #02070e;")
view.page().setBackgroundColor(QColor(2, 7, 14))
view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
view.page().settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
view.setUrl(QUrl.fromLocalFile(str(html_path)))
view.show()

step = 0
def next_step():
    global step
    step += 1
    if step == 1:
        # Frontal capture
        pix = view.grab()
        pix.save("tests/hud_face_preview.png", "PNG")
        print("[OK] Saved tests/hud_face_preview.png")
        # Rotate to 3/4 angle
        view.page().runJavaScript("targetX = 0.58; targetY = -0.05;")
        QTimer.singleShot(2000, next_step)
    elif step == 2:
        # 3/4 Angle capture
        pix = view.grab()
        pix.save("tests/hud_angle_3_4.png", "PNG")
        print("[OK] Saved tests/hud_angle_3_4.png")
        # Rotate to Left Profile
        view.page().runJavaScript("targetX = 1.5708; targetY = 0.0;")
        QTimer.singleShot(2000, next_step)
    elif step == 3:
        # Left Profile capture
        pix = view.grab()
        pix.save("tests/hud_profile.png", "PNG")
        print("[OK] Saved tests/hud_profile.png")
        # Return to center
        view.page().runJavaScript("targetX = 0.0; targetY = 0.0;")
        QTimer.singleShot(1500, next_step)
    elif step == 4:
        view.close()
        app.quit()

# Wait 3.5 seconds for initial GLB load
QTimer.singleShot(3500, next_step)
app.exec()
