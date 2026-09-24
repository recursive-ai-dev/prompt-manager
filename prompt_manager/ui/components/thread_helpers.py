"""Lifetime helpers for one-shot QThread + QObject worker pairs.

Pattern used across the dialogs: a QObject worker is moved into a
one-shot QThread, invoked via ``started`` -> ``worker.run``, and cleaned
up with ``quit()`` + ``wait()``.

When ``wait()`` times out (the worker is still inside a blocking network
call), dropping the last Python reference to the worker leaves the C++
object's destruction to whatever reference happens to remain on the
still-running thread (CPython frame refcounting).  That is fragile across
Python implementations: the worker's QObject could be freed while its
thread is still live.

``WorkerLifetime`` keeps a strong reference to the worker until the
thread's ``finished`` signal is delivered (after the thread's run has
ended), then releases it — so the C++ object can never be destroyed
under a live thread, and no reference outlives the thread either.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, QThread


class WorkerLifetime:
    """Holds a worker reference until its QThread has finished, then releases."""

    def __init__(self, worker: QObject, thread: QThread):
        self._refs = [worker]
        self._released = False
        try:
            if not thread.wait(0):
                # Thread still running: release when it actually finishes.
                # ``finished`` is delivered (queued) to the main thread, so
                # the release happens off the worker thread.
                thread.finished.connect(self._on_thread_finished)
        except RuntimeError:
            # Thread object already destroyed — release immediately.
            self._release()
        # If the thread finished between the check and the connect, the
        # signal will never fire; release now to avoid a dangling reference.
        try:
            if thread.wait(0):
                self._release()
        except RuntimeError:
            self._release()

    def _on_thread_finished(self) -> None:
        self._release()

    def _release(self) -> None:
        if not self._released:
            self._released = True
            self._refs.clear()

    @property
    def released(self) -> bool:
        return self._released


def track_worker(worker: Optional[QObject], thread: Optional[QThread], holders: list) -> None:
    """Register ``worker`` for delayed release after ``thread`` finishes.

    ``holders`` is a long-lived list owned by the dialog/panel; released
    holders should be pruned periodically (e.g. before starting a new run)
    to keep it small.
    """
    if worker is None or thread is None:
        return
    lifetime = WorkerLifetime(worker, thread)
    if lifetime.released:
        return
    holders.append(lifetime)
