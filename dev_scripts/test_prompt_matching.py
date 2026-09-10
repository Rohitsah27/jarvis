import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding='utf-8')
from core.ai.mock_provider import MockJarvisProvider

p = MockJarvisProvider()

test_phrases = [
    "open the chrome browser",
    "open chrome browser",
    "open chrome",
    "open the browser",
    "open browser",
    "launch chrome",
    "start chrome",
    "chrome",
    "क्रोम",
    "ओपन द क्रोम ब्राउजर",
    "ओपन क्रोम ब्राउज़र",
    "ओपन द क्रोम",
    "क्रोम खोलो",
    "ब्राउज़र खोलो",
    "ब्राउजर खोलो",
    "गूगल खोलो",
    "google खोलो",
    "open google",
    "open internet",
    "open youtube",
    "open web",
]

for phrase in test_phrases:
    res = p.generate_response(phrase)
    tools = [t.tool_name for t in res.tool_calls]
    is_fallback = "काम किया जा रहा है" in res.content
    print(f"[{'FALLBACK' if is_fallback else 'MATCHED'}] '{phrase}' -> tools: {tools} | content: {res.content[:30]}...")
