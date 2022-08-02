from functools import partial
from typing import Callable, Tuple
from PyQt5 import QtCore


class WorkerWrapper(QtCore.QObject):
    """Wraps a function to be executed in a thread with the given inputs."""
    finished = QtCore.pyqtSignal(object, name="finished")

    def __init__(self, f: Callable, inputs: dict):
        super().__init__()
        self.f = partial(f, **inputs)

    def run(self):
        results = self.f()
        self.finished.emit(results)


def run_in_thread(func: Callable, inputs: dict) -> Tuple[QtCore.QThread,
                                                         WorkerWrapper]:
    """Wraps a function to be executed in a different thread to avoid GUI
    blocking. Returns the created thread and a worker which is the wrapped
    function."""
    worker = WorkerWrapper(func, inputs)
    thread = QtCore.QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    return thread, worker
