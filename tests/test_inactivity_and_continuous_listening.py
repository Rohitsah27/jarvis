"""
Test for continuous voice listening and 15-minute inactivity standby timeout.
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from app.config import config
from core.voice.voice_engine import voice_engine, VoiceState
from ui.components.ai_core import AICoreState

# Create QApplication if not exists
app = QApplication.instance() or QApplication(sys.argv)


class TestContinuousListeningAndTimeout(unittest.TestCase):
    def setUp(self):
        config.ALWAYS_LISTEN = True
        config.VOICE_INACTIVITY_TIMEOUT_MINUTES = 15

    def test_config_defaults(self):
        self.assertTrue(config.ALWAYS_LISTEN)
        self.assertEqual(config.VOICE_INACTIVITY_TIMEOUT_MINUTES, 15)

    def test_voice_engine_transcript_ready_does_not_drop_to_ready(self):
        # When transcript is received, state must stay PROCESSING, not drop to READY
        voice_engine.set_state(VoiceState.PROCESSING)
        received_text = []
        voice_engine.transcript_ready.connect(lambda t: received_text.append(t))

        voice_engine._on_mic_transcript_ready("hello jarvis")

        self.assertEqual(received_text, ["hello jarvis"])
        self.assertEqual(voice_engine.state, VoiceState.PROCESSING)

    def test_main_window_speech_completed_keeps_listening_and_arms_timer(self):
        from ui.main_window import JarvisMainWindow

        # Mock background preloaders so tests instantiate window cleanly
        with patch.object(voice_engine, "speak"), \
             patch.object(voice_engine, "start_continuous_listening"):
            window = JarvisMainWindow(splash=None)

            # Simulate completion of assistant speech
            window._on_speech_completed()

            # Should be in Listening... mode
            self.assertEqual(window.title_bar.status_capsule._text, "Listening...")
            self.assertEqual(window.page_home.ai_core.state, AICoreState.LISTENING)
            self.assertTrue(window.page_home.mic_btn.isEnabled())
            self.assertTrue(window._voice_inactivity_timer.isActive())
            self.assertEqual(window._voice_inactivity_timer.interval(), 15 * 60 * 1000)

            # Now simulate 15 minutes inactivity timeout firing
            window._on_voice_inactivity_timeout()

            # Should transition to System Online / IDLE
            self.assertEqual(window.title_bar.status_capsule._text, "System Online")
            self.assertEqual(window.page_home.ai_core.state, AICoreState.IDLE)
            self.assertFalse(window._voice_inactivity_timer.isActive())

            window.close()

    @classmethod
    def tearDownClass(cls):
        voice_engine.shutdown()


if __name__ == "__main__":
    unittest.main()
