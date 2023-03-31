import numpy as np
import pandas as pd
import pytest
import ParticleDetection.reconstruct_3D.calibrate_cameras as cc
import ParticleDetection.utils.data_loading as dl
from conftest import EXAMPLES

calibration = dl.load_camera_calibration(EXAMPLES / "gp34.json")
transformation = dl.load_world_transformation(
    EXAMPLES / "transformation.json")


@pytest.mark.parametrize("transformation", [transformation, None])
def test_project_points(transformation):
    cam1 = np.random.random((2, 100)) * 500
    cam2 = np.random.random((2, 100)) * 500

    result = cc.project_points(cam1, cam2, calibration, transformation)
    assert result.shape == (3, 100)


def test_project_points_default_transform():
    cam1 = np.random.random((2, 100)) * 500
    cam2 = np.random.random((2, 100)) * 500

    result = cc.project_points(cam1, cam2, calibration)
    assert result.shape == (3, 100)


@pytest.mark.parametrize("transformation", [transformation, None])
def test_reproject_points(transformation):
    data_file = EXAMPLES / "rods_df_black.csv"
    data = dl.extract_3d_data(pd.read_csv(data_file, index_col=0))
    data = data.reshape((-1, 3))
    result = cc.reproject_points(data, calibration, transformation)
    assert len(result) == 2
    assert result[0].shape == (len(data), 2)
    assert result[1].shape == (len(data), 2)


def test_reproject_points_default_transform():
    data_file = EXAMPLES / "rods_df_green.csv"
    data = dl.extract_3d_data(pd.read_csv(data_file, index_col=0))
    data = data.reshape((-1, 3))
    result = cc.reproject_points(data, calibration)
    assert len(result) == 2
    assert result[0].shape == (len(data), 2)
    assert result[1].shape == (len(data), 2)
