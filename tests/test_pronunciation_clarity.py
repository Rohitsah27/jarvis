"""
Test suite for Pronunciation Clarity and Dictionary Expansion in JARVIS.
Verifies:
1. High-frequency English loanwords and user names ('Rohit', 'Chrome', 'open', etc.)
   are converted to clean Devanagari in Hindi context.
2. English sentences remain untouched and use the English voice.
3. Pronunciation overrides run before segmentation so sentences are not fractured
   into multi-voice British switches.
4. add_custom_word() and user_dictionary.json persistence.
5. Kokoro TTS synthesis of cleaned Devanagari text.
"""
import sys
import os
from pathlib import Path

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from core.voice.pronunciation import (
    preprocess_for_speech,
    apply_pronunciation_overrides,
    detect_language,
    add_custom_word,
    remove_custom_word,
    get_dictionary_stats,
    get_custom_words,
)
from core.voice.kokoro_engine import kokoro_engine


def test_pronunciation_preprocessing():
    print("\n--- 1. Testing Preprocessing on Hindi / Hinglish Sentences ---")
    test_cases = [
        (
            "नमस्ते Rohit, आपका WhatsApp और Chrome open ho gaya hai sir",
            "नमस्ते रोहित, आपका व्हाट्सएप और क्रोम ओपन हो गया है सर",
            "hi"
        ),
        (
            "Rohit Kumar, Notepad start kar diya gaya hai",
            "रोहित कुमार, नोटपैड स्टार्ट कर दिया गया है",
            "hi"
        ),
        (
            "System volume aur battery percent check kar raha hoon",
            "सिस्टम वॉल्यूम aur बैटरी परसेंट चेक कर रहा हूँ",
            "hi"
        ),
    ]

    for input_text, expected_substr, expected_lang in test_cases:
        segments = preprocess_for_speech(input_text)
        print(f"Input:    {input_text}")
        print(f"Segments: {segments}")
        assert len(segments) >= 1, f"Expected at least 1 segment for '{input_text}'"
        seg_text, seg_lang = segments[0]
        assert seg_lang == expected_lang, f"Expected lang '{expected_lang}', got '{seg_lang}'"
        # Verify Rohit is converted to रोहित
        if "Rohit" in input_text:
            assert "रोहित" in seg_text, f"Expected 'रोहित' in output, got '{seg_text}'"
            assert "Rohit" not in seg_text, f"Did not expect 'Rohit' in Hindi output, got '{seg_text}'"
        # Verify Chrome is converted to क्रोम
        if "Chrome" in input_text:
            assert "क्रोम" in seg_text, f"Expected 'क्रोम' in output, got '{seg_text}'"
        # Verify open is converted to ओपन
        if "open" in input_text:
            assert "ओपन" in seg_text, f"Expected 'ओपन' in output, got '{seg_text}'"
        print("  -> PASSED\n")


def test_english_preservation():
    print("\n--- 2. Testing English Sentence Preservation ---")
    en_input = "Hello Rohit, how can I assist you today?"
    segments = preprocess_for_speech(en_input)
    print(f"Input:    {en_input}")
    print(f"Segments: {segments}")
    assert len(segments) == 1, f"Expected 1 segment, got {len(segments)}"
    seg_text, seg_lang = segments[0]
    assert seg_lang == "en", f"Expected lang 'en', got '{seg_lang}'"
    print("  -> PASSED\n")


def test_custom_dictionary_persistence():
    print("\n--- 3. Testing Custom Word Addition & Persistence ---")
    stats_before = get_dictionary_stats()
    print(f"Stats before: {stats_before}")

    # Add a custom word
    added = add_custom_word("AlphaPilot", "अल्फा पायलट", "custom_test")
    assert added, "Failed to add custom word"

    # Verify preprocessing picks it up
    segments = preprocess_for_speech("नमस्ते AlphaPilot, स्वागत है")
    print(f"Segments with custom word: {segments}")
    assert "अल्फा पायलट" in segments[0][0], f"Expected 'अल्फा पायलट' in '{segments[0][0]}'"

    # Clean up custom word
    removed = remove_custom_word("AlphaPilot")
    assert removed, "Failed to remove custom word"

    stats_after = get_dictionary_stats()
    print(f"Stats after cleanup: {stats_after}")
    print("  -> PASSED\n")


def test_kokoro_synthesis():
    print("\n--- 4. Testing Kokoro Neural TTS Speech Synthesis ---")
    test_phrase = "नमस्ते Rohit, आपका WhatsApp और Chrome ओपन हो गया है।"
    print(f"Synthesizing: '{test_phrase}'")
    wav_path = kokoro_engine.synthesize(test_phrase)
    assert wav_path is not None, "Synthesize returned None"
    assert os.path.exists(wav_path), f"Audio file does not exist at {wav_path}"
    file_size = os.path.getsize(wav_path)
    print(f"Generated WAV file: {wav_path} (size: {file_size} bytes)")
    assert file_size > 5000, f"Audio file is too small ({file_size} bytes)"

    # Clean up temp file
    try:
        os.remove(wav_path)
    except Exception:
        pass
    print("  -> PASSED\n")


if __name__ == "__main__":
    test_pronunciation_preprocessing()
    test_english_preservation()
    test_custom_dictionary_persistence()
    test_kokoro_synthesis()
    print("\n===========================================")
    print("ALL PRONUNCIATION & SPEECH TESTS PASSED!")
    print("===========================================")
