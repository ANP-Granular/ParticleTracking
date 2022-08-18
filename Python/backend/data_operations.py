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
from typing import Iterable, List, Dict, Tuple
from PyQt5 import QtCore
import Python.ui.rodnumberwidget as rn
import Python.backend.logger as lg


rod_data: pd.DataFrame = None
lock = QtCore.QReadWriteLock(QtCore.QReadWriteLock.Recursive)


def extract_rods(cam_id: str, frame: int, color: str) -> \
        List[rn.RodNumberWidget]:
    """Extracts rod data for one color and creates the `RodNumberWidget`s.

    Extracts the rod position data one color in one frame from `rod_data`. It 
    creates the `RodNumberWidget` that is associated with each rod.

    Parameters
    ----------
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
    global rod_data
    lock.lockForRead()
    col_list = ["particle", "frame", f"x1_{cam_id}",
                f"x2_{cam_id}", f"y1_{cam_id}",
                f"y2_{cam_id}", f"seen_{cam_id}"]

    df_part = rod_data.loc[rod_data.color == color, col_list]
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
    lock.unlock()
    return new_rods


def extract_seen_information() -> Tuple[Dict[int, Dict[str, dict]], list]:
    """Extracts the seen/unseen parameter for all rods in `rod_data`.

    Returns
    -------
    Dict[Dict[dict]]
        Frame[Color[RodNo.]] -> out[501]["red"][1] = ["seen", "unseen"]
    list
        out_list = ["gp1_seen", "gp2_seen"]
    """
    global rod_data
    lock.lockForRead()
    seen_data = {}
    col_list = ["particle", "frame", "color"]
    cam_regex = re.compile('seen_gp\d+')
    to_include = []
    for col in rod_data.columns:
        if re.fullmatch(cam_regex, col):
            to_include.append(col)
    col_list.extend(to_include)

    df_part = rod_data[col_list]
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
    lock.unlock()
    return seen_data, [cam.split("_")[-1] for cam in to_include]


def find_unused_rods() -> pd.DataFrame:
    """Searches for unused rods in the `rod_data` dataset.

    Marks and returns unused rods by verifying that the columns "\*_gp\*" in
    the dataset contain only 0 or NaN.

    Returns
    -------
    DataFrame
        The rows from the given dataset that were identified as not being used.
    """
    global rod_data
    lock.lockForRead()
    cam_regex = re.compile('[xy][12]_gp\d+')
    to_include = []
    for col in rod_data.columns:
        if re.fullmatch(cam_regex, col):
            to_include.append(col)

    has_nans = rod_data[rod_data.isna().any(axis=1)]
    has_data = has_nans.loc[:, has_nans.columns.isin(to_include)].any(
        axis=1)
    unused = has_nans.loc[has_data == False]
    lock.unlock()
    return unused


def change_data(new_data: dict) -> None:
    """Changes or extends the `rod_data` dataset with the given new data.

    Parameters
    ----------
    new_data : dict
        Dictionary describing the new/changed rod data. Must contain the fields
        ["frame", "cam_id", "color", "position", "rod_id"]
    """
    global rod_data
    lock.lockForWrite()
    frame = new_data["frame"]
    cam_id = new_data["cam_id"]
    color = new_data["color"]
    points = new_data["position"]
    rod_id = new_data["rod_id"]
    seen = new_data["seen"]
    
    if isinstance(rod_id, Iterable):
        for i in range(len(rod_id)):
            tmp_data = {
                "frame": frame[i],
                "cam_id": cam_id[i],
                "color": color[i],
                "position": points[i],
                "rod_id": rod_id[i],
                "seen": seen[i]
            }
            rod_data = change_data(rod_data, tmp_data)
        lock.unlock()
        return

    data_unavailable = rod_data.loc[(rod_data.frame == frame) & (
            rod_data.particle == rod_id) & (rod_data.color == color),
        [f"x1_{cam_id}", f"y1_{cam_id}", f"x2_{cam_id}", f"y2_{cam_id}"]].empty
    if data_unavailable:
        new_idx = rod_data.index.max() + 1
        rod_data.loc[new_idx] = len(rod_data.columns) * [math.nan]
        rod_data.loc[new_idx, [f"x1_{cam_id}", f"y1_{cam_id}",
                              f"x2_{cam_id}", f"y2_{cam_id}", "frame",
                              f"seen_{cam_id}", "particle", "color"]] \
            = [*points, frame, seen, rod_id, color]
    else:
        rod_data.loc[(rod_data.frame == frame) & (rod_data.particle == rod_id)
                    & (rod_data.color == color),
                    [f"x1_{cam_id}", f"y1_{cam_id}",
                     f"x2_{cam_id}", f"y2_{cam_id}", f"seen_{cam_id}"]] = \
            [*points, seen]
    rod_data = rod_data.astype({"frame": 'int', f"seen_{cam_id}": 'int',
                              "particle": 'int'})
    lock.unlock()
    return


def rod_number_swap(mode: lg.NumberChangeActions, previous_id: int, 
                    new_id: int, color: str, frame: int, 
                    cam_id: str = None) -> pd.DataFrame:
    """Adjusts a DataFrame according to rod number switching modes.
    
    Parameters
    ----------
    mode: str
        Possible values "all", "one_cam", "both_cams".
    """
    global rod_data
    lock.lockForWrite()
    tmp_set = rod_data.copy()
    if mode == lg.NumberChangeActions.ALL:
        rod_data.loc[(tmp_set.color == color) & 
                    (tmp_set.particle == previous_id) &
                    (tmp_set.frame >= frame), "particle"] = new_id
        rod_data.loc[(tmp_set.color == color) & 
                    (tmp_set.particle == new_id) &
                    (tmp_set.frame >= frame), "particle"] = previous_id
    elif mode == lg.NumberChangeActions.ALL_ONE_CAM:
        cols = rod_data.columns
        mask_previous = (tmp_set.color == color) & \
                        (tmp_set.particle == previous_id) & \
                        (tmp_set.frame >= frame)
        mask_new = (tmp_set.color == color) & \
                   (tmp_set.particle == new_id) & \
                   (tmp_set.frame >= frame)
        cam_cols = [c for c in cols if cam_id in c] 
        rod_data.loc[mask_previous, cam_cols] = \
            tmp_set.loc[mask_new, cam_cols].values
        rod_data.loc[mask_new, cam_cols] = \
            tmp_set.loc[mask_previous, cam_cols].values
    elif mode == lg.NumberChangeActions.ONE_BOTH_CAMS:
        rod_data.loc[(tmp_set.color == color) & (tmp_set.particle == previous_id)
                    & (tmp_set.frame == frame), "particle"] = new_id
        rod_data.loc[(tmp_set.color == color) & (tmp_set.particle == new_id) & 
                    (tmp_set.frame == frame), "particle"] = previous_id
    else:
        # unknown mode
        pass
    lock.unlock()
    return
