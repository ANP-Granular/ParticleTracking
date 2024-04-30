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

import ParticleDetection.reconstruct_3D.match2D as m2d
import ParticleDetection.utils.data_loading as dl


@pytest.fixture(scope="session")
def example_data() -> pd.DataFrame:
    data_file = EXAMPLES / "rods_df_black.csv"
    data = pd.read_csv(data_file, index_col=0)
    return data


@pytest.mark.parametrize("rematching", [False, True])
def test_match_csv_complex(tmp_path: Path, rematching: bool):
    colors = [
        "black",
    ]
    frames = list(range(505, 508))

    calibration = EXAMPLES / "gp34.json"
    transformation = EXAMPLES / "transformation.json"
    data_folder = EXAMPLES
    assert not (tmp_path / "output").exists()

    result = m2d.match_csv_complex(
        str(data_folder),
        str(tmp_path / "output"),
        colors,
        "gp3",
        "gp4",
        frames,
        calibration,
        transformation,
        rematching,
    )
    assert len(result) == 2
    assert (tmp_path / "output").exists()
    assert len(list((tmp_path / "output").iterdir())) == 1
    result_df = pd.read_csv(tmp_path / "output/rods_df_black.csv", index_col=0)
    assert list(result_df.frame.unique()) == frames


@pytest.mark.parametrize("renumber", [False, True])
def test_match_complex(
    tmp_path: Path, example_data: pd.DataFrame, renumber: bool
):
    color = "black"
    cam1 = "gp3"
    cam2 = "gp4"
    frames = list(range(505, 508))

    calibration = dl.load_camera_calibration(EXAMPLES / "gp34.json")
    transformation = dl.load_world_transformation(
        EXAMPLES / "transformation.json"
    )
    result = m2d.match_complex(
        example_data,
        frames,
        color,
        calibration,
        transformation,
        cam1,
        cam2,
        renumber,
    )
    assert len(result) == 3
    assert len(result[0].frame.unique()) == len(frames)

    for f in frames:
        input_len = len(example_data.loc[example_data.frame == f])
        result_f = result[0].loc[result[0].frame == f]
        assert len(result_f) == input_len


@pytest.mark.filterwarnings("ignore::FutureWarning")
@pytest.mark.parametrize("renumber", [False, True])
def test_match_frame(example_data: pd.DataFrame, renumber: bool):
    frame = 508
    color = "black"
    cam1 = "gp3"
    cam2 = "gp4"
    cols_2D = [
        f"x1_{cam1}",
        f"y1_{cam1}",
        f"x2_{cam1}",
        f"y2_{cam1}",
        f"x1_{cam2}",
        f"y1_{cam2}",
        f"x2_{cam2}",
        f"y2_{cam2}",
    ]
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

    result = m2d.match_frame(
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
        renumber,
    )
    assert len(result) == 3
    input_len = len(example_data.loc[example_data.frame == frame])
    assert len(result[0]) == input_len
    assert result[1].shape == (input_len,)
    assert result[2].shape == (input_len,)
    if not renumber:
        input_data = example_data.loc[example_data.frame == frame]
        for particle in list(result[0].particle.unique()):
            previous_data = input_data.loc[
                input_data.particle == particle, cols_2D
            ]
            for col in cols_2D:
                assert previous_data.isin(
                    result[0].loc[result[0].particle == particle, col]
                ).any(axis=None)
