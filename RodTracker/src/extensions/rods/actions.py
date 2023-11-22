#  Copyright (c) 2023 Adrian Niemann Dmitry Puzyrev
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

"""**TBD**"""


from enum import Enum, auto
import logging
from typing import Optional, Iterable, Union, List

import numpy as np

from RodTracker.backend.logger import Action
from . import rods

_logger = logging.getLogger(__name__)


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
        old_rod: rods.RodNumber,
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

    def undo(self, rods: List[rods.RodNumber]) -> List[rods.RodNumber]:
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
        old_rod: rods.RodNumber,
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

    def undo(self, rods: List[rods.RodNumber] = None):
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
        self.rod.rod_state = rods.RodState.NORMAL
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
        old_rod: rods.RodNumber,
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

    def undo(self, rods: List[rods.RodNumber] = None) -> List[rods.RodNumber]:
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
        new_rod: rods.RodNumber,
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

    def undo(self, rods: List[rods.RodNumber] = None) -> List[rods.RodNumber]:
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

    def undo(self, rods: Optional[Iterable[rods.RodNumber]]):
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
        old_rods: Union[rods.RodNumber, List[rods.RodNumber]],
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

    def undo(self, rods: List[rods.RodNumber] = None) -> List[rods.RodNumber]:
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

    def undo(self, rods: List[rods.RodNumber]):
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
