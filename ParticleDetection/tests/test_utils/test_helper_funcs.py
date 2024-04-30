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

import itertools

import numpy as np
import pytest
import torch
from conftest import create_dummy_mask

import ParticleDetection.utils.helper_funcs as hf


@pytest.fixture()
def detection_result():
    width = 500
    height = 500
    masks = np.zeros((3, width, height))
    endpoints = np.zeros((3, 2, 2))
    for i in range(3):
        masks[i, :, :], endpoints[i, 0, :], endpoints[i, 1, :] = (
            create_dummy_mask(width, height, 0, 100, 10)
        )
    test_prediction = {
        "pred_classes": torch.tensor([0, 1, 4]),
        "pred_masks": torch.tensor(masks),
    }
    return test_prediction


widths = [750, 1003]
heights = [750, 1003]
angles = [0, 10, 67, 83]
lengths = [10, 100, 200]
thicknesses = [3, 7, 15]
parameters = list(
    itertools.product(widths, heights, angles, lengths, thicknesses)
)


@pytest.mark.parametrize("width,height,angle,length,thickness", parameters)
def test_line_estimator_simple(width, height, angle, length, thickness):
    mask, ep1, ep2 = create_dummy_mask(width, height, angle, length, thickness)
    out = hf.line_estimator_simple(mask)

    if (out == -1).all():
        # no line found, also a valid return value
        return

    # do assertion only on better fitting pair
    diff_0 = np.min(
        [np.linalg.norm(out[0] - ep1), np.linalg.norm(out[0] - ep2)]
    )
    diff_1 = np.min(
        [np.linalg.norm(out[1] - ep1), np.linalg.norm(out[1] - ep2)]
    )
    assert (diff_0 < 10.0) and (diff_1 < 10.0)


@pytest.mark.filterwarnings("ignore:invalid value")
@pytest.mark.parametrize("width,height,angle,length,thickness", parameters)
def test_line_estimator(width, height, angle, length, thickness):
    mask, ep1, ep2 = create_dummy_mask(width, height, angle, length, thickness)
    out = hf.line_estimator(mask)
    if (out == -1).all():
        # no line found, also a valid return value
        return

    # do assertion only on better fitting pair
    diff_0 = np.min(
        [np.linalg.norm(out[0] - ep1), np.linalg.norm(out[0] - ep2)]
    )
    diff_1 = np.min(
        [np.linalg.norm(out[1] - ep1), np.linalg.norm(out[1] - ep2)]
    )
    assert (diff_0 < 10.0) and (diff_1 < 10.0)


def test_rod_endpoints(monkeypatch: pytest.MonkeyPatch):
    width = 500
    height = 500
    masks = np.zeros((3, width, height))
    endpoints = np.zeros((3, 2, 2))
    for i in range(3):
        masks[i, :, :], endpoints[i, 0, :], endpoints[i, 1, :] = (
            create_dummy_mask(width, height, 0, 100, 10)
        )
    test_prediction = {
        "pred_classes": torch.tensor([0, 1, 4]),
        "pred_masks": torch.tensor(masks),
    }
    next_line = 0

    def provide_endpoints(*args, **kwargs):
        nonlocal next_line
        next_line += 1
        return endpoints[next_line - 1]

    test_classes = {0: "test0", 1: "test1", 4: "test4"}
    monkeypatch.setattr(hf, "line_estimator_simple", provide_endpoints)
    test_result = hf.rod_endpoints(test_prediction, test_classes)
    assert isinstance(test_result, dict)
    assert set(test_result.keys()) == set(test_classes.values())


def test_rod_endpoints_expected_int(monkeypatch: pytest.MonkeyPatch):
    width = 500
    height = 500
    masks = np.zeros((3, width, height))
    endpoints = np.zeros((3, 2, 2))
    for i in range(3):
        masks[i, :, :], endpoints[i, 0, :], endpoints[i, 1, :] = (
            create_dummy_mask(width, height, i * 10, 100, 10)
        )
    test_prediction = {
        "pred_classes": torch.tensor([0, 1, 4]),
        "pred_masks": torch.tensor(masks),
    }
    next_line = 0

    def provide_endpoints(*args, **kwargs):
        nonlocal next_line
        next_line += 1
        return endpoints[next_line - 1]

    test_classes = {0: "test0", 1: "test1", 4: "test4"}
    monkeypatch.setattr(hf, "line_estimator_simple", provide_endpoints)
    test_result = hf.rod_endpoints(
        test_prediction, test_classes, expected_particles=3
    )
    for k, v in test_result.items():
        assert len(v) == 3
        assert (v[1:] == np.array([[-1, -1], [-1, -1]])).all()
        assert v[0] in endpoints


def test_rod_endpoints_expected_dict(monkeypatch: pytest.MonkeyPatch):
    width = 500
    height = 500
    masks = np.zeros((3, width, height))
    endpoints = np.zeros((3, 2, 2))
    for i in range(3):
        masks[i, :, :], endpoints[i, 0, :], endpoints[i, 1, :] = (
            create_dummy_mask(width, height, i * 10, 100, 10)
        )
    test_prediction = {
        "pred_classes": torch.tensor([0, 1, 4]),
        "pred_masks": torch.tensor(masks),
    }
    next_line = 0

    def provide_endpoints(*args, **kwargs):
        nonlocal next_line
        next_line += 1
        return endpoints[next_line - 1]

    test_classes = {0: 0, 1: 1, 4: 4}
    monkeypatch.setattr(hf, "line_estimator_simple", provide_endpoints)
    expected = {0: 4, 1: 5, 2: 1, 4: 2}
    test_result = hf.rod_endpoints(
        test_prediction, test_classes, expected_particles=expected
    )
    assert len(test_result.keys()) == 3
    for k, v in test_result.items():
        assert len(v) == expected[k]
        assert (v[1:] == np.array([[-1, -1], [-1, -1]])).all()
        assert v[0] in endpoints


def test_rod_endpoints_excessive_particles(monkeypatch: pytest.MonkeyPatch):
    width = 500
    height = 500
    masks = np.zeros((1, 3, width, height))
    endpoints = np.zeros((3, 2, 2))
    for i in range(3):
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
    next_line = 0

    def provide_endpoints(*args, **kwargs):
        nonlocal next_line
        next_line += 1
        return endpoints[next_line - 1]

    test_classes = {0: "test0"}
    monkeypatch.setattr(hf, "line_estimator_simple", provide_endpoints)
    test_result = hf.rod_endpoints(
        test_prediction, test_classes, expected_particles=2
    )
    assert list(test_result.keys()) == [
        "test0",
    ]
    assert len(test_result["test0"]) == 2


def test_rod_endpoints_unknown_method():
    width = 500
    height = 500
    masks = np.zeros((3, width, height))
    for i in range(3):
        masks[i, :, :], _, _ = create_dummy_mask(width, height, 0, 100, 10)
    test_prediction = {
        "pred_classes": torch.tensor([0, 1, 4]),
        "pred_masks": torch.tensor(masks),
    }
    test_classes = {0: "test0", 1: "test1", 4: "test4"}
    with pytest.raises(ValueError, match="Unknown extraction method"):
        hf.rod_endpoints(test_prediction, test_classes, method="test")
