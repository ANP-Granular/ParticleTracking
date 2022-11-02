"""
Function(s) to reconstruct 3D rod endpoints from images of a stereocamera
system by solving an n-partite matching problem between the rods within one
frame and the respective previous frame.

Authors:    Adrian Niemann (adrian.niemann@ovgu.de)
Date:       31.10.2022

"""
import os
import copy
import pathlib
import warnings
import itertools
from typing import Iterable, Tuple

import cv2
import pulp
import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation as R
from scipy.optimize import linear_sum_assignment
from tqdm import tqdm

import ParticleDetection.utils.data_loading as dl


# BUG: the minimization does not work yet
def npartite_matching(weights: np.ndarray, maximize: bool = True,
                      solver: pulp.LpSolver = pulp.PULP_CBC_CMD(msg=False))\
        -> Tuple[np.ndarray]:
    """Solve an n-partite matching problem.

    The weights given represent the cost of assigning the entities associated
    with the respective indices together.

    Parameters
    ----------
    weights : np.ndarray
        A n-dimensional matrix where each entry is the cost associated with
        choosing the combination of indeces. The number of dimensions represent
        the number of groups and the size of each dimension the number of
        members in this group.
    maximize : bool, optional
        By default True.
    solver : pulp.LpSolver, optional
        A solver for the matching problem.
        By default pulp.PULP_CBC_CMD(msg=False).

    Returns
    -------
    Tuple[np.ndarray]
        The length of the tuple is equal to the number of dimensions of
        `weights`. Each element of the tuple has a maximum size of the smallest
        dimension of `weights`. The elements of the arrays represent the index
        of the groups paired member.

    Examples
    --------
    The following weights are defined: weights.shape -> [12, 12, 4]
    This means three groups must be associated to each other, with four
    paths, because the smallest dimension has size 4.
    weights[0, 5, 2] then represents the cost of pairing element 0 of group
    0 with element 5 of group 1 and element 2 of group 2.

    >>> npartite_matching(np.random((12, 12, 4)))
    (array([2, 9, 4, 11]), array([6, 9, 1, 0]), array([2, 1, 0, 3]))

    Note
    ----
    Adapted from:
    https://stackoverflow.com/questions/60940781/solving-the-assignment-problem-for-3-groups-instead-of-2
    """
    if not maximize:
        warnings.warn("Minimization is currently not fully supported."
                      "Results might be incorrect.")

    # get dimensions from weights array
    dims = weights.shape

    # prepare auxiliary variables
    grid = [range(dim) for dim in dims]
    varx = itertools.product(*grid)

    # initialize variables
    xxx = pulp.LpVariable.dicts('xxx', varx, cat=pulp.LpBinary)

    # initialize optimization problem
    if maximize:
        problem = pulp.LpProblem('RodMatching_max', pulp.LpMaximize)
    else:
        problem = pulp.LpProblem('RodMatching_min', pulp.LpMinimize)
    # set objective
    # sum_ijk... c_ijk... x_ijk...
    problem += pulp.lpSum([weights[iii] * xxx[iii] for iii in xxx])

    # set constraints
    # sum_i x_ijk... <= 1
    # sum_j x_ijk... <= 1
    # sum...
    for idi, dim in enumerate(dims):
        for idv in range(dim):
            gric = copy.deepcopy(grid)
            gric[idi] = [idv]
            vary = itertools.product(*gric)
            problem += pulp.lpSum(xxx[iii] for iii in vary) <= 1

    problem.solve(solver)

    # write binary variables to array
    rex = weights.copy() * 0
    for iii in xxx:
        rex[iii] = xxx[iii].value()

    # find optimal matching = path and path weights
    whr = np.where(rex)
    return whr


def create_weights_0(p_3D: np.ndarray, p_3D_prev: np.ndarray) -> np.ndarray:
    """Create weights from 3D-displacements for matching rods between frames.

    Creates a weight matrix for matching rods between frames, using the rod
    endpoint displacement between frames as the cost of an assignment.

    Parameters
    ----------
    p_3D : np.ndarray
        Shape must be in (rod_ids(cam1), rod_ids(cam2), 4, 3)
        Dimension explanations:
        (rod_id(cam1), rod_id(cam2), endpoint-combination, 3D-coordinates)
    p_3D_prev : np.ndarray
        Shape must be in (rod_ids, 2, 3).
        Dimension explanations:
        (rod_id, end-point, 3D-coordinates)

    Returns
    -------
    np.ndarray
        Weights in the shape of (rod_id, rod_ids(cam1), rod_ids(cam2))
    """
    rods1, rods2 = p_3D.shape[0:2]
    rods_prev = p_3D_prev.shape[0]
    p_3D = np.concatenate((p_3D, p_3D), axis=2)
    p_3D = p_3D.reshape((rods1, rods2, -1, 6))

    p_3D_prev = np.concatenate((p_3D_prev, p_3D_prev), axis=1)
    p_3D_prev = np.concatenate((p_3D_prev, np.flip(p_3D_prev, axis=1)), axis=1)
    p_3D_prev = p_3D_prev.reshape((rods_prev, -1, 6))

    delta_s = np.asarray([p_3D - p for p in p_3D_prev])
    delta_s = delta_s.reshape((*delta_s.shape[0:4], 2, 3))
    delta_s = np.linalg.norm(delta_s, axis=-1)
    delta_s = np.sum(delta_s, axis=-1)

    weights = np.concatenate(rods_prev*[delta_s, ], axis=-1)
    weights = 1/weights

    return weights


def create_weights_1(p_3D: np.ndarray, p_3D_prev: np.ndarray,
                     repr_errs: np.ndarray, repr_errs_prev: np.ndarray)\
        -> np.ndarray:
    """Generate weights with 3D-displacement*reprojection-error.

    Creates a weight matrix for matching rods between frames, using the rod
    endpoint displacement between frames times the reprojection-error of the
    rod endpoints as the cost of an assignment.

    Parameters
    ----------
    p_3D : np.ndarray
        Shape must be in (rod_ids(cam1), rod_ids(cam2), 4, 3)
        Dimension explanations:
        (rod_id(cam1), rod_id(cam2), endpoint-combination, 3D-coordinates)
    p_3D_prev : np.ndarray
        Shape must be in (rod_ids, 2, 3).
        Dimension explanations:
        (rod_id, end-point, 3D-coordinates)
    repr_errs : np.ndarray
        Shape must be in (rod_ids(cam1), rod_ids(cam2), 4, 2)
        Dimension explanations:
        (rod_id(cam1), rod_id(cam2), end-combo, err{cam1, cam2})
    repr_errs_prev : np.ndarray
        Shape must be in (rod_id,), with rod_id representing the rods from the
        previous frame.

    Returns
    -------
    np.ndarray
        Weights in the shape of (rod_id, rod_ids(cam1), rod_ids(cam2))
    """

    rods1, rods2 = p_3D.shape[0:2]
    rods_prev = p_3D_prev.shape[0]

    weights = create_weights_0(p_3D, p_3D_prev)

    # create "costs" using reprojection errors
    costs = np.sum(repr_errs, axis=-1)
    costs = np.concatenate((costs, costs), axis=2)
    costs = costs.reshape((*costs.shape[0:2], -1, 2))
    costs = np.sum(costs, axis=-1)
    costs = costs.reshape((costs.shape[0], -1))
    costs = np.repeat(np.expand_dims(costs, axis=0),
                      rods_prev, axis=0)
    costs = np.concatenate(
        [costs[i]*repr_errs_prev[i] for i in range(len(repr_errs_prev))]
    )
    costs = costs.reshape((rods_prev, rods1, rods2, -1))

    costs = np.concatenate(rods_prev*[costs, ], axis=-1)

    weights = weights * (1 / costs)
    return weights


def create_weights_2(p_3D: np.ndarray, p_3D_prev: np.ndarray,
                     repr_errs: np.ndarray, repr_errs_prev: np.ndarray)\
        -> np.ndarray:
    """Create weights with 3D-displacement*reprojection-error*rod_length.

    Creates a weight matrix for matching rods between frames, using the rod
    endpoint displacement between frames times the reprojection-error of the
    rod endpoints times the 3D rod length as the cost of an assignment.

    Parameters
    ----------
    p_3D : np.ndarray
        Shape must be in (rod_ids(cam1), rod_ids(cam2), 4, 3)
        Dimension explanations:
        (rod_id(cam1), rod_id(cam2), endpoint-combination, 3D-coordinates)
    p_3D_prev : np.ndarray
        Shape must be in (rod_ids, 2, 3).
        Dimension explanations:
        (rod_id, end-point, 3D-coordinates)
    repr_errs : np.ndarray
        Shape must be in (rod_ids(cam1), rod_ids(cam2), 4, 2)
        Dimension explanations:
        (rod_id(cam1), rod_id(cam2), end-combo, err{cam1, cam2})
    repr_errs_prev : np.ndarray
        Shape must be in (rod_id,), with rod_id representing the rods from the
        previous frame.

    Returns
    -------
    np.ndarray
        Weights in the shape of (rod_id, rod_ids(cam1), rod_ids(cam2))
    """
    weights = create_weights_1(p_3D, p_3D_prev, repr_errs, repr_errs_prev)
    p_3D = np.concatenate((p_3D, p_3D), axis=2)
    len_diff = np.linalg.norm(
        np.diff(
            p_3D.reshape((*p_3D.shape[0:2], -1, 2, 3)),
            axis=-2
        ),
        axis=-1)
    len_diff = np.abs(10-len_diff)
    # FIXME: remove hard-coded shape
    # weights = weights * (1 / len_diff.reshape(12, 48))
    weights = weights * len_diff.reshape(12, 48)

    return weights


def assign(input_folder: str, output_folder: str, colors: Iterable[str],
           cam1_name: str = "gp1", cam2_name: str = "gp2",
           frame_numbers: Iterable[int] = None, calibration_file: str = None,
           transformation_file: str = None) -> Tuple[np.ndarray]:
    """Matches, triangulates and tracks rods over frames from *.csv data files.

    The function matches rods over multiple frames using npartite matching and
    a combination of 3D displacement and 2D reprojection error as the weights.
    This results in 3D reconstructed rods, that are tracked over the course of
    the given frames.
    It takes *.csv files with the columns from `datasets.DEFAULT_COLUMNS` as
    input and also outputs the results in this format.
    The resulting dataset is saved in the given output folder.

    Parameters
    ----------
    input_folder : str
        Folder containing the *.csv files for all colors given in `colors`s.
    output_folder : str
        Folder to write the output to. The parent folder of this must exist
        already.
    colors : Iterable[str]
        Names of the colors present in the dataset.
        See `datasets.DEFAULT_CLASSES`.
    cam1_name : str, optional
        First camera's identifier in the given dataset.
        By default "gp1".
    cam2_name : str, optional
        Second camera's identifier in the given dataset.
        By default "gp2".
    frame_numbers : Iterable[int], optional
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

    Returns
    -------
    Tuple[np.ndarray]
        -> [0]: reprojection errors
        -> [1]: rod lengths
    """
    if calibration_file is None:
        this_dir = pathlib.Path(__file__).parent.resolve()
        calibration_file = this_dir.joinpath(
            "example_calibration/Matlab/gp12.json")
    if transformation_file is None:
        this_dir = pathlib.Path(__file__).parent.resolve()
        transformation_file = this_dir.joinpath(
            "example_calibration/Matlab/world_transformation.json")
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

    # Preparation of world transformations
    rotx = R.from_matrix(np.asarray(transforms["M_rotate_x"])[0:3, 0:3])
    roty = R.from_matrix(np.asarray(transforms["M_rotate_y"])[0:3, 0:3])
    rotz = R.from_matrix(np.asarray(transforms["M_rotate_z"])[0:3, 0:3])
    rot_comb = roty*rotz*rotx
    tw1 = np.asarray(transforms["M_trans"])[0:3, 3]
    tw2 = np.asarray(transforms["M_trans2"])[0:3, 3]

    all_repr_errs = []
    all_rod_lengths = []
    for color in colors:
        f_in = input_folder + f"/rods_df_{color}.csv"
        data = pd.read_csv(f_in, sep=",", index_col=0)
        df_out = pd.DataFrame()
        for fn in tqdm(range(len(frame_numbers)), colour="green"):
            idx = frame_numbers[fn]
            # Load data
            cols_cam1 = [f'x1_{cam1_name}', f'y1_{cam1_name}',
                         f'x2_{cam1_name}', f'y2_{cam1_name}']
            cols_cam2 = [f'x1_{cam2_name}', f'y1_{cam2_name}',
                         f'x2_{cam2_name}', f'y2_{cam2_name}']
            _data_cam1 = data.loc[data.frame == idx, cols_cam1]
            _data_cam2 = data.loc[data.frame == idx, cols_cam2]
            # remove rows with NaNs or only 0s
            _data_cam1.dropna(how="all", inplace=True)
            _data_cam2.dropna(how="all", inplace=True)
            _data_cam1 = _data_cam1.loc[(_data_cam1 != 0).any(axis=1)]
            _data_cam2 = _data_cam2.loc[(_data_cam2 != 0).any(axis=1)]
            if len(_data_cam1.index) == 0 or len(_data_cam2.index) == 0:
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
            pairs_original = [list(itertools.product(p[0], p[1])) for p in
                              itertools.product(rods_cam1, rods_cam2)]

            pairs_all = np.reshape(pairs_all, (-1, 2, 2))
            pairs_original = np.reshape(pairs_original, (-1, 2, 2))

            p_triang = cv2.triangulatePoints(
                P1, P2,
                pairs_all[:, 0, :].squeeze().transpose(),
                pairs_all[:, 1, :].squeeze().transpose())
            p_triang = np.asarray([p[0:3]/p[3] for p in
                                   p_triang.transpose()])

            # Reprojection to the image plane for point matching
            repr_cam1 = cv2.projectPoints(
                p_triang, r1, t1, calibration["CM1"],
                calibration["dist1"])[0].squeeze()
            repr_cam2 = cv2.projectPoints(
                p_triang, r2, t2, calibration["CM2"],
                calibration["dist2"])[0].squeeze()

            repr_cam1 = pairs_original[:, 0, :] - repr_cam1
            repr_cam2 = pairs_original[:, 1, :] - repr_cam2
            # p_repr: [combo, err_point, cam]
            p_repr = np.stack([repr_cam1, repr_cam2], axis=2)
            p_repr = np.swapaxes(p_repr, 1, 2)  # [combo, cam, err_point]
            repr_errs = np.sum(np.linalg.norm(p_repr, axis=2), axis=1)

            # Transformation to world coordinates
            p_triang = rot_comb.apply((p_triang + tw1)) + tw2

            # Consolidate data
            # Caution: the data order is different form the MATLAB script
            #   ---> Matlab: (p11, p21), (p12, p21), (p11, p22), (p12, p22)
            #   ---> Python: (p11, p21), (p11, p22), (p12, p21), (p12, p22)
            # repr_errs desired shape:[block x err(p)] with
            #   block: re11, re12, re21, re22
            repr_errs = np.reshape(repr_errs, (-1, 4))

            # regular matching
            if fn == 0:
                costs = np.reshape(
                        np.min(
                            [np.sum(repr_errs[:, 0::3], axis=1),
                             np.sum(repr_errs[:, 1:3], axis=1)], axis=0),
                        (len(undist_cam1), len(undist_cam2))
                    )

                cam1_ind, cam2_ind = linear_sum_assignment(costs)
                assignment_cost = costs[cam1_ind, cam2_ind]
                all_repr_errs.append(assignment_cost)

                point_choices = np.asarray(
                    np.sum(repr_errs[:, 0::3], axis=1) <=
                    np.sum(repr_errs[:, 1:3], axis=1))
                point_choices = point_choices.reshape((len(rods_cam1),
                                                       len(rods_cam2)))

                p_triang = p_triang.reshape((len(rods_cam1), len(rods_cam2),
                                             4, 3))

                # Accumulation of the data for saving
                out = np.zeros((len(cam1_ind), 2*3+3+1+4+4))
                for idx_r in range(len(cam1_ind)):
                    i2 = cam2_ind[idx_r]
                    if point_choices[idx_r, i2]:
                        # use point matching of (p11,p21) and (p12,p22)
                        out[idx_r, 0:6] = p_triang[
                            idx_r, i2, 0::3, :].flatten()
                        out[idx_r, 6:9] = p_triang[
                            idx_r, i2, 0::3, :].sum(axis=0)/2
                        out[idx_r, 9] = np.linalg.norm(
                            np.diff(p_triang[idx_r, i2, 0::3, :], axis=0))
                        out[idx_r, 10:14] = rods_cam1[idx_r, :].flatten()
                        out[idx_r, 14:] = rods_cam2[i2, :].flatten()
                    else:
                        # use point matching of (p11,p22) and (p12,p21)
                        out[idx_r, 0:6] = p_triang[idx_r, i2, 1:3, :].flatten()
                        out[idx_r, 6:9] = p_triang[
                            idx_r, i2, 1:3, :].sum(axis=0) / 2
                        out[idx_r, 9] = np.linalg.norm(
                            np.diff(p_triang[idx_r, i2, 1:3, :], axis=0))
                        out[idx_r, 10:14] = rods_cam1[idx_r, -1::-1].flatten()
                        out[idx_r, 14:] = rods_cam2[i2, -1::-1].flatten()
                all_rod_lengths.append(out[:, 9])

                # Data preparation for saving as *.csv
                tmp_df = pd.DataFrame(out, columns=data.columns[:out.shape[1]])
                tmp_df["frame"] = idx
                tmp_df["color"] = color
                tmp_df["particle"] = list(range(len(cam1_ind)))
                seen_cols = [col for col in data.columns if "seen" in col]
                tmp_df[seen_cols] = 1
                df_out = pd.concat([df_out, tmp_df])

            else:
                # 3-assignment matching
                p_triang = p_triang.reshape((len(rods_cam1), len(rods_cam2),
                                             4, 3))
                rep_errs = np.linalg.norm(p_repr, axis=2)
                rep_errs = np.reshape(rep_errs, (len(rods_cam1),
                                      len(rods_cam2), 4, 2))

                last_points = df_out.loc[df_out.frame == frame_numbers[fn-1],
                                         ["x1", "y1", "z1", "x2", "y2", "z2"]]
                last_points = last_points.to_numpy()
                last_points = last_points.reshape((-1, 2, 3))
                # rep_errs: (rod_id(cam1), rod_id(cam2), end-combo, err{cam1, cam2})    # noqa: E501
                # p_triang: (rod_id(cam1), rod_id(cam2), end-combo, 3D-coordinates)     # noqa: E501
                # last_points: (rod_id, end-point, 3D-coordinates)

                prev_repr_errs = all_repr_errs[fn-1]
                weights = create_weights_1(p_triang, last_points, rep_errs,
                                           prev_repr_errs)

                rod, cam1_ind, cam2_ind, combo_idx = npartite_matching(
                    weights, maximize=True)

                rod_nums = list(range(weights.shape[0]))
                idx_out = np.empty((4, weights.shape[0]))
                idx_out.fill(np.nan)
                idx_out[:, rod] = np.stack(
                    [rod, cam1_ind, cam2_ind, combo_idx % 4], axis=0)

                if np.isnan(idx_out).any():
                    idx_out[0, np.isnan(idx_out[0, :])] = [
                        r for r in rod_nums if r not in rod]
                    idx_out[1, np.isnan(idx_out[1, :])] = [
                        r for r in rod_nums if r not in cam1_ind]
                    idx_out[2, np.isnan(idx_out[2, :])] = [
                        r for r in rod_nums if r not in cam2_ind]
                    idx_out[3, np.isnan(idx_out[3, :])] = \
                        np.zeros(np.sum(np.isnan(idx_out[3, :])))

                idx_out = idx_out.astype(int)

                p_triang = np.concatenate((p_triang, p_triang), axis=2)
                p_out = p_triang.reshape((*p_triang.shape[0:2], -1, 2, 3))
                out = np.zeros((idx_out.shape[1], 2*3+3+1+4+4))
                for rod_id in range(idx_out.shape[1]):
                    idx_r = idx_out[0, rod_id]
                    i1 = idx_out[1, rod_id]
                    i2 = idx_out[2, rod_id]
                    i3 = idx_out[3, rod_id]

                    out[idx_r, 0:6] = p_out[i1, i2, i3, :].flatten()
                    out[idx_r, 6:9] = \
                        p_out[i1, i2, i3, :].sum(axis=0) / 2
                    out[idx_r, 9] = np.linalg.norm(
                        np.diff(p_out[i1, i2, i3, :], axis=0))
                    out[idx_r, 10:14] = rods_cam1[i1, :].flatten()
                    out[idx_r, 14:] = rods_cam2[i2, :].flatten()

                ###############################################################
                all_rod_lengths.append(out[:, 9])
                # BUG: costs are only defined on the first frame iteration
                all_repr_errs.append(costs[idx_out[1, :], idx_out[2, :]])

                # Data preparation for saving as *.csv
                tmp_df = pd.DataFrame(out, columns=data.columns[:out.shape[1]])
                tmp_df["frame"] = idx
                tmp_df["color"] = color
                tmp_df["particle"] = rod_nums

                seen_cols = [col for col in data.columns if "seen" in col]
                tmp_df[seen_cols] = 1
                df_out = pd.concat([df_out, tmp_df])

        # Save results to disk
        df_out.reset_index(drop=True, inplace=True)
        df_out.to_csv(os.path.join(output_folder, f"rods_df_{color}.csv"),
                      sep=",")

    return np.asarray(all_repr_errs), np.asarray(all_rod_lengths)
