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

import pathlib
import sys
import inspect

currentdir = pathlib.Path(
    inspect.getfile(inspect.currentframe())).resolve().parent
parentdir = currentdir.parent
sys.path.insert(0, str(parentdir))

from PyQt5 import QtWidgets                                     # noqa: E402
from RodTracker import TEMP_DIR                                 # noqa: E402
import RodTracker.backend.logger as lg                          # noqa: E402
import RodTracker.ui.mainwindow as mw                           # noqa: E402

sys.excepthook = lg.exception_logger

HAS_SPLASH = False
try:
    import pyi_splash
    HAS_SPLASH = True
except ModuleNotFoundError:
    # Application not bundled
    HAS_SPLASH = False


def main():
    if HAS_SPLASH:
        pyi_splash.update_text("Updating environment...")
    if not TEMP_DIR.exists():
        TEMP_DIR.mkdir()
    if HAS_SPLASH:
        pyi_splash.update_text("Loading UI...")

    app = QtWidgets.QApplication(sys.argv)
    main_window = mw.RodTrackWindow()

    if HAS_SPLASH:
        # Close the splash screen.
        pyi_splash.close()

    main_window.show()
    main_window.raise_()
    main_window.activateWindow()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
