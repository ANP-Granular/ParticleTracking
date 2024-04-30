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

"""
Collection of (mostly deprecated) functions to load stereo camera calibration
data and rod position data.

**Authors:**    Adrian Niemann (adrian.niemann@ovgu.de)\n
**Date:**       02.11.2022

"""
import json
import warnings
from pathlib import Path
from typing import Iterable, List, Tuple, Union

import cv2
import numpy as np
import pandas as pd
import torch
from scipy.spatial.transform import Rotation as R


def extract_stereo_params(calibration_params: dict) -> dict:
    """Load stereo camera calibrations from a direct MATLAB ``*.json`` export.

    Loads stereo camera calibrations, that have been exported to ``*.json``
    directly from MATLAB and therefore still adhere to MATLAB's naming
    convention. These are then transferred to the naming convention used by
    this package (OpenCV's naming convention).

    Parameters
    ----------
    calibration_params : dict
        A MATLAB stereo camera calibration loaded from a ``*.json`` file.

    Returns
    -------
    dict
        Stereo camera calibration matrices to be used by this package.
        Has the keys: ``"F"``, ``"R"``, ``"T"``, ``"E"``

    Notes
    -----
    Nomenclature correspondences::

        OpenCV:             Matlab:
        F                   FundamentalMatrix
        E                   EssentialMatrix
        T                   TranslationOfCamera2
        R                   inv(RotationOfCamera2)

    Matlab docs: (stereoParameters-rotationOfCamera2)\n
    Rotation of camera 2 relative to camera 1, specified as a 3-by-3 matrix.
    The ``rotationOfCamera2`` and the ``translationOfCamera2`` represent the
    relative rotation and translation between camera 1 and camera 2,
    respectively.
    They convert camera 2 coordinates back to camera 1 coordinates using::

            orientation1 = rotationOfCamera2 * orientation2
            location1 = translationOfCamera2 * orientation2 + location2

    where, ``orientation1`` and ``location1`` represent the absolute pose of
    camera 1, and ``orientation2 and ``location2`` represent the absolute pose
    of camera 2.

    OpenCV docs:

    a) ``stereoCalibrate()``:
        R
            Output rotation matrix. Together with the translation vector T,
            this matrix brings points given in the first camera's coordinate
            system to points in the second camera's coordinate system. In more
            technical terms, the tuple of R and T performs a change of basis
            from the first camera's coordinate system to the second camera's
            coordinate system. Due to its duality, this tuple is equivalent to
            the position of the first camera with respect to the second camera
            coordinate system.
        T
            Output translation vector, see description above.

    b) ``stereoRectify()``:
        R
            Rotation matrix from the coordinate system of the first camera to
            the second camera, see stereoCalibrate.
        T
            Translation vector from the coordinate system of the first camera
            to the second camera, see stereoCalibrate.

    If one computes the poses of an object relative to the first camera and to
    the second camera, ``(R1, T1)`` and ``(R2, T2)``, respectively, for a
    stereo camera where the relative position and orientation between the two
    cameras are fixed, then those poses definitely relate to each other.
    This means, if the relative position and orientation ``(R, T)`` of the two
    cameras is known, it is possible to compute ``(R2, T2)`` when ``(R1, T1)``
    is given. This is what the described function does.
    It computes ``(R, T)`` such that::

            R2=R * R1
            T2=R * T1 + T.

    Therefore, one can compute the coordinate representation of a 3D point for
    the second camera's coordinate system when given the point's coordinate
    representation in the first camera's coordinate system::

        ⎡X2⎤            ⎡X1⎤
        ⎢Y2⎥ = ⎡R T⎤ *  ⎢Y1⎥
        ⎢Z2⎥   ⎣0 1⎦    ⎢Z1⎥
        ⎣ 1⎦            ⎣ 1⎦.

    See https://de.mathworks.com/help/vision/ref/stereoparameters.html and
    https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html for more info.

    """
    warnings.warn(
        "Avoid using this function. Instead convert the calibration"
        "to the currently used json-format.",
        DeprecationWarning,
    )
    F = np.asarray(calibration_params["FundamentalMatrix"])
    E = np.asarray(calibration_params["EssentialMatrix"])
    R = np.linalg.inv(np.asarray(calibration_params["RotationOfCamera2"]))
    T = np.asarray(calibration_params["TranslationOfCamera2"])
    return {"F": F, "R": R, "T": T, "E": E}


def extract_cam_params(mat_params: dict) -> dict:
    """Load camera calibrations from a direct MATLAB ``*.json`` export.

    Loads camera calibrations, that have been exported to ``*.json`` directly
    from MATLAB and therefore still adhere to MATLAB's naming and data
    convention.These are then transferred to the data(/naming) convention used
    by this package (OpenCV's data convention).

    Parameters
    ----------
    mat_params : dict
        A MATLAB camera calibration loaded from a ``*.json`` file.

    Returns
    -------
    dict
        Camera calibration matrices and distortion coefficients to be used by
        this package.
        Has the keys: ``"matrix"``, ``"distortions"``

    Notes
    -----
    Camera matrix correspondences::

        OpenCV:             Matlab:
        [[fx,  0, cx],       [[fx,  0, 0],
         [ 0, fy, cy],        [ s, fy, 0],
         [ 0,  0,  1]]        [cx, cy, 1]]

    OpenCV distortion coefficients::

        (k1, k2, p1, p2[, k3[, k4, k5, k6[, s1, s2, s3, s4[, tau_x, tau_y]]]])

    -> 4, 5, 8, 12, or 14 elements

    - ``fx, fy`` -> focal lengths
    - ``cx, cy`` -> Principal point
    - ``k1, k2[, k3, k4, k5, k6]`` -> Radial (distortion) coefficients
    - ``p1, p2`` -> Tangential distortion coefficients
    - ``s1, s2, s3, s4`` -> prism distortion coefficients
    - ``τx, τy`` -> angular parameters (for image sensor tilts)

    see:
    https://de.mathworks.com/help/vision/ref/cameraintrinsics.html
    https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html
    """
    warnings.warn(
        "Avoid using this function. Instead convert the calibration"
        "to the currently used json-format.",
        DeprecationWarning,
    )
    # mat_matrix = camera_parameters["IntrinsicMatrix"]
    fx, fy = mat_params["FocalLength"]
    cx, cy = mat_params["PrincipalPoint"]

    # adjust for Matlab start index (1,1), see
    # https://ch.mathworks.com/help/vision/ref/stereoparameterstoopencv.html)
    cx = cx - 1
    cy = cy - 1

    cam_matrix = np.asarray(
        [[fx, 0, cx], [0, fy, cy], [0, 0, 1]]  # mtx/A/K in OpenCV
    )
    ks = mat_params["RadialDistortion"]
    ps = mat_params["TangentialDistortion"]
    dist_coeffs = np.asarray([*ks[0:2], *ps, *ks[3:]])

    return {
        "matrix": cam_matrix,
        "distortions": dist_coeffs,
    }


def load_calib_from_json(
    file_name: str,
) -> Union[Tuple[dict, dict], Tuple[None, dict], None]:
    """Attempts to load camera calibrations or transformations to
    *world*/*experiment* coordinates saved in the MATLAB format.

    Parameters
    ----------
    filename : str

    Returns
    -------
    None | dict | tuple

    .. warning::
        .. deprecated:: 0.4.0
            Please convert your old configurations compatible with
            :func:`load_world_transformation` and
            :func:`load_camera_calibration`.
    """
    with open(file_name, "r") as f:
        all_calibs = json.load(f)
    if "stereoParams" in all_calibs.keys():
        warnings.warn(
            "Don't use this function anymore to load camera "
            "calibrations. Use `load_camera_calibration` instead.",
            DeprecationWarning,
        )
        cam1 = extract_cam_params(
            all_calibs["stereoParams"]["CameraParameters1"]
        )
        cam2 = extract_cam_params(
            all_calibs["stereoParams"]["CameraParameters2"]
        )
        stereo_params = extract_stereo_params(all_calibs["stereoParams"])
        stereo_params["img_size"] = all_calibs["stereoParams"][
            "CameraParameters2"
        ]["ImageSize"]
        return stereo_params, cam1, cam2

    elif "transformations" in all_calibs.keys():
        warnings.warn(
            "Don't use this function anymore to transformations "
            "calibrations. Use `load_world_transformation` instead.",
            DeprecationWarning,
        )
        return all_calibs["transformations"]
    return


def load_world_transformation(file_name: str) -> dict:
    """Loads a transformation to world/experiment coordinates from
    ``*.json`` files.

    It attempts to load a transformation from camera 1 coordinates to
    world/experiment coordinates. There are two structures this function can
    load and distinguish between.

    - a legacy version leading to a structure::

        loaded["transformations"]["M_rotate_x"]
                                 ["M_rotate_y"]
                                 ["M_rotate_z"]
                                 ["M_trans2"]
                                 ["M_trans]

    - a new version that only has one rotation matrix and one translation
      vector::

        loaded["rotation"]
              ["translation"]

    The first structure is then transformed into the second one.

    Parameters
    ----------
    file_name : str
        Path to the ``*.json`` file containing the transformation data.

    Returns
    -------
    dict
        Loaded transformation data in the format::

            loaded["rotation"] = ndarray((3, 3))
                  ["translation"] = ndarray((3,))
    """
    with open(file_name, "r") as f:
        f_trafo = json.load(f)
    if "transformations" in f_trafo.keys():
        transform = f_trafo["transformations"]
        rotx = R.from_matrix(np.asarray(transform["M_rotate_x"])[0:3, 0:3])
        roty = R.from_matrix(np.asarray(transform["M_rotate_y"])[0:3, 0:3])
        rotz = R.from_matrix(np.asarray(transform["M_rotate_z"])[0:3, 0:3])
        tw1 = np.asarray(transform["M_trans"])[0:3, 3]
        tw2 = np.asarray(transform["M_trans2"])[0:3, 3]
        rotation = rotz * roty * rotx
        translation = rotation.apply(tw1) + tw2
        return {"rotation": rotation.as_matrix(), "translation": translation}
    elif set(f_trafo.keys()) == {"rotation", "translation"}:
        return {
            "rotation": np.array(f_trafo["rotation"]),
            "translation": np.array(f_trafo["translation"]),
        }
    else:
        raise ValueError(
            f"Incompatible structure of the given file: " f"{file_name}"
        )


def load_camera_calibration(file_name: str) -> dict:
    """Loads camera calibration data from ``*.json`` files.

    Loads calibration data from a stereo camera calibration, in the format
    given in ``./calibration_data``.

    Parameters
    ----------
    file_name : str
        Path to the ``*.json`` file containing the calibration data.

    Returns
    -------
    dict
        Loaded calibration data.
    """
    with open(file_name, "r") as f:
        f_calib = json.load(f)
    calibration = {}
    for key, val in f_calib.items():
        if not (type(val) is list):
            continue
        calibration[key] = np.asarray(val)
    return calibration


def load_positions_from_txt(
    base_file_name: str,
    columns: List[str],
    frames: Iterable[int],
    expected_particles: int = None,
) -> pd.DataFrame:
    """Loads the rod data from point matching and adds a frame column."""
    warnings.warn(
        "Don't use the *.txt data format anymore but switch to the"
        " new *.csv format",
        DeprecationWarning,
    )
    if "particle" not in columns:
        columns.append("particle")
    data = pd.DataFrame(columns=columns)
    for f in frames:
        data_raw = pd.read_csv(
            base_file_name.format(f), sep=" ", header=None, names=columns
        )
        if expected_particles:
            # Fill missing rods with "empty" rows
            missing = expected_particles - len(data_raw)
            empty_rods = pd.DataFrame(
                missing
                * [
                    [
                        4.5,
                        5,
                        5,
                        5.5,
                        5,
                        5,
                        5,
                        5,
                        5,
                        1.0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        f,
                        0,
                    ]
                ],
                columns=columns,
            )
            data_raw = pd.concat([data_raw, empty_rods], ignore_index=True)
        data_raw["particle"] = range(0, len(data_raw))
        data_raw["frame"] = f
        data = pd.concat([data, data_raw], ignore_index=True)
    return data


def read_image(img_path: Path) -> torch.Tensor:
    """Loads an image for detection with an exported model.

    Parameters
    ----------
    img_path : Path

    Returns
    -------
    Tensor
    """
    img = cv2.imread(str(img_path.resolve()))  # loads in 'BGR' mode
    img = torch.from_numpy(np.ascontiguousarray(img.transpose(2, 0, 1)))
    return img


def extract_3d_data(df_data: pd.DataFrame) -> np.ndarray:
    """Extract the 3D data from a rod position ``DataFrame`` ready for
    plotting.

    Parameters
    ----------
    df_data : pd.DataFrame
        Rod position data, with at least the following columns:\n
        ``"particle"``, ``"frame"``, ``"x1"``, ``"y1"``, ``"z1"``, ``"x2"``,
        ``"y2"``, ``"z2"``

    Returns
    -------
    np.ndarray
        Dimensions: [frame, particle, 3, 2]
    """
    no_frames = len(df_data.frame.unique())
    no_particles = len(df_data.particle.unique())
    data3d = np.empty((no_frames, no_particles, 3, 2))
    data3d.fill(np.nan)
    for idx_f, f in enumerate(df_data.frame.unique()):
        frame_data = df_data.loc[df_data.frame == f]
        idx_p = frame_data["particle"].to_numpy()
        data3d[idx_f, idx_p, :, 0] = frame_data[["x1", "y1", "z1"]].to_numpy()
        data3d[idx_f, idx_p, :, 1] = frame_data[["x2", "y2", "z2"]].to_numpy()
    return data3d
