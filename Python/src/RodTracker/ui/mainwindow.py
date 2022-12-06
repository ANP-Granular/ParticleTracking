#  Copyright (c) 2022 Adrian Niemann Dmitry Puzyrev
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

import shutil
import pathlib
import platform
from typing import Iterable, List, Callable
from functools import partial

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QRadioButton, \
    QScrollArea, QTreeWidgetItem
from PyQt5.QtGui import QWheelEvent

import RodTracker.backend.settings as se
import RodTracker.backend.logger as lg
import RodTracker.backend.data_operations as d_ops
import RodTracker.backend.file_operations as f_ops
import RodTracker.backend.parallelism as pl
import RodTracker.backend.file_locations as fl
import RodTracker.backend.img_data as img_data
import RodTracker.ui.rodnumberwidget as rn
import RodTracker.ui.mainwindow_layout as mw_l
from RodTracker.ui import dialogs
from RodTracker.ui.settings_setup import init_settings


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
    image_managers : List[ImageData]
        Manager objects for loaded/selected image datasets. There is one
        associated with each `RodImageWidget` in `cameras`.
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
    saving_finished()
        Is emitted after saving to trigger all loggers to reset their list of
        unsaved actions.
    update_3d(int)
        Is emitted to trigger the 3D view to update the displayed rods.

    Slots
    -----
    catch_data(Action)
    catch_number_switch([NumberChangeActions, int, int], [NumberChangeActions, int, int, str, int, str, bool])      # noqa: E501
    cb_changed(int)
    color_change(bool)
    change_color(str)
    create_new_rod(int, list)
    display_method_change(bool)
    display_rod_changed(str)
    images_loaded(int, str, Path)
    next_image(int, int)
    slider_moved(int)
    tab_has_changes(bool, str)
    tree_selection(QTreeWidgetItem, int)
    update_changed_data(object)
    update_settings(dict)
    view_changed(int)

    """
    fileList: List[pathlib.Path] = None
    logger_id: str = "main"
    logger: lg.ActionLogger
    request_undo = QtCore.pyqtSignal(str, name="request_undo")
    request_redo = QtCore.pyqtSignal(str, name="request_redo")
    saving_finished = QtCore.pyqtSignal()
    update_3d = QtCore.pyqtSignal(int)

    _allow_overwrite: bool = False
    _rod_incr: float = 1.0
    _fit_next_img: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.threads = QtCore.QThreadPool()
        self.ui = mw_l.Ui_MainWindow()
        self.ui.setupUi(self)

        # Adaptations of the UI
        self.setWindowIcon(QtGui.QIcon(fl.icon_path()))
        self.ui.pb_undo.setIcon(QtGui.QIcon(fl.undo_icon_path()))
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
        self.image_managers = [img_data.ImageData(0), img_data.ImageData(1)]
        for manager in self.image_managers:
            id = manager._logger_id
            manager._logger = self.ui.lv_actions_list.get_new_logger(id)

        self.cameras = [self.ui.camera_0, self.ui.camera_1]
        for cam in self.cameras:
            cam.logger = self.ui.lv_actions_list.get_new_logger(cam.cam_id)
            cam.setPixmap(QtGui.QPixmap(fl.icon_path()))

        self.original_data = None   # Holds the original data directory
        self.data_files = pathlib.Path(
            self.ui.lv_actions_list.temp_manager.name)
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

        init_settings(self.ui, self.settings)
        self.ui.view_3d.set_mode_group(self.ui.rb_all_3d, self.ui.rb_color_3d,
                                       self.ui.rb_one_3d)
        self.connect_signals()
        self.settings.send_settings()
        self.ui.view_3d.toggle_display(self.ui.cb_show_3D.checkState())
        self.ui.view_3d.update_color(self.get_selected_color())
        self.ui.view_3d.rod_changed(self.ui.le_disp_one.text())

    def connect_signals(self):
        # Opening files
        self.ui.action_open_rods.triggered.connect(self.get_rod_selection)
        self.ui.pb_load_rods.clicked.connect(self.get_rod_selection)
        self.ui.le_rod_dir.returnPressed.connect(self.get_rod_selection)

        # Saving
        self.ui.pb_save_rods.clicked.connect(self.save_changes)
        self.ui.action_save.triggered.connect(self.save_changes)
        self.saving_finished.connect(self.logger.actions_saved)

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
        self.ui.pb_front.clicked.connect(self.ui.view_3d.show_front)
        self.ui.pb_top.clicked.connect(self.ui.view_3d.show_top)

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
        self.update_3d.connect(self.ui.view_3d.update_rods)
        self.ui.cb_show_3D.stateChanged.connect(self.ui.view_3d.toggle_display)
        self.ui.le_disp_one.textChanged.connect(self.ui.view_3d.rod_changed)

        # Settings
        self.settings.settings_changed.connect(self.update_settings)
        self.settings.settings_changed.connect(
            rn.RodNumberWidget.update_defaults)
        self.settings.settings_changed.connect(self.ui.view_3d.update_settings)

        # Logging
        self.logger.notify_unsaved.connect(self.tab_has_changes)
        self.logger.data_changed.connect(self.catch_data)

        # Cameras
        tab_idx = self.ui.camera_tabs.currentIndex()
        for cam, manager in zip(self.cameras, self.image_managers):
            manager.data_loaded.connect(self.images_loaded)
            manager.next_img[int, int].connect(self.next_image)
            manager.next_img[QtGui.QImage].connect(cam.image)
            if str(tab_idx) in manager._logger_id:
                self.ui.pb_load_images.clicked.connect(
                    partial(manager.select_images,
                            self.ui.le_image_dir.text()))
                self.ui.action_open.triggered.connect(
                    partial(manager.select_images,
                            self.ui.le_image_dir.text()))
                self.ui.le_image_dir.returnPressed.connect(
                    partial(manager.select_images,
                            self.ui.le_image_dir.text()))

            cam.request_color_change.connect(self.change_color)
            cam.request_frame_change.connect(manager.image_at)
            cam.normal_frame_change.connect(self.show_next)
            cam.logger.notify_unsaved.connect(self.tab_has_changes)
            cam.logger.request_saving.connect(self.save_changes)
            cam.logger.data_changed.connect(self.catch_data)
            self.saving_finished.connect(cam.logger.actions_saved)
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
            lambda: self.cameras[tab_idx].adjust_rod_length(
                -self._rod_incr, False))
        self.ui.action_lengthen_displayed.triggered.connect(
            lambda: self.cameras[tab_idx].adjust_rod_length(
                self._rod_incr, False))
        self.ui.action_shorten_selected.triggered.connect(
            lambda: self.cameras[tab_idx].adjust_rod_length(
                -self._rod_incr, True))
        self.ui.action_lengthen_selected.triggered.connect(
            lambda: self.cameras[tab_idx].adjust_rod_length(
                self._rod_incr, True))

        # Help
        self.ui.action_docs.triggered.connect(lambda: dialogs.show_readme(
            self))
        self.ui.action_about.triggered.connect(lambda: dialogs.show_about(
            self))
        self.ui.action_about_qt.triggered.connect(
            lambda: QMessageBox.aboutQt(self, "RodTracker"))
        self.ui.action_logs.triggered.connect(lg.open_logs)

    @QtCore.pyqtSlot(QTreeWidgetItem, int)
    def tree_selection(self, item: QTreeWidgetItem, col: int):
        """Handle the selection of a rod & frame in the `RodTree` widget.

        Parameters
        ----------
        item : QTreeWidgetItem
            Selected item in the `RodTree` widget.
        col : int
            Column of the `RodTree` widget the item was selected in.
        """
        if not item.childCount():
            # change camera
            # TODO
            # change color
            color = item.parent().text(0)
            self.change_color(color)
            # change frame
            frame = int(item.parent().parent().text(0)[7:])
            tab_idx = self.ui.camera_tabs.currentIndex()
            self.image_managers[tab_idx].image(frame)
            # activate clicked rod
            cam = self.cameras[tab_idx]
            if cam.edits:
                selected_rod = int(item.text(0)[4:6])
                cam.rod_activated(selected_rod)
        return

    @QtCore.pyqtSlot(int)
    def slider_moved(self, pos: int):
        """Handle image displays corresponding to slider movements.

        Parameters
        ----------
        pos : int
            New position of the slider, that is thereby the new image index to
            be displayed.
        """
        tab_idx = self.ui.camera_tabs.currentIndex()
        self.image_managers[tab_idx].image_at(pos)

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
        if "rod_increment" in settings:
            self._rod_incr = settings["rod_increment"]

    @QtCore.pyqtSlot(int, int)
    def next_image(self, frame: int, frame_idx: int):
        """Handles updates of the currently displayed image.

        Updates the GUI controls to match the currently displayed image.

        Parameters
        ----------
        frame : int
            Frame number of the newly displayed image.
        frame_idx : int
            Index of the newly displayed image in the whole image dataset.
        """
        self.ui.le_frame_disp.setText(f"Frame: {frame}")
        self.ui.slider_frames.setSliderPosition(frame_idx)
        self.logger.frame = frame
        self.cameras[self.ui.camera_tabs.currentIndex()].logger.frame = frame
        # Fit the first image of a newly loaded dataset to the screen
        if self._fit_next_img:
            self.fit_to_window()
            self._fit_next_img = False

        self.update_3d.emit(frame)
        self.ui.tv_rods.update_tree_folding(frame, self.get_selected_color())

        if not self.ui.action_persistent_view.isChecked():
            self.fit_to_window()
            del self.cameras[self.ui.camera_tabs.currentIndex()].edits
        else:
            if self.original_data is not None:
                self.show_overlay()

    @QtCore.pyqtSlot(int, str, pathlib.Path)
    def images_loaded(self, frames: int, cam_id: str, folder: pathlib.Path):
        """Handles updates of loaded image datasets.

        Updates the GUI elements to match the newly loaded image dataset.

        Parameters
        ----------
        frames : int
            Number of loaded frames.
        cam_id : str
            ID of the loaded dataset/folder/camera.
        folder : pathlib.Path
            Folder from which the images were loaded.
        """
        self._fit_next_img = True
        # Set new camera ID
        tab_idx = self.ui.camera_tabs.currentIndex()
        tab_text = self.ui.camera_tabs.tabText(tab_idx)
        front_text = tab_text.split("(")[0]
        end_text = tab_text.split(")")[-1]
        new_text = front_text + "(" + cam_id + ")" +\
            end_text
        self.ui.camera_tabs.setTabText(tab_idx, new_text)
        self.cameras[tab_idx].cam_id = cam_id

        # Update slider
        self.ui.slider_frames.setMaximum(frames - 1)
        self.ui.slider_frames.setSliderPosition(0)
        self.ui.le_frame_disp.setText("Frame: ???")

        # Update folder display
        self.ui.le_image_dir.setText(str(folder))

    def get_rod_selection(self):
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
        try_again = True
        while try_again:
            old_original_data = self.original_data
            # self.original_data = QFileDialog.getExistingDirectory(
            #     self, 'Choose Folder with position data', ui_dir) + '/'
            self.original_data = QFileDialog.getExistingDirectory(
                self, 'Choose Folder with position data', ui_dir)
            if self.original_data == '':
                if old_original_data is None:
                    self.original_data = None
                else:
                    self.original_data = old_original_data
                return
            self.original_data = pathlib.Path(self.original_data).resolve()
            try_again = self.open_rod_folder()

    def open_rod_folder(self) -> bool:
        """Tries to open the selected folder with potential rod position data.

        It is evaluated which files in the folder are valid data files and what
        colors they describe. The GUI is updated accordingly to the found
        files. The original files are copied to a temporary location for
        storage of temporary changes. The data is opened immediately, if
        applicable by the GUI state. The data discovery/loading is logged.

        Returns
        -------
        None
        """
        if self.original_data is not None:
            # delete old stored files
            for file in self.data_files.iterdir():
                file.unlink()   # deletes the file
            d_ops.lock.lockForWrite()
            d_ops.rod_data = None
            d_ops.lock.unlock()

            # Check for eligible files and de-/activate radio buttons
            eligible_files = f_ops.folder_has_data(self.original_data)
            if not eligible_files:
                # No matching file was found
                msg = QMessageBox()
                msg.setWindowIcon(QtGui.QIcon(fl.icon_path()))
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
                    return False
                else:
                    # Retry folder selection
                    return True

            else:
                self._allow_overwrite = False
                # Check whether there is already corrected data
                out_folder = self.original_data.stem + "_corrected"
                out_folder = self.original_data.parent / out_folder
                corrected_files = f_ops.folder_has_data(out_folder)
                if corrected_files:
                    msg = QMessageBox()
                    msg.setWindowIcon(QtGui.QIcon(fl.icon_path()))
                    msg.setIcon(QMessageBox.Question)
                    msg.setWindowTitle("Rod Tracker")
                    msg.setText("There seems to be corrected data "
                                "already. Do you want to use that "
                                "instead of the selected data?")
                    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
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
                worker = pl.Worker(d_ops.extract_seen_information)
                worker.signals.result.connect(self.ui.tv_rods.setup_tree)
                self.threads.start(worker)

                # Rod position data was selected correctly
                self.ui.le_rod_dir.setText(str(self.original_data.parent))
                self.ui.le_save_dir.setText(str(out_folder))
                this_action = lg.FileAction(self.original_data.parent,
                                            lg.FileActions.LOAD_RODS)
                this_action.parent_id = self.logger_id
                self.ui.lv_actions_list.add_action(
                    this_action)
                self.show_overlay()
                self.update_3d.emit(self.logger.frame)
                for btn in rb_colors:
                    if btn.text().lower() not in found_colors:
                        group_layout.removeWidget(btn)
                        btn.hide()
                        btn.deleteLater()
                return False
        return True

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
            tab_idx = self.ui.camera_tabs.currentIndex()
            if self.image_managers[tab_idx].folder is None:
                dialogs.show_warning("There is no image loaded yet. Please "
                                     "select an image before rods can be "
                                     "displayed.")
                return
            else:
                self.load_rods()
        else:
            dialogs.show_warning("There are no rod position files selected "
                                 "yet. Please select files!")
            self.get_rod_selection()

    def load_rods(self):
        """Loads rod data for one color and creates the `RodNumberWidget`s.

        Loads the rod position data for the selected color in the GUI. It
        creates the `RodNumberWidget` that is associated with each rod. A
        message is logged, if there is no data available for this frame in the
        loaded files.

        Returns
        -------
        None
        """
        # Load rod position data
        if self.original_data is None or not self.ui.cb_overlay.isChecked():
            return
        tab_idx = self.ui.camera_tabs.currentIndex()
        if self.cameras[tab_idx]._image is None:
            return
        frame = self.image_managers[tab_idx].frames[
            self.image_managers[tab_idx].frame_idx]
        color = self.get_selected_color()
        new_rods = d_ops.extract_rods(self.cameras[tab_idx].cam_id,
                                      frame, color)
        for rod in new_rods:
            self.settings.settings_changed.connect(rod.update_settings)
            rod.setParent(self.cameras[tab_idx])

        # Distinguish between display methods
        if self.ui.rb_disp_all.isChecked():
            # Display all loaded rods
            self.cameras[tab_idx].edits = new_rods
        elif self.ui.rb_disp_one.isChecked():
            # Display only one user chosen rod
            rod_id = self.ui.le_disp_one.text()
            rod_present = False
            for rod in new_rods:
                if rod_id == "":
                    rod_present = True
                    self.cameras[tab_idx].edits = []
                    break
                if int(rod.rod_id) == int(rod_id):
                    self.cameras[tab_idx].edits = [rod]
                    rod_present = True
                    break
            if not rod_present:
                lg._logger.info(f"Rod #{rod_id} is not available in the "
                                f"currently loaded data.")
                self.cameras[tab_idx].edits = []

        else:
            # something went wrong/no display selected notification
            self.cameras[tab_idx].edits = []
            lg._logger.warning("Display method is not selected.")

        self.ui.le_rod_disp.setText(f"Loaded Particles: {len(new_rods)}")
        if not new_rods:
            lg._logger.info(f"No rod position data available for "
                            f"frame #{frame}.")

    @QtCore.pyqtSlot(bool)
    def display_method_change(self, state: bool) -> None:
        """Handles changes of `QRadioButtons` for display method selection."""
        if state:
            self.load_rods()

    @QtCore.pyqtSlot(str)
    def display_rod_changed(self, number: str):
        """Handles a change of rod numbers in the user's input field."""
        self.ui.view_3d.current_rod = int(number)
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
        tab_idx = self.ui.camera_tabs.currentIndex()
        self.image_managers[tab_idx].next_image(direction)

    def original_size(self):
        """Displays the currently loaded image in its native size.

        Returns
        -------
        None
        """
        tab_idx = self.ui.camera_tabs.currentIndex()
        self.cameras[tab_idx].scale_factor = 1
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
        tab_idx = self.ui.camera_tabs.currentIndex()
        self.cameras[tab_idx].scale_to_size(to_size)

    def scale_image(self, factor):
        """Sets a new relative scaling for the current image.

        Sets a new scaling to the currently displayed image. The scaling factor
        acts relative to the already applied scaling.

        Parameters
        ----------
        factor : float
            The relative scaling factor. Example:
            factor=1.1, current scaling=2.0     ->  new scaling=2.2

        Returns
        -------
        None
        """
        tab_idx = self.ui.camera_tabs.currentIndex()
        new_zoom = self.cameras[tab_idx].scale_factor * factor
        self.cameras[tab_idx].scale_factor = new_zoom
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
            self.ui.tv_rods.update_tree_folding(self.logger.frame,
                                                self.last_color)
            self.ui.view_3d.update_color(self.last_color)

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
        self.ui.tv_rods.new_rod(self.logger.frame, self.last_color, number)

        cam = self.cameras[self.ui.camera_tabs.currentIndex()]
        new_rod = rn.RodNumberWidget(self.last_color, cam, str(number))
        new_rod.rod_id = number
        new_rod.setObjectName(f"rn_{number}")
        new_rod.rod_points = new_position
        new_rod.rod_state = rn.RodState.SELECTED
        # Newly created rods are always "seen"
        new_rod.seen = True
        new_rods = []
        for rod in cam.edits:
            new_rods.append(rod.copy())
        new_rods.append(new_rod)
        cam.edits = new_rods
        last_action = lg.CreateRodAction(new_rod.copy())
        cam.logger.add_action(last_action)

    @QtCore.pyqtSlot(lg.Action)
    def catch_data(self, change: lg.Action) -> None:
        """Changes the data stored in RAM according to the Action performed."""
        new_data = change.to_save()
        if new_data is None:
            return

        worker = pl.Worker(d_ops.change_data, new_data=new_data)
        worker.signals.result.connect(self.update_changed_data)
        self.threads.start(worker)

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
                self.ui.tv_rods.update_tree(tmp_data, no_gen=True)
            self.ui.tv_rods.generate_tree()
        else:
            self.ui.tv_rods.update_tree(new_data)

    @QtCore.pyqtSlot(object)
    def update_changed_data(self, _):
        """Updates the main data storage in RAM (used for communication
        with threads)."""
        cam = self.cameras[self.ui.camera_tabs.currentIndex()]
        previously_selected = cam.active_rod
        if not previously_selected:
            return
        self.load_rods()
        cam.rod_activated(previously_selected)

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
            tmp_file = self.data_files / self.data_file_name.format(color)
            df_current = d_ops.rod_data.loc[
                d_ops.rod_data.color == color].copy()
            df_current = df_current.astype({"frame": 'int', "particle": 'int'})
            df_current.to_csv(tmp_file, index_label="")
        d_ops.lock.unlock()

        if temp_only:
            # skip permanent saving
            return

        save_dir = self.ui.le_save_dir.text()
        if save_dir == self.ui.le_rod_dir.text() and not self._allow_overwrite:
            msg = QMessageBox()
            msg.setWindowIcon(QtGui.QIcon(fl.icon_path()))
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
        save_dir = pathlib.Path(save_dir)
        if not save_dir.exists():
            save_dir.mkdir()

        for file in self.data_files.iterdir():
            save_file = save_dir / file.name
            shutil.copy2(file, save_file)
            this_action = lg.FileAction(save_file, lg.FileActions.SAVE)
            this_action.parent_id = self.logger_id
            self.ui.lv_actions_list.add_action(this_action)
        # notify loggers that everything was saved
        self.saving_finished.emit()

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
        msg.setWindowIcon(QtGui.QIcon(fl.icon_path()))
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
                self.ui.tv_rods.update_tree_folding(self.logger.frame,
                                                    to_color)

    @QtCore.pyqtSlot(lg.NumberChangeActions, int, int)
    @QtCore.pyqtSlot(lg.NumberChangeActions, int, int, str, int, str, bool)
    def catch_number_switch(self, mode: lg.NumberChangeActions, old_id: int,
                            new_id: int, color: str = None, frame: int = None,
                            cam_id: str = None, log: bool = True):
        """Handles changes of rod numbers for more than the current frame and
        camera."""
        cam = self.cameras[self.ui.camera_tabs.currentIndex()]
        if color is None:
            color = self.get_selected_color()
        if frame is None:
            frame = self.logger.frame
        if cam_id is None:
            cam_id = cam.cam_id

        worker = pl.Worker(d_ops.rod_number_swap, mode=mode,
                           previous_id=old_id, new_id=new_id, color=color,
                           frame=frame, cam_id=cam_id)
        worker.signals.result.connect(self.update_changed_data)
        self.threads.start(worker)

        if log:
            cam.logger.add_action(
                lg.NumberExchange(mode, old_id, new_id,
                                  self.get_selected_color(), self.logger.frame,
                                  cam.cam_id)
            )
        return

    def change_view(self, direction: int) -> None:
        """Helper method for programmatic changes of the camera tabs."""
        old_idx = self.ui.camera_tabs.currentIndex()
        new_idx = old_idx + direction
        if new_idx > (self.ui.camera_tabs.count() - 1):
            new_idx -= self.ui.camera_tabs.count()
        elif new_idx < 0:
            new_idx += self.ui.camera_tabs.count()
        self.ui.camera_tabs.setCurrentIndex(new_idx)

    @QtCore.pyqtSlot(int)
    def view_changed(self, new_idx: int):
        """Handles switches between the camera tabs.

        Handles the switches between the camera tabs and depending on the
        GUI state tries to load the same frame for the newly displayed tab
        as in the old one. If no frame is available in the new tab it
        displays a dummy graphic and logs a warning message.

        Parameters
        ----------
        new_idx : int
            The index of the tab that is shown next.

        Returns
        -------
        None
        """
        manager = self.image_managers[new_idx]
        cam = self.cameras[new_idx]

        reconnect(
            self.ui.action_shorten_displayed.triggered,
            lambda: cam.adjust_rod_length(-self._rod_incr, False))
        reconnect(
            self.ui.action_lengthen_displayed.triggered,
            lambda: cam.adjust_rod_length(self._rod_incr, False))
        reconnect(
            self.ui.action_shorten_selected.triggered,
            lambda: cam.adjust_rod_length(-self._rod_incr, True))
        reconnect(
            self.ui.action_lengthen_selected.triggered,
            lambda: cam.adjust_rod_length(self._rod_incr, True))

        reconnect(
            self.ui.pb_load_images.clicked,
            lambda: manager.select_images(self.ui.le_image_dir.text()))
        reconnect(
            self.ui.action_open.triggered,
            lambda: manager.select_images(self.ui.le_image_dir.text()))
        reconnect(
            self.ui.le_image_dir.returnPressed,
            lambda: manager.select_images(self.ui.le_image_dir.text()))

        if manager.folder is None:
            self.ui.le_image_dir.setText("")
        else:
            self.ui.le_image_dir.setText(str(manager.folder))

        if self.ui.action_persistent_view.isChecked():
            # Ensure the image/frame number is consistent over views
            old_frame = self.logger.frame
            if manager.frames:
                idx_diff = manager.frames.index(old_frame) - manager.frame_idx
                self.show_next(idx_diff)

        if self.ui.cb_overlay.isChecked():
            # ensure that rods are loaded
            self.load_rods()

    def requesting_undo(self) -> None:
        """Helper method to emit a request for reverting the last action."""
        cam = self.cameras[self.ui.camera_tabs.currentIndex()]
        self.request_undo.emit(cam.cam_id)

    def requesting_redo(self) -> None:
        """Helper method to emit a request for repeating the last action."""
        cam = self.cameras[self.ui.camera_tabs.currentIndex()]
        self.request_redo.emit(cam.cam_id)

    @QtCore.pyqtSlot(bool, str)
    def tab_has_changes(self, has_changes: bool, cam_id: str) -> None:
        """Changes the current tabs text to indicate it has (no) changes."""
        for i in range(self.ui.camera_tabs.count()):
            tab_txt = self.ui.camera_tabs.tabText(i)
            if cam_id not in tab_txt:
                continue

            if has_changes:
                if tab_txt[-1] == "*":
                    return
                new_text = tab_txt + "*"
            else:
                if tab_txt[-1] != "*":
                    return
                new_text = tab_txt[0:-1]
            self.ui.camera_tabs.setTabText(i, new_text)

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
            msg.setWindowIcon(QtGui.QIcon(fl.icon_path()))
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
            # No position data loaded
            return
        to_delete = d_ops.find_unused_rods()
        if len(to_delete):
            confirm = dialogs.ConfirmDeleteDialog(to_delete, parent=self)
            if confirm.exec():
                delete_idx = to_delete.index[confirm.confirmed_delete]
                if len(delete_idx):
                    d_ops.lock.lockForWrite()
                    # deleted_rows = d_ops.rod_data.loc[delete_idx].copy()
                    d_ops.rod_data = d_ops.rod_data.drop(index=delete_idx)
                    d_ops.lock.unlock()
                    performed_action = lg.PermanentRemoveAction(
                        len(delete_idx))
                    self.logger.add_action(performed_action)
                    # Update rods and tree display
                    worker = pl.Worker(d_ops.extract_seen_information)
                    worker.signals.result.connect(self.ui.tv_rods.setup_tree)
                    self.threads.start(worker)

                    self.load_rods()
                else:
                    lg._logger.info("No rods confirmed for permanent "
                                    "deletion.")
            else:
                # Aborted data cleaning
                return
        else:
            # No unused rods found for deletion
            return


def reconnect(signal: QtCore.pyqtSignal, newhandler: Callable = None,
              oldhandler: Callable = None) -> None:
    """(Re-)connect handler(s) to a signal.

    Connect a new handler function to a signal while either removing all other,
    previous handlers, or just one specific one.

    Parameters
    ----------
    signal : QtCore.pyqtSignal
    newhandler : Callable, optional
        By default None.
    oldhandler : Callable, optional
        Handler function currently connected to `signal`. All connected
        functions will be removed, if this parameters is None.
        By default None.
    """
    try:
        if oldhandler is not None:
            while True:
                signal.disconnect(oldhandler)
        else:
            signal.disconnect()
    except TypeError:
        pass
    if newhandler is not None:
        signal.connect(newhandler)
