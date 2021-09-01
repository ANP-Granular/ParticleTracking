import tempfile
from abc import abstractmethod
from enum import Enum
from typing import Optional, Iterable

from PyQt5.QtWidgets import QListWidgetItem, QListWidget
from PyQt5 import QtCore

from rodnumberwidget import RodNumberWidget, RodState

TEMP_DIR = tempfile.gettempdir() + "/RodTracker"


class FileActions(Enum):
    SAVE = "Saved changes"
    LOAD_IMAGES = "image file(s) loaded from"
    OPEN_IMAGE = "Opened image"
    MODIFY = "Modified file"
    LOAD_RODS = "Loaded rod file(s) from"


class Action(QListWidgetItem):
    action: str

    @abstractmethod
    def __str__(self):
        """Returns a string representation of the action."""

    @abstractmethod
    def undo(self, rods: Optional[Iterable[RodNumberWidget]]):
        """Triggers events to undo this action."""


class FileAction(Action):
    action: FileActions

    def __init__(self, path: str, action: FileActions, file_num=None,
                 *args, **kwargs):
        self.file = path
        self.action = action
        self.file_num = None
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
        return to_str

    def undo(self, rods=None):
        if self.action is FileActions.MODIFY:
            # TODO: evaluate whether it should be implemented
            pass
        else:
            # This action cannot be undone
            return


class DeleteRodAction(Action):
    def __init__(self, old_rod: RodNumberWidget, coupled_action: Action = None,
                 *args, **kwargs):
        self.rod = old_rod
        self.action = "Deleted rod"
        self.coupled_action = coupled_action
        super().__init__(str(self), *args, **kwargs)

    def __str__(self):
        return f"{self.action} #{self.rod.rod_id}"

    def undo(self, rods: [RodNumberWidget] = None):
        self.rod.rod_id = self.coupled_action.new_id
        self.rod.setText(str(self.rod.rod_id))
        self.rod.rod_state = RodState.NORMAL
        self.rod.setVisible(True)
        return self.rod


class ChangedRodNumberAction(Action):
    def __init__(self, old_rod: RodNumberWidget, new_id: int,
                 coupled_action: Action = None, *args,
                 **kwargs):
        self.rod = old_rod
        self.new_id = new_id
        self.action = "Changed rod"
        self.coupled_action = coupled_action
        super().__init__(str(self), *args, **kwargs)

    def __str__(self):
        return f"{self.action} #{self.rod.rod_id} ---> #{self.new_id}"

    def undo(self, rods: [RodNumberWidget]) -> [RodNumberWidget]:
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


class ChangeRodPositionAction(Action):
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
        return f"#{self.rod.rod_id} {self.action}: {initial_pos} ---" \
               f"> {end_pos}"

    def undo(self, rods: [RodNumberWidget] = None) -> [RodNumberWidget]:
        if rods is None:
            raise Exception("Unable to undo action. No rods supplied.")
        for rod in rods:
            if rod.rod_id == self.rod.rod_id:
                rod.rod_points = self.rod.rod_points
                return rods


class ActionLogger(QListWidget):
    __pyqtSignals__ = ("undoAction(Action)",)
    # Create custom signals
    undo_action = QtCore.pyqtSignal(Action, name="undoAction")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unsaved_changes = []
        self.temp_manager = tempfile.TemporaryDirectory(
            prefix="Session_", dir=TEMP_DIR)

    def add_action(self, last_action: Action):
        self.insertItem(self.count(), last_action)
        if type(last_action) != FileAction:
            self.unsaved_changes.append(last_action)
        elif type(last_action) == FileAction:
            if last_action.action == FileActions.SAVE:
                # Clear unsaved changes
                self.unsaved_changes = []
        self.item(self.count()-1).setSelected(True)
        self.scrollToBottom()

    def catch_rodnumber_change(self, new_rod: RodNumberWidget, last_id: int)\
            -> ChangedRodNumberAction:
        old_rod = new_rod.copy_rod()
        old_rod.setEnabled(False)
        old_rod.setVisible(False)
        old_rod.rod_id = last_id
        new_id = new_rod.rod_id
        this_action = ChangedRodNumberAction(old_rod, new_id)
        self.add_action(this_action)
        return this_action

    def undo_last(self):
        undo_item = self.takeItem(self.count()-1)
        if undo_item in self.unsaved_changes:
            self.undo_action.emit(undo_item)
            self.unsaved_changes.remove(undo_item)
            del undo_item
            self.scrollToBottom()
        else:
            self.insertItem(self.count(), undo_item)

    def discard_changes(self):
        # TODO: also undo changes in the temp file (later)
        all_items = [self.item(idx) for idx in range(self.count())]
        for item in all_items:
            if item in self.unsaved_changes:
                self.takeItem(self.indexFromItem(item).row())
                self.unsaved_changes.remove(item)
                del item
