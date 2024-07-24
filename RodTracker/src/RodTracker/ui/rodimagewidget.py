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

"""**TBD**"""

import logging
import math
from typing import List, Union

import matplotlib as mpl
import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QInputDialog, QLabel

import RodTracker.backend.logger as lg
import RodTracker.ui.rodnumberwidget as rn
from RodTracker.ui import dialogs

_logger = logging.getLogger(__name__)
_colors = mpl.colormaps["tab10"].colors


class RodImageWidget(QLabel):
    """A custom ``QLabel`` that displays an image and can overlay rods.

    Parameters
    ----------
    *args : iterable
        Positional arguments for the ``QLabel`` superclass.
    **kwargs : dict
        Keyword arguments for the ``QLabel`` superclass.


    .. admonition:: Signals

        - :attr:`loaded_rods`
        - :attr:`normal_frame_change`
        - :attr:`notify_undone`
        - :attr:`number_switches`
        - :attr:`request_color_change`
        - :attr:`request_frame_change`

    .. admonition:: Slots

        - :meth:`adjust_rod_length`
        - :meth:`delete_rod`
        - :meth:`extract_rods`
        - :meth:`undo_action`
        - :meth:`update_settings`

    Attributes
    ----------
    base_pixmap : QPixmap
        A *clean* image in the correct scaled size.
    rod_pixmap : QPixmap
        Image that is temporarily painted on when rod corrections are put in
        by the user.
    startPos : QtCore.QPoint
        Start position for new rod position.
    """

    request_color_change = QtCore.pyqtSignal(str, name="request_color_change")
    """pyqtSignal(str): Request to change the displayed colors.

    Currently this is used to revert actions performed on a color other than
    the displayed one.
    """

    request_frame_change = QtCore.pyqtSignal(int, name="request_frame_change")
    """pyqtSignal(int) : Request to change the displayed frames.

    Currently this is used to revert actions performed on a frame other than
    the displayed one.
    """

    notify_undone = QtCore.pyqtSignal(lg.Action, name="notify_undone")
    """pyqtSignal(Action) : Notifies objects, that the :class:`.Action` in the
    payload has been reverted.
    """

    normal_frame_change = QtCore.pyqtSignal(int, name="normal_frame_change")
    """pyqtSignal(int) : Requests a normal change of frame.

    The payload is the index of the desired frame, relative to the current one,
    e.g. ``-1`` to request the previous image.
    """

    number_switches = QtCore.pyqtSignal(
        [lg.NumberChangeActions, int, int, str],
        [lg.NumberChangeActions, int, int, str, str, int],
        name="number_switches",
    )
    """pyqtSignal : Indicates switches of numbers between rods.

    - **[NumberChangeActions, int, int, str]**:\n
      Notifies data maintainance objects, that the user attempts to change
      rod IDs in more than just the frame displayed by this
      :class:`RodImageWidget`.\n
      Payload: type of the attempted change, previous rod ID, new rod ID, and
      camera ID

    - **[NumberChangeActions, int, int, str, str, int]**:\n
      The second version of this signal will be obsolete.\n
      Payload: type of the attempted change, previous rod ID, new rod ID,
      camera ID, rod color, and frame
    """

    loaded_rods = QtCore.pyqtSignal(int, name="loaded_rods")
    """pyqtSignal(int) : Notifies objects, how many rods have just been loaded
    for display.
    """

    autoselect: bool = True

    rods: List[rn.RodNumberWidget]
    _logger: lg.ActionLogger = None
    _current_color: str = "unknown"
    # Settings
    _rod_thickness = 3
    _number_offset = 15
    _position_scaling = 10.0
    _rod_incr = 1.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Custom properties
        self.startPos = None
        self._image = None
        # Image that is temporarily painted on when rod corrections are input
        self.rod_pixmap = None
        # "clean" image in correct scaling
        self.base_pixmap = None
        self._rods = None
        self._scale_factor = 1.0
        self._offset = [0, 0]
        self._cam_id = "unknown"

    # Access to properties ====================================================
    @property
    def rods(self) -> List[rn.RodNumberWidget]:
        """
        Property that hold :class:`.RodNumberWidget` representing rods that are
        displayable on the Widget.

        Returns
        -------
        List[RodNumberWidget]
        """
        return self._rods

    @rods.setter
    def rods(self, new_edits: List[rn.RodNumberWidget]):
        # Delete previous rods
        del self.rods
        # Save and connect new rods
        self._rods = new_edits
        for rod in self._rods:
            self._connect_rod(rod)
        self._scale_image()

    @rods.deleter
    def rods(self):
        if self._rods is None:
            return
        for rod in self._rods:
            rod.deleteLater()
        self._rods = None

    @property
    def scale_factor(self) -> float:
        """
        Property that holds the scaling factor by which the original image
        is scaled when displayed.

        Returns
        -------
        float
        """
        return self._scale_factor

    @scale_factor.setter
    def scale_factor(self, factor: float):
        if factor <= 0:
            raise ValueError("factor must be >0")
        self._scale_factor = factor
        self._scale_image()

    @QtCore.pyqtSlot(QtGui.QImage)
    def image(self, new_image: QtGui.QImage):
        """Show a new image in this widget.

        Parameters
        ----------
        new_image : QImage

        Raises
        ------
        ValueError
            If the image is Null.
        """
        if new_image.isNull():
            raise ValueError("Assigned image cannot be 'Null'.")
        self._image = new_image
        self.base_pixmap = QtGui.QPixmap.fromImage(new_image)
        self._scale_image()

    @property
    def logger(self) -> lg.ActionLogger:
        """
        Property that holds a logger object keeping track of users' actions
        performed on this widget and its contents.

        Returns
        -------
        ActionLogger
        """
        return self._logger

    @logger.setter
    def logger(self, new_logger: lg.ActionLogger):
        if self._logger:
            self._logger.undo_action.disconnect()
        self._logger = new_logger
        self._logger.undo_action.connect(self.undo_action)

    @property
    def cam_id(self) -> str:
        """
        Property that holds a string used as and ID for logging and data
        selection.

        It must be human readable as it is used for labelling the performed
        actions displayed in the GUI.

        Returns
        -------
        str
        """
        return self._cam_id

    @cam_id.setter
    def cam_id(self, cam_id: str):
        self._cam_id = cam_id
        try:
            self._logger.parent_id = cam_id
        except AttributeError:
            raise AttributeError(
                "There is no ActionLogger set for this " "Widget yet."
            )

    @property
    def active_rod(self):
        """Property that returns the currently activated rod, if applicable.

        Returns
        -------
        int | None
        """
        if not self._rods:
            return None
        for rod in self._rods:
            if rod.rod_state == rn.RodState.SELECTED:
                return rod.rod_id
        return None

    def frame(self, frame: int):
        """Set the frame number information about the displayed image.

        Parameters
        ----------
        frame : int
            Frame number that is associated with the currently displayed image.
        """
        if self._logger is not None:
            self._logger.frame = frame

    def set_autoselect(self, state: bool):
        """En-/Disable autoselection of rods based on the mouse distance.

        Parameters
        ----------
        state : bool
            New state of the autoselection.
        """
        self.autoselect = state

    # Display manipulation ====================================================
    def _scale_image(self) -> None:
        if self._image is None:
            return
        old_pixmap = QtGui.QPixmap.fromImage(self._image)
        new_pixmap = old_pixmap.scaledToHeight(
            int(old_pixmap.height() * self._scale_factor),
            QtCore.Qt.SmoothTransformation,
        )
        self.setPixmap(new_pixmap)
        self.base_pixmap = new_pixmap

        # Handle the pixmap's shift to the center of the widget, in cases
        #  the surrounding scrollArea is larger than the pixmap
        x_off = (self.width() - self.base_pixmap.width()) // 2
        y_off = (self.height() - self.base_pixmap.height()) // 2
        self._offset = [x_off if x_off > 0 else 0, y_off if y_off > 0 else 0]

        # Update rod and number display
        self.draw_rods()

    def draw_rods(self) -> Union[QtGui.QPixmap, None]:
        """Updates the visual display of overlayed rods in the widget.

        Updates the visual appearance of all rods that are overlaying the
        original image. It specifically handles the different visual states
        a rod can be assigned.

        Returns
        -------
        Union[QPixmap, None]
        """
        if self._rods is None:
            # No rods available that might need redrawing
            return
        rod_pixmap = QtGui.QPixmap(self.base_pixmap)
        painter = QtGui.QPainter(rod_pixmap)
        for rod in self._rods:
            rod_pos = self.adjust_rod_position(rod)
            # Gets the display style from the rod number widget.
            try:
                pen = rod.pen
            except rn.RodStateError:
                dialogs.show_warning(
                    "A rod with unknown state was " "encountered!"
                )
                pen = None
            if pen is None:
                continue
            painter.setPen(pen)
            painter.drawLine(*rod_pos)

        painter.end()
        self.setPixmap(rod_pixmap)
        return rod_pixmap

    def clear_screen(self) -> None:
        """Removes the displayed rods and deletes them.

        Returns
        -------
        None
        """
        del self.rods
        self._scale_image()

    def scale_to_size(self, new_size: QtCore.QSize):
        """Scales the image to a specified size.

        Scales the image to a specified size, while retaining the image's
        aspect ratio.

        Parameters
        ----------
        new_size : QSize

        Returns
        -------
        None
        """
        if self._image is None:
            return
        old_pixmap = QtGui.QPixmap.fromImage(self._image)
        height_ratio = new_size.height() / old_pixmap.height()
        width_ratio = new_size.width() / old_pixmap.width()
        if height_ratio > width_ratio:
            # Use width
            self.scale_factor = width_ratio
            return
        else:
            # Use height
            self.scale_factor = height_ratio
            return

    # Interaction callbacks ===================================================
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Reimplements ``QLabel.mousePressEvent(event)``.

        Handles the beginning and ending actions for rod corrections by the
        user.

        Parameters
        ----------
        event : QMouseEvent

        Returns
        -------
        None
        """
        if self._rods is not None and self._current_color != "":
            if self.startPos is None:
                # Check rod states for number editing mode
                for rod in self._rods:
                    if not rod.isReadOnly():
                        # Rod is in number editing mode
                        if event.button() == QtCore.Qt.LeftButton:
                            # Confirm changes and check for conflicts
                            last_id = rod.rod_id
                            rod.rod_id = int(rod.text())
                            self.check_rod_conflicts(rod, last_id)
                        elif event.button() == QtCore.Qt.RightButton:
                            # Abort editing and restore previous number
                            rod.setText(str(rod.rod_id))
                            rod.deactivate_rod()
                            self.draw_rods()
                            self.rod_pixmap = None
                        return

                if (
                    event.button() == QtCore.Qt.RightButton
                    and self._rods is not None
                ):
                    # Deactivate any active rods
                    self.rod_activated(-1)
                elif event.button() == QtCore.Qt.LeftButton:
                    # Start rod correction
                    self.startPos = self.subtract_offset(
                        event.pos(), self._offset
                    )
                    for rod in self._rods:
                        if rod.rod_state == rn.RodState.SELECTED:
                            rod.rod_state = rn.RodState.EDITING
                    self.rod_pixmap = self.draw_rods()
            else:
                if event.button() == QtCore.Qt.RightButton:
                    # Abort current line drawing
                    self.startPos = None
                    for rod in self._rods:
                        if rod.rod_state == rn.RodState.EDITING:
                            rod.rod_state = rn.RodState.SELECTED
                    self.draw_rods()
                    self.rod_pixmap = None
                else:
                    # Finish line and save it
                    self.save_line(
                        self.startPos,
                        self.subtract_offset(event.pos(), self._offset),
                    )
                    self.startPos = None
                    self.draw_rods()
                    self.rod_pixmap = None

    def mouseMoveEvent(self, mouse_event: QtGui.QMouseEvent) -> None:
        """Reimplements ``QLabel.mouseMoveEvent(event)``.

        Handles the drawing and updating of a *draft* rod during start and end
        point selection.

        Parameters
        ----------
        mouse_event : QMouseEvent

        Returns
        -------
        None
        """
        # Draw intermediate rod position between clicks
        if self.startPos is not None:
            end = self.subtract_offset(mouse_event.pos(), self._offset)
            pixmap = QtGui.QPixmap(self.rod_pixmap)
            qp = QtGui.QPainter(pixmap)
            pen = QtGui.QPen(QtCore.Qt.white, self._rod_thickness)
            qp.setPen(pen)
            qp.drawLine(self.startPos, end)
            qp.end()
            self.setPixmap(pixmap)
        elif self.rods is not None and self.autoselect:
            # activate rod that is closes to the cursor
            mouse_pos = np.array(
                [mouse_event.pos().x(), mouse_event.pos().y()]
            )
            closest_rod = None
            min_dist = np.inf
            for rod in self.rods:
                # distance 0: distance from center
                # distance = np.linalg.norm(rod.rod_center - mouse_pos)

                # distance 1: use closest endpoint
                points = np.asarray(
                    [
                        self._position_scaling * self._scale_factor * coord
                        for coord in rod.rod_points
                    ]
                )
                dist_p1 = np.linalg.norm(
                    points[0:2] + np.array(self._offset) - mouse_pos
                )
                dist_p2 = np.linalg.norm(
                    points[2:] + np.array(self._offset) - mouse_pos
                )
                distance = np.min([dist_p1, dist_p2])

                # distance 2: min distance to the whole line segment
                # points = np.asarray([
                #     self._position_scaling * self._scale_factor * coord
                #     for coord in rod.rod_points])
                # p1 = points[0:2] + np.array(self._offset)
                # p2 = points[2:] + np.array(self._offset)
                # distance = _line_segment_distance(p1, p2, mouse_pos)

                if distance < min_dist:
                    min_dist = distance
                    closest_rod = rod
            self.rod_activated(closest_rod.rod_id)

    def save_line(self, start: QtCore.QPoint, end: QtCore.QPoint):
        """Saves a line selected by the user to be a rod with a rod number.

        The user's selected start and end point are saved in a
        :class:`.RodNumberWidget`. Either in one that was activated prior to
        the point selection, or that is selected by the user post point
        selection as part of this function.

        Parameters
        ----------
        start : QPoint
        end : QPoint

        Returns
        -------
        None
        """
        send_rod = None
        for rod in self._rods:
            if rod.rod_state == rn.RodState.EDITING:
                new_position = [start.x(), start.y(), end.x(), end.y()]
                new_position = [
                    coord / self._position_scaling / self._scale_factor
                    for coord in new_position
                ]
                rod.seen = True
                this_action = lg.ChangeRodPositionAction(
                    rod.copy(), new_position
                )
                self._logger.add_action(this_action)
                rod.rod_points = new_position
                rod.rod_state = rn.RodState.SELECTED
                send_rod = rod
                break

        if send_rod is None:
            # Find out which rods are unseen
            rods_unseen = []
            for rod in self._rods:
                if not rod.seen:
                    rods_unseen.append(rod.rod_id)
            rods_unseen.sort()

            # Get intended rod number from user
            if rods_unseen:
                dialog_rodnum = (
                    f"Unseen rods: {rods_unseen}\n" f"Enter rod number:"
                )
                selected_rod, ok = QInputDialog.getInt(
                    self,
                    "Choose a rod to replace",
                    dialog_rodnum,
                    value=rods_unseen[0],
                    min=0,
                    max=99,
                )
            else:
                dialog_rodnum = "No unseen rods. Enter rod number: "
                selected_rod, ok = QInputDialog.getInt(
                    self,
                    "Choose a rod to replace",
                    dialog_rodnum,
                    min=0,
                    max=99,
                )

            if not ok:
                return
            # Check whether the rod already exists
            rod_exists = False
            for rod in self._rods:
                if rod.rod_id == selected_rod:
                    # Overwrite previous position
                    rod_exists = True
                    rod.rod_id = selected_rod
                    new_position = [start.x(), start.y(), end.x(), end.y()]
                    new_position = [
                        coord / self._position_scaling / self._scale_factor
                        for coord in new_position
                    ]
                    # Mark rod as "seen", before logging!
                    rod.seen = True
                    this_action = lg.ChangeRodPositionAction(
                        rod.copy(), new_position
                    )
                    self._logger.add_action(this_action)
                    rod.rod_points = new_position
                    rod.rod_state = rn.RodState.SELECTED
                    break
            if not rod_exists:
                # Rod didn't exists -> create new RodNumber
                corrected_pos = [
                    start.x() / self._position_scaling / self._scale_factor,
                    start.y() / self._position_scaling / self._scale_factor,
                    end.x() / self._position_scaling / self._scale_factor,
                    end.y() / self._position_scaling / self._scale_factor,
                ]
                self.create_rod(selected_rod, corrected_pos)

    # Rod Handling ============================================================
    def rod_activated(self, rod_id: int) -> None:
        """Changes the rod state of the one given to active.

        The rod state of the rod, which ID is given to active and
        deactivates all other rods maintained by this widget.

        Parameters
        ----------
        rod_id : int
            ID of the rod that shall be activated.

        Returns
        -------
        None
        """
        # A new rod was activated for position editing. Deactivate all others.
        for rod in self._rods:
            if rod.rod_id != rod_id:
                rod.deactivate_rod()
            if rod.rod_id == rod_id:
                rod.rod_state = rn.RodState.SELECTED
                rod.setFocus(QtCore.Qt.OtherFocusReason)
        self.draw_rods()

    def check_rod_conflicts(
        self, set_rod: rn.RodNumberWidget, last_id: int
    ) -> None:
        """Checks whether a new/changed rod has a number conflict with others.

        Checks whether a new/changed rod has an ID that conflicts with is
        already occupied by one/multiple other rods in this widget. The user is
        displayed multiple options for resolving these conflicts.

        Parameters
        ----------
        set_rod : RodNumberWidget
            The rod in its new (changed) state.
        last_id : int
            The rod's previous ID, i.e. directly prior to the change.

        Returns
        -------
        None


        .. hint::

            **Emits**:

                - :attr:`number_switches` [NumberChangeActions, int, int, str]
                - :attr:`number_switches` [NumberChangeActions, int, int, str,
                  int, str]
        """
        # Marks any rods that have the same number in RodStyle.CONFLICT
        conflicting = []
        for rod in self._rods:
            if rod.rod_id == set_rod.rod_id:
                conflicting.append(rod)
        if len(conflicting) > 1:
            for rod in conflicting:
                rod.rod_state = rn.RodState.CONFLICT
        self.draw_rods()
        if len(conflicting) > 1:
            msg = dialogs.ConflictDialog(last_id, set_rod.rod_id)
            msg.exec()
            if msg.clickedButton() == msg.btn_switch_all:
                self.number_switches.emit(
                    lg.NumberChangeActions.ALL,
                    last_id,
                    set_rod.rod_id,
                    self.cam_id,
                )
                self._logger.add_action(
                    lg.NumberExchange(
                        lg.NumberChangeActions.ALL,
                        last_id,
                        set_rod.rod_id,
                        set_rod.color,
                        self._logger.frame,
                        self.cam_id,
                    )
                )

            elif msg.clickedButton() == msg.btn_one_cam:
                self.number_switches.emit(
                    lg.NumberChangeActions.ALL_ONE_CAM,
                    last_id,
                    set_rod.rod_id,
                    self.cam_id,
                )
                self._logger.add_action(
                    lg.NumberExchange(
                        lg.NumberChangeActions.ALL_ONE_CAM,
                        last_id,
                        set_rod.rod_id,
                        set_rod.color,
                        self._logger.frame,
                        self.cam_id,
                    )
                )

            elif msg.clickedButton() == msg.btn_both_cams:
                self.number_switches.emit(
                    lg.NumberChangeActions.ONE_BOTH_CAMS,
                    last_id,
                    set_rod.rod_id,
                    self.cam_id,
                )
                self._logger.add_action(
                    lg.NumberExchange(
                        lg.NumberChangeActions.ONE_BOTH_CAMS,
                        last_id,
                        set_rod.rod_id,
                        set_rod.color,
                        self._logger.frame,
                        self.cam_id,
                    )
                )

            elif msg.clickedButton() == msg.btn_only_this:
                # Switch the rod numbers
                first_change = None
                second_change = None
                for rod in conflicting:
                    rod.rod_state = rn.RodState.CHANGED
                    if rod is not set_rod:
                        id_to_log = rod.rod_id
                        rod.setText(str(last_id))
                        rod.rod_id = last_id
                        first_change = self.catch_rodnumber_change(
                            rod, id_to_log
                        )
                    else:
                        second_change = self.catch_rodnumber_change(
                            rod, last_id
                        )
                first_change.coupled_action = second_change
                second_change.coupled_action = first_change

            elif msg.clickedButton() == msg.btn_cancel:
                # Return to previous state
                if last_id == -1:
                    set_rod.deleteLater()
                    self._rods.remove(set_rod)
                else:
                    set_rod.setText(str(last_id))
                    set_rod.rod_id = last_id
                for rod in conflicting:
                    rod.rod_state = rn.RodState.CHANGED
            self.draw_rods()
        else:
            if set_rod.rod_id == last_id:
                return
            # No conflicts, inform logger
            if self._logger is None:
                raise Exception("Logger not set.")
            new_id = set_rod.rod_id
            set_rod.rod_id = last_id
            self.create_rod(new_id, set_rod.rod_points)
            self.delete_rod(set_rod)

    def catch_rodnumber_change(
        self, new_rod: rn.RodNumberWidget, last_id: int
    ) -> lg.ChangedRodNumberAction:
        """Handles the number/ID change of rods for logging.

        Constructs an Action for a number/ID change of a rod that can be
        used for logging with an ActionLogger.

        Parameters
        ----------
        new_rod : RodNumberWidget
            The rod in its new (changed) state.
        last_id : int
            The rod's previous ID, i.e. directly prior to the change.

        Returns
        -------
        ChangedRodNumberAction
        """
        old_rod = new_rod.copy()
        old_rod.setEnabled(False)
        old_rod.setVisible(False)
        old_rod.rod_id = last_id
        new_id = new_rod.rod_id
        action = lg.ChangedRodNumberAction(old_rod, new_id)
        self._logger.add_action(action)
        return action

    def check_exchange(self, drop_position):
        """Evaluates, whether a position is on top of a
        :class:`.RodNumberWidget`.

        Evaluates, whether a position is on top of a :class:`.RodNumberWidget`
        maintained by this object."""
        # TODO: check where rod number was dropped and whether an exchange
        #  is needed.
        pass

    @QtCore.pyqtSlot(lg.Action)
    def undo_action(
        self,
        action: Union[
            lg.Action,
            lg.ChangeRodPositionAction,
            lg.ChangedRodNumberAction,
            lg.DeleteRodAction,
        ],
    ):
        """Reverts an :class:`.Action` performed on a rod.

        Reverts the :class:`.Action` given this function, if it was constructed
        by the object. It can handle actions performed on a rod. This includes
        position changes, number changes and deletions. It returns without
        further actions, if the :class:`.Action` was not originally performed
        on this object or if it has is of an unknown type.

        Parameters
        ----------
        action : Union[Action, ChangeRodPositionAction, ChangedRodNumberAction,
                       DeleteRodAction]
            An :class:`.Action` that was logged previously. It will only be
            reverted, if it associated with this object.

        Returns
        -------
        None


        .. hint::

            **Emits**:

            - :attr:`request_frame_change`
            - :attr:`request_color_change`
            - :attr:`number_switches` [NumberChangeActions, int, int, str,
              str, int]
        """
        if action.parent_id != self._cam_id:
            return

        if action.frame != self.logger.frame:
            self.request_frame_change.emit(action.frame)

        try:
            action_color = action.rod.color
            if action_color != self._rods[0].color:
                self.request_color_change.emit(action_color)
        except AttributeError:
            # Given action does not require a color to be handled
            pass

        if isinstance(action, lg.ChangeRodPositionAction) or isinstance(
            action, lg.PruneLength
        ):
            new_rods = action.undo(rods=self._rods)
            self._rods = new_rods
            self.draw_rods()
        elif isinstance(action, lg.DeleteRodAction):
            if action.coupled_action is not None:
                self._logger.register_undone(action.coupled_action)
            current_rods = self._rods
            new_rods = []
            for rod in current_rods:
                if rod.rod_id != action.rod.rod_id:
                    new_rods.append(rod)
                else:
                    rod.deleteLater()
            if action.coupled_action:
                new_rods = action.coupled_action.undo(rods=new_rods)
            deleted_rod = action.undo(None)
            self._connect_rod(deleted_rod)
            new_rods.append(deleted_rod)
            self._rods = new_rods
            self.draw_rods()

        elif isinstance(action, lg.ChangedRodNumberAction):
            if action.coupled_action is not None:
                self._logger.register_undone(action.coupled_action)
            new_rods = action.undo(rods=self._rods)
            self._rods = new_rods
            self.draw_rods()

        elif isinstance(action, lg.CreateRodAction):
            new_rods = action.undo(rods=self._rods)
            if action.coupled_action is not None:
                # This should only get triggered when a
                #  RodNumberChangeAction that incorporates a RodDeletion gets
                #  redone, so a CreateRodAction+RodPositionChange.
                #  If this shall be extended to more combinations the line
                #  below must be uncommented and then the redo mechanism will
                #  break for the above mentioned occasion! So more work is
                #  required then.
                # self._logger.register_undone(action.coupled_action)
                new_rods = action.coupled_action.undo(rods=new_rods)
            self._rods = new_rods
            self.draw_rods()

        elif isinstance(action, lg.NumberExchange):
            self.number_switches[
                lg.NumberChangeActions, int, int, str, str, int
            ].emit(
                action.mode,
                action.new_id,
                action.previous_id,
                action.cam_id,
                action.color,
                action.frame,
            )

        else:
            # Cannot handle this action
            return

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        """
        Adjust rod positions after resizing of the widget happened,
        e.g. the slider was actuated or the image was scaled.

        Parameters
        ----------
        a0 : QResizeEvent

        Returns
        -------
        None
        """
        super().resizeEvent(a0)
        # Adjust rod positions after resizing of the widget happened,
        #  e.g. the slider was actuated or the image was scaled
        if self._rods is not None:
            # Calculate offset
            x_off = (a0.size().width() - self.base_pixmap.width()) // 2
            y_off = (a0.size().height() - self.base_pixmap.height()) // 2
            x_off = x_off if x_off > 0 else 0
            y_off = y_off if y_off > 0 else 0
            self._offset = [x_off, y_off]

            # Complete version
            for rod in self._rods:
                self.adjust_rod_position(rod)

    @QtCore.pyqtSlot(float, bool)
    def adjust_rod_length(
        self, amount: float = 1.0, only_selected: bool = True
    ):
        """Adjusts rod length(s) by a given amount in px.

        Adds the length (in px) given in ``amount`` to the active rod or all
        rods. Negative values shorten the rod(s).

        Parameters
        ----------
        amount : float, optional
            Amount in px by which the lenght will be adjusted.
            By default ``1``.
        only_selected : bool, optional
            Whether to only adjust the currently active rod's length.
            By default ``True``.
        """
        rods = []
        new_pos = []
        previously_selected = None
        for rod in self._rods:
            if rod.rod_state == rn.RodState.SELECTED:
                previously_selected = rod.rod_id
            elif only_selected:
                continue

            n_p = np.asarray(rod.rod_points)
            rod_direction = np.array([n_p[0:2] - n_p[2:]])
            rod_direction = rod_direction / np.sqrt(np.sum(rod_direction**2))
            rod_direction = amount / 2 * rod_direction
            if np.isnan(rod_direction).any():
                rod_direction = np.array([0, 0])
            n_p += np.concatenate([rod_direction, -rod_direction]).flatten()
            n_p = list(n_p)
            rod.rod_points = n_p
            rods.append(rod.copy())
            new_pos.append(n_p)
        self._logger.add_action(lg.PruneLength(rods, new_pos, amount))
        self.draw_rods()
        self.rod_activated(previously_selected)
        return

    @staticmethod
    def subtract_offset(
        point: QtCore.QPoint, offset: List[int]
    ) -> QtCore.QPoint:
        """Subtracts a given offset from a point and returns the new point.

        Parameters
        ----------
        point : QPoint
        offset : List[int]

        Returns
        -------
        QPoint
        """
        new_x = point.x() - offset[0]
        new_y = point.y() - offset[1]
        return QtCore.QPoint(new_x, new_y)

    def adjust_rod_position(self, rod: rn.RodNumberWidget) -> List[int]:
        """Adjusts a rod number position to be on the right side of its rod.

        The position of the :class:`.RodNumberWidget` is adjusted, such that it
        is displayed to the right side and in the middle of its corresponding
        rod. This adjustment is mainly due to scaling of the image. It also
        returns the rods position in the image associated with the moved
        :class:`.RodNumberWidget`.

        Parameters
        ----------
        rod : RodNumberWidget

        Returns
        -------
        List[int]
        """
        rod_pos = rod.rod_points
        rod_pos = [
            int(self._position_scaling * self._scale_factor * coord)
            for coord in rod_pos
        ]
        rod.rod_center = (np.array(rod_pos[0:2]) + np.array(rod_pos[2:])) / 2
        rod.rod_center += np.array(self._offset)
        # Update rod number positions
        x = rod_pos[2] - rod_pos[0]
        y = rod_pos[3] - rod_pos[1]
        x_orthogonal = -y
        y_orthogonal = x
        if x_orthogonal < 0:
            # Change vector to always point to the right
            x_orthogonal = -x_orthogonal
            y_orthogonal = -y_orthogonal
        len_vec = math.sqrt(x_orthogonal**2 + y_orthogonal**2)
        try:
            pos_x = (
                rod_pos[0]
                + int(x_orthogonal / len_vec * self._number_offset)
                + int(x / 2)
            )
            pos_y = (
                rod_pos[1]
                + int(y_orthogonal / len_vec * self._number_offset)
                + int(y / 2)
            )
            # Account for the widget's dimensions
            pos_x -= rod.size().width() / 2
            pos_y -= rod.size().height() / 2

        except ZeroDivisionError:
            # Rod has length of 0
            pos_x = rod_pos[0] + self._number_offset
            pos_y = rod_pos[1] + self._number_offset

        pos_x += self._offset[0]
        pos_y += self._offset[1]

        rod.move(QtCore.QPoint(int(pos_x), int(pos_y)))
        return rod_pos

    @QtCore.pyqtSlot(rn.RodNumberWidget)
    def delete_rod(self, rod: rn.RodNumberWidget) -> None:
        """Deletes the given rod, thus sets its position to ``(-1, -1)``.

        Parameters
        ----------
        rod : RodNumberWidget

        Returns
        -------
        None
        """
        rod.setText(str(rod.rod_id))
        delete_action = lg.DeleteRodAction(rod.copy())
        rod.seen = False
        rod.rod_points = 4 * [-1]
        rod.rod_state = rn.RodState.CHANGED
        self._logger.add_action(delete_action)
        self.draw_rods()

    def _connect_rod(self, rod: rn.RodNumberWidget) -> None:
        """Connects all signals from the given rod with the widget's slots.

        Parameters
        ----------
        rod : RodNumberWidget

        Returns
        -------
        None
        """
        if self._current_color != "":
            # Rods should not be interactable if all are displayed,
            # indicated by _current_color == ""
            rod.activated.connect(self.rod_activated)
            rod.id_changed.connect(self.check_rod_conflicts)
            rod.request_delete.connect(self.delete_rod)
            rod.installEventFilter(self)
        rod.show()

    def eventFilter(
        self, source: QtCore.QObject, event: QtCore.QEvent
    ) -> bool:
        """Intercepts events, here ``QKeyEvents`` for frame switching and edit
        aborting.

        Parameters
        ----------
        source : QObject
        event : QEvent

        Returns
        -------
        bool
            ``True``, if the event shall not be propagated further.
            ``False``, if the event shall be passed to the next object to be
            handled.


        .. hint::

            **Emits:**

                - :attr:`normal_frame_change`
        """

        if event.type() != QtCore.QEvent.KeyPress:
            return False
        event = QKeyEvent(event)
        if not isinstance(source, rn.RodNumberWidget):
            return False
        if source.isReadOnly():
            if event.key() == QtCore.Qt.Key_Escape:
                # Abort any editing (not rod number editing)
                if self._rods is not None:
                    # Deactivate any active rods
                    self.rod_activated(-1)
                    return True
            elif event.key() == QtCore.Qt.Key_Right:
                self.normal_frame_change.emit(1)
                return False
            elif event.key() == QtCore.Qt.Key_Left:
                self.normal_frame_change.emit(-1)
                return False
            elif event.key() == QtCore.Qt.Key_A:
                # Lengthen rod
                amount = self._rod_incr
            elif event.key() == QtCore.Qt.Key_S:
                # Shorten rod
                amount = -self._rod_incr
            elif event.key() == QtCore.Qt.Key.Key_Delete:
                # Delete the currently selected rod
                self.delete_rod(source)
                return True
            else:
                # RodNumberWidget is in the process of rod number changing,
                #  let the widget handle that itself
                return False

            if "amount" in locals():
                # Adjust rod length
                self.adjust_rod_length(amount)
                return True
        return False

    @QtCore.pyqtSlot(dict)
    def update_settings(self, settings: dict) -> None:
        """Catches updates of the settings from a :class:`.Settings` class.

        Checks for the keys relevant to itself and updates the corresponding
        attributes. Redraws itself with the new settings in place.

        Parameters
        ----------
        settings : dict

        Returns
        -------
        None
        """
        settings_changed = False
        if "rod_thickness" in settings:
            settings_changed = True
            self._rod_thickness = settings["rod_thickness"]
        if "number_offset" in settings:
            settings_changed = True
            self._number_offset = settings["number_offset"]
        if "position_scaling" in settings:
            settings_changed = True
            self._position_scaling = settings["position_scaling"]
        if "rod_increment" in settings:
            settings_changed = True
            self._rod_incr = settings["rod_increment"]

        if settings_changed:
            self.draw_rods()

    @QtCore.pyqtSlot(pd.DataFrame, str)
    def extract_rods(self, data: pd.DataFrame, color: str) -> None:
        """Extract rod positions for a color and create the
        :class:`.RodNumberWidget` (s).

        Extracts the rod position data one color in one frame from ``data``.
        It creates the :class:`.RodNumberWidget` that is associated with each
        rod. If a rod has been activated previously, it is attempted to
        activate a rod with the same number again.

        Parameters
        ----------
        data : DataFrame
            Data from which to extract the 2D rod positions relevant to this
            camera view. Required columns:
            ``"x1_{self.cam_id}"``, ``"x2_{self.cam_id}"``,
            ``"y1_{self.cam_id}"``, ``"y2_{self.cam_id}"``,
            ``"seen_{self.cam_id}"``, ``"particle"``, ``"frame"``
        color : str
            Color of the rods given in ``data``.

        Returns
        -------
        None


        .. hint::

            **Emits:**

                - :attr:`loaded_rods`
        """
        active_rod = self.active_rod
        col_list = [
            "particle",
            "frame",
            f"x1_{self.cam_id}",
            f"x2_{self.cam_id}",
            f"y1_{self.cam_id}",
            f"y2_{self.cam_id}",
            f"seen_{self.cam_id}",
            "color",
        ]
        try:
            data = data[col_list]
        except KeyError:
            _logger.info(
                f"Couldn't extract rods. Didn't find all necessary columns: "
                f"{col_list}"
            )
            del self.rods
            return
        self._current_color = color
        new_rods = []
        cleaned = data.fillna(-1)

        # TODO: handle when more rod colors present than in colormap
        colors_present = cleaned["color"].unique()

        for _, rod in cleaned.iterrows():
            x1 = rod[f"x1_{self.cam_id}"]
            x2 = rod[f"x2_{self.cam_id}"]
            y1 = rod[f"y1_{self.cam_id}"]
            y2 = rod[f"y2_{self.cam_id}"]
            seen = bool(rod[f"seen_{self.cam_id}"])
            no = int(rod["particle"])
            rod_color = rod["color"]

            # Add rods
            ident = rn.RodNumberWidget(
                rod_color, self, str(no), QtCore.QPoint(0, 0)
            )
            ident.rod_id = no
            ident.rod_points = [x1, y1, x2, y2]
            ident.setObjectName(f"rn_{no}_{rod_color}")
            ident.seen = seen
            if len(colors_present) > 1:
                try:
                    rgb_color = QtGui.QColor.fromRgbF(
                        *mpl.colors.to_rgba(rod_color, alpha=1.0)
                    ).getRgb()[:-1]
                except ValueError as e:
                    _logger.warning(
                        f"Unknown color for 2D display!\n{e.args}\n"
                        f"Using a different color instead."
                    )
                    color_idx = np.where(colors_present == rod_color)[0][0]
                    rgb_color = QtGui.QColor.fromRgbF(
                        *_colors[color_idx]
                    ).getRgb()[:-1]
                ident._rod_color = rgb_color
                # Rods should not be interactable if all are displayed
                ident.setDisabled(True)
            new_rods.append(ident)
        self.rods = new_rods
        if active_rod is not None:
            self.rod_activated(active_rod)
        self.loaded_rods.emit(len(new_rods))

    def create_rod(self, number: int, new_position: list):
        """Create a new rod, display it and log this action.

        Parameters
        ----------
        number : int
        new_position : list
            Positon coordinates: [x1, y1, x2, y2]
        """
        new_rod = rn.RodNumberWidget(self._current_color, self, str(number))
        new_rod.rod_id = number
        new_rod.setObjectName(f"rn_{number}")
        new_rod.rod_points = new_position
        new_rod.rod_state = rn.RodState.SELECTED
        # Newly created rods are always "seen"
        new_rod.seen = True
        self._rods.append(new_rod)
        self._connect_rod(new_rod)
        self._scale_image()
        last_action = lg.CreateRodAction(new_rod.copy())
        self._logger.add_action(last_action)


def line_segment_distance(
    p1: np.ndarray, p2: np.ndarray, p: np.ndarray
) -> float:
    l2 = np.sum((p2 - p1) ** 2)  # |p2-p1|, without the root
    if l2 == 0.0:
        # line segment of length 0
        return np.linalg.norm(p1 - p)
    m = np.max([0.0, np.min([1.0, np.dot(p - p1, p2 - p1) / l2])])
    min_d_point = p1 + m * (p2 - p1)
    return float(np.linalg.norm(min_d_point - p))
