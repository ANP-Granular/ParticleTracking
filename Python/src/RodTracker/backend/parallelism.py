import sys
import traceback
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
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()
