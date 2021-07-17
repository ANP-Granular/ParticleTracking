import math
import os
import sys
from PyQt5 import QtCore, QtWidgets, Qt
from PyQt5.QtGui import QPixmap, QPen
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import pandas as pd
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QImage
from track_ui import Ui_MainWindow
from rodnumberwidget import RodNumberWidget, RodState, RodStyle


class RodTrackWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.setFocus()
        # Initialize
        self.startPos = None
        # scale factor for image
        self.scaleFactor = 1.0
        # tracker of the current image that's displayed
        self.CurrentFileIndex = 0
        self.data_files = None
        self.data_file_name = 'rods_df_{:s}.csv'
        self.color = "black"
        self.image = None
        self.rod_pixmap = None
        self.base_pixmap = None
        self.fileList = None
        self.track = True
        self.edits = None

        # Signal to activate actions
        self.ui.pushprevious.clicked.connect(self.show_prev)
        self.ui.pushnext.clicked.connect(self.show_next)
        self.ui.overlay.clicked.connect(self.show_overlay)
        # self.ui.RodNumber.clicked.connect(lambda: self.show_overlay(
        #     with_number=True))
        # self.ui.ClearSave.clicked.connect(self.clear_screen)
        self.ui.actionzoom_in.triggered.connect(lambda: self.scaleImage(
            factor=1.25))
        self.ui.actionzoom_out.triggered.connect(lambda: self.scaleImage(
            factor=0.8))
        self.ui.actionopen.triggered.connect(self.file_open)
        self.ui.normalSizeAct.triggered.connect(self.original_size)
        # self.ui.fitToWindowAct.triggered.connect(self.fitToWindow)
        self.ui.Photo.mouseMoveEvent = self.move_mouse
        self.ui.Photo.mousePressEvent = self.getPixel

    def file_open(self):
        # opens directory to select image
        fileName, _ = QFileDialog.getOpenFileName(None, 'Open an image', '',
                                                  'Images (*.png *.jpeg '
                                                  '*.jpg)')
        file_name = os.path.split(fileName)[-1]
        # File name without extension
        file_name = os.path.splitext(file_name)[0]
        print('File name:', file_name)
        if fileName:
            # open file as image
            self.image = QImage(fileName)
            if self.image.isNull():
                QMessageBox.information(self, "Image Viewer",
                                        "Cannot load %s." % fileName)
                return
            # Directory
            dirpath = os.path.dirname(fileName)
            print('Dir_name:', dirpath)
            self.fileList = []
            # this loop is kinda tricky
            # it loop through all the images
            # checks for some condition
            # and appends it to a file List
            for idx, f in enumerate(os.listdir(dirpath)):
                f_compare = os.path.splitext(f)[0]
                indx_f = f_compare == file_name
                if indx_f is True:
                    # Set file index
                    self.CurrentFileIndex = idx
                fpath = os.path.join(dirpath, f)
                # print('fpath name:', fpath)
                if os.path.isfile(fpath) and f.endswith(('.png', '.jpg',
                                                         '.jpeg')):
                    # Add all image files to a list
                    self.fileList.append(fpath)
            # Sort according to name / ascending order
            self.fileList.sort()
            print('Num of items in list:', len(self.fileList))
            # then the image is displayed in this function NoRods
            self.show_pixmap_NoRods()
            print('Open_file {}:'.format(self.CurrentFileIndex), file_name)
            self.ui.label.setText('File opened: {}'.format(file_name))

    def show_pixmap_NoRods(self):
        self.base_pixmap = QtGui.QPixmap.fromImage(self.image)
        self.ui.Photo.setPixmap(self.base_pixmap)
        self.scaleFactor = 1.0
        # self.ui.fitToWindowAct.setEnabled(True)
        self.updateActions()

    def show_overlay(self, with_number=False):
        items = ("black", "blue", "green", "purple", "red", "yellow")
        col_list = ["particle", "frame", "x1_gp3", "x2_gp3", "y1_gp3",
                    "y2_gp3"]
        while True:
            # TODO: Check whether image file is loaded
            if self.data_files is not None:
                item, ok = QInputDialog.getItem(None,
                                                "Select a color to display",
                                                "list of colors", items, 0,
                                                False)
                if not ok:
                    return
                else:
                    self.color = item
                    file_found = os.path.exists(self.data_files +
                        self.data_file_name.format(item))
                    if file_found:
                        # Overlay rod position data from the file
                        # TODO: This if-clause needs a rework/can be removed
                        if with_number:
                            # Overlay with colored bars and rod numbers
                            self.load_rods()
                            pass
                        else:
                            # Overlay only with colored bars
                            self.load_rods()
                        return
                    else:
                        # If a folder was selected previously, but no
                        # matching file was found
                        msg = QMessageBox()
                        msg.setIcon(QMessageBox.Warning)
                        msg.setText(
                            f"There was no file for '{item}' found in: "
                            f"'{self.data_files}'")
                        msg.setStandardButtons(
                            QMessageBox.Retry | QMessageBox.Cancel)
                        btn_select = msg.addButton("Select Folder",
                                                   QMessageBox.ActionRole)
                        user_decision = msg.exec()
                        if user_decision == QMessageBox.Cancel:
                            # Stop overlaying
                            return
                        elif msg.clickedButton() == btn_select:
                            # Switch to folder selection
                            self.data_files = None
                            continue
                        else:
                            # Retry color selection
                            continue
            else:
                self.data_files = QFileDialog.getExistingDirectory(
                    None, 'Choose Folder with position data', '') + '/'
                if self.data_files == '/':
                    self.data_files = None
                    return

    def load_rods(self):
        # Load rod position data
        items = ("black", "blue", "green", "purple", "red", "yellow")
        col_list = ["particle", "frame", "x1_gp3", "x2_gp3", "y1_gp3",
                    "y2_gp3"]
        filename = (self.fileList[self.CurrentFileIndex])
        file_name = os.path.split(filename)[-1]
        df_part = pd.read_csv(self.data_files +
                              self.data_file_name.format(
                                  self.color),
                              usecols=col_list)
        df_part2 = df_part[df_part["frame"] ==
                           int(file_name[1:4])].reset_index()

        if self.edits is not None:
            for rn in self.edits:
                rn.deleteLater()
        self.edits = []
        for ind_rod, value in enumerate(df_part2['particle']):
            x1 = df_part2['x1_gp3'][ind_rod]
            x2 = df_part2['x2_gp3'][ind_rod]
            y1 = df_part2['y1_gp3'][ind_rod]
            y2 = df_part2['y2_gp3'][ind_rod]
            # Add rods
            ident = RodNumberWidget(self.ui.Photo, str(value), QPoint(0, 0))
            ident.setStyleSheet(RodStyle.GENERAL)
            ident.rod_id = value
            ident.rod_points = [x1, y1, x2, y2]
            # Connect signals emitted by the rods
            ident.activated.connect(self.rod_activated)
            ident.id_changed.connect(self.check_rod_conflicts)
            ident.setObjectName(f"rn_{ind_rod}")
            ident.show()
            self.edits.append(ident)
        self.draw_rods()

    def draw_rods(self):
        self.rod_pixmap = QPixmap(self.base_pixmap)
        painter = QPainter(self.rod_pixmap)
        if self.edits is None:
            # No rods available that might need redrawing
            return
        for rod in self.edits:
            rod_pos = rod.rod_points
            rod_pos = [int(10*self.scaleFactor*coord) for coord in rod_pos]

            # Update rod number positions
            x = rod_pos[2] - rod_pos[0]
            y = rod_pos[3] - rod_pos[1]
            x_orth = -y
            y_orth = x
            len_vec = math.sqrt(x_orth**2 + y_orth**2)
            try:
                pos_x = rod_pos[0] + int(x_orth/len_vec*15) + int(x/2)
                pos_y = rod_pos[1] + int(y_orth/len_vec*15) + int(y/2)
            except ZeroDivisionError:
                # Rod has length of 0
                pos_x = rod_pos[0] + 17
                pos_y = rod_pos[1] + 17
            rod.move(QPoint(pos_x, pos_y))

            # Set the line style depending on the rod number widget state
            if rod.rod_state == RodState.NORMAL:
                pen_color = Qt.cyan
            elif rod.rod_state == RodState.SELECTED:
                pen_color = Qt.white
            elif rod.rod_state == RodState.EDITING:
                # Skip this rod as a new one is currently drawn
                continue
            elif rod.rod_state == RodState.CHANGED:
                pen_color = Qt.green
            elif rod.rod_state == RodState.CONFLICT:
                pen_color = Qt.red
            else:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("RodTracking")
                msg.setText("A rod with unknown state was encountered!")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec()
                continue
            # Draw the rods
            pen = QPen(pen_color, 3)
            painter.setPen(pen)
            painter.drawLine(*rod_pos)

        painter.end()
        self.ui.Photo.setPixmap(self.rod_pixmap)
        # self.ui.fitToWindowAct.setEnabled(True)
        self.updateActions()

    def clear_screen(self):
        if self.edits is not None:
            for s in self.edits:
                s.deleteLater()
            self.edits = None
            self.ui.Photo.setPixmap(self.base_pixmap)
            # self.ui.fitToWindowAct.setEnabled(True)
            self.updateActions()

    def move_mouse(self, mouse_event):
        # Draw intermediate rod position between clicks
        if self.startPos is not None:
            end = mouse_event.pos()
            pixmap = QPixmap(self.rod_pixmap)
            qp = QPainter(pixmap)
            pen = QPen(Qt.white, 3)
            qp.setPen(pen)
            qp.drawLine(self.startPos, end)
            qp.end()
            self.ui.Photo.setPixmap(pixmap)

    def getPixel(self, event):
        if self.edits is not None:
            if self.startPos is None:
                # Check rod states for number editing mode
                for rod in self.edits:
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
                        return

                if event.button() == QtCore.Qt.RightButton and \
                        self.edits is not None:
                    # Deactivate any active rods
                    self.rod_activated(-1)
                elif event.button() == QtCore.Qt.LeftButton:
                    # Start rod correction
                    self.startPos = event.pos()
                    for rod in self.edits:
                        if rod.rod_state == RodState.SELECTED:
                            rod.set_state(RodState.EDITING)
                    self.draw_rods()
            else:
                if event.button() == QtCore.Qt.RightButton:
                    # Abort current line drawing
                    self.startPos = None
                    for rod in self.edits:
                        if rod.rod_state == RodState.EDITING:
                            rod.set_state(RodState.SELECTED)
                    self.draw_rods()
                else:
                    # Finish line and save it
                    self.save_line(self.startPos, event.pos())
                    self.startPos = None
                    self.draw_rods()

    # TODO: Overload save_line to either accept (QPoint, QPoint) or
    #  (RodNumberWidget)
    def save_line(self, start, end, selected_rod=None):
        if selected_rod is None:
            for rod in self.edits:
                if rod.rod_state == RodState.EDITING:
                    selected_rod = rod.rod_id
                    new_position = [start.x(), start.y(), end.x(), end.y()]
                    new_position = [coord/10/self.scaleFactor for coord in
                                    new_position]
                    rod.rod_points = new_position
                    rod.set_state(RodState.SELECTED)
                    break
        if selected_rod is None:
            # Get intended rod number from user
            selected_rod, ok = QInputDialog.getInt(self.ui.Photo,
                                                   'Choose a rod to replace',
                                                   'Rod number')
            if not ok:
                return
            # Check whether the rod already exists
            rod_exists = False
            for rod in self.edits:
                if rod.rod_id == selected_rod:
                    # Overwrite previous position
                    rod_exists = True
                    rod.rod_id = selected_rod
                    new_position = [start.x(), start.y(), end.x(), end.y()]
                    new_position = [coord / 10 / self.scaleFactor for coord in
                                    new_position]
                    rod.rod_points = new_position
                    rod.set_state(RodState.SELECTED)
                    break
            if not rod_exists:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setText(f"There was no rod found with #{selected_rod}")
                msg.setStandardButtons(QMessageBox.Retry | QMessageBox.Cancel)
                user_decision = msg.exec()
                if user_decision == QMessageBox.Cancel:
                    # Discard line
                    return
                else:
                    # Retry rod number selection
                    self.save_line(start, end)
                # # Rod didn't exists -> create new RodNumber
                # new_rod = RodNumberWidget(self.ui.Photo, str(selected_rod),
                #                           QPoint(start.x(), start.y()))
                # new_rod.setStyleSheet(RodStyle.GENERAL)
                # new_rod.last_id = selected_rod
                # # Connect signals emitted by the rods
                # new_rod.activated.connect(self.rod_activated)
                # new_rod.id_changed.connect(self.check_rod_conflicts)
                # new_rod.setObjectName(f"rn_{selected_rod}")
                # new_rod.show()
                # self.edits.append(new_rod)
                # new_position = [start.x(), start.y(), end.x(), end.y()]
                # new_position = [coord / 10 / self.scaleFactor for coord in
                #                 new_position]
                # new_rod.rod_points = new_position
                # new_rod.set_state(RodState.SELECTED)

        # Save changes to disk immediately
        filename = (self.fileList[self.CurrentFileIndex])
        file_name = os.path.split(filename)[-1]
        df_part = pd.read_csv(self.data_files + self.data_file_name.format(
            self.color), index_col=0)
        df_part.loc[(df_part.frame == int(file_name[1:4])) &
                    (df_part.particle == selected_rod), "x1_gp3"] = \
            start.x()/10.0/self.scaleFactor
        df_part.loc[(df_part.frame == int(file_name[1:4])) &
                    (df_part.particle == selected_rod), "x2_gp3"] = \
            end.x()/10.0/self.scaleFactor
        df_part.loc[(df_part.frame == int(file_name[1:4])) &
                    (df_part.particle == selected_rod), "y1_gp3"] = \
            start.y()/10.0/self.scaleFactor
        df_part.loc[(df_part.frame == int(file_name[1:4])) &
                    (df_part.particle == selected_rod), "y2_gp3"] = \
            end.y()/10.0/self.scaleFactor
        df_part.to_csv(self.data_files + self.data_file_name.format(
            self.color), index_label="")

    def show_next(self):
        if self.fileList:
            try:
                self.CurrentFileIndex += 1
                # Chooses next image with specified extension
                filename = (self.fileList[self.CurrentFileIndex])
                file_name = os.path.split(filename)[-1]
                file_name = os.path.splitext(file_name)[0]
                # Create Pixmap operator to display image
                image_next = QImage(filename)
                if image_next.isNull():
                    # the file is not a valid image, remove it from the list
                    # and try to load the next one
                    self.fileList.remove(filename)
                    self.show_next()
                else:
                    # TODO: use a dedicated image display/update method
                    #  instead of reimplementing it in multiple methods
                    # Clean up current rods
                    if self.edits is not None:
                        for rod in self.edits:
                            rod.deleteLater()
                        self.edits = None
                    # Display next image
                    new_pixmap = QtGui.QPixmap.fromImage(image_next)
                    self.base_pixmap = new_pixmap
                    self.image = image_next
                    self.ui.Photo.setPixmap(new_pixmap)
                    self.scaleFactor = 1.0
                    # self.ui.fitToWindowAct.setEnabled(True)
                    self.updateActions()
                    print('Next_file {}:'.format(self.CurrentFileIndex),
                          file_name)
                    # Update information on last action
                    self.ui.label.setText('File: {}'.format(file_name))

            except IndexError:
                # the iterator has finished, restart it
                self.CurrentFileIndex = -1
                self.show_next()
        else:
            # no file list found, load an image
            self.file_open()

    def show_prev(self):
        if self.fileList:
            try:
                self.CurrentFileIndex -= 1
                # Chooses previous image with specified extension
                filename = (self.fileList[self.CurrentFileIndex])
                file_name = os.path.split(filename)[-1]
                file_name = os.path.splitext(file_name)[0]
                # Create Pixmap operator to display image
                image_prev = QImage(filename)
                if image_prev.isNull():
                    # the file is not a valid image, remove it from the list
                    # and try to load the next one
                    self.fileList.remove(filename)
                    self.show_prev()
                else:
                    # TODO: use a dedicated image display/update method
                    #  instead of reimplementing it in multiple methods
                    # Clean up current rods
                    if self.edits is not None:
                        for rod in self.edits:
                            rod.deleteLater()
                        self.edits = None
                    # Display next image
                    new_pixmap = QtGui.QPixmap.fromImage(image_prev)
                    self.base_pixmap = new_pixmap
                    self.image = image_prev
                    self.ui.Photo.setPixmap(new_pixmap)
                    self.scaleFactor = 1.0
                    # self.ui.fitToWindowAct.setEnabled(True)
                    self.updateActions()
                    print('Prev_file {}:'.format(self.CurrentFileIndex),
                          file_name)
                    self.ui.label.setText('File: {}'.format(file_name))
            except IndexError:
                # the iterator has finished, restart it
                self.CurrentFileIndex = 0
                self.show_prev()
        else:
            # no file list found, select an image file
            self.file_open()

    def original_size(self):
        self.scaleFactor = 1.0
        self.scaleImage(1.0)

    def fitToWindow(self):
        fitToWindow = self.ui.fitToWindowAct.isChecked()
        self.ui.scrollArea.setWidgetResizable(fitToWindow)
        if not fitToWindow:
            self.original_size()
        self.updateActions()

    def updateActions(self):
        self.ui.actionzoom_in.setEnabled(not
                                         self.ui.fitToWindowAct.isChecked())
        self.ui.actionzoom_in.setEnabled(not
                                         self.ui.fitToWindowAct.isChecked())
        self.ui.normalSizeAct.setEnabled(not
                                         self.ui.fitToWindowAct.isChecked())

    def scaleImage(self, factor):
        if self.image is None:
            return
        self.scaleFactor = self.scaleFactor * factor
        old_pixmap = QtGui.QPixmap.fromImage(self.image)
        new_pixmap = old_pixmap.scaledToHeight(
            int(old_pixmap.height() * self.scaleFactor),
            QtCore.Qt.SmoothTransformation)
        self.ui.Photo.setPixmap(new_pixmap)

        if self.base_pixmap is not None:
            self.base_pixmap = new_pixmap

        # Update rod and number display
        self.draw_rods()

        # Disable zoom, if zoomed too much
        self.ui.actionzoom_in.setEnabled(self.scaleFactor < 9.0)
        self.ui.actionzoom_out.setEnabled(self.scaleFactor > 0.11)

    def rod_activated(self, rod_id):
        # A new rod was activated for position editing. Deactivate all others.
        for rod in self.edits:
            if rod.rod_id != rod_id:
                rod.deactivate_rod()
            if rod.rod_id == rod_id:
                rod.set_state(RodState.SELECTED)
        self.draw_rods()

    def check_rod_conflicts(self, set_rod, last_id):
        # Marks any rods that have the same number in RodStyle.CONFLICT
        conflicting = []
        for rod in self.edits:
            if rod.rod_id == set_rod.rod_id:
                conflicting.append(rod)
        if len(conflicting) > 1:
            for rod in conflicting:
                rod.set_state(RodState.CONFLICT)
        self.draw_rods()
        if len(conflicting) > 1:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText(
                f"A conflict was encountered with setting Rod"
                f"#{set_rod.rod_id} (previously Rod#{last_id}). \nHow shall "
                f"this conflict be resolved?")
            btn_switch = msg.addButton("Switch numbers",
                                       QMessageBox.ActionRole)
            btn_return = msg.addButton("Return state", QMessageBox.ActionRole)
            btn_disc_old = msg.addButton("Discard old rod",
                                         QMessageBox.ActionRole)
            btn_keep_both = msg.addButton("Resolve manual",
                                          QMessageBox.ActionRole)
            msg.exec()
            if msg.clickedButton() == btn_switch:
                # Switch the rod numbers
                for rod in conflicting:
                    rod.set_state(RodState.CHANGED)
                    if rod is not set_rod:
                        rod.setText(str(last_id))
                        rod.rod_id = last_id
                    new_line = [int(coord * 10 * self.scaleFactor) for coord in
                                rod.rod_points]
                    self.save_line(QPoint(*new_line[0:2]),
                                   QPoint(*new_line[2:]),
                                   rod.rod_id)
            elif msg.clickedButton() == btn_return:
                # Return to previous state
                if last_id == -1:
                    set_rod.deleteLater()
                    self.edits.remove(set_rod)
                else:
                    set_rod.setText(str(last_id))
                    set_rod.rod_id = last_id
                for rod in conflicting:
                    rod.set_state(RodState.CHANGED)
            elif msg.clickedButton() == btn_disc_old:
                for rod in conflicting:
                    if rod is not set_rod:
                        rod.deleteLater()
                        self.edits.remove(rod)
                        continue
                    rod.set_state(RodState.CHANGED)
                # Delete old and save new
                new_line = [int(coord*10*self.scaleFactor) for coord in
                            set_rod.rod_points]
                self.save_line(QPoint(*new_line[0:2]), QPoint(*new_line[2:]),
                               set_rod.rod_id)
                self.save_line(QPoint(0, 0), QPoint(0, 0), last_id)
            else:
                # Save new rod, delete old position, keep old displayed
                # (user resolves the rest)
                set_rod.set_state(RodState.CHANGED)
                new_line = [int(coord * 10 * self.scaleFactor) for coord in
                            set_rod.rod_points]
                self.save_line(QPoint(*new_line[0:2]), QPoint(*new_line[2:]),
                               set_rod.rod_id)
                self.save_line(QPoint(0, 0), QPoint(0, 0), last_id)
            self.draw_rods()

    def check_exchange(self, drop_position):
        # TODO: check where rod number was dropped and whether an exchange
        #  is needed.
        pass


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_window = RodTrackWindow()
    main_window.show()
    sys.exit(app.exec_())
