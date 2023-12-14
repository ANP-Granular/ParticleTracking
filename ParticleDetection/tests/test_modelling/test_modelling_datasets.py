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
from enum import Enum
from types import ModuleType
from pathlib import Path
import json
import numpy as np
from PIL import Image
from ParticleDetection.utils.datasets import DataSet
try:
    from ParticleDetection.modelling import datasets
except ModuleNotFoundError:
    # Mock imports of detectron2 modules to allow running of function tests,
    # that don't depend on them.
    module = ModuleType('detectron2')
    submodule = ModuleType('structures')
    submodule.BoxMode = Enum("BoxMode", ["XYXY_ABS", ])
    sys.modules["detectron2"] = module
    sys.modules["detectron2.structures"] = submodule

    submodule2 = ModuleType("data")
    submodule2.DatasetCatalog = None
    submodule2.MetadataCatalog = None
    sys.modules["detectron2.data"] = submodule2

    module2 = ModuleType("shapely")
    submod2_0 = ModuleType("geometry")
    submod2_1 = ModuleType("point")
    submod2_1.Point = None
    submod2_2 = ModuleType("affinity")
    submod2_2.scale = None
    submod2_2.rotate = None
    sys.modules["shapely"] = module2
    sys.modules["shapely.geometry"] = submod2_0
    sys.modules["shapely.geometry.point"] = submod2_1
    sys.modules["shapely.affinity"] = submod2_2
finally:
    from ParticleDetection.modelling import datasets


def test_load_custom_data(tmp_path: Path):
    test_annotations = {
        "test0": {"filename": "testing.png", "regions": [
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '3'}},   # noqa: E501
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '5'}},   # noqa: E501
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '0'}},   # noqa: E501
        ]},
        "test1": {"filename": "testing.png", "regions": [
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '3'}},   # noqa: E501
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '5'}},   # noqa: E501
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '0'}},   # noqa: E501
        ]}
    }
    with open(tmp_path / "test.json", "w") as f:
        json.dump(test_annotations, f)
    im = Image.fromarray((np.random.random((512, 256)) * 255).astype(int),
                         mode="L")
    im.save(tmp_path / "testing.png")
    test_data = DataSet("test", str(tmp_path), "/test.json")
    result = datasets.load_custom_data(test_data)
    assert len(result) == 2
    for idx, res in enumerate(result):
        assert set(res.keys()) == {"image_id", "width", "height", "file_name",
                                   "annotations"}
        assert res["image_id"] == idx
        assert res["width"] == 256
        assert res["height"] == 512


def test_dataset_size(tmp_path: Path):
    test_annotations = {
        "test0": {"filename": "testing.png", "regions": [
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '3'}},   # noqa: E501
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '5'}},   # noqa: E501
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '0'}},   # noqa: E501
        ]},
        "test1": {"filename": "testing.png", "regions": [
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '3'}},   # noqa: E501
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '5'}},   # noqa: E501
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '0'}},   # noqa: E501
        ]},
        "test2": {"filename": "testing.png", "regions": []}
    }
    with open(tmp_path / "test.json", "w") as f:
        json.dump(test_annotations, f)
    test_data = DataSet("test", str(tmp_path), "/test.json")
    result = datasets.get_dataset_size(test_data)
    assert result == 2


def test_dataset_classes(tmp_path: Path):
    test_annotations = {
        "test0": {"filename": "testing.png", "regions": [
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '3'}},   # noqa: E501
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '5'}},   # noqa: E501
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '0'}},   # noqa: E501
        ]},
        "test1": {"filename": "testing.png", "regions": [
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '3'}},   # noqa: E501
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '1'}},   # noqa: E501
            {'shape_attributes': {'name': 'polygon', 'all_points_x': [1025, 1034, 1071, 1062], 'all_points_y': [214, 219, 142, 138]}, 'region_attributes': {'rod_col': '13'}},   # noqa: E501
        ]},
        "test2": {"filename": "testing.png", "regions": []}
    }
    with open(tmp_path / "test.json", "w") as f:
        json.dump(test_annotations, f)
    test_data = DataSet("test", str(tmp_path), "/test.json")
    result = datasets.get_dataset_classes(test_data)
    assert result == {0, 1, 3, 5, 13}
