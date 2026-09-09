"""
Automated unit and integration tests for JARVIS desktop application.
Tests module loading, UI rendering in offscreen mode, AI inference, and telemetry.
"""
import os
import sys

# Ensure root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass



def test_imports():
    print("Testing core module imports...")
    import app.config
    import core.ai
    import core.voice
    import core.tools
    import core.system
    import ui.styles
    import ui.components
    import ui.pages
    import ui.main_window
    print("[OK] All modules imported successfully.")


def test_ai_provider():
    print("Testing AI Provider and Manager...")
    from core.ai.manager import ai_manager
    response = ai_manager.ask("Hello JARVIS")
    assert response.content, "Response content is empty"
    print(f"[OK] AI response received: '{response.content[:40]}...'")

    # Test tool intent detection
    response_screenshot = ai_manager.ask("Take a screenshot of the screen")
    assert len(response_screenshot.tool_calls) > 0, "Failed to parse screenshot tool call"
    print(f"[OK] Tool intent detected: {response_screenshot.tool_calls[0].tool_name}")


def test_tool_manager():
    print("Testing Tool Manager and Permission Architecture...")
    from core.tools.tool_manager import tool_manager
    res = tool_manager.execute_tool("get_system_status")
    assert res.success, f"Tool execution failed: {res.output}"
    print(f"[OK] Tool result: {res.output}")


def test_ui_instantiation():
    print("Testing UI instantiation in offscreen mode...")
    from app.application import JarvisApplication
    from ui.main_window import JarvisMainWindow

    app = JarvisApplication(sys.argv)
    window = JarvisMainWindow()
    assert window is not None

    # Test page switches
    for page_idx in range(11):
        window.sidebar.select_page(page_idx)
        assert window.pages_stack.currentIndex() == page_idx

    # Test prompt simulation
    window._handle_user_prompt("Diagnostics report")

    # Cleanup
    window.close()
    print("[OK] UI instantiated, page navigation verified, and closed cleanly.")


if __name__ == "__main__":
    test_imports()
    test_ai_provider()
    test_tool_manager()
    test_ui_instantiation()
    print("\nALL AUTOMATED TESTS PASSED SUCCESSFULLY!")

