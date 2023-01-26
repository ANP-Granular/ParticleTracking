import sys
from PyQt5 import QtCore


class WorkerSignals(QtCore.QObject):
    error = QtCore.pyqtSignal(tuple)
    result = QtCore.pyqtSignal(object)
    finished = QtCore.pyqtSignal()


class Worker(QtCore.QRunnable):
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
        except:                                                    # noqa: E722
            exctype, value, tb = sys.exc_info()
            self.signals.error.emit((exctype, value, tb))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()
