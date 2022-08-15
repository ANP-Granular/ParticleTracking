import itertools
from typing import List
import numpy as np
import matplotlib.pyplot as plt
import mpl_toolkits.mplot3d.axes3d as p3
import matplotlib.animation as animation
import matplotlib.image as mpimg
import pandas as pd
import trackpy as tp
import skimage
from scipy.io import loadmat
from scipy.signal import savgol_filter
from scipy.optimize import linear_sum_assignment
# import seaborn as sns
from filterpy.common import kinematic_kf, Q_discrete_white_noise
from filterpy.kalman import IMMEstimator
from .data_loading import load_positions_from_txt


def tracking_trackpy(data: pd.DataFrame, report: bool = False) -> pd.DataFrame:
    """
    
    """
    # Linking of trajectories (center of particles)
    predictor = tp.predict.NearestVelocityPredict()
    tp.quiet(suppress=True)
    rods = predictor.link_df(data, 1, pos_columns=["x", "y", "z"], memory=3)
    tp.quiet(suppress=False)

    # Filtering trajectories
    data_out = tp.filter_stubs(rods, 5)
    
    # Report
    if report:
        print(f"Before: {data['particle'].nunique()}\tAfter: "
              f"{data_out['particle'].nunique()}")
    return data_out


def tracking_global_assignment(data: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    # get frame info from data
    frames = data["frame"].unique()

    # data_pX: (frame, rod, coord)
    data_p1 = data[["x1", "y1", "z1"]].to_numpy().reshape((len(frames), -1, 3))
    data_p2 = data[["x2", "y2", "z2"]].to_numpy().reshape((len(frames), -1, 3))

    point_combos = [list(itertools.product(p1, p2)) for p1, p2 in zip(data_p1, data_p2)]
    point_combos = np.asarray(point_combos)
    p1s = point_combos[:, :, 0, :]
    p2s = point_combos[:, :, 1, :]

    distances = np.zeros((2, len(frames) - 1, p1s.shape[1]))
    distances[0, :] = np.linalg.norm(np.diff(p1s, axis=0), axis=2) + \
        np.linalg.norm(np.diff(p2s, axis=0), axis=2)
    distances[1, :] = \
        np.linalg.norm(p1s[0:-1, :] - p2s[1:, :], axis=2) + \
        np.linalg.norm(p2s[0:-1, :] - p1s[1:, :], axis=2)

    # distances = np.zeros((2, len(frames)-1, data_p1.shape[1]))
    # distances[0, :] = np.linalg.norm(np.diff(data_p1, axis=0), axis=2) + \
    #     np.linalg.norm(np.diff(data_p2, axis=0), axis=2)
    # distances[1, :] = \
    #     np.linalg.norm(data_p1[0:-1, :] - data_p2[1:, :], axis=2) + \
    #     np.linalg.norm(data_p2[0:-1, :] - data_p1[1:, :], axis=2)
    # cost = np.min(distances, axis=0)
    # p1_ind, p2_ind = linear_sum_assignment(cost)

    cost = np.min(distances, axis=0)
    cost = np.reshape(cost, (len(frames)-1, data_p1.shape[1], data_p2.shape[1]))
    results = [[linear_sum_assignment(f_c)] for f_c in cost]
    results = np.asarray(results).squeeze()[:, 1, :]
    out1 = np.zeros(data_p1.shape)
    out2 = np.zeros(data_p2.shape)
    out1[0, :] = data_p1[0, :]
    out2[0, :] = data_p2[0, :]
    # FIXME:
    out1[1, :] = data_p1[1, results[0, :], :]

    data[["x1", "y1", "z1"]] = ...
    data[["x2", "y2", "z2"]] = ...
    return data


def tracking_imm_kalman():
    pass


def testing():
    colors = ['blue', 'green', 'orange', 'purple', 'red', 'yellow', 'lilac',
              'brown']

    col_names = ['x1', 'y1', 'z1', 'x2', 'y2', 'z2', 'x', 'y', 'z', 'l',
                 'x1_gp1',
                 'y1_gp1', 'x2_gp1', 'y2_gp1', 'x1_gp2', 'y1_gp2', 'x2_gp2',
                 'y2_gp2', 'frame']
    col_names_seen = ['x1', 'y1', 'z1', 'x2', 'y2', 'z2', 'x', 'y', 'z', 'l',
                      'x1_gp1', 'y1_gp1', 'x2_gp1', 'y2_gp1', 'x1_gp2',
                      'y1_gp2',
                      'x2_gp2', 'y2_gp2', 'seen_gp1', 'seen_gp2', 'frame']

    for c in colors:
        file_format = f"./testfiles/data3D/data3d_{c}/"
        # file_format = f"./3Dreconstruction/testfiles/data3D/data3d_{c}/"
        file_format += "{:05d}.txt"
        frames = list(range(732, 737))
        data = load_positions_from_txt(file_format, col_names, frames, 8)
        data["seen_gp1"] = 1
        data["seen_gp2"] = 1
        tracked = tracking_global_assignment(data)
        # Preliminary saving
        tracked.to_csv('./testfiles/data3D/rods_df_{:s}.csv'.format(c))

if __name__ == "__main__":
    # testing()
    pass
