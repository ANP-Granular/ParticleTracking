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
    """Helper object to provide :class:`Plotter` access to ``pyqtSignal``."""

    result_plot = QtCore.pyqtSignal(Figure, name="result_plot")
    """pyqtSignal(Figure): Transfers a result ``Figure`` for display elsewhere.
    """

    error = QtCore.pyqtSignal(tuple, name="error")
    """pyqtSignal(tuple) : Signal for propagating errors occuring in the
    worker's thread.\n
    | The transferred tuple should contain the following values:
    | [0]: Exception type
    | [1]: Exception value
    | [2]: Exception traceback

    See Also
    --------
    `sys.exc_info()`_

    .. _sys.exc_info():
        https://docs.python.org/3/library/sys.html#sys.exc_info
    """


class Plotter(QtCore.QRunnable):
    """**TBD**"""
    def __init__(self, data: pd.DataFrame, **kwargs):
        self.data = data
        self.signals = PlotterSignals()
        self.kwargs = kwargs
        super().__init__()

    def run(self):
        """**TBD**


        .. hint::

            **Emits**

            - :attr:`PlotterSignals.error`       **(potentially repeatedly)**
            - :attr:`PlotterSignals.result_plot` **(potentially repeatedly)**
        """
        try:
            with warnings.catch_warnings():
                warnings.simplefilter(action="ignore", category=UserWarning)
                self.generate_plots(self.data, **self.kwargs)
        except:                                                 # noqa: E722
            exctype, value, tb = sys.exc_info()
            self.signals.error.emit((exctype, value, tb))

    def generate_plots(self, data: pd.DataFrame, **kwargs):
        """**TBD**

        Parameters
        ----------
        data : pd.DataFrame
            **TBD**


        .. hint::

            **Emits**

            - :attr:`PlotterSignals.error`       **(potentially repeatedly)**
            - :attr:`PlotterSignals.result_plot` **(potentially repeatedly)**
        """
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
        """**TBD**

        Parameters
        ----------
        data : pd.DataFrame
            **TBD**
        colors : List[str], optional
            **TBD**
            By default None.
        start_frame : int, optional
            **TBD**
            By default None.
        end_frame : int, optional
            **TBD**
            By default None.

        See also
        --------
        :meth:`ParticleDetection.reconstruct_3D.visualization.displacement_fwise`


        .. hint::

            **Emits**

            - :attr:`PlotterSignals.result_plot`
        """
        if colors is None:
            colors = list(data["color"].unique())
        if start_frame is None:
            start_frame = data["frame"].min()
        if end_frame is None:
            end_frame = data["frame"].max()
        if start_frame == end_frame:
            _logger.error("Only received data for one frame. "
                          "Cannot compute a 3D displacement plot.")
            return
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
        """**TBD**

        Parameters
        ----------
        data : DataFrame
            **TBD**
        position_scaling : float, optional
            **TBD**
            By default None.

        See also
        --------
        :meth:`ParticleDetection.reconstruct_3D.visualization.length_hist`


        .. hint::

            **Emits**

            - :attr:`PlotterSignals.result_plot`
        """
        if position_scaling is None:
            position_scaling = 1.0
        rod_lens = data["l"].dropna().to_numpy() * position_scaling
        if not len(rod_lens):
            _logger.error("Did not receive any valid particle length data. "
                          "Cannot compute histogram of lengths.")
            return
        len_fig = vis.length_hist(rod_lens.reshape((-1)))
        self.signals.result_plot.emit(len_fig)

    def plot_reprojection_errors(self, data: pd.DataFrame, calibration: dict,
                                 position_scaling: float = 1.0, transformation:
                                 dict = None):
        """**TBD**

        Parameters
        ----------
        data : pd.DataFrame
            **TBD**
        calibration : dict
            **TBD**
        position_scaling : float, optional
            **TBD**
            By default 1.0.
        transformation : dict, optional
            **TBD**
            By default None.

        See also
        --------
        :meth:`ParticleDetection.reconstruct_3D.visualization.reprojection_errors_hist`


        .. hint::

            **Emits**

            - :attr:`PlotterSignals.result_plot`
        """
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
        """**TBD**

        Parameters
        ----------
        data : pd.DataFrame
            **TBD**
        calibration : dict
            **TBD**
        position_scaling : float, optional
            **TBD**
            By default 1.0.
        transformation : dict, optional
            **TBD**
            By default None.

        Returns
        -------
        ndarray | None
            **TBD**
        """
        if calibration is None:
            return
        # check all columns are present and in order, such that the below code
        # works
        cols = list(data.columns)
        cols_ok = (cols[0:3] == ["x1", "y1", "z1"])
        cols_ok = cols_ok or (cols[3:6] == ["x2", "y2", "z2"])
        cols_3d = ['x1', 'y1', 'z1', 'x2', 'y2', 'z2', 'x', 'y', 'z', 'l']
        cols_2d = ['x1_', 'y1_', 'x2_', 'y2_']
        cols_2d_ok = [(intended in col)
                      for col, intended in zip(cols[10:18], 2 * cols_2d)]
        if not ((cols[0:10] == cols_3d) and all(cols_2d_ok)):
            _logger.error(f"Incorrect columns/order provided. "
                          f"Data must adhere to the following column order: "
                          f"{[*cols_3d, *(2*cols_2d)]}")
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
    """Helper object to provide :class:`Reconstructor` and class:`Tracker`
    access to ``pyqtSignal``."""
    error = QtCore.pyqtSignal(tuple, name="error")
    """pyqtSignal(tuple) : Signal for propagating errors occuring in the
    worker's thread.\n
    | The transferred tuple should contain the following values:
    | [0]: Exception type
    | [1]: Exception value
    | [2]: Exception traceback

    See Also
    --------
    `sys.exc_info()`_

    .. _sys.exc_info():
        https://docs.python.org/3/library/sys.html#sys.exc_info
    """

    progress = QtCore.pyqtSignal(float, name="progress")
    """pyqtSignal(float) : Reports the progress of the started computation.

    The progress is reported as the ratio of finished iterations over all
    iterations, so :math:`\\in [0, 1]`.
    """

    result = QtCore.pyqtSignal(pd.DataFrame, name="result")
    """pyqtSignal(DataFrame) : Reports the result of completed reconstructions.
    """


class Reconstructor(QtCore.QRunnable):
    """**TBD**"""
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
        """**TBD**


        .. hint::

            **Emits**

            - :attr:`TrackerSignals.error`
            - :attr:`TrackerSignals.progress`
            - :attr:`TrackerSignals.result`
        """
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


class Tracker(Reconstructor):
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

            raise NotImplementedError
            for i in range(num_frames):
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
