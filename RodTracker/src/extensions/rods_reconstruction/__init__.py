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

from RodTracker.backend.settings import Settings
from RodTracker.ui.mainwindow import RodTrackWindow
from RodTracker.ui.settings import BoolSetting

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
        # load all required modules
        from . import reconstruction
    except ModuleNotFoundError as e:
        _logger.error(f"Extension is missing a module: {e}")

    # Insert menus/menu items
    pass

    # Insert utility tabs
    reconstructor_tab = reconstruction.ReconstructorTab("reconstructor")
    main_window.add_utility_tab(reconstructor_tab, "Reconstruction")

    # Insert settings
    main_window.add_setting(
        BoolSetting("Rods.recalc_3d_points", False, "Recalculate 3D-Points")
    )

    # Connect object(s) to settings
    settings_obj = Settings()
    settings_obj.setting_signals.setting_changed.connect(
        reconstructor_tab.update_settings
    )
