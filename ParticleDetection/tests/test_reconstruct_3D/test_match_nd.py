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
import pandas as pd
import pytest
from conftest import EXAMPLES
from scipy.spatial.transform import Rotation as R

import ParticleDetection.reconstruct_3D.matchND as mnd
import ParticleDetection.utils.data_loading as dl


@pytest.fixture(scope="session")
def example_data() -> pd.DataFrame:
    data_file = EXAMPLES / "rods_df_black.csv"
    data = pd.read_csv(data_file, index_col=0)
    return data


@pytest.mark.parametrize(
    "test_shape",
    [(2, 3, 4), (2, 3), (4, 3, 7), (3, 4, 5, 6), (7, 10, 1, 3, 5)],
)
def test_npartite_matching(test_shape):
    weights = np.random.random(test_shape)
    result = mnd.npartite_matching(weights)
    assert len(result) == len(test_shape)
    max_out_dim = np.min(test_shape)
    for i, dim in enumerate(test_shape):
        assert result[i].shape == (max_out_dim,)
        assert np.max(result[i]) <= dim - 1


@pytest.mark.parametrize(
    "dimensions", [(10, 10, 10), (4, 5, 4), (4, 5, 5), (3, 4, 5)]
)
def test_create_weights(dimensions):
    cam1_dim = dimensions[0]
    cam2_dim = dimensions[1]
    previous_dim = dimensions[2]

    p_3D = np.random.random((cam1_dim, cam2_dim, 4, 3))
    p_3D_prev = np.random.random((previous_dim, 2, 3))
    repr_errs = np.random.random((cam1_dim, cam2_dim, 4, 2))

    result = mnd.create_weights(p_3D, p_3D_prev, repr_errs)
    assert len(result) == 2
    assert result[0].shape == (previous_dim, cam1_dim, cam2_dim)
    assert result[1].shape == (previous_dim, cam1_dim, cam2_dim)


def test_assign(tmp_path: Path):
    colors = [
        "black",
    ]
    frames = list(range(505, 508))

    calibration = EXAMPLES / "gp34.json"
    transformation = EXAMPLES / "transformation.json"
    data_folder = EXAMPLES
    assert not (tmp_path / "output").exists()

    result = mnd.assign(
        str(data_folder),
        str(tmp_path / "output"),
        colors,
        "gp3",
        "gp4",
        frames,
        calibration,
        transformation,
    )
    assert len(result) == 2
    assert (tmp_path / "output").exists()
    assert len(list((tmp_path / "output").iterdir())) == 1
    result_df = pd.read_csv(tmp_path / "output/rods_df_black.csv", index_col=0)
    assert list(result_df.frame.unique()) == frames


def test_match_frame_nd(example_data: pd.DataFrame):
    frame = 508
    color = "black"
    calibration = dl.load_camera_calibration(EXAMPLES / "gp34.json")
    transformation = dl.load_world_transformation(
        EXAMPLES / "transformation.json"
    )

    # Derive projection matrices from the calibration
    r1 = np.eye(3)
    t1 = np.expand_dims(np.array([0.0, 0.0, 0.0]), 1)
    P1 = np.vstack((r1.T, t1.T)) @ calibration["CM1"].T
    P1 = P1.T

    r2 = calibration["R"]
    t2 = calibration["T"]
    P2 = np.vstack((r2.T, t2.T)) @ calibration["CM2"].T
    P2 = P2.T

    # Preparation of world transformations
    rot = R.from_matrix(transformation["rotation"])
    trans = transformation["translation"]

    result = mnd.match_frame(
        example_data,
        example_data,
        "gp3",
        "gp4",
        frame,
        color,
        calibration,
        P1,
        P2,
        rot,
        trans,
        r1,
        r2,
        t1,
        t2,
    )
    assert len(result) == 3
    input_len = len(example_data.loc[example_data.frame == frame])
    assert len(result[0]) == input_len
    assert result[1].shape == (input_len,)
    assert result[2].shape == (input_len,)
