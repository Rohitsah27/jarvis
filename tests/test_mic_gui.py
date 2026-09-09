"""
Dedicated Standalone Live Microphone & Speech Recognition Tester GUI.
Run this tool directly with: python tests/test_mic_gui.py
Provides a real-time reactive VU meter, speech threshold indicator,
and instant transcription of your spoken commands.
"""
import os
import sys
import time
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QProgressBar,
    QFrame,
    QTextEdit,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor
import speech_recognition as sr
import audioop
from app.config import config
from core.voice.voice_engine import get_available_microphones


class MicMonitorThread(QThread):
    volume_tick = Signal(int, int)  # rms, threshold
    speech_started = Signal()
    transcript_ready = Signal(str)

    def __init__(self, device_index=None, parent=None):
        super().__init__(parent)
        self.device_index = device_index
        self._running = True

    def stop(self):
        self._running = False
        self.wait(1500)

    def run(self):
        recognizer = sr.Recognizer()
        mic = None
        try:
            mic = sr.Microphone(device_index=self.device_index)
        except Exception:
            try:
                mic = sr.Microphone()
            except Exception:
                return

        if not mic:
            return

        with mic as source:
            try:
                recognizer.adjust_for_ambient_noise(source, duration=0.8)
                measured = recognizer.energy_threshold
                recognizer.energy_threshold = min(max(float(config.MIC_ENERGY_THRESHOLD), measured * 1.35), 180.0)
            except Exception:
                recognizer.energy_threshold = 75.0

            thresh = int(recognizer.energy_threshold)

            while self._running:
                try:
                    chunk = source.stream.read(source.CHUNK)
                    if not chunk or len(chunk) == 0:
                        continue
                    rms = audioop.rms(chunk, source.SAMPLE_WIDTH)
                    self.volume_tick.emit(rms, thresh)

                    if rms > thresh:
                        self.speech_started.emit()
                        # Capture phrase
                        try:
                            audio = recognizer.listen(source, timeout=1.5, phrase_time_limit=5.0)
                            # Transcribe
                            text = None
                            try:
                                text = recognizer.recognize_google(audio, language="en-IN")
                            except Exception:
                                try:
                                    text = recognizer.recognize_google(audio, language="hi-IN")
                                except Exception:
                                    pass
                            if text and text.strip():
                                self.transcript_ready.emit(text.strip())
                        except Exception:
                            pass
                except Exception:
                    self.msleep(50)


class LiveMicTesterWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JARVIS - Live Microphone & Voice Tester")
        self.setFixedSize(540, 420)
        self.setStyleSheet("background-color: #070e1a; color: #ffffff;")
        self.monitor_thread = None
        self._init_ui()
        self._start_monitoring()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("🎙️ JARVIS LIVE VOICE TESTER")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title.setStyleSheet("color: #00d2ff; letter-spacing: 1.5px;")
        layout.addWidget(title, alignment=Qt.AlignCenter)

        sub = QLabel("Speak into your microphone to verify audio capture in real-time.")
        sub.setStyleSheet("color: #94a3b8; font-size: 9pt;")
        layout.addWidget(sub, alignment=Qt.AlignCenter)

        # Device Selector
        row_dev = QHBoxLayout()
        lbl_d = QLabel("Active Microphone:")
        lbl_d.setStyleSheet("color: #e2e8f0; font-weight: bold;")
        self.combo_dev = QComboBox()
        self.combo_dev.setStyleSheet("background: #0f172a; color: #38bdf8; border: 1px solid #00d2ff; padding: 6px; border-radius: 6px;")
        mics = get_available_microphones()
        for idx, name in mics:
            self.combo_dev.addItem(name, idx)
        self.combo_dev.currentIndexChanged.connect(self._on_device_changed)
        row_dev.addWidget(lbl_d)
        row_dev.addWidget(self.combo_dev, 1)
        layout.addLayout(row_dev)

        # VU Meter Box
        meter_card = QFrame()
        meter_card.setStyleSheet("background: #0f172a; border: 1px solid rgba(0,210,255,0.3); border-radius: 10px; padding: 14px;")
        m_layout = QVBoxLayout(meter_card)
        m_layout.setSpacing(10)

        self.lbl_volume = QLabel("Current Audio Level: 0 RMS | Threshold: --")
        self.lbl_volume.setStyleSheet("color: #38bdf8; font-family: monospace; font-size: 10pt; font-weight: bold;")
        m_layout.addWidget(self.lbl_volume)

        self.bar_meter = QProgressBar()
        self.bar_meter.setRange(0, 350)
        self.bar_meter.setValue(0)
        self.bar_meter.setTextVisible(False)
        self.bar_meter.setFixedHeight(22)
        self.bar_meter.setStyleSheet(
            """
            QProgressBar {
                background: #020617;
                border: 1px solid #00d2ff;
                border-radius: 11px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d2ff, stop:0.7 #00ffaa, stop:1.0 #ef4444);
                border-radius: 9px;
            }
            """
        )
        m_layout.addWidget(self.bar_meter)

        self.lbl_voice_indicator = QLabel("● SILENCE (Listening...)")
        self.lbl_voice_indicator.setStyleSheet("color: #64748b; font-weight: bold; font-size: 10.5pt;")
        m_layout.addWidget(self.lbl_voice_indicator, alignment=Qt.AlignCenter)

        layout.addWidget(meter_card)

        # Recognized Speech Output Box
        layout.addWidget(QLabel("Transcribed User Speech:"))
        self.txt_transcript = QTextEdit()
        self.txt_transcript.setReadOnly(True)
        self.txt_transcript.setFixedHeight(70)
        self.txt_transcript.setPlaceholderText("Say 'Hello JARVIS' or 'Open Chrome' to test recognition...")
        self.txt_transcript.setStyleSheet("background: #0b1526; color: #00ffea; font-size: 10.5pt; font-weight: bold; border: 1px solid rgba(0,210,255,0.3); border-radius: 6px; padding: 8px;")
        layout.addWidget(self.txt_transcript)

        # Control button
        self.btn_toggle = QPushButton("Restart Audio Stream")
        self.btn_toggle.setFixedHeight(34)
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.setStyleSheet("background: #00d2ff; color: #070e1a; font-weight: bold; border-radius: 6px;")
        self.btn_toggle.clicked.connect(self._restart_monitoring)
        layout.addWidget(self.btn_toggle)

    def _start_monitoring(self):
        dev = self.combo_dev.currentData()
        self.monitor_thread = MicMonitorThread(device_index=dev, parent=self)
        self.monitor_thread.volume_tick.connect(self._on_volume_tick)
        self.monitor_thread.speech_started.connect(self._on_speech_started)
        self.monitor_thread.transcript_ready.connect(self._on_transcript_ready)
        self.monitor_thread.start()

    def _on_device_changed(self):
        self._restart_monitoring()

    def _restart_monitoring(self):
        if self.monitor_thread and self.monitor_thread.isRunning():
            self.monitor_thread.stop()
        self._start_monitoring()

    def _on_volume_tick(self, rms: int, thresh: int):
        self.bar_meter.setValue(min(350, rms))
        self.lbl_volume.setText(f"Current Volume: {rms:3d} RMS  |  Speech Trigger: {thresh:2d} RMS")
        if rms > thresh:
            self.lbl_voice_indicator.setText("● 🎙️ VOICE CAPTURED! (Speaking Detected)")
            self.lbl_voice_indicator.setStyleSheet("color: #00ffaa; font-weight: bold; font-size: 11pt;")
        elif rms > thresh * 0.6:
            self.lbl_voice_indicator.setText("● Low Ambient Sound")
            self.lbl_voice_indicator.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 10pt;")
        else:
            self.lbl_voice_indicator.setText("● Silence (Ready)")
            self.lbl_voice_indicator.setStyleSheet("color: #64748b; font-weight: normal; font-size: 10pt;")

    def _on_speech_started(self):
        self.lbl_voice_indicator.setText("● ⏳ Processing your speech...")
        self.lbl_voice_indicator.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 11pt;")

    def _on_transcript_ready(self, text: str):
        self.txt_transcript.append(f"Heard: '{text}'")
        self.lbl_voice_indicator.setText(f"✓ Speech Recognized: '{text}'")
        self.lbl_voice_indicator.setStyleSheet("color: #00ffea; font-weight: bold; font-size: 11pt;")

    def closeEvent(self, event):
        if self.monitor_thread and self.monitor_thread.isRunning():
            self.monitor_thread.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = LiveMicTesterWindow()
    win.show()
    sys.exit(app.exec())
