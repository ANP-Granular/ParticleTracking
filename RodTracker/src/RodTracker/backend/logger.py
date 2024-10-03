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
Class and methods used in RodTracked GUI for manipulation with particles
coordinate data and logging the resulting actions.

**Author:**     Adrian Niemann (adrian.niemann@ovgu.de)\n
**Date:**       2022-2024
"""

import logging
import pathlib
from abc import abstractmethod
from enum import Enum, auto
from typing import Iterable, List, Optional, Union

import numpy as np
from pandas import DataFrame
from PyQt5 import QtCore
from PyQt5.QtWidgets import QListWidgetItem

import RodTracker.ui.rodnumberwidget as rn

_logger = logging.getLogger(__name__)


def qt_error_handler(
    mode: QtCore.QtMsgType, context: QtCore.QMessageLogContext, msg: str
):
    """Handler for logging uncaught Qt exceptions during the program flow."""
    context_info = (
        f"category: {context.category}\n"
        f"function: {context.function}, line: {context.line}\n"
        f"file: {context.file}\n"
    )
    if mode == QtCore.QtInfoMsg:
        _logger.info(context_info + f"{msg}")
    elif mode == QtCore.QtWarningMsg:
        _logger.warning(context_info + f"{msg}")
    elif mode == QtCore.QtCriticalMsg:
        _logger.critical(context_info + f"{msg}")
    elif mode == QtCore.QtFatalMsg:
        _logger.error(context_info + f"{msg}")
    else:
        _logger.debug(context_info + f"{msg}")


QtCore.qInstallMessageHandler(qt_error_handler)


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


class NumberChangeActions(Enum):
    """Helper class holding valid kinds of rod number changes.

    Attributes
    ----------
    ALL : int
        Indicates a switch of rod numbers in all cameras from the current frame
        to the last frame of the dataset.
    ALL_ONE_CAM : int
        Indicates a switch of rod numbers in the currently displayed camera
        from the current frame to the last frame of the dataset.
    ONE_BOTH_CAMS : int
        Indicates a switch of rod numbers in all cameras for the current frame
        only.
    CURRENT : int
        Indicates a switch of rod numbers in the current camera only and the
        current frame only.
    """

    ALL = auto()
    ALL_ONE_CAM = auto()
    ONE_BOTH_CAMS = auto()
    CURRENT = auto()


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

    @abstractmethod
    def undo(self, rods: Optional[Iterable[rn.RodNumberWidget]]):
        """Triggers events to revert this action."""

    def to_save(self):
        """Gives information for saving this action, None, if it's not
        savable."""
        return None

    def invert(self):
        """Generates an inverted version of the :class:`Action` (for redoing),
        None if the :class:`Action` is not invertible."""
        raise NotInvertableError


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


class DeleteData(Action):
    def __init__(
        self, data: DataFrame, parent_id: str = None, *args, **kwargs
    ):
        self.action = "Deleted data"
        self.del_data = data
        self._parent_id = parent_id
        self.colors = self.del_data.color.unique()

        super().__init__(str(self), *args, **kwargs)

        frames = self.del_data.frame.unique()
        if len(frames) == 1:
            self.frame = frames[0]

    def __str__(self):
        to_str = ""
        if self._parent_id is not None:
            to_str += f"({self._parent_id}) "
        to_str += f"{self.action}: {len(self.del_data)} particles"

        if len(self.colors) == 1:
            to_str += f" of class '{self.colors[0]}'"

        if self.frame:
            to_str += f" on frame {self.frame}"
        else:
            to_str += f" on {len(self.del_data.frame.unique())} frames"
        return to_str

    def undo(self, rods: Optional[Iterable[rn.RodNumberWidget]] = None):
        """Do NOT use for this type of Action."""
        return []

    def to_save(self):
        # TODO
        super().to_save(self)

    def invert(self):
        # TODO: verify this works as expected! (eg. inverted_action is not
        #       deleted prematurely)
        inverted_action = DeleteData(self.del_data, self.parent_id)
        inverted_action.revert = not self.revert
        return inverted_action


class ChangedRodNumberAction(Action):
    """Class to represent a change of the rod number as a loggable action.

    Parameters
    ----------
    rod : RodNumberWidget
        A copy of the rod whose number is changed.
    new_id : int
        The new rod number of the changed rod.
    coupled_action : Action, optional
        The instance of an :class:`Action` that is performed at the same time
        with this and must be reverted as well, if this :class:`Action` is
        reverted. For example when the numbers of two rods are exchanged.
        (Default is None)
    *args : iterable
        Positional arguments for the ``QListWidgetItem`` superclass.
    **kwargs : dict
        Keyword arguments for the ``QListWidgetItem`` superclass.

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
        The instance of an :class:`Action` that is performed at the same time
        with this and must be reverted as well, if this :class:`Action` is
        reverted.
    """

    def __init__(
        self,
        old_rod: rn.RodNumberWidget,
        new_id: int,
        coupled_action: Action = None,
        *args,
        **kwargs,
    ):
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

    def undo(self, rods: List[rn.RodNumberWidget]) -> List[rn.RodNumberWidget]:
        """Triggers events to revert this action.

        Parameters
        ----------
        rods : List[RodNumberWidget]
            A list of :class:`RodNumberWidget` in which should be the
            originally changed rod(s).

        Returns
        -------
        List[RodNumberWidget]
        """
        if rods is None:
            raise Exception("Unable to undo action. No rods supplied.")
        for rod in rods:
            if rod.rod_id == self.new_id:
                rod.rod_id = self.rod.rod_id
                rod.setText(str(rod.rod_id))
            elif (
                rod.rod_id == self.rod.rod_id
                and type(self.coupled_action) is ChangedRodNumberAction
            ):
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
            "color": self.rod.color,
            "seen": self.rod.seen,
        }
        if self.revert:
            # If the action was reverted
            out["rod_id"] = self.rod.rod_id
        else:
            # If the action was performed
            out["rod_id"] = self.new_id
        return out

    def invert(self):
        """Generates an inverted version of the :class:`ChangedRodNumberAction`
        (for redoing).

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
        The instance of an :class:`Action` that is performed at the same time
        with this and must be reverted as well, if this :class:`Action` is
        reverted.
        (Default is None)
    *args : iterable
        Positional arguments for the ``QListWidgetItem`` superclass.
    **kwargs : dict
        Keyword arguments for the ``QListWidgetItem`` superclass.

    Attributes
    ----------
    rod : RodNumberWidget
        A copy of the rod whose position was changed, prior to the change.
    action : str
        Description of what kind of action was performed.
        (Default is "Deleted rod")
    coupled_action : Union[Action, ChangeRodNumberAction, None]
        The instance of an :class:`Action` that is performed at the same time
        with this and must be reverted as well, if this :class:`Action` is
        reverted.

    """

    def __init__(
        self,
        old_rod: rn.RodNumberWidget,
        coupled_action: Union[Action, ChangedRodNumberAction] = None,
        *args,
        **kwargs,
    ):
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

    def undo(self, rods: List[rn.RodNumberWidget] = None):
        """Triggers events to revert this action.

        Parameters
        ----------
        rods : List[RodNumberWidget]
            A list of :class:`RodNumberWidget` in which should be the
            originally changed rod(s).

        Returns
        -------
        List[RodNumberWidget]
        """
        if self.coupled_action:
            self.rod.rod_id = self.coupled_action.new_id
        self.rod.setText(str(self.rod.rod_id))
        self.rod.rod_state = rn.RodState.NORMAL
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
            "color": self.rod.color,
        }
        if self.revert:
            # If the action was reverted
            out["position"] = self.rod.rod_points
            out["seen"] = self.rod.seen
        else:
            # If the action was performed
            out["position"] = 4 * [np.nan]
            out["seen"] = not self.rod.seen
        return out

    def invert(self):
        """Generates an inverted version of the :class:`DeleteRodAction` (for
        redoing).

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
    new_postion : List[int]
        The newly set starting and ending points of the rod, i.e. [x1, y1,
        x2, y2].
    *args : iterable
        Positional arguments for the ``QListWidgetItem`` superclass.
    **kwargs : dict
        Keyword arguments for the ``QListWidgetItem`` superclass.

    Attributes
    ----------
    rod : RodNumberWidget
        A copy of the rod whose position was changed, prior to the change.
    new_pos : List[int]
        The newly set starting and ending points of the rod.
    action : str
        Default is "Rod position updated".
    """

    def __init__(
        self,
        old_rod: rn.RodNumberWidget,
        new_position: List[int],
        *args,
        **kwargs,
    ):
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

        to_str = (
            f") #{self.rod.rod_id} {self.action}: {initial_pos} ---"
            f"> {end_pos}"
        )
        if self.rod is not None:
            to_str = f"{self.rod.color}" + to_str
        if self.frame is not None:
            to_str = f"{self.frame}, " + to_str
        if self._parent_id is not None:
            to_str = f"{self._parent_id}, " + to_str
        to_str = "(" + to_str
        return to_str

    def undo(
        self, rods: List[rn.RodNumberWidget] = None
    ) -> List[rn.RodNumberWidget]:
        """Triggers events to revert this action.

        Parameters
        ----------
        rods : List[RodNumberWidget]
            A list of :class:`RodNumberWidget` in which should be the
            originally changed rod(s).

        Returns
        -------
        List[RodNumberWidget]

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
            "color": self.rod.color,
            "seen": self.rod.seen,
        }
        if self.revert:
            # If the action was reverted
            out["position"] = self.rod.rod_points
        else:
            # If the action was performed
            out["position"] = self.new_pos
        return out

    def invert(self):
        """Generates an inverted version of the
        :class:`ChangeRodPositionAction` (for redoing).

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
        Positional arguments for the ``QListWidgetItem`` superclass.
    **kwargs : dict
        Keyword arguments for the ``QListWidgetItem`` superclass.

    Attributes
    ----------
    rod : RodNumberWidget
        A copy of the rod which was created.
    action : str
        Default is "Created new rod".
    """

    def __init__(
        self,
        new_rod: rn.RodNumberWidget,
        coupled_action: Union[Action, ChangedRodNumberAction] = None,
        *args,
        **kwargs,
    ):
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

    def undo(
        self, rods: List[rn.RodNumberWidget] = None
    ) -> List[rn.RodNumberWidget]:
        """Triggers events to revert this action.

        Parameters
        ----------
        rods : List[RodNumberWidget]
            A list of :class:`RodNumberWidget` in which should be the created
            rod.

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
            "color": self.rod.color,
        }
        if self.revert:
            # If the action was reverted
            out["position"] = [0, 0, 0, 0]
            out["seen"] = False
        else:
            # If the action was performed
            out["position"] = self.rod.rod_points
            out["seen"] = True
        return out

    def invert(self):
        """Generates an inverted version of the :class:`CreateRodAction` (for
        redoing).

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


class PermanentRemoveAction(Action):
    """Action to describe permanent deletion of a rod from a dataset.

    Parameters
    ----------
    rod_quantity : int
        Number of rods (rows) have been deleted.
    *args : iterable
        Positional arguments for the ``QListWidgetItem`` superclass.
    **kwargs : dict
        Keyword arguments for the ``QListWidgetItem`` superclass.
    """

    def __init__(self, rod_quantity: int, *args, **kwargs):
        self.quantity = rod_quantity
        self.action = "Permanently deleted {:d} unused rods"
        super().__init__(str(self), *args, **kwargs)

    def __str__(self):
        to_str = self.action.format(self.quantity)
        return to_str

    def undo(self, rods: Optional[Iterable[rn.RodNumberWidget]]):
        # TODO: implement
        pass


class PruneLength(Action):
    """Class to represent the pruning of a rods length as a loggable action.

    Parameters
    ----------
    old_rod : RodNumberWidget
        A copy of the rod whose position was changed, prior to the change.
    new_postion : List[int]
        The newly set starting and ending points of the rod, i.e. [x1, y1,
        x2, y2].
    *args : iterable
        Positional arguments for the ``QListWidgetItem`` superclass.
    **kwargs : dict
        Keyword arguments for the ``QListWidgetItem`` superclass.

    Attributes
    ----------
    rod : RodNumberWidget
        A copy of the rod whose position was changed, prior to the change.
    new_pos : [int]
        The newly set starting and ending points of the rod.
    action : str
        Default is "Rod length pruned: ".
    """

    def __init__(
        self,
        old_rods: Union[rn.RodNumberWidget, List[rn.RodNumberWidget]],
        new_positions: List[List[int]],
        adjustment: float,
        *args,
        **kwargs,
    ):
        self.rods = old_rods
        self.new_pos = new_positions
        self.adjustment = adjustment
        super().__init__(str(self), *args, **kwargs)

    def __str__(self):
        to_str = ") "
        if len(self.rods) > 1:
            to_str += f"All rod lengths adjusted by: {self.adjustment}"
        else:
            to_str += (
                f"#{self.rods[0].rod_id} length adjusted "
                f"by: {self.adjustment}"
            )

        if self.rods is not None:
            to_str = f"{self.rods[0].color}" + to_str
        if self.frame is not None:
            to_str = f"{self.frame}, " + to_str
        if self._parent_id is not None:
            to_str = f"{self._parent_id}, " + to_str
        to_str = "(" + to_str
        return to_str

    def undo(
        self, rods: List[rn.RodNumberWidget] = None
    ) -> List[rn.RodNumberWidget]:
        """Triggers events to revert this action.

        Parameters
        ----------
        rods : List[RodNumberWidget]
            A list of :class:`.RodNumberWidget` in which should be the
            originally changed rod(s).

        Returns
        -------
        List[RodNumberWidget]

        Raises
        ------
        Exception
        """
        if rods is None:
            raise Exception("Unable to undo action. No rods supplied.")

        for rod in rods:
            for rod_s in self.rods:
                if rod.rod_id == rod_s.rod_id:
                    rod.rod_points = self.rod.rod_points
                    break
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
            "rod_id": [rod.rod_id for rod in self.rods],
            "cam_id": [self.parent_id] * len(self.rods),
            "frame": [self.frame] * len(self.rods),
            "color": [rod.color for rod in self.rods],
            "seen": [rod.seen for rod in self.rods],
        }
        if self.revert:
            # If the action was reverted
            out["position"] = [rod.rod_points for rod in self.rods]
        else:
            # If the action was performed
            out["position"] = [pos for pos in self.new_pos]
        return out

    def invert(self):
        """Generates an inverted version of this action(for redoing).

        Returns
        -------
        PruneLength
        """
        inverted_rods = []
        inverted_pos = []
        for rod, pos in zip(self.rods, self.new_pos):
            inv_rod = rod.copy()
            inv_rod.rod_points = pos
            inverted_rods.append(inv_rod)
            inverted_pos = rod.rod_points
        inverted = ChangeRodPositionAction(inverted_rods, inverted_pos)
        inverted.parent_id = self.parent_id
        inverted.frame = self.frame
        return inverted


class NumberExchange(Action):
    color: str = None

    def __init__(
        self,
        mode: NumberChangeActions,
        previous_id: int,
        new_id: int,
        color: str,
        frame: int,
        cam_id: str = None,
    ):
        self.mode = mode
        self.previous_id = previous_id
        self.new_id = new_id
        self.cam_id = cam_id
        self.color = color
        super().__init__(str(self))
        self.frame = frame

    def undo(self, rods: List[rn.RodNumberWidget]):
        # TODO
        pass
        # return rods

    def __str__(self):
        to_str = (
            f") Changed rod #{self.previous_id} ---> #{self.new_id} "
            f"of color {self.color}"
        )
        if self.mode == NumberChangeActions.ALL:
            to_str += f" in frames >= {self.frame} and cameras."
        elif self.mode == NumberChangeActions.ALL_ONE_CAM:
            to_str += f" in frames >= {self.frame} of {self.cam_id}."
        elif self.mode == NumberChangeActions.ONE_BOTH_CAMS:
            to_str += f" in frame {self.frame} of all cameras."
        elif self.mode == NumberChangeActions.CURRENT:
            raise NotImplementedError()

        if self.color is not None:
            to_str = f"{self.color}" + to_str
        if self.frame is not None:
            to_str = f"{self.frame}, " + to_str
        if self._parent_id is not None:
            to_str = f"{self._parent_id}, " + to_str
        to_str = "(" + to_str
        return to_str

    def to_save(self):
        """The operation is already 'saved' as it directly modifies the main
        dataframe."""
        return None

    def invert(self):
        """Generates an inverted version of this action(for redoing).

        Returns
        -------
        NumberExchange
        """
        return NumberExchange(
            self.mode,
            self.new_id,
            self.previous_id,
            self.color,
            self.frame,
            self.cam_id,
        )


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
        self.logged_actions: List[Action] = []
        self.unsaved_changes = []
        self.repeatable_changes: List[Action] = []

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
        try:
            inv_undo_item = undo_item.invert()
        except NotInvertableError:
            # Action cannot be reversed
            self.logged_actions.append(undo_item)
            return
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
