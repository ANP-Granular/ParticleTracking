import os
import cv2
import numpy as np


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
        Boolean flag to draw corner detection results for camera one images.
        By default False.

    Returns
    -------
    Tuple :
        Return values of OpenCV's `stereoCalibrate()` function.
        [0] : reprojection error
        [1] : camera matrix 1
        [2] : distortion coefficients 1
        [3] : camera matrix 2
        [4] : distortion coefficients 2
        [5] : rotation matrix (R) -> with T can transform points in camera
              one's coordinate system to points in camear two's coordinate
              system
        [6] : translation vector (T)
        [7] : essential matrix (E)
        [8] : fundamental matrix (F)
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
