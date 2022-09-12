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

import os
import shutil
import platform
from typing import Iterable, List

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QRadioButton, \
    QScrollArea, QTreeWidgetItem, QAbstractItemView
from PyQt5.QtGui import QImage, QWheelEvent

from Python.backend import settings as se, logger as lg, \
    data_operations as d_ops, file_operations as f_ops
from Python.ui import rodnumberwidget as rn, mainwindow_layout as mw_l, dialogs
import Python.backend.parallelism as pl

ICON_PATH = "./resources/icon_main.ico"


class RodTrackWindow(QtWidgets.QMainWindow):
    """The main window for the Rod Tracker application.

    This class handles most of the interaction between the user and the GUI
    elements of the Rod Tracker application. Especially most interactions
    that trigger file access are located here. Also most custom interactions
    between visual elements are setup or managed here.

    Parameters
    ----------
    *args : iterable
        Positional arguments for the QMainWindow superclass.
    **kwargs : dict
        Keyword arguments for the QMainWindow superclass.

    Attributes
    ----------
    ui : Ui_MainWindow
        The GUI main window object, that contains all other visual objects.
    cameras : List[RodImageWidget]
        A copy of all image display objects (views) from the GUI main window.
    current_camera : RodImageWidget
        The currently selected/displayed image display object. This is
        automatically updated when the user switches between the different
        tabs.
    view_filelists : List[List[str]]
        A list of all selected image files for all camera views.
    fileList : List[str]
        A list of all selected image files for the `current_camera` view.
    file_ids : List[List[int]]
        A list of all selected image/frame numbers for all camera views.
    current_file_ids : List[str]
        A list of all selected image/frame numbers for the `current_camera`
        view.
    file_indexes : List[int]
        The index of the currently loaded image file for all camera views.
    CurrentFileIndex : int
        The index of the currently loaded image file for the
        `current_camera` view.
    original_data : str
        The full path to folder containing the rod position data files.
    data_files : str
        The full path to the temporary folder containing the working copies
        of the files in the `original_data` directory. These files are only
        available during runtime of the program and all changes are stored
        there before final saving by the user.
    data_file_name : str
        The template string to match file names of data file candidates in a
        user-selected folder.
    last_color : str
        The color that is currently selected in the GUI and therefore used
        for data display.
    logger : ActionLogger
        A logger object keeping track of users' actions performed on the
        main window, i.e. data and image loading and saving.
    logger_id : str
        The ID provided to the logger for accountability of the actions in
        the GUI.

    Signals
    -------
    request_undo(str)
        Is emitted when the user wants to revert an action. The payload is
        the ID of the widget on which the last action shall be reverted.
    request_redo(str)
        Is emitted when the user wants to redo a previously reverted action.
        The payload is the ID of the widget on which the last action shall
        be redone.

    Slots
    -----
    cb_changed(int)
    color_change(bool)
    change_color(str)
    view_changed(int)
    tab_has_changes(bool)

    """
    background_tasks = []
    fileList: List[str] = None
    logger_id: str = "main"
    logger: lg.ActionLogger
    request_undo = QtCore.pyqtSignal(str, name="request_undo")
    request_redo = QtCore.pyqtSignal(str, name="request_redo")
    _current_file_ids: list = []
    _CurrentFileIndex: int = 0
    _allow_overwrite: bool = False
    _rod_incr: float = 1.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = mw_l.Ui_MainWindow()
        self.ui.setupUi(self)

        # Adaptations of the UI
        self.ui.tv_rods.header().setDefaultSectionSize(150)
        self.ui.tv_rods.header().setMinimumSectionSize(125)
        # Adapt menu action shortcuts for Mac
        if platform.system() == "Darwin":
            self.ui.action_zoom_in.setShortcut("Ctrl+=")
            self.ui.action_zoom_out.setShortcut("Ctrl+-")

        # Set maximum button/checkbox sizes to avoid text clipping
        pb_load_txt = self.ui.pb_load_images.text()
        pb_load_size = self.ui.pb_load_images.fontMetrics().width(
            pb_load_txt)
        pb_rod_txt = self.ui.pb_load_rods.text()
        pb_rod_size = self.ui.pb_load_rods.fontMetrics().width(
            pb_rod_txt)
        max_width = pb_rod_size if pb_rod_size > pb_load_size else pb_load_size
        self.ui.pb_load_images.setMaximumWidth(int(2 * max_width))
        self.ui.pb_load_rods.setMaximumWidth(int(2 * max_width))
        cb_ov_txt = self.ui.cb_overlay.text()
        cb_ov_size = self.ui.cb_overlay.fontMetrics().width(cb_ov_txt)
        self.ui.cb_overlay.setMaximumWidth(int(2 * cb_ov_size))

        # Set possible inputs for rod selection field
        self.ui.le_disp_one.setInputMask("99")
        self.ui.le_disp_one.setText("00")

        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.setFocus()

        # Initialize
        self.cameras = [self.ui.camera_0, self.ui.camera_1]
        self.current_camera = self.cameras[self.ui.camera_tabs.currentIndex()]
        self.view_filelists = [[], []]
        self.file_ids = [[], []]
        self.file_indexes = [0, 0]

        for cam in self.cameras:
            cam.logger = self.ui.lv_actions_list.get_new_logger(cam.cam_id)

        self.original_data = None   # Holds the original data directory
        self.data_files = self.ui.lv_actions_list.temp_manager.name
        self.data_file_name = 'rods_df_{:s}.csv'
        self.last_color = None
        self.rod_info = None
        for rb in self.ui.group_rod_color.findChildren(QRadioButton):
            if rb.isChecked():
                self.last_color = rb.objectName()[3:]
        self.logger = self.ui.lv_actions_list.get_new_logger(self.logger_id)
        self.ui.sa_camera_0.verticalScrollBar().installEventFilter(self)
        self.ui.sa_camera_1.verticalScrollBar().installEventFilter(self)
        self.switch_left = QtWidgets.QShortcut(QtGui.QKeySequence(
            "Ctrl+tab"), self)
        self.switch_right = QtWidgets.QShortcut(QtGui.QKeySequence(
            "tab"), self)
        self.ui.slider_frames.setMinimum(0)
        self.ui.slider_frames.setMaximum(1)
        self.settings = se.Settings()

        self.connect_signals()
        self.settings.send_settings()

    def connect_signals(self):
        # Opening files
        self.ui.pb_load_images.clicked.connect(self.open_image_folder)
        self.ui.action_open.triggered.connect(self.open_image_folder)
        self.ui.le_image_dir.returnPressed.connect(self.open_image_folder)
        self.ui.action_open_rods.triggered.connect(self.open_rod_folder)
        self.ui.pb_load_rods.clicked.connect(self.open_rod_folder)
        self.ui.le_rod_dir.returnPressed.connect(self.open_rod_folder)

        # Saving
        self.ui.pb_save_rods.clicked.connect(self.save_changes)
        self.ui.action_save.triggered.connect(self.save_changes)

        # Undo/Redo
        self.ui.action_revert.triggered.connect(self.requesting_undo)
        self.ui.pb_undo.clicked.connect(self.requesting_undo)
        self.ui.action_redo.triggered.connect(self.requesting_redo)

        # View controls
        self.ui.action_zoom_in.triggered.connect(lambda: self.scale_image(
            factor=1.25))
        self.ui.action_zoom_out.triggered.connect(lambda: self.scale_image(
            factor=0.8))
        self.ui.action_original_size.triggered.connect(self.original_size)
        self.ui.action_fit_to_window.triggered.connect(self.fit_to_window)
        self.ui.cb_overlay.stateChanged.connect(self.cb_changed)

        # Displayed data
        self.ui.action_cleanup.triggered.connect(self.clean_data)
        for rb in self.ui.group_rod_color.findChildren(QRadioButton):
            rb.toggled.connect(self.color_change)
        self.ui.pb_previous.clicked.connect(
            lambda: self.show_next(direction=-1))
        self.ui.pb_next.clicked.connect(lambda: self.show_next(direction=1))
        self.switch_left.activated.connect(lambda: self.change_view(-1))
        self.switch_right.activated.connect(lambda: self.change_view(1))
        self.ui.camera_tabs.currentChanged.connect(self.view_changed)
        self.ui.slider_frames.sliderMoved.connect(self.slider_moved)
        self.ui.tv_rods.itemClicked.connect(self.tree_selection)

        # Display methods
        self.ui.le_disp_one.textChanged.connect(self.display_rod_changed)
        for rb in self.ui.group_disp_method.findChildren(QRadioButton):
            rb.toggled.connect(self.display_method_change)

        # Settings
        self.settings.settings_changed.connect(self.update_settings)
        self.settings.settings_changed.connect(
            rn.RodNumberWidget.update_defaults)
        self.ui.action_preferences.triggered.connect(
            lambda: self.settings.show_dialog(self))

        # Logging
        self.logger.notify_unsaved.connect(self.tab_has_changes)
        self.logger.data_changed.connect(self.catch_data)

        # Cameras
        for cam in self.cameras:
            cam.request_color_change.connect(self.change_color)
            cam.request_frame_change.connect(self.change_frame)
            cam.normal_frame_change.connect(self.show_next)
            cam.logger.notify_unsaved.connect(self.tab_has_changes)
            cam.logger.request_saving.connect(self.save_changes)
            cam.logger.data_changed.connect(self.catch_data)
            cam.request_new_rod.connect(self.create_new_rod)
            cam.number_switches[lg.NumberChangeActions, int, int].connect(
                self.catch_number_switch)
            cam.number_switches[
                lg.NumberChangeActions, int, int, str, int, str, bool].connect(
                self.catch_number_switch)
            self.request_undo.connect(cam.logger.undo_last)
            self.request_redo.connect(cam.logger.redo_last)
            self.settings.settings_changed.connect(cam.update_settings)
        self.ui.action_shorten_displayed.triggered.connect(
            lambda: self.current_camera.adjust_rod_length(
                -self._rod_incr, False))
        self.ui.action_lengthen_displayed.triggered.connect(
            lambda: self.current_camera.adjust_rod_length(
                self._rod_incr, False))
        self.ui.action_shorten_selected.triggered.connect(
            lambda: self.current_camera.adjust_rod_length(
                -self._rod_incr, True))
        self.ui.action_lengthen_selected.triggered.connect(
            lambda: self.current_camera.adjust_rod_length(
                self._rod_incr, True))

        # Help
        self.ui.action_docs.triggered.connect(lambda: dialogs.show_readme(
            self))
        self.ui.action_about.triggered.connect(lambda: dialogs.show_about(
            self))
        self.ui.action_about_qt.triggered.connect(
            lambda: QMessageBox.aboutQt(self, "RodTracker"))
        self.ui.action_logs.triggered.connect(lg.open_logs)

    @property
    def current_file_index(self):
        return self._CurrentFileIndex

    @current_file_index.setter
    def current_file_index(self, new_idx: int):
        self._CurrentFileIndex = new_idx
        try:
            self.ui.le_frame_disp.setText(f"Frame: "
                                          f"{self._current_file_ids[new_idx]}")
        except IndexError:
            self.ui.le_frame_disp.setText("Frame: ???")

    @property
    def current_file_ids(self):
        return self._current_file_ids

    @current_file_ids.setter
    def current_file_ids(self, new_ids):
        self._current_file_ids = new_ids
        self.ui.slider_frames.setMaximum(len(new_ids) - 1)
        self.ui.slider_frames.setMinimum(0)
        try:
            self.ui.le_frame_disp.setText(
                f"Frame: {self._current_file_ids[self.current_file_index]}")
            self.ui.slider_frames.setSliderPosition(self.current_file_index)
        except IndexError:
            self.ui.le_frame_disp.setText("Frame: ???")

    @QtCore.pyqtSlot(QTreeWidgetItem, int)
    def tree_selection(self, item: QTreeWidgetItem, col: int):
        if not item.childCount():
            # change camera
            # TODO
            # change color
            color = item.parent().text(0)
            self.change_color(color)
            # change frame
            frame = int(item.parent().parent().text(0)[7:])
            self.change_frame(frame)
            # activate clicked rod
            if self.current_camera.edits:
                selected_rod = int(item.text(0)[4:6])
                self.current_camera.rod_activated(selected_rod)
        return

    def update_tree(self, new_data: dict, no_gen=False):
        """Update the "seen" status in the displayed rod data tree.
        Skip updating of the tree by using no_gen=True."""
        header = self.ui.tv_rods.headerItem()
        headings = []
        for i in range(1, header.columnCount()):
            headings.append(header.text(i))
        insert_idx = headings.index(new_data["cam_id"])
        self.rod_info[new_data["frame"]][new_data["color"]][new_data[
            "rod_id"]][insert_idx] = "seen" if new_data["seen"] else "unseen"
        if no_gen:
            return
        self.generate_tree()

    def update_tree_folding(self):
        """Updates the folding of the tree view.

        The tree view is updated in synchrony with the UI switching frames
        and colors. The corresponding portion of the tree is expanded and
        moved into view.
        """
        self.ui.tv_rods.collapseAll()
        root = self.ui.tv_rods.invisibleRootItem()
        frames = [int(root.child(i).text(0)[7:])
                  for i in range(root.childCount())]
        try:
            expand_frame = root.child(frames.index(self.logger.frame))
        except ValueError:
            # frame not found in list -> unable to update the list
            return
        colors = [expand_frame.child(i).text(0)
                  for i in range(expand_frame.childCount())]

        try:
            to_expand = colors.index(self.get_selected_color())
        except ValueError:
            to_expand = 0
        expand_color = expand_frame.child(to_expand)

        self.ui.tv_rods.expandItem(expand_frame)
        self.ui.tv_rods.expandItem(expand_color)
        self.ui.tv_rods.scrollToItem(expand_frame,
                                     QAbstractItemView.PositionAtTop)
        return

    def generate_tree(self):
        """(Re)generates the tree for display of loaded rod data."""
        self.ui.tv_rods.clear()
        for frame in self.rod_info.keys():
            current_frame = QTreeWidgetItem(self.ui.tv_rods)
            current_frame.setText(0, f"Frame: {frame}")
            for color in self.rod_info[frame].keys():
                current_color = QTreeWidgetItem(
                    current_frame)
                current_color.setText(0, color)
                for particle in self.rod_info[frame][color].keys():
                    current_particle = QTreeWidgetItem(
                        current_color)
                    current_particle.setText(
                        0, f"Rod{particle:3d}: "
                    )
                    for idx, gp in enumerate(
                            self.rod_info[frame][color][particle]):
                        current_particle.setText(idx + 1, gp)
                current_color.sortChildren(0, QtCore.Qt.AscendingOrder)
            current_frame.sortChildren(0, QtCore.Qt.AscendingOrder)
        self.update_tree_folding()

    def slider_moved(self, _):
        if self.current_file_ids:
            new_idx = self.ui.slider_frames.sliderPosition()
            idx_diff = new_idx - self.current_file_index
            self.show_next(idx_diff)

    @QtCore.pyqtSlot(dict)
    def update_settings(self, settings: dict):
        """Catches updates of the settings from a `Settings` class.

        Checks for the keys relevant to itself and updates the corresponding
        attributes. Updates itself with the new settings in place.

        Parameters
        ----------
        settings : dict

        Returns
        -------
        None
        """
        settings_changed = False
        if "rod_increment" in settings:
            settings_changed = True
            self._rod_incr = settings["rod_increment"]

    def open_image_folder(self):
        """Lets the user select an image folder to show images from.

        Lets the user select an image from folder out of which all images
        are marked for later display. The selected image is opened
        immediately. It tries to extract a camera id from
        the selected folder and logs the opening action.

        Returns
        -------
        None
        """
        # check for a directory
        ui_dir = self.ui.le_image_dir.text()
        # opens directory to select image
        kwargs = {}
        # handle file path issue when running on linux as a snap
        if 'SNAP' in os.environ:
            kwargs["options"] = QFileDialog.DontUseNativeDialog
        chosen_file, _ = QFileDialog.getOpenFileName(self, 'Open an image',
                                                     ui_dir,
                                                     'Images (*.png *.jpeg '
                                                     '*.jpg)', **kwargs)
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
            read_dir = os.path.dirname(chosen_file)
            self.fileList, self.current_file_ids = f_ops.get_images(read_dir)
            self.current_file_index = self.current_file_ids.index(
                int(file_name))

            # Sort according to name / ascending order
            desired_file = self.fileList[self.current_file_index]
            self.fileList.sort()
            self.current_file_index = self.fileList.index(desired_file)
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
            self.ui.le_image_dir.setText(read_dir)
            if self.original_data is not None:
                self.show_overlay()

            # Update persistent file lists
            self.view_filelists[self.ui.camera_tabs.currentIndex()] = \
                self.fileList
            self.file_ids[self.ui.camera_tabs.currentIndex()] = \
                self.current_file_ids

            # Update slider
            self.ui.slider_frames.setMaximum(len(self.fileList) - 1)
            self.ui.slider_frames.setSliderPosition(self.current_file_index)
            current_id = self.current_file_ids[self.current_file_index]
            self.ui.le_frame_disp.setText(f"Frame: {current_id}")

            # Logging
            new_frame = self.current_file_ids[self.current_file_index]
            self.logger.frame = new_frame
            self.current_camera.logger.frame = new_frame
            first_action = lg.FileAction(read_dir, lg.FileActions.LOAD_IMAGES,
                                         len(self.fileList),
                                         cam_id=self.current_camera.cam_id,
                                         parent_id="main")
            first_action.parent_id = self.logger_id
            self.logger.add_action(first_action)

            self.update_tree_folding()

    def open_rod_folder(self):
        """Lets the user select a folder with rod position data.

        Lets the user select a folder with rod position data. It is
        evaluated which files in the folder are valid data files and what
        colors they describe. The GUI is updated accordingly to the found
        files. The original files are copied to a temporary location for
        storage of temporary changes. The data is opened immediately,
        if applicable by the GUI state. The data discovery/loading is logged.

        Returns
        -------
        None
        """
        # check for a directory
        ui_dir = self.ui.le_rod_dir.text()
        while True:
            old_original_data = self.original_data
            self.original_data = QFileDialog.getExistingDirectory(
                self, 'Choose Folder with position data', ui_dir) + '/'
            if self.original_data == '/':
                if old_original_data is None:
                    self.original_data = None
                else:
                    self.original_data = old_original_data
                return

            if self.original_data is not None:
                # delete old stored files
                for file in os.listdir(self.data_files):
                    os.remove(self.data_files + "/" + file)
                d_ops.lock.lockForWrite()
                d_ops.rod_data = None
                d_ops.lock.unlock()
                
                # Check for eligible files and de-/activate radio buttons
                eligible_files = f_ops.folder_has_data(self.original_data)
                if not eligible_files:
                    # No matching file was found
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
                        self.ui.le_rod_dir.setText("")
                        self.clear_screen()
                        self._allow_overwrite = False
                        return
                    else:
                        # Retry folder selection
                        continue

                else:
                    self._allow_overwrite = False
                    # Check whether there is already corrected data
                    out_folder = self.original_data[:-1] + "_corrected"
                    corrected_files = f_ops.folder_has_data(out_folder)
                    if corrected_files:
                        msg = QMessageBox()
                        msg.setWindowIcon(QtGui.QIcon(ICON_PATH))
                        msg.setIcon(QMessageBox.Question)
                        msg.setWindowTitle("Rod Tracker")
                        msg.setText("There seems to be corrected data "
                                    "already. Do you want to use that "
                                    "instead of the selected data?")
                        msg.setStandardButtons(QMessageBox.Yes |
                                               QMessageBox.No)
                        user_decision = msg.exec()
                        if user_decision == QMessageBox.Yes:
                            self.original_data = out_folder + "/"
                            self._allow_overwrite = True

                    # Load data
                    d_ops.lock.lockForWrite()
                    d_ops.rod_data, found_colors = f_ops.get_color_data(
                        self.original_data, self.data_files)
                    d_ops.lock.unlock()

                    # Update visual elements
                    rb_colors = [child for child
                                 in self.ui.group_rod_color.children() if
                                 type(child) is QRadioButton]
                    rb_color_texts = [btn.text().lower() for btn in rb_colors]
                    group_layout = self.ui.group_rod_color.layout()
                    max_col = group_layout.columnCount() - 1
                    max_row = 1
                    if group_layout.itemAtPosition(1, max_col) is not None:
                        # 'Add' a new column as current layout is full
                        max_col += 1
                        max_row = 0
                    for color in found_colors:
                        if color not in rb_color_texts:
                            # Create new QRadioButton for this color
                            new_btn = QRadioButton(text=color.capitalize())
                            new_btn.setObjectName(f"rb_{color}")
                            new_btn.toggled.connect(self.color_change)
                            # retain only 2 rows
                            group_layout.addWidget(new_btn, max_row, max_col)
                            if max_row == 1:
                                max_row = 0
                                max_col += 1
                            else:
                                max_row += 1

                    # Display as a tree
                    thread, worker = pl.run_in_thread(
                        d_ops.extract_seen_information, {})
                    worker.finished.connect(self.setup_tree)
                    self.background_tasks.append((thread, worker))
                    thread.start()

                    # Rod position data was selected correctly
                    self.ui.le_rod_dir.setText(self.original_data[:-1])
                    self.ui.le_save_dir.setText(out_folder)
                    this_action = lg.FileAction(self.original_data[:-1],
                                                lg.FileActions.LOAD_RODS)
                    this_action.parent_id = self.logger_id
                    self.ui.lv_actions_list.add_action(
                        this_action)
                    self.show_overlay()
                    for btn in rb_colors:
                        if btn.text().lower() not in found_colors:
                            group_layout.removeWidget(btn)
                            btn.hide()
                            btn.deleteLater()
                    return

    @QtCore.pyqtSlot(object)
    def setup_tree(self, inputs):
        """Handles the setup of the treeview from extracted rod data."""
        assert len(inputs) == 2
        rod_info, columns = inputs[:]
        assert type(columns) is list
        assert type(rod_info) is dict

        self.rod_info = rod_info
        self.ui.tv_rods.clear()
        self.ui.tv_rods.setColumnCount(len(columns) + 1)
        headers = [self.ui.tv_rods.headerItem().text(0),
                   *columns]
        self.ui.tv_rods.setHeaderLabels(headers)
        self.generate_tree()
        self.update_tree_folding()

    def show_overlay(self):
        """Tries to load rods and hints the user if that is not possible.

        Tries to load rods and hints the user if that is not possible. It
        displays warnings, if
            a) no images are loaded (yet)
            b) no rod position data is loaded (yet).

        Returns
        -------
        None
        """
        if not self.ui.cb_overlay.isChecked():
            return
        if self.original_data is not None:
            # Check whether image file is loaded
            if self.fileList is None:
                dialogs.show_warning("There is no image loaded yet. Please "
                                     "select an image before rods can be "
                                     "displayed.")
                return
            else:
                self.load_rods()
        else:
            dialogs.show_warning(f"There are no rod position files selected "
                                 f"yet. Please select files!")
            self.open_rod_folder()

    def load_rods(self):
        """Loads rod data for one color and creates the `RodNumberWidget`s.

        Loads the rod position data for the selected color in the GUI. It
        creates the `RodNumberWidget` that is associated with each rod. A
        message is displayed in the main window's statusbar, if there is no
        data available for this frame in the loaded files.

        Returns
        -------
        None
        """
        # Load rod position data
        if self.original_data is None or not self.ui.cb_overlay.isChecked():
            return
        if self.current_camera.image is None:
            return
        file_name = (self.fileList[self.current_file_index])
        file_name = os.path.split(file_name)[-1]
        file_name = file_name[1:4]
        color = self.get_selected_color()
        new_rods = d_ops.extract_rods(self.current_camera.cam_id,
                                      int(file_name), color)
        for rod in new_rods:
            self.settings.settings_changed.connect(rod.update_settings)
            rod.setParent(self.current_camera)
        # Trick to adjust the RodNumber bounds
        self.settings.send_settings()

        # Distinguish between display methods
        if self.ui.rb_disp_all.isChecked():
            # Display all loaded rods
            self.current_camera.edits = new_rods
        elif self.ui.rb_disp_one.isChecked():
            # Display only one user chosen rod
            rod_id = self.ui.le_disp_one.text()
            rod_present = False
            for rod in new_rods:
                if rod_id == "":
                    rod_present = True
                    self.current_camera.edits = []
                    break
                if int(rod.rod_id) == int(rod_id):
                    self.current_camera.edits = [rod]
                    rod_present = True
                    break
            if not rod_present:
                self.statusBar().showMessage("This rod is not available in "
                                             "the currently loaded data.",
                                             5000)
                self.current_camera.edits = []

        else:
            # something went wrong/no display selected notification
            self.current_camera.edits = []
            self.statusBar().showMessage("Display method not selected.", 5000)

        self.ui.le_rod_disp.setText(f"Loaded Rods: {len(new_rods)}")
        if not new_rods:
            self.statusBar().showMessage("No rod data available for this "
                                         "image.", 5000)

    @QtCore.pyqtSlot(bool)
    def display_method_change(self, state: bool) -> None:
        """Handles changes of `QRadioButtons` for display method selection."""
        if state:
            self.load_rods()

    @QtCore.pyqtSlot(str)
    def display_rod_changed(self, _: str):
        """Handles a change of rod numbers in the user's input field."""
        if self.ui.rb_disp_one.isChecked():
            self.load_rods()

    def clear_screen(self) -> None:
        """Clears the screen from any displayed rods."""
        self.cameras[self.ui.camera_tabs.currentIndex()].clear_screen()

    @QtCore.pyqtSlot(int)
    def cb_changed(self, state):
        """Catches a QCheckBox state change and overlays or clears the rods.

        Parameters
        ----------
        state : int
            The new state of the QCheckbox {0, 2}

        Returns
        -------
        None
        """
        if state == 0:
            # deactivated
            self.clear_screen()
        elif state == 2:
            # activated
            self.show_overlay()

    def show_next(self, direction: int):
        """Tries to open the next image.

        It tries to open the next image in the direction provided relative
        to the currently opened image.

        Parameters
        ----------
        direction : int
            Direction of the image to open next. Its the index relative to
            the currently opened image.
            a) direction = 3    ->  opens the image three positions further
            b) direction = -1   ->  opens the previous image
            c) direction = 0    ->  keeps the current image open

        Returns
        -------
        None
        """
        if direction == 0:
            # No change necessary
            return
        if self.fileList:
            # Switch images
            try:
                self.current_file_index += direction
                # Chooses next image with specified extension
                filename = (self.fileList[self.current_file_index])
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
                        self.current_file_index
                    # Update information on last action
                    new_idx = self.current_file_index if \
                        self.current_file_index >= 0 else \
                        len(self.current_file_ids) + self.current_file_index
                    self.ui.slider_frames.setSliderPosition(new_idx)
                    new_frame = self.current_file_ids[self.current_file_index]
                    self.logger.frame = new_frame
                    self.current_camera.logger.frame = new_frame
                    self.update_tree_folding()

            except IndexError:
                # the iterator has finished, restart it
                if direction > 0:
                    self.current_file_index = -1
                else:
                    self.current_file_index = 0
                self.show_next(direction)
        else:
            # no file list found, load an image
            self.open_image_folder()

    def original_size(self):
        """Displays the currently loaded image in its native size.

        Returns
        -------
        None
        """
        self.current_camera.scale_factor = 1
        self.ui.action_zoom_in.setEnabled(True)
        self.ui.action_zoom_out.setEnabled(True)

    def fit_to_window(self):
        """Fits the image to the space available in the GUI.

        Fits the image to the space available for the image in the GUI and
        keeps the aspect ratio as in the original.

        Returns
        -------
        None
        """
        current_sa = self.findChild(QScrollArea,
                                    f"sa_camera_"
                                    f"{self.ui.camera_tabs.currentIndex()}")
        to_size = current_sa.size()
        to_size = QtCore.QSize(to_size.width() - 20, to_size.height() - 20)
        self.current_camera.scale_to_size(to_size)

    def scale_image(self, factor):
        """Sets a new relative scaling for the current image.

        Sets a new scaling to the currently displayed image by
        `current_camera`. The scaling factor given thereby acts relative to
        the already applied scaling.

        Parameters
        ----------
        factor : float
            The relative scaling factor. Example:
            factor=1.1, current scaling=2.0     ->  new scaling=2.2

        Returns
        -------
        None
        """
        new_zoom = self.current_camera.scale_factor * factor
        self.current_camera.scale_factor = new_zoom
        # Disable zoom, if zoomed too much
        self.ui.action_zoom_in.setEnabled(new_zoom < 9.0)
        self.ui.action_zoom_out.setEnabled(new_zoom > 0.11)

    def get_selected_color(self):
        """Gets the currently selected color in the GUI.

        Returns
        -------
        str
            The color that is currently selected in the GUI.
        """
        for rb in self.ui.group_rod_color.findChildren(QRadioButton):
            if rb.isChecked():
                return rb.objectName()[3:]

    @QtCore.pyqtSlot(bool)
    def color_change(self, state: bool) -> None:
        """Handles changes of the `QRadioButtons` for color selection."""
        if state:
            self.last_color = self.get_selected_color()
            self.show_overlay()
            self.update_tree_folding()

    @QtCore.pyqtSlot(int, list)
    def create_new_rod(self, number: int, new_position: list) -> None:
        """Creates a new rod, that was previously not in the loaded data.

        Creates the new rod, adds it to the currently displayed
        `RodImageWidget`'s list of `RodNumberWidget`s and notifies the
        respective logger object about this performed action.

        Parameters
        ----------
        number : int
            The new rod's ID.
        new_position : list
            The new rod's position in the unscaled image's reference frame.
            [x1, y1, x2, y2]

        Returns
        -------
        None
        """
        # update information for the tree view
        self.rod_info[self.logger.frame][self.last_color][number] = \
            ["unseen", "unseen"]

        new_rod = rn.RodNumberWidget(self.last_color, self.current_camera,
                                     str(number))
        new_rod.rod_id = number
        new_rod.setObjectName(f"rn_{number}")
        new_rod.rod_points = new_position
        new_rod.rod_state = rn.RodState.SELECTED
        # Newly created rods are always "seen"
        new_rod.seen = True
        new_rods = []
        for rod in self.current_camera.edits:
            new_rods.append(rod.copy())
        new_rods.append(new_rod)
        self.current_camera.edits = new_rods
        last_action = lg.CreateRodAction(new_rod.copy())
        self.current_camera.logger.add_action(last_action)

    @QtCore.pyqtSlot(lg.Action)
    def catch_data(self, change: lg.Action) -> None:
        """Changes the data stored in RAM according to the Action performed."""
        new_data = change.to_save()
        if new_data is None:
            return

        thread, worker = pl.run_in_thread(d_ops.change_data, 
                                          {"new_data": new_data})
        worker.finished.connect(self.update_changed_data)
        self.background_tasks.append((thread, worker))
        thread.start()

        if isinstance(new_data["frame"], Iterable):
            for i in range(len(new_data["frame"])):
                tmp_data = {
                    "frame": new_data["frame"][i],
                    "cam_id": new_data["cam_id"][i],
                    "color": new_data["color"][i],
                    "position": new_data["position"][i],
                    "rod_id": new_data["rod_id"][i],
                    "seen": new_data["seen"][i]
                }
                self.update_tree(tmp_data, no_gen=True)
            self.generate_tree()
        else:
            self.update_tree(new_data)

    @QtCore.pyqtSlot(object)
    def update_changed_data(self, _):
        """Updates the main data storage in RAM (used for communication
        with threads)."""
        previously_selected = self.current_camera.active_rod
        self.load_rods()
        self.current_camera.rod_activated(previously_selected)

    def save_changes(self, temp_only=False):
        """Saves unsaved changes to disk temporarily or permanently.

        Saves the changes made in all views to disk. Depending on the flags
        it will be only to the temporary files or also to the (user-)chosen
        permanent saving directory. A warning is issued, if the user tries
        to overwrite the original data files.

        Parameters
        ----------
        temp_only : bool
            Flag to either save to the temporary files only or permanently
            to the (user-)chosen location.
            (Default is False)

        Returns
        -------
        None
        """
        # TODO: move saving to different Thread(, if it still takes too long)
        if d_ops.rod_data is None:
            return
        # Skip, if there are no changes
        if not self.ui.lv_actions_list.unsaved_changes:
            return

        # Clean up data from unused rods before permanent saving
        if not temp_only:
            self.clean_data()

        # Update temporary files
        d_ops.lock.lockForRead()
        for rb in self.ui.group_rod_color.findChildren(QRadioButton):
            color = rb.objectName()[3:]
            tmp_file = self.data_files + "/" + self.data_file_name.format(
                color)
            df_current = d_ops.rod_data.loc[d_ops.rod_data.color == color].copy()
            df_current = df_current.astype({"frame": 'int', "particle": 'int'})
            df_current.to_csv(tmp_file, index_label="")
        d_ops.lock.unlock()

        if temp_only:
            # skip permanent saving
            return

        save_dir = self.ui.le_save_dir.text()
        if save_dir == self.ui.le_rod_dir.text() and not self._allow_overwrite:
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

        for file in os.listdir(self.data_files):
            shutil.copy2(self.data_files + "/" + file, save_dir + "/" + file)
            save_file = save_dir + "/" + file
            this_action = lg.FileAction(save_file, lg.FileActions.SAVE)
            this_action.parent_id = self.logger_id
            self.ui.lv_actions_list.add_action(this_action)
        # notify loggers that everything was saved
        self.logger.actions_saved()
        for cam in self.cameras:
            cam.logger.actions_saved()

    @staticmethod
    def warning_unsaved() -> bool:
        """Warns that there are unsaved changes that might get lost.

        Issues a warning popup to the user to either discard any unsaved
        changes or stay in the current state to prevent changes get lost.

        Returns
        -------
        bool
            True, if changes shall be discarded.
            False, if the user aborted.
        """
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
        """Activates the given color QRadioButton in the GUI.

        Parameters
        ----------
        to_color : str
            The color that is activated.

        Returns
        -------
        None
        """
        for rb in self.ui.group_rod_color.findChildren(QRadioButton):
            if rb.objectName()[3:] == to_color:
                # activate the last color
                rb.toggle()
                self.update_tree_folding()

    @QtCore.pyqtSlot(int)
    def change_frame(self, to_frame: int):
        """Loads the requested frame for the currently used view/camera.

        Parameters
        ----------
        to_frame : int
            ID of the requested frame.

        Returns
        -------
        None
        """
        try:
            new_idx = self.current_file_ids.index(to_frame)
            idx_diff = new_idx - self.current_file_index
        except ValueError:
            # Image not found
            self.current_camera.setPixmap(QtGui.QPixmap(ICON_PATH))
            self.ui.statusbar.showMessage(f"No image with ID"
                                          f":{to_frame} found.", 4000)
            return
        # Loads a new image
        self.show_next(idx_diff)
        if self.ui.cb_overlay.isChecked():
            # Ensure that rods are loaded
            self.load_rods()

    @QtCore.pyqtSlot(lg.NumberChangeActions, int, int)
    @QtCore.pyqtSlot(lg.NumberChangeActions, int, int, str, int, str, bool)
    def catch_number_switch(self, mode: lg.NumberChangeActions, old_id: int,
                            new_id: int, color: str = None, frame: int = None,
                            cam_id: str = None, log: bool = True):
        """Handles changes of rod numbers for more than the current frame and
        camera."""
        if color is None:
            color = self.get_selected_color()
        if frame is None:
            frame = self.logger.frame
        if cam_id is None:
            cam_id = self.current_camera.cam_id
        thread, worker = pl.run_in_thread(d_ops.rod_number_swap,
                                          {"mode": mode, "previous_id": old_id,
                                          "new_id": new_id, "color": color,
                                          "frame": frame, "cam_id": cam_id})
        worker.finished.connect(self.update_changed_data)
        self.background_tasks.append((thread, worker))
        thread.start()

        if log:
            self.current_camera.logger.add_action(
                lg.NumberExchange(mode, old_id, new_id, 
                                  self.get_selected_color(), self.logger.frame,
                                  self.current_camera.cam_id)
                )
        return

    def change_view(self, direction: int) -> None:
        """Helper method for programmatic changes of the camera tabs."""
        old_idx = self.ui.camera_tabs.currentIndex()
        new_idx = old_idx + direction
        if new_idx > 1:
            new_idx = 0
        elif new_idx < 0:
            new_idx = 1
        self.ui.camera_tabs.setCurrentIndex(new_idx)

    @QtCore.pyqtSlot(int)
    def view_changed(self, new_idx):
        """Handles switches between the camera tabs.

        Handles the switches between the camera tabs and depending on the
        GUI state tries to load the same frame for the newly displayed tab
        as in the old one. If no frame is available in the new tab it
        displays a dummy graphic and shows a message in the main window's
        statusbar.

        Parameters
        ----------
        new_idx : int
            The index of the tab that is shown next.

        Returns
        -------
        None
        """
        # Ensure the image/frame number is consistent over views
        index_diff = 0
        if self.ui.action_persistent_view.isChecked():
            if self.current_file_ids:
                current_id = self.current_file_ids[self.current_file_index]
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

        self.current_file_index = self.file_indexes[new_idx]
        self.fileList = self.view_filelists[new_idx]
        self.current_file_ids = self.file_ids[new_idx]
        self.current_camera = self.cameras[new_idx]

        # Connect signals for rod alteration
        self.ui.action_shorten_displayed.triggered.disconnect()
        self.ui.action_lengthen_displayed.triggered.disconnect()
        self.ui.action_shorten_selected.triggered.disconnect()
        self.ui.action_lengthen_selected.triggered.disconnect()
        self.ui.action_shorten_displayed.triggered.connect(
            lambda: self.current_camera.adjust_rod_length(
                -self._rod_incr, False))
        self.ui.action_lengthen_displayed.triggered.connect(
            lambda: self.current_camera.adjust_rod_length(
                self._rod_incr, False))
        self.ui.action_shorten_selected.triggered.connect(
            lambda: self.current_camera.adjust_rod_length(
                -self._rod_incr, True))
        self.ui.action_lengthen_selected.triggered.connect(
            lambda: self.current_camera.adjust_rod_length(
                self._rod_incr, True))

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

    def requesting_undo(self) -> None:
        """Helper method to emit a request for reverting the last action."""
        self.request_undo.emit(self.current_camera.cam_id)

    def requesting_redo(self) -> None:
        """Helper method to emit a request for repeating the last action."""
        self.request_redo.emit(self.current_camera.cam_id)

    @QtCore.pyqtSlot(bool)
    def tab_has_changes(self, has_changes: bool) -> None:
        """Changes the current tabs text to indicate it has (no) changes."""
        tab_idx = self.ui.camera_tabs.currentIndex()
        if has_changes:
            if self.ui.camera_tabs.tabText(tab_idx)[-1] == "*":
                return
            new_text = self.ui.camera_tabs.tabText(tab_idx) + "*"
        else:
            if self.ui.camera_tabs.tabText(tab_idx)[-1] != "*":
                return
            new_text = self.ui.camera_tabs.tabText(tab_idx)[0:-1]
        self.ui.camera_tabs.setTabText(tab_idx, new_text)

    def eventFilter(self, source: QtCore.QObject, event: QtCore.QEvent)\
            -> bool:
        """Intercepts events, here modified scroll events for zooming.

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
        if source not in [self.ui.sa_camera_0.verticalScrollBar(),
                          self.ui.sa_camera_1.verticalScrollBar()]:
            return False
        if type(event) != QtGui.QWheelEvent:
            return False

        event = QWheelEvent(event)
        if not event.modifiers() == QtCore.Qt.ControlModifier:
            return False
        if event.angleDelta().y() < 0:
            self.scale_image(factor=0.8)
        elif event.angleDelta().y() > 0:
            self.scale_image(factor=1.25)
        return True

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        """Reimplements QMainWindow.resizeEvent(a0).

        Currently not used.

        Parameters
        ----------
        a0 : QResizeEvent.

        Returns
        -------
        None
        """
        super().resizeEvent(a0)
        # get the screen's resolution the application is displayed on
        # self.screen().size()
        # adapt margins to screen resolution

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        """Reimplements QMainWindow.closeEvent(a0).

        In case of unsaved changes, the user is asked to save or discard
        these before closing the application. The closing can be aborted
        with this dialog.

        Parameters
        ----------
        a0 : QCloseEvent

        Returns
        -------
        None
        """
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

    def clean_data(self):
        """Deletes unused rods from the dataset in RAM.

        Unused rods are identified by not having positional data in the
        *gp_* columns of the dataset. This assumed when only NaN or 0 is
        present in all these columns for a given rod/row. The user is asked
        to confirm these deletions and has the opportunity to exclude
        identified candidates from deletion. All confirmed rows are then
        deleted from the main dataset in RAM and therefore propagated to
        disk on the next saving operation.

        Returns
        -------
        None
        """
        if d_ops.rod_data is None:
            self.ui.statusbar.showMessage("No position data loaded. Unable "
                                          "to clean unused rods.", 4000)
            return
        to_delete = d_ops.find_unused_rods()
        if len(to_delete):
            confirm = dialogs.ConfirmDeleteDialog(to_delete, parent=self)
            if confirm.exec():
                delete_idx = to_delete.index[confirm.confirmed_delete]
                if len(delete_idx):
                    d_ops.lock.lockForWrite()
                    deleted_rows = d_ops.rod_data.loc[delete_idx].copy()
                    d_ops.rod_data = d_ops.rod_data.drop(index=delete_idx)
                    d_ops.lock.unlock()
                    performed_action = lg.PermanentRemoveAction(len(delete_idx))
                    self.logger.add_action(performed_action)
                    # Update rods and tree display
                    thread, worker = pl.run_in_thread(
                        d_ops.extract_seen_information, {})
                    worker.finished.connect(self.setup_tree)
                    self.background_tasks.append((thread, worker))
                    thread.start()
                    self.load_rods()
                else:
                    self.ui.statusbar.showMessage("No rods confirmed for "
                                                  "permanent deletion.", 4000)
            else:
                self.ui.statusbar.showMessage("Aborted data cleaning.",
                                              4000)
                return
        else:
            self.ui.statusbar.showMessage("No unused rods found for "
                                          "deletion.", 4000)
            return
