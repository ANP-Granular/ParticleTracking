import os
import sys
import platform
import pandas as pd
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QInputDialog
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QImage
from track_ui import Ui_MainWindow
from rodnumberwidget import RodNumberWidget


class RodTrackWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Adapt menu action shortcuts for Mac
        if platform.system() == "Darwin":
            self.ui.actionzoom_in.setShortcut("Ctrl+=")
            self.ui.actionzoom_out.setShortcut("Ctrl+-")

        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.setFocus()
        # Initialize
        # tracker of the current image that's displayed
        self.CurrentFileIndex = 0
        self.data_files = None
        self.data_file_name = 'rods_df_{:s}.csv'
        self.color = "black"
        self.fileList = None
        # self.track = True

        # Signal to activate actions
        self.ui.pushprevious.clicked.connect(
            lambda: self.show_next(direction=-1))
        self.ui.pushnext.clicked.connect(lambda: self.show_next(direction=1))
        self.ui.overlay.clicked.connect(self.show_overlay)
        # self.ui.RodNumber.clicked.connect(lambda: self.show_overlay(
        #     with_number=True))
        # self.ui.ClearSave.clicked.connect(self.clear_screen)
        self.ui.actionzoom_in.triggered.connect(lambda: self.scale_image(
            factor=1.25))
        self.ui.actionzoom_out.triggered.connect(lambda: self.scale_image(
            factor=0.8))
        self.ui.actionopen.triggered.connect(self.file_open)
        self.ui.normalSizeAct.triggered.connect(self.original_size)
        self.ui.action_fit_to_window.triggered.connect(self.fit_to_window)
        self.ui.Photo.line_to_save[RodNumberWidget].connect(self.save_line)
        self.ui.Photo.line_to_save[RodNumberWidget, bool].connect(
            self.save_line)

    def file_open(self):
        # opens directory to select image
        chosen_file, _ = QFileDialog.getOpenFileName(self, 'Open an image', '',
                                                     'Images (*.png *.jpeg '
                                                     '*.jpg)')
        file_name = os.path.split(chosen_file)[-1]
        # File name without extension
        file_name = os.path.splitext(file_name)[0]
        print('File name:', file_name)
        if chosen_file:
            # open file as image
            loaded_image = QImage(chosen_file)
            if loaded_image.isNull():
                QMessageBox.information(self, "Image Viewer",
                                        "Cannot load %s." % chosen_file)
                return
            # Directory
            dirpath = os.path.dirname(chosen_file)
            print('Dir_name:', dirpath)
            self.fileList = []

            # checks all files for naming convention according to the
            # selected file and append them to a file List
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
            self.ui.Photo.image = loaded_image
            self.fit_to_window()

            # Logging
            print('Num of items in list:', len(self.fileList))
            print('Open_file {}:'.format(self.CurrentFileIndex), file_name)
            self.ui.label.setText('File opened: {}'.format(file_name))

    def show_overlay(self, with_number=False):
        items = ("black", "blue", "green", "purple", "red", "yellow")
        # col_list = ["particle", "frame", "x1_gp3", "x2_gp3", "y1_gp3",
        #             "y2_gp3"]
        while True:
            # TODO: Check whether image file is loaded
            if self.data_files is not None:
                item, ok = QInputDialog.getItem(self,
                                                "Select a color to display",
                                                "list of colors", items, 0,
                                                False)
                if not ok:
                    return
                else:
                    self.color = item
                    file_found = os.path.exists(
                        self.data_files + self.data_file_name.format(item))
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
        # items = ("black", "blue", "green", "purple", "red", "yellow")
        if self.data_files is None:
            return
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

        new_rods = []
        for ind_rod, value in enumerate(df_part2['particle']):
            x1 = df_part2['x1_gp3'][ind_rod]
            x2 = df_part2['x2_gp3'][ind_rod]
            y1 = df_part2['y1_gp3'][ind_rod]
            y2 = df_part2['y2_gp3'][ind_rod]
            # Add rods
            ident = RodNumberWidget(self.ui.Photo, str(value), QPoint(0, 0))
            ident.rod_id = value
            ident.rod_points = [x1, y1, x2, y2]
            ident.setObjectName(f"rn_{ind_rod}")
            new_rods.append(ident)
        self.ui.Photo.edits = new_rods

    def clear_screen(self):
        self.ui.Photo.clear_screen()
        self.update_actions()

    @QtCore.pyqtSlot(RodNumberWidget)
    @QtCore.pyqtSlot(RodNumberWidget, bool)
    def save_line(self, rod: RodNumberWidget, delete_after=False):
        # Save rod to disk
        filename = (self.fileList[self.CurrentFileIndex])
        file_name = os.path.split(filename)[-1]
        df_part = pd.read_csv(self.data_files + self.data_file_name.format(
            self.color), index_col=0)
        df_part.loc[(df_part.frame == int(file_name[1:4])) &
                    (df_part.particle == rod.rod_id), "x1_gp3"] = \
            rod.rod_points[0]
        df_part.loc[(df_part.frame == int(file_name[1:4])) &
                    (df_part.particle == rod.rod_id), "x2_gp3"] = \
            rod.rod_points[2]
        df_part.loc[(df_part.frame == int(file_name[1:4])) &
                    (df_part.particle == rod.rod_id), "y1_gp3"] = \
            rod.rod_points[1]
        df_part.loc[(df_part.frame == int(file_name[1:4])) &
                    (df_part.particle == rod.rod_id), "y2_gp3"] = \
            rod.rod_points[3]
        df_part.to_csv(self.data_files + self.data_file_name.format(
            self.color), index_label="")
        if delete_after:
            rod.deleteLater()

    def show_next(self, direction: int):
        if self.fileList:
            try:
                self.CurrentFileIndex += direction
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
                    self.show_next(direction)
                else:
                    self.ui.Photo.image = image_next
                    if self.ui.action_persistent_view.isChecked():
                        self.load_rods()
                    else:
                        del self.ui.Photo.edits
                        self.ui.Photo.scale_factor = 1

                    print('Next_file {}:'.format(self.CurrentFileIndex),
                          file_name)
                    # Update information on last action
                    self.ui.label.setText('File: {}'.format(file_name))

            except IndexError:
                # the iterator has finished, restart it
                if direction > 0:
                    self.CurrentFileIndex = -1
                else:
                    self.CurrentFileIndex = 0
                self.show_next(direction)
        else:
            # no file list found, load an image
            self.file_open()

    def original_size(self):
        self.ui.Photo.scale_factor = 1
        self.ui.actionzoom_in.setEnabled(True)
        self.ui.actionzoom_out.setEnabled(True)

    def fit_to_window(self):
        to_size = self.ui.scrollArea_3.size()
        to_size = QtCore.QSize(to_size.width()-20, to_size.height()-20)
        self.ui.Photo.scale_to_size(to_size)

    def update_actions(self):
        self.ui.actionzoom_in.setEnabled(
            not self.ui.action_fit_to_window.isChecked())
        self.ui.actionzoom_in.setEnabled(
            not self.ui.action_fit_to_window.isChecked())
        self.ui.normalSizeAct.setEnabled(
            not self.ui.action_fit_to_window.isChecked())

    def scale_image(self, factor):
        new_zoom = self.ui.Photo.scale_factor * factor
        self.ui.Photo.scale_factor = new_zoom
        # Disable zoom, if zoomed too much
        self.ui.actionzoom_in.setEnabled(new_zoom < 9.0)
        self.ui.actionzoom_out.setEnabled(new_zoom > 0.11)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_window = RodTrackWindow()
    main_window.show()
    sys.exit(app.exec_())
