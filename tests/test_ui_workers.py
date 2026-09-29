"""Deterministic cancellation, stale signal, and worker lifetime regressions."""

import threading
import time

import pytest

pytest.importorskip("PyQt6")
from PyQt6.QtCore import QCoreApplication, QEvent

from prompt_manager.core.arena import ArenaResult
from prompt_manager.integrations.llm_providers import LLMResponse
from prompt_manager.ui.components import arena_dialog, github_dialog, preview_panel


def process_until(qapp, predicate):
    deadline = time.monotonic() + 3
    while not predicate() and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.001)
    assert predicate()


@pytest.mark.parametrize("kind", ["preview", "arena", "oauth"])
def test_cancelled_job_cannot_update_or_clear_new_job(qapp, monkeypatch, kind):
    release = threading.Event()
    entered = threading.Event()
    calls = 0

    def response(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            entered.set()
            assert release.wait(3)
        return "answer"

    if kind == "preview":
        widget = preview_panel.PreviewPanel()
        widget.set_content("hello")
        monkeypatch.setattr(preview_panel.PollinationsClient, "generate", response)
        start = widget.run_pollinations
        cancel = widget.cancel_pollinations
        current = lambda: widget._poll_worker
        thread = lambda: widget._poll_thread
        result = lambda: widget.ai_response_edit.toPlainText()
    elif kind == "arena":
        widget = arena_dialog.ArenaDialog(prompt="hello")
        def compare(*args, **kwargs):
            response()
            return ArenaResult("hello", "", [LLMResponse(content="answer", model_id="pollinations:openai-fast")])
        monkeypatch.setattr(arena_dialog, "run_arena_comparison", compare)
        start = widget.run_arena
        cancel = widget.cancel_arena
        current = lambda: widget._worker
        thread = lambda: widget._worker_thread
        result = lambda: widget.card1.output_edit.toPlainText()
    else:
        widget = github_dialog.GithubDialog()
        def poll(worker):
            response()
            worker.error_occurred.emit("answer")
        monkeypatch.setattr(github_dialog._DevicePollWorker, "_poll", poll)
        monkeypatch.setattr(github_dialog.QMessageBox, "warning", lambda *args: None)
        start = lambda: widget._start_poll_thread("client", "code", 5, 60)
        cancel = widget._cancel_device_flow
        current = lambda: widget._poll_worker
        thread = lambda: widget._poll_thread
        result = lambda: widget.oauth_poll_status.text()

    start()
    old_thread = thread()
    assert old_thread.wait(3000)  # Queue the old result without delivering it.
    cancel()
    start()
    new_thread = thread()
    try:
        assert entered.wait(3)
        new_worker = current()
        qapp.processEvents()
        assert current() is new_worker
        assert result() != "answer"
        release.set()
        process_until(qapp, lambda: current() is None)
        assert result() == "answer"
    finally:
        release.set()
        new_thread.wait(3000)
        widget.deleteLater()
        qapp.processEvents()


def test_destroying_originating_widget_keeps_blocked_job_alive(qapp, monkeypatch):
    entered = threading.Event()
    release = threading.Event()
    def generate(*args, **kwargs):
        entered.set()
        assert release.wait(3)
        return "late answer"

    monkeypatch.setattr(preview_panel.PollinationsClient, "generate", generate)
    widget = preview_panel.PreviewPanel()
    widget.set_content("hello")
    widget.run_pollinations()
    thread = widget._poll_thread
    try:
        assert entered.wait(3)
        widget.cancel_pollinations()
        assert thread.isRunning()
        widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        assert thread.isRunning()
    finally:
        release.set()
        assert thread.wait(3000)
        qapp.processEvents()


def test_worker_initialization_error_is_reported(qapp, monkeypatch):
    widget = preview_panel.PreviewPanel()
    widget.set_content("hello")
    def fail(*args, **kwargs):
        raise ValueError("invalid client configuration")
    monkeypatch.setattr(preview_panel, "PollinationsClient", fail)
    widget.run_pollinations()
    thread = widget._poll_thread
    try:
        process_until(qapp, lambda: widget._poll_worker is None)
        assert "invalid client configuration" in widget.ai_response_edit.toPlainText()
    finally:
        thread.wait(3000)
        widget.deleteLater()
        qapp.processEvents()


def test_oauth_cancellation_during_request_does_not_accept_token(monkeypatch):
    from unittest.mock import MagicMock
    worker = github_dialog._DevicePollWorker("client", "code", 5, 60)
    received = []
    worker.token_received.connect(received.append)
    def read():
        worker.stop()
        return b'{"access_token": "cancelled-token"}'
    response = MagicMock()
    response.__enter__.return_value.read.side_effect = read
    monkeypatch.setattr(worker._stop_event, "wait", lambda _: False)
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: response)
    worker.run_poll()
    assert received == []


def test_shutdown_interrupts_oauth_polling_wait(qapp):
    from prompt_manager.ui.worker_thread import WorkerThread
    worker = github_dialog._DevicePollWorker("client", "code", 600, 1200)
    thread = WorkerThread(worker, worker.run_poll, worker.stop)
    thread.start()
    thread.shutdown()
    assert worker._stop
    assert not thread.isRunning()
    qapp.processEvents()


@pytest.mark.parametrize("fails", [False, True])
def test_arena_restores_controls_and_marks_only_winning_slot(qapp, monkeypatch, fails):
    widget = arena_dialog.ArenaDialog(prompt="hello")
    model_id = widget.card1.get_selected_model_id()
    cards = (widget.card1, widget.card2, widget.card3)
    for card in cards:
        card.model_combo.setCurrentIndex(card.model_combo.findData(model_id))
    def compare(*args, **kwargs):
        if fails:
            raise RuntimeError("comparison failed")
        return ArenaResult("hello", "", [
            LLMResponse(content="answer", model_id=model_id, elapsed_seconds=elapsed)
            for elapsed in (3, 1, 2)
        ])
    monkeypatch.setattr(arena_dialog, "run_arena_comparison", compare)
    widget.run_arena()
    thread = widget._worker_thread
    try:
        assert all(not card.model_combo.isEnabled() for card in cards)
        process_until(qapp, lambda: widget._worker is None)
        assert all(card.model_combo.isEnabled() and card.progress.isHidden() for card in cards)
        if fails:
            assert all("comparison failed" in card.output_edit.toPlainText() for card in cards)
        else:
            assert ["FASTEST" in card.status_badge.text() for card in cards] == [False, True, False]
    finally:
        thread.wait(3000)
        widget.deleteLater()
        qapp.processEvents()
