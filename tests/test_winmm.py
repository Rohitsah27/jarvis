import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import ctypes
import time
import urllib.request
import json
import tempfile
from app.config import config

def test_winmm():
    print("Generating Elevenlabs test MP3...")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": config.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": "टेस्ट",
        "model_id": config.ELEVENLABS_MODEL_ID,
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        audio = resp.read()
        
    tmp_mp3 = os.path.join(tempfile.gettempdir(), "test_winmm.mp3")
    with open(tmp_mp3, "wb") as f:
        f.write(audio)
    print(f"Saved {len(audio)} bytes to {tmp_mp3}")
    
    winmm = ctypes.windll.winmm
    alias = "test_alias"
    winmm.mciSendStringW(f'close {alias}', None, 0, None)
    ret = winmm.mciSendStringW(f'open "{tmp_mp3}" type mpegvideo alias {alias}', None, 0, None)
    print("open ret:", ret)
    ret = winmm.mciSendStringW(f'play {alias}', None, 0, None)
    print("play ret:", ret)
    
    buf = ctypes.create_unicode_buffer(128)
    for _ in range(50):
        winmm.mciSendStringW(f'status {alias} mode', buf, 128, None)
        mode = buf.value.lower()
        if mode not in ("playing", "paused"):
            break
        time.sleep(0.05)
        
    winmm.mciSendStringW(f'stop {alias}', None, 0, None)
    winmm.mciSendStringW(f'close {alias}', None, 0, None)
    print("Playback finished cleanly with winmm!")

if __name__ == "__main__":
    test_winmm()
