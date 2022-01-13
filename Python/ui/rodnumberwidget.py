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

from PyQt5 import QtCore, QtGui, QtWidgets
from enum import Enum


class RodStyle(str, Enum):
    """Styles for rod numbers."""
    GENERAL = "background-color: transparent;" \
              "color: rgb({},{},{}); " \
              "font: {}px; font-weight: bold;"
    SELECTED = "background-color: transparent;" \
               "color: white; " \
               "font: {}px; font-weight: bold;"
    CONFLICT = "background-color: transparent;" \
               "color: red; " \
               "font: {}px; font-weight: bold;"
    CHANGED = "background-color: transparent;" \
              "color: green; " \
              "font: {}px; font-weight: bold;"


class RodState(Enum):
    """States of a rod."""
    NORMAL = 0
    SELECTED = 1
    EDITING = 2
    CHANGED = 3
    CONFLICT = 4


class RodStateError(ValueError):
    """Custom error that is raised when an unknown RodState is encountered."""
    def __init__(self):
        self.message = "The assigned RodState is invalid. Please assign a " \
                       "known RodState."
        super().__init__(self.message)


class RodNumberWidget(QtWidgets.QLineEdit):
    """A custom QLineEdit to display rod numbers and have associated rods.

    Parameters
    ----------
    color : str
        The color of the rod that this widget represents.
    parent : QWidget, optional
        The widgets parent widget. Default is None.
    text : str, optional
        The text displayed by the widget. Default is "".
    pos : QPoint, optional
        The position of the widget (relative to its parent widget). Default
        is QPoint(0, 0)

    Attributes
    ----------
    initial_text : str
    initial_pos : QPoint
    rod_id : str
        The number of the rod.
    rod_state : RodState
    rod_points : List[int]
        The starting and ending points of the rod in UNSCALED form.
        [x1, y1, x2, y2]
    color : str
        The color of the rod being represented.

    Signals
    -------
    gotActivated(int)
    droppedRodNumber(QPoint)
    changedRodNumber(QLineEdit, int)
    request_delete(QLineEdit)

    Slots
    -----
    update_settings(dict)
    """

    __pyqtSignals__ = ("gotActivated(int)", "droppedRodNumber(QPoint)",
                       "changedRodNumber(QLineEdit, int)")
    # Create custom signals
    activated = QtCore.pyqtSignal(int, name="gotActivated")
    dropped = QtCore.pyqtSignal(QtCore.QPoint, name="droppedRodNumber")
    id_changed = QtCore.pyqtSignal(QtWidgets.QLineEdit, int,
                                   name="changedRodNumber")
    request_delete = QtCore.pyqtSignal(QtWidgets.QLineEdit,
                                       name="request_delete")
    rod_state: RodState
    seen: bool = False

    _boundary_offset: int = 5
    _number_size: int = 12
    _number_color: [int] = [0, 0, 0]
    _rod_thickness: int = 3
    _rod_color: [int] = [0, 255, 255]

    def __init__(self, color, parent=None, text="", pos=QtCore.QPoint(0, 0)):
        # General setup
        super().__init__()
        self.__mousePressPos = None
        self.__mouseMovePos = None

        # Include given parameters
        self.setParent(parent)
        self.setText(text)
        self.initial_text = text
        self.initial_pos = pos
        self.move(pos)
        self._rod_id = None
        self._rod_state = RodState.NORMAL
        self.rod_points = [0, 0, 0, 0]
        self.color = color

        # Set initial visual appearance & function
        self.setInputMask("99")
        self.setMouseTracking(False)
        self.setFrame(False)
        self.setReadOnly(True)
        self.setStyleSheet(RodStyle.GENERAL.format(*self._number_color,
                                                   self._number_size))

        content_size = self.fontMetrics().boundingRect("99")
        content_size.setWidth(content_size.width() + self._boundary_offset)
        self.setGeometry(content_size)

    @property
    def rod_id(self):
        """Property that represents the rod's ID (number).

        Returns
        -------
        int
        """
        return self._rod_id

    @rod_id.setter
    def rod_id(self, new_id: int):
        if new_id > 99:
            raise ValueError("Only values <100 allowed.")
        self._rod_id = new_id
        self.initial_text = str(new_id)
        self.setText(str(new_id))

    @property
    def rod_state(self):
        """Holds the state of the rod.

        State of the rod also determines the visual appearance.

        Returns
        -------
        RodState
        """
        return self._rod_state

    @rod_state.setter
    def rod_state(self, new_state: RodState):
        new_style = ""
        if new_state == RodState.NORMAL:
            new_style = RodStyle.GENERAL.format(*self._number_color,
                                                self._number_size)
        elif new_state == RodState.SELECTED:
            new_style = RodStyle.SELECTED.format(self._number_size)
        elif new_state == RodState.EDITING:
            new_style = RodStyle.SELECTED.format(self._number_size)
        elif new_state == RodState.CHANGED:
            new_style = RodStyle.CHANGED.format(self._number_size)
        elif new_state == RodState.CONFLICT:
            new_style = RodStyle.CONFLICT.format(self._number_size)
        else:
            raise RodStateError()
        self._rod_state = new_state
        self.setStyleSheet(new_style)

    @property
    def pen(self):
        color = None
        if self.rod_state == RodState.NORMAL:
            color = QtGui.QColor(*self._rod_color)
        elif self.rod_state == RodState.SELECTED:
            color = QtCore.Qt.white
        elif self.rod_state == RodState.EDITING:
            # Don't return a pen as a new rod is currently drawn
            return None
        elif self.rod_state == RodState.CHANGED:
            color = QtCore.Qt.green
        elif self.rod_state == RodState.CONFLICT:
            color = QtCore.Qt.red
        else:
            raise RodStateError()
        if self.seen:
            line_style = QtCore.Qt.SolidLine
        else:
            line_style = QtCore.Qt.DotLine

        return QtGui.QPen(color, self._rod_thickness, line_style)

    # Controlling "editing" behaviour
    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent) -> None:
        """ Reimplements QLineEdit.mouseDoubleClickEvent(e).

        Handles the selection of a rod number for editing.

        Parameters
        ----------
        e : QMouseEvent

        Returns
        -------
        None
        """
        self.setReadOnly(False)
        self.selectAll()

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        """ Reimplements QLineEdit.keyPressEvent(e).

        Handles the confirmation and exiting during rod number editing using
        keyboard keys.

        Parameters
        ----------
        e : QMouseEvent

        Returns
        -------
        None
        """
        if e.key() == QtCore.Qt.Key_Return or e.key() == QtCore.Qt.Key_Enter:
            # Confirm & end editing (keep changes)
            self.end(False)
            self.setReadOnly(True)
            user_text = self.text()
            if user_text == "":
                self.request_delete.emit(self)
                return
            self.initial_text = self.text()
            previous_id = self.rod_id
            self.rod_id = int(self.text())
            self.id_changed.emit(self, previous_id)

        elif e.key() == QtCore.Qt.Key_Escape:
            # Abort editing (keep initial value)
            self.end(False)
            self.setReadOnly(True)
            self.setText(self.initial_text)
        else:
            # Normal editing
            super().keyPressEvent(e)

    # Controlling "movement" behaviour
    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        """ Reimplements QLineEdit.mouseMoveEvent(e).

        Handles the position updating during drag&drop of this widget by the
        user.

        Parameters
        ----------
        e : QMouseEvent

        Returns
        -------
        None
        """
        if self.isReadOnly():
            if self.__mouseMovePos is None or self.__mousePressPos is None:
                self.__mouseMovePos = e.globalPos()
                self.__mousePressPos = e.globalPos()
                return
            curr_pos = self.mapToGlobal(self.pos())
            global_pos = e.globalPos()
            diff = global_pos - self.__mouseMovePos
            new_pos = self.mapFromGlobal(curr_pos + diff)
            self.move(new_pos)
            self.__mouseMovePos = global_pos
            self.parentWidget().repaint()
            return

    def mousePressEvent(self, event):
        """ Reimplements QLineEdit.mousePressEvent(event).

        Handles the selection of a rod for corrections and drag&drop of this
        widget by the user.

        Parameters
        ----------
        event : QMouseEvent

        Returns
        -------
        None
        """

        # Propagate regular event (otherwise blocks functions relying on it)
        QtWidgets.QLineEdit.mousePressEvent(self, event)

        if self.isReadOnly():
            self.__mousePressPos = None
            self.__mouseMovePos = None
            if event.button() == QtCore.Qt.LeftButton:
                self.__mousePressPos = event.globalPos()
                self.__mouseMovePos = event.globalPos()
                self.activated.emit(self.rod_id)

    def mouseReleaseEvent(self, event) -> None:
        """ Reimplements QLineEdit.mouseReleaseEvent(event).

        Handles ending of drag&drop of this widget by the user.

        Parameters
        ----------
        event : QMouseEvent

        Returns
        -------
        None
        """
        if self.__mousePressPos is not None:
            moved = event.globalPos() - self.__mousePressPos
            if moved.manhattanLength() > 3:
                # Mouse just moved minimally (not registered as "dragging")
                event.ignore()
                return
            self.dropped.emit(event.globalPos())
        return

    # Actions triggered on other rods
    def deactivate_rod(self) -> None:
        """Handles the deactivation of this rod.

        Returns
        -------
        None
        """
        if self.styleSheet() != RodStyle.CONFLICT.format(self._number_size):
            self.rod_state = RodState.NORMAL
        self.setReadOnly(True)

    def copy(self):
        """Copies this instance of a RodNumberWidget.

        Returns
        -------
        RodNumberWidget
        """
        copied = RodNumberWidget(self.color, self.parent(), self.text(),
                                 self.pos())
        copied.rod_state = self.rod_state
        copied.rod_points = self.rod_points
        copied.rod_id = self.rod_id
        copied.setVisible(False)
        return copied

    @QtCore.pyqtSlot(int)
    def resolution_adjust(self, font_size, bound_offset=5):
        """Sets the new font size and adapts the widgets size to it.
        Currently not used."""
        current_font = self.font()
        current_font.setPointSizeF(font_size)
        self.setFont(current_font)

        self._boundary_offset = bound_offset
        content_size = self.fontMetrics().boundingRect("99")
        content_size.setWidth(content_size.width() + self._boundary_offset)
        self.setGeometry(content_size)

    @QtCore.pyqtSlot(dict)
    def update_settings(self, settings: dict):
        """Catches updates of the settings from a `Settings` class.

        Checks for the keys relevant to itself and updates the corresponding
        attributes. Redraws itself with the new settings in place, if
        settings were changed.

        Parameters
        ----------
        settings : dict

        Returns
        -------
        None
        """
        settings_changed = False
        if "number_size" in settings:
            settings_changed = True
            self._number_size = settings["number_size"]
        if "number_color" in settings:
            settings_changed = True
            self._number_color = settings["number_color"]
        if "boundary_offset" in settings:
            settings_changed = True
            self._boundary_offset = settings["boundary_offset"]
        if "rod_thickness" in settings:
            settings_changed = True
            self._rod_thickness = settings["rod_thickness"]
        if "rod_color" in settings:
            settings_changed = True
            self._rod_color = settings["rod_color"]

        if settings_changed:
            if self.rod_state == RodState.NORMAL:
                self.setStyleSheet(RodStyle.GENERAL.format(
                    *self._number_color, self._number_size))
            elif self.rod_state == RodState.SELECTED:
                self.setStyleSheet(RodStyle.SELECTED.format(self._number_size))
            elif self.rod_state == RodState.EDITING:
                self.setStyleSheet(RodStyle.SELECTED.format(self._number_size))
            elif self.rod_state == RodState.CHANGED:
                self.setStyleSheet(RodStyle.CHANGED.format(self._number_size))
            elif self.rod_state == RodState.CONFLICT:
                self.setStyleSheet(RodStyle.CONFLICT.format(self._number_size))

            content_size = self.fontMetrics().boundingRect("99")
            content_size.setWidth(content_size.width() + self._boundary_offset)
            self.setGeometry(content_size)

    @classmethod
    def update_defaults(cls, settings: dict) -> None:
        """Catches updates of the settings from a `Settings` class.

        Checks for the keys relevant to itself and updates the corresponding
        class attributes. Updates those attributes to already have the
        correct values when new RodNumberWidgets are created.

        Parameters
        ----------
        settings : dict

        Returns
        -------
        None
        """
        if "number_size" in settings:
            cls._number_size = settings["number_size"]
        if "number_color" in settings:
            cls._number_color = settings["number_color"]
        if "boundary_offset" in settings:
            cls._boundary_offset = settings["boundary_offset"]
        if "rod_thickness" in settings:
            cls._rod_thickness = settings["rod_thickness"]
        if "rod_color" in settings:
            cls._rod_color = settings["rod_color"]

