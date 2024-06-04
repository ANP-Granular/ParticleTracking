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

from PyQt5 import QtGui, QtWidgets

from RodTracker.backend.settings import Settings
from RodTracker.ui.mainwindow import RodTrackWindow
from RodTracker.ui.settings import ColorSetting, FloatSetting, IntSetting

_logger = logging.getLogger(__name__)


def setup(
    _: QtWidgets.QSplashScreen = None,
    main_window: RodTrackWindow = None,
    *args,
    **kwargs,
):
    try:
        # load all required modules
        from . import data, display_tab, rod_tree, rods
    except ModuleNotFoundError as e:
        _logger.error(f"Extension is missing a module: {e}")

    # Insert image interaction tabs
    front_view = display_tab.RodImageTab()
    front_view.ID = "front_view"
    main_window.add_image_interaction_tab(front_view, "Front View")

    top_view = display_tab.RodImageTab()
    top_view.ID = "top_view"
    main_window.add_image_interaction_tab(top_view, "Top View")

    # Add a position data provider
    rod_data = data.RodData()
    main_window.register_position_data(rod_data, [front_view, top_view])

    # Connect position data to views
    front_view.logger.data_changed.connect(rod_data.data_changed)
    front_view.image_manager.next_img[int, int].connect(
        lambda num, idx: front_view.frame(num)
    )
    top_view.logger.data_changed.connect(rod_data.data_changed)
    top_view.image_manager.next_img[int, int].connect(
        lambda num, idx: top_view.frame(num)
    )

    # Insert utility tabs
    tree_display = rod_tree.RodTree("Rods")
    rod_data.data_update.connect(tree_display.update_tree)
    rod_data.batch_update.connect(tree_display.batch_update_tree)
    rod_data.seen_loaded.connect(tree_display.setup_tree)
    tree_display.itemClicked.connect(
        lambda: _logger.info(
            "'RodTree.itemClicked()'-connection is not (yet) implemented."
        )
    )

    # TODO: verify the selected class thing works, as this might be only run at
    #   creation time of the outer lambda function
    top_view.image_manager.next_img.connect(
        lambda frame, _: tree_display.update_tree_folding(
            frame, lambda: main_window.get_selected_class()
        )
    )
    main_window.add_utility_tab(tree_display, "Rods")

    # Insert settings
    main_window.add_setting(
        FloatSetting(
            "Rods.rod_increment", 1, "Rod length in-/decrement [px]: "
        )
    )
    main_window.add_setting(
        IntSetting("Rods.rod_thickness", 3, "Rod Thickness [px]: ", 0, 15)
    )
    main_window.add_setting(
        IntSetting("Rods.number_offset", 15, "Number Offset [px]: ", 0, 50)
    )
    main_window.add_setting(
        IntSetting("Rods.number_size", 11, "Number Size [pt]: ", 0, 30)
    )
    main_window.add_setting(
        FloatSetting("Rods.position_scaling", 1, "Position Scaling: ")
    )
    main_window.add_setting(
        ColorSetting("Rods.rod_color", (0, 255, 255), "Rod Color: ")
    )
    main_window.add_setting(
        ColorSetting("Rods.number_color", (224, 27, 36), "Number Color: ")
    )
    # Connect objects to settings
    settings_obj = Settings()
    settings_obj.setting_signals.setting_changed.connect(
        front_view.update_settings
    )
    settings_obj.setting_signals.setting_changed.connect(
        top_view.update_settings
    )
    settings_obj.setting_signals.setting_changed.connect(
        tree_display.update_settings
    )
    settings_obj.setting_signals.setting_changed.connect(
        rod_data.update_settings
    )
    settings_obj.setting_signals.setting_changed.connect(
        rods.RodNumber.update_defaults
    )

    # Insert menus/menu items
    main_bar = main_window.menuBar()
    # File - Menu
    open_rod_data = QtWidgets.QAction("Open Rod Data", main_bar)
    open_rod_data.triggered.connect(rod_data.select_data)
    main_window.ui.menuFile.addAction(open_rod_data)
    # Edit - Menu
    rod_edit_menu = QtWidgets.QMenu("Rods", main_bar)
    main_window.ui.menuEdit.addMenu(rod_edit_menu)
    rod_edit_menu.addAction(
        "Shorten Selected Rod",
        lambda: _logger.info("'Shorten Selected Rod' is not implemented."),
        QtGui.QKeySequence("S"),
    )
    rod_edit_menu.addAction(
        "Shorten Displayed Rods",
        lambda: _logger.info("'Shorten Displayed Rods' is not implemented."),
        QtGui.QKeySequence("A"),
    )
    rod_edit_menu.addAction(
        "Lengthen Selected Rod",
        lambda: _logger.info("'Lengthen Selected Rod' is not implemented."),
        QtGui.QKeySequence("T"),
    )
    rod_edit_menu.addAction(
        "Lengthen Displayed Rods",
        lambda: _logger.info("'Lengthen Displayed Rods' is not implemented."),
        QtGui.QKeySequence("R"),
    )
    rod_edit_menu.addSeparator()
    rod_edit_menu.addAction(
        "Cleanup Data",
        lambda: _logger.info("'Cleanup Data' is not implemented."),
    )

    # View - Menu
    rod_view_menu = QtWidgets.QMenu("Rods", main_bar)
    main_window.ui.menuView.addMenu(rod_view_menu)

    autoselect = rod_view_menu.addAction(
        "Autoselect Rods",
        lambda: _logger.info("'Autoselect Rods' is not implemented."),
        QtGui.QKeySequence("G"),
    )
    autoselect.setCheckable(True)
    autoselect.setChecked(False)

    persistent_view = rod_view_menu.addAction(
        "Persistent View",
        lambda: _logger.info("'Persistent View' is not implemented."),
    )
    persistent_view.setCheckable(True)
    persistent_view.setChecked(False)
