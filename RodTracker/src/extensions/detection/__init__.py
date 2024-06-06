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

import logging
from pathlib import Path

from PyQt5 import QtWidgets

from RodTracker.ui.mainwindow import RodTrackWindow

_logger = logging.getLogger(__name__)
REQUIRED_EXTENSIONS = [
    "rods",
]


def setup(
    _: QtWidgets.QSplashScreen = None,
    main_window: RodTrackWindow = None,
    *args,
    **kwargs,
):
    try:
        # load all modules
        from . import detection

    except ModuleNotFoundError as e:
        _logger.error(f"Extension is missing a module: {e}")
        # install()

    # Insert menus/menu items
    pass
    # Insert image interaction tabs
    pass
    # Insert utility tabs
    detector_tab = detection.DetectorUI(id="detector")
    main_window.add_utility_tab(detector_tab, "Detector")

    # Insert settings
    pass

    _logger.debug("Initalization is not fully implemented.")


def install():
    # Try installing requirements from file
    import subprocess
    import sys

    req_path = Path(__file__).parent / "requirements.txt"
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", str(req_path)]
    )
