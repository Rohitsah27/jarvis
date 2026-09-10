"""
Unit tests for Real-Time Duplex Voice Communication, Audio-Preserved Barge-In,
and Contextual Topic Resumption.
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from app.config import config
from core.ai.manager import ai_manager, ChatMessage
from core.ai.tool_prompt import build_tools_system_prompt
from core.voice.voice_engine import voice_engine, VoiceState

app = QApplication.instance() or QApplication(sys.argv)


class TestDuplexAndContext(unittest.TestCase):
    def setUp(self):
        config.BARGE_IN_ENABLED = True
        config.ACTIVE_CONVERSATION_HISTORY_TURNS = 16
        ai_manager.clear_history()

    def test_config_barge_in_and_turns(self):
        self.assertTrue(config.BARGE_IN_ENABLED)
        self.assertEqual(config.ACTIVE_CONVERSATION_HISTORY_TURNS, 16)

    def test_system_prompt_rules(self):
        prompt = build_tools_system_prompt("Rohit")
        self.assertIn("STRICT TOPIC GROUNDING & RELEVANCE", prompt)
        self.assertIn("REAL-TIME DUPLEX INTERRUPTIONS & TOPIC RESUMPTION", prompt)
        self.assertIn("Never wander off", prompt)

    def test_mark_last_assistant_message_interrupted(self):
        ai_manager.add_message("user", "What is quantum computing?")
        ai_manager.add_message("assistant", "Quantum computing is a rapidly-emerging technology that harnesses the laws of quantum mechanics")

        ai_manager.mark_last_assistant_message_interrupted()

        history = ai_manager.conversation_history
        self.assertEqual(len(history), 2)
        self.assertIn("[User interrupted", history[1].content)

    def test_fast_path_recorded_in_history(self):
        ai_manager.record_interaction("open chrome", "सर, गूगल क्रोम खोला जा रहा है।")
        history = ai_manager.conversation_history
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].role, "user")
        self.assertEqual(history[0].content, "open chrome")
        self.assertEqual(history[1].role, "assistant")
        self.assertEqual(history[1].content, "सर, गूगल क्रोम खोला जा रहा है।")

    def test_barge_in_interruption_not_ignored_during_speech(self):
        from ui.main_window import JarvisMainWindow

        with patch.object(voice_engine, "speak"), \
             patch.object(voice_engine, "start_continuous_listening"):
            window = JarvisMainWindow(splash=None)

            handled_prompts = []
            window._handle_user_prompt = lambda p, **kw: handled_prompts.append(p)

            # Mock voice engine as currently speaking
            with patch.object(voice_engine, "is_speaking", return_value=True), \
                 patch.object(voice_engine, "_on_barge_in_detected") as mock_barge:
                
                # User interrupts with a side question while JARVIS is speaking
                window._on_voice_transcript_received("wait what is the time right now")

                # Barge-in must be triggered and prompt must be processed!
                mock_barge.assert_called_once()
                self.assertIn("wait what is the time right now", handled_prompts)

            window.close()

    @classmethod
    def tearDownClass(cls):
        voice_engine.shutdown()


if __name__ == "__main__":
    unittest.main()
