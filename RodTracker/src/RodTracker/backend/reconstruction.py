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
import warnings
import logging
from typing import List
import pandas as pd
import numpy as np
from matplotlib.figure import Figure
from scipy.spatial.transform import Rotation as R

from PyQt5 import QtCore
from ParticleDetection.reconstruct_3D import calibrate_cameras as cc
from ParticleDetection.reconstruct_3D import visualization as vis
from ParticleDetection.utils import data_loading as dl
from ParticleDetection.reconstruct_3D.match2D import match_frame

_logger = logging.getLogger(__name__)


class PlotterSignals(QtCore.QObject):
    result_plot = QtCore.pyqtSignal(Figure, name="result_plot")
    error = QtCore.pyqtSignal(tuple, name="error")


class Plotter(QtCore.QRunnable):
    def __init__(self, data: pd.DataFrame, **kwargs):
        self.data = data
        self.signals = PlotterSignals()
        self.kwargs = kwargs
        super().__init__()

    def run(self):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter(action="ignore", category=UserWarning)
                self.generate_plots(self.data, **self.kwargs)
        except:                                                 # noqa: E722
            exctype, value, tb = sys.exc_info()
            self.signals.error.emit((exctype, value, tb))

    def generate_plots(self, data: pd.DataFrame, **kwargs):
        colors = kwargs.get("colors")
        start_f = kwargs.get("start_frame")
        end_f = kwargs.get("end_frame")
        scale = kwargs.get("position_scaling")
        calib = kwargs.get("calibration")
        trafo = kwargs.get("transformation")
        try:
            self.plot_displacements_3d(data, colors, start_f, end_f)
        except:                                                 # noqa: E722
            exctype, value, tb = sys.exc_info()
            self.signals.error.emit((exctype, value, tb))
        try:
            self.plot_rod_lengths(data, scale)
        except:                                                 # noqa: E722
            exctype, value, tb = sys.exc_info()
            self.signals.error.emit((exctype, value, tb))
        try:
            self.plot_reprojection_errors(data, calib, scale, trafo)
        except:                                                 # noqa: E722
            exctype, value, tb = sys.exc_info()
            self.signals.error.emit((exctype, value, tb))

    def plot_displacements_3d(self, data: pd.DataFrame, colors: List[str] =
                              None, start_frame: int = None, end_frame: int =
                              None):
        if colors is None:
            colors = list(data["color"].unique())
        if start_frame is None:
            start_frame = data["frame"].min()
        if end_frame is None:
            end_frame = data["frame"].max()
        for color in colors:
            c_data = data.loc[data.color == color]
            to_plot = dl.extract_3d_data(c_data)
            fig = vis.displacement_fwise(
                to_plot, frames=np.arange(start_frame, end_frame),
                show=False)
            axis = fig.axes[0]
            axis.set_title(color)
            self.signals.result_plot.emit(fig)

    def plot_rod_lengths(self, data: pd.DataFrame, position_scaling: float =
                         None):
        if position_scaling is None:
            position_scaling = 1.0
        rod_lens = data["l"].to_numpy() * position_scaling
        len_fig = vis.length_hist(rod_lens.reshape((-1)))
        self.signals.result_plot.emit(len_fig)

    def plot_reprojection_errors(self, data: pd.DataFrame, calibration: dict,
                                 position_scaling: float = 1.0, transformation:
                                 dict = None):
        if data is None:
            _logger.error(f"Insufficient position data was provided: "
                          f"{data}")
        if calibration is None:
            _logger.error(f"Insufficient calibration data was provided:"
                          f" {calibration}")
        if position_scaling is None:
            position_scaling = 1.0
        rep_errs = self.reproject_data(data, calibration, position_scaling,
                                       transformation)
        if rep_errs is not None:
            err_fig = vis.reprojection_errors_hist(rep_errs.reshape((-1)))
            self.signals.result_plot.emit(err_fig)

    @staticmethod
    def reproject_data(data: pd.DataFrame, calibration: dict,
                       position_scaling: float = 1.0, transformation: dict =
                       None):
        if calibration is None:
            return
        e1_3d = data.iloc[:, 0:3].to_numpy() * position_scaling
        e2_3d = data.iloc[:, 3:6].to_numpy() * position_scaling
        e1_2d_c1 = data.iloc[:, 10:12].to_numpy() * position_scaling
        e2_2d_c1 = data.iloc[:, 12:14].to_numpy() * position_scaling
        e1_2d_c2 = data.iloc[:, 14:16].to_numpy() * position_scaling
        e2_2d_c2 = data.iloc[:, 16:18].to_numpy() * position_scaling

        repr_errs = []
        e1_repr_c1, e1_repr_c2 = cc.reproject_points(
            e1_3d, calibration, transformation)
        e2_repr_c1, e2_repr_c2 = cc.reproject_points(
            e2_3d, calibration, transformation)
        repr_errs.append(np.abs(e1_repr_c1 - e1_2d_c1))
        repr_errs.append(np.abs(e1_repr_c2 - e1_2d_c2))
        repr_errs.append(np.abs(e2_repr_c1 - e2_2d_c1))
        repr_errs.append(np.abs(e2_repr_c2 - e2_2d_c2))
        repr_errs = np.sum(np.asarray(repr_errs), axis=-1)
        return repr_errs


class TrackerSignals(QtCore.QObject):
    error = QtCore.pyqtSignal(tuple, name="error")
    progress = QtCore.pyqtSignal(float, name="progress")
    result = QtCore.pyqtSignal(pd.DataFrame, name="result")


class Tracker(QtCore.QRunnable):
    def __init__(self, data: pd.DataFrame, frames: list[int],
                 calibration: dict, transformation: dict, cams: list[str],
                 color: str):
        super().__init__()
        self.data = data
        self.frames = frames
        self.calibration = calibration
        self.transform = transformation
        self.cams = cams
        self.color = color
        self.signals = TrackerSignals()

    def run(self):
        try:
            # Derive projection matrices from the calibration
            r1 = np.eye(3)
            t1 = np.expand_dims(np.array([0., 0., 0.]), 1)
            P1 = np.vstack((r1.T, t1.T)) @ self.calibration["CM1"].T
            P1 = P1.T

            r2 = self.calibration["R"]
            t2 = self.calibration["T"]
            P2 = np.vstack((r2.T, t2.T)) @ self.calibration["CM2"].T
            P2 = P2.T

            rotx = R.from_matrix(
                np.asarray(self.transform["M_rotate_x"])[0:3, 0:3])
            roty = R.from_matrix(
                np.asarray(self.transform["M_rotate_y"])[0:3, 0:3])
            rotz = R.from_matrix(
                np.asarray(self.transform["M_rotate_z"])[0:3, 0:3])
            tw1 = np.asarray(self.transform["M_trans"])[0:3, 3]
            tw2 = np.asarray(self.transform["M_trans2"])[0:3, 3]
            rot = rotz * roty * rotx

            df_out = pd.DataFrame()
            num_frames = len(self.frames)
            for i in range(num_frames):
                # TODO: evaluate, whether its renumber should be "True"
                tmp = match_frame(self.data, self.cams[0], self.cams[1],
                                  self.frames[i],
                                  self.color, self.calibration, P1, P2, rot,
                                  tw1, tw2, r1, r2, t1, t2, renumber=False)[0]
                df_out = pd.concat([df_out, tmp])
                self.signals.progress.emit(1 / num_frames)
            df_out.reset_index(drop=True, inplace=True)
            self.signals.result.emit(df_out)
        except:                                                 # noqa: E722
            exctype, value, tb = sys.exc_info()
            self.signals.error.emit((exctype, value, tb))
