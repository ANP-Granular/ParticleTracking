#  Copyright (c) 2021 Adrian Niemann Dmitry Puzyrev
#
#  This file is part of RodTracker.
#  RodTracker is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  RodTracker is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with RodTracker.  If not, see <http://www.gnu.org/licenses/>.

import re
import math
import pandas as pd
from typing import List, Dict, Tuple
from PyQt5 import QtCore
from PyQt5.QtWidgets import QTreeWidget
import Python.ui.rodnumberwidget as rn


def extract_rods(data, cam_id: str, frame: int, color: str) -> \
        List[rn.RodNumberWidget]:
    """Extracts rod data for one color and creates the `RodNumberWidget`s.

    Extracts the rod position data one color in one frame. It creates the
    `RodNumberWidget` that is associated with each rod.

    Parameters
    ----------
    data : DataFrame
        Dataset from which the rod positions and IDs are extracted.
    cam_id : str
        ID of the camera for selection of the correct columns in `data`.
    frame : int
        Number/ID of the frame to display/extract.
    color : str
        Color to display/extract.

    Returns
    -------
    List[RodNumberWidget]
    """
    col_list = ["particle", "frame", f"x1_{cam_id}",
                f"x2_{cam_id}", f"y1_{cam_id}",
                f"y2_{cam_id}", f"seen_{cam_id}"]

    df_part = data.loc[data.color == color, col_list]
    df_part2 = df_part[df_part["frame"] == frame].reset_index().fillna(0)

    new_rods = []
    for ind_rod, value in enumerate(df_part2['particle']):
        x1 = df_part2[f'x1_{cam_id}'][ind_rod]
        x2 = df_part2[f'x2_{cam_id}'][ind_rod]
        y1 = df_part2[f'y1_{cam_id}'][ind_rod]
        y2 = df_part2[f'y2_{cam_id}'][ind_rod]
        seen = bool(df_part2[f'seen_{cam_id}'][ind_rod])

        # Add rods
        ident = rn.RodNumberWidget(color, None, str(value),
                                   QtCore.QPoint(0, 0))
        ident.rod_id = value
        ident.rod_points = [x1, y1, x2, y2]
        ident.setObjectName(f"rn_{ind_rod}")
        ident.seen = seen
        new_rods.append(ident)
    return new_rods


# TODO: move to different Thread
def extract_seen_information(data: pd.DataFrame) -> \
        Tuple[Dict[int, Dict[str, dict]], list]:
    """Extracts the seen/unseen parameter for all rods in the dataset.

    Parameters
    ----------
    data : DataFrame
        (Complete) dataset of rods.

    Returns
    -------
    Dict[Dict[dict]]
        Frame[Color[RodNo.]] -> out[501]["red"][1] = ["seen", "unseen"]
    list
        out_list = ["gp1_seen", "gp2_seen"]
    """
    seen_data = {}
    col_list = ["particle", "frame", "color"]
    cam_regex = re.compile('seen_gp\d+')
    to_include = []
    for col in data.columns:
        if re.fullmatch(cam_regex, col):
            to_include.append(col)
    col_list.extend(to_include)

    df_part = data[col_list]
    for item in df_part.iterrows():
        item = item[1]
        current_seen = ['seen' if item[gp] else 'unseen' for gp in
                        to_include]
        if item.frame in seen_data.keys():
            if item.color in seen_data[item.frame].keys():
                seen_data[item.frame][item.color][item.particle] = current_seen
            else:
                seen_data[item.frame][item.color] = {item.particle:
                                                     current_seen}
        else:
            seen_data[item.frame] = \
                {item.color: {item.particle: current_seen}}
    return seen_data, [cam.split("_")[-1] for cam in to_include]


def find_unused_rods(data: pd.DataFrame) -> pd.DataFrame:
    """Searches for unused rods in the given dataset.

    Marks and returns unused rods by verifying that the columns "\*_gp\*" in
    the dataset contain only 0 or NaN.

    Parameters
    ----------
    data : DataFrame
        Dataset of rods.

    Returns
    -------
    DataFrame
        The rows from the given dataset that were identified as not being used.
    """
    cam_regex = re.compile('[xy][12]_gp\d+')
    to_include = []
    for col in data.columns:
        if re.fullmatch(cam_regex, col):
            to_include.append(col)

    has_nans = data[data.isna().any(axis=1)]
    has_data = has_nans.loc[:, has_nans.columns.isin(to_include)].any(
        axis=1)
    unused = has_nans.loc[has_data == False]
    return unused


def change_data(dataset: pd.DataFrame, new_data: dict) -> pd.DataFrame:
    """Changes or extends the rod dataset with the given new data.

    Parameters
    ----------
    dataset : DataFrame
        Dataset of rods.
    new_data : dict
        Dictionary describing the new/changed rod data. Must contain the fields
        ["frame", "cam_id", "color", "position", "rod_id"]

    Returns
    -------
    DataFrame
        The changed/extended dataset.
    """
    frame = new_data["frame"]
    cam_id = new_data["cam_id"]
    color = new_data["color"]
    points = new_data["position"]
    rod_id = new_data["rod_id"]
    seen = new_data["seen"]

    data_unavailable = dataset.loc[(dataset.frame == frame) & (
            dataset.particle == rod_id) & (dataset.color == color),
        [f"x1_{cam_id}", f"y1_{cam_id}", f"x2_{cam_id}", f"y2_{cam_id}"]].empty
    if data_unavailable:
        new_idx = dataset.index.max() + 1
        dataset.loc[new_idx] = len(dataset.columns) * [math.nan]
        dataset.loc[new_idx, [f"x1_{cam_id}", f"y1_{cam_id}",
                              f"x2_{cam_id}", f"y2_{cam_id}", "frame",
                              f"seen_{cam_id}", "particle", "color"]] \
            = [*points, frame, seen, rod_id, color]
    else:
        dataset.loc[(dataset.frame == frame) & (dataset.particle == rod_id)
                    & (dataset.color == color),
                    [f"x1_{cam_id}", f"y1_{cam_id}",
                     f"x2_{cam_id}", f"y2_{cam_id}", f"seen_{cam_id}"]] = \
            [*points, seen]
    dataset = dataset.astype({"frame": 'int', f"seen_{cam_id}": 'int',
                              "particle": 'int'})
    return dataset
