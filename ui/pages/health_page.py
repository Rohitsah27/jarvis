"""
Project Health Dashboard.

Read-only view over Observe Mode + the Permission-Based Auto-Update flow:
STT/TTS engine status, whatever JARVIS is currently doing about an observed
issue, the most recent problem it noticed, whether the Claude CLI used by
run_claude_cli/auto-fix is even reachable on this machine, a rolling error
log, and the fix-task queue with its statuses.

Nothing on this page can change code or approve anything — that only ever
happens through the voice/chat confirmation flow in main_window.py. This is
purely a status mirror of core/observability/observer.py and task_queue.py.
"""
import shutil
from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
    QScrollArea,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from ui.styles.theme import theme
from app.config import config
from core.observability.observer import observer, ObservedIssue
from core.observability.task_queue import task_queue, FixTask


class StatusCard(QFrame):
    """Small card: a title, a status pill, and an optional detail line."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("StatusCard")
        self.setStyleSheet(
            f"""
            QFrame#StatusCard {{
                background-color: {theme.BG_PANEL};
                border: 1px solid rgba(0, 210, 255, 0.18);
                border-radius: 12px;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        lbl_title = QLabel(title)
        lbl_title.setFont(QFont(theme.FONT_FAMILY, 10, QFont.Bold))
        lbl_title.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; letter-spacing: 1px; background: transparent;")
        layout.addWidget(lbl_title)

        self.lbl_value = QLabel("—")
        self.lbl_value.setFont(QFont(theme.FONT_MONO, 12, QFont.Bold))
        self.lbl_value.setWordWrap(True)
        self.lbl_value.setStyleSheet(f"color: {theme.STATUS_ONLINE}; background: transparent;")
        layout.addWidget(self.lbl_value)

        self.lbl_detail = QLabel("")
        self.lbl_detail.setFont(QFont(theme.FONT_FAMILY, 8))
        self.lbl_detail.setWordWrap(True)
        self.lbl_detail.setStyleSheet(f"color: {theme.TEXT_MUTED}; background: transparent;")
        layout.addWidget(self.lbl_detail)

    def set_status(self, value: str, detail: str = "", color: Optional[str] = None):
        self.lbl_value.setText(value)
        self.lbl_detail.setText(detail)
        self.lbl_value.setStyleSheet(f"color: {color or theme.STATUS_ONLINE}; background: transparent;")


class LogRow(QFrame):
    """One line in the issue log / task queue list."""

    def __init__(self, time_str: str, tag: str, tag_color: str, message: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(8)

        lbl_time = QLabel(time_str)
        lbl_time.setFixedWidth(70)
        lbl_time.setFont(QFont(theme.FONT_MONO, 8))
        lbl_time.setStyleSheet(f"color: {theme.TEXT_MUTED}; background: transparent;")

        lbl_tag = QLabel(f"[{tag}]")
        lbl_tag.setFixedWidth(80)
        lbl_tag.setFont(QFont(theme.FONT_MONO, 8, QFont.Bold))
        lbl_tag.setStyleSheet(f"color: {tag_color}; background: transparent;")

        lbl_msg = QLabel(message)
        lbl_msg.setWordWrap(True)
        lbl_msg.setFont(QFont(theme.FONT_FAMILY, 9))
        lbl_msg.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; background: transparent;")

        layout.addWidget(lbl_time)
        layout.addWidget(lbl_tag)
        layout.addWidget(lbl_msg, 1)


class ScrollingLogPanel(QFrame):
    """Reusable scrollable list panel, used for both the issue log and the task queue."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("LogPanel")
        self.setStyleSheet(
            f"""
            QFrame#LogPanel {{
                background-color: {theme.BG_PANEL};
                border: 1px solid rgba(0, 210, 255, 0.18);
                border-radius: 12px;
            }}
            """
        )
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 10, 14, 10)
        main_layout.setSpacing(6)

        lbl_title = QLabel(title)
        lbl_title.setFont(QFont(theme.FONT_FAMILY, 9, QFont.Bold))
        lbl_title.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; letter-spacing: 1px; background: transparent;")
        main_layout.addWidget(lbl_title)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")

        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.rows_layout = QVBoxLayout(self.container)
        self.rows_layout.setContentsMargins(2, 2, 2, 2)
        self.rows_layout.setSpacing(1)
        self.rows_layout.addStretch(1)

        self.scroll_area.setWidget(self.container)
        main_layout.addWidget(self.scroll_area, 1)

    def set_rows(self, rows):
        """rows: list of (time_str, tag, tag_color, message) tuples, newest first."""
        while self.rows_layout.count() > 1:
            item = self.rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not rows:
            empty = QLabel("Nothing to show yet.")
            empty.setFont(QFont(theme.FONT_FAMILY, 9))
            empty.setStyleSheet(f"color: {theme.TEXT_MUTED}; background: transparent;")
            self.rows_layout.insertWidget(0, empty)
            return
        for i, (time_str, tag, tag_color, message) in enumerate(rows):
            self.rows_layout.insertWidget(i, LogRow(time_str, tag, tag_color, message, parent=self))


_ISSUE_COLORS = {
    "critical": "#ff4d4d",
    "error": "#ff4d4d",
    "warning": "#ffb800",
    "info": "#38bdf8",
}
_TASK_COLORS = {
    "pending": "#8da3c0",
    "approved": "#38bdf8",
    "running": "#b366ff",
    "completed": "#00ff9d",
    "failed": "#ff4d4d",
    "rejected": "#506580",
}


class HealthPage(QWidget):
    """Project Health dashboard — read-only status mirror, refreshes on a timer
    plus instantly whenever the observer or task queue signal an update."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

        observer.issue_observed.connect(lambda *_: self.refresh())
        task_queue.task_updated.connect(lambda *_: self.refresh())

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(4000)

        self.refresh()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 14, 20, 14)
        main_layout.setSpacing(14)

        lbl_head = QLabel("PROJECT HEALTH DASHBOARD")
        lbl_head.setFont(QFont(theme.FONT_DISPLAY, 12, QFont.Bold))
        lbl_head.setStyleSheet(f"color: {theme.CYAN_ACCENT}; letter-spacing: 1.5px;")
        main_layout.addWidget(lbl_head)

        grid = QGridLayout()
        grid.setSpacing(14)

        self.card_stt = StatusCard("SPEECH-TO-TEXT")
        self.card_tts = StatusCard("TEXT-TO-SPEECH")
        self.card_claude = StatusCard("CLAUDE CLI CONNECTION")
        self.card_task = StatusCard("CURRENT TASK")
        self.card_issue = StatusCard("LAST OBSERVED ISSUE")
        self.card_update = StatusCard("LAST UPDATE")

        grid.addWidget(self.card_stt, 0, 0)
        grid.addWidget(self.card_tts, 0, 1)
        grid.addWidget(self.card_claude, 0, 2)
        grid.addWidget(self.card_task, 1, 0)
        grid.addWidget(self.card_issue, 1, 1)
        grid.addWidget(self.card_update, 1, 2)
        main_layout.addLayout(grid)

        lists_layout = QHBoxLayout()
        lists_layout.setSpacing(14)

        self.panel_issues = ScrollingLogPanel("OBSERVED ISSUES (LATEST FIRST)")
        self.panel_tasks = ScrollingLogPanel("FIX TASK QUEUE (LATEST FIRST)")

        lists_layout.addWidget(self.panel_issues, 1)
        lists_layout.addWidget(self.panel_tasks, 1)
        main_layout.addLayout(lists_layout, 1)

    def refresh(self):
        self._refresh_stt()
        self._refresh_tts()
        self._refresh_claude()
        self._refresh_current_task()
        self._refresh_last_issue()
        self._refresh_last_update()
        self._refresh_lists()

    def _refresh_stt(self):
        try:
            from core.voice.stt_engine import stt_engine
            status = stt_engine.status_summary()
        except Exception as e:
            status = f"Unknown ({e})"
        color = theme.STATUS_ONLINE if status.startswith("Ready") else (
            theme.STATUS_WARNING if "Degraded" in status or "Not loaded" in status else theme.STATUS_ERROR
        )
        self.card_stt.set_status(status, f"Engine: {getattr(config, 'STT_ENGINE', '?')}", color)

    def _refresh_tts(self):
        engine_mode = getattr(config, "TTS_ENGINE", "edge").lower().strip()
        try:
            if engine_mode in ("edge", "edge_tts"):
                from core.voice.edge_tts_engine import edge_tts_engine
                status = edge_tts_engine.status_summary()
            elif engine_mode == "xtts":
                from core.voice.xtts_engine import xtts_engine
                status = xtts_engine.status_summary()
            else:
                from core.voice.kokoro_engine import kokoro_engine
                status = kokoro_engine.status_summary()
        except Exception as e:
            status = f"Unknown ({e})"
        color = theme.STATUS_ONLINE if status.startswith("Ready") else (
            theme.STATUS_WARNING if "Not loaded" in status else theme.STATUS_ERROR
        )
        self.card_tts.set_status(status, f"Engine: {engine_mode}", color)

    def _refresh_claude(self):
        # run_claude_cli / the auto-fix flow both shell out to the "claude"
        # binary — if it isn't even on PATH, approving a fix would just fail
        # immediately, so surface that here rather than after the fact.
        path = shutil.which("claude")
        if path:
            self.card_claude.set_status("Reachable", path, theme.STATUS_ONLINE)
        else:
            self.card_claude.set_status("Not found on PATH", "run_claude_cli / auto-fix would fail", theme.STATUS_ERROR)

    def _refresh_current_task(self):
        task = task_queue.get_current_task()
        if task is None:
            self.card_task.set_status("Idle", "No fix currently in progress", theme.TEXT_MUTED)
        else:
            self.card_task.set_status(task.status.upper(), task.description[:80], theme.STATUS_THINKING)

    def _refresh_last_issue(self):
        issue: Optional[ObservedIssue] = observer.get_last_issue()
        if issue is None:
            self.card_issue.set_status("None", "No problems observed yet", theme.STATUS_ONLINE)
        else:
            color = _ISSUE_COLORS.get(issue.severity, theme.STATUS_WARNING)
            self.card_issue.set_status(issue.category, f"{issue.summary[:80]} ({issue.readable_time})", color)

    def _refresh_last_update(self):
        finished = [t for t in task_queue.get_recent_tasks(50) if t.status in ("completed", "failed")]
        if not finished:
            self.card_update.set_status("Never", "No fix has been applied yet", theme.TEXT_MUTED)
        else:
            last = finished[0]
            color = theme.STATUS_ONLINE if last.status == "completed" else theme.STATUS_ERROR
            self.card_update.set_status(last.status.upper(), last.readable_time, color)

    def _refresh_lists(self):
        issue_rows = [
            (issue.readable_time.split(" ")[-1], issue.category, _ISSUE_COLORS.get(issue.severity, theme.STATUS_WARNING), issue.summary)
            for issue in observer.get_recent_issues(30)
        ]
        self.panel_issues.set_rows(issue_rows)

        task_rows = [
            (task.readable_time.split(" ")[-1], task.status, _TASK_COLORS.get(task.status, theme.TEXT_MUTED), task.description)
            for task in task_queue.get_recent_tasks(30)
        ]
        self.panel_tasks.set_rows(task_rows)
