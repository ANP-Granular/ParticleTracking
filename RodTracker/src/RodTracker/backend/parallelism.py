# Copyright (c) 2023-24 Adrian Niemann, Dmitry Puzyrev, and others
#
# This file is part of RodTracker.
# RodTracker is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RodTracker is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RodTracker. If not, see <http://www.gnu.org/licenses/>.

"""
Classes used in RodTracked GUI for parallel thread work
(some lengthy computations/data loading is performed outside
of the main thread).

**Author:**     Adrian Niemann (adrian.niemann@ovgu.de)\n
**Date:**       2022-2024
"""

import sys
from functools import wraps

from PyQt5 import QtCore


def error_handler(func):
    """Decorator function to provide proper error handling.

    This function is intended as a wrapper for the `QRunnable.run()` function.
    It assumes that the `QRunnable` object has an attribute
    `self.signals.error` which is a `pyqtSignal` that expects the exception
    type, value, and traceback as its values.

    See Also
    --------
    :class:`WorkerSignals`, :class:`Worker`
    """

    @wraps(func)
    def error_wrapper(self):
        try:
            func(self)
        except:  # noqa: E722
            exctype, value, tb = sys.exc_info()
            self.signals.error.emit((exctype, value, tb))

    return error_wrapper


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
    """Wrapper object for a function that shall be run in a thread other than
    the main thread.

    Parameters
    ----------
    func : callable
        Function to be run in a thread other than the main thread.
    *args : Iterable
        Positional arguments :attr:`func` shall be run with.
    **kwargs : dict
        Keyword arguments :attr:`func` shall be run with.

    Attributes
    ----------
    func : callable
        Function to be run in a thread other than the main thread.
    args : Iterable
        Positional arguments :attr:`func` will be run with.
    kwargs : dict
        Keyword arguments :attr:`func` will be run with.
    signals : WorkerSignals
        Signals that can be emitted after the invocation of the
        :class:`Worker` object.
    """

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @error_handler
    def run(self):
        """Run the :attr:`func` with :attr:`args` and attr:`kwargs` as its
        parameters.

        This function is not intended to be run directly but by invoking it via
        a ``QThreadPool.start(worker)`` call.


        .. hint::

            **Emits**

            - :attr:`WorkerSignals.error`
            - :attr:`WorkerSignals.result`
            - :attr:`WorkerSignals.finished`
        """
        try:
            result = self.func(*self.args, **self.kwargs)
        except:  # noqa: E722
            exctype, value, tb = sys.exc_info()
            self.signals.error.emit((exctype, value, tb))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()
