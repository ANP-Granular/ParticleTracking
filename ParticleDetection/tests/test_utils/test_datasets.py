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

import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from conftest import load_rod_data

from ParticleDetection.utils import datasets


def test_get_object_counts(tmp_path: Path):
    test_objs = [random.randint(1, 5) for _ in range(5)]
    test_data = {i: {"regions": test_objs[i] * ["test"]} for i in range(5)}
    test_file = tmp_path / "test.json"
    with open(test_file, "w") as f:
        json.dump(test_data, f)

    test_dataset = datasets.DataSet("test", str(tmp_path) + "/", "test.json")
    found_objs = datasets.get_object_counts(test_dataset)
    assert found_objs == test_objs


def test_get_dataset_classes(tmp_path: Path):
    test_classes = [random.randint(1, 5) for _ in range(100)]
    test_expected = set(test_classes)
    test_data = {
        i: {"regions": [{"region_attributes": {"rod_col": test_classes[i]}}]}
        for i in range(100)
    }
    test_file = tmp_path / "test.json"
    with open(test_file, "w") as f:
        json.dump(test_data, f)
    test_dataset = datasets.DataSet("test", str(tmp_path) + "/", "test.json")
    found_classes = datasets.get_dataset_classes(test_dataset)
    assert found_classes == test_expected


def test_get_dataset_size(tmp_path: Path):
    test_images = random.choices([0, 1], weights=[0.1, 0.9], k=100)
    test_data = {
        i: {"regions": ["test"]} if test_images[i] == 1 else {"regions": []}
        for i in range(100)
    }
    test_file = tmp_path / "test.json"
    with open(test_file, "w") as f:
        json.dump(test_data, f)

    test_dataset = datasets.DataSet("test", str(tmp_path) + "/", "test.json")
    found_images_w_data = datasets.get_dataset_size(test_dataset)
    assert found_images_w_data == sum(test_images)


def test_insert_missing_rods():
    test_data = load_rod_data(["green", "black"])
    test_data = test_data.loc[test_data.frame == 500]
    previous_numbers = set(test_data["particle"])
    expected = len(test_data.particle.unique()) + 2
    inserted = datasets.insert_missing_rods(test_data, expected, "gp3", "gp4")
    assert len(inserted.particle.unique()) == expected
    inserted_numbers = set(inserted["particle"]).difference(previous_numbers)

    expected_insertions = [*(11 * [float("NaN")]), *(8 * [-1.0]), 0, 0]
    cols = [
        col
        for col in inserted.columns
        if col not in ["frame", "particle", "color"]
    ]
    for num in inserted_numbers:
        for color in inserted.color.unique():
            np.testing.assert_allclose(
                inserted.loc[
                    (inserted.particle == num) & (inserted.color == color),
                    cols,
                ].values.tolist()[0],
                expected_insertions,
            )


def test_replace_missing_rods():
    test_data = load_rod_data(["black"])
    unchanged_cols = [
        "x1",
        "y1",
        "z1",
        "x2",
        "y2",
        "z2",
        "x",
        "y",
        "z",
        "l",
        "frame",
        "particle",
        "color",
    ]
    changed_cols = [
        col for col in test_data.columns if col not in unchanged_cols
    ]
    cols_2d = [
        col
        for col in changed_cols
        if (("gp3" in col) or ("gp4" in col)) and not ("seen" in col)
    ]
    cols_seen = [col for col in changed_cols if "seen" in col]
    nan_selection = np.array(random.choices([False, True], k=len(test_data)))
    test_data.loc[nan_selection] = np.nan
    replaced = datasets.replace_missing_rods(test_data, "gp3", "gp4")
    pd.testing.assert_frame_equal(
        test_data.loc[~nan_selection], replaced.loc[~nan_selection]
    )
    pd.testing.assert_frame_equal(
        test_data.loc[nan_selection, unchanged_cols],
        replaced.loc[nan_selection, unchanged_cols],
    )
    assert (replaced.loc[nan_selection, cols_seen] == 0.0).all(None)
    assert (replaced.loc[nan_selection, cols_2d] == -1.0).all(None)


@pytest.mark.filterwarnings("ignore:indexing past")
@pytest.mark.parametrize("cam_id,frame,", [("gp3", 100), ("gp4", 100)])
def test_add_points(cam_id: str, frame: int):
    test_points = {
        "black": np.array(
            [
                [0, 23.5, 15, 223.78],
                [0, 23.5, 15, 223.78],
                [0, 23.5, 15, 223.78],
            ]
        ),
        "green": np.array([[0, 23.5, 15, 223.78], [0, 23.5, 15, 223.78]]),
    }
    test_data = load_rod_data(["black"])
    accessible = test_data.set_index(["color", "frame", "particle"])
    prev_nums = {}
    for k in test_points.keys():
        try:
            prev_nums[k] = len(accessible.loc[(k, frame)])
        except KeyError:
            prev_nums[k] = 0
    inserted = datasets.add_points(test_points, test_data, cam_id, frame)
    inserted.set_index(["color", "frame", "particle"], inplace=True)
    cam_cols = [col for col in inserted.columns if cam_id in col]
    other_cols = [col for col in inserted.columns if col not in cam_cols]
    for k, v in test_points.items():
        assert len(inserted.loc[k, frame]) == prev_nums[k] + len(v)
        assert inserted.loc[k, frame][other_cols].isna().all(None)
        assert (
            inserted.loc[k, frame][cam_cols].to_numpy()
            == np.append(v, np.ones((len(v), 1)), axis=1)
        ).all()


@pytest.mark.filterwarnings("ignore:indexing past")
def test_add_points_both_cams():
    frame = 100
    test_points = {
        "black": np.array(
            [
                [0, 23.5, 15, 223.78],
                [0, 23.5, 15, 223.78],
                [0, 23.5, 15, 223.78],
            ]
        ),
    }
    test_data = datasets.add_points(
        test_points, load_rod_data(["black"]), "gp3", frame
    )
    inserted = datasets.add_points(test_points, test_data, "gp4", frame)
    sec_cam_cols = [col for col in test_data.columns if "gp4" in col]
    v = test_points["black"]
    inserted.set_index(["color", "frame", "particle"], inplace=True)
    assert (
        inserted.loc["black", frame][sec_cam_cols].to_numpy()
        == np.append(v, np.ones((len(v), 1)), axis=1)
    ).all()
