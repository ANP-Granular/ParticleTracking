import tempfile
from abc import abstractmethod
from enum import Enum
from typing import Optional, Iterable, Union, List

from PyQt5.QtWidgets import QListWidgetItem, QListWidget
from PyQt5 import QtCore

from rodnumberwidget import RodNumberWidget, RodState

TEMP_DIR = tempfile.gettempdir() + "/RodTracker"


class FileActions(Enum):
    """Helper class holding all valid kinds of FileActions."""

    SAVE = "Saved changes"
    LOAD_IMAGES = "image file(s) loaded from"
    OPEN_IMAGE = "Opened image"
    MODIFY = "Modified file"
    LOAD_RODS = "Loaded rod file(s) from"


class Action(QListWidgetItem):
    """Base class for all Actions that are loggable by an `ActionLogger`."""

    # TODO: include frame(number) OR see TODO in ActionLogger as alternative
    action: str
    _parent_id: str = None

    @property
    def parent_id(self) -> str:
        """The ID of the object that is responsible for (reverting) this
        action."""
        return self._parent_id

    @parent_id.setter
    def parent_id(self, new_id: str):
        self._parent_id = new_id
        self.setText(str(self))

    @abstractmethod
    def __str__(self):
        """Returns a string representation of the action."""

    @abstractmethod
    def undo(self, rods: Optional[Iterable[RodNumberWidget]]):
        """Triggers events to revert this action."""


class FileAction(Action):
    """Class to represent a loggable action that was performed on a file.

    Parameters
    ----------
    path : str
        Path to the file that this action describes.
    action : FileActions
    file_num : int, optional
        Number of the image file that was loaded. It will be displayed to
        the user, if it was set. (Default is None)
    cam_id : str, optional
        The objects ID on which behalf this action was done. This is
        necessary for displaying it to the user. (Default is None)
    parent_id : str, optional
        The ID of the object that is responsible for (reverting) this
        action. (Default is None)
    *args : iterable
        Positional arguments for the `QListWidgetItem` superclass.
    **kwargs : dict
        Keyword arguments for the `QListWidgetItem` superclass.

    """

    action: FileActions

    def __init__(self, path: str, action: FileActions, file_num=None,
                 cam_id=None, parent_id: str = None, *args, **kwargs):

        self._parent_id = parent_id
        self.file = path
        self.action = action
        self.file_num = None
        self.cam_id = cam_id
        if action is FileActions.LOAD_IMAGES:
            self.file_num = file_num
        elif action is FileActions.LOAD_RODS:
            pass
        elif action is FileActions.MODIFY:
            pass
        super().__init__(str(self), *args, **kwargs)

    def __str__(self):
        to_str = f"{self.action.value}: {self.file}"
        if self.file_num is not None:
            to_str = str(self.file_num) + " " + to_str
        if self.cam_id is not None:
            to_str = f"({self.cam_id}) " + to_str
        elif self._parent_id is not None:
            to_str = f"({self._parent_id}) " + to_str
        return to_str

    @property
    def parent_id(self):
        return self._parent_id

    @parent_id.setter
    def parent_id(self, new_id: str):
        self._parent_id = new_id
        self.setText(str(self))

    def undo(self, rods=None):
        if self.action is FileActions.MODIFY:
            # TODO: evaluate whether it should be implemented
            pass
        else:
            # This action cannot be undone
            return


class ChangedRodNumberAction(Action):
    """Class to represent a change of the rod number as a loggable action.

    Parameters
    ----------
    rod : RodNumberWidget
        A copy of the rod whose number is changed.
    new_id : int
        The new rod number of the changed rod.
    coupled_action : Action, optional
        The instance of an `Action` that is performed at the same time with
        this and must be reverted as well, if this `Action` is reverted. For
        example when the numbers of two rods are exchanged. (Default is None)
    *args : iterable
        Positional arguments for the `QListWidgetItem` superclass.
    **kwargs : dict
        Keyword arguments for the `QListWidgetItem` superclass.
    """

    def __init__(self, old_rod: RodNumberWidget, new_id: int,
                 coupled_action: Action = None, *args,
                 **kwargs):
        self.rod = old_rod
        self.new_id = new_id
        self.action = "Changed rod"
        self.coupled_action = coupled_action
        super().__init__(str(self), *args, **kwargs)

    def __str__(self):
        to_str = f"{self.action} #{self.rod.rod_id} ---> #{self.new_id}"
        if self._parent_id is not None:
            to_str = f"({self._parent_id}) " + to_str
        return to_str

    def undo(self, rods: [RodNumberWidget]) -> [RodNumberWidget]:
        """Triggers events to revert this action.

        Parameters
        ----------
        rods : [RodNumberWidget]
            A list of `RodNumberWidget`s in which should be the originally
            changed rod(s).

        Returns
        -------
        [RodNumberWidget]
        """
        if rods is None:
            raise Exception("Unable to undo action. No rods supplied.")
        for rod in rods:
            if rod.rod_id == self.new_id:
                rod.rod_id = self.rod.rod_id
                rod.setText(str(rod.rod_id))
            elif rod.rod_id == self.rod.rod_id and type(self.coupled_action)\
                    is ChangedRodNumberAction:
                rod.rod_id = self.new_id
                rod.setText(str(rod.rod_id))
        return rods


class DeleteRodAction(Action):
    """Class to represent the deletion of a rod as a loggable action.

    Parameters
    ----------
    old_rod : RodNumberWidget
        A copy of the rod that is deleted.
    coupled_action : Union[Action, ChangedRodNumberAction], optional
        The instance of an `Action` that is performed at the same time with
        this and must be reverted as well, if this `Action` is reverted.
        (Default is None)
    *args : iterable
        Positional arguments for the `QListWidgetItem` superclass.
    **kwargs : dict
        Keyword arguments for the `QListWidgetItem` superclass.
    """
    def __init__(self, old_rod: RodNumberWidget, coupled_action: Union[
        Action, ChangedRodNumberAction] = None,
                 *args, **kwargs):
        self.rod = old_rod
        self.action = "Deleted rod"
        self.coupled_action = coupled_action
        super().__init__(str(self), *args, **kwargs)

    def __str__(self):
        to_str = f"{self.action} #{self.rod.rod_id}"
        if self._parent_id is not None:
            to_str = f"({self._parent_id}) " + to_str
        return to_str

    def undo(self, rods: [RodNumberWidget] = None):
        """Triggers events to revert this action.

        Parameters
        ----------
        rods : [RodNumberWidget]
            A list of `RodNumberWidget`s in which should be the originally
            changed rod(s).

        Returns
        -------
        [RodNumberWidget]
        """
        self.rod.rod_id = self.coupled_action.new_id
        self.rod.setText(str(self.rod.rod_id))
        self.rod.rod_state = RodState.NORMAL
        self.rod.setVisible(True)
        return self.rod


class ChangeRodPositionAction(Action):
    """Class to represent the change of a rod's position as a loggable action.

    Parameters
    ----------
    old_rod : RodNumberWidget
        A copy of the rod whose position was changed, prior to the change.
    new_postion : [int]
        The newly set starting and ending points of the rod, i.e. [x1, y1,
        x2, y2].
    *args : iterable
        Positional arguments for the `QListWidgetItem` superclass.
    **kwargs : dict
        Keyword arguments for the `QListWidgetItem` superclass.

    Attributes
    ----------
    rod : RodNumberWidget
        A copy of the rod whose position was changed, prior to the change.
    new_pos : [int]
        The newly set starting and ending points of the rod.
    action : str
        Default is "Rod position updated".
    """

    def __init__(self, old_rod: RodNumberWidget, new_position: [int], *args,
                 **kwargs):
        self.rod = old_rod
        self.new_pos = new_position
        self.action = "Rod position updated"
        super().__init__(str(self), *args, **kwargs)

    def __str__(self):
        initial_pos = "[("
        end_pos = "[("
        for coord in range(4):
            initial_pos += f"{self.rod.rod_points[coord]:.2f}"
            end_pos += f"{self.new_pos[coord]:.2f}"
            if (coord % 2) == 0:
                initial_pos += ", "
                end_pos += ", "
            elif coord == 1:
                initial_pos += "), ("
                end_pos += "), ("
        initial_pos += ")]"
        end_pos += ")]"

        to_str = f"#{self.rod.rod_id} {self.action}: {initial_pos} ---" \
                 f"> {end_pos}"
        if self._parent_id is not None:
            to_str = f"({self._parent_id}) " + to_str
        return to_str

    def undo(self, rods: [RodNumberWidget] = None) -> [RodNumberWidget]:
        """Triggers events to revert this action.

        Parameters
        ----------
        rods : [RodNumberWidget]
            A list of `RodNumberWidget`s in which should be the originally
            changed rod(s).

        Returns
        -------
        [RodNumberWidget]

        Raises
        ------
        Exception
        """
        if rods is None:
            raise Exception("Unable to undo action. No rods supplied.")
        for rod in rods:
            if rod.rod_id == self.rod.rod_id:
                rod.rod_points = self.rod.rod_points
                return rods


class ActionLogger(QtCore.QObject):
    __pyqtSignals__ = ("undoAction(Action)",)
    # Create custom signals
    undo_action = QtCore.pyqtSignal(Action, name="undoAction")
    undone_action = QtCore.pyqtSignal(Action, name="undone_action")
    added_action = QtCore.pyqtSignal(Action, name="added_action")
    notify_unsaved = QtCore.pyqtSignal(bool, name="notify_unsaved")
    request_saving = QtCore.pyqtSignal(bool, name="request_saving")
    unsaved_changes: List[Action]
    parent_id: str

    def __init__(self, parent_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_id = parent_id
        self.logged_actions = []
        # TODO: make unsaved_changes a dict {frame_no: [Action]}  OR  see
        #  TODO in Action as an alternative
        self.unsaved_changes = []

    def add_action(self, last_action: Action) -> None:
        """Registers the actions performed by its parent and propagates them
        for visual display in the GUI."""
        last_action.parent_id = self.parent_id
        self.logged_actions.append(last_action)
        if type(last_action) is not FileAction:
            if not self.unsaved_changes:
                self.notify_unsaved.emit(True)
            self.unsaved_changes.append(last_action)
        elif type(last_action) is FileAction:
            if last_action.action == FileActions.SAVE:
                self.unsaved_changes = []
                self.notify_unsaved.emit(False)
        self.added_action.emit(last_action)

    @QtCore.pyqtSlot(str)
    def undo_last(self, parent_id: str) -> None:
        """De-registers the last unsaved action recorded and triggers its
        undo process."""
        if parent_id != self.parent_id:
            return
        if not self.logged_actions:
            # Nothing logged yet
            return
        undo_item = self.logged_actions.pop()
        if undo_item not in self.unsaved_changes:
            # Last action is not revertible, no further action required
            self.logged_actions.append(undo_item)
            return
        # Remove & Delete action
        self.unsaved_changes.pop()
        if not self.unsaved_changes:
            # No more unsaved changes present
            self.notify_unsaved.emit(False)
        self.undo_action.emit(undo_item)
        del undo_item

    def register_undone(self, undone_action: Action):
        """Lets the logger know that an action was undone without using its
        undo method(s)."""
        if undone_action in self.unsaved_changes:
            self.unsaved_changes.remove(undone_action)
            self.logged_actions.remove(undone_action)
            self.undone_action.emit(undone_action)
            if not self.unsaved_changes:
                # No more unsaved changes present
                self.notify_unsaved.emit(False)

    def discard_changes(self):
        """Discards all unsaved changes made. Currently only deletes the
        Actions, but does NOT revert the changes."""
        for item in self.unsaved_changes:
            self.undo_action.emit(item)
            self.logged_actions.remove(item)
            self.undone_action.emit(item)
            del item
        # Save changes only in the temp location
        self.request_saving.emit(True)
        self.unsaved_changes = []
        self.notify_unsaved.emit(False)

    @QtCore.pyqtSlot()
    def actions_saved(self):
        """All unsaved actions were saved"""
        if self.unsaved_changes:
            self.unsaved_changes = []
            self.notify_unsaved.emit(False)


class ActionLoggerWidget(QListWidget):
    temp_manager: tempfile.TemporaryDirectory
    _loggers: List[ActionLogger] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.temp_manager = tempfile.TemporaryDirectory(
            prefix="Session_", dir=TEMP_DIR)

    @property
    def unsaved_changes(self) -> List[Action]:
        """Collects the unsaved changes from all loggers and returns them
        collectively.

        Returns
        -------
        List[Action]"""
        all_unsaved = [item for changes in self._loggers for item in
                       changes.unsaved_changes]
        return all_unsaved

    def get_new_logger(self, parent_id: str) -> ActionLogger:
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
        new_logger = ActionLogger(parent_id)
        new_logger.added_action.connect(self.add_action)
        new_logger.undo_action.connect(self.remove_action)
        new_logger.undone_action.connect(self.remove_action)
        self._loggers.append(new_logger)
        return new_logger

    @QtCore.pyqtSlot(Action)
    def add_action(self, new_action: Action) -> None:
        """Adds a new action to the list being displayed in the GUI."""
        if not self._loggers:
            # No loggers exist yet/anymore
            return
        self.insertItem(self.count(), new_action)
        self.scrollToBottom()

    @QtCore.pyqtSlot(Action)
    def remove_action(self, undo_action: Action) -> None:
        """Removes an Action from the displayed list and deletes it."""
        item_pos = self.row(undo_action)
        undo_item = self.takeItem(item_pos)
        del undo_item
        self.scrollToBottom()

    def discard_changes(self):
        # FIXME: It might be a bad idea to discard the changes from all the
        #  loggers here. The question is whether this should be used only in
        #  the application close operation or whether its used when new data
        #  is loaded or when stuff is done on only one of the cameras?
        for logger in self._loggers:
            logger.discard_changes()
