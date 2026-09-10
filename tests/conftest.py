"""
Shared pytest fixtures for the JARVIS test suite.

Sets QT_QPA_PLATFORM=offscreen before any Qt import (required for CI/headless
runs — no real display) and provides a single session-scoped QApplication,
since PySide6 QObjects (including several classes under test here) generally
need one to exist.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


@pytest.fixture(scope="session")
def qapp():
    from app.config import config
    config.ALWAYS_LISTEN = False  # tests must never spin up a real mic thread
    from app.application import JarvisApplication
    app = JarvisApplication.instance()
    if app is None:
        app = JarvisApplication(sys.argv)
    yield app


@pytest.fixture(autouse=True)
def _reset_confirmation_service(qapp):
    """
    Every test gets a clean ConfirmationService listener state — a test
    that attaches a handler and forgets to detach it would otherwise leak
    into later tests and silently change their fail-closed/fail-open
    behavior.
    """
    from core.tools.confirmation import confirmation_service

    def _reset():
        if confirmation_service._listener_count > 0:
            try:
                confirmation_service.confirmation_requested.disconnect()
            except (RuntimeError, TypeError):
                pass
        confirmation_service._listener_count = 0

    _reset()
    yield
    _reset()


@pytest.fixture
def approve_all(qapp):
    """Attaches a handler that approves every confirmation request. Returns
    the list of requests it saw, so a test can assert on what was asked."""
    from core.tools.confirmation import confirmation_service

    seen = []

    def _handler(req):
        seen.append(req)
        confirmation_service.resolve(req.request_id, True, reason="test_auto_approve")

    confirmation_service.attach_handler(_handler)
    yield seen
    confirmation_service.detach_handler(_handler)


@pytest.fixture
def deny_all(qapp):
    """Attaches a handler that denies every confirmation request."""
    from core.tools.confirmation import confirmation_service

    seen = []

    def _handler(req):
        seen.append(req)
        confirmation_service.resolve(req.request_id, False, reason="test_auto_deny")

    confirmation_service.attach_handler(_handler)
    yield seen
    confirmation_service.detach_handler(_handler)
