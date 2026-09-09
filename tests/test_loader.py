import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings

class LoggingPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceId):
        print(f"[CONSOLE {level}] {message} (line {lineNumber})")

app = QApplication(sys.argv)
html_path = Path("ui/web/jarvis_hud.html").resolve()
view = QWebEngineView()
view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
page = LoggingPage(view)
view.setPage(page)
view.setUrl(QUrl.fromLocalFile(str(html_path)))
view.show()

def check_loader():
    def on_result(res):
        print("RESULT FROM JS:", res)
    view.page().runJavaScript("""
        (function() {
            var tag = document.getElementById('loader-tag');
            return {
                tagText: tag ? tag.innerText : null,
                tagOpacity: tag ? tag.style.opacity : null,
                faceChildren: typeof faceRoot !== 'undefined' ? faceRoot.children.length : -1,
                hasComposer: typeof composer !== 'undefined'
            };
        })()
    """, on_result)

QTimer.singleShot(2500, check_loader)
QTimer.singleShot(4000, app.quit)
app.exec()
