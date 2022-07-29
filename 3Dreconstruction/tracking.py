from typing import List
import numpy as np
import matplotlib.pyplot as plt
import mpl_toolkits.mplot3d.axes3d as p3
import matplotlib.animation as animation
import matplotlib.image as mpimg
# import pandas as pd
# import trackpy as tp
import skimage
from scipy.io import loadmat
from scipy.signal import savgol_filter
from scipy.optimize import linear_sum_assignment
# import seaborn as sns
from filterpy.common import kinematic_kf, Q_discrete_white_noise
from filterpy.kalman import IMMEstimator
from data_loading import load_positions_from_txt


def tracking_trackpy(colors: List[str], c):
    pass


def tracking_global_assignment():
    pass


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
        file_format += "{:05d}.txt"
        data = load_positions_from_txt(file_format, col_names, [732, 733], 8)
        data["seen_gp1"] = 1
        data["seen_gp2"] = 1


if __name__ == "__main__":
    testing()
