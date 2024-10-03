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
Includes objects and methods used for detection of particles by RodTracker.

**Author:**     Adrian Niemann (adrian.niemann@ovgu.de)\n
**Date:**       2022-2024
"""

import logging
from pathlib import Path
from typing import Dict, List

import pandas as pd
import torch
from ParticleDetection.utils import datasets as ds
from ParticleDetection.utils import detection
from ParticleDetection.utils import helper_funcs as hf
from PyQt5 import QtCore

from RodTracker.backend.logger import Action, NotInvertableError
from RodTracker.backend.parallelism import error_handler

_logger = logging.getLogger(__name__)
abort_requested: bool = False
lock = QtCore.QReadWriteLock(QtCore.QReadWriteLock.NonRecursive)


class RodDetection(Action):
    """Representation of the detection of rods on one frame as a loggable
    action.

    Parameters
    ----------
    frame : int
        Frame the rods have been detected on.
    cam_id : str
        ID of the camera the image was produced by.
    num_detected: int
        Total number of rods that have been detected, i.e. all colors combined.
    *args : Iterable
        Positional arguments after ``text`` of the :class:`.Action`
        superclass.
    **kwargs : dict
        Keyword arguments of the :class:`.Action` superclass.

    Attributes
    ----------
    num_detected : int
        Total number of rods that have been detected, i.e. all colors combined.
    """

    cam_id: str
    """str : ID of the camera the image was produced by."""

    def __init__(
        self, frame: int, cam_id: str, num_detected: int, *args, **kwargs
    ):
        self.cam_id = cam_id
        self.num_detected = num_detected
        self._frame = frame
        super().__init__(str(self), *args, **kwargs)

    def __str__(self):
        return (
            f"({self.cam_id}, {self._frame}) Detected {self.num_detected} "
            f"rods."
        )

    def undo(self, _):
        """
        Raises
        ------
        NotInvertableError
            This action is generally not invertable.
        """
        raise NotInvertableError


class DetectorSignals(QtCore.QObject):
    """Helper object to provide :class:`Detector` access to ``pyqtSignal``."""

    error = QtCore.pyqtSignal(tuple, name="error")
    """pyqtSignal(tuple) : Signal for propagating errors occuring in the
    :class:`Worker`'s thread.\n
    | The transferred tuple should contain the following values:
    | [0]: Exception type
    | [1]: Exception value
    | [2]: Exception traceback

    See Also
    --------
    `sys.exc_info()`_

    :py:obj:`sys.exc_info`

    .. _sys.exc_info():
        https://docs.python.org/3/library/sys.html#sys.exc_info
    """

    progress = QtCore.pyqtSignal([float, pd.DataFrame, str], name="progress")
    """pyqtSignal(float, DataFrame, str) : Reports the progress of started
    detections.

    [0]: progress as the ratio of finished frames over all frames, so
    :math:`\\in [0, 1]`

    [1]: DataFrame containing only the 2D data of the detected rods.\n
    See also: :func:`ParticleDetection.utils.datasets.add_points`

    [2]: ID of the camera dataset the frame is taken from.
    """

    finished = QtCore.pyqtSignal(str, name="finished")
    """pyqtSignal(str) : Indicates the detection has finished successfully.

    The payload is the ID of the camera dataset this detection process was run
    on.
    """


class Detector(QtCore.QRunnable):
    """Object for running the detection of rods in a thread different from the
    main thread.

    This object runs the detection of rods in a set of frames for one camera
    angle. The desired colors to detect and their expected occurrences must be
    specified. Only predefined colors are supported at the moment.

    Parameters
    ----------
    cam_id : str
        ID of the camera on whos images the detection of rods shall be run.
    model : ScriptModule
        Neural network model that shall be used for detection.
    images : List[Path]
        Paths to the image files the detection of rods shall be performed on.
        Each entry in :attr:`images` corresponds to one in :attr:`frames`.
    frames : List[int]
        Frames the detection of rods will be performed on. Each entry in
        :attr:`frames` corresponds to one in :attr:`images`.
    classes : Dict[int, list]
        Classes of objects to detect in the images, i.e. rod colors that shall
        be detected, togther with their human readable name and the amount of
        particles that shall be detected per frame individually for each class.
        list[0] : color as a ``str``
        list[1] : expected amount of particles as an ``int``
    threshold : float, optional
        Confidence threshold :math:`\\in [0, 1]` below which objects are
        rejected after detection.\n
        Default is ``0.5``.

    Raises
    ------
    ValueError
        Is raised when ``len(images) != len(frames)``.

    See also
    --------
    :const:`~ParticleDetection.utils.datasets.DEFAULT_CLASSES`

    Attributes
    ----------
    cam_id : str
        ID of the camera on whos images the detection of rods shall be run.
    frames : List[int]
        Frames the detection of rods will be performed on. Each entry in
        :attr:`frames` corresponds to one in :attr:`images`.
    images : List[Path]
        Paths to the image files the detection of rods will be performed on.
        Each entry in :attr:`images` corresponds to one in :attr:`frames`.
    model : ScriptModule
        Neural network model that will be used for detection.
    signals : DetectorSignals
        Signals that can be emitted during the running of a :class:`Detector`
        object. Their purpose is to report errors, progress, and (intermediate)
        results.
    threshold : float
        Confidence threshold :math:`\\in [0, 1]` below which objects are
        rejected after detection.\n
        :math:`\\in [0, 1]`
    expected : Dict[int, int]
        The amount of particles per frame for each class that shall be
        detected.
        ``expected[class] = amount``
    """

    classes: Dict[int, str] = {}
    """Dict[int, str] : Classes of objects to detect in the images, i.e.
    rod colors that will be detected.

    Default is ``{}``."""

    def __init__(
        self,
        cam_id: str,
        model: torch.ScriptModule,
        images: List[Path],
        frames: List[int],
        classes: Dict[int, list],
        threshold: float = 0.5,
    ):
        super().__init__()
        self.cam_id = cam_id
        self.model = model
        self.signals = DetectorSignals()
        if len(images) != len(frames):
            raise ValueError(
                "There must be the same number of images and frames."
            )
        self.images = images
        self.frames = frames
        self.expected: Dict[int, int] = {}
        for id, description in classes.items():
            color = description[0]
            amount = description[1]
            self.classes[id] = color
            self.expected[id] = amount
        if threshold > 1.0:
            threshold = 1.0
        elif threshold < 0.0:
            threshold = 0.0
        self.threshold = threshold

    @error_handler
    def run(self):
        """Run the detection of rods with the parameters set in this
        :class:`Detector` object.

        This function is not intended to be run directly but by invoking it via
        a ``QThreadPool.start(detector)`` call.


        .. admonition:: Emits

            - :attr:`DetectorSignals.error`
            - :attr:`DetectorSignals.progress`
            - :attr:`DetectorSignals.finished`
        """
        global abort_requested
        cols = [
            col.format(id1=self.cam_id, id2=self.cam_id)
            for col in ds.DEFAULT_COLUMNS
        ]
        data = pd.DataFrame(columns=cols)
        data = data.loc[:, ~data.columns.duplicated()]
        num_frames = len(self.images)
        for i in range(num_frames):
            lock.lockForRead()
            if abort_requested:
                lock.unlock()
                self.signals.finished.emit(self.cam_id)
                return
            lock.unlock()
            img = self.images[i]
            frame = self.frames[i]
            outputs = detection._run_detection(self.model, img)
            if "pred_masks" in outputs:
                points = hf.rod_endpoints(
                    outputs, self.classes, expected_particles=self.expected
                )
                tmp_data = ds.add_points(points, data, self.cam_id, frame)
            self.signals.progress.emit(1 / num_frames, tmp_data, self.cam_id)
        data.reset_index(drop=True, inplace=True)
        self.signals.finished.emit(self.cam_id)
