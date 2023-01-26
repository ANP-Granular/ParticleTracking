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

import pytest
from pytestqt.qtbot import QtBot
from PyQt5 import QtCore
import RodTracker.backend.parallelism as pl


def runner_func(x=2, y=3):
    return x + y


@pytest.mark.parametrize("inputs,outputs",
                         [({}, [5]),
                          ({"x": 4}, [7]),
                          ({"y": 4}, [6]),
                          ({"x": 4, "y": 4}, [8])])
def test_run_func(inputs, outputs, qtbot: QtBot):
    threads = QtCore.QThreadPool()
    worker = pl.Worker(runner_func, **inputs)
    with qtbot.waitSignal(worker.signals.result, timeout=1000) as result:
        threads.start(worker)
    assert result.args == outputs


def test_thread_cleaned(qtbot: QtBot):
    threads = QtCore.QThreadPool()
    worker = pl.Worker(runner_func)
    with qtbot.waitSignal(worker.signals.finished, timeout=1000):
        threads.start(worker)
    assert threads.activeThreadCount() == 0


def test_error_propagation(qtbot: QtBot):
    threads = QtCore.QThreadPool()
    worker = pl.Worker(lambda: runner_func(None))
    with qtbot.waitSignal(worker.signals.error, timeout=1000) as result:
        threads.start(worker)
    assert len(result.args) == 1 and len(result.args[0]) == 3
    assert result.args[0][0] is TypeError
