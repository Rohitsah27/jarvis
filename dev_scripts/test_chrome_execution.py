import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from core.ai.manager import ai_manager
from core.tools.tool_manager import tool_manager

def test_chrome_flow():
    phrases = [
        "open the chrome browser",
        "open chrome",
        "open browser",
        "क्रोम खोलो",
        "ब्राउजर खोलो",
        "ओपन द क्रोम ब्राउजर",
        "गूगल खोलो",
    ]
    for prompt in phrases:
        print(f"\n--- Testing prompt: '{prompt}' ---")
        response = ai_manager.ask(prompt)
        print(f"Response Content: {response.content}")
        assert len(response.tool_calls) > 0, f"Tool call expected for '{prompt}'"
        call = response.tool_calls[0]
        assert call.tool_name == "open_browser"
        print(f"[OK] Intent verified: {call.tool_name}")
    print("\n[SUCCESS] All Chrome & Browser phrases verified end-to-end!")

if __name__ == "__main__":
    test_chrome_flow()
