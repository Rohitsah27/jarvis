import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding='utf-8')

import speech_recognition as sr
import win32com.client
import pythoncom
import tempfile

def test():
    pythoncom.CoInitialize()
    speaker = win32com.client.Dispatch("SAPI.SpVoice")
    filestream = win32com.client.Dispatch("SAPI.SpFileStream")
    
    r = sr.Recognizer()
    phrases = [
        "open the chrome browser",
        "open chrome browser",
        "open chrome",
        "open the browser",
        "open browser",
        "chrome browser",
        "launch chrome",
        "open google",
    ]
    for p in phrases:
        filestream = win32com.client.Dispatch("SAPI.SpFileStream")
        tmp_wav = os.path.join(tempfile.gettempdir(), "test_phrase.wav")
        filestream.Open(tmp_wav, 3, False)
        speaker.AudioOutputStream = filestream
        speaker.Speak(p)
        filestream.Close()
        
        with sr.AudioFile(tmp_wav) as source:
            audio = r.record(source)
            
        print(f"Phrase '{p}':")
        try:
            hi_text = r.recognize_google(audio, language="hi-IN")
            print(f"  [hi-IN]: '{hi_text}'")
        except Exception as e:
            print(f"  [hi-IN]: err {e}")
            
        try:
            en_text = r.recognize_google(audio, language="en-IN")
            print(f"  [en-IN]: '{en_text}'")
        except Exception as e:
            print(f"  [en-IN]: err {e}")

if __name__ == "__main__":
    test()
