"""
Comprehensive automated tests for Screen Vision Analysis and Advanced Desktop Controls.
Tests NLU intent recognition, tool registration, and execution.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from core.ai.manager import ai_manager
from core.tools.tool_manager import tool_manager
from core.system.screen_analyzer import screen_analyzer

def run_tests():
    print("=" * 60)
    print("JARVIS SCREEN VISION & DESKTOP CONTROLS VERIFICATION")
    print("=" * 60)

    # Test 1: Screen Analyzer Direct
    print("\n[Test 1] Testing ScreenAnalyzer.analyze_screen()...")
    res = screen_analyzer.analyze_screen("what is showing in this screen")
    assert "answer" in res, "Missing 'answer' in analysis result"
    assert len(res["answer"]) > 10, "Answer is too short"
    print(f"✓ Analysis output: {res['answer']}")

    # Test 2: NLU Intent - 'what is showing in this screen'
    print("\n[Test 2] Testing NLU Intent: 'what is showing in this screen'...")
    resp = ai_manager.ask("what is showing in this screen")
    assert len(resp.tool_calls) > 0, "Expected tool call for screen question"
    assert resp.tool_calls[0].tool_name == "analyze_screen", f"Expected analyze_screen, got {resp.tool_calls[0].tool_name}"
    print(f"✓ Tool Call: {resp.tool_calls[0].tool_name}")
    print(f"✓ Spoken Response: {resp.content}")

    # Test 3: NLU Intent - Hindi 'स्क्रीन पर क्या दिख रहा है'
    print("\n[Test 3] Testing NLU Intent (Hindi): 'स्क्रीन पर क्या दिख रहा है'...")
    resp_hi = ai_manager.ask("स्क्रीन पर क्या दिख रहा है")
    assert len(resp_hi.tool_calls) > 0
    assert resp_hi.tool_calls[0].tool_name == "analyze_screen"
    print(f"✓ Tool Call: {resp_hi.tool_calls[0].tool_name}")
    print(f"✓ Hindi Response: {resp_hi.content}")

    # Test 4: NLU Intent - Window Controls ('minimize window')
    print("\n[Test 4] Testing NLU Intent: 'minimize window'...")
    resp_win = ai_manager.ask("minimize window")
    assert any(c.tool_name == "control_window" for c in resp_win.tool_calls)
    print(f"✓ Tool Call: {resp_win.tool_calls[0].tool_name} with args {resp_win.tool_calls[0].arguments}")

    # Test 5: NLU Intent - Volume Controls ('volume up', 'mute')
    print("\n[Test 5] Testing NLU Intent: 'volume up' & 'mute'...")
    resp_vol = ai_manager.ask("volume up")
    assert any(c.tool_name == "control_volume" for c in resp_vol.tool_calls)
    assert resp_vol.tool_calls[0].arguments.get("action") == "up"
    print(f"✓ Volume Up Tool: {resp_vol.tool_calls[0].tool_name} -> {resp_vol.tool_calls[0].arguments}")

    resp_mute = ai_manager.ask("आवाज़ बंद करो म्यूट करो")
    assert any(c.tool_name == "control_volume" for c in resp_mute.tool_calls)
    assert resp_mute.tool_calls[0].arguments.get("action") == "mute"
    print(f"✓ Mute Tool: {resp_mute.tool_calls[0].tool_name} -> {resp_mute.tool_calls[0].arguments}")

    # Test 6: NLU Intent - Media Controls ('pause music')
    print("\n[Test 6] Testing NLU Intent: 'pause music'...")
    resp_med = ai_manager.ask("pause music")
    assert any(c.tool_name == "control_media" for c in resp_med.tool_calls)
    print(f"✓ Media Tool: {resp_med.tool_calls[0].tool_name} -> {resp_med.tool_calls[0].arguments}")

    # Test 7: Tool Execution - analyze_screen tool via ToolManager
    print("\n[Test 7] Executing analyze_screen tool via ToolManager...")
    tool_res = tool_manager.execute_tool("analyze_screen", query="what is on my screen")
    assert tool_res.success, f"Tool execution failed: {tool_res.error}"
    print(f"✓ ToolManager Result: {tool_res.output}")

    print("\n" + "=" * 60)
    print("ALL 7 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
