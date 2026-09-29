"""Lifetime management for blocking network jobs that emit Qt signals."""

from PyQt6.QtCore import QCoreApplication, QThread


class WorkerThread(QThread):
    """Retain a job until it returns, independently of its originating widget.

    The worker is a signal emitter with no timers or event-driven Qt I/O. Its
    blocking callable runs here; the QObject itself stays on the GUI thread so
    queued results are delivered before its deferred deletion.
    """

    def __init__(self, worker, run, cancel):
        app = QCoreApplication.instance()
        super().__init__(app)
        self.worker = worker
        self._run_job = run
        self._cancel_job = cancel
        self.finished.connect(worker.deleteLater)
        self.finished.connect(self.deleteLater)
        app.aboutToQuit.connect(self.shutdown)

    def run(self):
        self._run_job()

    def shutdown(self):
        # Blocking HTTP calls cannot be interrupted by QThread.quit(). Wait
        # only on application exit, never when cancelling or closing a dialog.
        self._cancel_job()
        self.wait()
