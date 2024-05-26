import os
import subprocess
import sys
from typing import Callable

from PyQt5 import QtCore, QtGui

import RodTracker


def blank_icon() -> QtGui.QIcon:
    blank_pix = QtGui.QPixmap(40, 100)
    blank_pix.fill(QtCore.Qt.transparent)
    return QtGui.QIcon(blank_pix)


def busy_icon() -> QtGui.QIcon:
    busy_pix = QtGui.QPixmap(40, 100)
    busy_pix.fill(QtCore.Qt.transparent)
    busy_painter = QtGui.QPainter(busy_pix)
    busy_painter.setBrush(
        QtGui.QBrush(QtCore.Qt.green, QtCore.Qt.SolidPattern)
    )
    busy_painter.setPen(QtCore.Qt.NoPen)
    busy_painter.drawEllipse(0, 0, 40, 40)
    busy_painter.end()
    return QtGui.QIcon(busy_pix)


def open_logs():
    """Opens the log file."""
    if sys.platform == "win32":
        os.startfile(RodTracker.LOG_FILE)
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.run([opener, RodTracker.LOG_FILE])


def report_issue():
    QtGui.QDesktopServices.openUrl(
        QtCore.QUrl(
            "https://github.com/ANP-Granular/ParticleTracking/issues/new?labels=bug&projects=&template=bug_report.md&title="  # noqa: E501
        )
    )


def request_feature():
    QtGui.QDesktopServices.openUrl(
        QtCore.QUrl(
            "https://github.com/ANP-Granular/ParticleTracking/issues/new?labels=enhancement&projects=&template=feature_request.md&title="  # noqa: E501
        )
    )


def reconnect(
    signal: QtCore.pyqtSignal,
    newhandler: Callable = None,
    oldhandler: Callable = None,
) -> None:
    """(Re-)connect handler(s) to a signal.

    Connect a new handler function to a signal while either removing all other,
    previous handlers, or just one specific one.

    Parameters
    ----------
    signal : QtCore.pyqtSignal
    newhandler : Callable, optional
        By default ``None``.
    oldhandler : Callable, optional
        Handler function currently connected to ``signal``. All connected
        functions will be removed, if this parameters is ``None``.
        By default ``None``.
    """
    try:
        if oldhandler is not None:
            while True:
                signal.disconnect(oldhandler)
        else:
            signal.disconnect()
    except TypeError:
        pass
    if newhandler is not None:
        signal.connect(newhandler)
