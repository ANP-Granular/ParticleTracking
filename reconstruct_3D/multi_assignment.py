import os
import pathlib
import itertools

import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation as R
from scipy.optimize import linear_sum_assignment

import reconstruct_3D.data_loading as dl
from thirdparty import ap

def compute_weights():
    pass

def assign(input_folder, output_folder, colors, cam1_name="gp1", 
           cam2_name="gp2", frame_numbers=None, calibration_file=None, 
           transformation_file=None):
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
        for fn in range(len(frame_numbers)):
            idx = frame_numbers[fn]
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

            # regular matching
            if fn == 0:
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

                # Transformation to world coordinates
                p_triang = rot_comb.apply((p_triang + tw1))+ tw2

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

                # Accumulation of the data for saving
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
            
            else:
                # 3-assignment matching
                last_points = df_out.loc[df_out.frame==frame_numbers[fn-1], 
                                         ["x1", "y1", "z1", "x2", "y2", "z2"]]
                last_points = last_points.to_numpy()
                
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

                # Transformation to world coordinates
                p_triang = rot_comb.apply((p_triang + tw1))+ tw2

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
                
                p_triang = p_triang.reshape((len(rods_cam1), len(rods_cam2), 4, 3))
                p_triang_c1 = p_triang[:, :, 0::3, :].reshape((len(rods_cam1), len(rods_cam2),6))  # 11, 22
                p_triang_c2 = p_triang[:, :, 1:3, :].reshape((len(rods_cam1), len(rods_cam2),6))   # 12, 21

                dp_c1 = np.asarray([p_triang_c1 - p for p in last_points])
                dp_c1 = dp_c1.reshape(((-1, len(rods_cam1), len(rods_cam2), 2, 3)))
                
                # FIXME: these must be transformed to edge weights, currently 
                #   it's the weight of the resulting subgraph
                weights_c1 = np.mean(np.linalg.norm(dp_c1, axis=-1), axis=-1)   
                whr = ap.npartite_matching(weights_c1, maximize=True)
                graph, pos, fig = ap.plot_results(weights_c1, whr)
                plt.show()
                print("3-assignment")


if __name__ == "__main__":
    pass