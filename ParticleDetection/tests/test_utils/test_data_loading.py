import json
from pathlib import Path
import pytest
import cv2
import torch
import numpy as np
import ParticleDetection.utils.data_loading as dl
from conftest import load_rod_data

transformation = {
    "rotation": np.random.rand(3, 3).tolist(),
    "translation": np.random.rand(1, 3).tolist()
}
legacy_transformation = {
    "transformations": {
        "M_rotate_x": np.random.rand(3, 4).tolist(),
        "M_rotate_y": np.random.rand(3, 4).tolist(),
        "M_rotate_z": np.random.rand(3, 4).tolist(),
        "M_trans": np.random.rand(3, 4).tolist(),
        "M_trans2": np.random.rand(3, 4).tolist()
    }
}


@pytest.mark.parametrize("trafo", (transformation, legacy_transformation))
def test_load_world_transformation(trafo: dict, tmpdir: Path):
    trafo_file = tmpdir / "transformation.json"
    with open(trafo_file, "w") as f:
        json.dump(trafo, f)
    loaded = dl.load_world_transformation(str(trafo_file))
    assert isinstance(loaded, dict)
    assert "rotation" in loaded
    assert "translation" in loaded
    assert isinstance(loaded["rotation"], np.ndarray)
    assert isinstance(loaded["translation"], np.ndarray)
    assert loaded["rotation"].shape == (3, 3)
    assert ((loaded["translation"].shape == (3, 1)) or
            (loaded["translation"].shape == (1, 3)) or
            (loaded["translation"].shape == (3,)))


def test_load_transformation_wrong_format(tmpdir: Path):
    trafo = {
        "rot": np.random.rand(3, 3).tolist(),
        "trans": np.random.rand(1, 3).tolist()
    }
    trafo_file = tmpdir / "transformation.json"
    with open(trafo_file, "w") as f:
        json.dump(trafo, f)
    with pytest.raises(ValueError):
        dl.load_world_transformation(trafo_file)


def test_load_calibration(tmpdir: Path):
    calib = {
        "test0": np.random.rand(3,).tolist(),
        "test1": np.random.rand(3, 1).tolist(),
        "test2": np.random.rand(3, 2).tolist(),
        "test3": np.random.rand(3, 3).tolist(),
    }
    calib_file = tmpdir / "calibration.json"
    with open(calib_file, "w") as f:
        json.dump(calib, f)
    loaded = dl.load_camera_calibration(str(calib_file))
    assert loaded.keys() == calib.keys()
    for k in loaded.keys():
        assert isinstance(loaded[k], np.ndarray)
        assert (loaded[k] == calib[k]).all()


def test_read_image(tmpdir: Path):
    width = 100
    height = 200
    test_img = np.random.randint(0, 255, (width, height, 3))
    img_path = Path(tmpdir) / "test.png"
    cv2.imwrite(str(img_path), test_img)
    loaded = dl.read_image(img_path)
    assert isinstance(loaded, torch.Tensor)
    loaded = loaded.numpy().squeeze()
    np.testing.assert_allclose(loaded[0], test_img[:, :, 0])
    np.testing.assert_allclose(loaded[1], test_img[:, :, 1])
    np.testing.assert_allclose(loaded[2], test_img[:, :, 2])


def test_extract_3d_data():
    test_data = load_rod_data(["blue"])
    frames = len(test_data.frame.unique())
    particles = len(test_data.particle.unique())

    extracted = dl.extract_3d_data(test_data)
    assert extracted.shape == (frames, particles, 3, 2)
    assert not np.isnan(extracted).all()
    cols1 = ["x1", "y1", "z1"]
    cols2 = ["x2", "y2", "z2"]
    for end_point in test_data[cols1].values:
        assert end_point in extracted[:, :, :, 0]
    for end_point in test_data[cols2].values:
        assert end_point in extracted[:, :, :, 1]


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_extract_stereo_params():
    calibration = {
        "FundamentalMatrix": np.random.rand(3, 3).tolist(),
        "EssentialMatrix": np.random.rand(3, 3).tolist(),
        "RotationOfCamera2": np.random.rand(3, 3).tolist(),
        "TranslationOfCamera2": np.random.rand(3, 1).tolist()
    }
    loaded = dl.extract_stereo_params(calibration)
    assert set(loaded.keys()) == {"F", "R", "T", "E"}
