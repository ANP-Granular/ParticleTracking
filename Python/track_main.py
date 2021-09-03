import os
import shutil
import sys
import platform

import pandas as pd
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QRadioButton
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QImage

from actionlogger import FileAction, TEMP_DIR, FileActions
from track_ui import Ui_MainWindow
from rodnumberwidget import RodNumberWidget

ICON_PATH = "./resources/icon_main.ico"

HAS_SPLASH = False
try:
    import pyi_splash
    HAS_SPLASH = True
except ModuleNotFoundError:
    # Application not bundled
    HAS_SPLASH = False


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
        self.ui.photo.logger = self.ui.lv_actions_list
        # tracker of the current image that's displayed
        self.CurrentFileIndex = 0
        self.original_data = None   # Holds the original data directory
        self.data_files = self.ui.lv_actions_list.temp_manager.name
        self.data_file_name = 'rods_df_{:s}.csv'
        self.fileList = None
        self.last_color = None
        for rb in self.ui.group_rod_color.findChildren(QRadioButton):
            if rb.isChecked():
                self.last_color = rb.objectName()[3:]

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
            # rb.toggled.connect(lambda state: self.show_overlay() if state
            #                    else None)
            rb.toggled.connect(self.color_change)

        # File actions
        self.ui.pb_load_images.clicked.connect(self.open_image_folder)
        self.ui.action_open.triggered.connect(self.open_image_folder)
        self.ui.le_image_dir.returnPressed.connect(self.open_image_folder)
        self.ui.pb_load_rods.clicked.connect(self.open_rod_folder)
        self.ui.le_rod_dir.returnPressed.connect(self.open_rod_folder)
        self.ui.pb_previous.clicked.connect(
            lambda: self.show_next(direction=-1))
        self.ui.pb_next.clicked.connect(lambda: self.show_next(direction=1))
        self.ui.pb_save_rods.clicked.connect(self.save_changes)

        # Undo
        self.ui.action_revert.triggered.connect(
            self.ui.lv_actions_list.undo_last)
        self.ui.pb_undo.clicked.connect(self.ui.lv_actions_list.undo_last)
        self.ui.photo.request_color_change.connect(self.change_color)

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
            if self.original_data is not None:
                self.show_overlay()

            # Logging
            first_action = FileAction(dirpath, FileActions.LOAD_IMAGES,
                                      len(self.fileList))
            self.ui.lv_actions_list.add_action(first_action)
            second_action = FileAction(file_name, FileActions.OPEN_IMAGE)
            self.ui.lv_actions_list.add_action(second_action)

    def open_rod_folder(self):
        # check for a directory
        ui_dir = self.ui.le_rod_dir.text()
        while True:
            self.original_data = QFileDialog.getExistingDirectory(
                self, 'Choose Folder with position data', ui_dir) + '/'
            if self.original_data == '/':
                self.original_data = None
                return

            if self.original_data is not None:
                # delete old stored files
                for file in os.listdir(self.data_files):
                    os.remove(self.data_files + "/" + file)

                # check for eligible files and de-/activate radio buttons
                eligible_files = False
                rb_colors = [child for child
                             in self.ui.group_rod_color.children() if
                             type(child) is QRadioButton]
                for rb in rb_colors:
                    rb.setEnabled(False)
                    next_color = rb.text().lower()
                    file_found = os.path.exists(
                        self.original_data + self.data_file_name.format(
                            next_color))
                    if file_found:
                        eligible_files = True
                        rb.setEnabled(True)
                        # copy file to temporary storage
                        src_file = self.original_data + \
                            self.data_file_name.format(next_color)
                        dst_file = self.data_files\
                            + "/" + self.data_file_name.format(next_color)
                        shutil.copy2(src=src_file, dst=dst_file)

                if eligible_files:
                    self.ui.le_rod_dir.setText(self.original_data[:-1])
                    self.ui.le_save_dir.setText(self.original_data[:-1] +
                                                "_corrected")
                    this_action = FileAction(self.original_data[:-1],
                                             FileActions.LOAD_RODS)
                    self.ui.lv_actions_list.add_action(this_action)
                    self.show_overlay()
                    return
                else:
                    # no matching file was found
                    msg = QMessageBox()
                    msg.setWindowIcon(QtGui.QIcon(ICON_PATH))
                    msg.setIcon(QMessageBox.Warning)
                    msg.setWindowTitle("Rod Tracker")
                    msg.setText(f"There were no useful files found in: "
                                f"'{self.original_data}'")
                    msg.setStandardButtons(
                        QMessageBox.Retry | QMessageBox.Cancel)
                    user_decision = msg.exec()
                    self.original_data = None
                    if user_decision == QMessageBox.Cancel:
                        # Stop overlaying
                        return
                    else:
                        # Retry folder selection
                        continue

    def show_overlay(self):
        if not self.ui.cb_overlay.isChecked():
            return
        if self.original_data is not None:
            # Check whether image file is loaded
            if self.fileList is None:
                msg = QMessageBox()
                msg.setWindowIcon(QtGui.QIcon(ICON_PATH))
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("Rod Tracker")
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
            msg.setWindowIcon(QtGui.QIcon(ICON_PATH))
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Rod Tracker")
            msg.setText(f"There are no rod position files selected yet. "
                        f"Please select files!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            self.open_rod_folder()

    def load_rods(self):
        # Load rod position data
        # items = ("black", "blue", "green", "purple", "red", "yellow")
        if self.original_data is None:
            return
        col_list = ["particle", "frame", "x1_gp3", "x2_gp3", "y1_gp3",
                    "y2_gp3"]
        filename = (self.fileList[self.CurrentFileIndex])
        file_name = os.path.split(filename)[-1]
        df_part = pd.read_csv(self.data_files + "/" +
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
            ident = RodNumberWidget(self.last_color, self.ui.photo,
                                    str(value), QPoint(0, 0))
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
            self.save_changes(temp_only=True)
            self.clear_screen()
        elif state == 2:
            # activated
            self.show_overlay()

    def show_next(self, direction: int):
        if self.fileList:
            # Unsaved changes handling
            if not self.ui.lv_actions_list.unsaved_changes == []:
                if self.warning_unsaved():
                    self.ui.lv_actions_list.discard_changes()
                else:
                    return
            # Switch images
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

                    # Update information on last action
                    this_action = FileAction(file_name, FileActions.OPEN_IMAGE)
                    self.ui.lv_actions_list.add_action(this_action)

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
            if self.ui.lv_actions_list.unsaved_changes is not []:
                self.save_changes(temp_only=True)
            self.last_color = self.get_selected_color()
            self.show_overlay()

    def save_changes(self, temp_only=False):
        # TODO: move saving to different Thread(, if it still takes too long)
        # Skip, if there are no changes
        if not self.ui.lv_actions_list.unsaved_changes:
            return
        # Save rods to disk
        filename = (self.fileList[self.CurrentFileIndex])
        file_name = os.path.split(filename)[-1]
        tmp_file = self.data_files + "/" + self.data_file_name.format(
            self.last_color)
        df_part = pd.read_csv(tmp_file, index_col=0)
        if self.ui.photo.edits is not None:
            # Skips this, if no rods are displayed
            for rod in self.ui.photo.edits:
                df_part.loc[(df_part.frame == int(file_name[1:4])) &
                            (df_part.particle == rod.rod_id),
                            ["x1_gp3", "y1_gp3", "x2_gp3", "y2_gp3"]] = \
                    rod.rod_points

            df_part.to_csv(tmp_file, index_label="")
        if temp_only:
            # skip permanent saving
            return

        save_dir = self.ui.le_save_dir.text()
        if save_dir == self.ui.le_rod_dir.text():
            msg = QMessageBox()
            msg.setWindowIcon(QtGui.QIcon(ICON_PATH))
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Rod Tracker")
            msg.setText("The saving path points to the original data!"
                        "Do you want to overwrite it?")
            msg.addButton("Overwrite", QMessageBox.ActionRole)
            btn_cancel = msg.addButton("Cancel",
                                       QMessageBox.ActionRole)
            msg.exec()
            if msg.clickedButton() == btn_cancel:
                return

        if not os.path.exists(save_dir):
            os.mkdir(save_dir)
        # TODO: only save the files from the "unsaved" changes
        for file in os.listdir(self.data_files):
            shutil.copy2(self.data_files + "/" + file, save_dir + "/" + file)
            save_file = save_dir + "/" + file
            this_action = FileAction(save_file, FileActions.SAVE)
            self.ui.lv_actions_list.add_action(this_action)

    @staticmethod
    def warning_unsaved() -> bool:
        msg = QMessageBox()
        msg.setWindowIcon(QtGui.QIcon(ICON_PATH))
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Rod Tracker")
        msg.setText("There are unsaved changes!")
        btn_discard = msg.addButton("Discard changes",
                                    QMessageBox.ActionRole)
        btn_cancel = msg.addButton("Cancel",
                                   QMessageBox.ActionRole)
        msg.setDefaultButton(btn_cancel)
        msg.exec()
        if msg.clickedButton() == btn_discard:
            return True
        elif msg.clickedButton() == btn_cancel:
            return False
        else:
            return False

    @QtCore.pyqtSlot(str)
    def change_color(self, to_color: str):
        for rb in self.ui.group_rod_color.findChildren(QRadioButton):
            if rb.objectName()[3:] == to_color:
                # activate the last color
                rb.toggle()


if __name__ == "__main__":
    if HAS_SPLASH:
        pyi_splash.update_text("Updating environment...")

    if not os.path.exists(TEMP_DIR):
        os.mkdir(TEMP_DIR)

    if HAS_SPLASH:
        pyi_splash.update_text("Loading UI...")

    app = QtWidgets.QApplication(sys.argv)
    main_window = RodTrackWindow()

    if HAS_SPLASH:
        # Close the splash screen.
        pyi_splash.close()

    main_window.show()
    sys.exit(app.exec_())
