# Copyright (c) 2023-24 Adrian Niemann, Dmitry Puzyrev
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
Functions to reconstruct 3D rod endpoints from images of a stereocamera system
on a per-frame basis, without knowledge about positions in other frames.
Some functions are directly ported from a MATLAB implementation to python.

**Authors**: Adrian Niemann (adrian.niemann@ovgu.de), Dmitry Puzyrev
(dmitry.puzyrev@ovgu.de)

**Date**:       01.11.2022

"""
import itertools
import logging
import os
import pathlib
import warnings
from typing import Iterable

import cv2
import numpy as np
import pandas as pd
import scipy.io as sio
from scipy.optimize import linear_sum_assignment
from scipy.spatial.transform import Rotation as R
from tqdm import tqdm

import ParticleDetection.utils.data_loading as dl

_logger = logging.getLogger(__name__)


def match_matlab_simple(
    cam1_folder,
    cam2_folder,
    output_folder,
    colors,
    frame_numbers,
    calibration_file=None,
    transformation_file=None,
    cam1_convention="{idx:05d}_{color:s}.mat",
    cam2_convention="{idx:05d}_{color:s}.mat",
):  # pragma: no cover
    """Ported Matlab script from ``match_rods_2020mix_gp12_cl1.m``.
    This function takes the same input file format and outputs the same file
    formats as the previous implementation in MATLAB. Use this function for a
    consistent behaviour to previous data processings.

    Parameters
    ----------
    See :func:`match_matlab_complex`

    Returns
    -------
    See :func:`match_matlab_complex`

    Note
    ----
    This function currently saves the 3D points in the first camera's
    coordinate system, NOT the world/box coordinate system.


    .. warning::
        .. deprecated:: 0.4.0
            Use :func:`match_csv_complex` instead.
    """
    warnings.warn(
        "match_matlab_*() functions are deprecated."
        " Use functions for csv instead.",
        DeprecationWarning,
    )

    if not cam1_convention.endswith(".mat"):
        cam1_convention += ".mat"
    if not cam2_convention.endswith(".mat"):
        cam2_convention += ".mat"
    if calibration_file is None:
        this_dir = pathlib.Path(__file__).parent.resolve()
        calibration_file = this_dir.joinpath(
            "example_calibration/Matlab/gp12.json"
        )
    if transformation_file is None:
        this_dir = pathlib.Path(__file__).parent.resolve()
        transformation_file = this_dir.joinpath(
            "example_calibration/Matlab/world_transformation.json"
        )
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    # Load Matlab exported calibrations
    calibration = dl.load_camera_calibration(str(calibration_file))
    transforms = dl.load_calib_from_json(transformation_file)

    # Derive projection matrices from the calibration
    r1 = np.eye(3)
    t1 = np.expand_dims(np.array([0.0, 0.0, 0.0]), 1)
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
    rot_comb = rotz * roty * rotx
    tw1 = np.asarray(transforms["M_trans"])[0:3, 3]
    tw2 = np.asarray(transforms["M_trans2"])[0:3, 3]

    # Setup the triangulation function with the loaded calibration
    def triangulate(point1, point2, sampson=False):
        orig1 = point1
        orig2 = point2
        point1 = cv2.undistortImagePoints(
            point1, calibration["CM1"], calibration["dist1"]
        ).squeeze()
        point2 = cv2.undistortImagePoints(
            point2, calibration["CM2"], calibration["dist2"]
        ).squeeze()
        if sampson:
            # Use Sampson distance as an additional correction
            Fn = calibration["F"] / np.linalg.norm(calibration["F"])
            r = np.append(point2.T, 1) @ Fn @ np.append(point1, 1)
            fd0 = Fn[0:2, 0:2].T @ point2 + Fn[2, 0:2].T
            fd1 = Fn[0:2, 0:2].T @ point1 + Fn[2, 0:2].T
            g = fd0.T @ fd0 + fd1.T @ fd1
            e = r / g
            point1 = point1 - e * fd0
            point2 = point2 - e * fd1

        wp = cv2.triangulatePoints(P1, P2, point1, point2)
        wp = wp[0:3] / wp[3]
        rp1 = cv2.projectPoints(
            wp, r1, t1, calibration["CM1"], distCoeffs=calibration["dist1"]
        )[0]
        rp2 = cv2.projectPoints(
            wp, r2, t2, calibration["CM2"], distCoeffs=calibration["dist2"]
        )[0]
        # Transformation to world coordinates
        wp = rot_comb.apply((wp + tw1)) + tw2
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
            cam1_file = cam1_folder + cam1_convention.format(
                idx=idx, color=color
            )
            cam2_file = cam2_folder + cam2_convention.format(
                idx=idx, color=color
            )
            rods_cam1 = sio.loadmat(cam1_file)["rod_data_links"][0]
            rods_cam2 = sio.loadmat(cam2_file)["rod_data_links"][0]
            # format of rods_camX: [rod, point, coordinate(x/y)]
            rods_cam1 = np.asarray(
                [np.asarray([rod[0], rod[1]]) for rod in rods_cam1]
            ).squeeze()
            rods_cam2 = np.asarray(
                [np.asarray([rod[0], rod[1]]) for rod in rods_cam2]
            ).squeeze()

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
                    rep_errs[i, j] = np.asarray(
                        [[rep_e1, rep_e2], [rep_e3, rep_e4]]
                    )
                    lengths[i, j, 0] = np.linalg.norm(wp1_1 - wp1_2)
                    lengths[i, j, 1] = np.linalg.norm(wp2_1 - wp2_2)

            cam1_ind, cam2_ind = linear_sum_assignment(
                np.min(np.sum(rep_errs, (-2, -1)), 2)
            )
            summed_errs = np.min(np.sum(rep_errs, (3, 4)), 2)
            all_repr_errs.append(summed_errs[cam1_ind, cam2_ind])
            out = np.zeros((len(cam1_ind), 2 * 3 + 3 + 1 + 4 + 4))
            for i, j in zip(cam1_ind, cam2_ind):
                c1_p1 = rods_cam1[i, 0]
                c1_p2 = rods_cam1[i, 1]
                c2_p1 = rods_cam2[j, 0]
                c2_p2 = rods_cam2[j, 1]
                wp1_1, rep_e1 = triangulate(c1_p1, c2_p1)
                wp1_2, rep_e2 = triangulate(c1_p2, c2_p2)
                wp2_1, rep_e3 = triangulate(c1_p2, c2_p1)
                wp2_2, rep_e4 = triangulate(c1_p1, c2_p2)
                rep_errs[i, j] = np.asarray(
                    [[rep_e1, rep_e2], [rep_e3, rep_e4]]
                )
                lengths[i, j, 0] = np.linalg.norm(wp1_1 - wp1_2)
                lengths[i, j, 1] = np.linalg.norm(wp2_1 - wp2_2)
                if rep_e1 + rep_e2 < rep_e3 + rep_e4:
                    out[i, 0:6] = np.concatenate(
                        (wp1_1, wp1_2), axis=0
                    ).squeeze()
                    out[i, 6:9] = ((wp1_1 + wp1_2) / 2).squeeze()
                    out[i, 9] = lengths[i, j, 0]
                    out[i, 10:14] = rods_cam1[i].flatten()
                    out[i, 14:] = rods_cam2[j].flatten()
                else:
                    out[i, 0:6] = np.concatenate(
                        (wp2_1, wp2_2), axis=0
                    ).squeeze()
                    out[i, 6:9] = ((wp2_1 + wp2_2) / 2).squeeze()
                    out[i, 9] = lengths[i, j, 1]
                    out[i, 10:14] = rods_cam1[i].flatten()
                    out[i, 14:] = rods_cam2[j, ::-1].flatten()
            all_rod_lengths.append(out[:, 9])
            file_out = f"{f_out}{idx:05d}.txt"
            np.savetxt(file_out, out, fmt="%.18f", delimiter=" ")
    return all_repr_errs, all_rod_lengths


def match_matlab_complex(
    cam1_folder,
    cam2_folder,
    output_folder,
    colors,
    frame_numbers,
    calibration_file=None,
    transformation_file=None,
    cam1_convention="{idx:05d}_{color:s}.mat",
    cam2_convention="{idx:05d}_{color:s}.mat",
):  # pragma: no cover
    """Match rod endpoints per frame such that the reprojection error is
    minimal.
    This function takes the same input file format and outputs the same file
    formats as the previous implementation in MATLAB. The inputs and outputs
    are equivalent to :func:`match_matlab_simple` but makes heavy use of matrix
    operations to increase computational efficiency.

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
        Path to a ``*.json`` file with stereocalibration data for the cameras
        which produced the images for the rod position data.\n
        By default the calibration constructed with Matlab for GP1 and GP2 is
        used.
    transformation_file : str, optional
        Path to a ``*.json`` file with transformation matrices expressing the
        transformation from the first camera's coordinate system to the
        world/box coordinate system.\n
        By default the transformation constructed with Matlab is used.
    cam1_convention : str, optional
        Naming convention for the first camera's position data files defined
        by a formattable string, that accepts some of the following
        variables: ``{idx, color}``.\n
        By default ``"{idx:05d}_{color:s}.mat"``.
    cam2_convention : str, optional
        Naming convention for the second camera's position data files defined
        by a formattable string, that accepts some of the following
        variables: ``{idx, color}``.\n
        By default ``"{idx:05d}_{color:s}.mat"``.

    Returns
    -------
    ndarray, ndarray
        Reprojection errors, rod lengths of the matched rod endpoints.

    Note
    ----
    This function currently saves the 3D points in the first camera's
    coordinate system, **NOT** the world/box coordinate system.


    .. warning::
        .. deprecated:: 0.4.0
            Use :func:`match_csv_complex` instead.
    """
    warnings.warn(
        "match_matlab_*() functions are deprecated."
        " Use functions for csv instead.",
        DeprecationWarning,
    )

    if not cam1_convention.endswith(".mat"):
        cam1_convention += ".mat"
    if not cam2_convention.endswith(".mat"):
        cam2_convention += ".mat"
    if calibration_file is None:
        this_dir = pathlib.Path(__file__).parent.resolve()
        calibration_file = this_dir.joinpath(
            "example_calibration/Matlab/gp12.json"
        )
    if transformation_file is None:
        this_dir = pathlib.Path(__file__).parent.resolve()
        transformation_file = this_dir.joinpath(
            "example_calibration/Matlab/world_transformation.json"
        )
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    calibration = dl.load_camera_calibration(str(calibration_file))
    transforms = dl.load_calib_from_json(str(transformation_file))

    # Derive projection matrices from the calibration
    r1 = np.eye(3)
    t1 = np.expand_dims(np.array([0.0, 0.0, 0.0]), 1)
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
    rot_comb = rotz * roty * rotx
    tw1 = np.asarray(transforms["M_trans"])[0:3, 3]
    tw2 = np.asarray(transforms["M_trans2"])[0:3, 3]

    all_repr_errs = []
    all_rod_lengths = []
    for color in colors:
        f_out = output_folder + f"data3d_{color}/"
        if not os.path.exists(f_out):
            os.mkdir(f_out)

        for idx in frame_numbers:
            # Load data
            cam1_file = cam1_folder + cam1_convention.format(
                idx=idx, color=color
            )
            cam2_file = cam2_folder + cam2_convention.format(
                idx=idx, color=color
            )
            rods_cam1 = sio.loadmat(cam1_file)["rod_data_links"][0]
            rods_cam2 = sio.loadmat(cam2_file)["rod_data_links"][0]

            # format of rods_camX: [rod, point, coordinate(x/y)]
            rods_cam1 = np.asarray(
                [np.asarray([rod[0], rod[1]]) for rod in rods_cam1]
            ).squeeze()
            rods_cam2 = np.asarray(
                [np.asarray([rod[0], rod[1]]) for rod in rods_cam2]
            ).squeeze()

            # Undistort points using the camera calibration
            tmp_points = cv2.undistortImagePoints(
                rods_cam1.reshape(2, -1),
                calibration["CM1"],
                calibration["dist1"],
            ).squeeze()
            undist_cam1 = np.zeros(tmp_points.shape)
            tmp_points = np.concatenate([tmp_points[:, 0], tmp_points[:, 1]])
            for i in range(len(tmp_points)):
                undist_cam1[i // 2][i % 2] = tmp_points[i]
            undist_cam1 = undist_cam1.reshape((-1, 2, 2))

            tmp_points = cv2.undistortImagePoints(
                rods_cam2.reshape(2, -1),
                calibration["CM2"],
                calibration["dist2"],
            ).squeeze()
            undist_cam2 = np.zeros(tmp_points.shape)
            tmp_points = np.concatenate([tmp_points[:, 0], tmp_points[:, 1]])
            for i in range(len(tmp_points)):
                undist_cam2[i // 2][i % 2] = tmp_points[i]
            undist_cam2 = undist_cam2.reshape((-1, 2, 2))

            # Triangulation of all possible point-pairs to 3D
            pairs_all = [
                list(itertools.product(p[0], p[1]))
                for p in itertools.product(undist_cam1, undist_cam2)
            ]
            pairs_all = np.reshape(pairs_all, (-1, 2, 2))

            pairs_original = [
                list(itertools.product(p[0], p[1]))
                for p in itertools.product(rods_cam1, rods_cam2)
            ]
            pairs_original = np.reshape(pairs_original, (-1, 2, 2))

            p_triang = cv2.triangulatePoints(
                P1,
                P2,
                pairs_all[:, 0, :].squeeze().transpose(),
                pairs_all[:, 1, :].squeeze().transpose(),
            )
            p_triang = np.asarray(
                [p[0:3] / p[3] for p in p_triang.transpose()]
            )

            # Reprojection to the image plane for point matching
            repr_cam1 = cv2.projectPoints(
                p_triang, r1, t1, calibration["CM1"], calibration["dist1"]
            )[0].squeeze()
            repr_cam2 = cv2.projectPoints(
                p_triang, r2, t2, calibration["CM2"], calibration["dist2"]
            )[0].squeeze()

            repr_cam1 = pairs_original[:, 0, :] - repr_cam1
            repr_cam2 = pairs_original[:, 1, :] - repr_cam2
            # Dimensions p_repr: [combo, err_point, cam]
            p_repr = np.stack([repr_cam1, repr_cam2], axis=2)
            p_repr = np.swapaxes(p_repr, 1, 2)  # [combo, cam, err_point]
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
                    [
                        np.sum(repr_errs[:, 0::3], axis=1),
                        np.sum(repr_errs[:, 1:3], axis=1),
                    ],
                    axis=0,
                ),
                (len(undist_cam1), len(undist_cam2)),
            )

            cam1_ind, cam2_ind = linear_sum_assignment(costs)
            assignment_cost = costs[cam1_ind, cam2_ind]
            all_repr_errs.append(assignment_cost)

            point_choices = np.asarray(
                np.sum(repr_errs[:, 0::3], axis=1)
                <= np.sum(repr_errs[:, 1:3], axis=1)
            )

            point_choices = point_choices.reshape(
                (len(rods_cam1), len(rods_cam2))
            )

            # Transformation to world coordinates
            p_triang = rot_comb.apply((p_triang + tw1)) + tw2
            p_triang = p_triang.reshape((len(rods_cam1), len(rods_cam2), 4, 3))

            out = np.zeros((len(cam1_ind), 2 * 3 + 3 + 1 + 4 + 4))
            idx_out = 0  # TODO: remove the use of idx_out
            for m in range(len(cam1_ind)):
                k = cam1_ind[m]
                j = cam2_ind[m]
                if point_choices[k, j]:
                    # use point matching of (p11,p21) and (p12,p22)
                    out[idx_out, 0:6] = p_triang[k, j, 0::3, :].flatten()
                    out[idx_out, 6:9] = p_triang[k, j, 0::3, :].sum(axis=0) / 2
                    out[idx_out, 9] = np.linalg.norm(
                        np.diff(p_triang[k, j, 0::3, :], axis=0)
                    )
                    out[idx_out, 10:14] = rods_cam1[k, :].flatten()
                    out[idx_out, 14:] = rods_cam2[j, :].flatten()

                else:
                    # use point matching of (p11,p22) and (p12,p21)
                    out[idx_out, 0:6] = p_triang[k, j, 1:3, :].flatten()
                    out[idx_out, 6:9] = p_triang[k, j, 1:3, :].sum(axis=0) / 2
                    out[idx_out, 9] = np.linalg.norm(
                        np.diff(p_triang[k, j, 1:3, :], axis=0)
                    )
                    out[idx_out, 10:14] = rods_cam1[k, -1::-1].flatten()
                    out[idx_out, 14:] = rods_cam2[j, -1::-1].flatten()

                idx_out += 1  # TODO: remove the use of idx_out
            all_rod_lengths.append(out[:, 9])

            file_out = f"{f_out}{idx:05d}.txt"
            np.savetxt(file_out, out, fmt="%.18f", delimiter=" ")
    return np.array(all_repr_errs), np.array(all_rod_lengths)


def match_csv_complex(
    input_folder,
    output_folder,
    colors,
    cam1_name="gp1",
    cam2_name="gp2",
    frame_numbers=None,
    calibration_file=None,
    transformation_file=None,
    rematching=True,
):
    """Matches and triangulates rods from ``*.csv`` data files.

    The function matches rod endpoints per frame such that the reprojection
    error is minimal. It takes ``*.csv`` files with the columns from
    :const:`~ParticleDetection.utils.datasets.DEFAULT_COLUMNS` as input and
    also outputs the results in this format.

    Parameters
    ----------
    input_folder : str
        Folder containing the ``*.csv`` files for all colors given in
        ``colors``.
    output_folder : str
        Folder to write the output to. The parent folder of this must exist
        already.
    colors : Iterable[str]
        Names of the colors present in the dataset.
        See :const:`~ParticleDetection.utils.datasets.DEFAULT_CLASSES`.
    cam1_name : str, optional
        First camera's identifier in the given dataset.\n
        By default ``"gp1"``.
    cam2_name : str, optional
        Second camera's identifier in the given dataset.\n
        By default ``"gp2"``.
    frame_numbers : Iterable[int], optional
        An iterable of frame numbers present in the data.
        By default ``None``.
    calibration_file : str, optional
        Path to a ``*.json`` file with stereocalibration data for the cameras
        which produced the images for the rod position data.\n
        By default the calibration constructed with Matlab for GP1 and GP2 is
        used.
    transformation_file : str, optional
        Path to a ``*.json`` file with transformation matrices expressing the
        transformation from the first camera's coordinate system to the
        world/box coordinate system.\n
        By default the transformation constructed with Matlab is used.

    Returns
    -------
    ndarray, ndarray
        Reprojection errors, rod lengths of the matched rod endpoints.
    """
    if calibration_file is None:
        this_dir = pathlib.Path(__file__).parent.resolve()
        calibration_file = this_dir.joinpath(
            "example_calibration/Matlab/gp12.json"
        )
    if transformation_file is None:
        this_dir = pathlib.Path(__file__).parent.resolve()
        transformation_file = this_dir.joinpath(
            "example_calibration/Matlab/world_transformation.json"
        )
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    calibration = dl.load_camera_calibration(str(calibration_file))
    transforms = dl.load_world_transformation(str(transformation_file))

    # Derive projection matrices from the calibration
    r1 = np.eye(3)
    t1 = np.expand_dims(np.array([0.0, 0.0, 0.0]), 1)
    P1 = np.vstack((r1.T, t1.T)) @ calibration["CM1"].T
    P1 = P1.T

    r2 = calibration["R"]
    t2 = calibration["T"]
    P2 = np.vstack((r2.T, t2.T)) @ calibration["CM2"].T
    P2 = P2.T

    # Preparation of world transformations
    rot = R.from_matrix(transforms["rotation"])
    trans = transforms["translation"]

    all_repr_errs = []
    all_rod_lengths = []
    for color in colors:
        f_in = input_folder + f"/rods_df_{color}.csv"
        data = pd.read_csv(f_in, sep=",", index_col=0)
        df_out = pd.DataFrame()
        for idx in frame_numbers:
            ret = match_frame(
                data,
                cam1_name,
                cam2_name,
                idx,
                color,
                calibration,
                P1,
                P2,
                rot,
                trans,
                r1,
                r2,
                t1,
                t2,
                rematching,
            )
            tmp_df, costs, lens = ret
            all_repr_errs.append(costs)
            all_rod_lengths.append(lens)
            df_out = pd.concat([df_out, tmp_df])
        df_out.reset_index(drop=True, inplace=True)
        df_out.to_csv(
            os.path.join(output_folder, f"rods_df_{color}.csv"), sep=","
        )

    return np.array(all_repr_errs), np.array(all_rod_lengths)


def match_complex(
    data: pd.DataFrame,
    frame_numbers: Iterable[int],
    color: str,
    calibration: dict,
    transform: dict,
    cam1_name="gp1",
    cam2_name="gp2",
    renumber: bool = True,
):
    """Matches and triangulates rods from a ``DataFrame``.

    The function matches rod endpoints per frame such that the reprojection
    error is minimal.

    Parameters
    ----------
    data : DataFrame
        Dataset of rod positions.
    frame_numbers : Iterable[int]
        An iterable of frame numbers present in the data.
    color : str
        Color of the rods in ``data`` to match.
    calibration : dict
        Stereocamera calibration parameters with the required fields:\n
        ``"CM1"``: camera matrix of cam1\n
        ``"R"``: rotation matrix between cam1 & cam2\n
        ``"T"``: translation vector between cam1 & cam2\n
        ``"CM2"``: camera matrix of cam2
    transform : dict
        Coordinate system transformation matrices from camera 1 coordinates to
        *world*/*experiment* coordinates.
        **Must contain the following fields:**\n
        ``"M_rotate_x"``, ``"M_rotate_y"``, ``"M_rotate_z"``, ``"M_trans"``,
        ``"M_trans2"``
    cam1_name : str, optional
        First camera's identifier in the given dataset.\n
        By default ``"gp1"``.
    cam2_name : str, optional
        Second camera's identifier in the given dataset.\n
        By default ``"gp2"``.
    renumber : bool, optional
        Flag, whether to keep the already assigned combinations between
        camera 1 and camera 2.\n
        ``True``:   Only the endpoint combinations are (re-)evaluated.\n
        ``False``:  Rod combinations between camera 1 and camera 1 as well as
        their respective endpoint combinations are (re-)evaluated.\n
        By default ``True``.

    Returns
    -------
    Tuple[DataFrame, ndarray, ndarray]
        Returns the endpoint matched `DataFrame` together with the reprojection
        errors and the resulted rod lengths.
    """
    # Derive projection matrices from the calibration
    r1 = np.eye(3)
    t1 = np.expand_dims(np.array([0.0, 0.0, 0.0]), 1)
    P1 = np.vstack((r1.T, t1.T)) @ calibration["CM1"].T
    P1 = P1.T

    r2 = calibration["R"]
    t2 = calibration["T"]
    P2 = np.vstack((r2.T, t2.T)) @ calibration["CM2"].T
    P2 = P2.T

    if "translation" in transform.keys():
        rot = R.from_matrix(transform["rotation"])
        trans = transform["translation"]
    else:
        rotx = R.from_matrix(np.asarray(transform["M_rotate_x"])[0:3, 0:3])
        roty = R.from_matrix(np.asarray(transform["M_rotate_y"])[0:3, 0:3])
        rotz = R.from_matrix(np.asarray(transform["M_rotate_z"])[0:3, 0:3])
        tw1 = np.asarray(transform["M_trans"])[0:3, 3]
        tw2 = np.asarray(transform["M_trans2"])[0:3, 3]
        rot = rotz * roty * rotx
        trans = rot.apply(tw1) + tw2

    all_repr_errs = []
    all_rod_lengths = []
    df_out = pd.DataFrame()
    for idx in frame_numbers:
        ret = match_frame(
            data,
            cam1_name,
            cam2_name,
            idx,
            color,
            calibration,
            P1,
            P2,
            rot,
            trans,
            r1,
            r2,
            t1,
            t2,
            renumber,
        )
        tmp_df, costs, lens = ret
        all_repr_errs.append(costs)
        all_rod_lengths.append(lens)
        df_out = pd.concat([df_out, tmp_df])
    df_out.reset_index(drop=True, inplace=True)
    return df_out, all_repr_errs, all_rod_lengths


def match_frame(
    data: pd.DataFrame,
    cam1_name: str,
    cam2_name: str,
    frame: int,
    color: str,
    calibration: dict,
    P1: np.ndarray,
    P2: np.ndarray,
    rot: R,
    trans: np.ndarray,
    r1: np.ndarray,
    r2: np.ndarray,
    t1: np.ndarray,
    t2: np.ndarray,
    renumber: bool = True,
):
    """Matches and triangulates rods from a ``DataFrame``.

    Parameters
    ----------
    data : DataFrame
        Dataset of rod positions.
    cam1_name : str
        First camera's identifier in the given dataset, e.g. ``"gp1"``.
    cam2_name : str
        Second camera's identifier in the given dataset, e.g. ``"gp2"``.
    frame : int
        Frame in ``data`` who's endpoints shall be (re-)evaluated.
    color : str
        Color of the rods in ``data`` to match.
    calibration : dict
        Stereocamera calibration parameters with the required fields:\n
        ``"CM1"``: camera matrix of cam1\n
        ``"R"``: rotation matrix between cam1 & cam2\n
        ``"T"``: translation vector between cam1 & cam2\n
        ``"CM2"``: camera matrix of cam2
    P1 : ndarray
        Projection matrix for camera 1.
    P2 : ndarray
        Projection matrix for camera 2.
    rot : Rotation
        Rotation from camera 1 coordinates to *world*/*experiment* coordinates.
    trans : ndarray
        Translation vector as part of the transformation to
        *world*/*experiment* coordinates.
    r1 : ndarray
        Rotation matrix of camera 1.
    r2 : ndarray
        Rotation matrix of camera 2.
    t1 : ndarray
        Translation vector of camera 1.
    t2 : ndarray
        Translation vector of camera 2.
    renumber : bool, optional
        Flag, whether to keep the already assigned combinations between
        camera 1 and camera 2.\n
        ``True``: Only the endpoint combinations are (re-)evaluated.\n
        ``False``: Rod combinations between camera 1 and camera 1 as well as
        their respective endpoint combinations are (re-)evaluated.\n
        By default ``True``.

    Returns
    -------
    Tuple[DataFrame, ndarray, ndarray]
        Returns the ``DataFrame`` with (re-)matched endpoints for ``frame`` of
        ``color``. Additionally, returns the assignment costs, i.e. the sum of
        end point reprojection errors per rod. Lastly, returns the lengths of
        the reconstructed rods.
    """
    # Load data
    cols_cam1 = [
        f"x1_{cam1_name}",
        f"y1_{cam1_name}",
        f"x2_{cam1_name}",
        f"y2_{cam1_name}",
    ]
    cols_cam2 = [
        f"x1_{cam2_name}",
        f"y1_{cam2_name}",
        f"x2_{cam2_name}",
        f"y2_{cam2_name}",
    ]
    _data_cam1 = data.loc[data.frame == frame, cols_cam1]
    _data_cam2 = data.loc[data.frame == frame, cols_cam2]
    # remove rows with NaNs or only 0s
    _data_cam1.dropna(how="all", inplace=True)
    _data_cam2.dropna(how="all", inplace=True)
    _data_cam1 = _data_cam1.loc[(_data_cam1 != 0).any(axis=1)]
    _data_cam2 = _data_cam2.loc[(_data_cam2 != 0).any(axis=1)]
    if not renumber:
        drop_rows = _data_cam1.index.symmetric_difference(_data_cam2.index)
        _data_cam1.drop(index=drop_rows, inplace=True, errors="ignore")
        _data_cam2.drop(index=drop_rows, inplace=True, errors="ignore")
        df_particles = data.drop(index=drop_rows, errors="ignore")[
            ["frame", "particle"]
        ]
    if len(_data_cam1.index) == 0 or len(_data_cam2.index) == 0:
        # no rod data available for matching
        return

    # format of rods_camX: [rod, point, coordinate(x/y)]
    rods_cam1 = _data_cam1.to_numpy().reshape(-1, 2, 2)
    rods_cam2 = _data_cam2.to_numpy().reshape(-1, 2, 2)

    # Undistort points using the camera calibration
    tmp_points = cv2.undistortImagePoints(
        rods_cam1.reshape(2, -1), calibration["CM1"], calibration["dist1"]
    ).squeeze()
    undist_cam1 = np.zeros(tmp_points.shape)
    tmp_points = np.concatenate([tmp_points[:, 0], tmp_points[:, 1]])
    for i in range(len(tmp_points)):
        undist_cam1[i // 2][i % 2] = tmp_points[i]
    undist_cam1 = undist_cam1.reshape((-1, 2, 2))

    tmp_points = cv2.undistortImagePoints(
        rods_cam2.reshape(2, -1), calibration["CM2"], calibration["dist2"]
    ).squeeze()
    undist_cam2 = np.zeros(tmp_points.shape)
    tmp_points = np.concatenate([tmp_points[:, 0], tmp_points[:, 1]])
    for i in range(len(tmp_points)):
        undist_cam2[i // 2][i % 2] = tmp_points[i]
    undist_cam2 = undist_cam2.reshape((-1, 2, 2))

    if renumber:
        # Triangulation of all possible point-pairs to 3D
        pairs_all = [
            list(itertools.product(p[0], p[1]))
            for p in itertools.product(undist_cam1, undist_cam2)
        ]
        pairs_original = [
            list(itertools.product(p[0], p[1]))
            for p in itertools.product(rods_cam1, rods_cam2)
        ]

    else:
        pairs_all = [
            list(itertools.product(p[0], p[1]))
            for p in zip(undist_cam1, undist_cam2)
        ]
        pairs_original = [
            list(itertools.product(p[0], p[1]))
            for p in zip(rods_cam1, rods_cam2)
        ]

    pairs_all = np.reshape(pairs_all, (-1, 2, 2))
    pairs_original = np.reshape(pairs_original, (-1, 2, 2))

    p_triang = cv2.triangulatePoints(
        P1,
        P2,
        pairs_all[:, 0, :].squeeze().transpose(),
        pairs_all[:, 1, :].squeeze().transpose(),
    )
    p_triang = np.asarray([p[0:3] / p[3] for p in p_triang.transpose()])

    # Reprojection to the image plane for point matching
    repr_cam1 = cv2.projectPoints(
        p_triang, r1, t1, calibration["CM1"], calibration["dist1"]
    )[0].squeeze()
    repr_cam2 = cv2.projectPoints(
        p_triang, r2, t2, calibration["CM2"], calibration["dist2"]
    )[0].squeeze()

    repr_cam1 = pairs_original[:, 0, :] - repr_cam1
    repr_cam2 = pairs_original[:, 1, :] - repr_cam2
    # Dimensions p_repr: [combo, err_point, cam]
    p_repr = np.stack([repr_cam1, repr_cam2], axis=2)
    p_repr = np.swapaxes(p_repr, 1, 2)  # [combo, cam, err_point]
    repr_errs = np.mean(np.linalg.norm(p_repr, axis=2), axis=1)

    # Transformation to world coordinates
    p_triang = rot.apply(p_triang) + trans

    # Consolidate data
    # Caution: the data order is different form the MATLAB script
    #   ---> Matlab: (p11, p21), (p12, p21), (p11, p22), (p12, p22)
    #   ---> Python: (p11, p21), (p11, p22), (p12, p21), (p12, p22)
    # repr_errs desired shape:[block x err(p)] with
    #   block: re11, re12, re21, re22
    repr_errs = np.reshape(repr_errs, (-1, 4))
    if renumber:
        costs = np.reshape(
            np.min(
                [
                    np.sum(repr_errs[:, 0::3], axis=1),
                    np.sum(repr_errs[:, 1:3], axis=1),
                ],
                axis=0,
            ),
            (len(undist_cam1), len(undist_cam2)),
        )
        cam1_ind, cam2_ind = linear_sum_assignment(costs)
        costs = costs[cam1_ind, cam2_ind]
        point_choices = np.asarray(
            np.sum(repr_errs[:, 0::3], axis=1)
            <= np.sum(repr_errs[:, 1:3], axis=1)
        )
        point_choices = point_choices.reshape((len(rods_cam1), len(rods_cam2)))
    else:
        costs = np.min(
            [
                np.sum(repr_errs[:, 0::3], axis=1),
                np.sum(repr_errs[:, 1:3], axis=1),
            ],
            axis=0,
        )
        cam1_ind = np.arange(0, len(undist_cam1))
        cam2_ind = np.arange(0, len(undist_cam2))
        point_choices = np.sum(repr_errs[:, 0::3], axis=1) <= np.sum(
            repr_errs[:, 1:3], axis=1
        )
        point_choices = np.eye(len(point_choices)) * point_choices
        p_triang = p_triang.reshape(-1, 4, 3)
        p_triang = np.tile(p_triang, (len(p_triang), 1, 1))

    try:
        p_triang = p_triang.reshape((len(rods_cam1), len(rods_cam2), 4, 3))
    except ValueError as e:
        _logger.error(f"A value error has occured during reshaping: {e}")

    # Accumulation of the data for saving
    out = np.zeros((len(cam1_ind), 2 * 3 + 3 + 1 + 4 + 4))
    for i1 in range(len(cam1_ind)):
        i2 = cam2_ind[i1]
        if point_choices[i1, i2]:
            # use point matching of (p11,p21) and (p12,p22)
            out[i1, 0:6] = p_triang[i1, i2, 0::3, :].flatten()
            out[i1, 6:9] = p_triang[i1, i2, 0::3, :].sum(axis=0) / 2
            out[i1, 9] = np.linalg.norm(
                np.diff(p_triang[i1, i2, 0::3, :], axis=0)
            )
            out[i1, 10:14] = rods_cam1[i1, :].flatten()
            out[i1, 14:] = rods_cam2[i2, :].flatten()
        else:
            # use point matching of (p11,p22) and (p12,p21)
            out[i1, 0:6] = p_triang[i1, i2, 1:3, :].flatten()
            out[i1, 6:9] = p_triang[i1, i2, 1:3, :].sum(axis=0) / 2
            out[i1, 9] = np.linalg.norm(
                np.diff(p_triang[i1, i2, 1:3, :], axis=0)
            )
            out[i1, 10:14] = rods_cam1[i1, -1::-1].flatten()
            out[i1, 14:] = rods_cam2[i2, -1::-1].flatten()

    # Data preparation for saving as *.csv
    cols_3d = ["x1", "y1", "z1", "x2", "y2", "z2", "x", "y", "z", "l"]
    tmp_df = pd.DataFrame(out, columns=[*cols_3d, *cols_cam1, *cols_cam2])
    tmp_df["frame"] = frame
    tmp_df["color"] = color
    if (not renumber) and ("particle" in data.columns):
        tmp_df["particle"] = df_particles.loc[
            df_particles.frame == frame, "particle"
        ].values
    else:
        tmp_df["particle"] = list(range(len(tmp_df)))
    seen_cols = [col for col in data.columns if "seen" in col]
    tmp_df[seen_cols] = 1
    return tmp_df, costs, out[:, 9]


def reorder_endpoints_csv(
    input_folder: str,
    output_folder: str,
    colors: Iterable[str],
    cam1_name: str = "gp1",
    cam2_name: str = "gp2",
    frame_numbers: Iterable[int] = None,
):
    """Reorders endpoints from ``*.csv`` data files.

    The function reorders rod endpoints per frame such that the endpoints
    displacement between consecutive frames is minimal. It does not change the
    rod number assignment and does not match the 2D endpoint coordinates into
    3D acoording to the reprojection error. Usually this step is performed
    after rematching or instead of it if rematching is not necessary.

    It takes ``*.csv`` files with the columns from
    :const:`~ParticleDetection.utils.datasets.DEFAULT_COLUMNS` as input and
    also outputs the results in this format.

    Parameters
    ----------
    input_folder : str
        Folder containing the ``*.csv`` files for all colors given in
        ``colors``.
    output_folder : str
        Folder to write the output to. The parent folder of this must exist
        already.
    colors : Iterable[str]
        Names of the colors present in the dataset.
        See :const:`~ParticleDetection.utils.datasets.DEFAULT_CLASSES`.
    cam1_name : str, optional
        First camera's identifier in the given dataset.\n
        By default ``"gp1"``.
    cam2_name : str, optional
        Second camera's identifier in the given dataset.\n
        By default ``"gp2"``.
    frame_numbers : Iterable[int], optional
        An iterable of frame numbers present in the data.\n
        By default ``None``.

    Returns
    -------
    Tuple[ndarray]
        Returns the assignment costs, i.e. the sum of end point reprojection
        errors per rod.
    """
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    for color in colors:
        f_in = input_folder + f"/rods_df_{color}.csv"
        data = pd.read_csv(f_in, sep=",", index_col=0)

        frame = frame_numbers[0]
        dfs_out = []
        df_raw_add = data.loc[data["frame"] == frame].sort_values("particle")
        mincosts_T = np.zeros((len(df_raw_add), len(frame_numbers) - 1))
        df0 = df_raw_add.copy()

        dfs_out.append(df_raw_add)

        for frame in tqdm(frame_numbers[1:]):
            df1 = data.loc[data["frame"] == frame].sort_values("particle")

            df_raw_add = df1.copy()

            for i in df1["particle"].unique():
                x1_0 = df0.loc[df0["particle"] == i, "x1"].to_numpy()
                y1_0 = df0.loc[df0["particle"] == i, "y1"].to_numpy()
                z1_0 = df0.loc[df0["particle"] == i, "z1"].to_numpy()
                x2_0 = df0.loc[df0["particle"] == i, "x2"].to_numpy()
                y2_0 = df0.loc[df0["particle"] == i, "y2"].to_numpy()
                z2_0 = df0.loc[df0["particle"] == i, "z2"].to_numpy()

                x1_1 = df1.loc[df1["particle"] == i, "x1"].to_numpy()
                y1_1 = df1.loc[df1["particle"] == i, "y1"].to_numpy()
                z1_1 = df1.loc[df1["particle"] == i, "z1"].to_numpy()
                x2_1 = df1.loc[df1["particle"] == i, "x2"].to_numpy()
                y2_1 = df1.loc[df1["particle"] == i, "y2"].to_numpy()
                z2_1 = df1.loc[df1["particle"] == i, "z2"].to_numpy()

                x1gp1_1 = df1.loc[df1["particle"] == i, "x1_gp1"].to_numpy()
                y1gp1_1 = df1.loc[df1["particle"] == i, "y1_gp1"].to_numpy()
                x2gp1_1 = df1.loc[df1["particle"] == i, "x2_gp1"].to_numpy()
                y2gp1_1 = df1.loc[df1["particle"] == i, "y2_gp1"].to_numpy()

                x1gp2_1 = df1.loc[df1["particle"] == i, "x1_gp2"].to_numpy()
                y1gp2_1 = df1.loc[df1["particle"] == i, "y1_gp2"].to_numpy()
                x2gp2_1 = df1.loc[df1["particle"] == i, "x2_gp2"].to_numpy()
                y2gp2_1 = df1.loc[df1["particle"] == i, "y2_gp2"].to_numpy()

                comb1 = np.linalg.norm(
                    [x1_0 - x1_1, y1_0 - y1_1, z1_0 - z1_1]
                ) + np.linalg.norm([x2_0 - x2_1, y2_0 - y2_1, z2_0 - z2_1])
                comb2 = np.linalg.norm(
                    [x2_0 - x1_1, y2_0 - y1_1, z2_0 - z1_1]
                ) + np.linalg.norm([x1_0 - x2_1, y1_0 - y2_1, z1_0 - z2_1])

                mincosts_T[i, frame - frame_numbers[1]] = min(comb1, comb2)

                if comb2 < comb1:
                    df_raw_add.loc[df_raw_add["particle"] == i, "x1"] = x2_1
                    df_raw_add.loc[df_raw_add["particle"] == i, "y1"] = y2_1
                    df_raw_add.loc[df_raw_add["particle"] == i, "z1"] = z2_1
                    df_raw_add.loc[df_raw_add["particle"] == i, "x2"] = x1_1
                    df_raw_add.loc[df_raw_add["particle"] == i, "y2"] = y1_1
                    df_raw_add.loc[df_raw_add["particle"] == i, "z2"] = z1_1

                    df_raw_add.loc[df_raw_add["particle"] == i, "x1_gp1"] = (
                        x2gp1_1
                    )
                    df_raw_add.loc[df_raw_add["particle"] == i, "y1_gp1"] = (
                        y2gp1_1
                    )
                    df_raw_add.loc[df_raw_add["particle"] == i, "x2_gp1"] = (
                        x1gp1_1
                    )
                    df_raw_add.loc[df_raw_add["particle"] == i, "y2_gp1"] = (
                        y1gp1_1
                    )

                    df_raw_add.loc[df_raw_add["particle"] == i, "x1_gp2"] = (
                        x2gp2_1
                    )
                    df_raw_add.loc[df_raw_add["particle"] == i, "y1_gp2"] = (
                        y2gp2_1
                    )
                    df_raw_add.loc[df_raw_add["particle"] == i, "x2_gp2"] = (
                        x1gp2_1
                    )
                    df_raw_add.loc[df_raw_add["particle"] == i, "y2_gp2"] = (
                        y1gp2_1
                    )

            df0 = df_raw_add.copy()
            dfs_out.append(df_raw_add)

        df_out = pd.concat(dfs_out)

        df_out.reset_index(drop=True, inplace=True)
        df_out.to_csv(
            os.path.join(output_folder, f"rods_df_{color}.csv"), sep=","
        )

    return mincosts_T
