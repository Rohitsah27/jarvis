"""
Live Voice Test Script for JARVIS.
Monitors microphone in real time, displays live energy volume meter,
and transcribes speech as soon as you speak.
"""
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import speech_recognition as sr
import audioop

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def run_live_test(duration=10):
    print("=" * 60)
    print("        JARVIS LIVE MICROPHONE & VOICE TEST")
    print("=" * 60)

    recognizer = sr.Recognizer()
    
    # Check default mic
    try:
        mic = sr.Microphone()
    except Exception as e:
        print(f"[ERROR] Could not open microphone: {e}")
        return

    with mic as source:
        print("\n[Step 1] Measuring ambient silence for 1 second... Please stay quiet.")
        recognizer.adjust_for_ambient_noise(source, duration=1.0)
        ambient = recognizer.energy_threshold
        # Optimal speech threshold: comfortably above ambient
        calibrated_thresh = max(70, int(ambient * 1.35))
        recognizer.energy_threshold = calibrated_thresh

        print(f"[INFO] Measured Ambient Silence: {ambient:.1f}")
        print(f"[INFO] Calibrated Speech Trigger Threshold: {calibrated_thresh}")
        print("\n[Step 2] LIVE AUDIO MONITORING STARTED for next 5 seconds.")
        print(">>> PLEASE SPEAK SOMETHING NOW (e.g. 'Hello JARVIS' or 'Open Chrome') <<<\n")

        start = time.time()
        max_rms_seen = 0

        while time.time() - start < 5.0:
            chunk = source.stream.read(source.CHUNK)
            rms = audioop.rms(chunk, source.SAMPLE_WIDTH)
            if rms > max_rms_seen:
                max_rms_seen = rms

            # Build visual ASCII meter with standard chars
            bars = int(min(25, rms / 15))
            meter = "#" * bars + "-" * (25 - bars)
            status = ">>> SPEECH DETECTED! <<<" if rms > calibrated_thresh else "Silence"
            
            print(f"\r[Vol: {rms:4d}] |{meter}| {status:24s}", end="", flush=True)
            time.sleep(0.08)

        print(f"\n\n[INFO] Live monitoring finished. Peak volume detected: {max_rms_seen} RMS")

        if max_rms_seen > calibrated_thresh:
            print("[SUCCESS] Your microphone is CAPTURING your voice successfully!")
        else:
            print("[WARNING] Volume was low. If using OnePlus Nord Buds 2r or external headset, ensure it is set as active.")

        print("\n[Step 3] Now recording a test phrase for speech recognition...")
        print(">>> SPEAK A COMMAND NOW (e.g. 'Open Chrome') <<<")
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            print("\n[INFO] Sound captured! Transcribing with Google STT...")
            try:
                text = recognizer.recognize_google(audio, language="en-IN")
                print(f"[RECOGNIZED (en-IN)]: '{text}'")
            except Exception:
                try:
                    text = recognizer.recognize_google(audio, language="hi-IN")
                    print(f"[RECOGNIZED (hi-IN)]: '{text}'")
                except Exception as e:
                    print(f"[NOTICE] No clear words recognized: {e}")
        except sr.WaitTimeoutError:
            print("\n[NOTICE] Listening timed out (no speech detected above threshold).")
        except Exception as e:
            print(f"\n[ERROR] Audio listen error: {e}")

    print("\n" + "=" * 60)
    print("                    TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    run_live_test()
