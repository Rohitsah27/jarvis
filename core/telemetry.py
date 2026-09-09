"""
Lightweight timestamped pipeline-stage logging — the "runtime testing and
logging mode" for tracing a voice command end to end: mic input start, STT
result, agent intent (tool chosen by the fast-path router or the LLM planner),
tool success/error, TTS start, total latency.

Zero new dependencies (stdlib `logging` only). Writes to console AND a small
rotating debug file (capped ~1MB total) so a session's trace survives after
the app closes without ever becoming a real disk-space concern. Toggle off
entirely via config.DEBUG_PIPELINE_LOGGING for a quiet run.
"""
import logging
import os
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_FILE = _LOG_DIR / "jarvis_debug.log"

_logger = logging.getLogger("jarvis.pipeline")
_logger.setLevel(logging.INFO)
_logger.propagate = False

if not _logger.handlers:
    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
        _fmt = logging.Formatter("%(asctime)s.%(msecs)03d %(message)s", datefmt="%H:%M:%S")

        _console = logging.StreamHandler()
        _console.setFormatter(_fmt)
        _logger.addHandler(_console)

        # Small on purpose: 512KB x 2 files = ~1MB max, never grows unbounded.
        _file_handler = RotatingFileHandler(
            _LOG_FILE, maxBytes=512 * 1024, backupCount=1, encoding="utf-8"
        )
        _file_handler.setFormatter(_fmt)
        _logger.addHandler(_file_handler)
    except Exception as e:
        print(f"[Telemetry] Could not set up debug log file: {e}")


def _debug_logging_enabled() -> bool:
    try:
        from app.config import config
        return bool(getattr(config, "DEBUG_PIPELINE_LOGGING", True))
    except Exception:
        return True


def now() -> float:
    return time.perf_counter()


def log_stage(stage: str, t0: float = None, **fields) -> float:
    """
    Logs '[PIPELINE] STAGE  +123ms  key=val ...' to console + logs/jarvis_debug.log,
    and returns the current time.perf_counter() so callers can chain reference
    points, e.g.:
        t0 = log_stage("MIC_INPUT_START")
        ...
        log_stage("STT_RESULT", t0, text="...")
    Always returns a valid timestamp (even when logging is disabled) so timing
    chains keep working regardless of the debug-mode toggle.
    """
    t = time.perf_counter()
    if _debug_logging_enabled():
        elapsed = f"+{(t - t0) * 1000:.0f}ms" if t0 is not None else "T+0ms"
        extras = " ".join(f"{k}={v}" for k, v in fields.items())
        _logger.info(f"[PIPELINE] {stage:<18} {elapsed:>9}  {extras}".rstrip())
    return t
