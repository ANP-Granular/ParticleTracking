import tempfile
from typing import List
from PyQt5 import QtCore, QtWidgets
from Python.backend import logger as lg


class LoggerWidget(QtWidgets.QListWidget):
    """A custom Widget to maintain loggers and display Actions in the GUI.

    This class maintains the `ActionLogger` objects that are used in the
    program. It also manages the location for any temporary files that are
    program session specific. This widget displays the logged actions in the
    GUI. Use an instance of this class to create new loggers for other
    objects of the GUI that perform actions that can be logged or reverted.

    Parameters
    ----------
    *args : iterable
        Positional arguments for the QListWidget superclass.
    **kwargs : dict
        Keyword arguments for the QListWidget superclass.

    Attributes
    ----------
    temp_manager : TemporaryDirectory
    unsaved_changes : List[Action]
        An ordered list of all actions that were logged by the
        `ActionLogger` objects maintained by this `LoggerWidget`
        instance. Do NOT try to insert performed actions in here directly.
        This property only derives its contents from the `ActionLogger`
        objects.
    repeatable_changes : List[Action]
        An ordered list of all currently redoable/repeatable actions that were
        logged by the `ActionLogger` objects maintained by this
        `LoggerWidget` instance. Do NOT try to insert performed actions
        in here directly. This property only derives its contents from the
        `ActionLogger` objects.

    Slots
    -----
    add_action(Action)
    remove_action(Action)

    """

    temp_manager: tempfile.TemporaryDirectory
    _loggers: List[lg.ActionLogger] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.temp_manager = tempfile.TemporaryDirectory(
            prefix="Session_", dir=lg.TEMP_DIR)

    @property
    def unsaved_changes(self) -> List[lg.Action]:
        """Collects the unsaved changes from all loggers and returns them
        collectively.

        Returns
        -------
        List[Action]
        """
        all_unsaved = [item for changes in self._loggers for item in
                       changes.unsaved_changes]
        return all_unsaved

    @property
    def repeatable_changes(self) -> List[lg.Action]:
        """Collects the repeatable changes from all loggers and returns them
        collectively.

        Returns
        -------
        List[Action]
        """
        all_repeatable = [item for changes in self._loggers for item in
                          changes.repeatable_changes]
        return all_repeatable

    def get_new_logger(self, parent_id: str) -> lg.ActionLogger:
        """
        Creates a new ActionLogger, registers its signals for displaying the
        actions logged by it and returns it.

        Parameters
        ----------
        parent_id : str
            A unique name that indicates the object from which actions will
            be logged in the ActionLogger.

        Returns
        -------
        ActionLogger
        """
        new_logger = lg.ActionLogger(parent_id)
        new_logger.added_action.connect(self.add_action)
        new_logger.undo_action.connect(self.remove_action)
        new_logger.undone_action.connect(self.remove_action)
        self._loggers.append(new_logger)
        return new_logger

    @QtCore.pyqtSlot(lg.Action)
    def add_action(self, new_action: lg.Action) -> None:
        """Adds a new action to the list being displayed in the GUI."""
        if not self._loggers:
            # No loggers exist yet/anymore
            return
        self.insertItem(self.count(), new_action)
        self.scrollToBottom()

    @QtCore.pyqtSlot(lg.Action)
    def remove_action(self, undo_action: lg.Action) -> None:
        """Removes an Action from the displayed list and deletes it."""
        item_pos = self.row(undo_action)
        undo_item = self.takeItem(item_pos)
        del undo_item
        self.scrollToBottom()

    def discard_changes(self):
        for logger in self._loggers:
            logger.discard_changes()
