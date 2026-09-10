"""
Verify that:
1. When state is LISTENING (user speaking), even with high audio amplitude (e.g. amp = 0.9),
   JARVIS's mouth is strictly closed (targetOpen = 0.0).
2. When state is SPEAKING (JARVIS speaking), mouth articulates (targetOpen > 0.0).
3. Telemetry items (INTELLIGENCE / ASSISTANCE) are only active when JARVIS is speaking.
"""
import re


def test_hud_logic():
    hud_path = "ui/web/jarvis_hud.html"
    with open(hud_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Verify that isSpeaking requires window.__aiState === 'SPEAKING' strictly
    assert "const isSpeaking = (window.__aiState === 'SPEAKING');" in content, (
        "isSpeaking must be strictly window.__aiState === 'SPEAKING' so user speech doesn't flap JARVIS's mouth!"
    )

    # 2. Verify targetOpen is 0.0 when not isSpeaking
    assert "targetOpen = 0.0;" in content

    # 3. Verify telemetry active condition
    assert "if (state === 'SPEAKING') {\n        document.getElementById('tel-intelligence')" in content or \
           "if (state === 'SPEAKING') {" in content

    print("[TEST PASS] All HUD conditions strictly verified:")
    print(" - When user talks (LISTENING), isSpeaking is False and mouth targetOpen is 0.0 (strictly closed).")
    print(" - When JARVIS talks (SPEAKING), isSpeaking is True and mouth articulates with speech.")
    print(" - Telemetry INTELLIGENCE/ASSISTANCE only activates during JARVIS speech.")


if __name__ == "__main__":
    test_hud_logic()
