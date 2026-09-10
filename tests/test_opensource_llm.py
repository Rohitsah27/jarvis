import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding='utf-8')

from core.ai.manager import ai_manager
from core.ai.opensource_provider import OpenSourceLLMProvider

def test_llm():
    print("Testing Open-Source LLM Provider Integration...")
    p = OpenSourceLLMProvider()
    print(f"Active Provider Name: {ai_manager.active_provider_name}")
    print(f"Ollama local daemon status: {'Online' if p.is_ollama_available() else 'Offline (Using Built-in Local Neural NLU)'}")
    
    test_cases = [
        ("open the chrome browser", "open_browser"),
        ("take a screenshot", "take_screenshot"),
        ("open visual studio code", "open_application"),
        ("show system status", "get_system_status"),
        ("नमस्ते जार्विस, आप क्या कर सकते हैं?", None),
    ]
    
    for prompt, expected_tool in test_cases:
        res = ai_manager.ask(prompt)
        tools = [t.tool_name for t in res.tool_calls]
        print(f"\nUser: '{prompt}'")
        print(f"JARVIS: '{res.content}'")
        print(f"Tools Detected: {tools}")
        if expected_tool:
            assert expected_tool in tools, f"Expected {expected_tool} in {tools}"
            
    print("\n[SUCCESS] Open-Source LLM Provider verified successfully!")

if __name__ == "__main__":
    test_llm()
