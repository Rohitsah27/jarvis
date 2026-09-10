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

    # Test tool intent detection. When a real cloud LLM is configured (as
    # opposed to the deterministic offline regex brain), this makes an
    # actual network call, and real models don't emit the [ACTION: ...]
    # tag with 100% consistency on every sampling — a security fix removed
    # the fallback that used to silently paper over that by substituting
    # the offline brain's own tool-call guess whenever the real model's
    # response had none (see core/ai/*_provider.py — that fallback let an
    # action execute that neither the user nor the selected AI actually
    # approved, so it's gone for good). A couple of retries tolerates
    # ordinary sampling variance while still catching a genuine regression
    # (parsing broken, or the model never producing the tag at all).
    tool_calls = []
    last_content = ""
    for attempt in range(3):
        response_screenshot = ai_manager.ask("Take a screenshot of the screen")
        tool_calls = response_screenshot.tool_calls
        last_content = response_screenshot.content
        if tool_calls:
            break
    assert tool_calls, f"Failed to parse screenshot tool call after 3 attempts (last reply: {last_content[:80]!r})"
    print(f"[OK] Tool intent detected: {tool_calls[0].tool_name}")


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

    # Reuse an existing QApplication instance if one is already running
    # (e.g. this file collected alongside the rest of tests/ under a
    # single `pytest` invocation, which creates one via conftest.py's
    # session-scoped `qapp` fixture) — PySide6 raises if you try to
    # construct a second QApplication/QGuiApplication in one process, and
    # this file is also runnable standalone via `python
    # tests/test_components.py`, where no prior instance exists yet.
    app = JarvisApplication.instance()
    if app is None:
        app = JarvisApplication(sys.argv)
    window = JarvisMainWindow()
    assert window is not None

    # Test page switches
    for page_idx in range(12):
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

