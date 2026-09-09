"""
Voice Engine supporting Real Windows SAPI Text-to-Speech synthesis and
Continuous Microphone Speech Recognition via PyAudio & SpeechRecognition.
Ensures JARVIS is always hearing the user and talks back vocally.
"""
from enum import Enum
import json
import math
import os
import random
import sys
import tempfile
import time
from typing import Optional
import urllib.request

from PySide6.QtCore import QObject, Signal, QTimer, QThread

try:
    import speech_recognition as sr
    HAS_SR = True
except Exception:
    sr = None
    HAS_SR = False

try:
    import win32com.client
    HAS_SAPI = True
except Exception:
    HAS_SAPI = False

try:
    import webrtcvad
    HAS_VAD = True
except Exception:
    webrtcvad = None
    HAS_VAD = False

from app.config import config
from core.telemetry import now as telemetry_now, log_stage


class VoiceState(Enum):
    OFF = "MIC OFF"
    READY = "MIC READY"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    SPEAKING = "SPEAKING"


class SpeechSynthesisWorker(QThread):
    """Thread for non-blocking ElevenLabs Neural TTS and Windows SAPI fallback."""

    playback_started = Signal()
    synthesis_finished = Signal()
    amplitude_tick = Signal(float)

    def __init__(self, text: str, parent: Optional[QObject] = None, pipeline_t0: Optional[float] = None):
        super().__init__(parent)
        self.text = text
        self._running = True
        self._playback_started_emitted = False
        self._alias = f"jarvis_tts_{int(time.time() * 1000)}"
        self.pipeline_t0 = pipeline_t0

    def _notify_playback_start(self):
        """Emits playback_started exactly once when audio playback actually begins on the speaker device."""
        if not self._playback_started_emitted:
            self._playback_started_emitted = True
            self.playback_started.emit()

    @staticmethod
    def _find_output_device(p, device_name_substring: str):
        """Returns [(hostApi, index, info), ...] output devices whose name
        matches device_name_substring, WASAPI first — shared by the WAV-file
        path and the streaming path so device selection can't drift between
        the two. See _play_wav_via_device for why WASAPI is prioritized."""
        candidates = []
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info.get("maxOutputChannels", 0) > 0 and device_name_substring.lower() in str(info.get("name", "")).lower():
                candidates.append((info.get("hostApi"), i, info))
        _HOST_API_PRIORITY = {2: 0, 0: 1, 1: 2, 3: 3}
        candidates.sort(key=lambda c: _HOST_API_PRIORITY.get(c[0], 9))
        return candidates

    def _open_output_stream(self, p, device_name_substring: str, sample_rate: int):
        """Tries each candidate device (WASAPI first) until one opens
        successfully, matching the device's actual native rate/channel count
        (same reasoning as _play_wav_via_device: WASAPI shared mode can
        silently accept a mismatched format and play garbled audio instead
        of erroring). Returns (stream, native_rate, channels) or
        (None, None, None) if nothing opened."""
        import pyaudio
        for _host_api, device_index, device_info in self._find_output_device(p, device_name_substring):
            try:
                native_rate = int(device_info.get("defaultSampleRate") or sample_rate)
                device_max_ch = int(device_info.get("maxOutputChannels") or 1)
                target_channels = 2 if device_max_ch >= 2 else 1
                stream = p.open(format=pyaudio.paInt16, channels=target_channels, rate=native_rate,
                                 output=True, output_device_index=device_index)
                return stream, native_rate, target_channels
            except Exception as e:
                print(f"[VoiceEngine] Could not open output stream on device candidate: {e}")
                continue
        return None, None, None

    def _play_pcm_stream_via_device(self, chunk_iterator, device_name_substring: str, pipeline_t0=None) -> bool:
        """
        Plays (float32 samples, sample_rate) chunks through a specific output
        device AS THEY ARRIVE from a generator (e.g.
        KokoroEngine.synthesize_stream()), instead of waiting for a complete
        WAV file first — this is what actually removes the dead-air delay
        before JARVIS starts speaking. The output stream is opened lazily on
        the first chunk (Kokoro's sample rate is constant across chunks for
        one call, so the format decided then holds for the rest). Returns
        False if no candidate device could even be opened, so the caller can
        fall back to the proven buffer-then-play path — never raises.
        """
        try:
            import pyaudio
            import audioop
            import numpy as np

            p = pyaudio.PyAudio()
            stream = None
            native_rate = None
            channels = None
            first_chunk = True
            try:
                for samples, src_rate in chunk_iterator:
                    if not self._running:
                        break

                    if stream is None:
                        stream, native_rate, channels = self._open_output_stream(p, device_name_substring, src_rate)
                        if stream is None:
                            return False

                    pcm16 = (np.clip(samples, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
                    play_data = pcm16
                    if channels == 2:
                        # Kokoro's output is always mono; duplicate to both
                        # channels for a stereo-only device mix format.
                        play_data = audioop.tostereo(play_data, 2, 1, 1)
                    if native_rate != src_rate:
                        play_data, _ = audioop.ratecv(play_data, 2, channels, src_rate, native_rate, None)

                    if first_chunk:
                        log_stage("TTS_FIRST_CHUNK", pipeline_t0)
                        first_chunk = False
                        self._notify_playback_start()

                    write_chunk = 4096
                    for offset in range(0, len(play_data), write_chunk):
                        if not self._running:
                            break
                        slice_bytes = play_data[offset:offset + write_chunk]
                        stream.write(slice_bytes)
                        try:
                            rms_val = audioop.rms(slice_bytes, 2)
                            amp = min(1.0, max(0.12, rms_val / 6500.0))
                            self.amplitude_tick.emit(amp)
                        except Exception:
                            pass

                # PyAudio's blocking write() returns once data is ACCEPTED
                # into the buffer, not once it has actually finished playing
                # out through the speaker — closing the stream immediately
                # after the last write can clip the tail end of the last
                # word, which is exactly what made replies feel like they
                # stopped short instead of ending naturally. Only pause here
                # on a natural finish, not when deliberately interrupted
                # (barge-in / a newer reply superseding this one), where an
                # instant cutoff is exactly what's wanted.
                if stream is not None and self._running:
                    self.msleep(180)

                return stream is not None
            except Exception as e:
                print(f"[VoiceEngine] Streaming device playback warning: {e}")
                return stream is not None
            finally:
                if stream is not None:
                    try:
                        stream.stop_stream()
                        stream.close()
                    except Exception:
                        pass
                p.terminate()
        except Exception as e:
            print(f"[VoiceEngine] Streaming playback setup warning ({device_name_substring}): {e}")
            return False

    def _play_wav_via_device(self, filepath: str, device_name_substring: str) -> bool:
        """
        Plays a WAV file through a SPECIFIC output device by name (substring
        match), bypassing whatever Windows currently has set as the default
        playback device. This is the actual fix for "JARVIS's speech plays
        successfully but nobody hears it".

        WASAPI (host API 2) is tried FIRST, not last: for Bluetooth devices
        specifically, MME/DirectSound writes can return success without ever
        actually waking up the A2DP audio session — the call "succeeds" and
        nothing plays. WASAPI is what actually activates the session
        properly. Its tradeoff is strict shared-mode sample-rate matching
        (confirmed via direct test: opening a 24kHz stream on a 48kHz-native
        WASAPI device raises "Invalid sample rate") — handled here by
        resampling to the device's native rate with stdlib audioop instead of
        avoiding WASAPI, so Bluetooth devices get the API that actually works
        for them while wired devices still play at their native rate fine.
        Returns False (never raises) so the caller can fall back to the
        default-device MCI path if this device isn't found or playback fails.
        """
        try:
            import pyaudio
            import wave
            import audioop

            p = pyaudio.PyAudio()
            try:
                candidates = self._find_output_device(p, device_name_substring)
                if not candidates:
                    return False

                last_error = None
                for _host_api, device_index, device_info in candidates:
                    wf = wave.open(filepath, "rb")
                    try:
                        channels = wf.getnchannels()
                        sampwidth = wf.getsampwidth()
                        src_rate = wf.getframerate()
                        raw = wf.readframes(wf.getnframes())
                        fmt = p.get_format_from_width(sampwidth)

                        # Always match the device's actual native rate AND
                        # channel count up front — don't gamble on whether
                        # opening at the source format raises an exception.
                        # WASAPI shared mode can silently accept a
                        # channel-count mismatch (e.g. mono into a
                        # stereo-only Bluetooth mix format) without erroring,
                        # which plays back garbled/wrong-pitched audio
                        # instead of failing cleanly — that's what caused
                        # "unclear, wrong Hz" sound over Bluetooth earphones.
                        native_rate = int(device_info.get("defaultSampleRate") or src_rate)
                        device_max_ch = int(device_info.get("maxOutputChannels") or channels)
                        target_channels = 2 if device_max_ch >= 2 else 1

                        play_data = raw
                        if target_channels != channels:
                            if channels == 1 and target_channels == 2:
                                play_data = audioop.tostereo(play_data, sampwidth, 1, 1)
                            elif channels == 2 and target_channels == 1:
                                play_data = audioop.tomono(play_data, sampwidth, 0.5, 0.5)
                            channels = target_channels

                        if native_rate != src_rate:
                            play_data, _ = audioop.ratecv(play_data, sampwidth, channels, src_rate, native_rate, None)

                        stream = p.open(format=fmt, channels=channels, rate=native_rate,
                                         output=True, output_device_index=device_index)

                        try:
                            self._notify_playback_start()
                            chunk = 4096
                            phase = 0.0
                            for offset in range(0, len(play_data), chunk):
                                if not self._running:
                                    break
                                stream.write(play_data[offset:offset + chunk])
                                phase += 0.25
                                amp = 0.35 + 0.55 * abs(math.sin(phase * 1.6)) * random.uniform(0.85, 1.0)
                                self.amplitude_tick.emit(amp)
                            # See the matching comment in
                            # _play_pcm_stream_via_device: blocking write()
                            # returns once data is buffered, not once it has
                            # actually finished playing — closing right away
                            # can clip the last word's tail. Skip the pause
                            # on a deliberate interruption, where an instant
                            # stop is correct.
                            if self._running:
                                self.msleep(180)
                            return True
                        finally:
                            stream.stop_stream()
                            stream.close()
                    except Exception as e:
                        last_error = e
                        continue
                    finally:
                        wf.close()
                if last_error:
                    print(f"[VoiceEngine] All host APIs for '{device_name_substring}' failed; last error: {last_error}")
                return False
            finally:
                p.terminate()
        except Exception as e:
            print(f"[VoiceEngine] Device-targeted playback warning ({device_name_substring}): {e}")
            return False

    @staticmethod
    def _resolve_current_default_device_name() -> Optional[str]:
        """
        Queries Windows for whatever it CURRENTLY considers the default
        playback device (e.g. switches automatically when a Bluetooth headset
        connects/disconnects). Used so JARVIS's speech follows the same
        device the rest of the system is using, instead of a stale pin.
        """
        try:
            from pycaw.pycaw import AudioUtilities
            return AudioUtilities.GetSpeakers().FriendlyName
        except Exception as e:
            print(f"[VoiceEngine] Could not resolve current default output device: {e}")
            return None

    def _play_audio_file(self, filepath: str) -> bool:
        """Plays generated WAV or MP3 audio file using native Windows winmm with dynamic amplitude emission."""
        import ctypes
        import os

        # An explicit pin in config wins; otherwise dynamically follow
        # whatever Windows currently has as the default device, so JARVIS
        # naturally switches between speakers/Bluetooth exactly as Windows
        # does, rather than being stuck on one hardcoded target.
        target_device = getattr(config, "PREFERRED_TTS_OUTPUT_DEVICE", "") or self._resolve_current_default_device_name()
        if target_device and filepath.lower().endswith(".wav"):
            if self._play_wav_via_device(filepath, target_device):
                return True
            # Fall through to default-device MCI playback below if the
            # target device wasn't found or playback failed.

        try:
            winmm = ctypes.windll.winmm
            winmm.mciSendStringW(f'close {self._alias}', None, 0, None)
            abs_path = os.path.abspath(filepath)
            file_type = "waveaudio" if abs_path.lower().endswith(".wav") else "mpegvideo"
            open_ret = winmm.mciSendStringW(f'open "{abs_path}" type {file_type} alias {self._alias}', None, 0, None)
            if open_ret == 0:
                self._notify_playback_start()
                winmm.mciSendStringW(f'play {self._alias}', None, 0, None)
                buf = ctypes.create_unicode_buffer(128)
                phase = 0.0
                while self._running:
                    winmm.mciSendStringW(f'status {self._alias} mode', buf, 128, None)
                    mode = buf.value.lower()
                    if mode not in ("playing", "paused"):
                        break
                    phase += 0.25
                    amp = 0.35 + 0.55 * abs(math.sin(phase * 1.6)) * random.uniform(0.85, 1.0)
                    self.amplitude_tick.emit(amp)
                    self.msleep(40)

                winmm.mciSendStringW(f'stop {self._alias}', None, 0, None)
                winmm.mciSendStringW(f'close {self._alias}', None, 0, None)
                return True
        except Exception as e:
            print(f"[VoiceEngine] winmm audio playback error: {e}")

        # Fallback to pygame mixer if winmm fails
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(filepath)
            self._notify_playback_start()
            pygame.mixer.music.play()
            phase = 0.0
            while pygame.mixer.music.get_busy() and self._running:
                phase += 0.25
                amp = 0.35 + 0.55 * abs(math.sin(phase * 1.6)) * random.uniform(0.85, 1.0)
                self.amplitude_tick.emit(amp)
                self.msleep(40)
            return True
        except Exception as e:
            print(f"[VoiceEngine] pygame audio fallback error: {e}")
        return False

    def run(self):
        engine_mode = getattr(config, "TTS_ENGINE", "kokoro").lower().strip()

        # -------------------------------------------------------------
        # 0. XTTS-v2 High-Quality Neural Synthesis (Opt-in, Cloud-grade quality, slower)
        # -------------------------------------------------------------
        if engine_mode == "xtts" and self._running:
            try:
                from core.voice.xtts_engine import xtts_engine
                wav_file = xtts_engine.synthesize(self.text)
                if wav_file and os.path.exists(wav_file) and self._running:
                    played = self._play_audio_file(wav_file)
                    try:
                        os.remove(wav_file)
                    except Exception:
                        pass
                    if played:
                        self.amplitude_tick.emit(0.0)
                        self.synthesis_finished.emit()
                        return
            except Exception as e:
                print(f"[VoiceEngine] XTTS-v2 warning: {e}, falling back to Kokoro.")

        # -------------------------------------------------------------
        # 1. Kokoro Neural Speech Synthesis (Free, Offline, Studio Quality)
        # -------------------------------------------------------------
        if engine_mode in ("kokoro", "auto", "default", "xtts") and self._running:
            try:
                from core.voice.kokoro_engine import kokoro_engine

                # Streaming first: plays the first chunk as soon as it's
                # generated instead of waiting for the entire reply to
                # finish synthesizing — this is the actual fix for the
                # multi-second dead air before JARVIS starts speaking on
                # longer replies. Needs a resolvable output device to open
                # a live stream against; falls back to the proven
                # buffer-then-play path below if that's not available or
                # every candidate device fails to open (never leaves the
                # user with silence just because streaming didn't pan out).
                target_device = getattr(config, "PREFERRED_TTS_OUTPUT_DEVICE", "") or self._resolve_current_default_device_name()
                if target_device:
                    played = self._play_pcm_stream_via_device(
                        kokoro_engine.synthesize_stream(self.text), target_device, self.pipeline_t0
                    )
                    if played:
                        self.amplitude_tick.emit(0.0)
                        log_stage("TTS_DONE", self.pipeline_t0, engine="kokoro_stream")
                        self.synthesis_finished.emit()
                        return

                wav_file = kokoro_engine.synthesize(self.text)
                log_stage("TTS_SYNTH_DONE", self.pipeline_t0, engine="kokoro")
                if wav_file and os.path.exists(wav_file) and self._running:
                    played = self._play_audio_file(wav_file)
                    try:
                        os.remove(wav_file)
                    except Exception:
                        pass
                    if played:
                        self.amplitude_tick.emit(0.0)
                        log_stage("TTS_DONE", self.pipeline_t0)
                        self.synthesis_finished.emit()
                        return
            except Exception as e:
                print(f"[VoiceEngine] Kokoro TTS warning: {e}, attempting fallback.")

        # -------------------------------------------------------------
        # 2. ElevenLabs Multilingual V2 (Cloud Studio API)
        # -------------------------------------------------------------
        # CRITICAL: only take this path if the user actually selected ElevenLabs.
        # Merely having a leftover API key in config must NOT trigger this — that
        # previously meant any transient Kokoro hiccup (locked temp file, a
        # phonemizer stumble) caused the exact same reply to be spoken a SECOND
        # time through a totally different voice/engine, which is what "JARVIS
        # says everything twice" actually was.
        if engine_mode == "elevenlabs" and config.ELEVENLABS_API_KEY and self._running:
            try:
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}"
                headers = {
                    "xi-api-key": config.ELEVENLABS_API_KEY,
                    "Content-Type": "application/json",
                }
                payload = {
                    "text": self.text,
                    "model_id": config.ELEVENLABS_MODEL_ID,
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
                }

                req = urllib.request.Request(
                    url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    audio_bytes = resp.read()

                if audio_bytes and self._running:
                    tmp_file = os.path.join(tempfile.gettempdir(), f"{self._alias}.mp3")
                    with open(tmp_file, "wb") as f:
                        f.write(audio_bytes)

                    played = self._play_audio_file(tmp_file)
                    try:
                        os.remove(tmp_file)
                    except Exception:
                        pass
                    if played:
                        self.amplitude_tick.emit(0.0)
                        self.synthesis_finished.emit()
                        return
            except Exception as e:
                print(f"[VoiceEngine] ElevenLabs error ({e}), falling back to Kokoro Neural TTS...")
                # Automatic graceful fallback to Kokoro when ElevenLabs limit is reached
                try:
                    from core.voice.kokoro_engine import kokoro_engine
                    wav_file = kokoro_engine.synthesize(self.text)
                    if wav_file and os.path.exists(wav_file) and self._running:
                        played = self._play_audio_file(wav_file)
                        try:
                            os.remove(wav_file)
                        except Exception:
                            pass
                        if played:
                            self.amplitude_tick.emit(0.0)
                            self.synthesis_finished.emit()
                            return
                except Exception as e2:
                    print(f"[VoiceEngine] Secondary Kokoro fallback warning: {e2}")

        # -------------------------------------------------------------
        # 3. Windows Native SAPI David Voice (Local System Fallback)
        # -------------------------------------------------------------
        speaker = None
        if HAS_SAPI and self._running:
            try:
                import pythoncom
                pythoncom.CoInitialize()
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                speaker.Volume = config.SAPI_VOICE_VOLUME
                speaker.Rate = config.SAPI_VOICE_RATE

                voices = speaker.GetVoices()
                for i in range(voices.Count):
                    v = voices.Item(i)
                    if "David" in v.GetDescription():
                        speaker.Voice = v
                        break
            except Exception as e:
                print(f"[VoiceEngine] SAPI COM initialization error: {e}")
                speaker = None

        if speaker and self._running:
            try:
                self._notify_playback_start()
                speaker.Speak(self.text, 1)

                phase = 0.0
                while self._running:
                    done = speaker.WaitUntilDone(50)
                    if done:
                        break

                    phase += 0.25
                    amp = 0.4 + 0.5 * abs(math.sin(phase * 1.6)) * random.uniform(0.8, 1.0)
                    self.amplitude_tick.emit(amp)
            except Exception as e:
                print(f"[VoiceEngine] SAPI TTS playback error: {e}")
            finally:
                try:
                    import pythoncom
                    pythoncom.CoUninitialize()
                except Exception:
                    pass
        elif self._running:
            # 3. Tertiary: Windows PowerShell speech synthesis
            try:
                import subprocess
                clean_txt = self.text.replace('"', '').replace("'", "")
                ps_cmd = (
                    f"Add-Type -AssemblyName System.Speech; "
                    f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                    f"$s.Speak('{clean_txt}')"
                )
                self._notify_playback_start()
                subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, timeout=10)
            except Exception as e:
                print(f"[VoiceEngine] PowerShell TTS fallback error: {e}")

        log_stage("TTS_DONE", self.pipeline_t0, engine="sapi_or_fallback")
        self.amplitude_tick.emit(0.0)
        self.synthesis_finished.emit()

    def stop(self):
        self._running = False
        try:
            import ctypes
            ctypes.windll.winmm.mciSendStringW(f'stop {self._alias}', None, 0, None)
            ctypes.windll.winmm.mciSendStringW(f'close {self._alias}', None, 0, None)
        except Exception:
            pass


def get_available_microphones() -> list[tuple[Optional[int], str]]:
    """Returns list of available microphone input devices."""
    devices = [(None, "System Default Microphone")]
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) > 0 and info.get("hostApi") == 0:
                    name = info.get("name", f"Microphone {i}")
                    devices.append((i, name))
            except Exception:
                pass
        p.terminate()
    except Exception:
        pass
    return devices


class ReactiveAudioStreamWrapper:
    """Wraps PyAudio stream to capture real-time audio volume during speech recognition."""
    def __init__(self, stream, sample_width: int, callback):
        self._stream = stream
        self._sample_width = sample_width
        self._callback = callback

    def read(self, size):
        data = self._stream.read(size)
        if data and self._callback:
            rms = 0
            try:
                import audioop
                rms = audioop.rms(data, self._sample_width)
            except Exception:
                try:
                    import struct
                    count = len(data) // 2
                    if count > 0:
                        shorts = struct.unpack(f"{count}h", data)
                        rms = int(math.sqrt(sum(s * s for s in shorts) / count))
                except Exception:
                    rms = 0
            try:
                self._callback(rms)
            except Exception:
                pass
        return data

    def close(self):
        try:
            return self._stream.close()
        except Exception:
            pass

    def __getattr__(self, name):
        return getattr(self._stream, name)


class ContinuousMicListenerThread(QThread):
    """Background listener continuously capturing voice from user's microphone."""

    speech_detected = Signal()
    transcript_ready = Signal(str)
    listening_resumed = Signal()
    listening_active = Signal(bool)
    amplitude_tick = Signal(float)       # Real-time microphone RMS volume 0.0 - 1.0
    barge_in_detected = Signal()         # Loud speech detected while paused/speaking

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._running = True
        self._paused = False
        self._barge_in_armed = False
        self.recognizer = sr.Recognizer() if (HAS_SR and sr) else None
        if self.recognizer:
            self.recognizer.energy_threshold = config.MIC_ENERGY_THRESHOLD
            self.recognizer.dynamic_energy_threshold = False
            self.recognizer.pause_threshold = config.MIC_PAUSE_THRESHOLD
            self.recognizer.non_speaking_duration = 0.4

    def pause_listening(self):
        self._paused = True

    def resume_listening(self):
        self._paused = False

    def arm_barge_in(self):
        """While paused (JARVIS speaking), start watching for the user talking
        over it so speak() can be interrupted instead of ignored entirely."""
        self._barge_in_armed = True

    def disarm_barge_in(self):
        self._barge_in_armed = False

    def stop(self):
        self._running = False
        self.wait(1500)

    @staticmethod
    def _looks_like_speech(audio_data) -> bool:
        """
        Real voice-activity detection (WebRTC VAD — the same engine used in
        Chrome/WebRTC calls) run on a captured audio segment BEFORE spending
        an STT API call or flickering the UI into 'Processing' state on it.
        The plain RMS energy threshold that gates recognizer.listen() only
        asks "was this loud enough?" — a fan, a door, background chatter, or
        a cough are all "loud enough" but aren't speech, which is exactly why
        JARVIS kept lighting up on every ambient sound in a noisy room. VAD
        asks "does this actually sound like a human voice?" frame by frame.
        Fails OPEN (treats it as speech) on any error, so a VAD hiccup never
        blocks genuine commands — worst case it behaves like before.
        """
        if not HAS_VAD:
            return True
        try:
            vad = webrtcvad.Vad(2)  # 0=least aggressive filtering, 3=most
            raw = audio_data.get_raw_data(convert_rate=16000, convert_width=2)
            frame_ms = 30
            frame_bytes = int(16000 * (frame_ms / 1000.0) * 2)  # 16-bit mono PCM
            total = 0
            speech = 0
            for i in range(0, len(raw) - frame_bytes + 1, frame_bytes):
                frame = raw[i:i + frame_bytes]
                total += 1
                if vad.is_speech(frame, 16000):
                    speech += 1
            if total == 0:
                return True  # too short to judge — don't block it
            return (speech / total) >= 0.2
        except Exception as e:
            print(f"[VoiceEngine] VAD check warning (failing open): {e}")
            return True

    def run(self):
        if not HAS_SR or not sr or not self.recognizer:
            self.listening_active.emit(False)
            return

        mic = None
        try:
            device_index = config.MIC_DEVICE_INDEX
            mic = sr.Microphone(device_index=device_index)
        except Exception as e:
            print(f"[VoiceEngine] Selected mic {config.MIC_DEVICE_INDEX} warning: {e}, falling back to default.")
            try:
                mic = sr.Microphone()
            except Exception as e2:
                print(f"[VoiceEngine] Microphone access warning: {e2}")
                mic = None

        if not mic:
            self.listening_active.emit(False)
            return

        self.listening_active.emit(True)

        try:
            with mic as source:
                # Dynamic ambient calibration: ambient * 1.35 with floor of config.MIC_ENERGY_THRESHOLD (75) and ceiling of 180
                try:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
                    measured = self.recognizer.energy_threshold
                    self.recognizer.energy_threshold = min(max(float(config.MIC_ENERGY_THRESHOLD), measured * 1.35), 180.0)
                except Exception:
                    self.recognizer.energy_threshold = float(config.MIC_ENERGY_THRESHOLD)

                print(f"[VoiceEngine] Microphone listening active (Threshold: {self.recognizer.energy_threshold:.1f})")

                def _on_rms_chunk(rms: int):
                    if not self._running or self._paused:
                        return
                    thresh = self.recognizer.energy_threshold if self.recognizer else 75.0
                    # When user is genuinely speaking above ambient threshold
                    if rms > thresh:
                        excess = max(0.0, float(rms - thresh))
                        dynamic_range = max(100.0, float(thresh) * 1.5)
                        amp = min(1.0, 0.22 + 0.78 * min(1.0, excess / dynamic_range))
                    else:
                        # User is saying NOTHING: strictly 0.0!
                        amp = 0.0
                    self.amplitude_tick.emit(amp)

                source.stream = ReactiveAudioStreamWrapper(source.stream, source.SAMPLE_WIDTH, _on_rms_chunk)

                while self._running:
                    if self._paused:
                        if not self._barge_in_armed:
                            self.msleep(100)
                            continue

                        # Barge-in watch: JARVIS is speaking. Listen with a
                        # notably higher energy bar than normal speech so its
                        # own voice bleeding back through the speakers into the
                        # mic is less likely to false-trigger (no true acoustic
                        # echo cancellation here — headphones avoid this
                        # tradeoff entirely). Energy alone was found to
                        # false-trigger on nearly every reply in practice (the
                        # multiplied threshold still sits inside normal speech
                        # loudness), cutting JARVIS off mid-sentence — so a
                        # captured phrase must ALSO pass the WebRTC VAD gate
                        # before it counts as a genuine interruption, same bar
                        # normal listening already requires.
                        base_threshold = self.recognizer.energy_threshold
                        try:
                            self.recognizer.energy_threshold = base_threshold * config.BARGE_IN_ENERGY_MULTIPLIER
                            barge_audio = self.recognizer.listen(source, timeout=0.4, phrase_time_limit=3.0)
                            if self._barge_in_armed and self._paused and self._looks_like_speech(barge_audio):
                                print("[VoiceEngine] Barge-in detected — interrupting current speech.")
                                self.barge_in_detected.emit()
                        except sr.WaitTimeoutError:
                            pass
                        except Exception:
                            pass
                        finally:
                            self.recognizer.energy_threshold = base_threshold
                        continue

                    audio = None
                    try:
                        audio = self.recognizer.listen(
                            source, timeout=1.5, phrase_time_limit=config.MIC_PHRASE_LIMIT
                        )
                    except sr.WaitTimeoutError:
                        continue
                    except Exception as e:
                        self.msleep(100)
                        continue

                    if audio and not self._paused and self._running:
                        # VAD gate BEFORE announcing "Processing" or spending an
                        # STT call — filters out fan noise, background chatter,
                        # coughs, door slams etc. that are loud enough to cross
                        # the energy threshold but aren't actually speech.
                        if not self._looks_like_speech(audio):
                            print("[VoiceEngine] Noise filtered by VAD (not speech-like)")
                            self.listening_resumed.emit()
                            continue

                        print("[VoiceEngine] Sound captured! Processing phonemes...")
                        self.speech_detected.emit()
                        recognized_text = None

                        # 1. Primary STT: Hindi (default spoken language)
                        try:
                            text = self.recognizer.recognize_google(audio, language=config.VOICE_LANGUAGE)
                            if text and text.strip():
                                recognized_text = text.strip()
                        except Exception:
                            pass

                        # 2. Secondary STT: Indian English (en-IN) fallback for English/Hinglish phrases
                        if not recognized_text:
                            try:
                                text = self.recognizer.recognize_google(audio, language="en-IN")
                                if text and text.strip():
                                    recognized_text = text.strip()
                            except Exception:
                                pass

                        if recognized_text:
                            print(f"[VoiceEngine] Heard user speech: '{recognized_text}'")
                            self.amplitude_tick.emit(0.0)
                            # Temporarily pause listener so JARVIS can think and speak without echo or queueing
                            self._paused = True
                            self.transcript_ready.emit(recognized_text)
                        else:
                            print("[VoiceEngine] Ambient sound filtered (no words recognized)")
                            self.listening_resumed.emit()

        except Exception as e:
            print(f"[VoiceEngine] Microphone stream error: {e}")
            self.listening_active.emit(False)



class VoiceEngine(QObject):
    """
    Voice Subsystem providing continuous microphone listening and
    real Windows SAPI / ElevenLabs voice synthesis.
    """

    # Signals
    state_changed = Signal(object)      # Emits VoiceState
    transcript_ready = Signal(str)      # Emits recognized user speech text
    audio_amplitude = Signal(float)     # Emits 0.0 - 1.0 audio volume levels for animations
    speech_completed = Signal()         # Emits when JARVIS finishes speaking
    speech_interrupted = Signal()       # Emits when the user barges in over active speech

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._state = VoiceState.READY
        self._tts_worker: Optional[SpeechSynthesisWorker] = None
        self._mic_thread: Optional[ContinuousMicListenerThread] = None

        # Bumped every time a TTS worker is superseded (a new speak() call, or
        # a barge-in interruption). A worker that got interrupted mid-synthesis
        # often can't actually be killed (it's blocked inside a synchronous
        # Kokoro call stop() can't abort) and fires synthesis_finished LATE,
        # after a newer reply may already be playing — without this check that
        # stale signal would wipe out the reference to the CURRENT worker and
        # silently flip the state back to LISTENING mid-speech, which is what
        # "JARVIS cuts off and gets stuck" traced back to.
        self._tts_generation = 0

        # Safety watchdog to prevent getting stuck in PROCESSING or SPEAKING state
        self._watchdog = QTimer(self)
        self._watchdog.setSingleShot(True)
        self._watchdog.timeout.connect(self._on_watchdog_timeout)

        # Initialize continuous listener thread
        self._init_mic_thread()
        if config.ALWAYS_LISTEN:
            self.start_continuous_listening()

    def _init_mic_thread(self):
        self._mic_thread = ContinuousMicListenerThread(self)
        self._mic_thread.speech_detected.connect(self._on_mic_speech_detected)
        self._mic_thread.transcript_ready.connect(self._on_mic_transcript_ready)
        self._mic_thread.listening_resumed.connect(self._on_mic_listening_resumed)
        self._mic_thread.amplitude_tick.connect(self._on_mic_amplitude_tick)
        self._mic_thread.barge_in_detected.connect(self._on_barge_in_detected)

    def _on_mic_amplitude_tick(self, amp: float):
        if self._state == VoiceState.LISTENING:
            self.audio_amplitude.emit(amp)

    def set_microphone_device(self, device_index: Optional[int]) -> None:
        """Dynamically switches active microphone input device."""
        config.MIC_DEVICE_INDEX = device_index
        was_listening = (self._state == VoiceState.LISTENING)
        if self._mic_thread and self._mic_thread.isRunning():
            self._mic_thread.stop()
        self._init_mic_thread()
        if was_listening or config.ALWAYS_LISTEN:
            self.start_continuous_listening()

    @property
    def state(self) -> VoiceState:
        return self._state

    def set_state(self, new_state: VoiceState) -> None:
        if self._state != new_state:
            self._state = new_state
            self.state_changed.emit(self._state)

            if new_state == VoiceState.PROCESSING:
                # 4-second safety watchdog in case transcription stalls
                self._watchdog.start(4000)
            elif new_state == VoiceState.SPEAKING:
                # Generous safety watchdog in case TTS synthesis/playback
                # genuinely hangs (not the normal interrupted-worker case,
                # which is handled by generation tracking, but real hangs —
                # e.g. a wedged winmm session) — better to recover after 45s
                # than stay stuck "speaking" forever.
                self._watchdog.start(45000)
            else:
                self._watchdog.stop()

            # When quiet or returning to ready/listening, ensure amplitude is reset to 0.0
            if new_state in (VoiceState.READY, VoiceState.OFF, VoiceState.LISTENING):
                self.audio_amplitude.emit(0.0)

    def start_continuous_listening(self) -> None:
        """Starts always-listening mode so JARVIS continuously hears the user."""
        if not self._mic_thread.isRunning():
            self._mic_thread.start()
        self._mic_thread.resume_listening()
        self.set_state(VoiceState.LISTENING)

    def stop_listening(self) -> None:
        """Halts listening."""
        if self._mic_thread and self._mic_thread.isRunning():
            self._mic_thread.pause_listening()
        self.set_state(VoiceState.READY)

    def shutdown(self) -> None:
        """Fully stops all voice threads when closing the application."""
        try:
            if self._mic_thread:
                self._mic_thread.stop()
        except Exception:
            pass

        try:
            if self._tts_worker:
                self._tts_worker.stop()
                self._tts_worker.wait(1500)
        except (RuntimeError, Exception):
            pass
        self._tts_worker = None
        self.set_state(VoiceState.OFF)

    def toggle_listening(self) -> None:
        if self._state == VoiceState.LISTENING:
            self.stop_listening()
        else:
            self.start_continuous_listening()

    def is_speaking(self) -> bool:
        """Returns True if speech synthesis is currently active."""
        return self._state == VoiceState.SPEAKING or (self._tts_worker is not None and self._tts_worker.isRunning())

    def speak(self, text: str, pipeline_t0: Optional[float] = None) -> None:
        """
        Synthesize speech aloud through Windows speakers.
        Pauses full mic listening while speaking (so JARVIS doesn't transcribe
        its own voice), but arms barge-in watching so a sufficiently loud
        interruption still stops it — see ContinuousMicListenerThread's
        paused+armed branch and _on_barge_in_detected below.
        """
        if self._mic_thread and self._mic_thread.isRunning():
            self._mic_thread.pause_listening()
            if getattr(config, "BARGE_IN_ENABLED", True):
                self._mic_thread.arm_barge_in()

        # Hold state as PROCESSING during audio synthesis so the UI displays
        # "Thinking..." / "Processing..." and the mouth stays closed until sound starts
        self.set_state(VoiceState.PROCESSING)

        # Clean previous worker safely if exists
        try:
            if self._tts_worker:
                self._tts_worker.stop()
                self._tts_worker.wait(2000)
        except (RuntimeError, Exception):
            pass
        self._tts_worker = None

        self._tts_generation += 1
        my_generation = self._tts_generation

        self._tts_worker = SpeechSynthesisWorker(text, self, pipeline_t0=pipeline_t0)
        self._tts_worker.playback_started.connect(lambda: self._on_playback_started(my_generation))
        self._tts_worker.amplitude_tick.connect(self.audio_amplitude.emit)
        self._tts_worker.synthesis_finished.connect(lambda: self._on_tts_finished(my_generation))
        self._tts_worker.start()

    def _on_playback_started(self, generation: int):
        """Called the exact millisecond audio playback actually begins playing through speakers."""
        if generation != self._tts_generation:
            return
        self.set_state(VoiceState.SPEAKING)

    def _on_barge_in_detected(self):
        """The user spoke loudly enough over active TTS to count as an
        interruption: stop speaking immediately and start listening for
        whatever they're saying, instead of finishing the current reply."""
        if self._state not in (VoiceState.SPEAKING, VoiceState.PROCESSING) or self._tts_worker is None:
            return
        print("[VoiceEngine] Interrupting current speech for barge-in.")
        if self._mic_thread:
            self._mic_thread.disarm_barge_in()
        try:
            if self._tts_worker:
                self._tts_worker.stop()
        except (RuntimeError, Exception):
            pass
        self._tts_worker = None
        # Invalidate the interrupted worker's eventual signal — it's often
        # stuck inside a blocking synthesis call stop() can't abort, and will
        # still fire synthesis_finished once that call returns, long after
        # we've already moved on.
        self._tts_generation += 1
        self.speech_interrupted.emit()
        self.start_continuous_listening()

    def _on_tts_finished(self, generation: int):
        if generation != self._tts_generation:
            # Stale completion from a worker that was already superseded
            # (interrupted by barge-in, or replaced by a newer speak() call)
            # — acting on this would wipe out the CURRENT worker's reference
            # and flip state back to LISTENING while it's still genuinely
            # speaking. Just ignore it.
            print(f"[VoiceEngine] Ignoring stale TTS completion (gen {generation}, current {self._tts_generation}).")
            return

        self._tts_worker = None
        if self._mic_thread:
            self._mic_thread.disarm_barge_in()

        # If always listening is enabled, immediately resume listening
        if config.ALWAYS_LISTEN:
            self.start_continuous_listening()
        else:
            self.set_state(VoiceState.READY)

        self.speech_completed.emit()

    def _on_mic_speech_detected(self):
        self.set_state(VoiceState.PROCESSING)

    def _on_mic_transcript_ready(self, text: str):
        self._watchdog.stop()
        self.set_state(VoiceState.READY)
        self.transcript_ready.emit(text)

    def _on_mic_listening_resumed(self):
        self._watchdog.stop()
        self.set_state(VoiceState.LISTENING)

    def _on_watchdog_timeout(self):
        if self._state == VoiceState.PROCESSING:
            self.set_state(VoiceState.LISTENING)
        elif self._state == VoiceState.SPEAKING:
            # Genuine hang recovery (not the normal stale-signal case, which
            # generation tracking already handles) — force back to listening
            # rather than staying stuck "speaking" indefinitely.
            print("[VoiceEngine] Speech watchdog fired — forcing recovery to listening.")
            self._tts_generation += 1  # invalidate whatever worker is stuck
            if self._mic_thread:
                self._mic_thread.disarm_barge_in()
            self._tts_worker = None
            if config.ALWAYS_LISTEN:
                self.start_continuous_listening()
            else:
                self.set_state(VoiceState.READY)


# Global Voice Engine instance
voice_engine = VoiceEngine()
