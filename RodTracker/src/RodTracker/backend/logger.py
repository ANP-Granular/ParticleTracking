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

"""**TBD**"""

import logging
import pathlib
import tempfile
from abc import abstractmethod
from enum import Enum
from typing import Iterable, List, Optional

from PyQt5 import QtCore
from PyQt5.QtWidgets import QListWidgetItem

from RodTracker import DATA_DIR, Singleton

_logger = logging.getLogger(__name__)


class FileActions(Enum):
    """Helper class holding all valid kinds of :class:`FileActions`.

    Attributes
    ----------
    SAVE : str
        String representing the base of a saving to file action.
    LOAD_IMAGES : str
        String representing the base of a loaded images action.
    OPEN_IMAGE : str
        .. deprecated:: 0.1.0
            Should not be used anymore, because it clutters the displayed log
            of performed actions.
    MODIFY : str
        .. deprecated:: 0.1.0
            Should not used be anymore, because all changes are made in RAM.
            Use :attr:`SAVE` instead.
    LOAD_RODS : str
        String representing the base of a loaded rod position data action.
    """

    SAVE = "Saved changes"
    LOAD_IMAGES = "image file(s) loaded from"
    OPEN_IMAGE = "Opened image"
    MODIFY = "Modified file"
    LOAD_RODS = "Loaded rod file(s) from"


class NotInvertableError(Exception):
    """Raised when a not invertable action is attempted to be inverted."""

    pass


class Action(QListWidgetItem):
    """Base class for all Actions that are loggable by an
    :class:`ActionLogger`."""

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
        """Property holding the frame on which this :class:`Action` was
        performed."""
        return self._frame

    @frame.setter
    def frame(self, frame_id: int) -> None:
        self._frame = frame_id
        self.setText(str(self))

    @abstractmethod
    def __str__(self):
        """Returns a string representation of the action."""

    # TODO: updated docs (esp. what is in the iterable? -> particles)
    @abstractmethod
    def undo(self, rods: Optional[Iterable]):
        """Triggers events to revert this action."""

    def to_save(self):
        """Gives information for saving this action, None, if it's not
        savable."""
        return None

    def invert(self):
        """Generates an inverted version of the :class:`Action` (for redoing),
        None if the :class:`Action` is not invertible."""
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
        Positional arguments for the ``QListWidgetItem`` superclass.
    **kwargs : dict
        Keyword arguments for the ``QListWidgetItem`` superclass.

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

    def __init__(
        self,
        path: pathlib.Path,
        action: FileActions,
        file_num=None,
        cam_id=None,
        parent_id: str = None,
        *args,
        **kwargs,
    ):
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
        if self._parent_id is not None:
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


class ActionLogger(QtCore.QObject):
    """Logs actions performed on its associated GUI object.

    Keeps track of actions performed on/by a GUI object that is associated
    with it. It provides a list of the performed actions to a
    :class:`.LoggerWidget` for display in the GUI. It is also used to trigger
    reverting of these actions. Do NOT create instances of this class
    directly but let an instance of the :class:`.LoggerWidget` class do that,
    if the logged actions shall be displayed in the GUI.

    Parameters
    ----------
    *args :
        Positional arguments for the ``QObject`` superclass.
    **kwargs :
        Keyword arguments for the ``QObject`` superclass.


    .. admonition:: Signals

        - :attr:`undo_action`
        - :attr:`undone_action`
        - :attr:`added_action`
        - :attr:`notify_unsaved`
        - :attr:`request_saving`
        - :attr:`data_changed`

    .. admonition:: Slots

        - :meth:`undo_last`
        - :meth:`actions_saved`
        - :meth:`redo_last`

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
    frame : int
        Frame number that is currently relevant to the object this logger is
        associated with.
        Default is None.
    """

    __pyqtSignals__ = ("undoAction(Action)",)
    # Create custom signals
    undo_action = QtCore.pyqtSignal(Action, name="undoAction")
    """pyqtSignal(Action) : Requests the reverting of the `Action` that is
    given as the payload.
    """

    undone_action = QtCore.pyqtSignal(Action, name="undone_action")
    """pyqtSignal(Action) : Notifies that the `Action` in the payload has been
    reverted.
    """

    added_action = QtCore.pyqtSignal(Action, name="added_action")
    """pyqtSignal(Action) : Notifies that this object logged the `Action` from
    the payload.
    """

    notify_unsaved = QtCore.pyqtSignal((bool, str), name="notify_unsaved")
    """pyqtSignal(bool, str) : Notifies, if this objects attribute
    `unsaved_changes` changes from empty to being filled with one or more items
    (True) or from filled to being empty (False). The `parent_id` is added to
    the payload.
    """

    request_saving = QtCore.pyqtSignal(bool, name="request_saving")
    """pyqtSignal(bool) : Requests the saving of any unsaved changes.

    | True    ->  permanent saving
    | False   ->  temporary saving
    """

    data_changed = QtCore.pyqtSignal(Action, name="data_changed")
    """pyqtSignal(Action) : Notifies, if this object logged/undid/redid
    something that changed the displayed data.
    """

    unsaved_changes: List[Action]
    parent_id: str
    frame: int = None

    def __init__(self, parent_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_id = parent_id
        self.logged_actions = []
        self.unsaved_changes = []
        self.repeatable_changes = []

    def __str__(self):
        return (
            f"Logger({self.parent_id}) -> "
            f"Logged {len(self.logged_actions)} actions, "
            f"with currently {len(self.unsaved_changes)} changes."
        )

    def set_frame(self, new_frame: int) -> None:
        self.frame = new_frame

    def add_action(self, last_action: Action) -> None:
        """Registers the actions performed by its parent and propagates them
        for visual display in the GUI.

        Parameters
        ----------
        last_action : Action


        .. hint::

            **Emits**

            - :attr:`added_action`
            - :attr:`data_changed`
            - :attr:`notify_unsaved`

        """
        if last_action.parent_id is None:
            last_action.parent_id = self.parent_id
        if last_action.frame is None:
            last_action.frame = self.frame
        self.logged_actions.append(last_action)
        if self.repeatable_changes:
            self.repeatable_changes = []
        if type(last_action) is not FileAction:
            if not self.unsaved_changes:
                self.notify_unsaved.emit(True, self.parent_id)
            self.unsaved_changes.append(last_action)
        elif type(last_action) is FileAction:
            if last_action.action == FileActions.SAVE:
                self.unsaved_changes = []
                self.notify_unsaved.emit(False, self.parent_id)
        self.added_action.emit(last_action)
        self.data_changed.emit(last_action)

    @QtCore.pyqtSlot(str)
    def undo_last(self, parent_id: str) -> None:
        """De-registers the last unsaved action recorded and triggers its
        undo process.

        Parameters
        ----------
        parent_id : str


        .. hint::

            **Emits**

            - :attr:`data_changed`
            - :attr:`notify_unsaved`
            - :attr:`undo_action`
        """
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
                self.notify_unsaved.emit(True, self.parent_id)
            self.unsaved_changes.append(inv_undo_item)
        else:
            # Remove & Delete action
            self.unsaved_changes.pop()
            if not self.unsaved_changes:
                # No more unsaved changes present
                self.notify_unsaved.emit(False, self.parent_id)
        undo_item.revert = True
        self.undo_action.emit(undo_item)
        self.data_changed.emit(undo_item)
        del undo_item

    def register_undone(self, undone_action: Action):
        """Lets the logger know that an action was undone without using its
        undo method(s).

        Parameters
        ----------
        undone_action : Action


        .. hint::

            **Emits**

            - :attr:`data_changed`
            - :attr:`notify_unsaved`
            - :attr:`undone_action`
        """
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
                self.notify_unsaved.emit(False, self.parent_id)

    def discard_changes(self):
        """Discards and reverts all unsaved changes made.


        .. hint::

            **Emits**

            - :attr:`data_changed`          **(potentially repeatedly)**
            - :attr:`notify_unsaved`
            - :attr:`undo_action`           **(potentially repeatedly)**
            - :attr:`undone_action`         **(potentially repeatedly)**
        """
        for item in self.unsaved_changes:
            item.revert = True
            self.data_changed.emit(item)
            self.undo_action.emit(item)
            self.logged_actions.remove(item)
            self.undone_action.emit(item)
            del item
        # Save changes only in the temp location
        self.unsaved_changes = []
        self.notify_unsaved.emit(False, self.parent_id)

    @QtCore.pyqtSlot()
    def actions_saved(self):
        """All unsaved actions were saved.


        .. hint::

            **Emits**

            - :attr:`notify_unsaved`
        """
        if self.unsaved_changes:
            self.unsaved_changes = []
            self.notify_unsaved.emit(False, self.parent_id)

    @QtCore.pyqtSlot(str)
    def redo_last(self, parent_id: str) -> None:
        """De-registers the last undone action recorded and triggers its
        undo-(actually redo-)process.

        Parameters
        ----------
        parent_id : str


        .. hint::

            **Emits**

            - :attr:`added_action`
            - :attr:`data_changed`
            - :attr:`notify_unsaved`
            - :attr:`undo_action`
            - :attr:`unsaved_changes`
        """
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
                    self.notify_unsaved.emit(False, self.parent_id)
        except IndexError:
            try:
                if inv_rep_item.coupled_action is not None:
                    self.unsaved_changes.append(inv_rep_item.coupled_action)
            except AttributeError:
                pass
            self.unsaved_changes.append(inv_rep_item)
            self.notify_unsaved.emit(True, self.parent_id)

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


# TODO: find better name than 'MainLogger'
# TODO: copy stuff from temp to more permanent dir
class MainLogger(metaclass=Singleton):
    temp_manager: tempfile.TemporaryDirectory
    _loggers: List[ActionLogger] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.temp_manager = tempfile.TemporaryDirectory(
            prefix="Session_", dir=str(DATA_DIR)
        )
        from RodTracker.ui.tabs import HistoryTab

        self.history_ui: HistoryTab = None
        _logger.info(f"New session directory: {self.temp_manager.name}")

    @property
    def unsaved_changes(self) -> List[Action]:
        """Collects the unsaved changes from all loggers and returns them
        collectively.

        An ordered list of all actions that were logged by the
        :class:`.ActionLogger` objects maintained by this :class:`LoggerWidget`
        instance. Do NOT try to insert performed actions in here directly.
        This property only derives its contents from the :class:`.ActionLogger`
        objects.

        Returns
        -------
        List[Action]
        """
        all_unsaved = [
            item
            for changes in self._loggers
            for item in changes.unsaved_changes
        ]
        return all_unsaved

    @property
    def repeatable_changes(self) -> List[Action]:
        """Collects the repeatable changes from all loggers and returns them
        collectively.

        An ordered list of all currently redoable/repeatable actions that were
        logged by the :class:`.ActionLogger` objects maintained by this
        :class:`LoggerWidget` instance. Do NOT try to insert performed actions
        in here directly. This property only derives its contents from the
        :class:`.ActionLogger` objects.

        Returns
        -------
        List[Action]
        """
        all_repeatable = [
            item
            for changes in self._loggers
            for item in changes.repeatable_changes
        ]
        return all_repeatable

    def get_new_logger(self, parent_id: str) -> ActionLogger:
        """
        Creates a new :class:`ActionLogger`, registers its signals for
        displaying the actions logged by it and returns it.

        Parameters
        ----------
        parent_id : str
            A unique name that indicates the object from which actions will
            be logged in the :class:`ActionLogger`.

        Returns
        -------
        ActionLogger
        """
        new_logger = ActionLogger(parent_id)
        if self.history_ui is not None:
            self.history_ui.connect_to_logger(new_logger)
        self._loggers.append(new_logger)
        return new_logger

    def discard_changes(self):
        """Discard unsaved changes in all maintained :class`ActionLogger`
        objects."""
        for logger in self._loggers:
            logger.discard_changes()
