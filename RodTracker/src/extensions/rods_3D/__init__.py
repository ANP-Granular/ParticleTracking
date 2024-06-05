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

from PyQt5 import QtWidgets

from RodTracker.ui.mainwindow import RodTrackWindow
from RodTracker.ui.settings import IntSetting

_logger = logging.getLogger(__name__)


def setup(
    _: QtWidgets.QSplashScreen = None,
    main_window: RodTrackWindow = None,
    *args,
    **kwargs,
):
    try:
        # load all required modules
        from . import view3d
    except ModuleNotFoundError as e:
        _logger.error(f"Extension is missing a module: {e}")

    # Insert utility tabs
    main_window.add_utility_tab(view3d.View3DTab("3D-View"), "3D-View")
    # Insert settings
    main_window.add_setting(
        IntSetting("Rods.box_width", 112, "Box Width [mm]", 0, 1000)
    )
    main_window.add_setting(
        IntSetting("Rods.box_height", 80, "Box Height [mm]", 0, 1000)
    )
    main_window.add_setting(
        IntSetting("Rods.box_height", 80, "Box Depth [mm]", 0, 1000)
    )
