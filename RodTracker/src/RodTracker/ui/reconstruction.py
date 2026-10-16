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

"""
Includes classes which define widgets used for 3D reconstruction and
tracking of particles in RodTracker GUI.

**Author:**     Adrian Niemann (adrian.niemann@ovgu.de)\n
**Date:**       2022-2024
"""

import logging

# import os
from functools import partial
from typing import List

import matplotlib.backends.backend_qtagg as b_qt
import matplotlib.pyplot as plt
import pandas as pd
import ParticleDetection.utils.data_loading as dl
from matplotlib.figure import Figure
from PyQt5 import QtCore, QtWidgets

import RodTracker.ui.mainwindow_layout as mw_l
from RodTracker import exception_logger
from RodTracker.backend import parallelism as pl
from RodTracker.backend import reconstruction
from RodTracker.backend.reconstruction import Plotter, Reconstructor, Tracker
from RodTracker.backend.smoothing import (
    project_trajectories,
    smooth_trajectories,
)
from RodTracker.ui.dialogs import show_warning

_logger = logging.getLogger(__name__)


def init_reconstruction(ui: mw_l.Ui_MainWindow):
    """Initialize the functionality of reconstructing 3D particle positions.

    Parameters
    ----------
    ui : Ui_MainWindow
        UI object of the main window of the application, i.e. also containing
        the UI tab/objects for 3D reconstruction tasks.

    Returns
    -------
    None | ReconstructorUI
        Returns ``None``, if the system requirements for 3D particle position
        reconstruction are not met. Otherwise the ``ReconstructorUI`` object
        handling particle reconstructions is returned.
    """
    return ReconstructorUI(ui.tab_reconstruct)


class ReconstructorUI(QtWidgets.QWidget):
    """A custom ``QWidget`` to provide access to the reconstruction of 3D
    particle coordinates.

    This widget interfaces with the :mod:`ParticleDetection.reconstruct_3D`
    library and provides these functionalities to the GUI, i.e. reconstruction
    of 3D particle coordinates and tracking of particles over multiple frames.

    Parameters
    ----------
    ui : QWidget
        Widget containing the tab that is the GUI for the reconstruction and
        tracking functionality.
    *args : iterable
        Positional arguments for the ``QWidget`` superclass.
    **kwargs: dict
        Keyword arguments for the ``QWidget`` superclass.

    Attributes
    ----------
    used_colors : List[str]
        Selected colors for reconstruction/tracking/plotting.\n
        By default ``[]``.
    start_frame : int
        Lower bound of the frame range selected for
        reconstruction/tracking/plotting. The bound is inclusive.\n
        By default ``0``.
    end_frame : int
        Upper bound of the frame range selected for
        reconstruction/tracking/plotting. The bound is inclusive.\n
        By default ``0``.


    .. admonition:: Signals

        - :attr:`request_data`
        - :attr:`updated_data`

    .. admonition:: Slots

        - :meth:`add_plot`
        - :meth:`data_loaded`
        - :meth:`data_update`
        - :meth:`set_calibration`
        - :meth:`set_cam_ids`
        - :meth:`set_transformation`
        - :meth:`switch_plot_page`
        - :meth:`update_frames`
        - :meth:`update_settings`

    """

    position_scaling: float = 1.0
    """float : Scale factor to scale the loaded data for display (is usually
    kept as ``1.0``).

    Default is ``1.0``.
    """

    request_data = QtCore.pyqtSignal([list, list])
    """pyqtSignal(list, list) : Request a portion of the *main* dataset defined
    by

    | [0]: a list of frames, and
    | [1]: a list of colors.
    """

    updated_data = QtCore.pyqtSignal(pd.DataFrame)
    """pyqtSignal(DataFrame) : Sends an updated slice of the *main* dataset,
    that has been (re-)tracked or its 3D coordinates updated.

    This signal is emitted once for every color during the
    reconstruction/tracking process. The ``DataFrame`` in the payload is
    effectively an updated slice of the *main* dataset and does not contain
    new rows.
    """

    is_busy = QtCore.pyqtSignal(bool)
    """pyqtSignal(bool) : Notifies when a background task is started/finished.
    """

    smoothed_data_ready = QtCore.pyqtSignal(pd.DataFrame)
    """Emits the separately smoothed endpoint data frame."""

    original_projection_data_ready = QtCore.pyqtSignal(pd.DataFrame)
    """Emits independently computed original 3D reprojection coordinates."""

    smoothing_overlay_changed = QtCore.pyqtSignal(bool)
    """Emits whether the smoothed endpoint overlay should be visible."""

    original_projection_changed = QtCore.pyqtSignal(bool)
    """Emits whether the original 3D reprojection should be visible."""

    data: pd.DataFrame = None
    """DataFrame : Slice of the *main* ``DataFrame`` that is used for
    reconstruction/tracking.

    Default is ``None``.
    """

    cam_ids: List[str] = ["", ""]
    """List[str] : IDs of the two cameras intended for reconstruction of 3D
    coordinates.

    The IDs are used to identify the 2D data columns during the reconstruction
    process. If at least one of them is an empty string, the process of
    reconstruction or tracking will be immediatly aborted, because the there
    either is not enough data or the data is not identifiable.

    Default is ``["", ""]``.
    """

    _calibration = QtCore.pyqtSignal([dict])
    _progress_val: float = 0.0
    _colors_to_solve: int = 0
    _pre_solve_data_requested: bool = False

    def __init__(self, ui: QtWidgets.QWidget, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = ui
        self._threads = QtCore.QThreadPool()

        self._calibration = None
        self._transformation = None
        self._custom_solver = None
        self.reprojection_errs = None
        self.used_colors = []
        self.start_frame = 0
        self.end_frame = 0
        self.first_update = False
        self.smoothed_data = None
        self._smoothing_request_pending = False
        self._original_projection_request_pending = False
        self._original_projection_revision = 0
        self._available_colors = []

        # Signal connections
        tb_calibration = ui.findChild(QtWidgets.QToolButton, "tb_calibration")
        le_calibration = ui.findChild(QtWidgets.QLineEdit, "le_calibration")
        tb_calibration.clicked.connect(
            lambda: choose_calibration(le_calibration, self.set_calibration)
        )
        tb_transformation = ui.findChild(
            QtWidgets.QToolButton, "tb_transformation"
        )
        le_transformation = ui.findChild(
            QtWidgets.QLineEdit, "le_transformation"
        )
        tb_transformation.clicked.connect(
            lambda: choose_calibration(
                le_transformation, self.set_transformation
            )
        )
        start_f = ui.findChild(QtWidgets.QSpinBox, "start_frame")
        start_f.valueChanged.connect(self._change_start_frame)
        end_f = ui.findChild(QtWidgets.QSpinBox, "end_frame")
        end_f.valueChanged.connect(self._change_end_frame)

        for cb in ui.findChildren(QtWidgets.QCheckBox):
            if "tracking" in cb.objectName():
                continue
            cb.stateChanged.connect(self._toggle_color)

        self.stacked_plots = ui.findChild(
            QtWidgets.QStackedWidget, "stacked_plots"
        )
        self.lbl_current_plot = ui.findChild(
            QtWidgets.QLabel, "lbl_current_plot"
        )
        tb_left = self.ui.findChild(QtWidgets.QToolButton, "tb_plots_left")
        tb_left.clicked.connect(lambda: self.switch_plot_page(-1))
        tb_right = self.ui.findChild(QtWidgets.QToolButton, "tb_plots_right")
        tb_right.clicked.connect(lambda: self.switch_plot_page(1))

        self.pb_plots = self.ui.findChild(
            QtWidgets.QPushButton, "pb_update_plots"
        )
        self.pb_plots.clicked.connect(self.update_plots)

        self.pb_solve = ui.findChild(QtWidgets.QPushButton, "pb_solve")
        self.pb_solve.clicked.connect(self.solve)

        # Disable not implemented features
        ui.findChild(QtWidgets.QToolButton, "tb_solver").setEnabled(False)
        ui.findChild(QtWidgets.QLineEdit, "le_solver").setEnabled(False)
        ui.findChild(QtWidgets.QLabel, "lbl_solver").setEnabled(False)
        self.pb_solve.setEnabled(False)

        self.progress = ui.findChild(
            QtWidgets.QProgressBar, "progress_reconstruction"
        )
        self.progress.setValue(100)
        self._create_smoothing_panel()

    def _create_smoothing_panel(self):
        projection_panel = QtWidgets.QGroupBox("3D reprojection", self.ui)
        projection_layout = QtWidgets.QVBoxLayout(projection_panel)
        self.cb_original_projection = QtWidgets.QCheckBox(
            "Show original 3D reprojection (J)", projection_panel
        )
        self.cb_original_projection.setObjectName("cb_original_projection")
        self.cb_original_projection.setToolTip(
            "Distortion-aware projection of the current unsmoothed 3D "
            "endpoints (light green)."
        )
        self.cb_original_projection.setEnabled(False)
        self.cb_original_projection.toggled.connect(
            self._toggle_original_projection
        )
        projection_layout.addWidget(self.cb_original_projection)
        self.ui.layout().insertWidget(1, projection_panel)

        panel = QtWidgets.QGroupBox("Endpoint smoothing", self.ui)
        panel_layout = QtWidgets.QVBoxLayout(panel)

        frame_row = QtWidgets.QHBoxLayout()
        self.smoothing_start = QtWidgets.QSpinBox(panel)
        self.smoothing_start.setObjectName("smoothing_start_frame")
        self.smoothing_end = QtWidgets.QSpinBox(panel)
        self.smoothing_end.setObjectName("smoothing_end_frame")
        frame_row.addWidget(QtWidgets.QLabel("Start frame", panel))
        frame_row.addWidget(self.smoothing_start)
        frame_row.addWidget(QtWidgets.QLabel("End frame", panel))
        frame_row.addWidget(self.smoothing_end)
        panel_layout.addLayout(frame_row)

        self.smoothing_colors = QtWidgets.QGroupBox(
            "Colors and nominal lengths", panel
        )
        self.smoothing_color_layout = QtWidgets.QGridLayout(
            self.smoothing_colors
        )
        self.smoothing_color_controls = {}
        panel_layout.addWidget(self.smoothing_colors)

        parameter_form = QtWidgets.QFormLayout()
        self.translation_noise = self._make_parameter_spin(
            0.0001, 10000.0, 50.0, 4
        )
        self.orientation_noise = self._make_parameter_spin(
            0.000001, 100.0, 0.5, 6
        )
        self.length_tolerance = self._make_parameter_spin(0.1, 100.0, 1.5, 2)
        self.reprojection_tolerance = self._make_parameter_spin(
            0.1, 1000.0, 15.0, 1
        )
        self.translation_noise.setToolTip(
            "Higher values follow measured centers more closely."
        )
        self.orientation_noise.setToolTip(
            "Higher values follow measured rod axes more closely."
        )
        self.length_tolerance.setToolTip(
            "Length deviations beyond this value reduce observation weight."
        )
        self.reprojection_tolerance.setToolTip(
            "Pixel residual scale used to reduce weights for poor projections."
        )
        parameter_form.addRow(
            "Translation process noise", self.translation_noise
        )
        parameter_form.addRow(
            "Orientation process noise", self.orientation_noise
        )
        parameter_form.addRow("Length tolerance (mm)", self.length_tolerance)
        parameter_form.addRow(
            "Reprojection outlier scale (px)", self.reprojection_tolerance
        )
        panel_layout.addLayout(parameter_form)

        button_row = QtWidgets.QHBoxLayout()
        self.pb_smooth = QtWidgets.QPushButton("Smooth endpoints", panel)
        self.pb_smooth.setObjectName("pb_smooth_endpoints")
        self.pb_smooth.clicked.connect(self.smooth_selected)
        self.cb_smoothed_projection = QtWidgets.QCheckBox(
            "Show smoothed 3D projection (K)", panel
        )
        self.cb_smoothed_projection.setObjectName("cb_smoothed_projection")
        self.cb_smoothed_projection.setToolTip(
            "Distortion-aware projection of the smoothed 3D endpoints."
        )
        self.cb_smoothed_projection.setEnabled(False)
        self.cb_smoothed_projection.toggled.connect(
            self.smoothing_overlay_changed.emit
        )
        button_row.addWidget(self.pb_smooth)
        button_row.addWidget(self.cb_smoothed_projection)
        panel_layout.addLayout(button_row)

        self.pb_save_smoothed = QtWidgets.QPushButton(
            "Export smoothed CSV", panel
        )
        self.pb_save_smoothed.setEnabled(False)
        self.pb_save_smoothed.clicked.connect(self.save_smoothed_results)
        panel_layout.addWidget(self.pb_save_smoothed)

        self.ui.layout().insertWidget(2, panel)
        self._update_original_projection_enabled()

    @staticmethod
    def _make_parameter_spin(minimum, maximum, value, decimals):
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(decimals)
        spin.setSingleStep(10 ** (-decimals))
        spin.setValue(value)
        return spin

    def _update_smoothing_colors(self, colors):
        while self.smoothing_color_layout.count():
            item = self.smoothing_color_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.smoothing_color_controls.clear()
        defaults = {
            "blue": 10.0,
            "yellow": 10.0,
            "green": 15.0,
            "red": 15.0,
            "lilac": 15.0,
        }
        for row, color in enumerate(colors):
            normalized_color = color.lower()
            checkbox = QtWidgets.QCheckBox(
                normalized_color, self.smoothing_colors
            )
            checkbox.setChecked(True)
            length = self._make_parameter_spin(
                0.1, 100.0, defaults.get(normalized_color, 10.0), 2
            )
            length.setSuffix(" mm")
            self.smoothing_color_layout.addWidget(checkbox, row, 0)
            self.smoothing_color_layout.addWidget(length, row, 1)
            self.smoothing_color_controls[normalized_color] = (
                checkbox,
                length,
            )

    def smooth_selected(self):
        if not self._calibration or not self._transformation:
            show_warning(
                "Smoothing requires camera calibration and world "
                "transformation data."
            )
            return
        colors = [
            color
            for color, (checkbox, _) in self.smoothing_color_controls.items()
            if checkbox.isChecked()
        ]
        if not colors or any(not cam_id for cam_id in self.cam_ids):
            show_warning(
                "Smoothing requires selected colors and both camera IDs."
            )
            return
        start = self.smoothing_start.value()
        end = self.smoothing_end.value()
        if start > end:
            show_warning(
                "The smoothing start frame must not exceed its end frame."
            )
            return
        self._smoothing_request_pending = True
        self.pb_smooth.setEnabled(False)
        self.request_data.emit(list(range(start, end + 1)), colors)

    def _start_smoothing(self, data):
        if data.empty:
            self._finish_smoothing(pd.DataFrame())
            return
        lengths = {
            color: length.value()
            for color, (_, length) in self.smoothing_color_controls.items()
        }
        worker = pl.Worker(
            smooth_trajectories,
            data.copy(deep=True),
            lengths,
            self._calibration,
            self._transformation,
            tuple(self.cam_ids),
            translation_process_noise=self.translation_noise.value(),
            orientation_process_noise=self.orientation_noise.value(),
            length_tolerance=self.length_tolerance.value(),
            reprojection_tolerance=self.reprojection_tolerance.value(),
        )
        worker.signals.result.connect(self._finish_smoothing)
        worker.signals.error.connect(self._smoothing_failed)
        self.is_busy.emit(True)
        self._threads.start(worker)

    def _finish_smoothing(self, result):
        self.smoothed_data = result
        self.pb_smooth.setEnabled(True)
        self.cb_smoothed_projection.setEnabled(not result.empty)
        self.pb_save_smoothed.setEnabled(not result.empty)
        if self._threads.activeThreadCount() <= 1:
            self.is_busy.emit(False)
        self.smoothed_data_ready.emit(result)
        if result.empty:
            self.cb_smoothed_projection.setChecked(False)
            show_warning("No valid 3D rod endpoints were available to smooth.")
            return

    def invalidate_smoothed_data(self, *_args):
        """Clear projections computed from an outdated rod dataset."""
        self._original_projection_revision += 1
        self._original_projection_request_pending = False
        self.smoothed_data = None
        self.cb_smoothed_projection.setChecked(False)
        self.cb_original_projection.setChecked(False)
        self.cb_smoothed_projection.setEnabled(False)
        self.pb_save_smoothed.setEnabled(False)
        self.smoothed_data_ready.emit(pd.DataFrame())
        self.original_projection_data_ready.emit(pd.DataFrame())
        self._update_original_projection_enabled()

    def _smoothing_failed(self, error):
        self.pb_smooth.setEnabled(True)
        if self._threads.activeThreadCount() <= 1:
            self.is_busy.emit(False)
        exception_logger(*error)
        show_warning(f"Endpoint smoothing failed:\n{error[1]}")

    def save_smoothed_results(self):
        if self.smoothed_data is None or self.smoothed_data.empty:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.ui,
            "Export smoothed endpoint data",
            "smoothed_endpoints.csv",
            "CSV files (*.csv)",
        )
        if path:
            self.smoothed_data.to_csv(path, index=False)

    def toggle_smoothing_overlay(self):
        if self.cb_smoothed_projection.isEnabled():
            self.cb_smoothed_projection.toggle()

    def toggle_original_projection(self):
        if self.cb_original_projection.isEnabled():
            self.cb_original_projection.toggle()

    def _update_original_projection_enabled(self):
        enabled = bool(self._available_colors)
        enabled = enabled and self._calibration is not None
        enabled = enabled and self._transformation is not None
        enabled = enabled and all(self.cam_ids)
        self.cb_original_projection.setEnabled(enabled)

    def _toggle_original_projection(self, visible: bool):
        self.original_projection_changed.emit(visible)
        if not visible:
            self._original_projection_revision += 1
            self._original_projection_request_pending = False
            return
        colors = list(self.used_colors)
        start = self.start_frame
        end = self.end_frame
        if not colors or start > end:
            self.cb_original_projection.setChecked(False)
            return
        self._original_projection_request_pending = True
        self.request_data.emit(list(range(start, end + 1)), colors)

    def _start_original_projection(self, data):
        if data.empty:
            self._finish_original_projection(
                pd.DataFrame(), self._original_projection_revision
            )
            return
        request_id = self._original_projection_revision
        worker = pl.Worker(
            project_trajectories,
            data.copy(deep=True),
            self._calibration,
            self._transformation,
            tuple(self.cam_ids),
        )
        worker.signals.result.connect(
            lambda result: self._finish_original_projection(result, request_id)
        )
        worker.signals.error.connect(self._projection_failed)
        self.is_busy.emit(True)
        self._threads.start(worker)

    def _finish_original_projection(self, result, request_id):
        if self._threads.activeThreadCount() <= 1:
            self.is_busy.emit(False)
        if request_id != self._original_projection_revision:
            return
        if result.empty:
            self.cb_original_projection.setChecked(False)
        self.original_projection_data_ready.emit(result)

    def _projection_failed(self, error):
        if self._threads.activeThreadCount() <= 1:
            self.is_busy.emit(False)
        exception_logger(*error)
        self.cb_original_projection.setChecked(False)
        show_warning(f"Original 3D reprojection failed:\n{error[1]}")

    @QtCore.pyqtSlot(str)
    def set_calibration(self, path: str):
        """Attempts to load a new set of stereo camera calibration data.

        Attempt to load calibration data from the file given in ``path`` and
        activates the **Solve** button if both, calibration and transformation
        data, have been loaded. Additionally, the updating of plots is
        (re-)enabled upon successful loading of the calibration data.

        Parameters
        ----------
        path : str
            Path to the stereo camera calibration data that shall be loaded
            here.

        Returns
        -------
        None
        """
        self._calibration = dl.load_camera_calibration(path)
        self.invalidate_smoothed_data()
        self._update_original_projection_enabled()
        if self._calibration and self._transformation:
            self.ui.findChild(QtWidgets.QPushButton, "pb_solve").setEnabled(
                True
            )
        if self.data is not None:
            self.pb_plots.setEnabled(True)

    @QtCore.pyqtSlot(str)
    def set_transformation(self, path: str):
        """Attempts to load a new set transformations to world/experiment
        coordinates.

        Attempts to load transformation matrices fromt the file given in
        ``path`` and activates the **Solve** button if both, calibration and
        transformation data, have been loaded. Additionally, the updating of
        plots is (re-)enabled upon successful loading of the transformation
        data.

        Parameters
        ----------
        path : str
            Path to the transformation data that shall be loaded here.
        """
        self._transformation = dl.load_world_transformation(path)
        self.invalidate_smoothed_data()
        self._update_original_projection_enabled()
        if self._calibration and self._transformation:
            self.ui.findChild(QtWidgets.QPushButton, "pb_solve").setEnabled(
                True
            )
        if self.data is not None:
            self.pb_plots.setEnabled(True)

    def _change_start_frame(self, new_val: int):
        """Callback for the ``QSpinBox`` handling the start frame selection."""
        self.start_frame = new_val
        self.select_data()
        self.pb_plots.setEnabled(True)

    def _change_end_frame(self, new_val: int):
        """Callback for the ``QSpinBox`` handling the end frame selection."""
        self.end_frame = new_val
        self.select_data()
        self.pb_plots.setEnabled(True)

    @property
    def solver(self):
        """**Not Implemented.**"""
        raise NotImplementedError

    @solver.setter
    def solver(self, path: str):
        raise NotImplementedError

    @QtCore.pyqtSlot(pd.DataFrame)
    def data_update(self, data: pd.DataFrame):
        """Accepts a new dataset that shall be used for
        reconstruction/tracking.

        Accepts a new dataset and, depending on whether this is the first time
        data is given here, updates the plots or (re-)enables the button for
        updating the plots in the UI.

        Parameters
        ----------
        data : pd.DataFrame
            New data that shall be used for plotting, 3D coordinate
            reconstruction and tracking of particles.
        """
        self.data = data
        if self._original_projection_request_pending:
            self._original_projection_request_pending = False
            self._start_original_projection(data)
        if self._smoothing_request_pending:
            self._smoothing_request_pending = False
            self._start_smoothing(data)
        if any([cam == "" for cam in self.cam_ids]):
            # insufficient data for plotting given
            _logger.info("Insufficient data for plotting given. Skipping...")
            return
        if self.first_update:
            # The automatic updating of plots has been disabled due to a memory
            # issue with not garbage collected plot residues. See the
            # "Known issues" section in the docs to learn more about the
            # problem.
            # self.update_plots()
            # self.pb_plots.setEnabled(False)
            self.pb_plots.setEnabled(True)

            self.first_update = False
        else:
            self.pb_plots.setEnabled(True)

        # data had been requested by solve(), so re-run it
        if self._pre_solve_data_requested:
            self.solve()

    def select_data(self):
        """Request data defined by the selections in the UI.

        Requests a portion of the *main* data that is defined by the selections
        of the user in the reconstruction tab, i.e. start/end frame and colors
        of particles to include.

        Returns
        -------
        None


        .. hint::

            **Emits**:

                - :attr:`request_data`
        """
        self.request_data.emit(
            list(range(self.start_frame, self.end_frame + 1)), self.used_colors
        )

    def solve(self):
        """(Re-)Starts the reconstruction/tracking of particles.

        Starts either the reconstruction or tracking of particles, depending on
        the state of a ``QCheckBox``. One process/thread for every selected
        color (:attr:`used_colors`) is started, that will (re-)calculate the
        3D values (and particle IDs) for all frames in between
        :attr:`start_frame` and :attr:`end_frame`.

        Returns
        -------
        None
        """
        # request potentially updated position data before solving
        if not self._pre_solve_data_requested:
            self._pre_solve_data_requested = True
            self.select_data()
            return
        self._pre_solve_data_requested = False

        track = self.ui.findChild(
            QtWidgets.QCheckBox, "cb_tracking"
        ).isChecked()
        if (
            self.data is None
            or len(self.data) == 0
            or any([cam == "" for cam in self.cam_ids])
        ):
            # insufficient data for 3D reconstruction given
            show_warning(
                "Warning: 3D reconstruction requires "
                "the coordinate data from 2 cameras."
            )
            return
        frames = list(range(self.start_frame, self.end_frame + 1))
        self._progress_val = 0.0
        self.progress.setValue(0)
        num_colors = len(self.used_colors)
        self._colors_to_solve = num_colors
        self.is_busy.emit(True)
        for i in range(num_colors):
            color = self.used_colors[i]
            tmp = self.data.loc[self.data.color == color]
            if track:
                tracker = Tracker(
                    tmp,
                    frames,
                    self._calibration,
                    self._transformation,
                    self.cam_ids,
                    color,
                )
            else:
                tracker = Reconstructor(
                    tmp,
                    frames,
                    self._calibration,
                    self._transformation,
                    self.cam_ids,
                    color,
                )
            tracker.signals.progress.connect(
                lambda val: self._progress_update(val / num_colors)
            )
            tracker.signals.error.connect(lambda ret: exception_logger(*ret))
            tracker.signals.error.connect(
                lambda ret: self._solver_result(None)
            )
            tracker.signals.error.connect(
                lambda ret: partial(self._notify_error, color)
            )
            tracker.signals.error.connect(partial(self._notify_error, color))
            tracker.signals.result.connect(self._solver_result)
            self._threads.start(tracker)

        self.pb_solve.setText("Abort")
        self.pb_solve.clicked.disconnect()
        self.pb_solve.clicked.connect(self._abort_reconstruction)

    def _abort_reconstruction(self):
        self.pb_solve.setEnabled(False)
        reconstruction.lock.lockForWrite()
        reconstruction.abort_reconstruction = True
        reconstruction.lock.unlock()

    def _notify_error(self, color: str):
        show_warning(
            "Something went wrong during 3D reconstruction of "
            f"'{color}' particles.\n"
            "Please consult the logs for more information."
        )

    def _solver_result(self, result: pd.DataFrame):
        """Hook to handle the result of each reconstruction process.

        Updates the count of active reconstruction/tracking processes/threads
        and resets the UI for further reconstruction/tracking tasks after all
        have finished.
        Propagates the results of the finished task.

        Parameters
        ----------
        result : pd.DataFrame
            The ``DataFrame`` containing the result of the process, usually
            updated data of one color only but for all frames used during
            the finished process.


        .. hint::

            **Emits:**

                - :attr:`updated_data`
        """
        self._colors_to_solve -= 1
        if self._colors_to_solve == 0:
            if self._threads.activeThreadCount() == 0:
                self.is_busy.emit(False)
            self.pb_solve.setText("Solve")
            self.pb_solve.clicked.disconnect()
            self.pb_solve.clicked.connect(self.solve)
            self.pb_solve.setEnabled(True)
            self.progress.setValue(100)
            reconstruction.lock.lockForWrite()
            reconstruction.abort_reconstruction = False
            reconstruction.lock.unlock()
        if result is None:
            return
        self.data.update(result)
        self.updated_data.emit(result)
        self.select_data()

    def _progress_update(self, update: float):
        """Update the progressbar during the reconstruction/tracking process.

        Parameters
        ----------
        update : float
            Value to add upon the combined progress :math:`\\in [0, 1]`.

        Returns
        -------
        None
        """
        self._progress_val += 100 * update
        self.progress.setValue(int(self._progress_val))

    @QtCore.pyqtSlot(int)
    def switch_plot_page(self, direction: int):
        """Switch the displayed plot page relative to the currently displayed
        one.

        Parameters
        ----------
        direction : int
            Direction of the plot to display next. Its the index relative to
            the currently displayed plot.\n
            a) ``direction = 3``->  displays the plot three positions
            further\n
            b) ``direction = -1``->  displays the previous plot\n
            c) ``direction = 0``->  stays on the current plot
        """
        idx_max = self.stacked_plots.count() - 1
        idx_new = self.stacked_plots.currentIndex() + direction
        if idx_new > idx_max:
            idx_new = 0
        elif idx_new < 0:
            idx_new = idx_max
        self.stacked_plots.setCurrentIndex(idx_new)
        self.lbl_current_plot.setText(
            f"({self.stacked_plots.currentIndex() + 1}"
            f"/{self.stacked_plots.count()})"
        )

    @QtCore.pyqtSlot(str, str)
    def set_cam_ids(self, cam1: str, cam2: str):
        """Setter function for :attr:`cam_ids`.

        Parameters
        ----------
        cam1 : str
            ID for the first camera of the stereo camera setup.
        cam2 : str
            ID for the second camera of the stereo camera setup.

        Returns
        -------
        None
        """
        self.cam_ids = [cam1, cam2]
        self._update_original_projection_enabled()

    @QtCore.pyqtSlot(int, int, list)
    def data_loaded(self, f_min: int, f_max: int, colors: List[str]):
        """Hook to updated the available frame range and colors for
        reconstruction/tracking.

        This function is intended as a slot for the
        :attr:`~.RodData.data_loaded` signal. The range of available frames, as
        well as the available colors in the loaded dataset is updated and
        presented to users in the UI.

        Parameters
        ----------
        f_min : int
            Lowest frame currently available in the particle position dataset.
        f_max : int
            Highest frame currently available in the particle position dataset.
        colors : List[str]
            Colors currently available in the particle position dataset.

        Returns
        -------
        None
        """
        start = self.ui.findChild(QtWidgets.QSpinBox, "start_frame")
        start.setRange(f_min, f_max)
        start.setValue(f_min)
        end = self.ui.findChild(QtWidgets.QSpinBox, "end_frame")
        end.setRange(f_min, f_max)
        end.setValue(f_max)
        self._update_colors(colors)
        self._available_colors = list(colors)
        self.smoothing_start.setRange(f_min, f_max)
        self.smoothing_end.setRange(f_min, f_max)
        self.smoothing_start.setValue(max(f_min, 200))
        self.smoothing_end.setValue(f_max)
        self._update_smoothing_colors(colors)
        self._update_original_projection_enabled()
        self.first_update = True
        self.select_data()

    def _update_colors(self, colors: List[str]):
        """Update the checkable colors displayed in the UI."""
        color_group = self.ui.findChild(
            QtWidgets.QGroupBox, "group_colors_reconstruction"
        )
        color_cbs = color_group.findChildren(QtWidgets.QCheckBox)
        old_colors = [cb.text().lower() for cb in color_cbs]
        group_layout: QtWidgets.QGridLayout = color_group.layout()
        for cb in color_cbs:
            group_layout.removeWidget(cb)
            if cb.text().lower() not in colors:
                cb.hide()
                cb.deleteLater()
        row = 0
        col = 0
        for color in colors:
            try:
                cb = color_cbs[old_colors.index(color)]
            except ValueError:
                cb = QtWidgets.QCheckBox(text=color.lower())
                cb.setObjectName(f"cb_{color}")
                cb.stateChanged.connect(self._toggle_color)
            cb.setChecked(True)
            group_layout.addWidget(cb, row, col)
            if col == 1:
                col = 0
                row += 1
            else:
                col = 1

    def _toggle_color(self, _: int):
        """Update whether to use an available color.

        Parameters
        ----------
        _ : int
        """
        self.used_colors = []
        color_group = self.ui.findChild(
            QtWidgets.QGroupBox, "group_colors_reconstruction"
        )
        for cb in color_group.findChildren(QtWidgets.QCheckBox):
            if cb.checkState():
                self.used_colors.append(cb.objectName().split("_")[1])
        self.pb_plots.setEnabled(True)

    @QtCore.pyqtSlot(int, int)
    def update_frames(self, start: int, end: int):
        """Update the selected frame range for reconstruction/tracking.

        Parameters
        ----------
        start : int
            Lowest selected frame.
        end : int
            Highest selected frame.
        """
        spb_start = self.ui.findChild(QtWidgets.QSpinBox, "start_frame")
        spb_end = self.ui.findChild(QtWidgets.QSpinBox, "end_frame")
        spb_start.setValue(start)
        spb_end.setValue(end)

    def update_plots(self):
        """(Re-)Generate plots for evaluation of the 3D data in the dataset.

        Starts a thread that generates the evaluation plots for the data
        selected by the state of UI, i.e. selected colors
        (:attr:`self.used_colors`) and frame range (:attr:`start_frame`,
        :attr:`end_frame`).

        Returns
        -------
        None
        """
        while self.stacked_plots.count():
            self.stacked_plots.removeWidget(self.stacked_plots.currentWidget())
        plt.close("all")
        if self.data is None or len(self.data) == 0:
            show_warning("No data are provided for plotting.")
            return
        elif any([cam == "" for cam in self.cam_ids]):
            show_warning(
                "Plotting requires the coordinate data from 2 cameras."
            )
            return
        data_plt = self.data.loc[
            (self.data["frame"] >= self.start_frame)
            & (self.data["frame"] <= self.end_frame)
            & (self.data["color"].isin(self.used_colors))
        ]
        self.is_busy.emit(True)
        plotter = Plotter(
            data_plt.copy(),
            colors=self.used_colors,
            start_frame=self.start_frame,
            end_frame=self.end_frame,
            position_scaling=self.position_scaling,
            cam_ids=self.cam_ids,
            calibration=self._calibration,
            transformation=self._transformation,
        )
        plotter.signals.result_plot.connect(self.add_plot)
        plotter.signals.error.connect(lambda ret: exception_logger(*ret))
        self._threads.start(plotter)
        self.pb_plots.setEnabled(False)

    @QtCore.pyqtSlot(Figure)
    def add_plot(self, fig: Figure):
        """Add a figure to the display section.

        Attempts to add the given ``Figure`` as a new *page* for display in the
        UI.

        Parameters
        ----------
        fig : Figure
            ``Figure`` to be added to the stacked plots for display in the UI.

        Returns
        -------
        None
        """
        canvas = b_qt.FigureCanvasQTAgg(fig)
        nav_bar = b_qt.NavigationToolbar2QT(canvas, None)
        widget = QtWidgets.QWidget()
        widget.setLayout(QtWidgets.QVBoxLayout())
        widget.layout().setContentsMargins(0, 0, 0, 0)
        widget.layout().addWidget(canvas)
        widget.layout().addWidget(nav_bar)
        self.stacked_plots.insertWidget(self.stacked_plots.count(), widget)
        fig.tight_layout()
        self.lbl_current_plot.setText(
            f"({self.stacked_plots.currentIndex() + 1}"
            f"/{self.stacked_plots.count()})"
        )
        if self._threads.activeThreadCount() == 0:
            self.is_busy.emit(False)
        return

    @QtCore.pyqtSlot(dict)
    def update_settings(self, settings: dict) -> None:
        """Catches updates of the settings from a :class:`.Settings` class.

        Checks for the keys relevant to itself and updates the corresponding
        attributes. Redraws itself with the new settings in place.

        Parameters
        ----------
        settings : dict

        Returns
        -------
        None
        """
        settings_changed = False
        if "position_scaling" in settings:
            settings_changed = True
            self.position_scaling = settings["position_scaling"]

        if settings_changed and self.data is not None:
            self.pb_plots.setEnabled(True)


def choose_calibration(
    line_edit: QtWidgets.QLineEdit, destination_func: callable
):
    """Let a user select a calibration/transformation file and load it.

    Lets a user select a ``*.json`` file that should contain one kind of
    calibration, i.e. stereo camera calibration or transformtion to
    world/experiment coordinates. The chosen file is then passed to the given
    loading function for further processing.

    Parameters
    ----------
    line_edit : QLineEdit
        Display object for the desired calibration file.
    destination_func : callable
        Loading function for the desired calibration file.

    Returns
    -------
    None
    """
    # check for a directory
    ui_dir = line_edit.text()
    # opens directory to select image
    kwargs = {}
    # handle file path issue when running on linux as a snap
    # if "SNAP" in os.environ:
    kwargs["options"] = QtWidgets.QFileDialog.DontUseNativeDialog
    chosen_file, _ = QtWidgets.QFileDialog.getOpenFileName(
        line_edit, "Open a calibration", ui_dir, "*.json", **kwargs
    )
    if chosen_file == "":
        # File selection was aborted
        return None
    else:
        destination_func(chosen_file)
        line_edit.setText(chosen_file)
