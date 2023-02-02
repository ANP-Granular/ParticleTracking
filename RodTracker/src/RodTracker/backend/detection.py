from pathlib import Path
from typing import List, Dict
import torch
import pandas as pd
from PyQt5 import QtCore
from ParticleDetection.utils import (detection, helper_funcs as hf,
                                     datasets as ds)


class DetectorSignals(QtCore.QObject):
    error = QtCore.pyqtSignal(tuple, name="error")
    progress = QtCore.pyqtSignal([float, pd.DataFrame], name="progress")
    result = QtCore.pyqtSignal(pd.DataFrame, name="result")


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
            self.signals.progress.emit((i + 1) / num_frames, tmp_data)
        data.reset_index(drop=True, inplace=True)
        # TODO: change the signature, currently it just outputs an empty
        # dataframe
        self.signals.result.emit(data)
