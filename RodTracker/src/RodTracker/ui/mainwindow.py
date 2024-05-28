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
import logging
import platform
from pathlib import Path
from typing import Any, Dict, List

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtWidgets import QMessageBox, QRadioButton, QScrollArea

import RodTracker.backend.file_locations as fl
import RodTracker.backend.logger as lg
import RodTracker.backend.miscellaneous as misc
import RodTracker.backend.settings as se
import RodTracker.ui.mainwindow_layout as mw_l
from RodTracker import APPNAME
from RodTracker.backend import data
from RodTracker.ui import dialogs, settings, tabs

_logger = logging.getLogger(__name__)


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

    class_changed = QtCore.pyqtSignal(str, name="class_changed")

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

    # Internal settings variables
    _min_zoom: float = 0.11
    _max_zoom: float = 9.0
    _zoom_factor: float = 1.25  # zooms in by 1.25 (and out by 0.8)

    _fit_next_img: bool = False
    _image_tabs: List[tabs.ImageInteractionTab] = []
    _utility_tabs: List[tabs.UtilityTab] = []
    _particle_data_conntections: Dict[str, data.PositionData] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = mw_l.Ui_MainWindow()
        self.ui.setupUi(self)

        # Adaptations of the UI
        self.setWindowTitle(APPNAME)
        self.setWindowIcon(QtGui.QIcon(fl.icon_path()))
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
        # Set possible inputs for rod selection field
        self.ui.le_disp_one.setInputMask("99")
        self.ui.le_disp_one.setText("00")

        self.ui.action_fit_to_window.setShortcut(QtGui.QKeySequence("F"))

        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.setFocus()

        self.logger = lg.MainLogger().get_new_logger(self.logger_id)
        self.switch_right = QtWidgets.QShortcut(
            QtGui.QKeySequence("Ctrl+tab"), self
        )
        self.ui.slider_frames.setMinimum(0)
        self.ui.slider_frames.setMaximum(1)
        self.settings = se.Settings()

        # Tab icons for 'busy' indication
        default_icon = misc.blank_icon()
        self.ui.right_tabs.setIconSize(QtCore.QSize(7, 16))
        for tab in range(self.ui.right_tabs.count()):
            self.ui.right_tabs.setTabIcon(tab, default_icon)

        self.connect_signals()

        # TODO: add the 'busy' indication for the camera tabs too!
        history_tab = tabs.HistoryTab("History")
        self.add_utility_tab(history_tab, history_tab.ID)
        history_tab.pb_undo.clicked.connect(self.requesting_undo)

        self.settings_tab = tabs.SettingsTab("Settings")
        self.add_utility_tab(self.settings_tab, self.settings_tab.ID)

        # Add settings
        min_zoom = settings.FloatSetting(
            "General.min_zoom", self._min_zoom, "Minimal allowed zoom: "
        )
        max_zoom = settings.FloatSetting(
            "General.max_zoom", self._max_zoom, "Maximal allowed zoom: "
        )
        zoom_factor = settings.FloatSetting(
            "General.zoom_factor", self._zoom_factor, "Zoom factor: "
        )

        self.add_setting(min_zoom)
        self.add_setting(max_zoom)
        self.add_setting(zoom_factor)

    def connect_signals(self):
        """Connect all signals and slots of the RodTracker objects."""
        # Undo/Redo
        self.ui.action_revert.triggered.connect(self.requesting_undo)
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

        # Displayed data
        for rb in self.ui.group_rod_color.findChildren(QRadioButton):
            rb.toggled.connect(self.color_change)
        self.ui.pb_previous.clicked.connect(
            lambda: self.show_next(direction=-1)
        )
        self.ui.pb_next.clicked.connect(lambda: self.show_next(direction=1))
        self.switch_right.activated.connect(lambda: self.change_view(1))
        self.ui.camera_tabs.currentChanged.connect(self.view_changed)
        self.ui.right_tabs.currentChanged.connect(self.utility_changed)
        self.ui.slider_frames.sliderMoved.connect(self.slider_moved)

        # Display methods
        self.ui.le_disp_one.textChanged.connect(
            lambda _: self.method_2D_changed()
        )
        for rb in self.ui.group_disp_method.findChildren(QRadioButton):
            rb.toggled.connect(self.method_2D_changed)

        # Settings
        self.settings.setting_signals.setting_changed.connect(
            self.update_settings
        )

        # Logging
        self.logger.notify_unsaved.connect(self.tab_has_changes)

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
            lambda: QMessageBox.aboutQt(self, APPNAME)
        )
        self.ui.action_logs.triggered.connect(misc.open_logs)
        self.ui.action_bug_report.triggered.connect(misc.report_issue)
        self.ui.action_feature_request.triggered.connect(misc.request_feature)

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
        self._image_tabs[tab_idx].image_manager.image_at(pos)

    @QtCore.pyqtSlot(str, object)
    def update_settings(self, key: str, new_value: Any):
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
        if key == "General.min_zoom":
            self._min_zoom = new_value
            # TODO: verify new min_zoom is not exceeded and adjust accordingly
        elif key == "General.max_zoom":
            self._max_zoom = new_value
            # TODO: verify new max_zoom is not exceeded and adjust accordingly
        elif key == "General.zoom_factor":
            self._zoom_factor = new_value

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
        # Fit the first image of a newly loaded dataset to the screen
        if self._fit_next_img:
            self.fit_to_window()
            self._fit_next_img = False

        # =====================================================================
        # TODO: this should not be done here! It should be handled by the
        #       extensions, because it is no longer part of the
        #       base-application. Should instead be integrated into the tabs'
        #       `activate()` function that is run above
        if not self.ui.action_persistent_view.isChecked():
            self.fit_to_window()
            # TODO: define what happens during the 'persistent_view' mode
        # =====================================================================

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

        # TODO: document this generation behaviour better
        if "(" in tab_text:
            front_text = tab_text.split("(")[0]
        else:
            front_text = tab_text
        if ")" in tab_text:
            end_text = tab_text.split(")")[-1]
        else:
            end_text = ""
        new_text = front_text + "(" + cam_id + ")" + end_text

        self.ui.camera_tabs.setTabText(tab_idx, new_text)
        self._image_tabs[tab_idx].image_manager.ID = cam_id

        # Update slider
        self.ui.slider_frames.setMaximum(frames - 1)
        self.ui.slider_frames.setSliderPosition(0)
        self.ui.le_frame_disp.setText("Frame: ???")

        # Update folder display
        self.ui.le_image_dir.setText(str(folder))

    # TODO: PROPERLY DEFINE A POS-DATA LOADING/SAVING FLOW
    @QtCore.pyqtSlot(Path, Path, list)
    def particles_loaded(
        self, input: Path, output: Path, new_classes: List[str]
    ):
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

        rb_classes = self.ui.group_rod_color.findChildren(
            QtWidgets.QRadioButton
        )
        rb_color_texts = [btn.text().lower() for btn in rb_classes]
        group_layout: QtWidgets.QGridLayout = self.ui.group_rod_color.layout()
        for btn in rb_classes:
            group_layout.removeWidget(btn)
            if btn.text().lower() not in new_classes:
                btn.hide()
                btn.deleteLater()
        row = 0
        col = 0
        for n_cls in new_classes:
            try:
                btn = rb_classes[rb_color_texts.index(n_cls)]
            except ValueError:
                # Create new QRadioButton for this color
                btn = QtWidgets.QRadioButton(text=n_cls.lower())
                btn.setObjectName(f"rb_{n_cls}")
                btn.toggled.connect(self.color_change)
            group_layout.addWidget(btn, row, col)
            # Allow 4 rows per column
            if row == 3:
                row = 0
                col += 1
            else:
                row += 1
        group_layout.itemAtPosition(0, 0).widget().toggle()
        if platform.system() == "Windows":
            self.color_change(True)

    # TODO: rename function (eliminate the '2D' in the name)
    @QtCore.pyqtSlot(bool)
    def method_2D_changed(self, activated: bool = None) -> None:
        """Handles changes of 2D display method selection."""
        if activated is False:
            # avoid triggering this multiple times when deactivating one
            #   radio button and activating the next one
            return
        if activated is None and not self.ui.rb_disp_one.isChecked():
            # 'activated' is only None when the selected particle changes.
            # Therefore, avoid re-triggering the display of when a display
            # method is selected that does not depend on the selected particle.
            return
        tab_idx = self.ui.camera_tabs.currentIndex()
        particle_provider = self._particle_data_conntections[
            self._image_tabs[tab_idx].ID
        ]
        selected_class = self.get_selected_class()
        selected_particle = int(self.ui.le_disp_one.text())

        if self.ui.rb_disp_all.isChecked():
            particle_provider.update_2D_data()
            _logger.debug(
                "RodTrackWindow.method_2D_changed() selected all "
                "particles from all classes."
            )
        elif self.ui.rb_disp_class.isChecked():
            particle_provider.update_2D_data(selected_class)
            _logger.debug(
                "RodTrackWindow.method_2D_changed() "
                f"selected class: {selected_class}"
            )
        elif self.ui.rb_disp_one.isChecked():
            particle_provider.update_2D_data(selected_class, selected_particle)
            _logger.debug(
                "RodTrackWindow.method_2D_changed() selected particle: "
                f"{selected_particle} of class: {selected_class}"
            )
        elif self.ui.rb_disp_none.isChecked():
            self._image_tabs[tab_idx].clear_screen()
            _logger.debug(
                "RodTrackWindow.method_2D_changed() selected not to "
                "display any particles"
            )

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
        self._image_tabs[tab_idx].image_manager.next_image(direction)

    def original_size(self):
        """Displays the currently loaded image in its native size."""
        tab_idx = self.ui.camera_tabs.currentIndex()
        self._image_tabs[tab_idx].scale_factor = 1
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
        # TODO: change this finding of the scroll area
        current_sa = self.findChild(
            QScrollArea, f"sa_camera_" f"{self.ui.camera_tabs.currentIndex()}"
        )
        to_size = current_sa.size()
        to_size = QtCore.QSize(to_size.width() - 20, to_size.height() - 20)
        tab_idx = self.ui.camera_tabs.currentIndex()
        self._image_tabs[tab_idx].scale_to_size(to_size)

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
        new_zoom = self._image_tabs[tab_idx].scale_factor * factor
        self._image_tabs[tab_idx].scale_factor = new_zoom
        # Disable zoom, if zoomed too much
        self.ui.action_zoom_in.setEnabled(new_zoom < self._max_zoom)
        self.ui.action_zoom_out.setEnabled(new_zoom > self._min_zoom)

    def get_selected_class(self):
        """Gets the currently selected color in the GUI.

        Returns
        -------
        str
            The color that is currently selected in the GUI.
        """
        for rb in self.ui.group_rod_color.findChildren(QRadioButton):
            if rb.isChecked():
                return rb.objectName()[3:]

    # TODO: rename and implement details/define an interface
    @QtCore.pyqtSlot(bool)
    def color_change(self, state: bool) -> None:
        """Handles changes of the ``QRadioButtons`` for color selection."""
        if state:
            color = self.get_selected_class()  # noqa: F841
            self.class_changed.emit(color)
            _logger.warning(
                "RodTrackWindow.color_change() is not (fully) implemented!"
            )

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
        msg.setWindowTitle(APPNAME)
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
    def change_class(self, to_class: str):
        """Activates the given classes' QRadioButton in the GUI.

        Parameters
        ----------
        to_class : str
            The class that is activated.

        Returns
        -------
        None
        """
        for rb in self.ui.group_rod_color.findChildren(QRadioButton):
            if rb.objectName()[3:] == to_class:
                # Activate the last color
                rb.toggle()

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
        manager = self._image_tabs[new_idx].image_manager

        misc.reconnect(
            self.ui.pb_load_images.clicked,
            lambda: manager.select_images(self.ui.le_image_dir.text()),
        )
        misc.reconnect(
            self.ui.action_open.triggered,
            lambda: manager.select_images(self.ui.le_image_dir.text()),
        )
        misc.reconnect(
            self.ui.le_image_dir.returnPressed,
            lambda: manager.select_images(self.ui.le_image_dir.text()),
        )
        try:
            data_obj = self._particle_data_conntections[
                self._image_tabs[new_idx].ID
            ]
            misc.reconnect(self.ui.pb_save_rods.clicked, data_obj.save)
            misc.reconnect(self.ui.pb_load_rods.clicked, data_obj.select_data)
            misc.reconnect(
                self.ui.le_rod_dir.returnPressed, data_obj.select_data
            )
            misc.reconnect(self.class_changed, data_obj.update_2D_data)

            # connect the image tab with its data provider functions
            misc.reconnect(
                data_obj.position_data_2d,
                self._image_tabs[new_idx].extract_particles,
            )
            misc.reconnect(
                self._image_tabs[new_idx].image_manager.next_img[int, int],
                data_obj.set_frame,
            )

        except KeyError:
            # Image interaction tab is not associated to a position data object
            pass

        if manager.folder is None:
            self.ui.le_image_dir.setText("")
        else:
            self.ui.le_image_dir.setText(str(manager.folder))

        # Run custom activation code
        self._image_tabs[new_idx].activate()

        # =====================================================================
        # TODO: this should not be done here! It should be handled by the
        #       extensions, because it is no longer part of the
        #       base-application. Should instead be integrated into the tabs'
        #       `activate()` function that is run above
        if self.ui.action_persistent_view.isChecked():
            # Ensure the image/frame number is consistent over views
            old_frame = self.logger.frame
            if manager.frames:
                idx_diff = manager.frames.index(old_frame) - manager.frame_idx
                self.show_next(idx_diff)
        # =====================================================================

    @QtCore.pyqtSlot(int)
    def utility_changed(self, new_idx: int):
        """Triggers the activate() method of the newly shown utility tab.

        Parameters
        ----------
        new_idx : int
            The index of the tab that is shown next.

        Returns
        -------
        None
        """
        # Run custom activation code
        self._utility_tabs[new_idx].activate()

    def requesting_undo(self) -> None:
        """Helper method to emit a request for reverting the last action.


        .. hint::

            **Emits**

                - :attr:`request_undo`
        """
        cam = self._image_tabs[self.ui.camera_tabs.currentIndex()]
        self.request_undo.emit(cam.ID)

    def requesting_redo(self) -> None:
        """Helper method to emit a request for repeating the last action.


        .. hint::

            **Emits**

                - :attr:`request_redo`
        """
        cam = self._image_tabs[self.ui.camera_tabs.currentIndex()]
        self.request_redo.emit(cam.ID)

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
        # TODO: add docs
        if is_busy:
            tab_icon = misc.busy_icon()
        else:
            tab_icon = misc.blank_icon()
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
            tab.parent().parent().verticalScrollBar()
            for tab in self._image_tabs
        ]:
            return False
        if not isinstance(event, QtGui.QWheelEvent):
            return False

        event = QWheelEvent(event)
        if not event.modifiers() == QtCore.Qt.ControlModifier:
            return False
        factor = 1.0
        if event.angleDelta().y() < 0:
            factor = 1 / self._zoom_factor
        elif event.angleDelta().y() > 0:
            factor = self._zoom_factor
        self.scale_image(factor)
        return True

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
        if not lg.MainLogger().unsaved_changes == []:
            msg = QMessageBox()
            msg.setWindowIcon(QtGui.QIcon(fl.icon_path()))
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle(APPNAME)
            msg.setText("There are unsaved changes!")
            btn_save = msg.addButton("Save", QMessageBox.ActionRole)
            msg.addButton("Discard", QMessageBox.ActionRole)
            btn_cancel = msg.addButton("Cancel", QMessageBox.ActionRole)
            msg.setDefaultButton(btn_save)
            msg.exec()
            if msg.clickedButton() == btn_save:
                # trigger saving for all registered position data providers
                for data_provider in set(
                    self._particle_data_conntections.values()
                ):
                    data_provider.save()
                a0.accept()
                pass
            elif msg.clickedButton() == btn_cancel:
                a0.ignore()
            else:
                # Discards changes and proceeds with closing
                a0.accept()
        else:
            a0.accept()

    # TODO: add docs
    def add_image_interaction_tab(
        self, tab: tabs.ImageInteractionTab, tab_name: str = ""
    ) -> None:
        self._image_tabs.append(tab)

        new_tab_num = self.ui.camera_tabs.count()
        # TODO: evaluate, whether it is a good idea to change the ID here,
        #       instead it might be better to leave the ID to extensions
        if tab.ID == "unknown":
            # Change the ID to something unique in cases where the extension
            # did not handle this.
            tab.ID = f"camera_{new_tab_num}"
        if tab.image_manager.ID == "unknown":
            tab.image_manager.ID = f"camera_{new_tab_num}"

        new_tab_internal = QtWidgets.QWidget()
        new_tab_internal.setObjectName(f"tab_{new_tab_num}")
        layout = QtWidgets.QVBoxLayout(new_tab_internal)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll_area = QtWidgets.QScrollArea(new_tab_internal)
        scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName(f"sa_camera_{new_tab_num}")
        layout.addWidget(scroll_area)

        scroll_area.setWidget(tab)
        self.ui.camera_tabs.addTab(new_tab_internal, tab_name)

        # connect signals performed on each view
        scroll_area.verticalScrollBar().installEventFilter(self)
        tab.image_manager.data_loaded.connect(self.images_loaded)
        tab.image_manager.next_img[int, int].connect(self.next_image)

        tab.logger.notify_unsaved.connect(self.tab_has_changes)

        # TODO: this should be handled by the extension instead. It has been
        #   changed from the line below:
        #   cam.logger.request_saving.connect(self.rod_data.save_changes)
        tab.logger.request_saving.connect(self.ui.pb_save_rods.click)
        self.request_undo.connect(tab.logger.undo_last)
        self.request_redo.connect(tab.logger.redo_last)

        tab.loaded_particles.connect(
            lambda n: self.ui.le_rod_disp.setText(f"Loaded Particles: {n}")
        )
        _logger.info(f"Initialized a new image interaction tab: {tab}")

    # TODO: add docs
    def add_utility_tab(
        self,
        tab: tabs.UtilityTab,
        tab_name: str = "",
        add_scrollable: bool = True,
    ) -> None:
        self._utility_tabs.append(tab)
        new_tab_num = self.ui.right_tabs.count()
        if add_scrollable:
            new_tab_internal = QtWidgets.QWidget()
            new_tab_internal.setObjectName(f"utility_tab_{new_tab_num}")
            layout = QtWidgets.QVBoxLayout(new_tab_internal)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            scroll_area = QtWidgets.QScrollArea(new_tab_internal)
            scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
            scroll_area.setWidgetResizable(True)
            scroll_area.setObjectName(f"sa_utility_{new_tab_num}")
            layout.addWidget(scroll_area)

            scroll_area.setWidget(tab)
            self.ui.right_tabs.addTab(new_tab_internal, tab_name)
        else:
            self.ui.right_tabs.addTab(tab, tab_name)
        _logger.info(f"Initialized a new utility tab: {tab}")

    # TODO: add docs
    def add_setting(self, widget: settings.Setting):
        self.settings_tab.add_setting(widget)

    # TODO: add docs
    def ensure_usable(self):
        """_summary_"""
        if not len(self._image_tabs):
            _logger.warning(
                "No specialized image interaction tab loaded. "
                "Using a default image viewer."
            )
            self.add_image_interaction_tab(
                tabs.ImageInteractionTab("DefaultViewer"),
                "Default Image Viewer",
            )

    def register_position_data(
        self,
        data_object: data.PositionData,
        connected_viewers: List[tabs.ImageInteractionTab],
    ):
        """_summary_

        Parameters
        ----------
        data_object : data.PositionData
            _description_
        connected_viewers : List[tabs.ImageInteractionTab]
            _description_
        connected_utility : List[tabs.UtilityTab]
            _description_

        Warnings
        --------
        It is unlikely that the connection between the `data_object` and one
        of the `connected_viewers` is retained, if the ID of the viewer changes
        after calling this function.
        Therefore only call this function after you have added your tabs to the
        main app.
        """
        data_object.data_loaded[Path, Path, list].connect(
            self.particles_loaded
        )
        # save association of viewers with data provider
        for view in connected_viewers:
            self._particle_data_conntections[view.ID] = data_object
            # 'reactivate' the current view, if a data object was added to it
            tab_idx = self.ui.camera_tabs.currentIndex()
            if tab_idx >= 0 and self._image_tabs[tab_idx] == view:
                self.view_changed(tab_idx)
