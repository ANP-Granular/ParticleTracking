# Copyright (c) 2023-24 Adrian Niemann, Dmitry Puzyrev, and others
#
# This file is part of ParticleDetection.
# ParticleDetection is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ParticleDetection is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ParticleDetection. If not, see <http://www.gnu.org/licenses/>.

from pathlib import Path

import numpy as np
import pytest
import torch
from conftest import create_dummy_mask

import ParticleDetection.utils.detection as det


def test_run_detection(monkeypatch: pytest.MonkeyPatch, tmpdir):
    width = 500
    height = 500
    num_predictions = 3
    masks = np.zeros((1, num_predictions, width, height))
    endpoints = np.zeros((num_predictions, 2, 2))
    for i in range(num_predictions):
        masks[0, i, :, :], endpoints[i, 0, :], endpoints[i, 1, :] = (
            create_dummy_mask(width, height, i * 10, 100, 10)
        )
    test_prediction = {
        "pred_classes": torch.tensor(
            [
                0,
            ]
        ),
        "pred_masks": torch.tensor(masks),
    }
    dataset_format = "/{cam_id:s}/{frame:04d}.jpg"
    classes = {0: "black", 1: "blue"}

    monkeypatch.setattr(
        det, "_run_detection", lambda *args, **kwargs: test_prediction
    )

    det.run_detection(
        None,
        dataset_format,
        classes,
        Path(tmpdir),
        frames=list(range(501, 504)),
        cam1_name="gp3",
        cam2_name="gp4",
    )
    tmpdir = Path(tmpdir)
    for file in tmpdir.iterdir():
        if not file.is_file():
            continue
        assert "rods_df" in file.name
        assert file.stem.split("_")[-1] in ["df", "black"]
