#  Copyright (c) 2023 Adrian Niemann Dmitry Puzyrev
#
#  This file is part of ParticleDetection.
#  ParticleDetection is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  ParticleDetection is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with ParticleDetection.  If not, see <http://www.gnu.org/licenses/>.

import sys
from types import ModuleType
import json
from pathlib import Path
import numpy as np
import ParticleDetection.utils.datasets as ds
not_installed = False
try:
    from ParticleDetection.modelling import annotations
except ModuleNotFoundError:
    not_installed = True
    # Mock imports of detectron2 modules to allow running of function tests,
    # that don't depend on them.
    module = ModuleType('detectron2')
    submodule = ModuleType('structures')
    submodule.Instances = None
    submodule.BoxMode = None
    sys.modules["detectron2"] = module
    sys.modules["detectron2.structures"] = submodule

    submodule2 = ModuleType("utils")
    subsubmodule = ModuleType("visualizer")
    subsubmodule.GenericMask = None
    subsubmodule.Visualizer = None
    sys.modules["detectron2.utils"] = submodule2
    sys.modules["detectron2.utils.visualizer"] = subsubmodule
finally:
    from ParticleDetection.modelling import annotations


def test_remove_duplicate_regions(tmp_path: Path):
    test_annotations = {
        "test0": {"regions": np.random.rand(3, 3).tolist()},
        "test1": {"regions": [[1, 1, 1], [2, 1, 1], [1, 1, 1], [13, 12]]},
        "test2": {"regions": np.random.rand(3, 3).tolist()},
    }
    with open(tmp_path / "test.json", "w") as f:
        json.dump(test_annotations, f)
    test_dataset = ds.DataSet("test", str(tmp_path), "/test.json")
    annotations.remove_duplicate_regions(test_dataset)
    with open(tmp_path / "test.json", "r") as f:
        adjusted_data = json.load(f)

    assert (len(adjusted_data["test1"]["regions"]) ==
            len(test_annotations["test1"]["regions"]) - 1)
    assert adjusted_data["test0"] == test_annotations["test0"]
    assert adjusted_data["test2"] == test_annotations["test2"]


def test_change_visibility(tmp_path: Path):
    test_annotations = {
        "test0": {"regions": [
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, "region_attributes": {"rod_col": 0}, "keypoints": [150.76229162112642, 753.8142013053987, 1, 186.26318608587994, 818.8991744907798, 0]},  # noqa: E501
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, "region_attributes": {"rod_col": 0}, "keypoints": [150.76229162112642, 753.8142013053987, 2, 186.26318608587994, 818.8991744907798, 1]},  # noqa: E501
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, "region_attributes": {"rod_col": 0}, "keypoints": [150.76229162112642, 753.8142013053987, 0, 186.26318608587994, 818.8991744907798, 2]},  # noqa: E501
        ]},
    }
    with open(tmp_path / "test.json", "w") as f:
        json.dump(test_annotations, f)
    annotations.change_visibiliy(tmp_path / "test.json")
    with open(tmp_path / "test.json", "r") as f:
        adjusted_data = json.load(f)
    regions = adjusted_data["test0"]["regions"]
    for reg in regions:
        assert reg["keypoints"][2] == 2
        assert reg["keypoints"][-1] == 2


def test_change_class(tmp_path: Path):
    test_annotations = {
        "test0": {"regions": [
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '3'}},   # noqa: E501
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '5'}},   # noqa: E501
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '0'}},   # noqa: E501
        ]},
    }
    with open(tmp_path / "test.json", "w") as f:
        json.dump(test_annotations, f)
    annotations.change_class(tmp_path / "test.json")
    with open(tmp_path / "test.json", "r") as f:
        adjusted_data = json.load(f)
    regions = adjusted_data["test0"]["regions"]
    for reg in regions:
        assert int(reg["region_attributes"]["rod_col"]) == 0


def test_order_by_x(tmp_path: Path):
    test_annotations = {
        "test0": {"regions": [
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, "region_attributes": {"rod_col": 0}, "keypoints": [150.76229162112642, 753.8142013053987, 1, 186.26318608587994, 818.8991744907798, 0]},  # noqa: E501
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, "region_attributes": {"rod_col": 0}, "keypoints": [186.26318608587994, 818.8991744907798, 2, 150.76229162112642, 753.8142013053987, 1]},  # noqa: E501
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, "region_attributes": {"rod_col": 0}, "keypoints": [150.76229162112642, 753.8142013053987, 0, 186.26318608587994, 818.8991744907798, 2]},  # noqa: E501
        ]},
    }
    left = [150.76229162112642, 753.8142013053987]
    right = [186.26318608587994, 818.8991744907798]
    with open(tmp_path / "test.json", "w") as f:
        json.dump(test_annotations, f)
    annotations.order_by_x(tmp_path / "test.json")
    with open(tmp_path / "test.json", "r") as f:
        adjusted_data = json.load(f)
    regions = adjusted_data["test0"]["regions"]
    for reg in regions:
        assert reg["keypoints"][0:2] == left
        assert reg["keypoints"][3:5] == right


def test_delete_len_0(tmp_path: Path):
    test_annotations = {
        "test0": {"regions": [
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, "region_attributes": {"rod_col": 0}, "keypoints": [150.76229162112642, 753.8142013053987, 1, 186.26318608587994, 818.8991744907798, 0]},  # noqa: E501
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, "region_attributes": {"rod_col": 0}, "keypoints": [150.76229162112642, 753.8142013053987, 2, 150.76229162112642, 753.8142013053987, 1]},  # noqa: E501
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, "region_attributes": {"rod_col": 0}, "keypoints": [150.76229162112642, 753.8142013053987, 0, 186.26318608587994, 818.8991744907798, 2]},  # noqa: E501
        ]},
    }
    with open(tmp_path / "test.json", "w") as f:
        json.dump(test_annotations, f)
    annotations.delete_len_0(tmp_path / "test.json")
    with open(tmp_path / "test.json", "r") as f:
        adjusted_data = json.load(f)
    assert len(adjusted_data["test0"]["regions"]) == 2
