import os.path

import cv2
import scipy.io as sio
import numpy as np
from scipy.optimize import linear_sum_assignment
import json
import itertools


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


def load_calib_from_json(file_name: str) -> (dict, dict | None, dict | None):
    with open(file_name, "r") as f:
        all_calibs = json.load(f)
    if "stereoParams" in all_calibs.keys():
        cam1 = extract_cam_params(all_calibs["stereoParams"][
                                         "CameraParameters1"])
        cam2 = extract_cam_params(all_calibs["stereoParams"]["CameraParameters2"])
        stereo_params = extract_stereo_params(all_calibs["stereoParams"])
        stereo_params["img_size"] = all_calibs["stereoParams"][
            "CameraParameters2"]["ImageSize"]
        to_rectify = (
            cam1["matrix"], cam1["distortions"], cam2["matrix"],
            cam2["distortions"], stereo_params["img_size"], stereo_params["R"],
            stereo_params["T"]
        )
        r1, r2, p1, p2, _, _, _ = cv2.stereoRectify(*to_rectify)
        stereo_params.update({"R1": r1, "R2": r2, "P1": p1, "P2": p2})
        return stereo_params, cam1, cam2

    elif "transformations" in all_calibs.keys():
        return all_calibs["transformations"]
    return


def match_rods(cam1_folder, cam2_folder, output_folder, colors,
               frame_numbers, calibration_file=None,
               transformation_file=None,
               cam1_convention="{idx:05d}_{color:s}.mat",
               cam2_convention="{idx:05d}_{color:s}.mat"):
    """Ported from `match_rods_2020mix_gp12_cl1.m`.
    """
    if not cam1_convention.endswith(".mat"):
        cam1_convention += ".mat"
    if not cam2_convention.endswith(".mat"):
        cam2_convention += ".mat"
    if calibration_file is None:
        calibration_file = "/calibrations/gp12_calib_matlab.json"
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    stereo_params, cam1, cam2 = load_calib_from_json(calibration_file)
    transforms = load_calib_from_json(transformation_file)

    for color in colors:
        f_out = output_folder + f"data3d_{color}/"
        if not os.path.exists(f_out):
            os.mkdir(f_out)

        for idx in frame_numbers:
            # Load data
            cam1_file = cam1_folder + cam1_convention.format(idx=idx,
                                                             color=color)
            cam2_file = cam2_folder + cam2_convention.format(idx=idx,
                                                             color=color)
            rods_cam1 = sio.loadmat(cam1_file)["rod_data_links"][0]
            rods_cam2 = sio.loadmat(cam2_file)["rod_data_links"][0]
            # format of rods_camX: [rod, point, coordinate(x/y)]
            rods_cam1 = np.asarray([np.asarray([rod[0], rod[1]]) for rod in
                                rods_cam1]).squeeze()
            rods_cam2 = np.asarray([np.asarray([rod[0], rod[1]]) for rod in
                                rods_cam2]).squeeze()

            # Undistort points using the camera calibration
            tmp_points = cv2.undistortImagePoints(
                rods_cam1.reshape(2, -1), cam1["matrix"],
                cam1["distortions"]).squeeze()
            undist_cam1 = np.zeros(tmp_points.shape)
            tmp_points = np.concatenate([tmp_points[:, 0], tmp_points[:, 1]])
            for i in range(len(tmp_points)):
                undist_cam1[i // 2][i % 2] = tmp_points[i]
            undist_cam1 = undist_cam1.reshape((-1, 2, 2))

            tmp_points = cv2.undistortImagePoints(
                rods_cam2.reshape(2, -1), cam2["matrix"],
                cam2["distortions"]).squeeze()
            undist_cam2 = np.zeros(tmp_points.shape)
            tmp_points = np.concatenate([tmp_points[:, 0], tmp_points[:, 1]])
            for i in range(len(tmp_points)):
                undist_cam2[i // 2][i % 2] = tmp_points[i]
            undist_cam2 = undist_cam2.reshape((-1, 2, 2))

            # Triangulation of all possible point-pairs to 3D
            pairs_all = [list(itertools.product(p[0], p[1])) for p in
                         itertools.product(undist_cam1, undist_cam2)]
            pairs_all = np.reshape(pairs_all, (-1, 2, 2))
            # projection matrix generation taken from triangulate.m
            r1 = np.eye(3)
            t1 = np.expand_dims(np.array([0., 0., 0.]), 1)
            P1 = np.hstack([r1.transpose(), -r1.transpose().dot(t1)])
            P1_f = cam1["matrix"].dot(P1)

            r2 = stereo_params["R"]
            t2 = np.expand_dims(stereo_params["T"], 1)
            P2 = np.hstack([r2.transpose(), -r2.transpose().dot(t2)])
            P2_f = cam2["matrix"].dot(P2)
            # FIXME: currently yields points in the first cameras coordinate
            #  system (i.e. "gp3")
            p_triang = cv2.triangulatePoints(
                P1_f, P2_f,
                pairs_all[:, 0, :].squeeze().transpose(),
                pairs_all[:, 1, :].squeeze().transpose())
            p_triang = np.asarray([p[0:3]/p[3] for p in p_triang.transpose()])

            # Reprojection to the image plane for point matching
            # see: https://stackoverflow.com/questions/56500898/why-do-triangulated-points-not-project-back-to-same-image-points-in-opencv
            r1_vec_inv, _ = cv2.Rodrigues(r1.transpose())
            r2_vec_inv, _ = cv2.Rodrigues(r2.transpose())
            repr_cam1 = cv2.projectPoints(
                p_triang, r1_vec_inv, -t1.transpose(), cam1["matrix"],
                cam1["distortions"])[0].squeeze()
            repr_cam2 = cv2.projectPoints(
                p_triang, r2_vec_inv, -t2.transpose(), cam2["matrix"],
                cam2["distortions"])[0].squeeze()

            p_repr = np.stack([repr_cam1, repr_cam2], axis=2)
            p_repr = np.swapaxes(p_repr, 1, 2)
            repr_errs = np.mean(np.linalg.norm(p_repr, axis=2), axis=1)

            # Consolidate data
            # Caution: the data order is different form the MATLAB script
            #   ---> Matlab: (p11, p21), (p12, p21), (p11, p22), (p12, p22)
            #   ---> Python: (p11, p21), (p11, p22), (p12, p21), (p12, p22)
            # repr_errs desired shape:[block x err(p)] with
            #   block: re11, re12, re21, re22
            repr_errs = np.reshape(repr_errs, (-1, 4))
            costs = np.reshape(
                    np.min(
                        [np.sum(repr_errs[:, 0::3], axis=1),
                         np.sum(repr_errs[:, 1:3], axis=1)], axis=0),
                    (len(undist_cam1), len(undist_cam2))
                )

            cam1_ind, cam2_ind = linear_sum_assignment(costs)
            assignment_cost = costs[cam1_ind, cam2_ind].sum()

            point_choices = np.asarray(np.sum(repr_errs[:, 0::3], axis=1) <=
                                       np.sum(repr_errs[:, 1:3], axis=1))

            point_choices = point_choices.reshape((len(rods_cam1), len(rods_cam2)))
            p_triang = p_triang.reshape((len(rods_cam1), len(rods_cam2), 4, 3))
            out = np.zeros((len(cam1_ind), 2*3+3+1+4+4))
            idx_out = 0
            for m in range(len(cam1_ind)):
                k = cam1_ind[m]
                j = cam2_ind[m]
                # TODO: transformation to world coordinates of the 3D point
                # TODO: insert len of rod, midpoint of rod
                if point_choices[k, j]:
                    # use point matching of (p11,p21) and (p12,p22)
                    out[idx_out, 0:6] = p_triang[k, j, 0::3, :].flatten()
                    out[idx_out, 6:9] = p_triang[k, j, 0::3, :].sum(axis=0)/2
                    out[idx_out, 9] = np.linalg.norm(
                        np.diff(p_triang[k, j, 0::3, :], axis=0))
                    out[idx_out, 10:14] = rods_cam1[k, :].flatten()
                    out[idx_out, 14:] = rods_cam2[j, :].flatten()
                else:
                    # use point matching of (p11,p22) and (p12,p21)
                    out[idx_out, 0:6] = p_triang[k, j, 1:3, :].flatten()
                    out[idx_out, 6:9] = p_triang[k, j, 1:3, :].sum(axis=0) / 2
                    out[idx_out, 9] = np.linalg.norm(
                        np.diff(p_triang[k, j, 1:3, :], axis=0))
                    out[idx_out, 10:14] = rods_cam1[k, -1::-1].flatten()
                    out[idx_out, 14:] = rods_cam2[j, -1::-1].flatten()
                idx_out += 1

            file_out = f"{f_out}{idx:05d}.txt"
            np.savetxt(file_out, out, fmt="%.18f", delimiter=" ")
    return


def example_match_rods():
    """Shows the preparations and usage of `match_rods()`."""
    calibration_file = "/home/niemann/Documents/TrackingScripts/software" \
                       "/calib_matlab_09_2020/gp12_calib_matlab.json"
    transformation_file = "/home/niemann/Documents/TrackingScripts/software" \
                          "/calib_matlab_05_2017/transformations.json"
    colors = ["blue", "green", "red", "yellow", "brown"]
    base_folder = "/home/niemann/Documents/ParticleDetection/3Dreconstruction" \
                  "/testfiles"
    cam1_folder = base_folder + "/gp1/"
    cam1_convention = "FT2015_shot1_gp1_{idx:05d}_{color:s}.mat"
    cam2_folder = base_folder + "/gp2/"
    cam2_convention = "FT2015_shot1_gp2_{idx:05d}_{color:s}.mat"
    out_folder = base_folder + "/data3D/"

    start_frame = 732
    end_frame = 733
    frame_numbers = list(range(start_frame, end_frame+1))

    match_rods(cam1_folder, cam2_folder, out_folder, colors,
               frame_numbers, calibration_file, transformation_file,
               cam1_convention, cam2_convention)


if __name__ == "__main__":
    example_match_rods()
    # match_rods()


