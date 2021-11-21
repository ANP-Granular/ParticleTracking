import re
import math
import pandas as pd
from typing import List
from PyQt5 import QtCore
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
                f"y2_{cam_id}", "seen"]

    df_part = data.loc[data.color == color, col_list]
    df_part2 = df_part[df_part["frame"] == frame].reset_index().fillna(0)

    new_rods = []
    for ind_rod, value in enumerate(df_part2['particle']):
        x1 = df_part2[f'x1_{cam_id}'][ind_rod]
        x2 = df_part2[f'x2_{cam_id}'][ind_rod]
        y1 = df_part2[f'y1_{cam_id}'][ind_rod]
        y2 = df_part2[f'y2_{cam_id}'][ind_rod]
        seen = bool(df_part2["seen"][ind_rod])

        # Add rods
        ident = rn.RodNumberWidget(color, None, str(value),
                                   QtCore.QPoint(0, 0))
        ident.rod_id = value
        ident.rod_points = [x1, y1, x2, y2]
        ident.setObjectName(f"rn_{ind_rod}")
        ident.seen = seen
        new_rods.append(ident)
    return new_rods


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

    data_unavailable = dataset.loc[(dataset.frame == frame) & (
            dataset.particle == rod_id) & (dataset.color == color),
        [f"x1_{cam_id}", f"y1_{cam_id}", f"x2_{cam_id}", f"y2_{cam_id}"]].empty
    if data_unavailable:
        new_idx = dataset.index.max() + 1
        dataset.loc[new_idx] = len(dataset.columns) * [math.nan]
        dataset.loc[new_idx, [f"x1_{cam_id}", f"y1_{cam_id}",
                              f"x2_{cam_id}", f"y2_{cam_id}", "frame",
                              "seen", "particle", "color"]] \
            = [*points, frame, 1, rod_id, color]
    else:
        dataset.loc[(dataset.frame == frame) & (dataset.particle == rod_id)
                    & (dataset.color == color),
                    [f"x1_{cam_id}", f"y1_{cam_id}",
                     f"x2_{cam_id}", f"y2_{cam_id}"]] = points
    dataset = dataset.astype({"frame": 'int', "seen": 'int',
                              "particle": 'int'})
    return dataset
