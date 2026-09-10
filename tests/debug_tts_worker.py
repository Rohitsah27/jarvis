import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QCoreApplication
app = QCoreApplication(sys.argv)

from core.voice.voice_engine import SpeechSynthesisWorker

print("Testing SpeechSynthesisWorker...")
worker = SpeechSynthesisWorker("नमस्ते रोहित सर, जार्विस ऑनलाइन है।")

def on_done():
    print(">>> synthesis_finished signal received!")
    app.quit()

worker.synthesis_finished.connect(on_done)
worker.start()
app.exec()
print("Test completed successfully.")
