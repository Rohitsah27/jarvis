"""
Kokoro Neural Text-to-Speech Engine for JARVIS.
Provides completely free, offline, studio-quality speech synthesis:
- English: Kokoro bm_george (Deep, authoritative British JARVIS) or bm_daniel
- Hindi:   Kokoro hm_omega (Deep Hindi male) or hm_psi (Calm Hindi male)
Features automatic language detection (English vs. Hindi) and model caching.
"""
import asyncio
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Iterator, Optional, Tuple

try:
    import soundfile as sf
    from kokoro_onnx import Kokoro
    HAS_KOKORO = True
except Exception:
    HAS_KOKORO = False

from app.config import config
from core.voice.pronunciation import (
    detect_language,
    preprocess_for_speech,
    split_into_sentences,
    split_leading_clause,
    strip_markdown_for_speech,
)


class KokoroEngine:
    """Local Kokoro ONNX Speech Synthesizer."""

    _instance: Optional["KokoroEngine"] = None

    def __init__(self):
        self._kokoro: Optional[Kokoro] = None
        self._loaded = False
        # Guards _ensure_loaded(): the startup preload thread (TTSPreloadWorker)
        # and the first real speak() call race to load the model at app launch
        # without this — both would load the ~310MB fp32 model concurrently,
        # each paying the ~1.3-2.7s load cost instead of one paying it once.
        self._load_lock = threading.Lock()
        self._models_dir = Path(__file__).resolve().parent / "models"
        # NOTE: deliberately fp32, not int8. Measured on this machine: the int8
        # model has RTF ~2.1 (5.7s to synthesize 2.75s of audio) because this
        # onnxruntime build has no fused int8 kernels for Kokoro's ops, so it
        # dequantizes/requantizes around every op — actually SLOWER than fp32,
        # which measured RTF ~0.5 (1.4s for the same clip). This was the root
        # cause of "Kokoro made responses slow". Bigger file (~310MB vs ~88MB),
        # clearly worth it for 4x the speed.
        self._model_path = self._models_dir / "kokoro-v1.0.onnx"
        self._voices_path = self._models_dir / "voices-v1.0.bin"

    @classmethod
    def get_instance(cls) -> "KokoroEngine":
        if cls._instance is None:
            cls._instance = KokoroEngine()
        return cls._instance

    def is_available(self) -> bool:
        """Checks if Kokoro library and model files are present."""
        return HAS_KOKORO and self._model_path.exists() and self._voices_path.exists()

    def _ensure_loaded(self) -> bool:
        if self._loaded and self._kokoro:
            return True

        # Whichever thread gets here first does the actual load; any other
        # thread (e.g. the startup preload racing a real speak() call) just
        # waits for it instead of redundantly loading the model a second time.
        with self._load_lock:
            if self._loaded and self._kokoro:
                return True

            if not self.is_available():
                # Try auto-downloading if missing
                try:
                    from core.voice.download_kokoro import ensure_kokoro_models
                    if not ensure_kokoro_models():
                        return False
                except Exception as e:
                    print(f"[KokoroEngine] Auto-download error: {e}")
                    return False

            try:
                print("[KokoroEngine] Loading Kokoro Neural ONNX Model into memory...")
                start_t = time.perf_counter()
                self._kokoro = Kokoro(str(self._model_path), str(self._voices_path))
                self._loaded = True
                load_time = (time.perf_counter() - start_t) * 1000.0
                print(f"[KokoroEngine] Kokoro TTS ready ({load_time:.1f}ms).")
                return True
            except Exception as e:
                print(f"[KokoroEngine] Failed to initialize Kokoro: {e}")
                self._loaded = False
                return False

    @staticmethod
    def detect_language(text: str) -> str:
        """Kept for API compatibility \u2014 delegates to the canonical,
        engine-independent implementation in core/voice/pronunciation.py,
        shared by every TTS engine."""
        return detect_language(text)

    def _voice_for(self, lang: str, voice_override: Optional[str]) -> str:
        if voice_override:
            return voice_override
        if lang == "hi":
            return config.KOKORO_HINDI_VOICE or "hm_omega"
        return config.KOKORO_ENGLISH_VOICE or "bm_george"

    def synthesize(self, text: str, voice_override: Optional[str] = None, speed: Optional[float] = None) -> Optional[str]:
        """
        Synthesizes text into a temporary WAV audio file (full utterance,
        blocking until entirely done). Returns the absolute filepath of the
        generated audio, or None on failure. Kept as the non-streaming path
        used by engines/callers that need a complete file (XTTS/ElevenLabs
        share the same playback code, voice audition buttons, etc) — prefer
        synthesize_stream() for anything played live to the user, since it
        starts producing audio immediately instead of waiting for the whole
        reply to finish generating.
        """
        if not self._ensure_loaded():
            return None

        effective_speed = speed or config.KOKORO_SPEED

        if voice_override:
            # An explicit voice override always means "speak the whole thing
            # with this exact voice" — no per-language segmentation.
            cleaned_text = strip_markdown_for_speech(text)
            if not cleaned_text:
                return None
            segments = [(cleaned_text, detect_language(cleaned_text))]
        else:
            segments = preprocess_for_speech(text)
            if not segments:
                return None

        try:
            import numpy as np
            all_samples = []
            sample_rate = None
            for seg_text, seg_lang in segments:
                seg_text = seg_text.strip()
                if not seg_text:
                    continue
                chosen_voice = self._voice_for(seg_lang, voice_override)
                lang_code = "hi" if seg_lang == "hi" else "en-us"
                samples, sr = self._kokoro.create(
                    seg_text, voice=chosen_voice, speed=effective_speed, lang=lang_code,
                )
                if samples is not None and len(samples):
                    all_samples.append(samples)
                    sample_rate = sr

            if not all_samples:
                return None

            combined = np.concatenate(all_samples) if len(all_samples) > 1 else all_samples[0]

            # Write to unique temp file
            tmp_wav = os.path.join(tempfile.gettempdir(), f"jarvis_tts_{int(time.time() * 1000)}.wav")
            sf.write(tmp_wav, combined, sample_rate)
            return tmp_wav
        except Exception as e:
            print(f"[KokoroEngine] Synthesis error for '{text[:30]}...': {e}")
            return None

    def synthesize_stream(
        self, text: str, voice_override: Optional[str] = None, speed: Optional[float] = None
    ) -> Iterator[Tuple["object", int]]:
        """
        Yields (samples: np.ndarray[float32], sample_rate: int) chunks AS
        Kokoro generates them, instead of blocking until the whole utterance
        is synthesized — this is what actually cuts the dead-air-before-
        JARVIS-speaks lag, since playback can start on the first chunk while
        the rest is still being produced.

        Mixed Hindi/English text is split into per-language segments first,
        and known recurring English terms (JARVIS, WhatsApp, API, ...) are
        rewritten to a Devanagari spelling the Hindi voice pronounces
        correctly — both handled by the engine-independent
        core.voice.pronunciation.preprocess_for_speech() pipeline, shared by
        every TTS engine, not duplicated here.

        kokoro-onnx's create_stream() is an async generator; this wraps it in
        a local event loop scoped to this call so callers (a plain QThread,
        not asyncio) can consume it with an ordinary for-loop — no project-
        wide asyncio adoption needed.
        """
        if not self._ensure_loaded():
            return

        effective_speed = speed or config.KOKORO_SPEED

        if voice_override:
            # An explicit voice override (e.g. an audition button) always
            # means "speak the whole thing with this exact voice" — no
            # per-language segmentation in that case.
            cleaned_text = strip_markdown_for_speech(text)
            if not cleaned_text:
                return
            segments = [(cleaned_text, detect_language(cleaned_text))]
        else:
            segments = preprocess_for_speech(text)
            if not segments:
                return

        # Further split each language-segment into individual sentences.
        # kokoro-onnx's own internal batching only splits when a segment
        # exceeds ~510 phonemes, so without this a typical short reply (one
        # language, a sentence or two) becomes exactly ONE batch — the
        # first "streamed" chunk IS the whole reply, so no audio plays
        # until the entire thing has finished synthesizing. Splitting per
        # sentence here means the first sentence starts playing while later
        # ones are still being generated, which is the actual fix for the
        # dead-air gap before JARVIS starts speaking on ordinary replies.
        sentence_segments: list[tuple[str, str]] = []
        for seg_text, seg_lang in segments:
            for sentence in split_into_sentences(seg_text):
                sentence_segments.append((sentence, seg_lang))
        segments = sentence_segments or segments

        # Time-to-first-audio is set entirely by how long the FIRST sentence
        # takes to synthesize (everything after it is already hidden behind
        # streaming + background prefetch). If that first sentence is long,
        # shrink just its opening clause so there's less to synthesize
        # before any sound plays at all — the rest of that sentence follows
        # immediately after with no extra gap (same prefetch mechanism).
        if segments:
            first_text, first_lang = segments[0]
            lead_parts = split_leading_clause(first_text)
            if len(lead_parts) == 2:
                segments = [(lead_parts[0], first_lang), (lead_parts[1], first_lang)] + segments[1:]

        # Producer/consumer handoff: without this, sentence N+1 only starts
        # synthesizing once the CALLER has finished consuming (i.e. playing)
        # every chunk of sentence N, because a plain generator only runs
        # between yields. That serializes "play sentence N" and "synthesize
        # sentence N+1" into one straight line, so every sentence boundary
        # is an audible pause the length of that next sentence's synthesis
        # time. Running synthesis on a background thread that stays ahead
        # via a small bounded queue means sentence N+1's audio is usually
        # already sitting in the queue by the time playback asks for it —
        # Kokoro synthesizes noticeably faster than real-time (RTF ~0.5),
        # so it comfortably keeps ahead of playback in the common case.
        import queue as _queue_mod

        chunk_queue: "_queue_mod.Queue" = _queue_mod.Queue(maxsize=2)
        _DONE = object()
        # Set when the consumer stops early (barge-in interruption closes
        # this generator before it's exhausted) — without it, the producer
        # thread could block forever on a full queue nobody drains anymore,
        # leaking a stuck thread every time a reply gets interrupted, which
        # happens routinely in normal use.
        stop_event = threading.Event()

        def _put_or_stop(item) -> bool:
            """Blocking put that gives up (returning False) once stop_event
            is set, instead of blocking forever on a full, abandoned queue."""
            while not stop_event.is_set():
                try:
                    chunk_queue.put(item, timeout=0.2)
                    return True
                except _queue_mod.Full:
                    continue
            return False

        def _produce():
            loop = asyncio.new_event_loop()
            try:
                for seg_text, seg_lang in segments:
                    if stop_event.is_set():
                        return
                    seg_text = seg_text.strip()
                    if not seg_text:
                        continue

                    chosen_voice = self._voice_for(seg_lang, voice_override)
                    lang_code = "hi" if seg_lang == "hi" else "en-us"

                    try:
                        agen = self._kokoro.create_stream(
                            seg_text, voice=chosen_voice, speed=effective_speed, lang=lang_code,
                        )
                        while True:
                            if stop_event.is_set():
                                return
                            try:
                                chunk, sample_rate = loop.run_until_complete(agen.__anext__())
                            except StopAsyncIteration:
                                break
                            if chunk is not None and len(chunk):
                                if not _put_or_stop((chunk, sample_rate)):
                                    return
                    except Exception as e:
                        print(f"[KokoroEngine] Streaming synthesis error for segment '{seg_text[:30]}...': {e}")
                        continue
            finally:
                loop.close()
                if not stop_event.is_set():
                    _put_or_stop(_DONE)

        producer = threading.Thread(target=_produce, daemon=True)
        producer.start()
        try:
            while True:
                # A bare blocking get() would hang this generator (and
                # therefore the caller's for-loop consuming it, and
                # therefore the TTS worker thread) forever if the producer
                # ever genuinely stalls (e.g. a Kokoro/ONNX call that hangs
                # instead of raising) — normal synthesis of one sentence
                # never comes close to this, so hitting it means something
                # is actually wrong, and giving up is strictly better than
                # an unbounded wait with no recovery.
                try:
                    item = chunk_queue.get(timeout=20)
                except _queue_mod.Empty:
                    print("[KokoroEngine] Streaming synthesis stalled (no chunk within 20s) — aborting this utterance.")
                    break
                if item is _DONE:
                    break
                yield item
        finally:
            # Covers early abandonment (the caller breaks out of its for-loop
            # and this generator is closed/garbage-collected before
            # exhausting the queue) as well as normal completion.
            stop_event.set()


# Global singleton
kokoro_engine = KokoroEngine.get_instance()
