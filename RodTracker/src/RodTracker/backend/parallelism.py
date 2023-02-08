#  Copyright (c) 2023 Adrian Niemann Dmitry Puzyrev
#
#  This file is part of RodTracker.
#  RodTracker is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  RodTracker is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with RodTracker.  If not, see <http://www.gnu.org/licenses/>.

import sys
from PyQt5 import QtCore


class WorkerSignals(QtCore.QObject):
    """Helper object to provide :class:`Worker` access to ``pyqtSignal``."""
    error = QtCore.pyqtSignal(tuple)
    """pyqtSignal(tuple) : Signal for propagating errors occuring in the
    :class:`Worker`'s thread.\n
    | The transferred tuple should contain the following values:
    | [0]: Exception type
    | [1]: Exception value
    | [2]: Exception traceback

    See Also
    --------
    `sys.exc_info()`_

    :py:obj:`sys.exc_info`

    .. _sys.exc_info():
        https://docs.python.org/3/library/sys.html#sys.exc_info
    """

    result = QtCore.pyqtSignal(object)
    """pyqtSignal(object) : Signal for reporting the results of a
    :class:`Worker`."""

    finished = QtCore.pyqtSignal()
    """pyqtSignal(): Signal to indicate a :class:`Worker` has finished."""


class Worker(QtCore.QRunnable):
    """**TBD**"""
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        """**TBD**


        .. hint::

            **Emits**

            - :attr:`WorkerSignals.error`
            - :attr:`WorkerSignals.result`
            - :attr:`WorkerSignals.finished`
        """
        try:
            result = self.func(*self.args, **self.kwargs)
        except:                                                    # noqa: E722
            exctype, value, tb = sys.exc_info()
            self.signals.error.emit((exctype, value, tb))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()
