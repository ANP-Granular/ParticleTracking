"""Offline smoothing of reconstructed rigid-rod trajectories."""

import numpy as np
import pandas as pd
from ParticleDetection.reconstruct_3D.calibrate_cameras import reproject_points


def project_trajectories(
    data: pd.DataFrame,
    calibration: dict,
    transformation: dict,
    camera_ids: tuple,
) -> pd.DataFrame:
    """Project existing 3D endpoints into both calibrated camera views."""
    if data.empty:
        return pd.DataFrame()
    if len(camera_ids) != 2:
        raise ValueError("Projection requires exactly two camera IDs.")

    rotation, translation = _world_transform(transformation)
    point_columns = ["x1", "y1", "z1", "x2", "y2", "z2"]
    endpoints = data[point_columns].to_numpy(dtype=float).reshape(-1, 2, 3)
    valid = np.isfinite(endpoints).all(axis=(1, 2))
    if valid.any():
        projections = _project_to_cameras(
            endpoints[valid],
            calibration,
            rotation,
            translation,
            camera_ids,
        )
    else:
        projections = [np.empty((0, 2, 2)) for _ in camera_ids]

    result = data.copy()
    for camera_id, projected in zip(camera_ids, projections):
        for endpoint_idx in range(2):
            for coord_idx, coord_name in enumerate("xy"):
                values = np.full(len(data), np.nan)
                values[valid] = projected[:, endpoint_idx, coord_idx]
                result[
                    f"{coord_name}{endpoint_idx + 1}_{camera_id}_original"
                ] = values
    return result


def smooth_trajectories(
    data: pd.DataFrame,
    expected_lengths: dict,
    calibration: dict,
    transformation: dict,
    camera_ids: tuple,
    translation_process_noise: float = 0.2,
    orientation_process_noise: float = 0.002,
    length_tolerance: float = 1.5,
    reprojection_tolerance: float = 15.0,
) -> pd.DataFrame:
    """Smooth rod centers and axes and reproject the result into both views.

    Input rows are not modified. The result contains smoothed world endpoints
    and their distortion-aware 2D projections, with columns suffixed by
    ``_smooth``.
    """
    if data.empty:
        return pd.DataFrame()
    if len(camera_ids) != 2:
        raise ValueError("Smoothing requires exactly two camera IDs.")

    rotation, translation = _world_transform(transformation)
    output = []
    for (color, particle), group in data.groupby(
        ["color", "particle"], sort=False
    ):
        group = group.sort_values("frame")
        point_columns = ["x1", "y1", "z1", "x2", "y2", "z2"]
        endpoints = (
            group[point_columns].to_numpy(dtype=float).reshape(-1, 2, 3)
        )
        valid = np.isfinite(endpoints).all(axis=(1, 2))
        valid &= np.linalg.norm(endpoints[:, 1] - endpoints[:, 0], axis=1) > 0
        group = group.iloc[np.flatnonzero(valid)]
        endpoints = endpoints[valid]
        if not len(group):
            continue

        observed_lengths = np.linalg.norm(
            endpoints[:, 1] - endpoints[:, 0], axis=1
        )
        nominal_length = float(
            expected_lengths.get(
                str(color).lower(), np.nanmedian(observed_lengths)
            )
        )
        centers = endpoints.mean(axis=1)
        axes = endpoints[:, 1] - endpoints[:, 0]
        axes /= observed_lengths[:, None]
        for idx in range(1, len(axes)):
            if np.dot(axes[idx - 1], axes[idx]) < 0:
                axes[idx] *= -1

        quality = _observation_quality(
            group,
            endpoints,
            observed_lengths,
            nominal_length,
            calibration,
            rotation,
            translation,
            camera_ids,
            length_tolerance,
            reprojection_tolerance,
        )
        frames = group["frame"].to_numpy(dtype=float)
        smooth_centers = _rts_constant_velocity(
            frames,
            centers,
            quality,
            translation_process_noise,
            measurement_variance=1.0,
        )
        smooth_axes = _rts_constant_velocity(
            frames,
            axes,
            quality,
            orientation_process_noise,
            measurement_variance=0.01,
        )
        axis_norms = np.linalg.norm(smooth_axes, axis=1)
        bad_axes = ~np.isfinite(axis_norms) | (axis_norms < 1e-8)
        smooth_axes[bad_axes] = axes[bad_axes]
        smooth_axes /= np.linalg.norm(smooth_axes, axis=1)[:, None]

        smoothed_endpoints = np.stack(
            [
                smooth_centers - 0.5 * nominal_length * smooth_axes,
                smooth_centers + 0.5 * nominal_length * smooth_axes,
            ],
            axis=1,
        )
        projections = _project_to_cameras(
            smoothed_endpoints,
            calibration,
            rotation,
            translation,
            camera_ids,
        )
        raw_projections = _project_to_cameras(
            endpoints, calibration, rotation, translation, camera_ids
        )
        for row_idx, (_, row) in enumerate(group.iterrows()):
            result = row.to_dict()
            for endpoint_idx in range(2):
                for coord_idx, coord_name in enumerate("xyz"):
                    result[f"{coord_name}{endpoint_idx + 1}_smooth"] = (
                        smoothed_endpoints[row_idx, endpoint_idx, coord_idx]
                    )
            result["l_smooth"] = nominal_length
            result["smoothing_quality"] = quality[row_idx]
            for camera_id, projected, raw_projected in zip(
                camera_ids, projections, raw_projections
            ):
                for endpoint_idx in range(2):
                    result[f"x{endpoint_idx + 1}_{camera_id}_original"] = (
                        raw_projected[row_idx, endpoint_idx, 0]
                    )
                    result[f"y{endpoint_idx + 1}_{camera_id}_original"] = (
                        raw_projected[row_idx, endpoint_idx, 1]
                    )
                    result[f"x{endpoint_idx + 1}_{camera_id}_smooth"] = (
                        projected[row_idx, endpoint_idx, 0]
                    )
                    result[f"y{endpoint_idx + 1}_{camera_id}_smooth"] = (
                        projected[row_idx, endpoint_idx, 1]
                    )
            output.append(result)
    return pd.DataFrame(output)


def _world_transform(transformation):
    if "rotation" in transformation:
        return (
            np.asarray(transformation["rotation"], dtype=float),
            np.asarray(transformation["translation"], dtype=float),
        )
    transforms = transformation.get("transformations", transformation)
    rotate_x = np.asarray(transforms["M_rotate_x"], dtype=float)[:3, :3]
    rotate_y = np.asarray(transforms["M_rotate_y"], dtype=float)[:3, :3]
    rotate_z = np.asarray(transforms["M_rotate_z"], dtype=float)[:3, :3]
    rotation = rotate_z @ rotate_y @ rotate_x
    first_translation = np.asarray(transforms["M_trans"], dtype=float)[:3, 3]
    second_translation = np.asarray(transforms["M_trans2"], dtype=float)[:3, 3]
    translation = rotation @ first_translation + second_translation
    return rotation, translation


def _project_to_cameras(
    endpoints, calibration, rotation, translation, camera_ids
):
    world_points = endpoints.reshape(-1, 3)
    camera_calibration = dict(calibration)
    for key in ("CM1", "CM2", "R", "T", "dist1", "dist2"):
        camera_calibration[key] = np.asarray(calibration[key], dtype=float)
    transformation = {"rotation": rotation, "translation": translation}
    projected_camera_one, projected_camera_two = reproject_points(
        world_points, camera_calibration, transformation
    )
    return [
        projected_camera_one.reshape(-1, 2, 2),
        projected_camera_two.reshape(-1, 2, 2),
    ]


def _observation_quality(
    group,
    endpoints,
    observed_lengths,
    nominal_length,
    calibration,
    rotation,
    translation,
    camera_ids,
    length_tolerance,
    reprojection_tolerance,
):
    quality = np.ones(len(group), dtype=float)
    if length_tolerance > 0:
        length_error = np.abs(observed_lengths - nominal_length)
        quality += (length_error / length_tolerance) ** 2

    residuals = _reprojection_residuals(
        group, endpoints, calibration, rotation, translation, camera_ids
    )
    camera_scores = []
    for camera_residual in residuals.T:
        finite = np.isfinite(camera_residual)
        if not finite.any():
            continue
        baseline = np.median(camera_residual[finite])
        excess = np.maximum(camera_residual - baseline, 0)
        if reprojection_tolerance > 0:
            camera_scores.append(excess / reprojection_tolerance)
    if camera_scores:
        scores = np.stack(camera_scores, axis=1)
        scores[~np.isfinite(scores)] = 0
        quality += np.mean(scores**2, axis=1)
    return np.clip(quality, 1.0, 1000.0)


def _reprojection_residuals(
    group, endpoints, calibration, rotation, translation, camera_ids
):
    predictions = _project_to_cameras(
        endpoints, calibration, rotation, translation, camera_ids
    )
    residuals = np.full((len(group), len(camera_ids)), np.nan)
    for camera_idx, camera_id in enumerate(camera_ids):
        columns = [
            f"x1_{camera_id}",
            f"y1_{camera_id}",
            f"x2_{camera_id}",
            f"y2_{camera_id}",
        ]
        if not set(columns).issubset(group.columns):
            continue
        observed = group[columns].to_numpy(dtype=float).reshape(-1, 2, 2)
        valid = np.isfinite(observed).all(axis=(1, 2))
        valid &= (observed >= 0).all(axis=(1, 2))
        seen_column = f"seen_{camera_id}"
        if seen_column in group:
            seen = pd.to_numeric(group[seen_column], errors="coerce")
            valid &= seen.fillna(0).to_numpy(dtype=bool)
        direct = np.linalg.norm(predictions[camera_idx] - observed, axis=2)
        swapped = np.linalg.norm(
            predictions[camera_idx][:, ::-1] - observed, axis=2
        )
        residuals[valid, camera_idx] = np.minimum(
            direct[valid].mean(axis=1), swapped[valid].mean(axis=1)
        )
    return residuals


def _rts_constant_velocity(
    frames, observations, quality, process_noise, measurement_variance
):
    """Apply a robust constant-velocity Kalman filter and RTS pass."""
    count, dimensions = observations.shape
    if count == 1:
        return observations.copy()

    identity = np.eye(dimensions)
    observation_matrix = np.concatenate(
        [identity, np.zeros_like(identity)], axis=1
    )
    state = np.concatenate([observations[0], np.zeros(dimensions)])
    covariance = np.diag(
        np.concatenate(
            [
                np.full(dimensions, measurement_variance * quality[0]),
                np.full(dimensions, 100.0),
            ]
        )
    )
    filtered_states = [state.copy()]
    filtered_covariances = [covariance.copy()]
    predicted_states = [state.copy()]
    predicted_covariances = [covariance.copy()]
    transitions = [None]

    for idx in range(1, count):
        dt = max(float(frames[idx] - frames[idx - 1]), 1.0)
        transition = np.block(
            [
                [identity, dt * identity],
                [np.zeros_like(identity), identity],
            ]
        )
        process = process_noise * np.block(
            [
                [dt**3 / 3 * identity, dt**2 / 2 * identity],
                [dt**2 / 2 * identity, dt * identity],
            ]
        )
        state_prediction = transition @ state
        covariance_prediction = (
            transition @ covariance @ transition.T + process
        )
        observation_noise = measurement_variance * quality[idx] * identity
        innovation = observations[idx] - observation_matrix @ state_prediction
        innovation_covariance = (
            observation_matrix @ covariance_prediction @ observation_matrix.T
            + observation_noise
        )
        distance = np.sqrt(
            max(
                float(
                    innovation
                    @ np.linalg.solve(innovation_covariance, innovation)
                ),
                0.0,
            )
        )
        observation_noise *= max(1.0, distance / 4.0)
        innovation_covariance = (
            observation_matrix @ covariance_prediction @ observation_matrix.T
            + observation_noise
        )
        gain = np.linalg.solve(
            innovation_covariance,
            observation_matrix @ covariance_prediction,
        ).T
        state = state_prediction + gain @ innovation
        covariance = (np.eye(2 * dimensions) - gain @ observation_matrix) @ (
            covariance_prediction
        )
        covariance = 0.5 * (covariance + covariance.T)

        predicted_states.append(state_prediction)
        predicted_covariances.append(covariance_prediction)
        transitions.append(transition)
        filtered_states.append(state.copy())
        filtered_covariances.append(covariance.copy())

    smoothed = np.asarray(filtered_states)
    for idx in range(count - 2, -1, -1):
        gain = np.linalg.solve(
            predicted_covariances[idx + 1],
            transitions[idx + 1] @ filtered_covariances[idx],
        ).T
        smoothed[idx] += gain @ (smoothed[idx + 1] - predicted_states[idx + 1])
    return smoothed[:, :dimensions]
