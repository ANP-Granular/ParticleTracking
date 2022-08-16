import json
from typing import List, Tuple
import numpy as np
import pandas as pd


def extract_stereo_params(calibration_params: dict) -> dict:
    """
    OpenCV:             Matlab:
    F                   FundamentalMatrix
    E                   EssentialMatrix
    T                   TranslationOfCamera2
    R                   inv(RotationOfCamera2)

    Matlab docs: (stereoParameters-rotationOfCamera2)
    Rotation of camera 2 relative to camera 1, specified as a 3-by-3 matrix.
    The rotationOfCamera2 and the translationOfCamera2 represent the relative
    rotation and translation between camera 1 and camera 2, respectively.
    They convert camera 2 coordinates back to camera 1 coordinates using:

        orientation1 = rotationOfCamera2 * orientation2
        location1 = translationOfCamera2 * orientation2 + location2

    where, orientation1 and location1 represent the absolute pose of camera 1,
    and orientation2 and location2 represent the absolute pose of camera 2.

    OpenCV docs:
    a) `stereoCalibrate()`:
    R	    Output rotation matrix. Together with the translation vector T, this
            matrix brings points given in the first camera's coordinate system
            to points in the second camera's coordinate system. In more
            technical terms, the tuple of R and T performs a change of basis
            from the first camera's coordinate system to the second camera's
            coordinate system. Due to its duality, this tuple is equivalent to
            the position of the first camera with respect to the second camera
            coordinate system.
    T	    Output translation vector, see description above.
    b) `stereoRectify()`:
    R	    Rotation matrix from the coordinate system of the first camera to
            the second camera, see stereoCalibrate.
    T	    Translation vector from the coordinate system of the first camera
            to the second camera, see stereoCalibrate.

    If one computes the poses of an object relative to the first camera and to
    the second camera, (R1, T1) and (R2, T2), respectively, for a stereo
    camera where the relative position and orientation between the two cameras
    are fixed, then those poses definitely relate to each other.
    This means, if the relative position and orientation (R, T) of the two
    cameras is known, it is possible to compute (R2, T2) when (R1, T1) is given.
    This is what the described function does. It computes (R, T) such that:
        R2=R*R1
        T2=R*T1+T.

    Therefore, one can compute the coordinate representation of a 3D point for
    the second camera's coordinate system when given the point's coordinate
    representation in the first camera's coordinate system:
        ⎡X2⎤            ⎡X1⎤
        ⎢Y2⎥ = ⎡R T⎤ *  ⎢Y1⎥
        ⎢Z2⎥   ⎣0 1⎦    ⎢Z1⎥
        ⎣ 1⎦            ⎣ 1⎦.

    See https://de.mathworks.com/help/vision/ref/stereoparameters.html and
    https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html for more info.
    """
    F = np.asarray(calibration_params["FundamentalMatrix"])
    E = np.asarray(calibration_params["EssentialMatrix"])
    R = np.linalg.inv(np.asarray(calibration_params["RotationOfCamera2"]))
    T = np.asarray(calibration_params["TranslationOfCamera2"])
    return {"F": F, "R": R, "T": T, "E": E}


def extract_cam_params(mat_params: dict):
    """
    OpenCV:             Matlab:
    [[fx, 0, cx],       [[fx, 0, 0],
    [0, fy, cy],        [s, fy, 0],
    [0, 0, 1]]          [cx, cy, 1]]

    OpenCV:
    (k1, k2, p1, p2[, k3[, k4, k5, k6[, s1, s2, s3, s4[, tau_x, tau_y]]]])
    -> 4, 5, 8, 12 or 14 elements

    - fx, fy -> focal lengths
    - cx, cy -> Principal point
    - k1, k2[, k3, k4, k5, k6] -> Radial (distortion) coefficients
    - p1, p2 -> Tangential distortion coefficients
    - s1, s2, s3, s4 -> prism distortion coefficients
    - τx,τy -> angular parameters (for image sensor tilts)

    see:
    https://de.mathworks.com/help/vision/ref/cameraintrinsics.html
    https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html
    """
    # mat_matrix = camera_parameters["IntrinsicMatrix"]
    fx, fy = mat_params["FocalLength"]
    cx, cy = mat_params["PrincipalPoint"]

    # adjust for Matlab start index (1,1), see
    # https://ch.mathworks.com/help/vision/ref/stereoparameterstoopencv.html)
    cx = cx - 1
    cy = cy - 1

    cam_matrix = np.asarray(
        [[fx, 0, cx],  # mtx/A/K in OpenCV
         [0, fy, cy],
         [0, 0, 1]])
    ks = mat_params["RadialDistortion"]
    ps = mat_params["TangentialDistortion"]
    dist_coeffs = np.asarray([*ks[0:2], *ps, *ks[3:]])

    return {
        "matrix": cam_matrix,
        "distortions": dist_coeffs,
    }


def load_calib_from_json(file_name: str) -> \
        Tuple[dict, dict | None, dict | None]:
    with open(file_name, "r") as f:
        all_calibs = json.load(f)
    if "stereoParams" in all_calibs.keys():
        cam1 = extract_cam_params(all_calibs["stereoParams"][
                                         "CameraParameters1"])
        cam2 = extract_cam_params(all_calibs["stereoParams"]["CameraParameters2"])
        stereo_params = extract_stereo_params(all_calibs["stereoParams"])
        stereo_params["img_size"] = all_calibs["stereoParams"][
            "CameraParameters2"]["ImageSize"]
        return stereo_params, cam1, cam2

    elif "transformations" in all_calibs.keys():
        return all_calibs["transformations"]
    return


def load_positions_from_txt(base_file_name: str, columns: List[str],
                            frames: List[int], expected_particles: int =
                            None) -> pd.DataFrame:
    """Loads the rod data from point matching and adds a frame column."""
    if "particle" not in columns:
        columns.append("particle")
    data = pd.DataFrame(columns=columns)
    for f in frames:
        data_raw = pd.read_csv(base_file_name.format(f), sep=" ", header=None,
                               names=columns)
        if expected_particles:
            # Fill missing rods with "empty" rows
            missing = expected_particles - len(data_raw)
            empty_rods = pd.DataFrame(
                missing * [
                    [4.5, 5, 5, 5.5, 5, 5, 5, 5, 5, 1.0, 0, 0, 0, 0, 0, 0,
                     0, 0, f, 0]], columns=columns
            )
            data_raw = pd.concat([data_raw, empty_rods], ignore_index=True)
        data_raw["particle"] = range(0, len(data_raw))
        data_raw["frame"] = f
        data = pd.concat([data, data_raw], ignore_index=True)
    return data
