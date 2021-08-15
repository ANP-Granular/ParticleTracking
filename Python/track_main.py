import os
import sys
import platform
import pandas as pd
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QRadioButton
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
            self.ui.action_zoom_in.setShortcut("Ctrl+=")
            self.ui.action_zoom_out.setShortcut("Ctrl+-")

        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.setFocus()
        # Initialize
        # tracker of the current image that's displayed
        self.CurrentFileIndex = 0
        self.data_files = None
        self.data_file_name = 'rods_df_{:s}.csv'
        self.fileList = None

        # Connect signals

        # Viewing actions
        self.ui.action_zoom_in.triggered.connect(lambda: self.scale_image(
            factor=1.25))
        self.ui.action_zoom_out.triggered.connect(lambda: self.scale_image(
            factor=0.8))
        self.ui.action_original_size.triggered.connect(self.original_size)
        self.ui.action_fit_to_window.triggered.connect(self.fit_to_window)
        self.ui.cb_overlay.stateChanged.connect(self.cb_changed)
        for rb in self.ui.group_rod_color.findChildren(QRadioButton):
            rb.toggled.connect(lambda state: self.show_overlay() if state
                               else None)

        # File actions
        self.ui.pb_load_images.clicked.connect(self.open_image_folder)
        self.ui.action_open.triggered.connect(self.open_image_folder)
        self.ui.le_image_dir.returnPressed.connect(self.open_image_folder)
        self.ui.pb_load_rods.clicked.connect(self.open_rod_folder)
        self.ui.le_rod_dir.returnPressed.connect(self.open_rod_folder)
        self.ui.pb_previous.clicked.connect(
            lambda: self.show_next(direction=-1))
        self.ui.pb_next.clicked.connect(lambda: self.show_next(direction=1))

        # Internal/Rod signals & actions
        self.ui.photo.line_to_save[RodNumberWidget].connect(self.save_line)
        self.ui.photo.line_to_save[RodNumberWidget, bool].connect(
            self.save_line)

    def open_image_folder(self):
        # check for a directory
        ui_dir = self.ui.le_image_dir.text()
        # opens directory to select image
        chosen_file, _ = QFileDialog.getOpenFileName(self, 'Open an image',
                                                     ui_dir,
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
            self.ui.photo.image = loaded_image
            self.fit_to_window()
            self.ui.le_image_dir.setText(dirpath)
            if self.data_files is not None:
                self.show_overlay()

            # Logging
            print('Num of items in list:', len(self.fileList))
            print('Open_file {}:'.format(self.CurrentFileIndex), file_name)
            # self.ui.label.setText('File opened: {}'.format(file_name))

    def open_rod_folder(self):
        # check for a directory
        ui_dir = self.ui.le_rod_dir.text()
        while True:
            self.data_files = QFileDialog.getExistingDirectory(
                self, 'Choose Folder with position data', ui_dir) + '/'
            if self.data_files == '/':
                self.data_files = None
                return

            if self.data_files is not None:
                # check for eligable files and de-/activate radio buttons
                eligible_files = False
                rb_colors = [child for child
                             in self.ui.group_rod_color.children() if
                             type(child) is QRadioButton]
                for rb in rb_colors:
                    rb.setEnabled(False)
                    next_color = rb.text().lower()
                    file_found = os.path.exists(
                        self.data_files + self.data_file_name.format(
                            next_color))
                    if file_found:
                        eligible_files = True
                        rb.setEnabled(True)

                if eligible_files:
                    self.ui.le_rod_dir.setText(self.data_files[:-1])
                    self.ui.le_save_dir.setText(self.data_files[:-1] +
                                                "_corrected")
                    self.show_overlay()
                    return
                else:
                    # no matching file was found
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Warning)
                    msg.setWindowTitle("Rod Tracking")
                    msg.setText(f"There were no useful files found in: "
                                f"'{self.data_files}'")
                    msg.setStandardButtons(
                        QMessageBox.Retry | QMessageBox.Cancel)
                    user_decision = msg.exec()
                    self.data_files = None
                    if user_decision == QMessageBox.Cancel:
                        # Stop overlaying
                        return
                    else:
                        # Retry folder selection
                        continue

    def show_overlay(self):
        if not self.ui.cb_overlay.isChecked():
            return
        if self.data_files is not None:
            # Check whether image file is loaded
            if self.fileList is None:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("Rod Tracking")
                msg.setText(f"There is no image loaded yet. "
                            f"Please select an image before rods can be "
                            f"displayed.")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec()
                return
            else:
                self.load_rods()
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Rod Tracking")
            msg.setText(f"There are no rod position files selected yet. "
                        f"Please select files!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            self.open_rod_folder()

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
                                  self.get_selected_color()),
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
            ident = RodNumberWidget(self.ui.photo, str(value), QPoint(0, 0))
            ident.rod_id = value
            ident.rod_points = [x1, y1, x2, y2]
            ident.setObjectName(f"rn_{ind_rod}")
            new_rods.append(ident)
        self.ui.photo.edits = new_rods

    def clear_screen(self):
        self.ui.photo.clear_screen()

    def cb_changed(self, state):
        if state == 0:
            # deactivated
            self.clear_screen()
        elif state == 2:
            # activated
            self.show_overlay()

    @QtCore.pyqtSlot(RodNumberWidget)
    @QtCore.pyqtSlot(RodNumberWidget, bool)
    def save_line(self, rod: RodNumberWidget, delete_after=False):
        # Save rod to disk
        filename = (self.fileList[self.CurrentFileIndex])
        file_name = os.path.split(filename)[-1]
        df_part = pd.read_csv(self.data_files + self.data_file_name.format(
            self.get_selected_color()), index_col=0)
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
            self.get_selected_color()), index_label="")
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
                    self.ui.photo.image = image_next
                    if self.ui.action_persistent_view.isChecked():
                        self.load_rods()
                    else:
                        del self.ui.photo.edits
                        self.ui.photo.scale_factor = 1

                    print('Next_file {}:'.format(self.CurrentFileIndex),
                          file_name)
                    # Update information on last action
                    # self.ui.label.setText('File: {}'.format(file_name))

            except IndexError:
                # the iterator has finished, restart it
                if direction > 0:
                    self.CurrentFileIndex = -1
                else:
                    self.CurrentFileIndex = 0
                self.show_next(direction)
        else:
            # no file list found, load an image
            self.open_image_folder()

    def original_size(self):
        self.ui.photo.scale_factor = 1
        self.ui.action_zoom_in.setEnabled(True)
        self.ui.action_zoom_out.setEnabled(True)

    def fit_to_window(self):
        to_size = self.ui.sa_photo.size()
        to_size = QtCore.QSize(to_size.width()-20, to_size.height()-20)
        self.ui.photo.scale_to_size(to_size)

    def scale_image(self, factor):
        new_zoom = self.ui.photo.scale_factor * factor
        self.ui.photo.scale_factor = new_zoom
        # Disable zoom, if zoomed too much
        self.ui.action_zoom_in.setEnabled(new_zoom < 9.0)
        self.ui.action_zoom_out.setEnabled(new_zoom > 0.11)

    def get_selected_color(self):
        for rb in self.ui.group_rod_color.findChildren(QRadioButton):
            if rb.isChecked():
                return rb.objectName()[3:]

    def color_change(self, state):
        if state:
            self.show_overlay()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_window = RodTrackWindow()
    main_window.show()
    sys.exit(app.exec_())
