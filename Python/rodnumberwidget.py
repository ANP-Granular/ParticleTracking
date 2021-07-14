from PyQt5 import QtGui
from PyQt5.QtCore import pyqtSignal, QPoint
from PyQt5.QtWidgets import QLineEdit
from PyQt5 import QtCore

GENERAL_STYLE = "background-color: transparent;" \
                    "color: cyan;"
SELECTED_STYLE = "background-color: transparent;" \
                    "color: white;"
CONFLICT_STYLE = "background-color: transparent;" \
                    "color: red;"


class RodNumberWidget(QLineEdit):
    __pyqtSignals__ = ("gotActivated(int)",)
    # Create custom signals
    activated = pyqtSignal(int, name="gotActivated")
    dropped = pyqtSignal(QPoint, name="droppedRodNumber")
    id_changed = pyqtSignal(int, name="changedRodNumber")

    def __init__(self, parent, text, pos):
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

        # Set initial visual appearance & function
        self.setInputMask("99")
        self.setMouseTracking(False)
        self.setFrame(False)
        self.setReadOnly(True)
        self.setStyleSheet(GENERAL_STYLE)

    # Controlling "editing" behaviour
    def mouseDoubleClickEvent(self, e: QtGui.QMouseEvent) -> None:
        self.setReadOnly(False)
        self.selectAll()

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        if e.key() == QtCore.Qt.Key_Return or e.key() == QtCore.Qt.Key_Enter:
            # Confirm & end editing (keep changes)
            self.end(False)
            self.setReadOnly(True)
            self.initial_text = self.text()
            self.rod_id = int(self.text())
            self.id_changed.emit(self.rod_id)

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
        # Propagate regular event (otherwise blocks functions relying
        # on it)
        QLineEdit.mousePressEvent(self, event)

        if self.isReadOnly():
            self.__mousePressPos = None
            self.__mouseMovePos = None
            if event.button() == QtCore.Qt.LeftButton:
                self.__mousePressPos = event.globalPos()
                self.__mouseMovePos = event.globalPos()
                self.setStyleSheet(SELECTED_STYLE)
                self.activated.emit(self.rod_id)

    def mouseReleaseEvent(self, event):
        if self.__mousePressPos is not None:
            moved = event.globalPos() - self.__mousePressPos
            if moved.manhattanLength() > 3:
                # Mouse just moved minimally (not registered as "dragging")
                event.ignore()
                return
            self.dropped.emit(event.globalPos())

    # Actions triggered on other rods
    def deactivate_rod(self):
        if self.styleSheet() != CONFLICT_STYLE:
            self.setStyleSheet(GENERAL_STYLE)
        self.setReadOnly(True)
