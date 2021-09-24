import os
import shutil
import sys
import platform
import re
from typing import List

import pandas as pd
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QRadioButton, QScrollArea
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QImage

from actionlogger import FileAction, TEMP_DIR, FileActions, ActionLogger
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
    fileList: List[str] = None
    logger_id: str = "main"
    logger: ActionLogger
    request_undo = QtCore.pyqtSignal(str, name="request_undo")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Adaptations of the UI
        # Adapt menu action shortcuts for Mac
        if platform.system() == "Darwin":
            self.ui.action_zoom_in.setShortcut("Ctrl+=")
            self.ui.action_zoom_out.setShortcut("Ctrl+-")

        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.setFocus()

        # Initialize
        self.cameras = [self.ui.camera_0, self.ui.camera_1]
        self.current_camera = self.cameras[self.ui.camera_tabs.currentIndex()]
        self.view_filelists = [[], []]
        self.file_ids = [[], []]
        self.file_indexes = [0, 0]
        self.current_file_ids = []

        for cam in self.cameras:
            cam.logger = self.ui.lv_actions_list.get_new_logger(cam.cam_id)
            cam.request_color_change.connect(self.change_color)
            self.request_undo.connect(cam.logger.undo_last)
            cam.logger.notify_unsaved.connect(self.tab_has_changes)
            cam.logger.request_saving.connect(self.save_changes)

        # tracker of the current image that's displayed
        self.CurrentFileIndex = 0
        self.original_data = None   # Holds the original data directory
        self.data_files = self.ui.lv_actions_list.temp_manager.name
        self.data_file_name = 'rods_df_{:s}.csv'
        self.last_color = None
        for rb in self.ui.group_rod_color.findChildren(QRadioButton):
            if rb.isChecked():
                self.last_color = rb.objectName()[3:]
        self.logger = self.ui.lv_actions_list.get_new_logger(self.logger_id)
        self.logger.notify_unsaved.connect(self.tab_has_changes)

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
        self.ui.action_save.triggered.connect(self.save_changes)

        # Undo
        self.ui.action_revert.triggered.connect(self.requesting_undo)
        self.ui.pb_undo.clicked.connect(self.requesting_undo)

        # View controls
        self.switch_left = QtWidgets.QShortcut(QtGui.QKeySequence(
            "Ctrl+left"), self)
        self.switch_right = QtWidgets.QShortcut(QtGui.QKeySequence(
            "Ctrl+right"), self)
        self.switch_left.activated.connect(lambda: self.change_view(-1))
        self.switch_right.activated.connect(lambda: self.change_view(1))
        self.ui.camera_tabs.currentChanged.connect(self.view_changed)

    def open_image_folder(self):
        # check for a directory
        ui_dir = self.ui.le_image_dir.text()
        # opens directory to select image
        chosen_file, _ = QFileDialog.getOpenFileName(self, 'Open an image',
                                                     ui_dir,
                                                     'Images (*.png *.jpeg '
                                                     '*.jpg)')
        file_name = os.path.split(chosen_file)[-1]
        file_name = os.path.splitext(file_name)[0]
        if chosen_file:
            # open file as image
            loaded_image = QImage(chosen_file)
            if loaded_image.isNull():
                QMessageBox.information(self, "Image Viewer",
                                        "Cannot load %s." % chosen_file)
                return
            # Directory
            dirpath = os.path.dirname(chosen_file)
            self.fileList = []
            self.current_file_ids = []

            # checks all files for naming convention according to the
            # selected file and append them to a file List
            for idx, f in enumerate(os.listdir(dirpath)):
                f_compare = os.path.splitext(f)[0]
                indx_f = f_compare == file_name
                if indx_f is True:
                    # Set file index
                    self.CurrentFileIndex = idx
                fpath = os.path.join(dirpath, f)
                if os.path.isfile(fpath) and f.endswith(('.png', '.jpg',
                                                         '.jpeg')):
                    # Add all image files to a list
                    self.fileList.append(fpath)
                    self.current_file_ids.append(int(f_compare))

            # Sort according to name / ascending order
            self.fileList.sort()
            self.current_file_ids.sort()
            self.cameras[self.ui.camera_tabs.currentIndex()].image = \
                loaded_image

            # Get camera id for data display
            self.current_camera.cam_id = chosen_file.split("/")[-2]
            curr_idx = self.ui.camera_tabs.currentIndex()
            tab_text = self.ui.camera_tabs.tabText(curr_idx)
            front_text = tab_text.split("(")[0]
            end_text = tab_text.split(")")[-1]
            new_text = front_text + "(" + self.current_camera.cam_id + ")" +\
                end_text
            self.ui.camera_tabs.setTabText(curr_idx, new_text)

            self.fit_to_window()
            self.ui.le_image_dir.setText(dirpath)
            if self.original_data is not None:
                self.show_overlay()

            # Update persistent file lists
            self.view_filelists[self.ui.camera_tabs.currentIndex()] = \
                self.fileList
            self.file_ids[self.ui.camera_tabs.currentIndex()] = \
                self.current_file_ids

            # Logging
            first_action = FileAction(dirpath, FileActions.LOAD_IMAGES,
                                      len(self.fileList),
                                      cam_id=self.current_camera.cam_id,
                                      parent_id="test")
            first_action.parent_id = self.logger_id
            second_action = FileAction(file_name, FileActions.OPEN_IMAGE,
                                       cam_id=self.current_camera.cam_id)
            second_action.parent_id = self.logger_id
            self.logger.add_action(first_action)
            self.logger.add_action(second_action)

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
                rb_color_texts = [btn.text().lower() for btn in rb_colors]
                data_regex = re.compile('rods_df_\w+\.csv')
                group_layout = self.ui.group_rod_color.layout()
                max_col = group_layout.columnCount()-1
                max_row = 1
                if group_layout.itemAtPosition(1, max_col) is not None:
                    # 'Add' a new column as current layout is full
                    max_col += 1
                    max_row = 0

                found_colors = []
                for file in os.listdir(self.original_data):
                    whole_path = os.path.join(self.original_data, file)
                    if not os.path.isfile(whole_path):
                        continue
                    if re.fullmatch(data_regex, file) is not None:
                        eligible_files = True
                        found_color = os.path.splitext(file)[0].split("_")[-1]
                        found_colors.append(found_color)
                        # copy file to temporary storage
                        src_file = os.path.join(self.original_data, file)
                        dst_file = os.path.join(self.data_files, file)
                        shutil.copy2(src=src_file, dst=dst_file)
                        if found_color not in rb_color_texts:
                            # create new radiobutton for this color
                            new_btn = QRadioButton(
                                text=found_color.capitalize())
                            new_btn.setObjectName(f"rb_{found_color}")
                            new_btn.toggled.connect(self.color_change)
                            # retain only 2 rows
                            group_layout.addWidget(new_btn, max_row, max_col)
                            if max_row == 1:
                                max_row = 0
                                max_col += 1
                            else:
                                max_row += 1

                for btn in rb_colors:
                    if btn.text().lower() not in found_colors:
                        group_layout.removeWidget(btn)
                        btn.hide()
                        btn.deleteLater()

                if eligible_files:
                    self.ui.le_rod_dir.setText(self.original_data[:-1])
                    self.ui.le_save_dir.setText(self.original_data[:-1] +
                                                "_corrected")
                    this_action = FileAction(self.original_data[:-1],
                                             FileActions.LOAD_RODS)
                    this_action.parent_id = self.logger_id
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
        if self.original_data is None or not self.ui.cb_overlay.isChecked():
            return
        if self.current_camera.image is None:
            return
        cam_id = self.current_camera.cam_id
        col_list = ["particle", "frame", f"x1_{cam_id}",
                    f"x2_{cam_id}", f"y1_{cam_id}",
                    f"y2_{cam_id}"]

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
            x1 = df_part2[f'x1_{cam_id}'][ind_rod]
            x2 = df_part2[f'x2_{cam_id}'][ind_rod]
            y1 = df_part2[f'y1_{cam_id}'][ind_rod]
            y2 = df_part2[f'y2_{cam_id}'][ind_rod]
            # Add rods
            ident = RodNumberWidget(self.last_color, self.current_camera,
                                    str(value), QPoint(0, 0))
            ident.rod_id = value
            ident.rod_points = [x1, y1, x2, y2]
            ident.setObjectName(f"rn_{ind_rod}")
            new_rods.append(ident)
        self.current_camera.edits = new_rods
        if not new_rods:
            self.statusBar().showMessage("No rod data available for this "
                                         "image.", 5000)

    def clear_screen(self):
        self.cameras[self.ui.camera_tabs.currentIndex()].clear_screen()

    def cb_changed(self, state):
        if state == 0:
            # deactivated
            self.save_changes(temp_only=True)
            self.clear_screen()
        elif state == 2:
            # activated
            self.show_overlay()

    def show_next(self, direction: int):
        if direction == 0:
            # No change necessary
            return
        if self.fileList:
            # Unsaved changes handling
            if not self.current_camera.logger.unsaved_changes == []:
                if self.warning_unsaved():
                    self.current_camera.logger.discard_changes()
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
                    # The file is not a valid image, remove it from the list
                    # and try to load the next one
                    self.ui.statusbar.showMessage(f"The image {file_name} is "
                                                  f"corrupted and therefore "
                                                  f"excluded.", 4000)
                    self.fileList.remove(filename)
                    self.show_next(direction)
                else:
                    self.current_camera.image = image_next
                    if self.ui.action_persistent_view.isChecked():
                        self.load_rods()
                    else:
                        del self.current_camera.edits
                        self.current_camera.scale_factor = 1
                    self.file_indexes[self.ui.camera_tabs.currentIndex()] = \
                        self.CurrentFileIndex
                    # Update information on last action
                    this_action = FileAction(file_name,
                                             FileActions.OPEN_IMAGE,
                                             cam_id=self.current_camera.cam_id)
                    this_action.parent_id = self.logger_id
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
        self.current_camera.scale_factor = 1
        self.ui.action_zoom_in.setEnabled(True)
        self.ui.action_zoom_out.setEnabled(True)

    def fit_to_window(self):
        current_sa = self.findChild(QScrollArea,
                                    f"sa_camera_"
                                    f"{self.ui.camera_tabs.currentIndex()}")
        to_size = current_sa.size()
        to_size = QtCore.QSize(to_size.width()-20, to_size.height()-20)
        self.current_camera.scale_to_size(to_size)

    def scale_image(self, factor):
        new_zoom = self.current_camera.scale_factor * factor
        self.current_camera.scale_factor = new_zoom
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

    def save_changes(self, temp_only=False, current_only=False):
        # TODO: extend saving to include all frames that were changed in the
        #  temp_only=False condition
        # TODO: move saving to different Thread(, if it still takes too long)

        # Skip, if there are no changes
        if not self.ui.lv_actions_list.unsaved_changes:
            return
        # Save rods to disk
        for cam_idx in range(len(self.cameras)):
            try:
                filename = self.view_filelists[cam_idx][
                    self.file_indexes[cam_idx]]
            except IndexError:
                # No images loaded for this camera yet.
                continue
            file_name = os.path.split(filename)[-1]
            tmp_file = self.data_files + "/" + self.data_file_name.format(
                self.last_color)
            df_part = pd.read_csv(tmp_file, index_col=0)
            cam = self.cameras[cam_idx]
            if cam.edits is not None:
                # Skips this, if no rods are displayed
                cam_id = cam.cam_id
                for rod in cam.edits:
                    df_part.loc[(df_part.frame == int(file_name[1:4])) &
                                (df_part.particle == rod.rod_id),
                                [f"x1_{cam_id}", f"y1_{cam_id}",
                                 f"x2_{cam_id}", f"y2_{cam_id}"]] = \
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
            this_action.parent_id = self.logger_id
            self.ui.lv_actions_list.add_action(this_action)

        # notify loggers that everything was saved
        for cam in self.cameras:
            cam.logger.actions_saved()

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

    def change_view(self, direction):
        old_idx = self.ui.camera_tabs.currentIndex()
        new_idx = old_idx + direction
        if new_idx > 1:
            new_idx = 0
        elif new_idx < 0:
            new_idx = 1
        self.ui.camera_tabs.setCurrentIndex(new_idx)

    @QtCore.pyqtSlot(int)
    def view_changed(self, new_idx):
        self.save_changes(temp_only=True)
        # Ensure the image/frame number is consistent over views
        index_diff = 0
        if self.ui.action_persistent_view.isChecked():
            if self.current_file_ids:
                current_id = self.current_file_ids[self.CurrentFileIndex]
                try:
                    # Find the new camera's image corresponding to the old
                    # camera's image
                    new_id_idx = self.file_ids[new_idx].index(current_id)
                    index_diff = new_id_idx - self.file_indexes[new_idx]
                except ValueError:
                    # Image not found
                    self.cameras[new_idx].setPixmap(QtGui.QPixmap(ICON_PATH))
                    self.ui.statusbar.showMessage(f"No image with ID"
                                                  f":{current_id} found for "
                                                  f"this view.", 4000)

        self.CurrentFileIndex = self.file_indexes[new_idx]
        self.fileList = self.view_filelists[new_idx]
        self.current_file_ids = self.file_ids[new_idx]
        self.current_camera = self.cameras[new_idx]
        # Loads a new image, if necessary
        self.show_next(index_diff)
        try:
            new_path = os.path.split(self.fileList[0])[0]
        except IndexError:
            new_path = ""
        self.ui.le_image_dir.setText(new_path)

        if self.ui.cb_overlay.isChecked():
            # ensure that rods are loaded
            self.load_rods()

    def requesting_undo(self):
        self.request_undo.emit(self.current_camera.cam_id)

    @QtCore.pyqtSlot(bool)
    def tab_has_changes(self, has_changes: bool) -> None:
        tab_idx = self.ui.camera_tabs.currentIndex()
        if has_changes:
            new_text = self.ui.camera_tabs.tabText(tab_idx) + "*"
        else:
            new_text = self.ui.camera_tabs.tabText(tab_idx)[0:-1]
        self.ui.camera_tabs.setTabText(tab_idx, new_text)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        super().resizeEvent(a0)
        # get the screen's resolution the application is displayed on
        # self.screen().size()
        # adapt margins to screen resolution

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        # Unsaved changes handling
        if not self.ui.lv_actions_list.unsaved_changes == []:
            msg = QMessageBox()
            msg.setWindowIcon(QtGui.QIcon(ICON_PATH))
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Rod Tracker")
            msg.setText("There are unsaved changes!")
            btn_save = msg.addButton("Save", QMessageBox.ActionRole)
            msg.addButton("Discard", QMessageBox.ActionRole)
            btn_cancel = msg.addButton("Cancel",
                                       QMessageBox.ActionRole)
            msg.setDefaultButton(btn_save)
            msg.exec()
            if msg.clickedButton() == btn_save:
                self.save_changes(temp_only=False)
                a0.accept()
                pass
            elif msg.clickedButton() == btn_cancel:
                a0.ignore()
            else:
                # discards changes and proceeds with closing
                a0.accept()
        else:
            a0.accept()


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
