import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ctypes
import time
from core.voice.kokoro_engine import kokoro_engine

wav = kokoro_engine.synthesize("Hello sir, testing.")
print("Wav path:", wav)

winmm = ctypes.windll.winmm
alias = "test_mci_alias"
winmm.mciSendStringW(f"close {alias}", None, 0, None)
ret = winmm.mciSendStringW(f'open "{wav}" type waveaudio alias {alias}', None, 0, None)
print("Open ret:", ret)
winmm.mciSendStringW(f"play {alias}", None, 0, None)

buf = ctypes.create_unicode_buffer(128)
for i in range(40):
    winmm.mciSendStringW(f"status {alias} mode", buf, 128, None)
    val = buf.value.lower()
    print(f"i={i}, mode={val}")
    if val not in ("playing", "paused"):
        print("Loop ended! Mode was:", val)
        break
    time.sleep(0.1)

winmm.mciSendStringW(f"close {alias}", None, 0, None)
print("Done!")
