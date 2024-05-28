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
import logging
import math
from typing import Any, List, Union

import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QInputDialog

import RodTracker.backend.logger as lg
import RodTracker.backend.settings as se
import RodTracker.ui.dialogs as dlg
from RodTracker.ui import tabs

from . import actions, dialogs, rods

_logger = logging.getLogger(__name__)


class RodImageTab(tabs.ImageInteractionTab):
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
        [actions.NumberChangeActions, int, int, str],
        [actions.NumberChangeActions, int, int, str, str, int],
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
    # autoselect: bool = True
    autoselect: bool = False

    _particles: List[rods.RodNumber] = None
    _current_color: str = "unknown"
    # TODO: update settings on start
    # Settings
    _rod_thickness: int = 3
    _number_offset: int = 15
    _position_scaling: float = 1.0
    _rod_incr: float = 1.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Custom properties
        self.startPos = None
        self._image = None
        # Image that is temporarily painted on when rod corrections are input
        self.rod_pixmap = None

        self._scale_factor = 1.0
        self._offset = [0, 0]

    # Access to properties ====================================================
    @property
    def particles(self) -> List[rods.RodNumber]:
        """
        Property that hold :class:`.RodNumberWidget` representing rods that are
        displayable on the Widget.

        Returns
        -------
        List[RodNumberWidget]
        """
        return self._particles

    @particles.setter
    def particles(self, new_edits: List[rods.RodNumber]):
        # Delete previous rods
        del self.particles
        # Save and connect new rods
        self._particles = new_edits
        for rod in self._particles:
            self._connect_rod(rod)
        self._scale_image()

    @particles.deleter
    def particles(self):
        if self._particles is None:
            return
        for rod in self._particles:
            rod.deleteLater()
        self._particles = None

    @property
    def active_rod(self):
        """Property that returns the currently activated rod, if applicable.

        Returns
        -------
        int | None
        """
        if not self._particles:
            return None
        for rod in self._particles:
            if rod.rod_state == rods.RodState.SELECTED:
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

    def activate(self):
        # TODO
        pass

    # Display manipulation ====================================================
    # @override
    def update_particle_display(self) -> Union[QtGui.QPixmap, None]:
        """Updates the visual display of overlayed rods in the widget.

        Updates the visual appearance of all rods that are overlaying the
        original image. It specifically handles the different visual states
        a rod can be assigned.

        Returns
        -------
        Union[QPixmap, None]
        """
        if self._particles is None:
            # No rods available that might need redrawing
            return
        rod_pixmap = QtGui.QPixmap(self._pixmap)
        painter = QtGui.QPainter(rod_pixmap)
        for rod in self._particles:
            rod_pos = self.adjust_rod_position(rod)
            # Gets the display style from the rod number widget.
            try:
                pen = rod.pen
            except rods.RodStateError:
                dlg.show_warning("A rod with unknown state was encountered!")
                pen = None
            if pen is None:
                continue
            painter.setPen(pen)
            painter.drawLine(*rod_pos)

        painter.end()
        self.setPixmap(rod_pixmap)
        return rod_pixmap

    # @override
    def clear_screen(self) -> None:
        """Removes the displayed rods and deletes them.

        Returns
        -------
        None
        """
        del self.particles
        self._scale_image()

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
        if self._particles is not None:
            if self.startPos is None:
                # Check rod states for number editing mode
                for rod in self._particles:
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
                            self.update_particle_display()
                            self.rod_pixmap = None
                        return

                if (
                    event.button() == QtCore.Qt.RightButton
                    and self._particles is not None
                ):
                    # Deactivate any active rods
                    self.rod_activated(-1)
                elif event.button() == QtCore.Qt.LeftButton:
                    # Start rod correction
                    self.startPos = self.subtract_offset(
                        event.pos(), self._offset
                    )
                    for rod in self._particles:
                        if rod.rod_state == rods.RodState.SELECTED:
                            rod.rod_state = rods.RodState.EDITING
                    self.rod_pixmap = self.update_particle_display()
            else:
                if event.button() == QtCore.Qt.RightButton:
                    # Abort current line drawing
                    self.startPos = None
                    for rod in self._particles:
                        if rod.rod_state == rods.RodState.EDITING:
                            rod.rod_state = rods.RodState.SELECTED
                    self.update_particle_display()
                    self.rod_pixmap = None
                else:
                    # Finish line and save it
                    self.save_line(
                        self.startPos,
                        self.subtract_offset(event.pos(), self._offset),
                    )
                    self.startPos = None
                    self.update_particle_display()
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
        elif self.particles is not None and self.autoselect:
            # activate rod that is closes to the cursor
            mouse_pos = np.array(
                [mouse_event.pos().x(), mouse_event.pos().y()]
            )
            closest_rod = None
            min_dist = np.inf
            for rod in self.particles:
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
            # FIXME: this breaks if no rods are loaded yet
            #        (mitigation is below)
            if not self._particles:
                return
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
        for rod in self._particles:
            if rod.rod_state == rods.RodState.EDITING:
                new_position = [start.x(), start.y(), end.x(), end.y()]
                new_position = [
                    coord / self._position_scaling / self._scale_factor
                    for coord in new_position
                ]
                rod.seen = True
                this_action = actions.ChangeRodPositionAction(
                    rod.copy(), new_position
                )
                self._logger.add_action(this_action)
                rod.rod_points = new_position
                rod.rod_state = rods.RodState.SELECTED
                send_rod = rod
                break

        if send_rod is None:
            # Find out which rods are unseen
            rods_unseen = []
            for rod in self._particles:
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
            for rod in self._particles:
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
                    this_action = actions.ChangeRodPositionAction(
                        rod.copy(), new_position
                    )
                    self._logger.add_action(this_action)
                    rod.rod_points = new_position
                    rod.rod_state = rods.RodState.SELECTED
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
        for rod in self._particles:
            if rod.rod_id != rod_id:
                rod.deactivate_rod()
            if rod.rod_id == rod_id:
                rod.rod_state = rods.RodState.SELECTED
                rod.setFocus(QtCore.Qt.OtherFocusReason)
        self.update_particle_display()

    def check_rod_conflicts(
        self, set_rod: rods.RodNumber, last_id: int
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
        conflicting: List[rods.RodNumber] = []
        for rod in self._particles:
            if rod.rod_id == set_rod.rod_id:
                conflicting.append(rod)
        if len(conflicting) > 1:
            for rod in conflicting:
                rod.rod_state = rods.RodState.CONFLICT
        self.update_particle_display()
        if len(conflicting) > 1:
            msg = dialogs.ConflictDialog(last_id, set_rod.rod_id)
            msg.exec()
            if msg.clickedButton() == msg.btn_switch_all:
                self.number_switches.emit(
                    actions.NumberChangeActions.ALL,
                    last_id,
                    set_rod.rod_id,
                    self.ID,
                )
                self._logger.add_action(
                    actions.NumberExchange(
                        actions.NumberChangeActions.ALL,
                        last_id,
                        set_rod.rod_id,
                        set_rod.color,
                        self._logger.frame,
                        self.ID,
                    )
                )

            elif msg.clickedButton() == msg.btn_one_cam:
                self.number_switches.emit(
                    actions.NumberChangeActions.ALL_ONE_CAM,
                    last_id,
                    set_rod.rod_id,
                    self.ID,
                )
                self._logger.add_action(
                    actions.NumberExchange(
                        actions.NumberChangeActions.ALL_ONE_CAM,
                        last_id,
                        set_rod.rod_id,
                        set_rod.color,
                        self._logger.frame,
                        self.ID,
                    )
                )

            elif msg.clickedButton() == msg.btn_both_cams:
                self.number_switches.emit(
                    actions.NumberChangeActions.ONE_BOTH_CAMS,
                    last_id,
                    set_rod.rod_id,
                    self.ID,
                )
                self._logger.add_action(
                    actions.NumberExchange(
                        actions.NumberChangeActions.ONE_BOTH_CAMS,
                        last_id,
                        set_rod.rod_id,
                        set_rod.color,
                        self._logger.frame,
                        self.ID,
                    )
                )

            elif msg.clickedButton() == msg.btn_only_this:
                # Switch the rod numbers
                first_change = None
                second_change = None
                for rod in conflicting:
                    rod.rod_state = rods.RodState.CHANGED
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
                    self._particles.remove(set_rod)
                else:
                    set_rod.setText(str(last_id))
                    set_rod.rod_id = last_id
                for rod in conflicting:
                    rod.rod_state = rods.RodState.CHANGED
            self.update_particle_display()
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
        self, new_rod: rods.RodNumber, last_id: int
    ) -> actions.ChangedRodNumberAction:
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
        action = actions.ChangedRodNumberAction(old_rod, new_id)
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

    # @override
    @QtCore.pyqtSlot(lg.Action)
    def undo_action(
        self,
        action: Union[
            lg.Action,
            actions.ChangeRodPositionAction,
            actions.ChangedRodNumberAction,
            actions.DeleteRodAction,
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
        if action.parent_id != self.ID:
            return

        if action.frame != self.logger.frame:
            self.request_frame_change.emit(action.frame)

        try:
            action_color = action.rod.color
            if action_color != self._particles[0].color:
                self.request_color_change.emit(action_color)
        except AttributeError:
            # Given action does not require a color to be handled
            pass

        if isinstance(action, actions.ChangeRodPositionAction) or isinstance(
            action, actions.PruneLength
        ):
            new_rods = action.undo(rods=self._particles)
            self._particles = new_rods
            self.update_particle_display()
        elif isinstance(action, actions.DeleteRodAction):
            if action.coupled_action is not None:
                self._logger.register_undone(action.coupled_action)
            current_rods = self._particles
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
            self._particles = new_rods
            self.update_particle_display()

        elif isinstance(action, actions.ChangedRodNumberAction):
            if action.coupled_action is not None:
                self._logger.register_undone(action.coupled_action)
            new_rods = action.undo(rods=self._particles)
            self._particles = new_rods
            self.update_particle_display()

        elif isinstance(action, actions.CreateRodAction):
            new_rods = action.undo(rods=self._particles)
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
            self._particles = new_rods
            self.update_particle_display()

        elif isinstance(action, actions.NumberExchange):
            self.number_switches[
                actions.NumberChangeActions, int, int, str, str, int
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
        if self._particles:
            # Calculate offset
            x_off = (a0.size().width() - self._pixmap.width()) // 2
            y_off = (a0.size().height() - self._pixmap.height()) // 2
            x_off = x_off if x_off > 0 else 0
            y_off = y_off if y_off > 0 else 0
            self._offset = [x_off, y_off]

            # Complete version
            for rod in self._particles:
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
        for rod in self._particles:
            if rod.rod_state == rods.RodState.SELECTED:
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
        self._logger.add_action(actions.PruneLength(rods, new_pos, amount))
        self.update_particle_display()
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

    def adjust_rod_position(self, rod: rods.RodNumber) -> List[int]:
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

    @QtCore.pyqtSlot(rods.RodNumber)
    def delete_rod(self, rod: rods.RodNumber) -> None:
        """Deletes the given rod, thus sets its position to ``(-1, -1)``.

        Parameters
        ----------
        rod : RodNumberWidget

        Returns
        -------
        None
        """
        rod.setText(str(rod.rod_id))
        delete_action = actions.DeleteRodAction(rod.copy())
        rod.seen = False
        rod.rod_points = 4 * [-1]
        rod.rod_state = rods.RodState.CHANGED
        self._logger.add_action(delete_action)
        self.update_particle_display()

    def _connect_rod(self, rod: rods.RodNumber) -> None:
        """Connects all signals from the given rod with the widget's slots.

        Parameters
        ----------
        rod : RodNumberWidget

        Returns
        -------
        None
        """
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
        if not isinstance(source, rods.RodNumber):
            return False
        if source.isReadOnly():
            if event.key() == QtCore.Qt.Key_Escape:
                # Abort any editing (not rod number editing)
                if self._particles is not None:
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

    @QtCore.pyqtSlot(str, object)
    def update_settings(self, key: str, new_value: Any) -> None:
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
        super().update_settings(key, new_value)
        settings_changed = False
        if "Rods.rod_thickness" == key:
            settings_changed = True
            self._rod_thickness = new_value
        elif "Rods.number_offset" == key:
            settings_changed = True
            self._number_offset = new_value
        elif "Rods.position_scaling" == key:
            settings_changed = True
            self._position_scaling = new_value
        elif "Rods.rod_increment" == key:
            settings_changed = True
            self._rod_incr = new_value

        if settings_changed:
            self.update_particle_display()

    @QtCore.pyqtSlot(pd.DataFrame)
    def extract_particles(
        self, data: pd.DataFrame, color: str = "blue"
    ) -> None:
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
        data_id = self.image_manager.ID
        col_list = [
            "particle",
            "frame",
            f"x1_{data_id}",
            f"x2_{data_id}",
            f"y1_{data_id}",
            f"y2_{data_id}",
            f"seen_{data_id}",
        ]
        try:
            data = data[col_list]
        except KeyError:
            _logger.info(
                f"Couldn't extract rods. Didn't find columns: " f"{col_list}"
            )
            del self.particles
            return

        self._current_color = color
        new_rods = []
        cleaned = data.fillna(-1)
        for _, rod in cleaned.iterrows():
            x1 = rod[f"x1_{data_id}"]
            x2 = rod[f"x2_{data_id}"]
            y1 = rod[f"y1_{data_id}"]
            y2 = rod[f"y2_{data_id}"]
            seen = bool(rod[f"seen_{data_id}"])
            no = int(rod["particle"])

            # Add rods
            ident = rods.RodNumber(color, self, str(no), QtCore.QPoint(0, 0))
            ident.rod_id = no
            ident.rod_points = [x1, y1, x2, y2]
            ident.setObjectName(f"rn_{no}")
            ident.seen = seen
            se.Settings().setting_signals.setting_changed.connect(
                ident.update_settings
            )
            new_rods.append(ident)
        self.particles = new_rods
        if active_rod is not None:
            self.rod_activated(active_rod)
        self.loaded_particles.emit(len(new_rods))

    def create_rod(self, number: int, new_position: list):
        """Create a new rod, display it and log this action.

        Parameters
        ----------
        number : int
        new_position : list
            Positon coordinates: [x1, y1, x2, y2]
        """
        new_rod = rods.RodNumber(self._current_color, self, str(number))
        new_rod.rod_id = number
        new_rod.setObjectName(f"rn_{number}")
        new_rod.rod_points = new_position
        new_rod.rod_state = rods.RodState.SELECTED
        # Newly created rods are always "seen"
        new_rod.seen = True
        self._particles.append(new_rod)
        self._connect_rod(new_rod)
        self._scale_image()
        last_action = actions.CreateRodAction(new_rod.copy())
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
