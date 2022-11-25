import copy
from PyQt5 import QtWidgets, QtGui, QtCore
from RodTracker.backend.settings import Settings
import RodTracker.ui.mainwindow_layout as mw_l


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
        lambda: clear_select(ui))

    ui.thickness.valueChanged.connect(
        lambda val: settings.update_field("visual", "rod_thickness", val)
    )
    ui.offset.valueChanged.connect(
        lambda val: settings.update_field("visual", "number_offset", val)
    )
    ui.number_size.valueChanged.connect(
        lambda val: settings.update_field("visual", "number_size", val)
    )
    ui.number_rods.valueChanged.connect(
        lambda val: settings.update_field("experiment", "number_rods", val)
    )
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
        lambda _: handle_line_edit_changes(ui.position_scaling, settings,
                                           "visual", "position_scaling")
    )
    ui.rod_incr.textChanged.connect(
        lambda _: handle_line_edit_changes(ui.rod_incr, settings,
                                           "functional", "rod_increment")
    )
    ui.rod_color.clicked.connect(
        lambda: handle_color_pick(ui.rod_color, settings,
                                  "visual", "rod_color")
    )
    ui.number_color.clicked.connect(
        lambda: handle_color_pick(ui.number_color, settings,
                                  "visual", "number_color")
    )


def clear_select(ui: mw_l.Ui_MainWindow):
    """Helper to clear selections of QSpinBoxes after values changed."""
    ui.number_size.lineEdit().deselect()
    ui.offset.lineEdit().deselect()
    ui.thickness.lineEdit().deselect()


def handle_line_edit_changes(obj: QtWidgets.QLineEdit, settings: Settings,
                             category: str, field: str):
    """Handler function to extract the users' input from a `QLineEdit`.

    Parameters
    ----------
    obj : QtWidgets.QLineEdit
        The visual object, that has undergone a change.
    settings : Settings
        Settings object of the current session of the RodTracker.
    category : str
        Category of settings.
    field : str
        Field/setting within the `category`.
    """
    try:
        converted_val = float(obj.displayText())
    except ValueError:
        converted_val = 1.0
    settings.update_field(category, field, converted_val)


def handle_color_pick(obj: QtWidgets.QToolButton, settings: Settings,
                      category: str, field: str):
    """Handler function to let the user select a color for a setting.

    Parameters
    ----------
    obj : QtWidgets.QToolButton
        The visual object, that has been clicked.
    settings : Settings
        Settings object of the current session of the RodTracker.
    category : str
        Category of settings.
    field : str
        Field/setting within the `category`.
    """
    color_vals = settings._contents[category][field]
    color = QtWidgets.QColorDialog(QtGui.QColor(*color_vals), obj)
    if color.exec():
        color = color.selectedColor()
        draw_icon(QtGui.QColor(color), obj)
        settings.update_field(category, field,
                              [color.red(), color.green(), color.blue()])


def draw_icon(color: QtGui.QColor, target: QtWidgets.QToolButton):
    """Helper method to set the color selection button's background.

    Parameters
    ----------
    color : QtGui.QColor
    target : QtWidgets.QToolButton
    """
    to_icon = QtGui.QPixmap(35, 25)
    painter = QtGui.QPainter(to_icon)
    painter.fillRect(QtCore.QRect(0, 0, 35, 25),
                     QtGui.QColor(color))
    painter.end()
    target.setIcon(QtGui.QIcon(to_icon))
    target.setIconSize(QtCore.QSize(28, 15))


def set_all_values(se: dict, ui: mw_l.Ui_MainWindow):
    """Sets the values of all settings elements from a given dictionary.

    Parameters
    ----------
    se : dict
        Nested settings dictionary.
    ui : mw_l.Ui_MainWindow
        Object containing all visual elements of the RodTracker's main window.
    """
    ui.offset.setValue(se["visual"]["number_offset"])
    ui.thickness.setValue(se["visual"]["rod_thickness"])
    ui.number_size.setValue(se["visual"]["number_size"])
    ui.number_rods.setValue(se["experiment"]["number_rods"])
    ui.box_width.setValue(se["experiment"]["box_width"])
    ui.box_height.setValue(se["experiment"]["box_height"])
    ui.box_depth.setValue(se["experiment"]["box_depth"])
    draw_icon(QtGui.QColor(*se["visual"]["rod_color"]), ui.rod_color)
    draw_icon(QtGui.QColor(*se["visual"]["number_color"]), ui.number_color)
    ui.position_scaling.setText(
        "{:05.2f}".format(se["visual"]["position_scaling"]))
    ui.rod_incr.setText(
        "{:05.2f}".format(se["functional"]["rod_increment"]))


def restore_defaults(ui: mw_l.Ui_MainWindow, settings: Settings):
    """Resets the displayed settings to the default values.

    Parameters
    ----------
    ui : mw_l.Ui_MainWindow
        Object containing all visual elements of the RodTracker's main window.
    settings : Settings
        Settings object of the current session of the RodTracker.
    """
    if settings._default is None:
        QtWidgets.QMessageBox.critical(
            ui, "Restore defaults",
            "There are no defaults present! To reset the settings "
            "delete the file %temp%/RodTracker/settings.json and "
            "restart the application.")
    else:
        settings._contents = copy.deepcopy(settings._default)
        set_all_values(settings._contents, ui)
        settings.send_settings()
