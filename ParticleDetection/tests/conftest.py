from pathlib import Path
from typing import List
import cv2
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd


EXAMPLES = (Path(__file__).parent / "./example_data").resolve()


def load_rod_data(colors: List[str]):
    data = pd.DataFrame()
    folder = EXAMPLES
    for color in colors:
        tmp_data_file = folder.joinpath(f"rods_df_{color}.csv")
        tmp_data = pd.read_csv(tmp_data_file, index_col=0)
        tmp_data["color"] = color
        data = pd.concat([data, tmp_data])
    data.reset_index(inplace=True)
    return data


def create_dummy_mask(width: int, height: int, angle: int,
                      bar_lengths: int, bar_thickness: int):
    """Creates a dummy segmentation mask of a bar with a defined angle"""
    center_h = (height / 2) - bar_lengths / 2
    center_w = width / 2 - bar_thickness / 2

    rect = Rectangle((center_w, center_h), bar_thickness, bar_lengths,
                     angle=angle, rotation_point='center')
    corners = rect.get_corners()
    ep0 = corners[0] + np.diff(corners[0:2], axis=0) / 2
    ep1 = corners[2] + np.diff(corners[2:], axis=0) / 2

    img = np.zeros((height, width))
    cv2.fillPoly(img, np.int32([corners]), 255)
    mask = img > 0
    return mask, ep0, ep1
