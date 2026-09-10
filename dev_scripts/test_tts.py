"""
Test script to verify SAPI TTS directly.
"""
import win32com.client
import pythoncom
import time

def test():
    print("Initializing COM...")
    pythoncom.CoInitialize()
    speaker = win32com.client.Dispatch("SAPI.SpVoice")
    speaker.Volume = 100
    speaker.Rate = 1
    
    # Choose David
    voices = speaker.GetVoices()
    for i in range(voices.Count):
        v = voices.Item(i)
        if "David" in v.GetDescription():
            speaker.Voice = v
            break
            
    print("Speaking: 'Hello Rohit, JARVIS speech test.'")
    speaker.Speak("Hello Rohit, JARVIS speech test.", 1)
    
    while not speaker.WaitUntilDone(100):
        print(".", end="", flush=True)
        
    print("\nSpeech finished successfully!")
    pythoncom.CoUninitialize()

if __name__ == "__main__":
    test()
