# TODO: document functions/variables/module, resolve todos
import os
import sys
import json
import logging
import warnings
from typing import List
from pathlib import Path
from dataclasses import dataclass
import numpy as np
import pandas as pd

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter(
    "[%(asctime)s] %(name)s %(levelname)s: %(message)s",
    datefmt="%m/%d %H:%M:%S"
    )
ch.setFormatter(formatter)
_logger.addHandler(ch)

# TODO: add default colors/classes
# TODO: define config keys/structure as Literals
DEFAULT_COLUMNS = ['x1', 'y1', 'z1', 'x2', 'y2', 'z2', 'x', 'y', 'z', 'l',
                   'x1_{id1:s}', 'y1_{id1:s}', 'x2_{id1:s}', 'y2_{id1:s}',
                   'x1_{id2:s}', 'y1_{id2:s}', 'x2_{id2:s}', 'y2_{id2:s}',
                   'frame', 'seen_{id1:s}', 'seen_{id2:s}']


class DataSet:
    folder: str
    annotation: str
    name: str

    def __init__(self, name: str, folder: str, annotation_file: str):
        self.name = name
        self.annotation = os.path.abspath(folder+annotation_file)
        self.folder = os.path.abspath(folder)


@dataclass
class DataGroup:
    train: DataSet
    val: DataSet


def get_dataset_size(dataset: DataSet):
    """Compute the number of annotated images in a dataset (excluding
    augmentation)."""
    with open(dataset.annotation) as metadata:
        annotations = json.load(metadata)
    image_count = 0
    for image in list(annotations.values()):
        # Skip non-annotated image entries
        if image["regions"]:
            image_count += 1
    return image_count


def get_dataset_classes(dataset: DataSet):
    """Retrieve the number and IDs of thing classes in the dataset."""
    with open(dataset.annotation) as metadata:
        annotations = json.load(metadata)
    classes = {0, }
    for image in list(annotations.values()):
        regions = image["regions"]
        if regions:
            for region in regions:
                try:
                    classes.add(int(region["region_attributes"]["rod_col"]))
                except KeyError:
                    continue
    return classes


def get_object_counts(dataset: DataSet):
    """Returns a list of the number of objects in each image in the dataset."""
    with open(dataset.annotation) as metadata:
        annotations = json.load(metadata)
    return [len(annotations[key]["regions"]) for key in annotations.keys()]


# TODO: generelize function
def insert_missing_rods(dataset: pd.DataFrame, expected_rods: int) \
        -> pd.DataFrame:
    columns = ["x1", "y1", "z1", "x2", "y2", "z2", "x", "y", "z", "l",
               "x1_gp1", "y1_gp1", "x2_gp1", "y2_gp1",
               "x1_gp2", "y1_gp2", "x2_gp2", "y2_gp2",
               "frame", "seen_gp1", "seen_gp2", "color"]
    for color in dataset.color.unique():
        data_tmp = dataset.loc[dataset.color == color]
        for frame in data_tmp.frame.unique():
            rod_no = len(data_tmp.loc[data_tmp.frame == frame])
            if rod_no == expected_rods:
                continue
            elif rod_no > expected_rods:
                warnings.warn(f"More rods than expected for frame #{frame}"
                              f" of color '{color}'")
            missing = expected_rods - rod_no
            empty_rods = pd.DataFrame(missing * [
                [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan,
                 np.nan, np.nan, np.nan, -1, -1, -1, -1, -1, -1, -1, -1, frame,
                 0, 0, color]],
                columns=columns
                )
            empty_rods["particle"] = np.arange(rod_no, expected_rods,
                                               dtype=int)
            dataset = pd.concat([dataset, empty_rods], ignore_index=True)
    return dataset


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
    """Randomize the order of particles/endpoints in a dataset/-file."""
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
