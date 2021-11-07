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

    action: str
    _parent_id: str = None
    _frame: int = None
    revert: bool = False

    @property
    def inverted(self):
        """Returns a 'plain' inverted version of the action without any
        coupled actions."""
        return self.invert()

    @property
    def parent_id(self) -> str:
        """The ID of the object that is responsible for (reverting) this
        action."""
        return self._parent_id

    @parent_id.setter
    def parent_id(self, new_id: str):
        self._parent_id = new_id
        self.setText(str(self))

    @property
    def frame(self) -> int:
        """Property holding the frame on which this Action was performed."""
        return self._frame

    @frame.setter
    def frame(self, frame_id: int) -> None:
        self._frame = frame_id
        self.setText(str(self))

    @abstractmethod
    def __str__(self):
        """Returns a string representation of the action."""

    @abstractmethod
    def undo(self, rods: Optional[Iterable[RodNumberWidget]]):
        """Triggers events to revert this action."""

    def to_save(self):
        """Gives information for saving this action, None, if it's not
        savable."""
        return None

    def invert(self):
        """Generates an inverted version of the Action (for redoing),
        None if the Action is not invertible."""
        return None


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

    Attributes
    ----------
    action : FileActions
        Description of what kind of action was performed.
    file : str
        Path to the file that this action describes.
    file_num : Union[int, None]
        Number of the image file that was loaded. It will be displayed to
        the user, if it was set.
    cam_id : str
        The objects ID on which behalf this action was done. This is
        necessary for displaying it to the user.

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

    Attributes
    ----------
    rod : RodNumberWidget
        A copy of the rod whose number is changed.
    new_id : int
        The new rod number of the changed rod.
    action : str
        Description of what kind of action was performed.
        (Default is "Changed rod")
    coupled_action : Union[Action, None]
        The instance of an `Action` that is performed at the same time with
        this and must be reverted as well, if this `Action` is reverted.
    """

    def __init__(self, old_rod: RodNumberWidget, new_id: int,
                 coupled_action: Action = None, *args,
                 **kwargs):
        self.rod = old_rod
        self.new_id = new_id
        self.action = "Changed rod"
        self.coupled_action = coupled_action
        super().__init__(str(self), *args, **kwargs)

    @property
    def inverted(self):
        rod = self.rod.copy()
        rod.rod_id = self.new_id
        inverted = ChangedRodNumberAction(rod, self.rod.rod_id)
        inverted.parent_id = self.parent_id
        inverted.frame = self.frame
        return inverted

    def __str__(self):
        to_str = f") {self.action} #{self.rod.rod_id} ---> #{self.new_id}"
        if self.rod is not None:
            to_str = f"{self.rod.color}" + to_str
        if self.frame is not None:
            to_str = f"{self.frame}, " + to_str
        if self._parent_id is not None:
            to_str = f"{self._parent_id}, " + to_str
        to_str = "(" + to_str
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

    def to_save(self):
        """Generates a data representation of this action for saving.

        Returns
        -------
        dict
            Available fields: ("rod_id", "cam_id", "frame", "color",
            "position")
        """
        out = {
            "position": self.rod.rod_points,
            "cam_id": self.parent_id,
            "frame": self.frame,
            "color": self.rod.color
        }
        if self.revert:
            # If the action was reverted
            out["rod_id"] = self.rod.rod_id
        else:
            # If the action was performed
            out["rod_id"] = self.new_id
        return out

    def invert(self):
        """Generates an inverted version of the ChangedRodNumberAction (for
        redoing).

        Returns
        -------
        ChangedRodNumberAction
        """
        rod = self.rod.copy()
        rod.rod_id = self.new_id
        inverted = ChangedRodNumberAction(rod, self.rod.rod_id)
        inverted.parent_id = self.parent_id
        inverted.frame = self.frame
        if self.coupled_action is not None:
            inverted.coupled_action = self.coupled_action.inverted
        if inverted.coupled_action is not None:
            inverted.coupled_action.coupled_action = inverted
        return inverted


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

    Attributes
    ----------
    rod : RodNumberWidget
        A copy of the rod whose position was changed, prior to the change.
    action : str
        Description of what kind of action was performed.
        (Default is "Deleted rod")
    coupled_action : Union[Action, ChangeRodNumberAction, None]
        The instance of an `Action` that is performed at the same time with
        this and must be reverted as well, if this `Action` is reverted.

    """
    def __init__(self, old_rod: RodNumberWidget, coupled_action: Union[
        Action, ChangedRodNumberAction] = None,
                 *args, **kwargs):
        self.rod = old_rod
        self.action = "Deleted rod"
        self.coupled_action = coupled_action
        super().__init__(str(self), *args, **kwargs)

    @property
    def inverted(self):
        rod = self.rod.copy()
        inverted = CreateRodAction(rod)
        inverted.parent_id = self.parent_id
        inverted.frame = self.frame
        return inverted

    def __str__(self):
        to_str = f") {self.action} #{self.rod.rod_id}"
        if self.rod is not None:
            to_str = f"{self.rod.color}" + to_str
        if self.frame is not None:
            to_str = f"{self.frame}, " + to_str
        if self._parent_id is not None:
            to_str = f"{self._parent_id}, " + to_str
        to_str = "(" + to_str
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
        if self.coupled_action:
            self.rod.rod_id = self.coupled_action.new_id
        self.rod.setText(str(self.rod.rod_id))
        self.rod.rod_state = RodState.NORMAL
        self.rod.setVisible(True)
        return self.rod

    def to_save(self):
        """Generates a data representation of this action for saving.

        Returns
        -------
        dict
            Available fields: ("rod_id", "cam_id", "frame", "color",
            "position")
        """
        out = {
            "rod_id": self.rod.rod_id,
            "cam_id": self.parent_id,
            "frame": self.frame,
            "color": self.rod.color
        }
        if self.revert:
            # If the action was reverted
            out["position"] = self.rod.rod_points
        else:
            # If the action was performed
            out["position"] = [0, 0, 0, 0]
        return out

    def invert(self):
        """Generates an inverted version of the DeleteRodAction (for redoing).

        Returns
        -------
        ChangeRodPositionAction
        """
        rod = self.rod.copy()
        inverted = CreateRodAction(rod)
        inverted.parent_id = self.parent_id
        inverted.frame = self.frame
        if self.coupled_action is not None:
            inverted.coupled_action = self.coupled_action.inverted
        if inverted.coupled_action is not None:
            inverted.coupled_action.coupled_action = inverted
        return inverted


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

        to_str = f") #{self.rod.rod_id} {self.action}: {initial_pos} ---" \
                 f"> {end_pos}"
        if self.rod is not None:
            to_str = f"{self.rod.color}" + to_str
        if self.frame is not None:
            to_str = f"{self.frame}, " + to_str
        if self._parent_id is not None:
            to_str = f"{self._parent_id}, " + to_str
        to_str = "(" + to_str
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

    def to_save(self):
        """Generates a data representation of this action for saving.

        Returns
        -------
        dict
            Available fields: ("rod_id", "cam_id", "frame", "color",
            "position")
        """
        out = {
            "rod_id": self.rod.rod_id,
            "cam_id": self.parent_id,
            "frame": self.frame,
            "color": self.rod.color
        }
        if self.revert:
            # If the action was reverted
            out["position"] = self.rod.rod_points
        else:
            # If the action was performed
            out["position"] = self.new_pos
        return out

    def invert(self):
        """Generates an inverted version of the ChangeRodPositionAction (for
        redoing).

        Returns
        -------
        ChangeRodPositionAction
        """
        rod = self.rod.copy()
        rod.rod_points = self.new_pos
        inverted = ChangeRodPositionAction(rod, self.rod.rod_points)
        inverted.parent_id = self.parent_id
        inverted.frame = self.frame
        return inverted


class CreateRodAction(Action):
    """Class to represent the creation of a new rod as a loggable action.

    Parameters
    ----------
    new_rod : RodNumberWidget
        A copy of the rod which was created.
    *args : iterable
        Positional arguments for the `QListWidgetItem` superclass.
    **kwargs : dict
        Keyword arguments for the `QListWidgetItem` superclass.

    Attributes
    ----------
    rod : RodNumberWidget
        A copy of the rod which was created.
    action : str
        Default is "Created new rod".
    """

    def __init__(self, new_rod: RodNumberWidget, coupled_action: Union[
        Action, ChangedRodNumberAction] = None, *args, **kwargs):
        self.rod = new_rod
        self.action = "Created new rod"
        self.coupled_action = coupled_action
        super().__init__(str(self), *args, **kwargs)

    @property
    def inverted(self):
        inverted = DeleteRodAction(self.rod.copy())
        inverted.parent_id = self.parent_id
        inverted.frame = self.frame
        return inverted

    def __str__(self):
        to_str = ") " + self.action + f" #{self.rod.rod_id}"
        if self.rod is not None:
            to_str = f"{self.rod.color}" + to_str
        if self.frame is not None:
            to_str = f"{self.frame}, " + to_str
        if self._parent_id is not None:
            to_str = f"{self._parent_id}, " + to_str
        to_str = "(" + to_str
        return to_str

    def undo(self, rods: List[RodNumberWidget] = None) -> \
            List[RodNumberWidget]:
        """Triggers events to revert this action.

        Parameters
        ----------
        rods : List[RodNumberWidget]
            A list of `RodNumberWidget`s in which should be the created rod.

        Returns
        -------
        List[RodNumberWidget]

        Raises
        ------
        Exception
        """
        if rods is None:
            raise Exception("Unable to revert this action. No rods supplied.")
        for rod in rods:
            if rod.rod_id == self.rod.rod_id:
                rods.remove(rod)
                rod.deleteLater()
                return rods
        return rods

    def to_save(self):
        """Generates a data representation of this action for saving.

        Returns
        -------
        dict
            Available fields: ("rod_id", "cam_id", "frame", "color",
            "position")
        """
        out = {
            "rod_id": self.rod.rod_id,
            "cam_id": self.parent_id,
            "frame": self.frame,
            "color": self.rod.color
        }
        if self.revert:
            # If the action was reverted
            out["position"] = [0, 0, 0, 0]
        else:
            # If the action was performed
            out["position"] = self.rod.rod_points
        return out

    def invert(self):
        """Generates an inverted version of the CreateRodAction (for redoing).

        Returns
        -------
        DeleteRodAction
        """
        inverted = DeleteRodAction(self.rod.copy())
        inverted.parent_id = self.parent_id
        inverted.frame = self.frame
        if self.coupled_action is not None:
            inverted.coupled_action = self.coupled_action.inverted
        if inverted.coupled_action is not None:
            inverted.coupled_action.coupled_action = inverted
        return inverted


class ActionLogger(QtCore.QObject):
    """Logs actions performed on its associated GUI object.

    Keeps track of actions performed on/by a GUI object that is associated
    with it. It provides a list of the performed actions to a
    `ActionLoggerWidget` for display in the GUI. It is also used to trigger
    reverting of these actions. Do NOT create instances of this class
    directly but let an instance of the `ActionLoggerWidget` class do that,
    if the logged actions shall be displayed in the GUI.

    Parameters
    ----------
    *args :
        Positional arguments for the QObject superclass.
    **kwargs :
        Keyword arguments for the QObject superclass.

    Attributes
    ----------
    parent_id : str
        ID of the GUI object from which actions are logged. It must be human
        readable as it is used for labelling the actions displayed in the GUI.
    logged_actions : List[Action]
        A list of all actions performed/logged with this instance
        (saved and unsaved).
    unsaved_changes : List[Action]
        A list of all actions performed/logged with this instance that are
        savable but currently unsaved.
    repeatable_changes : List[Action]
        An ordered list of all currently redoable/repeatable actions that were
        logged with this instance.

    Signals
    -------
    undo_action(Action)
        Requests the reverting of the `Action` that is given as the payload.
    undone_action(Action)
        Notifies that the `Action` in the payload has been reverted.
    added_action(Action)
        Notifies that this object logged the `Action` from the payload.
    notify_unsaved(bool)
        Notifies, if this objects attribute `unsaved_changes` changes from
        empty to being filled with one or more items (True) or from filled to
        being empty (False).
    request_saving(bool)
        Requests the saving of any unsaved changes.
        True    ->  permanent saving
        False   ->  temporary saving
    data_changed(Action)
        Notifies, if this object logged, undid, redid something that changed
        the displayed data.


    Slots
    -----
    undo_last(str)
    actions_saved()
    redo_last(str)

    """
    __pyqtSignals__ = ("undoAction(Action)",)
    # Create custom signals
    undo_action = QtCore.pyqtSignal(Action, name="undoAction")
    undone_action = QtCore.pyqtSignal(Action, name="undone_action")
    added_action = QtCore.pyqtSignal(Action, name="added_action")
    notify_unsaved = QtCore.pyqtSignal(bool, name="notify_unsaved")
    request_saving = QtCore.pyqtSignal(bool, name="request_saving")
    data_changed = QtCore.pyqtSignal(Action, name="data_changed")
    unsaved_changes: List[Action]
    parent_id: str
    frame: int = None

    def __init__(self, parent_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_id = parent_id
        self.logged_actions = []
        self.unsaved_changes = []
        self.repeatable_changes = []

    def add_action(self, last_action: Action) -> None:
        """Registers the actions performed by its parent and propagates them
        for visual display in the GUI."""
        last_action.parent_id = self.parent_id
        last_action.frame = self.frame
        self.logged_actions.append(last_action)
        if self.repeatable_changes:
            self.repeatable_changes = []
        if type(last_action) is not FileAction:
            if not self.unsaved_changes:
                self.notify_unsaved.emit(True)
            self.unsaved_changes.append(last_action)
        elif type(last_action) is FileAction:
            if last_action.action == FileActions.SAVE:
                self.unsaved_changes = []
                self.notify_unsaved.emit(False)
        self.added_action.emit(last_action)
        self.data_changed.emit(last_action)

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
        inv_undo_item = undo_item.invert()
        self.repeatable_changes.append(inv_undo_item)
        if undo_item not in self.unsaved_changes:
            if not self.unsaved_changes:
                self.notify_unsaved.emit(True)
            self.unsaved_changes.append(inv_undo_item)
        else:
            # Remove & Delete action
            self.unsaved_changes.pop()
            if not self.unsaved_changes:
                # No more unsaved changes present
                self.notify_unsaved.emit(False)
        undo_item.revert = True
        self.undo_action.emit(undo_item)
        self.data_changed.emit(undo_item)
        del undo_item

    def register_undone(self, undone_action: Action):
        """Lets the logger know that an action was undone without using its
        undo method(s)."""
        if undone_action in self.logged_actions:
            undone_action.revert = True
            self.data_changed.emit(undone_action)
            try:
                self.unsaved_changes.remove(undone_action)
            except ValueError:
                # The unsaved_changes were deleted (is intended when the
                # changes were changed)
                pass
            self.logged_actions.remove(undone_action)
            self.undone_action.emit(undone_action)
            if not self.unsaved_changes:
                # No more unsaved changes present
                self.notify_unsaved.emit(False)

    def discard_changes(self):
        """Discards all unsaved changes made. Currently only deletes the
        Actions, but does NOT revert the changes."""
        for item in self.unsaved_changes:
            item.revert = True
            self.data_changed.emit(item)
            self.undo_action.emit(item)
            self.logged_actions.remove(item)
            self.undone_action.emit(item)
            del item
        # Save changes only in the temp location
        self.unsaved_changes = []
        self.notify_unsaved.emit(False)

    @QtCore.pyqtSlot()
    def actions_saved(self):
        """All unsaved actions were saved"""
        if self.unsaved_changes:
            self.unsaved_changes = []
            self.notify_unsaved.emit(False)

    @QtCore.pyqtSlot(str)
    def redo_last(self, parent_id: str) -> None:
        """De-registers the last undone action recorded and triggers its
        undo-(actually redo-)process."""
        if parent_id != self.parent_id:
            return

        if not self.repeatable_changes:
            # Nothing repeatable yet
            return
        rep_item = self.repeatable_changes.pop()
        inv_rep_item = rep_item.invert()
        try:
            if rep_item is self.unsaved_changes[-1]:
                self.unsaved_changes.pop()
                if not self.unsaved_changes:
                    # No more unsaved changes present
                    self.notify_unsaved.emit(False)
        except IndexError:
            try:
                if inv_rep_item.coupled_action is not None:
                    self.unsaved_changes.append(inv_rep_item.coupled_action)
            except AttributeError:
                pass
            self.unsaved_changes.append(inv_rep_item)
            self.notify_unsaved.emit(True)

        # Insert the coupled action before its parent to keep the correct
        # order for undoing
        try:
            if inv_rep_item.coupled_action is not None:
                self.logged_actions.append(inv_rep_item.coupled_action)
                rep_item.coupled_action.revert = True
                self.data_changed.emit(rep_item.coupled_action)
                self.added_action.emit(inv_rep_item.coupled_action)
        except AttributeError:
            pass
        self.logged_actions.append(inv_rep_item)

        rep_item.revert = True
        self.data_changed.emit(rep_item)
        self.undo_action.emit(rep_item)
        self.added_action.emit(inv_rep_item)
        del rep_item


class ActionLoggerWidget(QListWidget):
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
        `ActionLogger` objects maintained by this `ActionLoggerWidget`
        instance. Do NOT try to insert performed actions in here directly.
        This property only derives its contents from the `ActionLogger`
        objects.
    repeatable_changes : List[Action]
        An ordered list of all currently redoable/repeatable actions that were
        logged by the `ActionLogger` objects maintained by this
        `ActionLoggerWidget` instance. Do NOT try to insert performed actions
        in here directly. This property only derives its contents from the
        `ActionLogger` objects.

    Slots
    -----
    add_action(Action)
    remove_action(Action)

    """

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
        List[Action]
        """
        all_unsaved = [item for changes in self._loggers for item in
                       changes.unsaved_changes]
        return all_unsaved

    @property
    def repeatable_changes(self) -> List[Action]:
        """Collects the repeatable changes from all loggers and returns them
        collectively.

        Returns
        -------
        List[Action]
        """
        all_repeatable = [item for changes in self._loggers for item in
                          changes.repeatable_changes]
        return all_repeatable

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
