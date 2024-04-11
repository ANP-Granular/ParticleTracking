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
Collection of previously used automatic rod tracking approaches. These are just
implemented for comparison with new, more promising methods.

**Authors:** Dmitry Puzyrev (dmitry.puzyrev@ovgu.de), Adrian Niemann
(adrian.niemann@ovgu.de)

**Date:** 31.10.2022

"""
import itertools
from typing import Tuple

import numpy as np
import pandas as pd
import trackpy as tp
from scipy.optimize import linear_sum_assignment


def tracking_trackpy(data: pd.DataFrame, report: bool = False) -> pd.DataFrame:
    """Tracks rods (one colour) over multiple frames using ``trackpy``.

    Parameters
    ----------
    data : pd.DataFrame
        _Data(-slice) from rod tracking. Must contain at least the following
        columns: x, y, z,
    report : bool, optional
        Flag, whether to print the number of rods before and after tracking.
        By default False.

    Returns
    -------
    pd.DataFrame
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
        print(
            f"Before: {data['particle'].nunique()}\tAfter: "
            f"{data_out['particle'].nunique()}"
        )
    return data_out


def tracking_global_assignment(
    data: pd.DataFrame,
) -> Tuple[pd.DataFrame, np.ndarray]:
    """Tracks rods (one colour) over multiple frames with optimal assignment.

    The rods given are matched with all others in the next frame and the
    optimal assignment is determined by comparing the distances between the
    endpoints.

    Parameters
    ----------
    data : DataFrame
        Data(-slice) from rod tracking. Must contain at least the following
        columns: x1, y1, z1, x2, y2, z2, frame, particle(, unseen)

    Returns
    -------
    Tuple[DataFrame, ndarray]
        Retuns the tracked data, i.e. the initial data with adjusted particle
        numbers. Additionlly, returns the assignment costs per frame, i.e. the
        distance between the endpoints of all matched rods.
    """
    out = pd.DataFrame()
    # get frame info from data
    frames = data["frame"].unique()

    # data_pX: (frame, rod, coord)
    data_p1 = data[["x1", "y1", "z1"]].to_numpy().reshape((len(frames), -1, 3))
    data_p2 = data[["x2", "y2", "z2"]].to_numpy().reshape((len(frames), -1, 3))

    point_combos = [
        list(itertools.product(p1, p2)) for p1, p2 in zip(data_p1, data_p2)
    ]
    point_combos = np.asarray(point_combos)
    p1s = point_combos[:, :, 0, :]
    p2s = point_combos[:, :, 1, :]

    # distances: (combination, frame, data_p1 x data_p2)
    distances = np.zeros((2, len(frames) - 1, p1s.shape[1]))
    distances[0, :] = np.linalg.norm(
        np.diff(p1s, axis=0), axis=2
    ) + np.linalg.norm(np.diff(p2s, axis=0), axis=2)
    distances[1, :] = np.linalg.norm(
        p1s[0:-1, :] - p2s[1:, :], axis=2
    ) + np.linalg.norm(p2s[0:-1, :] - p1s[1:, :], axis=2)

    # TODO: double weight/distance, if rods were "unseen"

    cost = np.min(distances, axis=0)
    cost = np.reshape(
        cost, (len(frames) - 1, data_p1.shape[1], data_p2.shape[1])
    )
    results = [[linear_sum_assignment(f_c)] for f_c in cost]
    results = np.asarray(results).squeeze()

    out = data.copy()
    if "particle" not in out.columns:
        out["particle"] = 0
        init_ids = np.arange(len(out.loc[out.frame == frames[0]]))
        out.loc[out.frame == frames[0], ["particle"]] = init_ids
    for f, new_id in zip(frames[1:], results):
        tmp = out.loc[out.frame == f].copy()
        tmp.iloc[new_id[1, :], tmp.columns.get_loc("particle")] = new_id[1, :]
        out.loc[out.frame == f] = tmp

    out = out.sort_values(by=["frame", "particle"]).reset_index(drop=True)
    total_cost = cost[:, results[:, 0, :], results[:, 1, :]]
    total_cost = total_cost.diagonal(offset=0, axis1=0, axis2=1).sum(axis=0)
    return out, total_cost
