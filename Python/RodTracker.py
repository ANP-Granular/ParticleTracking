#  Copyright (c) 2021 Adrian Niemann Dmitry Puzyrev
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

import os
import sys

import inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 

from PyQt5 import QtWidgets

from Python.backend import logger as lg
from Python.ui import mainwindow as mw

sys.excepthook = lg.exception_logger
ICON_PATH = "./resources/icon_main.ico"

HAS_SPLASH = False
try:
    import pyi_splash
    HAS_SPLASH = True
except ModuleNotFoundError:
    # Application not bundled
    HAS_SPLASH = False


if __name__ == "__main__":
    if HAS_SPLASH:
        pyi_splash.update_text("Updating environment...")
    if not os.path.exists(lg.TEMP_DIR):
        os.mkdir(lg.TEMP_DIR)
    if HAS_SPLASH:
        pyi_splash.update_text("Loading UI...")

    app = QtWidgets.QApplication(sys.argv)
    main_window = mw.RodTrackWindow()

    if HAS_SPLASH:
        # Close the splash screen.
        pyi_splash.close()

    main_window.show()
    sys.exit(app.exec_())
