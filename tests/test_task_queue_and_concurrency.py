"""
Tests for core/observability/task_queue.py's atomic persistence and
thread-safety, plus cross-cutting concurrency tests (observer ids,
overlapping AutoFix proposals).
"""
import json
import threading

import pytest


@pytest.fixture
def isolated_task_queue(qapp, tmp_path, monkeypatch):
    import core.observability.task_queue as tq_module

    monkeypatch.setattr(tq_module, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(tq_module, "_QUEUE_FILE", tmp_path / "fix_task_queue.json")
    queue = tq_module.TaskQueue()
    return queue, tmp_path


def test_task_queue_atomic_write_no_tmp_left_behind(isolated_task_queue):
    queue, tmp_path = isolated_task_queue
    queue.create_task(issue_id="1", description="test task")
    assert not (tmp_path / "fix_task_queue.json.tmp").exists()
    assert (tmp_path / "fix_task_queue.json").exists()
    data = json.loads((tmp_path / "fix_task_queue.json").read_text(encoding="utf-8"))
    assert len(data) == 1


def test_task_queue_concurrent_create_unique_ids(isolated_task_queue):
    """Spawns many threads creating tasks simultaneously — every resulting
    id must be unique, no duplicates from the old unguarded
    self._next_id += 1 race."""
    queue, tmp_path = isolated_task_queue
    results = []
    lock = threading.Lock()

    def _worker(i):
        task = queue.create_task(issue_id=str(i), description=f"task {i}")
        with lock:
            results.append(task.id)

    threads = [threading.Thread(target=_worker, args=(i,)) for i in range(30)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert len(results) == 30
    assert len(set(results)) == 30, f"duplicate ids produced: {results}"


def test_task_queue_corrupted_file_backed_up_not_lost(isolated_task_queue):
    queue, tmp_path = isolated_task_queue
    (tmp_path / "fix_task_queue.json").write_text("not valid json {{{", encoding="utf-8")

    import core.observability.task_queue as tq_module
    reloaded = tq_module.TaskQueue()  # triggers _load()

    assert reloaded._tasks == []  # starts clean, doesn't crash
    backups = list(tmp_path.glob("fix_task_queue.corrupt.*.json"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "not valid json {{{"


def test_task_queue_set_status_updates_and_persists(isolated_task_queue):
    queue, tmp_path = isolated_task_queue
    task = queue.create_task(issue_id="1", description="test")
    updated = queue.set_status(task.id, "completed", "all good")
    assert updated.status == "completed"
    assert updated.result_summary == "all good"

    data = json.loads((tmp_path / "fix_task_queue.json").read_text(encoding="utf-8"))
    assert data[0]["status"] == "completed"


# --- Observer concurrency --------------------------------------------------

def test_observer_concurrent_record_issue_unique_ids(qapp, tmp_path, monkeypatch):
    import core.observability.observer as obs_module

    monkeypatch.setattr(obs_module, "_LOG_DIR", tmp_path)
    monkeypatch.setattr(obs_module, "_ISSUES_FILE", tmp_path / "observed_issues.jsonl")
    service = obs_module.ObserverService()

    results = []
    lock = threading.Lock()

    def _worker(i):
        issue = service.record_issue("test", f"issue {i}", source="concurrency_test")
        with lock:
            results.append(issue.id)

    threads = [threading.Thread(target=_worker, args=(i,)) for i in range(30)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert len(results) == 30
    assert len(set(results)) == 30, f"duplicate observer issue ids: {results}"


def test_observer_file_bounded_not_unbounded(qapp, tmp_path, monkeypatch):
    """The on-disk file must stay capped at _MAX_ISSUES_KEPT, not just the
    in-memory list — the original bug appended forever regardless of the
    in-memory cap."""
    import core.observability.observer as obs_module

    monkeypatch.setattr(obs_module, "_LOG_DIR", tmp_path)
    monkeypatch.setattr(obs_module, "_ISSUES_FILE", tmp_path / "observed_issues.jsonl")
    monkeypatch.setattr(obs_module, "_MAX_ISSUES_KEPT", 5)
    service = obs_module.ObserverService()

    for i in range(20):
        service.record_issue("test", f"issue {i}", source="bound_test")

    lines = (tmp_path / "observed_issues.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 5


# --- AutoFix overlapping proposals ------------------------------------------

@pytest.fixture
def isolated_auto_fix_manager(qapp, tmp_path, monkeypatch):
    """AutoFixManager.propose_fix()/handle_reply() call the MODULE-LEVEL
    task_queue singleton internally (core.observability.auto_fix.task_queue),
    which by default is the real logs/fix_task_queue.json — redirect that
    singleton's storage to a temp file for the duration of the test so we
    never write real task-history pollution into the user's actual log."""
    import core.observability.task_queue as tq_module
    import core.observability.auto_fix as auto_fix_module

    monkeypatch.setattr(tq_module, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(tq_module, "_QUEUE_FILE", tmp_path / "fix_task_queue.json")
    isolated_queue = tq_module.TaskQueue()
    monkeypatch.setattr(auto_fix_module, "task_queue", isolated_queue)

    return auto_fix_module.AutoFixManager()


def test_autofix_rejects_new_proposal_while_one_is_running(qapp, isolated_auto_fix_manager):
    from core.observability.observer import ObservedIssue

    mgr = isolated_auto_fix_manager
    mgr.mark_running("some-task-id")

    issue = ObservedIssue(id="99", timestamp=0.0, category="test", summary="test issue")
    question = mgr.propose_fix(issue)

    assert "already running" in question.lower()
    assert mgr.is_awaiting_confirmation() is False  # no new pending task was created

    mgr.mark_finished("some-task-id")


def test_autofix_pending_state_survives_until_worker_actually_starts(qapp, isolated_auto_fix_manager):
    """Approving a fix must not immediately clear is_fix_running() —
    that's set by the worker itself (mark_running), not by approval."""
    from core.observability.observer import ObservedIssue

    mgr = isolated_auto_fix_manager
    issue = ObservedIssue(id="1", timestamp=0.0, category="test", summary="test")
    mgr.propose_fix(issue)
    assert mgr.is_awaiting_confirmation() is True

    outcome = mgr.handle_reply("yes")
    approved, task = outcome
    assert approved is True
    assert mgr.is_awaiting_confirmation() is False  # confirmation phase over
    assert mgr.is_fix_running() is False  # but nothing is "running" until mark_running() is called

    mgr.mark_running(task.id)
    assert mgr.is_fix_running() is True
    mgr.mark_finished(task.id)
    assert mgr.is_fix_running() is False
