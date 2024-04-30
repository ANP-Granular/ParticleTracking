# Copyright (c) 2023-24 Adrian Niemann, Dmitry Puzyrev, and others
#
# This file is part of RodTracker.
# RodTracker is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RodTracker is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RodTracker. If not, see <http://www.gnu.org/licenses/>.

"""**TBD**"""

import platform
from functools import partial
from pathlib import Path
from typing import Callable, List

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtWidgets import (
    QMessageBox,
    QRadioButton,
    QScrollArea,
    QTreeWidgetItem,
)

import RodTracker.backend.file_locations as fl
import RodTracker.backend.img_data as img_data
import RodTracker.backend.logger as lg
import RodTracker.backend.rod_data as r_data
import RodTracker.backend.settings as se
import RodTracker.ui.mainwindow_layout as mw_l
import RodTracker.ui.rodnumberwidget as rn
from RodTracker.ui import dialogs
from RodTracker.ui.detection import init_detection
from RodTracker.ui.reconstruction import init_reconstruction
from RodTracker.ui.settings_setup import init_settings


class RodTrackWindow(QtWidgets.QMainWindow):
    """The main window for the Rod Tracker application.

    This class handles most of the interaction between the user and the GUI
    elements of the Rod Tracker application. It also sets up the backend
    objects necessary for this application.

    Parameters
    ----------
    *args : iterable
        Positional arguments for the ``QMainWindow`` superclass.
    **kwargs : dict
        Keyword arguments for the ``QMainWindow`` superclass.


    .. admonition:: Signals

        - :attr:`request_undo`
        - :attr:`request_redo`

    .. admonition:: Slots

        - :meth:`color_change`
        - :meth:`change_color`
        - :meth:`display_rod_changed`
        - :meth:`images_loaded`
        - :meth:`method_2D_changed`
        - :meth:`method_3D_changed`
        - :meth:`next_image`
        - :meth:`rods_loaded`
        - :meth:`show_2D_changed`
        - :meth:`show_3D_changed`
        - :meth:`slider_moved`
        - :meth:`tab_has_changes`
        - :meth:`tree_selection`
        - :meth:`update_settings`
        - :meth:`view_changed`

    Attributes
    ----------
    ui : Ui_MainWindow
        The GUI main window object, that contains all other visual objects.
    cameras : List[RodImageWidget]
        A copy of all image display objects (views) from the GUI main window.
    image_managers : List[ImageData]
        Manager objects for loaded/selected image datasets. There is one
        associated with each :class:`.RodImageWidget` in :attr:`cameras`.
    """

    request_undo = QtCore.pyqtSignal(str, name="request_undo")
    """pyqtSignal(str) : Is emitted when the user wants to revert an action.

    The payload is the ID of the widget on which the last action shall be
    reverted.
    """

    request_redo = QtCore.pyqtSignal(str, name="request_redo")
    """pyqtSignal(str) : Is emitted when the user wants to redo a previously
    reverted action.

    The payload is the ID of the widget on which the last action shall
    be redone.
    """

    logger_id: str = "main"
    """str : The ID provided to the logger for accountability of the actions in
    the GUI.

    Default is ``"main"``.
    """

    logger: lg.ActionLogger
    """ActionLogger : A logger object keeping track of users' actions performed
    on the main window, i.e. data and image loading and saving.
    """

    _rod_incr: float = 1.0
    _fit_next_img: bool = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        pb_load_size = self.ui.pb_load_images.fontMetrics().width(pb_load_txt)
        pb_rod_txt = self.ui.pb_load_rods.text()
        pb_rod_size = self.ui.pb_load_rods.fontMetrics().width(pb_rod_txt)
        max_width = pb_rod_size if pb_rod_size > pb_load_size else pb_load_size
        self.ui.pb_load_images.setMaximumWidth(int(2 * max_width))
        self.ui.pb_load_rods.setMaximumWidth(int(2 * max_width))
        cb_ov_txt = self.ui.cb_overlay.text()
        cb_ov_size = self.ui.cb_overlay.fontMetrics().width(cb_ov_txt)
        self.ui.cb_overlay.setMaximumWidth(int(2 * cb_ov_size))
        # Set possible inputs for rod selection field
        self.ui.le_disp_one.setInputMask("99")
        self.ui.le_disp_one.setText("00")

        self.ui.action_autoselect_rods.setChecked(False)
        self.ui.action_fit_to_window.setShortcut(QtGui.QKeySequence("F"))

        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.setFocus()

        # Initialize
        self.rod_data = r_data.RodData()
        id = self.rod_data._logger_id
        self.rod_data._logger = self.ui.lv_actions_list.get_new_logger(id)
        self.rod_data.show_2D = self.ui.cb_overlay.isChecked()
        self.rod_data.show_3D = self.ui.cb_show_3D.isChecked()

        self.image_managers = [img_data.ImageData(0), img_data.ImageData(1)]
        for manager in self.image_managers:
            id = manager._logger_id
            manager._logger = self.ui.lv_actions_list.get_new_logger(id)

        self.cameras = [self.ui.camera_0, self.ui.camera_1]
        for cam in self.cameras:
            cam.logger = self.ui.lv_actions_list.get_new_logger(cam.cam_id)
            cam.setPixmap(QtGui.QPixmap(fl.logo_path()))
            cam.autoselect = self.ui.action_autoselect_rods.isChecked()

        self.logger = self.ui.lv_actions_list.get_new_logger(self.logger_id)
        self.ui.sa_camera_0.verticalScrollBar().installEventFilter(self)
        self.ui.sa_camera_1.verticalScrollBar().installEventFilter(self)
        self.switch_right = QtWidgets.QShortcut(
            QtGui.QKeySequence("Ctrl+tab"), self
        )
        self.ui.slider_frames.setMinimum(0)
        self.ui.slider_frames.setMaximum(1)
        self.settings = se.Settings()

        init_settings(self.ui, self.settings)
        rn.RodNumberWidget.settings_signal = self.settings.settings_changed
        self.reconstructor = init_reconstruction(self.ui)
        self.detector = init_detection(self.ui, self.image_managers)
        if self.detector is not None:
            self.detector._logger = self.ui.lv_actions_list.get_new_logger(
                "Detector"
            )

        # Tab icons for 'busy' indication
        default_icon = blank_icon()
        self.ui.right_tabs.setIconSize(QtCore.QSize(7, 16))
        for tab in range(self.ui.right_tabs.count()):
            self.ui.right_tabs.setTabIcon(tab, default_icon)

        self.connect_signals()
        self.settings.send_settings()

    def connect_signals(self):
        """Connect all signals and slots of the Rod Tracker objects."""
        tab_idx = self.ui.camera_tabs.currentIndex()
        # Opening files
        self.ui.action_open_rods.triggered.connect(
            partial(self.rod_data.select_rods, self.ui.le_rod_dir.text())
        )
        self.ui.pb_load_rods.clicked.connect(
            partial(self.rod_data.select_rods, self.ui.le_rod_dir.text())
        )
        self.ui.le_rod_dir.returnPressed.connect(
            partial(self.rod_data.select_rods, self.ui.le_rod_dir.text())
        )

        # Data loading
        self.rod_data.data_loaded.connect(self.rods_loaded)
        self.rod_data.data_loaded[list].connect(
            lambda colors: self.rods_loaded(None, None, colors)
        )
        self.rod_data.seen_loaded.connect(self.ui.tv_rods.setup_tree)
        self.rod_data.is_busy.connect(
            lambda busy: self.tab_busy_changed(0, busy)
        )

        # Saving
        self.ui.pb_save_rods.clicked.connect(self.rod_data.save_changes)
        self.ui.action_save.triggered.connect(self.rod_data.save_changes)
        self.rod_data.saved.connect(self.logger.actions_saved)
        self.ui.le_save_dir.textChanged.connect(self.rod_data.set_out_folder)

        # Undo/Redo
        self.ui.action_revert.triggered.connect(self.requesting_undo)
        self.ui.pb_undo.clicked.connect(self.requesting_undo)
        self.ui.action_redo.triggered.connect(self.requesting_redo)

        # View controls
        self.ui.action_zoom_in.triggered.connect(
            lambda: self.scale_image(factor=1.25)
        )
        self.ui.action_zoom_out.triggered.connect(
            lambda: self.scale_image(factor=0.8)
        )
        self.ui.action_original_size.triggered.connect(self.original_size)
        self.ui.action_fit_to_window.triggered.connect(self.fit_to_window)
        self.ui.pb_front.clicked.connect(self.ui.view_3d.show_front)
        self.ui.pb_top.clicked.connect(self.ui.view_3d.show_top)

        # Displayed data
        self.ui.cb_overlay.stateChanged.connect(self.show_2D_changed)
        for rb in self.ui.group_rod_color.findChildren(QRadioButton):
            rb.toggled.connect(self.color_change)
        self.ui.pb_previous.clicked.connect(
            lambda: self.show_next(direction=-1)
        )
        self.ui.pb_next.clicked.connect(lambda: self.show_next(direction=1))
        self.switch_right.activated.connect(lambda: self.change_view(1))
        self.ui.camera_tabs.currentChanged.connect(self.view_changed)
        self.ui.slider_frames.sliderMoved.connect(self.slider_moved)
        self.ui.tv_rods.itemClicked.connect(self.tree_selection)
        self.rod_data.data_2d.connect(self.cameras[tab_idx].extract_rods)
        self.rod_data.data_3d.connect(self.ui.view_3d.update_rods)
        self.rod_data.data_update.connect(self.ui.tv_rods.update_tree)
        self.rod_data.batch_update.connect(self.ui.tv_rods.batch_update_tree)

        if self.reconstructor is not None:
            self.reconstructor.is_busy.connect(
                lambda busy: self.tab_busy_changed(5, busy)
            )
            self.rod_data.data_loaded[int, int, list].connect(
                self.reconstructor.data_loaded
            )
            self.rod_data.data_loaded[str, str].connect(
                self.reconstructor.set_cam_ids
            )
            self.reconstructor.request_data.connect(
                lambda frames, colors: self.rod_data.get_data(frames, colors)
            )
            self.rod_data.requested_data.connect(
                self.reconstructor.data_update
            )
            self.reconstructor.updated_data.connect(
                self.rod_data.receive_updated_data
            )
            self.rod_data.data_loaded[str, str].connect(
                self.reconstructor.set_cam_ids
            )

        if self.detector is not None:
            self.detector.is_busy.connect(
                lambda busy: self.tab_busy_changed(4, busy)
            )
            self.detector.detected_data.connect(self.rod_data.add_data)
            self.rod_data.saved.connect(self.detector._logger.actions_saved)

        # Display methods
        self.ui.le_disp_one.textChanged.connect(self.display_rod_changed)
        for rb in self.ui.group_disp_method.findChildren(QRadioButton):
            rb.toggled.connect(self.method_2D_changed)

        # 3D display methods
        for rb in self.ui.group_3D_mode.findChildren(QRadioButton):
            rb.toggled.connect(self.method_3D_changed)
        self.ui.cb_show_3D.stateChanged.connect(self.show_3D_changed)

        # 2D display and data provider widgets
        for cam, manager in zip(self.cameras, self.image_managers):
            manager.data_loaded.connect(self.images_loaded)
            manager.next_img[int, int].connect(self.next_image)
            manager.next_img[int, int].connect(
                lambda frame, idx: cam.frame(frame)
            )
            manager.next_img[QtGui.QImage].connect(cam.image)
            if str(tab_idx) in manager._logger_id:
                self.ui.pb_load_images.clicked.connect(
                    partial(manager.select_images, self.ui.le_image_dir.text())
                )
                self.ui.action_open.triggered.connect(
                    partial(manager.select_images, self.ui.le_image_dir.text())
                )
                self.ui.le_image_dir.returnPressed.connect(
                    partial(manager.select_images, self.ui.le_image_dir.text())
                )
            if self.ui.cb_overlay.isChecked():
                manager.next_img[int, int].connect(self.rod_data.update_frame)

            cam.request_color_change.connect(self.change_color)
            cam.request_frame_change.connect(manager.image_at)
            cam.normal_frame_change.connect(self.show_next)
            cam.logger.notify_unsaved.connect(self.tab_has_changes)
            cam.logger.request_saving.connect(self.rod_data.save_changes)
            cam.logger.data_changed.connect(self.rod_data.catch_data)
            self.rod_data.saved.connect(cam.logger.actions_saved)
            cam.number_switches[lg.NumberChangeActions, int, int, str].connect(
                self.rod_data.catch_number_switch
            )
            cam.number_switches[
                lg.NumberChangeActions, int, int, str, str, int
            ].connect(self.rod_data.catch_number_switch)
            self.request_undo.connect(cam.logger.undo_last)
            self.request_redo.connect(cam.logger.redo_last)
            self.settings.settings_changed.connect(cam.update_settings)
            cam.loaded_rods.connect(
                lambda n: self.ui.le_rod_disp.setText(f"Loaded Particles: {n}")
            )
            self.ui.action_autoselect_rods.toggled.connect(cam.set_autoselect)

        # Data manipulation
        self.ui.action_cleanup.triggered.connect(self.rod_data.clean_data)
        self.ui.action_shorten_displayed.triggered.connect(
            lambda: self.cameras[tab_idx].adjust_rod_length(
                -self._rod_incr, False
            )
        )
        self.ui.action_lengthen_displayed.triggered.connect(
            lambda: self.cameras[tab_idx].adjust_rod_length(
                self._rod_incr, False
            )
        )
        self.ui.action_shorten_selected.triggered.connect(
            lambda: self.cameras[tab_idx].adjust_rod_length(
                -self._rod_incr, True
            )
        )
        self.ui.action_lengthen_selected.triggered.connect(
            lambda: self.cameras[tab_idx].adjust_rod_length(
                self._rod_incr, True
            )
        )

        # Settings
        self.settings.settings_changed.connect(self.update_settings)
        self.settings.settings_changed.connect(
            rn.RodNumberWidget.update_defaults
        )
        self.settings.settings_changed.connect(self.ui.view_3d.update_settings)
        self.settings.settings_changed.connect(self.rod_data.update_settings)
        if self.reconstructor is not None:
            self.settings.settings_changed.connect(
                self.reconstructor.update_settings
            )
        if self.detector is not None:
            self.settings.settings_changed.connect(
                self.detector.update_settings
            )

        # Logging
        self.logger.notify_unsaved.connect(self.tab_has_changes)
        self.logger.data_changed.connect(self.rod_data.catch_data)

        # Help
        self.ui.action_docs_local.triggered.connect(
            lambda: fl.open_docs("local")
        )
        self.ui.action_docs_online.triggered.connect(
            lambda: fl.open_docs("online")
        )
        self.ui.action_about.triggered.connect(
            lambda: dialogs.show_about(self)
        )
        self.ui.action_about_qt.triggered.connect(
            lambda: QMessageBox.aboutQt(self, "RodTracker")
        )
        self.ui.action_logs.triggered.connect(lg.open_logs)
        self.ui.action_bug_report.triggered.connect(
            lambda: QtGui.QDesktopServices.openUrl(
                QtCore.QUrl(
                    "https://github.com/ANP-Granular/ParticleTracking/issues/new?labels=bug&projects=&template=bug_report.md&title="  # noqa: E501
                )
            )
        )
        self.ui.action_feature_request.triggered.connect(
            lambda: QtGui.QDesktopServices.openUrl(
                QtCore.QUrl(
                    "https://github.com/ANP-Granular/ParticleTracking/issues/new?labels=enhancement&projects=&template=feature_request.md&title="  # noqa: E501
                )
            )
        )

    @QtCore.pyqtSlot(QTreeWidgetItem, int)
    def tree_selection(self, item: QTreeWidgetItem, col: int):
        """Handle the selection of a rod & frame in the :class:`.RodTree`
        widget.

        Parameters
        ----------
        item : QTreeWidgetItem
            Selected item in the :class:`.RodTree` widget.
        col : int
            Column of the :class:`.RodTree` widget the item was selected in.
        """
        if not item.childCount():
            # Change camera
            # TODO
            # Change color
            color = item.parent().text(0)
            self.change_color(color)
            # Change frame
            frame = int(item.parent().parent().text(0)[7:])
            tab_idx = self.ui.camera_tabs.currentIndex()
            self.image_managers[tab_idx].image(frame)
            # Activate clicked rod
            cam = self.cameras[tab_idx]
            if cam.rods:
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
        """Catches updates of the settings from a :class:`.Settings` class.

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

        self.ui.tv_rods.update_tree_folding(frame, self.get_selected_color())

        if not self.ui.action_persistent_view.isChecked():
            self.fit_to_window()
            del self.cameras[self.ui.camera_tabs.currentIndex()].rods

    @QtCore.pyqtSlot(int, str, Path)
    def images_loaded(self, frames: int, cam_id: str, folder: Path):
        """Handles updates of loaded image datasets.

        Updates GUI elements to match the newly loaded image dataset.

        Parameters
        ----------
        frames : int
            Number of loaded frames.
        cam_id : str
            ID of the loaded dataset/folder/camera.
        folder : Path
            Folder from which the images were loaded.
        """
        self._fit_next_img = True
        # Set new camera ID
        tab_idx = self.ui.camera_tabs.currentIndex()
        tab_text = self.ui.camera_tabs.tabText(tab_idx)
        front_text = tab_text.split("(")[0]
        end_text = tab_text.split(")")[-1]
        new_text = front_text + "(" + cam_id + ")" + end_text
        self.ui.camera_tabs.setTabText(tab_idx, new_text)
        self.cameras[tab_idx].cam_id = cam_id

        # Update slider
        self.ui.slider_frames.setMaximum(frames - 1)
        self.ui.slider_frames.setSliderPosition(0)
        self.ui.le_frame_disp.setText("Frame: ???")

        # Update folder display
        self.ui.le_image_dir.setText(str(folder))

    @QtCore.pyqtSlot(Path, Path, list)
    def rods_loaded(self, input: Path, output: Path, new_colors: List[str]):
        """Handles updates of loaded rod position datasets.

        Updates GUI elements to match the newly loaded rod position dataset.

        Parameters
        ----------
        input : Path
            Path to the folder the position data is loaded from.
        output : Path
            Path to the (automatically) selected folder for later output of the
            corrected dataset.
        new_colors : List[str]
            Colors for which data is available in the loaded dataset.
        """
        # Update visual elements
        if input is not None:
            self.ui.le_rod_dir.setText(str(input))
        if output is not None:
            self.ui.le_save_dir.setText(str(output))

        rb_colors = self.ui.group_rod_color.findChildren(
            QtWidgets.QRadioButton
        )
        rb_color_texts = [btn.text().lower() for btn in rb_colors]
        group_layout: QtWidgets.QGridLayout = self.ui.group_rod_color.layout()
        for btn in rb_colors:
            group_layout.removeWidget(btn)
            if btn.text().lower() not in new_colors:
                btn.hide()
                btn.deleteLater()
        row = 0
        col = 0
        for color in new_colors:
            try:
                btn = rb_colors[rb_color_texts.index(color)]
            except ValueError:
                # Create new QRadioButton for this color
                btn = QtWidgets.QRadioButton(text=color.lower())
                btn.setObjectName(f"rb_{color}")
                btn.toggled.connect(self.color_change)
            group_layout.addWidget(btn, row, col)
            if row == 1:
                row = 0
                col += 1
            else:
                row = 1
        group_layout.itemAtPosition(0, 0).widget().toggle()
        if platform.system() == "Windows":
            self.color_change(True)

    @QtCore.pyqtSlot(bool)
    def method_2D_changed(self, _: bool) -> None:
        """Handles changes of 2D display method selection."""
        if self.ui.rb_disp_all.isChecked():
            self.rod_data.update_rod_2D()
        elif self.ui.rb_disp_one.isChecked():
            self.rod_data.update_rod_2D(int(self.ui.le_disp_one.text()))

    @QtCore.pyqtSlot(bool)
    def method_3D_changed(self, _: bool) -> None:
        """Handles changes of 3D display method selection."""
        self.ui.view_3d.clear()
        if self.ui.rb_all_3d.isChecked():
            self.rod_data.update_color_3D(send=False)
            self.rod_data.update_rod_3D()
        elif self.ui.rb_color_3d.isChecked():
            self.rod_data.update_rod_3D(send=False)
            self.rod_data.update_color_3D(self.get_selected_color())
        elif self.ui.rb_one_3d.isChecked():
            self.rod_data.update_color_3D(self.get_selected_color(), False)
            self.rod_data.update_rod_3D(int(self.ui.le_disp_one.text()))

    @QtCore.pyqtSlot(str)
    def display_rod_changed(self, number: str):
        """Handles a change of rod numbers in the user's input field."""
        rod = int(number)
        if self.ui.rb_disp_one.isChecked():
            self.rod_data.update_rod_2D(rod)
        if self.ui.rb_one_3d.isChecked():
            self.rod_data.update_rod_3D(rod)

    @QtCore.pyqtSlot(int)
    def show_2D_changed(self, state: int):
        """Catches a ``QCheckBox`` state change to display or clear rods in 2D.

        Parameters
        ----------
        state : int
            The new state of the QCheckbox {0, 2}

        Returns
        -------
        None
        """
        if state == 0:
            # Deactivated
            self.cameras[self.ui.camera_tabs.currentIndex()].clear_screen()
        self.rod_data.show_2D = bool(state)

    @QtCore.pyqtSlot(int)
    def show_3D_changed(self, state: int):
        """Catches a ``QCheckBox`` state change to display or clear rods in 3D.

        Parameters
        ----------
        state : int
            The new state of the QCheckbox {0, 2}

        Returns
        -------
        None
        """
        if state == 0:
            # Deactivated
            self.ui.view_3d.clear()
        self.rod_data.show_3D = bool(state)

    def show_next(self, direction: int):
        """Attempt to open the next image.

        Attempt to open the next image in the direction provided relative to
        the currently opened image.

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
        """Displays the currently loaded image in its native size."""
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
        current_sa = self.findChild(
            QScrollArea, f"sa_camera_" f"{self.ui.camera_tabs.currentIndex()}"
        )
        to_size = current_sa.size()
        to_size = QtCore.QSize(to_size.width() - 20, to_size.height() - 20)
        tab_idx = self.ui.camera_tabs.currentIndex()
        self.cameras[tab_idx].scale_to_size(to_size)

    def scale_image(self, factor: float):
        """Sets a new relative scaling for the current image.

        Sets a new scaling to the currently displayed image. The scaling factor
        acts relative to the already applied scaling.

        Parameters
        ----------
        factor : float
            The relative scaling factor. Example:\n
            ``factor=1.1``, current scaling: ``2.0``  ==>  new scaling: ``2.2``

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
        """Handles changes of the ``QRadioButtons`` for color selection."""
        if state:
            color = self.get_selected_color()
            self.rod_data.update_color_2D(color)
            self.ui.tv_rods.update_tree_folding(self.logger.frame, color)
            if (
                self.ui.rb_color_3d.isChecked()
                or self.ui.rb_one_3d.isChecked()
            ):
                self.rod_data.update_color_3D(color)

    @staticmethod
    def warning_unsaved() -> bool:
        """Warns that there are unsaved changes that might get lost.

        Issues a warning popup to the user to either discard any unsaved
        changes or stay in the current state to prevent changes get lost.

        Returns
        -------
        bool
            ``True``, if changes shall be discarded.
            ``False``, if the user aborted.
        """
        msg = QMessageBox()
        msg.setWindowIcon(QtGui.QIcon(fl.icon_path()))
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Rod Tracker")
        msg.setText("There are unsaved changes!")
        btn_discard = msg.addButton("Discard changes", QMessageBox.ActionRole)
        btn_cancel = msg.addButton("Cancel", QMessageBox.ActionRole)
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
                # Activate the last color
                rb.toggle()
                self.ui.tv_rods.update_tree_folding(
                    self.logger.frame, to_color
                )

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
        as in the old one.

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

        reconnect(self.rod_data.data_2d, cam.extract_rods)

        reconnect(
            self.ui.action_shorten_displayed.triggered,
            lambda: cam.adjust_rod_length(-self._rod_incr, False),
        )
        reconnect(
            self.ui.action_lengthen_displayed.triggered,
            lambda: cam.adjust_rod_length(self._rod_incr, False),
        )
        reconnect(
            self.ui.action_shorten_selected.triggered,
            lambda: cam.adjust_rod_length(-self._rod_incr, True),
        )
        reconnect(
            self.ui.action_lengthen_selected.triggered,
            lambda: cam.adjust_rod_length(self._rod_incr, True),
        )

        reconnect(
            self.ui.pb_load_images.clicked,
            lambda: manager.select_images(self.ui.le_image_dir.text()),
        )
        reconnect(
            self.ui.action_open.triggered,
            lambda: manager.select_images(self.ui.le_image_dir.text()),
        )
        reconnect(
            self.ui.le_image_dir.returnPressed,
            lambda: manager.select_images(self.ui.le_image_dir.text()),
        )

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

    def requesting_undo(self) -> None:
        """Helper method to emit a request for reverting the last action.


        .. hint::

            **Emits**

                - :attr:`request_undo`
        """
        cam = self.cameras[self.ui.camera_tabs.currentIndex()]
        self.request_undo.emit(cam.cam_id)

    def requesting_redo(self) -> None:
        """Helper method to emit a request for repeating the last action.


        .. hint::

            **Emits**

                - :attr:`request_redo`
        """
        cam = self.cameras[self.ui.camera_tabs.currentIndex()]
        self.request_redo.emit(cam.cam_id)

    def attempt_saving(self) -> None:
        """Handles the propagation of a saving attempt by a user."""
        if not self.ui.lv_actions_list.unsaved_changes:
            return
        self.rod_data.save_changes()

    @QtCore.pyqtSlot(bool, str)
    def tab_has_changes(self, has_changes: bool, cam_id: str) -> None:
        """Changes the tabs text to indicate it has (no) changes.

        Parameters
        ----------
        has_changes : bool
        cam_id : str
            Camera which indicated it now has (no) changes.
        """
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

    def tab_busy_changed(self, tab_idx: int, is_busy: bool):
        if is_busy:
            tab_icon = busy_icon()
        else:
            tab_icon = blank_icon()
        self.ui.right_tabs.setTabIcon(tab_idx, tab_icon)

    def eventFilter(
        self, source: QtCore.QObject, event: QtCore.QEvent
    ) -> bool:
        """Intercepts events, here modified scroll events for zooming.

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
        """
        if source not in [
            self.ui.sa_camera_0.verticalScrollBar(),
            self.ui.sa_camera_1.verticalScrollBar(),
        ]:
            return False
        if not isinstance(event, QtGui.QWheelEvent):
            return False

        event = QWheelEvent(event)
        if not event.modifiers() == QtCore.Qt.ControlModifier:
            return False
        factor = 1.0
        if event.angleDelta().y() < 0:
            factor = 0.8
        elif event.angleDelta().y() > 0:
            factor = 1.25
        self.scale_image(factor)
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

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        """Reimplements ``QMainWindow.closeEvent(a0)``.

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
            btn_cancel = msg.addButton("Cancel", QMessageBox.ActionRole)
            msg.setDefaultButton(btn_save)
            msg.exec()
            if msg.clickedButton() == btn_save:
                self.rod_data.save_changes(temp_only=False)
                a0.accept()
                pass
            elif msg.clickedButton() == btn_cancel:
                a0.ignore()
            else:
                # Discards changes and proceeds with closing
                a0.accept()
        else:
            a0.accept()


def reconnect(
    signal: QtCore.pyqtSignal,
    newhandler: Callable = None,
    oldhandler: Callable = None,
) -> None:
    """(Re-)connect handler(s) to a signal.

    Connect a new handler function to a signal while either removing all other,
    previous handlers, or just one specific one.

    Parameters
    ----------
    signal : QtCore.pyqtSignal
    newhandler : Callable, optional
        By default ``None``.
    oldhandler : Callable, optional
        Handler function currently connected to ``signal``. All connected
        functions will be removed, if this parameters is ``None``.
        By default ``None``.
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


def busy_icon() -> QtGui.QIcon:
    busy_pix = QtGui.QPixmap(40, 100)
    busy_pix.fill(QtCore.Qt.transparent)
    busy_painter = QtGui.QPainter(busy_pix)
    busy_painter.setBrush(
        QtGui.QBrush(QtCore.Qt.green, QtCore.Qt.SolidPattern)
    )
    busy_painter.setPen(QtCore.Qt.NoPen)
    busy_painter.drawEllipse(0, 0, 40, 40)
    busy_painter.end()
    return QtGui.QIcon(busy_pix)


def blank_icon() -> QtGui.QIcon:
    blank_pix = QtGui.QPixmap(40, 100)
    blank_pix.fill(QtCore.Qt.transparent)
    return QtGui.QIcon(blank_pix)
