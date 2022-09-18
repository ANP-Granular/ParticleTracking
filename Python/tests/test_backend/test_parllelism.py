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
