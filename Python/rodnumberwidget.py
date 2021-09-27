from PyQt5 import QtGui
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QLineEdit
from PyQt5 import QtCore
from enum import Enum


class RodStyle(str, Enum):
    """Styles for rod numbers."""
    GENERAL = "background-color: transparent;" \
              "color: black; font-weight: bold;"
    SELECTED = "background-color: transparent;" \
               "color: white; font-weight: bold;"
    CONFLICT = "background-color: transparent;" \
               "color: red; font-weight: bold;"
    CHANGED = "background-color: transparent;" \
              "color: green; font-weight: bold;"


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


class RodNumberWidget(QLineEdit):
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

    """

    __pyqtSignals__ = ("gotActivated(int)", "droppedRodNumber(QPoint)",
                       "changedRodNumber(QLineEdit, int)")
    # Create custom signals
    activated = QtCore.pyqtSignal(int, name="gotActivated")
    dropped = QtCore.pyqtSignal(QPoint, name="droppedRodNumber")
    id_changed = QtCore.pyqtSignal(QLineEdit, int, name="changedRodNumber")
    rod_state: RodState

    def __init__(self, color, parent=None, text="", pos=QPoint(0, 0)):
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
        self.rod_id = None
        self.rod_state = RodState.NORMAL
        self.rod_points = [0, 0, 0, 0]
        self.color = color

        # Set initial visual appearance & function
        self.setInputMask("99")
        self.setMouseTracking(False)
        self.setFrame(False)
        self.setReadOnly(True)
        self.setStyleSheet(RodStyle.GENERAL)
        content_size = self.fontMetrics().boundingRect("99")
        content_size.setWidth(content_size.width()+5)
        self.setGeometry(content_size)

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

        # Propagate regular event (otherwise blocks functions relying
        # on it)
        QLineEdit.mousePressEvent(self, event)

        if self.isReadOnly():
            self.__mousePressPos = None
            self.__mouseMovePos = None
            if event.button() == QtCore.Qt.LeftButton:
                self.__mousePressPos = event.globalPos()
                self.__mouseMovePos = event.globalPos()
                self.setStyleSheet(RodStyle.SELECTED)
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
        if self.styleSheet() != RodStyle.CONFLICT:
            self.setStyleSheet(RodStyle.GENERAL)
            self.rod_state = RodState.NORMAL
        self.setReadOnly(True)

    def set_state(self, new_state: RodState) -> None:
        """Handles state changes of this rod.

        Parameters
        ----------
        new_state : RodState

        Returns
        -------
        None
        """
        self.rod_state = new_state
        if new_state == RodState.NORMAL:
            self.deactivate_rod()
        elif new_state == RodState.SELECTED:
            self.setStyleSheet(RodStyle.SELECTED)
        elif new_state == RodState.EDITING:
            self.setStyleSheet(RodStyle.SELECTED)
        elif new_state == RodState.CHANGED:
            self.setStyleSheet(RodStyle.CHANGED)
        elif new_state == RodState.CONFLICT:
            self.setStyleSheet(RodStyle.CONFLICT)
        else:
            raise(RodStateError())

    def copy_rod(self):
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
