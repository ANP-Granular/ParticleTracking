import math
from typing import List
from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QLabel, QMessageBox, QInputDialog

from rodnumberwidget import RodNumberWidget, RodState
from actionlogger import ActionLogger, DeleteRodAction, \
    ChangeRodPositionAction, Action, ChangedRodNumberAction

ICON_PATH = "./resources/icon_main.ico"


class RodImageWidget(QLabel):
    edits: List[RodNumberWidget]
    request_color_change = QtCore.pyqtSignal(str, name="request_color_change")
    _logger: ActionLogger = None

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

    # Access to properties ====================================================
    @property
    def edits(self):
        return self._edits

    @edits.setter
    def edits(self, new_edits: List[RodNumberWidget]):
        # Delete previous rods
        del self.edits
        # Save and connect new rods
        self._edits = new_edits
        for rod in self._edits:
            rod.activated.connect(self.rod_activated)
            rod.id_changed.connect(self.check_rod_conflicts)
            rod.show()
        self._scale_image()

    @edits.deleter
    def edits(self):
        if self._edits is None:
            return
        for rod in self._edits:
            rod.deleteLater()
        self._edits = None

    @property
    def scale_factor(self):
        return self._scale_factor

    @scale_factor.setter
    def scale_factor(self, factor: float):
        if factor <= 0:
            raise ValueError('factor must be >0')
        self._scale_factor = factor
        self._scale_image()

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, new_image: QtGui.QImage):
        if new_image.isNull():
            raise ValueError("Assigned image cannot be 'Null'.")
        self._image = new_image
        self.base_pixmap = QtGui.QPixmap.fromImage(new_image)
        self._scale_image()

    @property
    def logger(self):
        return self._logger

    @logger.setter
    def logger(self, new_logger):
        if self._logger:
            self._logger.undo_action.disconnect()
        self._logger = new_logger
        self._logger.undo_action.connect(self.undo_action)

    # Display manipulation ====================================================
    def _scale_image(self):
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

    def draw_rods(self):
        if self._edits is None:
            # No rods available that might need redrawing
            return
        rod_pixmap = QtGui.QPixmap(self.base_pixmap)
        painter = QtGui.QPainter(rod_pixmap)
        for rod in self._edits:
            rod_pos = self.adjust_rod_position(rod)

            # Set the line style depending on the rod number widget state
            if rod.rod_state == RodState.NORMAL:
                pen_color = QtCore.Qt.cyan
            elif rod.rod_state == RodState.SELECTED:
                pen_color = QtCore.Qt.white
            elif rod.rod_state == RodState.EDITING:
                # Skip this rod as a new one is currently drawn
                continue
            elif rod.rod_state == RodState.CHANGED:
                pen_color = QtCore.Qt.green
            elif rod.rod_state == RodState.CONFLICT:
                pen_color = QtCore.Qt.red
            else:
                msg = QMessageBox()
                msg.setWindowIcon(QtGui.QIcon(ICON_PATH))
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("Rod Tracker")
                msg.setText("A rod with unknown state was encountered!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec()
                continue
            # Draw the rods
            pen = QtGui.QPen(pen_color, 3)
            painter.setPen(pen)
            painter.drawLine(*rod_pos)

        painter.end()
        self.setPixmap(rod_pixmap)
        return rod_pixmap

    def clear_screen(self):
        del self.edits
        self._scale_image()

    def scale_to_size(self, new_size: QtCore.QSize):
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
                            rod.set_state(RodState.EDITING)
                    self.rod_pixmap = self.draw_rods()
            else:
                if event.button() == QtCore.Qt.RightButton:
                    # Abort current line drawing
                    self.startPos = None
                    for rod in self._edits:
                        if rod.rod_state == RodState.EDITING:
                            rod.set_state(RodState.SELECTED)
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
        # Draw intermediate rod position between clicks
        if self.startPos is not None:
            end = self.subtract_offset(mouse_event.pos(), self._offset)
            pixmap = QtGui.QPixmap(self.rod_pixmap)
            qp = QtGui.QPainter(pixmap)
            pen = QtGui.QPen(QtCore.Qt.white, 3)
            qp.setPen(pen)
            qp.drawLine(self.startPos, end)
            qp.end()
            self.setPixmap(pixmap)

    def save_line(self, start, end):
        send_rod = None
        for rod in self._edits:
            if rod.rod_state == RodState.EDITING:
                new_position = [start.x(), start.y(), end.x(), end.y()]
                new_position = [coord / 10 / self._scale_factor for coord
                                in
                                new_position]
                this_action = ChangeRodPositionAction(rod.copy_rod(),
                                                      new_position)
                self._logger.add_action(this_action)
                rod.rod_points = new_position
                rod.set_state(RodState.SELECTED)
                send_rod = rod
                break
        if send_rod is None:
            # Get intended rod number from user
            selected_rod, ok = QInputDialog.getInt(self,
                                                   'Choose a rod to replace',
                                                   'Rod number')
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
                    new_position = [coord / 10 / self._scale_factor for coord
                                    in
                                    new_position]
                    this_action = ChangeRodPositionAction(rod.copy_rod(),
                                                          new_position)
                    self._logger.add_action(this_action)
                    rod.rod_points = new_position
                    rod.set_state(RodState.SELECTED)
                    break
            if not rod_exists:
                msg = QMessageBox()
                msg.setWindowIcon(QtGui.QIcon(ICON_PATH))
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("Rod Tracker")
                msg.setText(f"There was no rod found with #{selected_rod}")
                msg.setStandardButtons(
                    QMessageBox.Retry | QMessageBox.Cancel)
                user_decision = msg.exec()
                if user_decision == QMessageBox.Cancel:
                    # Discard line
                    return
                else:
                    # Retry rod number selection
                    self.save_line(start, end)
                # # Rod didn't exists -> create new RodNumber
                # new_rod = RodNumberWidget(self, str(selected_rod),
                #                           QPoint(start.x(), start.y()))
                # new_rod.setStyleSheet(RodStyle.GENERAL)
                # new_rod.last_id = selected_rod
                # # Connect signals emitted by the rods
                # new_rod.activated.connect(self.rod_activated)
                # new_rod.id_changed.connect(self.check_rod_conflicts)
                # new_rod.setObjectName(f"rn_{selected_rod}")
                # new_rod.show()
                # self._edits.append(new_rod)
                # new_position = [start.x(), start.y(), end.x(), end.y()]
                # new_position = [coord / 10 / self._scale_factor for coord in
                #                 new_position]
                # new_rod.rod_points = new_position
                # new_rod.set_state(RodState.SELECTED)

    # Rod Handling ============================================================
    def rod_activated(self, rod_id):
        # A new rod was activated for position editing. Deactivate all others.
        for rod in self._edits:
            if rod.rod_id != rod_id:
                rod.deactivate_rod()
            if rod.rod_id == rod_id:
                rod.set_state(RodState.SELECTED)
        self.draw_rods()

    def check_rod_conflicts(self, set_rod, last_id):
        # Marks any rods that have the same number in RodStyle.CONFLICT
        conflicting = []
        for rod in self._edits:
            if rod.rod_id == set_rod.rod_id:
                conflicting.append(rod)
        if len(conflicting) > 1:
            for rod in conflicting:
                rod.set_state(RodState.CONFLICT)
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
            msg.exec()
            if msg.clickedButton() == btn_switch:
                # Switch the rod numbers
                first_change = None
                second_change = None
                for rod in conflicting:
                    rod.set_state(RodState.CHANGED)
                    if rod is not set_rod:
                        id_to_log = rod.rod_id
                        rod.setText(str(last_id))
                        rod.rod_id = last_id
                        first_change = self._logger.catch_rodnumber_change(
                            rod, id_to_log)
                    else:
                        second_change = self._logger.catch_rodnumber_change(
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
                    rod.set_state(RodState.CHANGED)
            elif msg.clickedButton() == btn_disc_old:
                delete_action = None
                change_action = None
                for rod in conflicting:
                    if rod is not set_rod:
                        # Delete old by saving an "empty" rod (0,0)->(0,0)
                        rod.rod_id = last_id
                        rod.setText(str(last_id))
                        delete_action = DeleteRodAction(rod.copy_rod())
                        rod.rod_points = [0, 0, 0, 0]
                        rod.set_state(RodState.CHANGED)
                        continue
                    rod.set_state(RodState.CHANGED)
                    change_action = self._logger.catch_rodnumber_change(
                        rod, last_id)
                delete_action.coupled_action = change_action
                self._logger.add_action(delete_action)
            self.draw_rods()
        else:
            # No conflicts, inform logger
            if self._logger is None:
                raise Exception("Logger not set.")
            self._logger.catch_rodnumber_change(set_rod, last_id)

    def check_exchange(self, drop_position):
        # TODO: check where rod number was dropped and whether an exchange
        #  is needed.
        pass

    @QtCore.pyqtSlot(Action)
    def undo_action(self, action: Action):
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
                self._logger.takeItem(self._logger.indexFromItem(
                    action.coupled_action).row())
                self._logger.unsaved_changes.remove(action.coupled_action)
            new_rods = self._edits
            new_rods = [rod for rod in new_rods if rod.rod_id !=
                        action.rod.rod_id]
            new_rods = action.coupled_action.undo(rods=new_rods)
            new_rods.append(action.undo(None))
            self._edits = new_rods
            self.draw_rods()

        elif type(action) == ChangedRodNumberAction:
            if action.coupled_action is not None:
                self._logger.takeItem(self._logger.indexFromItem(
                    action.coupled_action).row())
                self._logger.unsaved_changes.remove(action.coupled_action)
            new_rods = action.undo(rods=self._edits)
            self._edits = new_rods
            self.draw_rods()
        else:
            # Cannot handle this action
            return

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        super().resizeEvent(a0)
        # Adjust rod positions after resizing of the widget happened,
        # e.g. the slider was acuated or the image was scaled
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
        new_x = point.x() - offset[0]
        new_y = point.y() - offset[1]
        return QtCore.QPoint(new_x, new_y)

    def adjust_rod_position(self, rod: RodNumberWidget):
        rod_pos = rod.rod_points
        rod_pos = [int(10 * self._scale_factor * coord)
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
                x_orthogonal / len_vec * 15) + int(x / 2)
            pos_y = rod_pos[1] + int(
                y_orthogonal / len_vec * 15) + int(y / 2)
            # Account for the widget's dimensions
            pos_x -= rod.size().width() / 2
            pos_y -= rod.size().height() / 2

        except ZeroDivisionError:
            # Rod has length of 0
            pos_x = rod_pos[0] + 17
            pos_y = rod_pos[1] + 17

        pos_x += self._offset[0]
        pos_y += self._offset[1]

        rod.move(QtCore.QPoint(pos_x, pos_y))
        return rod_pos
