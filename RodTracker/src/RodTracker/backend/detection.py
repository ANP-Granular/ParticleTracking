import logging
from pathlib import Path
from typing import List, Dict
import torch
import pandas as pd
from PyQt5 import QtCore
from ParticleDetection.utils import (detection, helper_funcs as hf,
                                     datasets as ds)
from RodTracker.backend.logger import Action, NotInvertableError

_logger = logging.getLogger(__name__)


class RodDetection(Action):
    cam_id: str

    def __init__(self, frame: int, cam_id: str, num_detected: int, *args,
                 **kwargs):
        self.cam_id = cam_id
        self.num_detected = num_detected
        self._frame = frame
        super().__init__(str(self), *args, **kwargs)

    def __str__(self):
        return (f"({self.cam_id}, {self._frame}) Detected {self.num_detected} "
                f"rods.")

    def undo(self, _):
        raise NotInvertableError


class DetectorSignals(QtCore.QObject):
    error = QtCore.pyqtSignal(tuple, name="error")
    progress = QtCore.pyqtSignal([float, pd.DataFrame, str], name="progress")
    finished = QtCore.pyqtSignal(str, name="result")


class Detector(QtCore.QRunnable):
    classes: Dict[int, str] = {}

    def __init__(self, cam_id: str, model: torch.ScriptModule,
                 images: List[Path], frames: List[int],
                 colors: Dict[int, str]):
        super().__init__()
        self.cam_id = cam_id
        self.model = model
        self.signals = DetectorSignals()
        if len(images) != len(frames):
            raise ValueError("There must be the same number of images and "
                             "frames.")
        self.images = images
        self.frames = frames
        for color in colors:
            current_class = list(ds.DEFAULT_CLASSES.keys())[
                list(ds.DEFAULT_CLASSES.values()).index(color)]
            self.classes[current_class] = color

    def run(self):
        cols = [col.format(id1=self.cam_id, id2=self.cam_id)
                for col in ds.DEFAULT_COLUMNS]
        data = pd.DataFrame(columns=cols)
        data = data.loc[:, ~data.columns.duplicated()]
        num_frames = len(self.images)
        for i in range(len(self.images)):
            img = self.images[i]
            frame = self.frames[i]
            outputs = detection._run_detection(self.model, img)
            if "pred_masks" in outputs:
                points = hf.rod_endpoints(outputs, self.classes)
                tmp_data = ds.add_points(points, data, self.cam_id, frame)
            self.signals.progress.emit((i + 1) / num_frames, tmp_data,
                                       self.cam_id)
        data.reset_index(drop=True, inplace=True)
        self.signals.finished.emit(self.cam_id)
