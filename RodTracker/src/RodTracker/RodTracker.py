# Copyright (c) 2023-24 Adrian Niemann, and others
#
# This file is part of RodTracker.
# RodTracker is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RodTracker is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RodTracker. If not, see <http://www.gnu.org/licenses/>.

import importlib.util
import inspect
import logging
import sys
from pathlib import Path

import importlib_resources
from PyQt5 import QtCore, QtGui, QtWidgets

import RodTracker

_logger = logging.getLogger(__name__)


def main():
    currentdir = Path(inspect.getfile(inspect.currentframe())).resolve().parent
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

    splash.showMessage("Updating environment ...", align, color)
    import RodTracker.backend.logger as lg

    lg.MainLogger()

    splash.showMessage("Loading UI ...", align, color)
    import RodTracker.ui.mainwindow as mw

    main_window = mw.RodTrackWindow()

    # Load extensions
    extension_folder = Path(__file__).parent.parent / "extensions"
    if hasattr(sys, "_MEIPASS"):
        extension_folder = Path(__file__).parent / "extensions"
    for entry in extension_folder.iterdir():
        if not entry.is_dir() or entry.stem == "__pycache__":
            continue
        next_extension = entry.stem
        if list(entry.glob("DEACTIVATED")):
            # Skip loading if a file named 'DEACTIVATED' is present
            _logger.info(f"Extension '{next_extension}' is deactived.")
            continue
        splash.showMessage(
            f"Loading Extension: {next_extension}", align, color
        )
        try:
            spec = importlib.util.spec_from_file_location(
                next_extension, entry / "__init__.py"
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[next_extension] = module
            spec.loader.exec_module(module)
            module.setup(splash, main_window=main_window)
            _logger.info(f"Successfully loaded extension: {next_extension}")
        except Exception:
            _logger.error(
                f"Failed to load extension '{next_extension}':",
                exc_info=sys.exc_info(),
            )
    splash.showMessage("Starting ...", align, color)
    main_window.ensure_usable()
    splash.finish(main_window)

    # Changing behavior of ErrorDialog
    sys.excepthook = RodTracker.exception_logger

    main_window.show()
    main_window.raise_()
    main_window.activateWindow()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
