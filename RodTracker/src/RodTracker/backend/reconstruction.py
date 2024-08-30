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
import sys
import warnings
from typing import List

import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from ParticleDetection.reconstruct_3D import calibrate_cameras as cc
from ParticleDetection.reconstruct_3D import matchND
from ParticleDetection.reconstruct_3D import visualization as vis
from ParticleDetection.reconstruct_3D.match2D import match_frame
from ParticleDetection.utils import data_loading as dl
from PyQt5 import QtCore
from scipy.spatial.transform import Rotation as R

from RodTracker.backend.parallelism import error_handler

_logger = logging.getLogger(__name__)
abort_reconstruction: bool = False
lock = QtCore.QReadWriteLock(QtCore.QReadWriteLock.NonRecursive)


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
    """Object to run the generation of 3D reconstruction and tracking plots.

    This object should run the generation of evaluation plots for the 3D
    reconstruction of the whole or a portion of a dataset. It is capable of
    running it in a thread different from the *main* thread to not keep the
    application responsive.

    Parameters
    ----------
    data : DataFrame
        Slice of the *main* rod position dataset that shall be used for
        plotting.

    Attributes
    ----------
    data : DataFrame
        Slice of the *main* rod position dataset that will be used for
        plotting.
    signals : PlotterSignals
        Signals that can be emitted during the running of a :class:`Plotter`
        object. Their purpose is to report errors and (intermediate) results.
    kwargs : dict
        Keyword arguments that will be used by the plotting functions. The
        currrently recognized keywords are:\n
        ``"colors"``, ``"start_frame"``, ``"end_frame"``,
        ``"position_scaling"``, ``"cam_ids"``, ``"calibration"``, and
        ``"transformation"``
    """

    def __init__(self, data: pd.DataFrame, **kwargs):
        self.data = data
        self.signals = PlotterSignals()
        self.kwargs = kwargs
        super().__init__()

    @error_handler
    def run(self):
        """Run the plotting of 3D reconstruction and tracking plots in this
        :class:`Plotter` object.

        This function is not intended to be run directly but by invoking it via
        a ``QThreadPool.start(plotter)`` call.


        .. hint::

            **Emits**

            - :attr:`PlotterSignals.error`       **(potentially repeatedly)**
            - :attr:`PlotterSignals.result_plot` **(potentially repeatedly)**
        """
        try:
            with warnings.catch_warnings():
                warnings.simplefilter(action="ignore", category=UserWarning)
                self.generate_plots(self.data, **self.kwargs)
        except:  # noqa: E722
            exctype, value, tb = sys.exc_info()
            self.signals.error.emit((exctype, value, tb))

    def generate_plots(self, data: pd.DataFrame, **kwargs):
        """Wrapper function for all plotting functions that unpacks options and
        then runs the plotting with the appropriate settings.

        Parameters
        ----------
        data : DataFrame
            Slice of the *main* rod position dataset that will be used for
            plotting.


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
        cam_ids = kwargs.get("cam_ids")
        try:
            self.plot_displacements_3d(data, colors, start_f, end_f)
        except:  # noqa: E722
            exctype, value, tb = sys.exc_info()
            self.signals.error.emit((exctype, value, tb))
        try:
            self.plot_rod_lengths(data, scale)
        except:  # noqa: E722
            exctype, value, tb = sys.exc_info()
            self.signals.error.emit((exctype, value, tb))
        try:
            self.plot_reprojection_errors(data, cam_ids, calib, scale, trafo)
        except:  # noqa: E722
            exctype, value, tb = sys.exc_info()
            self.signals.error.emit((exctype, value, tb))

    def plot_displacements_3d(
        self,
        data: pd.DataFrame,
        colors: List[str] = None,
        start_frame: int = None,
        end_frame: int = None,
    ):
        """Plot the frame-wise (minimum) displacement per rod and average of
        rods for multiple colors.

        From the 3D positions of rods the between frames displacement is
        calculated for each of the given rods. Both rod endpoint combinations
        are used to calculate the displacement and the respective minimum is
        chosen for plotting. The resulting plot then consists of one line per
        given particle, as well as, the average displacement of all particles
        between the frames.
        One ``Figure`` is generated for every color given in ``colors``.

        Parameters
        ----------
        data : pd.DataFrame
            (Slice of) a dataset of rod position data. Must contain the
            columns:\n
            ``color``, ``"particle"``, ``"frame"``, ``"x1"``, ``"y1"``,
            ``"z1"``, ``"x2"``, ``"y2"``, ``"z2"``
        colors : List[str], optional
            List of colors present in ``data`` that for which a plot shall be
            created. If this is not specified, i.e. set to ``None``, all colors
            in ``data`` will be used.\n
            By default ``None``.
        start_frame : int, optional
            First frame that shall be included in the generated plots. If this
            is not specified, i.e. set to ``None``, the lowest frame number
            found in ``data`` will be used.\n
            By default ``None``.
        end_frame : int, optional
            Last frame that shall be included in the generated plots. If this
            is not specified, i.e. set to ``None``, the highest frame number
            found int ``data`` will be used.\n
            By default ``None``.

        See also
        --------
        :meth:`ParticleDetection.reconstruct_3D.visualization.displacement_fwise`,
        :meth:`ParticleDetection.utils.data_loading.extract_3d_data`


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
            _logger.error(
                "Only received data for one frame. "
                "Cannot compute a 3D displacement plot."
            )
            return
        for color in colors:
            c_data = data.loc[data.color == color]
            if not len(c_data):
                # No plottable data available for this color
                continue
            to_plot = dl.extract_3d_data(c_data)
            if np.isnan(to_plot).all():
                # No plottable data available for this color
                continue
            fig = vis.displacement_fwise(
                to_plot, frames=np.arange(start_frame, end_frame), show=False
            )
            axis = fig.axes[0]
            axis.set_title(color)
            self.signals.result_plot.emit(fig)

    def plot_rod_lengths(
        self, data: pd.DataFrame, position_scaling: float = None
    ):
        """Plot a histogram of rod lengths.

        Plot a histogram of all rod lengths present in the given ``DataFrame``.
        The ``DataFrame`` therefore must contain a column called ``l`` that
        contains this data.

        Parameters
        ----------
        data : DataFrame
            (Slice of) a dataset of rod position data. Must contain the
            column:\n
            ``l``
        position_scaling : float, optional
            Scaling value by which to multiply the given data, in case it has
            been saved in a scaled form. If this is not specified, i.e. is set
            to ``None``, a scaling factor of ``1.0`` is chosen and the data
            will therefore not be changed.\n
            By default ``None``.

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
            _logger.error(
                "Did not receive any valid particle length data. "
                "Cannot compute histogram of lengths."
            )
            return
        len_fig = vis.length_hist(rod_lens.reshape((-1)))
        self.signals.result_plot.emit(len_fig)

    def plot_reprojection_errors(
        self,
        data: pd.DataFrame,
        cam_ids: List[str],
        calibration: dict = None,
        position_scaling: float = 1.0,
        transformation: dict = None,
    ):
        """Plot a histogram of reprojection errors.

        Plot a histogram of reprojection errors from 3D coordinates to 2D
        image coordinates for all rods present in the given ``DataFrame``.

        Parameters
        ----------
        data : pd.DataFrame
            (Slice of) a dataset of rod position data. Must contain the
            columns:\n
            ``'x1'``, ``'y1'``, ``'z1'``, ``'x2'``, ``'y2'``, ``'z2'``,
            ``'x1_{cam_id1}'``, ``'y1_{cam_id1}'``, ``'x2_{cam_id1}'``,
            ``'y2_{cam_id1}'``, ``'x1_{cam_id2}'``, ``'y1_{cam_id2}'``,
            ``'x2_{cam_id2}'``, ``'y2_{cam_id2}'``
        cam_ids : List[str]
            The IDs are used to identify the 2D data columns.
        calibration : dict, optional
            Stereo camera calibration data for the camera setup given in
            ``data``. The calculation reprojection errors depends on this and
            will therefore fail if this is not given, i.e. set to ``None``.\n
            By default ``None``.
        position_scaling : float, optional
            Scaling value by which to multiply the given data, in case it has
            been saved in a scaled form. If this is not specified, i.e. is set
            to ``None``, a scaling factor of ``1.0`` is chosen and the data
            will therefore not be changed.\n
            By default ``1.0``.
        transformation : dict, optional
            Transformation from the first camera's coordinate system to the
            experiment/world coordinate system. Providing a ``transformation``
            might not be essential, depending on the given ``data``. If
            ``data`` is given in the first camera's coordinate system this
            value should either not be set or a neutral transformation, that
            does not change the coordinate system.\n
            By default ``None``.

        See also
        --------
        :meth:`~ParticleDetection.reconstruct_3D.visualization.reprojection_errors_hist`,
        :meth:`reproject_data`,
        :meth:`~ParticleDetection.reconstruct_3D.calibrate_cameras.reproject_points`


        .. hint::

            **Emits**

            - :attr:`PlotterSignals.result_plot`
        """
        if data is None:
            _logger.error(f"Insufficient position data was provided: {data}")
        if calibration is None:
            _logger.error(
                f"Insufficient calibration data was provided: {calibration}"
            )
        if position_scaling is None:
            position_scaling = 1.0
        rep_errs = self.reproject_data(
            data, cam_ids, calibration, position_scaling, transformation
        )
        if rep_errs is not None:
            err_fig = vis.reprojection_errors_hist(rep_errs.reshape((-1)))
            self.signals.result_plot.emit(err_fig)

    @staticmethod
    def reproject_data(
        data: pd.DataFrame,
        cam_ids: List[str],
        calibration: dict,
        position_scaling: float = 1.0,
        transformation: dict = None,
    ):
        """Calculate reprojection errors for each row in a rod position data
        ``DataFrame``.

        Parameters
        ----------
        data : pd.DataFrame
            (Slice of) a dataset of rod position data. Must contain the
            columns:\n
            ``'x1'``, ``'y1'``, ``'z1'``, ``'x2'``, ``'y2'``, ``'z2'``,
            ``'x1_{cam_id1}'``, ``'y1_{cam_id1}'``, ``'x2_{cam_id1}'``,
            ``'y2_{cam_id1}'``, ``'x1_{cam_id2}'``, ``'y1_{cam_id2}'``,
            ``'x2_{cam_id2}'``, ``'y2_{cam_id2}'``
        cam_ids : List[str]
            The IDs are used to identify the 2D data columns.
        calibration : dict
            Stereo camera calibration data for the camera setup given in
            ``data``. The calculation reprojection errors depends on this and
            will therefore fail and return if this is not given, i.e. set to
            ``None``.
        position_scaling : float, optional
            Scaling value by which to multiply the given data, in case it has
            been saved in a scaled form. If this is not specified, i.e. is set
            to ``None``, a scaling factor of ``1.0`` is chosen and the data
            will therefore not be changed.\n
            By default ``1.0``.
        transformation : dict, optional
            Transformation from the first camera's coordinate system to the
            experiment/world coordinate system.
            Providing a ``transformation`` might not be essential, depending on
            the given ``data``. If ``data`` is given in the first camera's
            coordinate system this value should either not be set or a neutral
            transformation, that does not change the coordinate system.\n
            By default ``None``.

        Returns
        -------
        ndarray | None
            Absolute reprojection errors, with one value per row in ``data``.
            This function returns ``None``, if either no calibration data is
            given or ``data`` does not contain all necessary columns.

        See also
        --------
        :meth:`~ParticleDetection.reconstruct_3D.calibrate_cameras.reproject_points`
        """
        if calibration is None:
            return
        id1 = cam_ids[0]
        id2 = cam_ids[1]
        # fmt: off
        cols = ['x1', 'y1', 'z1', 'x2', 'y2', 'z2', 'x', 'y', 'z', 'l',
                f'x1_{id1:s}', f'y1_{id1:s}', f'x2_{id1:s}', f'y2_{id1:s}',
                f'x1_{id2:s}', f'y1_{id2:s}', f'x2_{id2:s}', f'y2_{id2:s}']
        # fmt: on
        data = data[cols]
        e1_3d = data.iloc[:, 0:3].to_numpy(dtype=float) * position_scaling
        e2_3d = data.iloc[:, 3:6].to_numpy(dtype=float) * position_scaling
        e1_2d_c1 = data.iloc[:, 10:12].to_numpy(dtype=float) * position_scaling
        e2_2d_c1 = data.iloc[:, 12:14].to_numpy(dtype=float) * position_scaling
        e1_2d_c2 = data.iloc[:, 14:16].to_numpy(dtype=float) * position_scaling
        e2_2d_c2 = data.iloc[:, 16:18].to_numpy(dtype=float) * position_scaling

        repr_errs = []

        # drop rows with nan
        to_drop_e1 = np.isnan(e1_3d).all(axis=1)
        to_drop_e2 = np.isnan(e2_3d).all(axis=1)
        e1_3d = e1_3d[~to_drop_e1]
        e1_2d_c1 = e1_2d_c1[~to_drop_e1]
        e1_2d_c2 = e1_2d_c2[~to_drop_e1]
        e2_3d = e2_3d[~to_drop_e2]
        e2_2d_c1 = e2_2d_c1[~to_drop_e2]
        e2_2d_c2 = e2_2d_c2[~to_drop_e2]

        if not len(e1_3d) or not len(e2_3d):
            # No reconstructable data available.
            return

        e1_repr_c1, e1_repr_c2 = cc.reproject_points(
            e1_3d, calibration, transformation
        )
        e2_repr_c1, e2_repr_c2 = cc.reproject_points(
            e2_3d, calibration, transformation
        )
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
    """Object for running the reconstruction of 3D rod coordinates in a thread
    different from the main thread.

    This object runs the reconstruction of 3D coordinates of rods from their
    2D stereo camera coordinates. The assignment of rod numbers remains
    untouched in with this method, i.e. there is **NO** automatic tracking of
    particles over multiple frames and **NO** per frame reprojection error
    optimization.

    Parameters
    ----------
    data : DataFrame
        data : pd.DataFrame
            (Slice of) a dataset of rod position data. Must contain at least
            following the columns:\n
            ``'x1_{cam_id1}'``, ``'y1_{cam_id1}'``, ``'x2_{cam_id1}'``,
            ``'y2_{cam_id1}'``, ``'x1_{cam_id2}'``, ``'y1_{cam_id2}'``,
            ``'x2_{cam_id2}'``, ``'y2_{cam_id2}'``, ``'frame'``
    frames : List[int]
        Frames the reconstruction of rods will be performed on.
    calibration : dict
        Stereocamera calibration parameters with the required fields:\n
        ``"CM1"``: camera matrix of cam1\n
        ``"R"``: rotation matrix between cam1 & cam2\n
        ``"T"``: translation vector between cam1 & cam2\n
        ``"CM2"``: camera matrix of cam2
    transformation : dict
        Coordinate system transformation matrices from camera 1 coordinates to
        *world*/*experiment* coordinates.
        **Must contain the following fields:**\n
        ``"rotation"``, ``"translation"``\n
        If no transformation is desired, either set this value to ``None`` or
        use as neutral transformation.
    cams : List[str]
        IDs of the cameras from whos images the 2D position data was generated.
    color : str
        Color of the rods in :attr:`data`. This value will also be written to
        the output ``DataFrame``.

    Attributes
    ----------
    data : DataFrame
        (Slice of) a dataset of rod position data. Must contain at least
        following the columns:\n
        ``'x1_{cam_id1}'``, ``'y1_{cam_id1}'``, ``'x2_{cam_id1}'``,
        ``'y2_{cam_id1}'``, ``'x1_{cam_id2}'``, ``'y1_{cam_id2}'``,
        ``'x2_{cam_id2}'``, ``'y2_{cam_id2}'``, ``'frame'``
    frames : List[int]
        Frames the reconstruction of rods will be performed on.
    calibration : dict
        Stereocamera calibration parameters with the required fields:\n
        ``"CM1"``: camera matrix of cam1\n
        ``"R"``: rotation matrix between cam1 & cam2\n
        ``"T"``: translation vector between cam1 & cam2\n
        ``"CM2"``: camera matrix of cam2
    transformation : dict
        Coordinate system transformation matrices from camera 1 coordinates to
        *world*/*experiment* coordinates.
        **Must contain the following fields:**\n
       ``"rotation"``, ``"translation"``\n
        If no transformation is desired, either set this value to ``None`` or
        use as neutral transformation.
    cams : List[str]
        IDs of the cameras from whos images the 2D position data was generated.
    color : str
        Color of the rods in :attr:`data`. This value will also be written to
        the output ``DataFrame``.
    signals : TrackerSignals
        Signals that can be emitted during the running of a
        :class:`Reconstructor` object. Their purpose is to report errors,
        progress, and (intermediate) results.

    See also
    --------
    :meth:`~ParticleDetection.reconstruct_3D.match2D.match_frame`
    """

    def __init__(
        self,
        data: pd.DataFrame,
        frames: List[int],
        calibration: dict,
        transformation: dict,
        cams: List[str],
        color: str,
    ):
        super().__init__()
        self.data = data
        self.frames = frames
        self.calibration = calibration
        self.transform = transformation
        self.cams = cams
        self.color = color
        self.signals = TrackerSignals()

    @error_handler
    def run(self):
        """Run the reconstruction of 3D rod coordinates with the parameters set
        in this :class:`Reconstructor` object.

        This function is not intended to be run directly but by invoking it via
        a ``QThreadPool.start(reconstructor)`` call.

        See also
        --------
        :meth:`~ParticleDetection.reconstruct_3D.match2D.match_frame`


        .. hint::

            **Emits**

            - :attr:`TrackerSignals.error`
            - :attr:`TrackerSignals.progress`
            - :attr:`TrackerSignals.result`
        """
        global abort_reconstruction, lock
        try:
            # Derive projection matrices from the calibration
            r1 = np.eye(3)
            t1 = np.expand_dims(np.array([0.0, 0.0, 0.0]), 1)
            P1 = np.vstack((r1.T, t1.T)) @ self.calibration["CM1"].T
            P1 = P1.T

            r2 = self.calibration["R"]
            t2 = self.calibration["T"]
            P2 = np.vstack((r2.T, t2.T)) @ self.calibration["CM2"].T
            P2 = P2.T

            rot = R.from_matrix(self.transform["rotation"])
            trans = self.transform["translation"]

            df_out = pd.DataFrame()
            num_frames = len(self.frames)
            for i in range(num_frames):
                lock.lockForRead()
                if abort_reconstruction:
                    lock.unlock()
                    df_out.reset_index(drop=True, inplace=True)
                    self.signals.result.emit(df_out)
                    return
                lock.unlock()

                # fmt: off
                tmp = match_frame(
                    self.data, self.cams[0], self.cams[1], self.frames[i],
                    self.color, self.calibration, P1, P2, rot, trans,
                    r1, r2, t1, t2, renumber=False
                )[0]
                # fmt: on

                df_out = pd.concat([df_out, tmp])
                self.signals.progress.emit(1 / num_frames)
            df_out.reset_index(drop=True, inplace=True)
            self.signals.result.emit(df_out)
        except:  # noqa: E722
            exctype, value, tb = sys.exc_info()
            self.signals.error.emit((exctype, value, tb))


class Tracker(Reconstructor):
    """Object for running the tracking of rods and reconstruction of 3D rod
    coordinates in a thread different from the main thread.

    This object runs the tracking of rods and simultaneous reconstruction of 3D
    coordinates from their 2D stereo camera coordinates. Rod numbers are
    reassigned in this process.

    Parameters
    ----------
    data : DataFrame
        data : pd.DataFrame
            (Slice of) a dataset of rod position data. Must contain at least
            following the columns:\n
            ``'x1_{cam_id1}'``, ``'y1_{cam_id1}'``, ``'x2_{cam_id1}'``,
            ``'y2_{cam_id1}'``, ``'x1_{cam_id2}'``, ``'y1_{cam_id2}'``,
            ``'x2_{cam_id2}'``, ``'y2_{cam_id2}'``, ``'frame'``
    frames : List[int]
        Frames the reconstruction of rods will be performed on.
    calibration : dict
        Stereocamera calibration parameters with the required fields:\n
        ``"CM1"``: camera matrix of cam1\n
        ``"R"``: rotation matrix between cam1 & cam2\n
        ``"T"``: translation vector between cam1 & cam2\n
        ``"CM2"``: camera matrix of cam2
    transformation : dict
        Coordinate system transformation matrices from camera 1 coordinates to
        *world*/*experiment* coordinates.
        **Must contain the following fields:**\n
        ``"rotation"``, ``"translation"``\n
        If no transformation is desired, either set this value to ``None`` or
        use as neutral transformation.
    cams : List[str]
        IDs of the cameras from whos images the 2D position data was generated.
    color : str
        Color of the rods in :attr:`data`. This value will also be written to
        the output ``DataFrame``.

    Attributes
    ----------
    data : DataFrame
        (Slice of) a dataset of rod position data. Must contain at least
        following the columns:\n
        ``'x1_{cam_id1}'``, ``'y1_{cam_id1}'``, ``'x2_{cam_id1}'``,
        ``'y2_{cam_id1}'``, ``'x1_{cam_id2}'``, ``'y1_{cam_id2}'``,
        ``'x2_{cam_id2}'``, ``'y2_{cam_id2}'``, ``'frame'``
    frames : List[int]
        Frames the reconstruction of rods will be performed on.
    calibration : dict
        Stereocamera calibration parameters with the required fields:\n
        ``"CM1"``: camera matrix of cam1\n
        ``"R"``: rotation matrix between cam1 & cam2\n
        ``"T"``: translation vector between cam1 & cam2\n
        ``"CM2"``: camera matrix of cam2
    transformation : dict
        Coordinate system transformation matrices from camera 1 coordinates to
        *world*/*experiment* coordinates.
        **Must contain the following fields:**\n
        ``"rotation"``, ``"translation"``\n
        If no transformation is desired, either set this value to ``None`` or
        use as neutral transformation.
    cams : List[str]
        IDs of the cameras from whos images the 2D position data was generated.
    color : str
        Color of the rods in :attr:`data`. This value will also be written to
        the output ``DataFrame``.
    signals : TrackerSignals
        Signals that can be emitted during the running of a
        :class:`Tracker` object. Their purpose is to report errors,
        progress, and (intermediate) results.

    See also
    --------
    :meth:`~ParticleDetection.reconstruct_3D.matchND.match_frame`
    """

    @error_handler
    def run(self):
        """Run the tracking of rods coordinates with the parameters set
        in this :class:`Tracker` object.

        This function is not intended to be run directly but by invoking it via
        a ``QThreadPool.start(reconstructor)`` call.

        See also
        --------
        :meth:`~ParticleDetection.reconstruct_3D.matchND.match_frame`


        .. hint::

            **Emits**

            - :attr:`TrackerSignals.error`
            - :attr:`TrackerSignals.progress`
            - :attr:`TrackerSignals.result`
        """
        global abort_reconstruction, lock
        try:
            # Derive projection matrices from the calibration
            r1 = np.eye(3)
            t1 = np.expand_dims(np.array([0.0, 0.0, 0.0]), 1)
            P1 = np.vstack((r1.T, t1.T)) @ self.calibration["CM1"].T
            P1 = P1.T

            r2 = self.calibration["R"]
            t2 = self.calibration["T"]
            P2 = np.vstack((r2.T, t2.T)) @ self.calibration["CM2"].T
            P2 = P2.T

            rot = R.from_matrix(self.transform["rotation"])
            trans = self.transform["translation"]

            num_frames = len(self.frames)
            df_out = pd.DataFrame()
            # TODO: add a check, that the frame has 3D data
            if self.frames[0] - 1 not in self.data.frame.unique():
                # Do a 2-dimensional reconstruction of 3D positions, because
                # there is no initial 3D data to relate to.
                lock.lockForRead()
                if abort_reconstruction:
                    df_out.reset_index(drop=True, inplace=True)
                    self.signals.result.emit(df_out)
                    lock.unlock()
                    return
                lock.unlock()

                # fmt: off
                tmp = match_frame(
                    self.data, self.cams[0], self.cams[1], self.frames[0],
                    self.color, self.calibration, P1, P2, rot, trans,
                    r1, r2, t1, t2, renumber=True
                )[0]
                # fmt: on

                df_out = pd.concat([df_out, tmp])
                self.frames = self.frames[1:]
                self.signals.progress.emit(1 / num_frames)
            else:
                # Set initial 3D data to previous frame
                tmp = self.data[self.data.frame == self.frames[0] - 1]

            for i in range(len(self.frames)):
                lock.lockForRead()
                if abort_reconstruction:
                    df_out.reset_index(drop=True, inplace=True)
                    self.signals.result.emit(df_out)
                    lock.unlock()
                    return
                lock.unlock()

                # Track particles
                # fmt: off
                tmp = matchND.match_frame(
                    self.data, tmp, self.cams[0], self.cams[1], self.frames[i],
                    self.color, self.calibration, P1, P2, rot,
                    trans, r1, r2, t1, t2
                )[0]
                # Rematch rod endpoints for better position results
                tmp = match_frame(
                    tmp, self.cams[0], self.cams[1], self.frames[i],
                    self.color, self.calibration, P1, P2, rot, trans,
                    r1, r2, t1, t2, renumber=False
                )[0]
                # fmt: on

                df_out = pd.concat([df_out, tmp])
                self.signals.progress.emit(1 / num_frames)
            df_out.reset_index(drop=True, inplace=True)
            self.signals.result.emit(df_out)
        except:  # noqa: E722
            exctype, value, tb = sys.exc_info()
            self.signals.error.emit((exctype, value, tb))
