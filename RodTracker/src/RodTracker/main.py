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

import inspect
import pathlib
import sys

import importlib_resources
from PyQt5 import QtCore, QtGui, QtWidgets

import RodTracker


def main():
    currentdir = (
        pathlib.Path(inspect.getfile(inspect.currentframe())).resolve().parent
    )
    parentdir = currentdir.parent
    sys.path.insert(0, str(parentdir))

    # Setup error handling before main window is running
    sys.excepthook = lambda t, val, tb: RodTracker.exception_logger(
        t, val, tb, use_exec=False
    )

    app = QtWidgets.QApplication(sys.argv)
    pixmap = QtGui.QPixmap(
        str(
            importlib_resources.files("RodTracker.resources").joinpath(
                "splash.png"
            )
        )
    )
    align = QtCore.Qt.AlignBottom | QtCore.Qt.AlignHCenter
    color = QtGui.QColorConstants.White
    splash = QtWidgets.QSplashScreen(pixmap)
    splash.show()

    splash.showMessage("Loading UI...", align, color)
    import RodTracker.ui.mainwindow as mw

    main_window = mw.RodTrackWindow()
    splash.finish(main_window)

    # Changing behavior of ErrorDialog
    sys.excepthook = RodTracker.exception_logger

    main_window.show()
    main_window.raise_()
    main_window.activateWindow()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
