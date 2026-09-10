"""
Unit tests for browser tab controls, tab switching power, and active tab execution.
"""
import unittest
from core.tools.tool_manager import tool_manager
from core.ai.brain import jarvis_brain


class TestBrowserTabs(unittest.TestCase):
    def test_control_tabs_tool_registered(self):
        """Ensure control_tabs tool is registered in tool_manager."""
        tool = tool_manager.get_tool("control_tabs")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "control_tabs")

    def test_brain_tab_switch_intents(self):
        """Verify brain intent mapping for tab switching and closing commands."""
        test_cases = [
            ("switch tab", "control_tabs", "next"),
            ("next tab", "control_tabs", "next"),
            ("tab badlo", "control_tabs", "next"),
            ("dusre tab par jao", "control_tabs", "next"),
            ("dusre tab pe jao", "control_tabs", "next"),
            ("agle tab me jao", "control_tabs", "next"),
            ("previous tab", "control_tabs", "previous"),
            ("pichle tab par jao", "control_tabs", "previous"),
            ("close tab", "control_tabs", "close"),
            ("tab band karo", "control_tabs", "close"),
            ("yeh tab band karo", "control_tabs", "close"),
            ("naya tab kholo", "control_tabs", "new"),
        ]

        for prompt, expected_tool, expected_action in test_cases:
            resp = jarvis_brain.think(prompt)
            self.assertGreaterEqual(len(resp.tool_calls), 1, f"Failed for prompt: {prompt}")
            tc = resp.tool_calls[0]
            self.assertEqual(tc.tool_name, expected_tool, f"Wrong tool for '{prompt}': got {tc.tool_name}")
            self.assertEqual(tc.arguments.get("action"), expected_action, f"Wrong action for '{prompt}': got {tc.arguments}")

    def test_music_playback_defaults_to_active_tab(self):
        """Verify music commands execute in CURRENT ACTIVE TAB (new_tab=False) by default."""
        prompts = [
            "play a song in youtube",
            "youtube par gana chalao",
            "kalyani song lagao",
            "play some music",
            "original song lagana",
        ]

        for p in prompts:
            resp = jarvis_brain.think(p)
            self.assertGreaterEqual(len(resp.tool_calls), 1, f"No tool calls for '{p}'")
            browser_calls = [c for c in resp.tool_calls if c.tool_name == "open_browser"]
            self.assertEqual(len(browser_calls), 1, f"Expected 1 open_browser call for '{p}'")
            self.assertIs(browser_calls[0].arguments.get("new_tab"), False, f"new_tab must be False for '{p}'")

    def test_music_playback_explicit_new_tab(self):
        """Verify music commands with explicit 'new tab' request open in a new tab."""
        prompts = [
            "open new tab and play a song in youtube",
            "naye tab me gana chalao",
            "play a song in a new tab",
        ]

        for p in prompts:
            resp = jarvis_brain.think(p)
            self.assertGreaterEqual(len(resp.tool_calls), 1, f"No tool calls for '{p}'")
            browser_calls = [c for c in resp.tool_calls if c.tool_name == "open_browser"]
            self.assertEqual(len(browser_calls), 1, f"Expected 1 open_browser call for '{p}'")
            self.assertIs(browser_calls[0].arguments.get("new_tab"), True, f"new_tab must be True for '{p}'")

    def test_combined_switch_tab_and_play(self):
        """Verify combined commands switch tab first and then navigate in that tab."""
        resp = jarvis_brain.think("switch tab and play a song in youtube")
        self.assertEqual(len(resp.tool_calls), 2)
        self.assertEqual(resp.tool_calls[0].tool_name, "control_tabs")
        self.assertEqual(resp.tool_calls[0].arguments.get("action"), "next")
        self.assertEqual(resp.tool_calls[1].tool_name, "open_browser")
        self.assertIs(resp.tool_calls[1].arguments.get("new_tab"), False)


if __name__ == "__main__":
    unittest.main()
