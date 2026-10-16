import cv2
import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation

from RodTracker.backend.smoothing import (
    project_trajectories,
    smooth_trajectories,
)


def test_smoothing_reduces_pose_noise_and_projects_with_distortion():
    frames = np.arange(30)
    center = np.column_stack(
        [0.25 * frames, 0.1 * frames, np.full(len(frames), 100.0)]
    )
    angle = 0.01 * frames
    axis = np.column_stack([np.cos(angle), np.sin(angle), np.zeros(30)])
    expected = np.stack([center - 5 * axis, center + 5 * axis], axis=1)
    rng = np.random.default_rng(5)
    noisy = expected + rng.normal(0, 0.8, expected.shape)
    noisy[15, 0] += [5, -3, 2]

    calibration = {
        "CM1": [[800, 0, 320], [0, 800, 240], [0, 0, 1]],
        "dist1": [0.08, -0.02, 0.001, 0.002, 0.0],
        "CM2": [[820, 0, 320], [0, 820, 240], [0, 0, 1]],
        "dist2": [-0.04, 0.01, -0.001, 0.001, 0.0],
        "R": np.eye(3).tolist(),
        "T": [-20, 0, 0],
    }
    measured_2d = {}
    for camera_id, rvec, tvec, matrix, distortion in [
        ("cam1", np.zeros(3), np.zeros(3), "CM1", "dist1"),
        (
            "cam2",
            cv2.Rodrigues(np.eye(3))[0],
            [-20, 0, 0],
            "CM2",
            "dist2",
        ),
    ]:
        measured_2d[camera_id] = cv2.projectPoints(
            noisy.reshape(-1, 1, 3),
            rvec,
            np.asarray(tvec, dtype=float),
            np.asarray(calibration[matrix], dtype=float),
            np.asarray(calibration[distortion], dtype=float),
        )[0].reshape(-1, 2, 2)
    data = pd.DataFrame(
        {
            "frame": frames,
            "color": "blue",
            "particle": 1,
            "x1": noisy[:, 0, 0],
            "y1": noisy[:, 0, 1],
            "z1": noisy[:, 0, 2],
            "x2": noisy[:, 1, 0],
            "y2": noisy[:, 1, 1],
            "z2": noisy[:, 1, 2],
            "seen_cam1": 1,
            "seen_cam2": 1,
        }
    )
    for camera_id in ("cam1", "cam2"):
        projected = measured_2d[camera_id]
        if camera_id == "cam1":
            projected += [24, -12]
        else:
            projected += [-18, 9]
        data[f"x1_{camera_id}"] = projected[:, 0, 0]
        data[f"y1_{camera_id}"] = projected[:, 0, 1]
        data[f"x2_{camera_id}"] = projected[:, 1, 0]
        data[f"y2_{camera_id}"] = projected[:, 1, 1]

    result = smooth_trajectories(
        data,
        {"blue": 10.0},
        calibration,
        {"rotation": np.eye(3).tolist(), "translation": [0, 0, 0]},
        ("cam1", "cam2"),
        translation_process_noise=0.05,
        orientation_process_noise=0.0005,
    )
    smoothed_columns = [
        "x1_smooth",
        "y1_smooth",
        "z1_smooth",
        "x2_smooth",
        "y2_smooth",
        "z2_smooth",
    ]
    smoothed = result[smoothed_columns].to_numpy().reshape(-1, 2, 3)
    raw_center_error = np.mean(
        np.sum((noisy.mean(axis=1) - center) ** 2, axis=1)
    )
    smoothed_center_error = np.mean(
        np.sum((smoothed.mean(axis=1) - center) ** 2, axis=1)
    )

    assert smoothed_center_error < raw_center_error
    smoothed_lengths = np.linalg.norm(smoothed[:, 1] - smoothed[:, 0], axis=1)
    assert np.allclose(smoothed_lengths, 10.0)
    for camera_id, rvec, tvec, matrix, distortion in [
        ("cam1", np.zeros(3), np.zeros(3), "CM1", "dist1"),
        (
            "cam2",
            cv2.Rodrigues(np.eye(3))[0],
            [-20, 0, 0],
            "CM2",
            "dist2",
        ),
    ]:
        projected = cv2.projectPoints(
            smoothed.reshape(-1, 1, 3),
            rvec,
            np.asarray(tvec, dtype=float),
            np.asarray(calibration[matrix], dtype=float),
            np.asarray(calibration[distortion], dtype=float),
        )[0].reshape(-1, 2, 2)
        projection_columns = [
            f"x1_{camera_id}_smooth",
            f"y1_{camera_id}_smooth",
            f"x2_{camera_id}_smooth",
            f"y2_{camera_id}_smooth",
        ]
        result_projection = (
            result[projection_columns].to_numpy().reshape(-1, 2, 2)
        )
        assert np.allclose(result_projection, projected)
        raw_projection = measured_2d[camera_id].copy()
        if camera_id == "cam1":
            raw_projection -= [24, -12]
        else:
            raw_projection -= [-18, 9]
        original_columns = [
            f"x1_{camera_id}_original",
            f"y1_{camera_id}_original",
            f"x2_{camera_id}_original",
            f"y2_{camera_id}_original",
        ]
        assert np.allclose(
            result[original_columns].to_numpy().reshape(-1, 2, 2),
            raw_projection,
        )
        assert not any(column.endswith("_overlay") for column in result)


def test_original_reprojection_inverts_nonidentity_world_transform():
    camera_endpoints = np.array([[[15.0, -3.0, 120.0], [25.0, -2.0, 120.0]]])
    rotation = Rotation.from_euler(
        "xyz", [17, -9, 31], degrees=True
    ).as_matrix()
    translation = np.array([12.5, -8.0, 34.0])
    world_endpoints = (
        Rotation.from_matrix(rotation).apply(camera_endpoints.reshape(-1, 3))
        + translation
    ).reshape(1, 2, 3)
    calibration = {
        "CM1": [[800, 0, 320], [0, 800, 240], [0, 0, 1]],
        "dist1": [0.08, -0.02, 0.001, 0.002, 0.0],
        "CM2": [[820, 0, 320], [0, 820, 240], [0, 0, 1]],
        "dist2": [-0.04, 0.01, -0.001, 0.001, 0.0],
        "R": np.eye(3).tolist(),
        "T": [-20, 0, 0],
    }
    data = pd.DataFrame(
        {
            "frame": [12],
            "color": ["blue"],
            "particle": [1],
            "x1": [world_endpoints[0, 0, 0]],
            "y1": [world_endpoints[0, 0, 1]],
            "z1": [world_endpoints[0, 0, 2]],
            "x2": [world_endpoints[0, 1, 0]],
            "y2": [world_endpoints[0, 1, 1]],
            "z2": [world_endpoints[0, 1, 2]],
        }
    )

    result = smooth_trajectories(
        data,
        {"blue": 10.0},
        calibration,
        {"rotation": rotation, "translation": translation},
        ("cam1", "cam2"),
    )

    for camera_id, rvec, tvec, matrix, distortion in [
        ("cam1", np.zeros(3), np.zeros(3), "CM1", "dist1"),
        (
            "cam2",
            cv2.Rodrigues(np.eye(3))[0],
            [-20, 0, 0],
            "CM2",
            "dist2",
        ),
    ]:
        expected = cv2.projectPoints(
            camera_endpoints.reshape(-1, 1, 3),
            rvec,
            np.asarray(tvec, dtype=float),
            np.asarray(calibration[matrix], dtype=float),
            np.asarray(calibration[distortion], dtype=float),
        )[0].reshape(1, 2, 2)
        actual_columns = [
            f"x1_{camera_id}_original",
            f"y1_{camera_id}_original",
            f"x2_{camera_id}_original",
            f"y2_{camera_id}_original",
        ]
        actual = result[actual_columns].to_numpy().reshape(1, 2, 2)
        assert np.allclose(actual, expected)


def test_original_projection_can_be_computed_without_smoothing():
    data = pd.DataFrame(
        {
            "frame": [12],
            "color": ["blue"],
            "particle": [1],
            "x1": [0.0],
            "y1": [0.0],
            "z1": [100.0],
            "x2": [10.0],
            "y2": [0.0],
            "z2": [100.0],
        }
    )
    calibration = {
        "CM1": [[800, 0, 320], [0, 800, 240], [0, 0, 1]],
        "dist1": [0, 0, 0, 0, 0],
        "CM2": [[820, 0, 320], [0, 820, 240], [0, 0, 1]],
        "dist2": [0, 0, 0, 0, 0],
        "R": np.eye(3).tolist(),
        "T": [-20, 0, 0],
    }

    result = project_trajectories(
        data,
        calibration,
        {"rotation": np.eye(3), "translation": [0, 0, 0]},
        ("cam1", "cam2"),
    )

    assert "x1_cam1_original" in result
    assert np.isfinite(result["x1_cam1_original"].iloc[0])
