"""Randomize the order of particles/endpoints in a dataset/-file."""
from pathlib import Path
from typing import List
import numpy as np
import pandas as pd

rnd_seed = 1


def randomize_particles(file: Path):
    file = file.resolve()
    out = file.parent / ("rand_particles_" + str(file.name))
    data = pd.read_csv(file, index_col=0)
    data_out = pd.DataFrame()
    for frame in data.frame.unique():
        data_tmp = data.loc[data.frame == frame].sample(frac=1,
                                                        ignore_index=True,
                                                        random_state=rnd_seed)
        data_out = pd.concat([data_out, data_tmp])
    data_out.reset_index(drop=True, inplace=True)
    data_out.to_csv(out, sep=",")


def randomize_endpoints(file: Path, cam_ids: List[str] = None):
    file = file.resolve()
    out_p = file.parent / ("rand_endpoints_" + str(file.name))
    if cam_ids is None:
        cam_ids = ["gp1", "gp2"]
    data = pd.read_csv(file, index_col=0)
    for c in cam_ids:
        to_perm = data[[f"x1_{c}", f"y1_{c}", f"x2_{c}", f"y2_{c}"]].to_numpy()
        out = np.zeros(to_perm.shape)
        for i in range(len(to_perm)):
            if np.random.randint(0, 2):
                out[i, :] = to_perm[i, :]
            else:
                out[i, 0:2] = to_perm[i, 2:]
                out[i, 2:] = to_perm[i, 0:2]
        data[[f"x1_{c}", f"y1_{c}", f"x2_{c}", f"y2_{c}"]] = out

    data.to_csv(out_p, sep=",")
