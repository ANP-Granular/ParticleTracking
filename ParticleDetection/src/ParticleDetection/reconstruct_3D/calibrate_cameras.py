import os
from typing import Tuple
import cv2
import numpy as np
from scipy.spatial.transform import Rotation as R


def stereo_calibrate(cam1_path: str, cam2_path: str, visualize: bool = False):
    """Calibrate a stereo camera system.

    Using images of a checkerboard with 4-by-5 inner corners to calibrate a
    stereo camera system.

    Parameters
    ----------
    cam1_path : str
        Absolute path to a folder containing only the calibration images from
        camera one.
    cam2_path : str
        Absolute path to a folder containing only the calibration images from
        camera two.
    visualize : bool, optional
        Boolean flag to draw corner detection results for camera one images.\n
        By default ``False``.

    Returns
    -------
    Tuple
        Return values of OpenCV's ``stereoCalibrate()`` function.\n
        [0] : reprojection error\n
        [1] : camera matrix 1\n
        [2] : distortion coefficients 1\n
        [3] : camera matrix 2\n
        [4] : distortion coefficients 2\n
        [5] : rotation matrix (R) -> with T can transform points in camera
        one's coordinate system to points in camear two's coordinate system\n
        [6] : translation vector (T)\n
        [7] : essential matrix (E)\n
        [8] : fundamental matrix (F)\n
    """
    # Setup
    corner_distance = 5     # mm
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
                1000, 1e-6)     # Termination criteria: (type, count, eps)
    obj_p = np.zeros((4 * 5, 3), np.float32)
    obj_p[:, :2] = np.mgrid[0:4, 0:5].T.reshape(-1, 2)
    obj_p = corner_distance * obj_p

    # Camera calibration
    obj_points = []
    img_points = []
    obj_points2 = []
    img_points2 = []
    f_images = os.listdir(cam1_path)
    f_images2 = os.listdir(cam2_path)
    for f_img, f_img2 in zip(f_images, f_images2):
        if not os.path.isfile(os.path.join(cam1_path, f_img)):
            continue
        if not os.path.isfile(os.path.join(cam2_path, f_img)):
            continue
        # Camera 1
        img = cv2.imread(os.path.join(cam1_path, f_img))
        img_grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ret, corners = cv2.findChessboardCorners(img_grey, (4, 5), None)

        img2 = cv2.imread(os.path.join(cam2_path, f_img2))
        img_grey2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        ret2, corners2 = cv2.findChessboardCorners(img_grey2, (4, 5), None)

        if ret == True and ret2 == True:                    # noqa: E712
            obj_points.append(obj_p)
            corners_fine = cv2.cornerSubPix(img_grey, corners, (11, 11),
                                            (-1, -1), criteria)
            img_points.append(corners_fine)

            obj_points2.append(obj_p)
            corners2_fine = cv2.cornerSubPix(img_grey2, corners2, (11, 11),
                                             (-1, -1), criteria)
            img_points2.append(corners2_fine)

            if visualize:
                cv2.drawChessboardCorners(img, (4, 5), corners_fine, ret)
                cv2.imshow('img', img)
                cv2.waitKey(1500)

    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(obj_points, img_points,
                                                       img_grey.shape[::-1],
                                                       None, None)
    ret2, mtx2, dist2, rvecs2, tvecs2 = cv2.calibrateCamera(
        obj_points2, img_points2, img_grey2.shape[::-1], None, None)

    # Stereo calibration
    stereocalibration_flags = cv2.CALIB_FIX_INTRINSIC
    ret, CM1, dist1, CM2, dist2, R, T, E, F = cv2.stereoCalibrate(
        obj_points, img_points, img_points2, mtx, dist,
        mtx2, dist2, img_grey.shape[::-1], criteria=criteria,
        flags=stereocalibration_flags)

    return ret, CM1, dist1, CM2, dist2, R, T, E, F


def project_points(p_cam1: np.ndarray, p_cam2: np.ndarray, calibration: dict,
                   transforms: dict | None):
    """Project points from a stereocamera system to 3D coordinates.

    Parameters
    ----------
    p_cam1 : ndarray
        Point coordinates on camera 1.
        Shape: ``(2, n)``
    p_cam2 : ndarray
        Point coordinates on camera 2.
        Shape: ``(2, n)``
    calibration : dict
        Stereocamera calibration parameters with the required fields:
        ``"CM1"``: camera matrix of cam1\n
        ``"R"``: rotation matrix between cam1 & cam2\n
        ``"T"``: translation vector between cam1 & cam2\n
        ``"CM2"``: camera matrix of cam2
    transforms : dict | None
        Coordinate system transformation matrices from camera 1 coordinates to
        *world*/*experiment* coordinates.
        **Must contain the following fields:**\n
        ``"M_rotate_x"``, ``"M_rotate_y"``, ``"M_rotate_z"``, ``"M_trans"``,
        ``"M_trans2"``\n
        Transformation of 3D coordinates to *world*/*experiment* coordinates is
        omitted if ``transforms`` is ``None``.

    Returns
    -------
    ndarray
        3D point coordinates in either the *world*/*experiment* coordinates or
        camera 1 coordinates, depending on whether ``transforms`` is given.
        Shape: ``(3, n)``
    """
    # Derive projection matrices from the calibration
    r1 = np.eye(3)
    t1 = np.expand_dims(np.array([0., 0., 0.]), 1)
    P1 = np.vstack((r1.T, t1.T)) @ calibration["CM1"].T
    P1 = P1.T

    r2 = calibration["R"]
    t2 = calibration["T"]
    P2 = np.vstack((r2.T, t2.T)) @ calibration["CM2"].T
    P2 = P2.T

    p3d = cv2.triangulatePoints(P1, P2, p_cam1, p_cam2)
    p3d = p3d[0:3] / p3d[3]

    if transforms is not None:
        rotx = R.from_matrix(np.asarray(transforms["M_rotate_x"])[0:3, 0:3])
        roty = R.from_matrix(np.asarray(transforms["M_rotate_y"])[0:3, 0:3])
        rotz = R.from_matrix(np.asarray(transforms["M_rotate_z"])[0:3, 0:3])
        tw1 = np.asarray(transforms["M_trans"])[0:3, 3]
        tw2 = np.asarray(transforms["M_trans2"])[0:3, 3]
        rot = rotz * roty * rotx
        p3d = rot.apply(p3d + tw1) + tw2

    return p3d


def reproject_points(points: np.ndarray, calibration: dict,
                     transforms: dict | None) -> Tuple[np.ndarray, np.ndarray]:
    """Project 3D coordinates to 2D stereocamera coordinates.

    Parameters
    ----------
    points : np.ndarray
        3D point coordinates in either the *world*/*experiment* coordinates or
        camera 1 coordinates, depending on whether ``transforms`` is given.
        Shape: ``(3, n)`` or ``(n, 3)``
    calibration : dict
        Stereocamera calibration parameters with the required fields:\n
        ``"CM1"``: camera matrix of cam1\n
        ``"R"``: rotation matrix between cam1 & cam2\n
        ``"T"``: translation vector between cam1 & cam2\n
        ``"CM2"``: camera matrix of cam2
    transforms : dict | None
        Coordinate system transformation matrices from camera 1 coordinates to
        *world*/*experiment* coordinates.
        **Must contain the following fields:**\n
        ``"M_rotate_x"``, ``"M_rotate_y"``, ``"M_rotate_z"``, ``"M_trans"``,
        ``"M_trans2"``\n
        Transformation of 3D coordinates from *world*/*experiment* coordinates
        is omitted if ``transforms`` is ``None``.

    Returns
    -------
    Tuple[ndarray, ndarray]
        2D image plane coordinates of camera 1 & 2.
    """
    # Derive projection matrices from the calibration
    r1 = np.eye(3)
    t1 = np.expand_dims(np.array([0., 0., 0.]), 1)
    P1 = np.vstack((r1.T, t1.T)) @ calibration["CM1"].T
    P1 = P1.T

    r2 = calibration["R"]
    t2 = calibration["T"]
    P2 = np.vstack((r2.T, t2.T)) @ calibration["CM2"].T
    P2 = P2.T

    if transforms is not None:
        rotx = R.from_matrix(np.asarray(transforms["M_rotate_x"])[0:3, 0:3])
        roty = R.from_matrix(np.asarray(transforms["M_rotate_y"])[0:3, 0:3])
        rotz = R.from_matrix(np.asarray(transforms["M_rotate_z"])[0:3, 0:3])
        tw1 = np.asarray(transforms["M_trans"])[0:3, 3]
        tw2 = np.asarray(transforms["M_trans2"])[0:3, 3]
        rot_inv = (rotz * roty * rotx).inv()
        points = rot_inv.apply(points - tw2) - tw1

    repr_cam1 = cv2.projectPoints(
        points, r1, t1, calibration["CM1"],
        calibration["dist1"])[0].squeeze()
    repr_cam2 = cv2.projectPoints(
        points, r2, t2, calibration["CM2"],
        calibration["dist2"])[0].squeeze()

    return repr_cam1, repr_cam2
