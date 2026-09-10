import os
import ctypes
import time

alias = "test_kokoro_wav"
path = os.path.abspath("tests/test_kokoro_en.wav")
winmm = ctypes.windll.winmm

winmm.mciSendStringW(f"close {alias}", None, 0, None)
ret = winmm.mciSendStringW(f'open "{path}" type waveaudio alias {alias}', None, 0, None)
print("Open ret:", ret)
if ret == 0:
    winmm.mciSendStringW(f"play {alias}", None, 0, None)
    buf = ctypes.create_unicode_buffer(64)
    while True:
        winmm.mciSendStringW(f"status {alias} mode", buf, 64, None)
        if buf.value.lower() != "playing":
            break
        time.sleep(0.05)
    winmm.mciSendStringW(f"close {alias}", None, 0, None)
    print("Playback finished successfully!")
