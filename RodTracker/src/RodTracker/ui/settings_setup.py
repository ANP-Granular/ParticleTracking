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

"""
Includes methods which allow to initialize/change user settings in
RodTracker GUI.

**Author:**     Adrian Niemann (adrian.niemann@ovgu.de)\n
**Date:**       2022-2024
"""

import copy

from PyQt5 import QtCore, QtGui, QtWidgets

import RodTracker.ui.mainwindow_layout as mw_l
from RodTracker.backend.settings import Settings


def init_settings(ui: mw_l.Ui_MainWindow, settings: Settings):
    """Initializes the visual elements controlling the RodTracker settings.

    During initialization all visual elements handling settings are connected
    to the necessary functions and retrieve their saved/inital values.

    Parameters
    ----------
    ui : Ui_MainWindow
        Object containing all visual elements of the RodTracker's main window.
    settings : Settings
        Settings object of the current session of the RodTracker.
    """
    ui.pb_defaults.clicked.connect(lambda: restore_defaults(ui, settings))
    set_all_values(settings._contents, ui)

    ui.thickness.lineEdit().selectionChanged.connect(lambda: clear_select(ui))
    ui.offset.lineEdit().selectionChanged.connect(lambda: clear_select(ui))
    ui.number_size.lineEdit().selectionChanged.connect(
        lambda: clear_select(ui)
    )

    ui.thickness.valueChanged.connect(
        lambda val: settings.update_field("visual", "rod_thickness", val)
    )
    ui.offset.valueChanged.connect(
        lambda val: settings.update_field("visual", "number_offset", val)
    )
    ui.number_size.valueChanged.connect(
        lambda val: settings.update_field("visual", "number_size", val)
    )
    ui.lbl_number_rods.setEnabled(False)
    ui.number_rods.setEnabled(False)
    ui.box_width.valueChanged.connect(
        lambda val: settings.update_field("experiment", "box_width", val)
    )
    ui.box_height.valueChanged.connect(
        lambda val: settings.update_field("experiment", "box_height", val)
    )
    ui.box_depth.valueChanged.connect(
        lambda val: settings.update_field("experiment", "box_depth", val)
    )
    ui.position_scaling.textChanged.connect(
        lambda _: handle_line_edit_changes(
            ui.position_scaling, settings, "visual", "position_scaling"
        )
    )
    ui.rod_incr.textChanged.connect(
        lambda _: handle_line_edit_changes(
            ui.rod_incr, settings, "functional", "rod_increment"
        )
    )
    ui.rod_color.clicked.connect(
        lambda: handle_color_pick(
            ui.rod_color, settings, "visual", "rod_color"
        )
    )
    ui.number_color.clicked.connect(
        lambda: handle_color_pick(
            ui.number_color, settings, "visual", "number_color"
        )
    )
    ui.cb_recalc_3D.stateChanged.connect(handle_checkbox)
    ui.lbl_recalc_3D.setToolTip(
        "Recalculate particles' 3D position "
        "immediately after a change was made in 2D."
    )
    ui.cb_recalc_3D.setEnabled(False)
    ui.lbl_recalc_3D.setEnabled(False)


def clear_select(ui: mw_l.Ui_MainWindow):
    """Helper to clear selections of ``QSpinBox`` after values changed."""
    ui.number_size.lineEdit().deselect()
    ui.offset.lineEdit().deselect()
    ui.thickness.lineEdit().deselect()


def handle_line_edit_changes(
    obj: QtWidgets.QLineEdit, settings: Settings, category: str, field: str
):
    """Handler function to extract the users' input from a ``QLineEdit``.

    Parameters
    ----------
    obj : QLineEdit
        The visual object, that has undergone a change.
    settings : Settings
        Settings object of the current session of the RodTracker.
    category : str
        Category of settings.
    field : str
        Field/setting within the ``category``.
    """
    try:
        converted_val = float(obj.displayText())
    except ValueError:
        converted_val = 1.0
    settings.update_field(category, field, converted_val)


def handle_color_pick(
    obj: QtWidgets.QToolButton, settings: Settings, category: str, field: str
):
    """Handler function to let the user select a color for a setting.

    Parameters
    ----------
    obj : QToolButton
        The visual object, that has been clicked.
    settings : Settings
        Settings object of the current session of the RodTracker.
    category : str
        Category of settings.
    field : str
        Field/setting within the ``category``.
    """
    color_vals = settings._contents[category][field]
    color = QtWidgets.QColorDialog(QtGui.QColor(*color_vals), obj)
    if color.exec():
        color = color.selectedColor()
        draw_icon(QtGui.QColor(color), obj)
        settings.update_field(
            category, field, [color.red(), color.green(), color.blue()]
        )


def draw_icon(color: QtGui.QColor, target: QtWidgets.QToolButton):
    """Helper method to set the color selection button's background.

    Parameters
    ----------
    color : QColor
    target : QToolButton
    """
    to_icon = QtGui.QPixmap(35, 25)
    painter = QtGui.QPainter(to_icon)
    painter.fillRect(QtCore.QRect(0, 0, 35, 25), QtGui.QColor(color))
    painter.end()
    target.setIcon(QtGui.QIcon(to_icon))
    target.setIconSize(QtCore.QSize(28, 15))


def handle_checkbox(state: int):
    raise NotImplementedError


def set_all_values(se: dict, ui: mw_l.Ui_MainWindow):
    """Sets the values of all settings elements from a given dictionary.

    Parameters
    ----------
    se : dict
        Nested settings dictionary.
    ui : Ui_MainWindow
        Object containing all visual elements of the RodTracker's main window.
    """
    ui.offset.setValue(se["visual"]["number_offset"])
    ui.thickness.setValue(se["visual"]["rod_thickness"])
    ui.number_size.setValue(se["visual"]["number_size"])
    ui.box_width.setValue(se["experiment"]["box_width"])
    ui.box_height.setValue(se["experiment"]["box_height"])
    ui.box_depth.setValue(se["experiment"]["box_depth"])
    draw_icon(QtGui.QColor(*se["visual"]["rod_color"]), ui.rod_color)
    draw_icon(QtGui.QColor(*se["visual"]["number_color"]), ui.number_color)
    ui.position_scaling.setText(
        "{:05.2f}".format(se["visual"]["position_scaling"])
    )
    ui.rod_incr.setText("{:05.2f}".format(se["functional"]["rod_increment"]))


def restore_defaults(ui: mw_l.Ui_MainWindow, settings: Settings):
    """Resets the displayed settings to the default values.

    Parameters
    ----------
    ui : Ui_MainWindow
        Object containing all visual elements of the RodTracker's main window.
    settings : Settings
        Settings object of the current session of the RodTracker.
    """
    if settings._default is None:
        QtWidgets.QMessageBox.critical(
            ui,
            "Restore defaults",
            "There are no defaults present! To reset the settings "
            "delete the file %temp%/RodTracker/settings.json and "
            "restart the application.",
        )
    else:
        settings._contents = copy.deepcopy(settings._default)
        set_all_values(settings._contents, ui)
        settings.send_settings()
