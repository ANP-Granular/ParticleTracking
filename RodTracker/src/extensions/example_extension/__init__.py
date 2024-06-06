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
from typing import Any
from PyQt5 import QtWidgets
from RodTracker.backend import data
from RodTracker.ui import tabs, settings
from RodTracker.ui.mainwindow import RodTrackWindow

_logger = logging.getLogger(__name__)
REQUIRED_EXTENSIONS = []


class CustomSetting(settings.Setting):
    def __init__(self, id: str, default_value: Any = None, *args, **kwargs):
        super().__init__(id, default_value, *args, **kwargs)
        settings_layout = QtWidgets.QHBoxLayout(self)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(settings_layout)
        settings_layout.addWidget(QtWidgets.QLabel("Custom Setting UI", self))
        test_button = QtWidgets.QPushButton("Just a button", self)
        settings_layout.addWidget(test_button)
        test_button.clicked.connect(
            lambda: self.setting_updated.emit(
                "Example Extension.Example", True
            )
        )

    def set_value_silently(self, new_value: Any):
        pass


def setup(
    _: QtWidgets.QSplashScreen = None,
    main_window: RodTrackWindow = None,
    *args,
    **kwargs,
):
    _logger.info("This is an example extension.")
    try:
        # Load all custom modules
        pass
    except ModuleNotFoundError as e:
        _logger.error(f"Extension is missing a module: {e}")
        raise e
        # install()

    # Insert menus/menu items
    main_bar = main_window.menuBar()
    # File - Menu
    test_item = QtWidgets.QAction("Test Item", main_bar)
    test_item.triggered.connect(lambda: _logger.info("Test Item clicked."))
    main_window.ui.menuFile.addAction(test_item)

    # Insert image interaction tabs
    image_0 = tabs.ImageInteractionTab()
    main_window.add_image_interaction_tab(image_0, "Image 0")
    image_1 = tabs.ImageInteractionTab()
    main_window.add_image_interaction_tab(image_1, "Image 1")

    # Insert utility tabs
    main_window.add_utility_tab(tabs.UtilityTab("Example"), "Example")

    # Insert settings
    example_color = settings.ColorSetting(
        "Example Extension.color_example",
        description="Example Color Setting: ",
    )
    example_bool = settings.BoolSetting(
        "Example Extension.bool_example",
        default_value=True,
        description="Example Boolean Setting: ",
    )
    custom_setting = CustomSetting("Example Extension.Custom Example")

    main_window.add_setting(example_bool)
    main_window.add_setting(example_color)
    main_window.add_setting(custom_setting)

    # Connect data to display
    test_data = data.PositionData()
    main_window.register_position_data(test_data, [image_0, image_1])


def install():
    # Try installing requirements from file
    import subprocess
    import sys

    req_path = Path(__file__).parent / "requirements.txt"
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", str(req_path)]
    )
    # TODO: copy files from `./example_data/*` to
    #       `../../example_data/__name__/*`
