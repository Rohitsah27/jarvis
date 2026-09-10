"""
Fix-task queue for the Permission-Based Auto-Update flow and the Project
Health dashboard. One task is created per observed issue the user has
been asked about — its status tracks the whole lifecycle so the dashboard
always has something concrete to show, even if nothing is currently running.

Statuses: pending -> approved -> running -> completed | failed
          (pending -> rejected if the user declines instead of approving)
"""
import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("jarvis.task_queue")

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
_QUEUE_FILE = _DATA_DIR / "fix_task_queue.json"

_MAX_TASKS_KEPT = 200


@dataclass
class FixTask:
    id: str
    issue_id: str
    description: str        # the task description that would be/was sent to Claude
    status: str = "pending"  # pending | approved | rejected | running | completed | failed
    created_at: float = 0.0
    updated_at: float = 0.0
    result_summary: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def readable_time(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.updated_at or self.created_at))


class TaskQueue(QObject):
    """Global singleton — same convention as ObserverService."""

    task_updated = Signal(object)  # FixTask

    _instance: Optional["TaskQueue"] = None

    def __init__(self):
        super().__init__()
        self._tasks: List[FixTask] = []
        self._next_id = 1
        # Guards _next_id's read-modify-write AND every read/mutate of
        # _tasks — record_issue()-equivalent calls here (create_task,
        # set_status) can come from multiple QThreads (tool workers, the
        # global excepthook, AutoFixWorker) concurrently. Without this,
        # two threads could read the same _next_id and produce two tasks
        # with a duplicated id, corrupting id-based lookups.
        self._lock = threading.Lock()
        self._load()

    @classmethod
    def get_instance(cls) -> "TaskQueue":
        if cls._instance is None:
            cls._instance = TaskQueue()
        return cls._instance

    def _load(self):
        if not _QUEUE_FILE.exists():
            return
        try:
            raw = _QUEUE_FILE.read_text(encoding="utf-8")
            data = json.loads(raw)
            self._tasks = [FixTask(**t) for t in data][-_MAX_TASKS_KEPT:]
            if self._tasks:
                self._next_id = max(int(t.id) for t in self._tasks) + 1
        except Exception as e:
            # A corrupt file must not silently vanish along with the
            # user's task history — preserve it alongside the real path
            # (timestamped, so a second corruption doesn't clobber the
            # first) so it can be inspected/recovered, and log clearly
            # instead of a console-only print swallowed once the app runs
            # without an attached terminal.
            logger.error("Could not load %s (%s: %s) — starting with an empty queue.", _QUEUE_FILE, type(e).__name__, e)
            try:
                if _QUEUE_FILE.exists():
                    backup = _QUEUE_FILE.with_name(f"fix_task_queue.corrupt.{int(time.time())}.json")
                    _QUEUE_FILE.replace(backup)
                    logger.error("Preserved corrupt queue file at %s for diagnosis.", backup)
            except Exception:
                pass
            print(f"[TaskQueue] Could not load existing queue: {e}")

    def _save_locked(self):
        """Caller must already hold self._lock."""
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            payload = json.dumps([t.to_dict() for t in self._tasks], ensure_ascii=False, indent=2)
            # Atomic write: a crash/power-loss mid-write must never leave
            # fix_task_queue.json half-written — a partial JSON file would
            # fail to parse on next load and silently discard the ENTIRE
            # task history, not just the one write in progress. Write to a
            # temp file in the same directory (guarantees the rename below
            # is on the same filesystem, hence atomic) and replace only
            # once the full write has succeeded and been flushed to disk.
            tmp_path = _QUEUE_FILE.with_suffix(".json.tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, _QUEUE_FILE)
        except Exception as e:
            logger.error("Could not save %s: %s", _QUEUE_FILE, e)
            print(f"[TaskQueue] Could not save queue: {e}")

    def create_task(self, issue_id: str, description: str) -> FixTask:
        with self._lock:
            task = FixTask(
                id=str(self._next_id), issue_id=issue_id, description=description,
                status="pending", created_at=time.time(), updated_at=time.time(),
            )
            self._next_id += 1
            self._tasks.append(task)
            self._tasks = self._tasks[-_MAX_TASKS_KEPT:]
            self._save_locked()
        self.task_updated.emit(task)
        return task

    def set_status(self, task_id: str, status: str, result_summary: str = "") -> Optional[FixTask]:
        with self._lock:
            task = None
            for t in self._tasks:
                if t.id == task_id:
                    t.status = status
                    t.updated_at = time.time()
                    if result_summary:
                        t.result_summary = result_summary[:1000]
                    task = t
                    break
            if task is not None:
                self._save_locked()
        if task is not None:
            self.task_updated.emit(task)
        return task

    def get_recent_tasks(self, n: int = 20) -> List[FixTask]:
        with self._lock:
            return list(reversed(self._tasks[-n:]))

    def get_current_task(self) -> Optional[FixTask]:
        """The most recent task still in flight (approved/running), or None
        if nothing is currently being worked on — what the dashboard's
        'Current Task' field shows."""
        with self._lock:
            for task in reversed(self._tasks):
                if task.status in ("approved", "running"):
                    return task
        return None


# Global singleton
task_queue = TaskQueue.get_instance()
