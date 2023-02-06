#  Copyright (c) 2023 Adrian Niemann Dmitry Puzyrev
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

import sys
import os
import logging
from typing import List
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import matplotlib.backends.backend_qtagg as b_qt
from PyQt5 import QtWidgets, QtCore
import RodTracker.ui.mainwindow_layout as mw_l
import RodTracker.backend.logger as lg
_logger = logging.getLogger(__name__)
if sys.version_info < (3, 10):
    _logger.warning("3D reconstruction is not available. "
                    "Please upgrade to Python 3.10 or greater and "
                    "reinstall the application.")
else:
    import ParticleDetection.utils.data_loading as dl
    from RodTracker.backend.reconstruction import (Plotter, Tracker,
                                                   Reconstructor)


def init_reconstruction(ui: mw_l.Ui_MainWindow):
    if sys.version_info < (3, 10):
        ui.tab_reconstruct.setEnabled(False)
        return
    return ReconstructorUI(ui.tab_reconstruct)


class ReconstructorUI(QtWidgets.QWidget):
    position_scaling: float = 1.0
    request_data = QtCore.pyqtSignal([list, list])
    updated_data = QtCore.pyqtSignal(pd.DataFrame)
    data: pd.DataFrame = None
    cam_ids: List[str] = ["", ""]
    _calibration = QtCore.pyqtSignal([dict])
    _progress_val: float = 0.
    _colors_to_solve: int = 0

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

        # Signal connections
        tb_calibration = ui.findChild(QtWidgets.QToolButton, "tb_calibration")
        le_calibration = ui.findChild(QtWidgets.QLineEdit, "le_calibration")
        tb_calibration.clicked.connect(
            lambda: choose_calibration(le_calibration, self.set_calibration)
        )
        tb_transformation = ui.findChild(QtWidgets.QToolButton,
                                         "tb_transformation")
        le_transformation = ui.findChild(QtWidgets.QLineEdit,
                                         "le_transformation")
        tb_transformation.clicked.connect(
            lambda: choose_calibration(le_transformation,
                                       self.set_transformation)
        )
        start_f = ui.findChild(QtWidgets.QSpinBox, "start_frame")
        start_f.valueChanged.connect(self.change_start_frame)
        end_f = ui.findChild(QtWidgets.QSpinBox, "end_frame")
        end_f.valueChanged.connect(self.change_end_frame)

        for cb in ui.findChildren(QtWidgets.QCheckBox):
            if "tracking" in cb.objectName():
                continue
            cb.stateChanged.connect(self.toggle_color)

        self.stacked_plots = ui.findChild(QtWidgets.QStackedWidget,
                                          "stacked_plots")
        tb_left = self.ui.findChild(QtWidgets.QToolButton, "tb_plots_left")
        tb_left.clicked.connect(lambda: self.switch_plot_page(-1))
        tb_right = self.ui.findChild(QtWidgets.QToolButton, "tb_plots_right")
        tb_right.clicked.connect(lambda: self.switch_plot_page(1))

        self.pb_plots = self.ui.findChild(QtWidgets.QPushButton,
                                          "pb_update_plots")
        self.pb_plots.clicked.connect(self.update_plots)

        self.pb_solve = ui.findChild(QtWidgets.QPushButton, "pb_solve")
        self.pb_solve.clicked.connect(self.solve)

        # Disable not implemented features
        ui.findChild(QtWidgets.QToolButton, "tb_solver").setEnabled(False)
        ui.findChild(QtWidgets.QLineEdit, "le_solver").setEnabled(False)
        ui.findChild(QtWidgets.QLabel, "lbl_solver").setEnabled(False)

        self.pb_solve.setEnabled(False)

        ui.findChild(QtWidgets.QCheckBox, "cb_tracking").setEnabled(False)

        self.progress = ui.findChild(QtWidgets.QProgressBar,
                                     "progress_reconstruction")
        self.progress.setValue(100)

    def set_calibration(self, path: str):
        self._calibration = dl.load_camera_calibration(path)
        if self._calibration and self._transformation:
            self.ui.findChild(
                QtWidgets.QPushButton, "pb_solve").setEnabled(True)
        if self.data is not None:
            self.pb_plots.setEnabled(True)

    def set_transformation(self, path: str):
        self._transformation = dl.load_calib_from_json(path)
        if self._calibration and self._transformation:
            self.ui.findChild(
                QtWidgets.QPushButton, "pb_solve").setEnabled(True)
        if self.data is not None:
            self.pb_plots.setEnabled(True)

    def change_start_frame(self, new_val: int):
        self.start_frame = new_val
        self.pb_plots.setEnabled(True)

    def change_end_frame(self, new_val: int):
        self.end_frame = new_val
        self.pb_plots.setEnabled(True)

    @property
    def solver(self):
        raise NotImplementedError

    @solver.setter
    def solver(self, path: str):
        raise NotImplementedError

    def data_update(self, data: pd.DataFrame):
        self.data = data
        if self.first_update:
            self.update_plots()
            self.pb_plots.setEnabled(False)
            self.first_update = False
        else:
            self.pb_plots.setEnabled(True)

    def select_data(self):
        self.request_data.emit(list(range(self.start_frame,
                                    self.end_frame + 1)), self.used_colors)

    def solve(self):
        track = self.ui.findChild(
            QtWidgets.QCheckBox, "cb_tracking").isChecked()
        if self.data is None or len(self.data) == 0:
            return
        frames = list(range(self.start_frame, self.end_frame + 1))
        self._progress_val = 0.
        self.progress.setValue(0)
        self.pb_solve.setEnabled(False)
        num_colors = len(self.used_colors)
        self._colors_to_solve = num_colors
        for i in range(num_colors):
            color = self.used_colors[i]
            tmp = self.data.loc[self.data.color == color]
            if track:
                tracker = Tracker(tmp, frames, self._calibration,
                                  self._transformation, self.cam_ids, color)
            else:
                tracker = Reconstructor(tmp, frames, self._calibration,
                                        self._transformation, self.cam_ids,
                                        color)
            tracker.signals.progress.connect(
                lambda val: self.progress_update(val / num_colors)
            )
            tracker.signals.error.connect(
                lambda ret: lg.exception_logger(*ret))
            tracker.signals.result.connect(self.solver_result)
            self._threads.start(tracker)

    def solver_result(self, result: pd.DataFrame):
        self._colors_to_solve -= 1
        if self._colors_to_solve == 0:
            self.pb_solve.setEnabled(True)
            self.progress.setValue(100)
        self.updated_data.emit(result)

    def progress_update(self, update: float):
        self._progress_val += 100 * update
        self.progress.setValue(int(self._progress_val))

    def switch_plot_page(self, direction: int):
        idx_max = self.stacked_plots.count() - 1
        idx_new = self.stacked_plots.currentIndex() + direction
        if idx_new > idx_max:
            idx_new = 0
        elif idx_new < 0:
            idx_new = idx_max
        self.stacked_plots.setCurrentIndex(idx_new)

    @QtCore.pyqtSlot(str, str)
    def set_cam_ids(self, cam1: str, cam2: str):
        self.cam_ids = [cam1, cam2]

    @QtCore.pyqtSlot(int, int, list)
    def data_loaded(self, f_min: int, f_max: int, colors: List[str]):
        start = self.ui.findChild(QtWidgets.QSpinBox, "start_frame")
        start.setRange(f_min, f_max)
        start.setValue(f_min)
        end = self.ui.findChild(QtWidgets.QSpinBox, "end_frame")
        end.setRange(f_min, f_max)
        end.setValue(f_max)
        self.update_colors(colors)
        if self.data is None:
            self.first_update = True
        self.select_data()

    def update_colors(self, colors: List[str]):
        color_group = self.ui.findChildren(QtWidgets.QGroupBox)[0]
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
                cb.stateChanged.connect(self.toggle_color)
            cb.setChecked(True)
            group_layout.addWidget(cb, row, col)
            if col == 1:
                col = 0
                row += 1
            else:
                col = 1

    def toggle_color(self, _: int):
        """Update whether to use an available color.

        Parameters
        ----------
        _ : int
        """
        self.used_colors = []
        for cb in self.ui.findChildren(QtWidgets.QCheckBox):
            if "tracking" in cb.objectName():
                continue
            if cb.checkState():
                self.used_colors.append(cb.objectName().split("_")[1])
        self.pb_plots.setEnabled(True)

    def update_frames(self, start: int, end: int):
        spb_start = self.ui.findChild(QtWidgets.QSpinBox, "start_frame")
        spb_end = self.ui.findChild(QtWidgets.QSpinBox, "end_frame")
        spb_start.setValue(start)
        spb_end.setValue(end)

    def update_plots(self):
        while self.stacked_plots.count():
            self.stacked_plots.removeWidget(self.stacked_plots.currentWidget())
        plt.close()
        if self.data is None or len(self.data) == 0:
            return
        data_plt = self.data.loc[(self.data["frame"] >= self.start_frame) &
                                 (self.data["frame"] <= self.end_frame)]
        plotter = Plotter(
            data_plt.copy(), colors=self.used_colors,
            start_frame=self.start_frame, end_frame=self.end_frame,
            position_scaling=self.position_scaling,
            calibration=self._calibration, transformation=self._transformation
        )
        plotter.signals.result_plot.connect(self.add_plot)
        plotter.signals.error.connect(lambda ret: lg.exception_logger(*ret))
        self._threads.start(plotter)
        self.pb_plots.setEnabled(False)

    @QtCore.pyqtSlot(Figure)
    def add_plot(self, fig: Figure):
        canvas = b_qt.FigureCanvasQTAgg(fig)
        nav_bar = b_qt.NavigationToolbar2QT(canvas, None)
        widget = QtWidgets.QWidget()
        widget.setLayout(QtWidgets.QVBoxLayout())
        widget.layout().setContentsMargins(0, 0, 0, 0)
        widget.layout().addWidget(canvas)
        widget.layout().addWidget(nav_bar)
        self.stacked_plots.insertWidget(self.stacked_plots.count(), widget)
        fig.tight_layout()
        return

    @QtCore.pyqtSlot(dict)
    def update_settings(self, settings: dict) -> None:
        """Catches updates of the settings from a `Settings` class.

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


def choose_calibration(line_edit: QtWidgets.QLineEdit,
                       destination_func: callable):
    # check for a directory
    ui_dir = line_edit.text()
    # opens directory to select image
    kwargs = {}
    # handle file path issue when running on linux as a snap
    if 'SNAP' in os.environ:
        kwargs["options"] = QtWidgets.QFileDialog.DontUseNativeDialog
    chosen_file, _ = QtWidgets.QFileDialog.getOpenFileName(
        line_edit, 'Open a calibration', ui_dir, '*.json',
        **kwargs)
    if chosen_file == "":
        # File selection was aborted
        return None
    else:
        destination_func(chosen_file)
        line_edit.setText(chosen_file)
