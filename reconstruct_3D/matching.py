import os.path
import itertools
import pathlib

import cv2
import scipy.io as sio
import pandas as pd
import numpy as np
from scipy.optimize import linear_sum_assignment
import matplotlib.pyplot as plt

import reconstruct_3D.data_loading as dl
from reconstruct_3D.result_visualizations import matching_results


def project_to_world(points, transforms: dict):
    rotx = np.asarray(transforms["M_rotate_x"])
    roty = np.asarray(transforms["M_rotate_y"])
    rotz = np.asarray(transforms["M_rotate_z"])
    tw1 = np.asarray(transforms["M_trans"])
    tw2 = np.asarray(transforms["M_trans2"])
    old_shape = points.shape
    points = np.reshape(points, (-1, 3))
    points = np.append(points, np.ones((len(points),1)), axis=1)
    for i in range(len(points)):
        points[i,:] = tw2.dot(rotx.dot(rotz.dot(roty.dot(
            tw1.dot(points[i,:])))))
    points = points[:,0:3].T
    return np.reshape(points, old_shape)


def project_from_world(points, transforms: dict):
    rotx = np.asarray(transforms["M_rotate_x"])
    roty = np.asarray(transforms["M_rotate_y"])
    rotz = np.asarray(transforms["M_rotate_z"])
    tw1 = np.asarray(transforms["M_trans"])
    tw2 = np.asarray(transforms["M_trans2"])
    old_shape = points.shape
    points = np.reshape(points, (-1, 3))
    points = np.append(points, np.ones((len(points),1)), axis=1)
    for i in range(len(points)):
        points[i,:] = tw1.dot(roty.dot(rotz.dot(rotx.dot(
            tw2.dot(points[i,:])))))
    points = points[:,0:3].T
    return np.reshape(points, old_shape)


def match_matlab_simple(cam1_folder, cam2_folder, output_folder, colors, 
                      frame_numbers, calibration_file=None,
                      transformation_file=None,
                      cam1_convention="{idx:05d}_{color:s}.mat",
                      cam2_convention="{idx:05d}_{color:s}.mat"):
    """Ported Matlab script from `match_rods_2020mix_gp12_cl1.m`.
    This function takes the same input file format and outputs the same file 
    formats as the previous implementation in MATLAB. Use this function for a 
    consistent behaviour to previous data processings.

    Parameters
    ----------
    See `match_matlab_complex(...)`

    Returns
    -------
    See `match_matlab_complex(...)`

    Note
    ----
    This function currently saves the 3D points in the first camera's 
    coordinate system, NOT the world/box coordinate system.
    """

    if not cam1_convention.endswith(".mat"):
        cam1_convention += ".mat"
    if not cam2_convention.endswith(".mat"):
        cam2_convention += ".mat"
    if calibration_file is None:
        this_dir = pathlib.Path(__file__).parent.resolve()
        calibration_file = this_dir.joinpath(
            "calibration_data/Matlab/gp12.json")
    if transformation_file is None:
        this_dir = pathlib.Path(__file__).parent.resolve()
        transformation_file = this_dir.joinpath(
            "calibration_data/Matlab/world_transformation.json")
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    # Load Matlab exported calibrations
    calibration = dl.load_camera_calibration(str(calibration_file))
    transforms = dl.load_calib_from_json(transformation_file)

    # Derive projection matrices from the calibration
    r1 = np.eye(3)
    t1 = np.expand_dims(np.array([0., 0., 0.]), 1)
    P1 = np.vstack((r1.T, t1.T)) @ calibration["CM1"].T
    P1 = P1.T

    r2 = calibration["R"]
    t2 = calibration["T"]
    P2 = np.vstack((r2.T, t2.T)) @ calibration["CM2"].T
    P2 = P2.T

    # Setup the triangulation function with the loaded calibration
    def triangulate(point1, point2, sampson=False):
        orig1 = point1
        orig2 = point2
        point1 = cv2.undistortImagePoints(point1, calibration["CM1"], 
                                        calibration["dist1"]).squeeze()
        point2 = cv2.undistortImagePoints(point2, calibration["CM2"], 
                                        calibration["dist2"]).squeeze()
        if sampson:
            # Use Sampson distance as an additional correction
            Fn=calibration["F"]/np.linalg.norm(calibration["F"])
            r = np.append(point2.T, 1) @ Fn @ np.append(point1, 1)
            fd0 = Fn[0:2, 0:2].T @ point2 + Fn[2, 0:2].T
            fd1 = Fn[0:2, 0:2].T @ point1 + Fn[2, 0:2].T
            g = fd0.T @ fd0 + fd1.T @ fd1
            e = r/g
            point1 = point1 - e*fd0
            point2 = point2 - e*fd1

        wp = cv2.triangulatePoints(P1, P2, point1, point2)
        wp = wp[0:3]/wp[3]
        rp1 = cv2.projectPoints(wp, r1, t1, calibration["CM1"], 
                                distCoeffs=calibration["dist1"])[0]
        rp2 = cv2.projectPoints(wp, r2, t2, calibration["CM2"], 
                                distCoeffs=calibration["dist2"])[0]
        rep_errs = [np.linalg.norm(orig1 - rp1), np.linalg.norm(orig2 - rp2)]
        return wp, rep_errs

    all_repr_errs = []
    all_rod_lengths = []
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

            lengths = np.zeros((len(rods_cam1), len(rods_cam2), 2))
            rep_errs = np.zeros((len(rods_cam1), len(rods_cam2), 2, 2, 2))
            for i in range(len(rods_cam1)):
                for j in range(len(rods_cam2)):
                    c1_p1 = rods_cam1[i, 0]
                    c1_p2 = rods_cam1[i, 1]
                    c2_p1 = rods_cam2[j, 0]
                    c2_p2 = rods_cam2[j, 1]
                    wp1_1, rep_e1 = triangulate(c1_p1, c2_p1)
                    wp1_2, rep_e2 = triangulate(c1_p2, c2_p2)
                    wp2_1, rep_e3 = triangulate(c1_p2, c2_p1)
                    wp2_2, rep_e4 = triangulate(c1_p1, c2_p2)
                    rep_errs[i, j] = np.asarray([[rep_e1, rep_e2], [rep_e3, rep_e4]])
                    lengths[i, j, 0] = np.linalg.norm(wp1_1 - wp1_2)
                    lengths[i, j, 1] = np.linalg.norm(wp2_1 - wp2_2)

            cam1_ind, cam2_ind = linear_sum_assignment(np.min(np.sum(rep_errs, (-2, -1)),2))
            summed_errs = np.min(np.sum(rep_errs, (3,4)),2)
            all_repr_errs.append(summed_errs[cam1_ind, cam2_ind])
            out = np.zeros((len(cam1_ind), 2*3+3+1+4+4))
            for i, j in zip(cam1_ind, cam2_ind):
                c1_p1 = rods_cam1[i, 0]
                c1_p2 = rods_cam1[i, 1]
                c2_p1 = rods_cam2[j, 0]
                c2_p2 = rods_cam2[j, 1]
                wp1_1, rep_e1 = triangulate(c1_p1, c2_p1)
                wp1_2, rep_e2 = triangulate(c1_p2, c2_p2)
                wp2_1, rep_e3 = triangulate(c1_p2, c2_p1)
                wp2_2, rep_e4 = triangulate(c1_p1, c2_p2)
                rep_errs[i, j] = np.asarray([[rep_e1, rep_e2], [rep_e3, rep_e4]])
                lengths[i, j, 0] = np.linalg.norm(wp1_1 - wp1_2)
                lengths[i, j, 1] = np.linalg.norm(wp2_1 - wp2_2)
                if rep_e1+rep_e2 < rep_e3+rep_e4:
                    out[i, 0:6] = np.concatenate((wp1_1, wp1_2), axis=0).squeeze()
                    out[i, 6:9] = ((wp1_1 + wp1_2) / 2).squeeze()
                    out[i, 9] = lengths[i, j, 0]
                    out[i, 10:14] = rods_cam1[i].flatten()
                    out[i, 14:] = rods_cam2[j].flatten()
                else:
                    out[i, 0:6] = np.concatenate((wp2_1, wp2_2), axis=0).squeeze()
                    out[i, 6:9] = ((wp2_1 + wp2_2) / 2).squeeze()
                    out[i, 9] = lengths[i, j, 1]
                    out[i, 10:14] = rods_cam1[i].flatten()
                    out[i, 14:] = rods_cam2[j, ::-1].flatten()
            all_rod_lengths.append(out[:, 9])
            file_out = f"{f_out}{idx:05d}.txt"
            np.savetxt(file_out, out, fmt="%.18f", delimiter=" ")
    return all_repr_errs, all_rod_lengths


def match_matlab_complex(cam1_folder, cam2_folder, output_folder, colors,
               frame_numbers, calibration_file=None,
               transformation_file=None,
               cam1_convention="{idx:05d}_{color:s}.mat",
               cam2_convention="{idx:05d}_{color:s}.mat"):
    """_summary_

    Parameters
    ----------
    cam1_folder : str
        Folder with rod data of the first camera.
    cam2_folder : str
        Folder with rod data of the second camera
    output_folder : str
        Folder to write the output to. The parent folder of this must exist 
        already.
    colors : List[str]
        Names of the colors present in the dataset.
    frame_numbers : Iterable[int]
        An iterable of frame numbers present in the data.
    calibration_file : str, optional
        Path to a *.json file with stereocalibration data for the cameras which
        produced the images for the rod position data. 
        By default the calibration constructed with Matlab for GP1 and GP2 is 
        used.
    transformation_file : str, optional
        Path to a *.json file with transformation matrices expressing the 
        transformation from the first camera's coordinate system to the 
        world/box coordinate system. 
        By default the transformation constructed with Matlab is used.
    cam1_convention : str, optional
        Naming convention for the first camera's position data files defined 
        by a formattable string, that accepts some of the following 
        variables: {idx, color}.
        By default "{idx:05d}_{color:s}.mat"
    cam2_convention : str, optional
        Naming convention for the second camera's position data files defined 
        by a formattable string, that accepts some of the following 
        variables: {idx, color}. 
        By default "{idx:05d}_{color:s}.mat"

    Returns
    -------
    np.ndarray, np.ndarray
        Reprojection errors, rod lengths of the matched rod endpoints.
    
    Note
    ----
    This function currently saves the 3D points in the first camera's 
    coordinate system, NOT the world/box coordinate system.
    """
    if not cam1_convention.endswith(".mat"):
        cam1_convention += ".mat"
    if not cam2_convention.endswith(".mat"):
        cam2_convention += ".mat"
    if calibration_file is None:
        this_dir = pathlib.Path(__file__).parent.resolve()
        calibration_file = this_dir.joinpath(
            "calibration_data/Matlab/gp12.json")
    if transformation_file is None:
        this_dir = pathlib.Path(__file__).parent.resolve()
        transformation_file = this_dir.joinpath(
            "calibration_data/Matlab/world_transformation.json")
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    calibration = dl.load_camera_calibration(str(calibration_file))
    transforms = dl.load_calib_from_json(str(transformation_file))

    # Derive projection matrices from the calibration
    r1 = np.eye(3)
    t1 = np.expand_dims(np.array([0., 0., 0.]), 1)
    P1 = np.vstack((r1.T, t1.T)) @ calibration["CM1"].T
    P1 = P1.T

    r2 = calibration["R"]
    t2 = calibration["T"]
    P2 = np.vstack((r2.T, t2.T)) @ calibration["CM2"].T
    P2 = P2.T

    all_repr_errs = []
    all_rod_lengths = []
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
                rods_cam1.reshape(2, -1), calibration["CM1"],
                calibration["dist1"]).squeeze()
            undist_cam1 = np.zeros(tmp_points.shape)
            tmp_points = np.concatenate([tmp_points[:, 0], tmp_points[:, 1]])
            for i in range(len(tmp_points)):
                undist_cam1[i // 2][i % 2] = tmp_points[i]
            undist_cam1 = undist_cam1.reshape((-1, 2, 2))

            tmp_points = cv2.undistortImagePoints(
                rods_cam2.reshape(2, -1), calibration["CM2"],
                calibration["dist2"]).squeeze()
            undist_cam2 = np.zeros(tmp_points.shape)
            tmp_points = np.concatenate([tmp_points[:, 0], tmp_points[:, 1]])
            for i in range(len(tmp_points)):
                undist_cam2[i // 2][i % 2] = tmp_points[i]
            undist_cam2 = undist_cam2.reshape((-1, 2, 2))

            # Triangulation of all possible point-pairs to 3D
            pairs_all = [list(itertools.product(p[0], p[1])) for p in
                         itertools.product(undist_cam1, undist_cam2)]
            pairs_all = np.reshape(pairs_all, (-1, 2, 2))

            pairs_original = [list(itertools.product(p[0], p[1])) for p in
                         itertools.product(rods_cam1, rods_cam2)]
            pairs_original = np.reshape(pairs_original, (-1, 2, 2))
            
            # FIXME: currently yields points in the first cameras coordinate
            #  system (i.e. "gp3")
            # TODO: transformation to "world"-coordinates
            p_triang = cv2.triangulatePoints(
                P1, P2,
                pairs_all[:, 0, :].squeeze().transpose(),
                pairs_all[:, 1, :].squeeze().transpose())
            p_triang = np.asarray([p[0:3]/p[3] for p in p_triang.transpose()])

            # Reprojection to the image plane for point matching
            repr_cam1 = cv2.projectPoints(
                p_triang, r1, t1, calibration["CM1"],
                calibration["dist1"])[0].squeeze()
            repr_cam2 = cv2.projectPoints(
                p_triang, r2, t2, calibration["CM2"],
                calibration["dist2"])[0].squeeze()
           
            repr_cam1 = pairs_original[:, 0, :] - repr_cam1
            repr_cam2 = pairs_original[:, 1, :] - repr_cam2
            p_repr = np.stack([repr_cam1, repr_cam2], axis=2) # [combo, err_point, cam]
            p_repr = np.swapaxes(p_repr, 1, 2)                # [combo, cam, err_point]
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
            assignment_cost = costs[cam1_ind, cam2_ind]
            all_repr_errs.append(assignment_cost)

            point_choices = np.asarray(np.sum(repr_errs[:, 0::3], axis=1) <=
                                       np.sum(repr_errs[:, 1:3], axis=1))

            point_choices = point_choices.reshape((len(rods_cam1), len(rods_cam2)))
            p_triang = p_triang.reshape((len(rods_cam1), len(rods_cam2), 4, 3))

            # TODO: transformation to world coordinates of the 3D point
            # p_triang = project_to_world(p_triang, transforms)
            out = np.zeros((len(cam1_ind), 2*3+3+1+4+4))
            idx_out = 0     # TODO: remove the use of idx_out
            for m in range(len(cam1_ind)):
                k = cam1_ind[m]
                j = cam2_ind[m]
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

                idx_out += 1 # TODO: remove the use of idx_out
            all_rod_lengths.append(out[:, 9])

            file_out = f"{f_out}{idx:05d}.txt"
            np.savetxt(file_out, out, fmt="%.18f", delimiter=" ")
    return np.array(all_repr_errs), np.array(all_rod_lengths)


def match_csv_complex(input_folder, output_folder, colors, cam1_name="gp1", 
                      cam2_name="gp2", frame_numbers=None, 
                      calibration_file=None, transformation_file=None):
    """Matches and triangulates rods from *.csv data files.

    Parameters
    ----------
    input_folder : str
        Folder containing the *.csv files for all colors given in `colors`s.
    output_folder : str
        See `match_matlab_complex()`.
    colors : Iterable[str]
        See `match_matlab_complex()`.
    cam1_name : str, optional
        First camera's identifier in the given dataset.
        By default "gp1".
    cam2_name : str, optional
        Second camera's identifier in the given dataset.
        By default "gp2".
    frame_numbers : Iterable[int], optional
        See `match_matlab_complex()`.
    calibration_file : str, optional
        See `match_matlab_complex()`.
    transformation_file : _type_, optional
        See `match_matlab_complex()`.

    Returns
    -------
    np.ndarray, np.ndarray
        Reprojection errors, rod lengths of the matched rod endpoints.
    
    Note
    ----
    This function currently saves the 3D points in the first camera's 
    coordinate system, NOT the world/box coordinate system.
    """
    if calibration_file is None:
        this_dir = pathlib.Path(__file__).parent.resolve()
        calibration_file = this_dir.joinpath(
            "calibration_data/Matlab/gp12.json")
    if transformation_file is None:
        this_dir = pathlib.Path(__file__).parent.resolve()
        transformation_file = this_dir.joinpath(
            "calibration_data/Matlab/world_transformation.json")
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    calibration = dl.load_camera_calibration(str(calibration_file))
    transforms = dl.load_calib_from_json(str(transformation_file))

    # Derive projection matrices from the calibration
    r1 = np.eye(3)
    t1 = np.expand_dims(np.array([0., 0., 0.]), 1)
    P1 = np.vstack((r1.T, t1.T)) @ calibration["CM1"].T
    P1 = P1.T

    r2 = calibration["R"]
    t2 = calibration["T"]
    P2 = np.vstack((r2.T, t2.T)) @ calibration["CM2"].T
    P2 = P2.T

    all_repr_errs = []
    all_rod_lengths = []
    for color in colors:
        f_in = input_folder + f"/rods_df_{color}.csv"
        data = pd.read_csv(f_in, sep=",", index_col=0)
        df_out = pd.DataFrame()
        for idx in frame_numbers:
            # Load data
            cols_cam1 = [f'x1_{cam1_name}', f'y1_{cam1_name}', 
                        f'x2_{cam1_name}', f'y2_{cam1_name}']
            cols_cam2 = [f'x1_{cam2_name}', f'y1_{cam2_name}',
                        f'x2_{cam2_name}', f'y2_{cam2_name}']
            _data_cam1 = data.loc[data.frame==idx, cols_cam1]
            _data_cam2 = data.loc[data.frame==idx, cols_cam2]
             # remove rows with NaNs or only 0s
            _data_cam1.dropna(how="all", inplace=True)
            _data_cam2.dropna(how="all", inplace=True)
            _data_cam1 = _data_cam1.loc[(_data_cam1!=0).any(axis=1)]
            _data_cam2 = _data_cam2.loc[(_data_cam2!=0).any(axis=1)]
            if len(_data_cam1.index)==0 or len(_data_cam2.index)==0:
                # no rod data available for matching
                continue

            # format of rods_camX: [rod, point, coordinate(x/y)]
            rods_cam1 = _data_cam1.to_numpy().reshape(-1, 2, 2)
            rods_cam2 = _data_cam2.to_numpy().reshape(-1, 2, 2)

            # Undistort points using the camera calibration
            tmp_points = cv2.undistortImagePoints(
                rods_cam1.reshape(2, -1), calibration["CM1"],
                calibration["dist1"]).squeeze()
            undist_cam1 = np.zeros(tmp_points.shape)
            tmp_points = np.concatenate([tmp_points[:, 0], tmp_points[:, 1]])
            for i in range(len(tmp_points)):
                undist_cam1[i // 2][i % 2] = tmp_points[i]
            undist_cam1 = undist_cam1.reshape((-1, 2, 2))

            tmp_points = cv2.undistortImagePoints(
                rods_cam2.reshape(2, -1), calibration["CM2"],
                calibration["dist2"]).squeeze()
            undist_cam2 = np.zeros(tmp_points.shape)
            tmp_points = np.concatenate([tmp_points[:, 0], tmp_points[:, 1]])
            for i in range(len(tmp_points)):
                undist_cam2[i // 2][i % 2] = tmp_points[i]
            undist_cam2 = undist_cam2.reshape((-1, 2, 2))

            # Triangulation of all possible point-pairs to 3D
            pairs_all = [list(itertools.product(p[0], p[1])) for p in
                         itertools.product(undist_cam1, undist_cam2)]
            pairs_all = np.reshape(pairs_all, (-1, 2, 2))

            pairs_original = [list(itertools.product(p[0], p[1])) for p in
                         itertools.product(rods_cam1, rods_cam2)]
            pairs_original = np.reshape(pairs_original, (-1, 2, 2))
            
            # FIXME: currently yields points in the first cameras coordinate
            #  system (i.e. "gp3")
            # TODO: transformation to "world"-coordinates
            p_triang = cv2.triangulatePoints(
                P1, P2,
                pairs_all[:, 0, :].squeeze().transpose(),
                pairs_all[:, 1, :].squeeze().transpose())
            p_triang = np.asarray([p[0:3]/p[3] for p in p_triang.transpose()])

            # Reprojection to the image plane for point matching
            repr_cam1 = cv2.projectPoints(
                p_triang, r1, t1, calibration["CM1"],
                calibration["dist1"])[0].squeeze()
            repr_cam2 = cv2.projectPoints(
                p_triang, r2, t2, calibration["CM2"],
                calibration["dist2"])[0].squeeze()
           
            repr_cam1 = pairs_original[:, 0, :] - repr_cam1
            repr_cam2 = pairs_original[:, 1, :] - repr_cam2
            p_repr = np.stack([repr_cam1, repr_cam2], axis=2) # [combo, err_point, cam]
            p_repr = np.swapaxes(p_repr, 1, 2)                # [combo, cam, err_point]
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
            assignment_cost = costs[cam1_ind, cam2_ind]
            all_repr_errs.append(assignment_cost)

            point_choices = np.asarray(np.sum(repr_errs[:, 0::3], axis=1) <=
                                       np.sum(repr_errs[:, 1:3], axis=1))

            point_choices = point_choices.reshape((len(rods_cam1), len(rods_cam2)))
            p_triang = p_triang.reshape((len(rods_cam1), len(rods_cam2), 4, 3))

            # TODO: transformation to world coordinates of the 3D point
            # p_triang = project_to_world(p_triang, transforms)
            out = np.zeros((len(cam1_ind), 2*3+3+1+4+4))
            for i1 in range(len(cam1_ind)):
                i2 = cam2_ind[i1]
                if point_choices[i1, i2]:
                    # use point matching of (p11,p21) and (p12,p22)
                    out[i1, 0:6] = p_triang[i1, i2, 0::3, :].flatten()
                    out[i1, 6:9] = p_triang[i1, i2, 0::3, :].sum(axis=0)/2
                    out[i1, 9] = np.linalg.norm(
                        np.diff(p_triang[i1, i2, 0::3, :], axis=0))
                    out[i1, 10:14] = rods_cam1[i1, :].flatten()
                    out[i1, 14:] = rods_cam2[i2, :].flatten()
                else:
                    # use point matching of (p11,p22) and (p12,p21)
                    out[i1, 0:6] = p_triang[i1, i2, 1:3, :].flatten()
                    out[i1, 6:9] = p_triang[i1, i2, 1:3, :].sum(axis=0) / 2
                    out[i1, 9] = np.linalg.norm(
                        np.diff(p_triang[i1, i2, 1:3, :], axis=0))
                    out[i1, 10:14] = rods_cam1[i1, -1::-1].flatten()
                    out[i1, 14:] = rods_cam2[i2, -1::-1].flatten()
            all_rod_lengths.append(out[:, 9])

            # Data preparation for saving as *.csv
            tmp_df = pd.DataFrame(out, columns=data.columns[:out.shape[1]])
            tmp_df["frame"] = idx
            tmp_df["color"] = color
            seen_cols = [col for col in data.columns if "seen" in col]
            tmp_df[seen_cols] = 1
            df_out = pd.concat([df_out, tmp_df])
        df_out.reset_index(drop=True, inplace=True)
        df_out.to_csv(os.path.join(output_folder, f"rods_df_{color}.csv"), sep=",")
    
    return np.array(all_repr_errs), np.array(all_rod_lengths)

def plot_rods(file: str, rods, color:str, save=False):
    base_folder = "./testfiles"
    img_file = base_folder + "/FT2015_shot1_gp1_00732.jpg"
    # img_file = base_folder + "/" + os.path.splitext(file)[0].split(f"_{color}")[0] + ".jpg"
    img = cv2.imread(img_file)
    width, height = img.shape[1], img.shape[0]
    fig = plt.figure(frameon=False)
    dpi = fig.get_dpi()
    fig.set_size_inches(
        (width + 1e-2) / dpi,
        (height + 1e-2) / dpi,
    )
    ax1 = fig.add_axes([0, 0, 1, 1])
    ax1.imshow(img)
    ax1.axis("off")
    for r in rods:
        ax1.plot(r[0:3:2], r[1:4:2], color=color)
    plt.show()


def example_match_rods():
    """Shows the preparations and usage of `match_matlab_simple()`."""
    debug = True

    calibration_file = "./calibration_data/Matlab/gp12.json"
    transformation_file = "./calibration_data/Matlab/" \
                          "world_transformation.json"
    colors = ["blue", "green", "red", "yellow", "brown"]
    base_folder = "./testfiles"
    cam1_folder = base_folder + "/gp1/"
    cam1_convention = "FT2015_shot1_gp1_{idx:05d}_{color:s}.mat"
    cam2_folder = base_folder + "/gp2/"
    cam2_convention = "FT2015_shot1_gp2_{idx:05d}_{color:s}.mat"
    out_folder = base_folder + "/data3D/"

    start_frame = 732
    end_frame = 736
    frame_numbers = list(range(start_frame, end_frame+1))
    if debug:
        calibration_file = "./calibration_data/Matlab/gp12.json"
        colors = ["blue",]
        base_folder = "./debug_files"
        cam1_folder = base_folder + "/gp3/"
        cam1_convention = "{idx:05d}_{color:s}.mat"
        cam2_folder = base_folder + "/gp4/"
        cam2_convention = "{idx:05d}_{color:s}.mat"
        out_folder = base_folder + "/data3D/"
        start_frame = 100
        end_frame = 904
        frame_numbers = list(range(start_frame, end_frame+1))

    if debug:
        from time import perf_counter
        start = perf_counter()
        errs, lens = match_matlab_simple(cam1_folder, cam2_folder, out_folder, colors,
                                frame_numbers, calibration_file,
                                transformation_file, cam1_convention,
                                cam2_convention)
        end_simple = perf_counter()
        errs, lens = match_matlab_complex(cam1_folder, cam2_folder, out_folder, colors,
                                frame_numbers, calibration_file,
                                transformation_file, cam1_convention,
                                cam2_convention)
        end_complex = perf_counter()
        print(f"Durations\nSimple: {end_simple-start} s"
              f"\tComplex: {end_complex-end_simple} s")
        
        err_vis = np.array([])
        len_vis = np.array([])
        for err, l in zip(errs, lens):
            err_vis = np.concatenate([err_vis, err.flatten()])
            len_vis = np.concatenate([len_vis, l.flatten()])
        matching_results(err_vis, len_vis)

    else:
        errs, lens = match_matlab_simple(cam1_folder, cam2_folder, out_folder, colors,
                                frame_numbers, calibration_file,
                                transformation_file, cam1_convention,
                                cam2_convention)
        err_vis = np.array([])
        len_vis = np.array([])
        for err, l in zip(errs, lens):
            err_vis = np.concatenate([err_vis, err.flatten()])
            len_vis = np.concatenate([len_vis, l.flatten()])
        matching_results(err_vis, len_vis)


def extract_mat_from_txt():
    import scipy.io as sio
    col_names = ['x1_r', 'y1_r', 'z1_r', 'x2_r', 'y2_r', 'z2_r', 
                 'x1', 'y1', 'z1', 'x2', 'y2', 'z2', 'x', 'y', 'z', 'l',
                 'x1_gp3', 'y1_gp3', 'x2_gp3', 'y2_gp3', 'x1_gp4', 'y1_gp4', 
                 'x2_gp4', 'y2_gp4', 'particle', 'frame']
    dbg_data_format = "./debug_files/data3d_blueT/{:05d}.txt"
    rods_exp = 12
    frames = list(range(100, 905))
    dbg_data = dl.load_positions_from_txt(dbg_data_format, col_names, frames)
    raw_3d = dbg_data[['x1_r', 'y1_r', 'z1_r', 'x2_r', 'y2_r', 'z2_r']].to_numpy()
    rods_cam1 = dbg_data[['x1_gp3', 'y1_gp3', 'x2_gp3', 'y2_gp3']].to_numpy()
    rods_cam2 = dbg_data[['x1_gp4', 'y1_gp4', 'x2_gp4', 'y2_gp4']].to_numpy()
    rods_cam1 = rods_cam1.reshape((-1, rods_exp, 4))
    rods_cam2 = rods_cam2.reshape((-1, rods_exp, 4))
    dt = np.dtype(
        [('Point1', np.float, (2,)), ('Point2', np.float, (2,))])
    for r_c1, r_c2, fr in zip(rods_cam1, rods_cam2, frames):
        arr = np.zeros((rods_exp,), dtype=dt)
        arr[:]['Point1'] = r_c1[:, 0:2]
        arr[:]['Point2'] = r_c1[:, 2:]
        sio.savemat(f"./debug_files/gp3/{fr:05d}_blue.mat", 
                    {'rod_data_links': arr})
        arr2 = np.zeros((rods_exp,), dtype=dt)
        arr2[:]['Point1'] = r_c2[:, 0:2]
        arr2[:]['Point2'] = r_c2[:, 2:]
        sio.savemat(f"./debug_files/gp4/{fr:05d}_blue.mat", 
                    {'rod_data_links': arr2})


if __name__ == "__main__":
    example_match_rods()
