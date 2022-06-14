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

import math
import numpy as np
import re
from typing import List, Union
from PyQt5 import QtGui, QtCore
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QLabel, QMessageBox, QInputDialog

from Python.ui.rodnumberwidget import RodNumberWidget, RodState, RodStateError
from Python.ui import dialogs
from Python.backend.logger import ActionLogger, DeleteRodAction, \
    ChangeRodPositionAction, Action, ChangedRodNumberAction, CreateRodAction


ICON_PATH = "./resources/icon_main.ico"


class RodImageWidget(QLabel):
    """A custom QLabel that displays an image and can overlay rods.

    Parameters
    ----------
    *args : iterable
        Positional arguments for the QLabel superclass.
    **kwargs : dict
        Keyword arguments for the QLabel superclass.

    Attributes
    ----------
    startPos : QtCore.QPoint
        Start position for new rod position.
    rod_pixmap : QPixmap
        Image that is temporarily painted on when rod corrections are put in
        by the user.
    base_pixmap : QPixmap
        A "clean" image in the correct scaled size.
    edits : List[RodNumberWidget]
    scale_factor : float
    image : QImage
    logger : ActionLogger
    cam_id : str
        ID of the GUI object. It must be human readable as it is used for
        labelling the performed actions displayed in the GUI.

    Signals
    -------
    request_color_change(str)
        Request to change the displayed colors. Currently this is used to
        revert actions performed on a color other than the displayed one.
    request_frame_change(int)
        Request to change the displayed frames. Currently this is used to
        revert actions performed on a frame other than the displayed one.
    notify_undone(Action)
        Notifies objects, that the `Action` in the payload has been reverted.
    request_new_rod(int, list)
        Request to generate and display a new rod with the ID and position
        given in the payload. The rod's position is given in the saving
        frame of reference.
    normal_frame_change(int)
        Requests a normal change of frame. The payload is the index of the
        desired frame, relative to the current one, e.g. -1 to request the
        previous image.

    Slots
    -----
    undo_action(Union[Action, ChangeRodPositionAction, ChangedRodNumberAction,
                      DeleteRodAction])
    delete_rod(RodNumberWidget)
    update_settings(dict)

    """

    edits: List[RodNumberWidget]
    request_color_change = QtCore.pyqtSignal(str, name="request_color_change")
    request_frame_change = QtCore.pyqtSignal(int, name="request_frame_change")
    notify_undone = QtCore.pyqtSignal(Action, name="notify_undone")
    request_new_rod = QtCore.pyqtSignal(int, list, name="request_new_rod")
    normal_frame_change = QtCore.pyqtSignal(int, name="normal_frame_change")
    _logger: ActionLogger = None
    # Settings
    _rod_thickness = 3
    _number_offset = 15
    _position_scaling = 10.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Custom properties
        self.startPos = None
        self._image = None
        # image that is temporarily painted on when rod corrections are input
        self.rod_pixmap = None
        # "clean" image in correct scaling
        self.base_pixmap = None
        self._edits = None
        self._scale_factor = 1.0
        self._offset = [0, 0]
        self._cam_id = "gp3"

    # Access to properties ====================================================
    @property
    def edits(self) -> List[RodNumberWidget]:
        """
        Property that holds `RodNumberWidget`s representing rods that are
        displayable on the Widget.

        Returns
        -------
        List[RodNumberWidget]
        """
        return self._edits

    @edits.setter
    def edits(self, new_edits: List[RodNumberWidget]):
        # Delete previous rods
        del self.edits
        # Save and connect new rods
        self._edits = new_edits
        for rod in self._edits:
            self._connect_rod(rod)
        self._scale_image()

    @edits.deleter
    def edits(self):
        if self._edits is None:
            return
        for rod in self._edits:
            rod.deleteLater()
        self._edits = None

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
            raise ValueError('factor must be >0')
        self._scale_factor = factor
        self._scale_image()

    @property
    def image(self) -> QtGui.QImage:
        """
        Property that holds the image, that is displayed by the Widget.

        Returns
        -------
        QImage
        """
        return self._image

    @image.setter
    def image(self, new_image: QtGui.QImage):
        if new_image.isNull():
            raise ValueError("Assigned image cannot be 'Null'.")
        self._image = new_image
        self.base_pixmap = QtGui.QPixmap.fromImage(new_image)
        self._scale_image()

    @property
    def logger(self) -> ActionLogger:
        """
        Property that holds a logger object keeping track of users' actions
        performed on this widget and its contents.

        Returns
        -------
        ActionLogger
        """
        return self._logger

    @logger.setter
    def logger(self, new_logger: ActionLogger):
        if self._logger:
            self._logger.undo_action.disconnect()
        self._logger = new_logger
        self._logger.undo_action.connect(self.undo_action)

    @property
    def cam_id(self) -> str:
        """
        Property that holds a string used as and ID for logging and data
        selection.

        Returns
        -------
        str
        """
        return self._cam_id

    @cam_id.setter
    def cam_id(self, cam_id: str):
        id_regex = re.compile('gp\d+')
        if re.fullmatch(id_regex, cam_id) is None:
            cam_id = "gp3"
        self._cam_id = cam_id
        try:
            self._logger.parent_id = cam_id
        except AttributeError:
            raise AttributeError("There is no ActionLogger set for this "
                                 "Widget yet.")

    # Display manipulation ====================================================
    def _scale_image(self) -> None:
        if self._image is None:
            return
        old_pixmap = QtGui.QPixmap.fromImage(self._image)
        new_pixmap = old_pixmap.scaledToHeight(
            int(old_pixmap.height() * self._scale_factor),
            QtCore.Qt.SmoothTransformation)
        self.setPixmap(new_pixmap)
        self.base_pixmap = new_pixmap

        # Handle the pixmap's shift to the center of the widget, in cases
        # the surrounding scrollArea is larger than the pixmap
        x_off = (self.width() - self.base_pixmap.width())//2
        y_off = (self.height() - self.base_pixmap.height())//2
        self._offset = [x_off if x_off > 0 else 0,
                        y_off if y_off > 0 else 0]

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
        if self._edits is None:
            # No rods available that might need redrawing
            return
        rod_pixmap = QtGui.QPixmap(self.base_pixmap)
        painter = QtGui.QPainter(rod_pixmap)
        for rod in self._edits:
            rod_pos = self.adjust_rod_position(rod)
            # Gets the display style from the rod number widget.
            try:
                pen = rod.pen
            except RodStateError:
                dialogs.show_warning("A rod with unknown state was "
                                     "encountered!")
                pen = None
            if pen is None:
                continue
            painter.setPen(pen)
            painter.drawLine(*rod_pos)

        painter.end()
        self.setPixmap(rod_pixmap)
        return rod_pixmap

    def clear_screen(self) -> None:
        """ Removes the displayed rods and deletes them.

        Returns
        -------
        None
        """
        del self.edits
        self._scale_image()

    def scale_to_size(self, new_size: QtCore.QSize):
        """ Scales the image to a specified size.

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
        height_ratio = new_size.height()/old_pixmap.height()
        width_ratio = new_size.width()/old_pixmap.width()
        if height_ratio > width_ratio:
            # use width
            self.scale_factor = width_ratio
            return
        else:
            # use height
            self.scale_factor = height_ratio
            return

    # Interaction callbacks ===================================================
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """ Reimplements QLabel.mousePressEvent(event).

        Handles the beginning and ending actions for rod corrections by the
        user.

        Parameters
        ----------
        event : QMouseEvent

        Returns
        -------
        None
        """
        if self._edits is not None:
            if self.startPos is None:
                # Check rod states for number editing mode
                for rod in self._edits:
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

                if event.button() == QtCore.Qt.RightButton and \
                        self._edits is not None:
                    # Deactivate any active rods
                    self.rod_activated(-1)
                elif event.button() == QtCore.Qt.LeftButton:
                    # Start rod correction
                    self.startPos = self.subtract_offset(event.pos(),
                                                         self._offset)
                    for rod in self._edits:
                        if rod.rod_state == RodState.SELECTED:
                            rod.rod_state = RodState.EDITING
                    self.rod_pixmap = self.draw_rods()
            else:
                if event.button() == QtCore.Qt.RightButton:
                    # Abort current line drawing
                    self.startPos = None
                    for rod in self._edits:
                        if rod.rod_state == RodState.EDITING:
                            rod.rod_state = RodState.SELECTED
                    self.draw_rods()
                    self.rod_pixmap = None
                else:
                    # Finish line and save it
                    self.save_line(self.startPos, self.subtract_offset(
                        event.pos(), self._offset))
                    self.startPos = None
                    self.draw_rods()
                    self.rod_pixmap = None

    def mouseMoveEvent(self, mouse_event: QtGui.QMouseEvent) -> None:
        """Reimplements QLabel.mouseMoveEvent(event).

        Handles the drawing and updating of a "draft" rod during start and end
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

    def save_line(self, start: QtCore.QPoint, end: QtCore.QPoint):
        """Saves a line selected by the user to be a rod with a rod number.

        The user's selected start and end point are saved in a
        `RodNumberWidget`. Either in one that was activated prior to the
        point selection, or that is selected by the user post point
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
        for rod in self._edits:
            if rod.rod_state == RodState.EDITING:
                new_position = [start.x(), start.y(), end.x(), end.y()]
                new_position = \
                    [coord / self._position_scaling / self._scale_factor
                     for coord in new_position]
                this_action = ChangeRodPositionAction(rod.copy(),
                                                      new_position)
                self._logger.add_action(this_action)
                rod.rod_points = new_position
                rod.rod_state = RodState.SELECTED
                send_rod = rod
                break
        
        if send_rod is None:
            # Get intended rod number from user
            
    
            # Find out which rods are unseen
            
            rods_unseen = []
            
            for rod in self._edits:
                if rod.seen == False:
                    rods_unseen.append(rod.rod_id)
                    
            rods_unseen.sort()
                    
            
            if rods_unseen:
                dialog_rodnum = 'Unseen rods: ' + str (rods_unseen) + '\n Enter rod number:'
                selected_rod, ok = QInputDialog.getInt(self,
                                                       'Choose a rod to replace',
                                                       dialog_rodnum, value = rods_unseen[0], min=0,
                                                       max=99)
            else:    
                dialog_rodnum = 'No unseen rods. Enter rod number: '
                selected_rod, ok = QInputDialog.getInt(self,
                                                       'Choose a rod to replace',
                                                       dialog_rodnum, min=0,
                                                       max=99)
            
            if not ok:
                return
            # Check whether the rod already exists
            rod_exists = False
            for rod in self._edits:
                if rod.rod_id == selected_rod:
                    # Overwrite previous position
                    rod_exists = True
                    rod.rod_id = selected_rod
                    new_position = [start.x(), start.y(), end.x(), end.y()]
                    new_position = \
                        [coord / self._position_scaling / self._scale_factor
                         for coord in new_position]
                    this_action = ChangeRodPositionAction(rod.copy(),
                                                          new_position)
                    self._logger.add_action(this_action)
                    rod.rod_points = new_position
                    # Mark rod as "seen"
                    rod.seen = True
                    rod.rod_state = RodState.SELECTED
                    break
            if not rod_exists:
                # Rod didn't exists -> create new RodNumber
                corrected_pos = [
                    start.x() / self._position_scaling / self._scale_factor,
                    start.y() / self._position_scaling / self._scale_factor,
                    end.x() / self._position_scaling / self._scale_factor,
                    end.y() / self._position_scaling / self._scale_factor
                ]
                self.request_new_rod.emit(selected_rod, corrected_pos)

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
        for rod in self._edits:
            if rod.rod_id != rod_id:
                rod.deactivate_rod()
            if rod.rod_id == rod_id:
                rod.rod_state = RodState.SELECTED
        self.draw_rods()

    def check_rod_conflicts(self, set_rod: RodNumberWidget, last_id: int) ->\
            None:
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
        """
        # Marks any rods that have the same number in RodStyle.CONFLICT
        conflicting = []
        for rod in self._edits:
            if rod.rod_id == set_rod.rod_id:
                conflicting.append(rod)
        if len(conflicting) > 1:
            for rod in conflicting:
                rod.rod_state = RodState.CONFLICT
        self.draw_rods()
        if len(conflicting) > 1:
            msg = QMessageBox()
            msg.setWindowIcon(QtGui.QIcon(ICON_PATH))
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Rod Tracker")
            msg.setText(
                f"A conflict was encountered with setting Rod"
                f"#{set_rod.rod_id} (previously Rod#{last_id}). \nHow shall "
                f"this conflict be resolved?")
            btn_switch = msg.addButton("Switch numbers",
                                       QMessageBox.ActionRole)
            btn_return = msg.addButton("Return state", QMessageBox.ActionRole)
            btn_disc_old = msg.addButton("Discard old rod",
                                         QMessageBox.ActionRole)
            btn_manual = msg.addButton("Resolve manual",
                                       QMessageBox.ActionRole)
            btn_manual.setEnabled(False)
            # The "Discard old rod" feature is currently disabled, as the
            # redo of the chained operations don't work correctly and need a
            # larger process refactoring, that does not appear to be worth
            # the time, as users report they are not using this feature but
            # rather accomplish the intended operation in another way.
            btn_disc_old.setEnabled(False)
            msg.exec()
            if msg.clickedButton() == btn_switch:
                # Switch the rod numbers
                first_change = None
                second_change = None
                for rod in conflicting:
                    rod.rod_state = RodState.CHANGED
                    if rod is not set_rod:
                        id_to_log = rod.rod_id
                        rod.setText(str(last_id))
                        rod.rod_id = last_id
                        first_change = self.catch_rodnumber_change(
                            rod, id_to_log)
                    else:
                        second_change = self.catch_rodnumber_change(
                            rod, last_id)
                first_change.coupled_action = second_change
                second_change.coupled_action = first_change

            elif msg.clickedButton() == btn_return:
                # Return to previous state
                if last_id == -1:
                    set_rod.deleteLater()
                    self._edits.remove(set_rod)
                else:
                    set_rod.setText(str(last_id))
                    set_rod.rod_id = last_id
                for rod in conflicting:
                    rod.rod_state = RodState.CHANGED
            elif msg.clickedButton() == btn_disc_old:
                # Discard old rod
                delete_action = None
                change_action = None
                for rod in conflicting:
                    if rod is not set_rod:
                        # Delete old by saving an "empty" rod (0,0)->(0,0)
                        rod.rod_id = last_id
                        rod.setText(str(last_id))
                        delete_action = DeleteRodAction(rod.copy())
                        rod.rod_points = [0, 0, 0, 0]
                        rod.rod_state = RodState.CHANGED
                        continue
                    rod.rod_state = RodState.CHANGED
                    change_action = self.catch_rodnumber_change(
                        rod, last_id)
                delete_action.coupled_action = change_action
                self._logger.add_action(delete_action)
            self.draw_rods()
        else:
            # No conflicts, inform logger
            if self._logger is None:
                raise Exception("Logger not set.")
            self.catch_rodnumber_change(set_rod, last_id)

    def catch_rodnumber_change(self, new_rod: RodNumberWidget, last_id: int)\
            -> ChangedRodNumberAction:
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
        this_action = ChangedRodNumberAction(old_rod, new_id)
        self._logger.add_action(this_action)
        return this_action

    def check_exchange(self, drop_position):
        """Evaluates, whether a position is on top of a `RodNumberWidget`.

        Evaluates, whether a position is on top of a `RodNumberWidget`
        maintained by this object."""
        # TODO: check where rod number was dropped and whether an exchange
        #  is needed.
        pass

    @QtCore.pyqtSlot(Action)
    def undo_action(self, action: Union[Action, ChangeRodPositionAction,
                                        ChangedRodNumberAction,
                                        DeleteRodAction]):
        """Reverts an `Action` performed on a rod.

        Reverts the `Action` given this function, if it was constructed by
        the object. It can handle actions performed on a rod. This includes
        position changes, number changes and deletions. It returns without
        further actions, if the `Action` was not originally performed on
        this object or if it has is of an unknown type.

        Parameters
        ----------
        action : Union[Action, ChangeRodPositionAction, ChangedRodNumberAction, DeleteRodAction]
            An `Action` that was logged previously. It will only be
            reverted, if it associated with this object.

        Returns
        -------
        None
        """
        if action.parent_id != self._cam_id:
            return

        if action.frame != self.logger.frame:
            self.request_frame_change.emit(action.frame)

        try:
            action_color = action.rod.color
            if action_color != self._edits[0].color:
                self.request_color_change.emit(action_color)
        except AttributeError:
            # given action does not require a color to be handled
            pass

        if type(action) == ChangeRodPositionAction:
            new_rods = action.undo(rods=self._edits)
            self._edits = new_rods
            self.draw_rods()
        elif type(action) == DeleteRodAction:
            if action.coupled_action is not None:
                self._logger.register_undone(action.coupled_action)
            current_rods = self._edits
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
            self._edits = new_rods
            self.draw_rods()

        elif type(action) == ChangedRodNumberAction:
            if action.coupled_action is not None:
                self._logger.register_undone(action.coupled_action)
            new_rods = action.undo(rods=self._edits)
            self._edits = new_rods
            self.draw_rods()

        elif type(action) == CreateRodAction:
            new_rods = action.undo(rods=self._edits)
            if action.coupled_action is not None:
                # This should only get triggered when a
                # RodNumberChangeAction that incorporates a RodDeletion gets
                # redone, so a CreateRodAction+RodPositionChange.
                # If this shall be extended to more combinations the line
                # below must be uncommented and then the redo mechanism will
                # break for the above mentioned occasion! So more work is
                # required then.
                # self._logger.register_undone(action.coupled_action)
                new_rods = action.coupled_action.undo(rods=new_rods)
            self._edits = new_rods
            self.draw_rods()
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
        # e.g. the slider was actuated or the image was scaled
        if self._edits is not None:
            # Calculate offset
            x_off = (a0.size().width() - self.base_pixmap.width()) // 2
            y_off = (a0.size().height() - self.base_pixmap.height()) // 2
            x_off = x_off if x_off > 0 else 0
            y_off = y_off if y_off > 0 else 0
            self._offset = [x_off, y_off]

            # Complete version
            for rod in self._edits:
                self.adjust_rod_position(rod)

    @staticmethod
    def subtract_offset(point: QtCore.QPoint, offset: [int]) -> QtCore.QPoint:
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

    def adjust_rod_position(self, rod: RodNumberWidget) -> List[int]:
        """Adjusts a rod number position to be on the right side of its rod.

        The position of the `RodNumberWidget` is adjusted, such that it is
        displayed to the right side and in the middle of its corresponding
        rod. This adjustment is mainly due to scaling of the image. It also
        returns the rods position in the image associated with the moved
        `RodNumberWidget`.

        Parameters
        ----------
        rod : RodNumberWidget

        Returns
        -------
        List[int]
        """
        rod_pos = rod.rod_points
        rod_pos = [int(self._position_scaling * self._scale_factor * coord)
                   for coord in rod_pos]

        # Update rod number positions
        x = rod_pos[2] - rod_pos[0]
        y = rod_pos[3] - rod_pos[1]
        x_orthogonal = -y
        y_orthogonal = x
        if x_orthogonal < 0:
            # change vector to always point to the right
            x_orthogonal = -x_orthogonal
            y_orthogonal = -y_orthogonal
        len_vec = math.sqrt(x_orthogonal ** 2 + y_orthogonal ** 2)
        try:
            pos_x = rod_pos[0] + int(
                x_orthogonal / len_vec * self._number_offset) + int(x / 2)
            pos_y = rod_pos[1] + int(
                y_orthogonal / len_vec * self._number_offset) + int(y / 2)
            # Account for the widget's dimensions
            pos_x -= rod.size().width() / 2
            pos_y -= rod.size().height() / 2

        except ZeroDivisionError:
            # Rod has length of 0
            pos_x = rod_pos[0] + self._number_offset
            pos_y = rod_pos[1] + self._number_offset

        pos_x += self._offset[0]
        pos_y += self._offset[1]

        rod.move(QtCore.QPoint(pos_x, pos_y))
        return rod_pos

    @QtCore.pyqtSlot(RodNumberWidget)
    def delete_rod(self, rod: RodNumberWidget) -> None:
        """Deletes the given rod, thus sets its position to (0,0).

        Parameters
        ----------
        rod : RodNumberWidget

        Returns
        -------
        None
        """
        rod.setText(str(rod.rod_id))
        delete_action = DeleteRodAction(rod.copy())
        rod.rod_points = [0, 0, 0, 0]
        rod.rod_state = RodState.CHANGED
        self._logger.add_action(delete_action)
        self.draw_rods()

    def _connect_rod(self, rod: RodNumberWidget) -> None:
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

    def eventFilter(self, source: QtCore.QObject, event: QtCore.QEvent) -> \
            bool:
        """Intercepts events, here QKeyEvents for frame switching and edit
        aborting.

        Parameters
        ----------
        source : QObject
        event : QEvent

        Returns
        -------
        bool
            True, if the event shall not be propagated further.
            False, if the event shall be passed to the next object to be
            handled.
        """
        if type(event) != QtGui.QKeyEvent:
            return False

        event = QKeyEvent(event)
        if type(source) != RodNumberWidget:
            return False
        if source.isReadOnly():
            if event.key() == QtCore.Qt.Key_Escape:
                # Abort any editing (not rod number editing)
                if self._edits is not None:
                    # Deactivate any active rods
                    self.rod_activated(-1)
                    return True
            elif event.key() == QtCore.Qt.Key_Right:
                self.normal_frame_change.emit(1)
                return False
            elif event.key() == QtCore.Qt.Key_Left:
                self.normal_frame_change.emit(-1)
                return False
            else:
                # RodNumberWidget is in the process of rod number changing,
                # let the widget handle that itself
                return False

        return False

    @QtCore.pyqtSlot(dict)
    def update_settings(self, settings: dict) -> None:
        """Catches updates of the settings from a `Settings` class.

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

        if settings_changed:
            self.draw_rods()
