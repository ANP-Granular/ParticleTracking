import json
from pathlib import Path
import numpy as np
import scipy.io as sio


def convert_old(folder: Path):
    cm1 = np.zeros((3, 3))
    cm1[[0, 1], [2, 2]] = np.loadtxt(folder / "c.txt")
    cm1[[0, 1], [0, 1]] = np.loadtxt(folder / "f.txt")
    cm1[2, 2] = 1.
    cm2 = np.zeros((3, 3))
    cm2[[0, 1], [2, 2]] = np.loadtxt(folder / "c2.txt")
    cm2[[0, 1], [0, 1]] = np.loadtxt(folder / "f2.txt")
    cm2[2, 2] = 1.

    dist1 = np.loadtxt(folder / "kc.txt")
    dist2 = np.loadtxt(folder / "kc2.txt")

    R = np.loadtxt(folder / "R.txt", delimiter=",")
    T = np.loadtxt(folder / "transvek.txt")

    to_json = {
        "CM1": cm1.tolist(),
        "dist1": [dist1.tolist()],
        "CM2": cm2.tolist(),
        "dist2": [dist2.tolist()],
        "R": R.tolist(),
        "T": [T.tolist()],
    }
    with open(folder / "converted.json", "w") as f:
        json.dump(to_json, f, indent=2)

    trafos = sio.loadmat(
        folder / "transformations.mat")["transformations"][0][0]
    world_to_json = {
        "transformations": {
            "M_rotate_x": trafos[0].tolist(),
            "M_rotate_y": trafos[1].tolist(),
            "M_rotate_z": trafos[2].tolist(),
            "M_trans2": trafos[3].tolist(),
            "M_trans": trafos[4].tolist(),
        }
    }
    with open(folder / "world_transformations_converted.json", "w") as f:
        json.dump(world_to_json, f, indent=2)


if __name__ == "__main__":
    convert_old(Path("../reconstruct_3D/calibration_data/Matlab/GAGa/"
                     "2015_06/GP78-original"))
