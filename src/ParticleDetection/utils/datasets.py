"""
Functions and classes for dataset information and manipulation.

Author:     Adrian Niemann (adrian.niemann@ovgu.de)
Date:       31.10.2022

"""
import os
import sys
import json
import logging
import warnings
from typing import List, Set, Dict
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


DEFAULT_CLASSES = {
    0: 'blue', 1: 'green', 2: 'orange', 3: 'purple', 4: 'red',
    5: 'yellow', 6: 'black', 7: 'lilac', 8: 'brown'
}
DEFAULT_COLUMNS = ['x1', 'y1', 'z1', 'x2', 'y2', 'z2', 'x', 'y', 'z', 'l',
                   'x1_{id1:s}', 'y1_{id1:s}', 'x2_{id1:s}', 'y2_{id1:s}',
                   'x1_{id2:s}', 'y1_{id2:s}', 'x2_{id2:s}', 'y2_{id2:s}',
                   'frame', 'seen_{id1:s}', 'seen_{id2:s}', 'color']
RNG_SEED = 1


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


def get_dataset_size(dataset: DataSet) -> int:
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


def get_dataset_classes(dataset: DataSet) -> Set[int]:
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


def get_object_counts(dataset: DataSet) -> List[int]:
    """Returns a list of the number of objects in each image in the dataset."""
    with open(dataset.annotation) as metadata:
        annotations = json.load(metadata)
    return [len(annotations[key]["regions"]) for key in annotations.keys()]


def insert_missing_rods(dataset: pd.DataFrame, expected_rods: int,
                        cam1_id: str = "gp1", cam2_id: str = "gp2") \
        -> pd.DataFrame:
    """Inserts 'empty' rods into a dataset, depending on how many are expected.

    Parameters
    ----------
    dataset : pd.DataFrame
        Dataset with the column format from `DEFAULT_COLUMNS`.
    expected_rods : int
        The expected number of rods per frame (and color).
    cam1_id : str
        Default is "gp1".
    cam2_id : str
        Default is "gp2".

    Returns
    -------
    pd.DataFrame
    """
    columns = [col.format(id1=cam1_id, id2=cam2_id) for col in DEFAULT_COLUMNS]
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


def randomize_particles(file: Path) -> None:
    """Randomizes particle numbers per frame of a given *.csv dataset.

    The dataset with randomized particle numbers is saved with
    'rand_particles_' as a prefix to the file's name.

    Parameters
    ----------
    file : Path
        Path to a *.csv file containing data in the format of
        `DEFAULT_COLUMNS`, but at minimum with column `frame`.
    """
    file = file.resolve()
    out = file.parent / ("rand_particles_" + str(file.name))
    data = pd.read_csv(file, index_col=0)
    data_out = pd.DataFrame()
    for frame in data.frame.unique():
        data_tmp = data.loc[data.frame == frame].sample(frac=1,
                                                        ignore_index=True,
                                                        random_state=RNG_SEED)
        data_out = pd.concat([data_out, data_tmp])
    data_out.reset_index(drop=True, inplace=True)
    data_out.to_csv(out, sep=",")


def randomize_endpoints(file: Path, cam_ids: List[str] = None) -> None:
    """Randomize the order of particles/endpoints in a dataset/-file.

    The dataset with randomized particle numbers is saved with
    'rand_endpoints_' as a prefix to the file's name.

    Parameters
    ----------
    file : Path
        Path to a *.csv file containing data in the format of
        `DEFAULT_COLUMNS`.
    cam_ids : List[str]
        Cam IDs present in the dataset.
        Default is ["gp1", "gp2"]

    Returns
    -------
    None
    """
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


def replace_missing_rods(dataset: pd.DataFrame, cam1_id: str = "gp1",
                         cam2_id: str = "gp2") -> pd.DataFrame:
    """Fills missing data in 'seen_...' and '[xy][12]_...' columns.

    Replaces NaN values in columns of the format 'seen_...' and '[xy][12]_...',
    see `DEFAULT_COLUMNS` for more information.
    NaNs in 'seen_...' are replaced by `0`, NaNs in '[xy][12]_...' are replaced
    by `-1.`.

    Parameters
    ----------
    dataset : pd.DataFrame
        Dataset with the column format from `DEFAULT_COLUMNS`.
    cam1_id : str
        Default is "gp1".
    cam2_id : str
        Default is "gp2".

    Returns
    -------
    pd.DataFrame
    """
    cols_2d = [col for col in dataset.columns
               if cam1_id in col or cam2_id in col]
    cols_seen = [col for col in dataset.columns if "seen" in col]
    dataset[cols_2d] = dataset[cols_2d].fillna(-1.)
    dataset[cols_seen] = dataset[cols_seen].fillna(0)
    return dataset


def add_points(points: Dict[str, np.ndarray], data: pd.DataFrame,
               cam_id: str, frame: int):
    """Updates a dataframe with new rod endpoint data for one camera and frame.

    Parameters
    ----------
    points : Dict[str, np.ndarray]
        Rod endpoints in the format obtained from
        `utils.helper_funcs.rod_endpoints`.
    data : pd.DataFrame
        Dataframe for the rods to be saved in.
    cam_id : str
        ID/Name of the camera, that produced the image the rod endpoints were
        computed on.
    frame : int
        Frame number in the dataset.

    Returns
    -------
    pd.DataFrame
        Returns the updated `data` dataframe.
    """
    cols = [col for col in data.columns if cam_id in col]
    for color, v in points.items():
        if np.size(v) == 0:
            continue
        v = np.reshape(v, (len(v), -1))
        seen = np.ones((len(v), 1))
        to_df = np.concatenate((v, seen), axis=1)
        temp_df = pd.DataFrame(to_df, columns=cols)
        if len(data.loc[(data.frame == frame) & (data.color == color)]) == 0:
            temp_df["frame"] = frame
            temp_df["color"] = color
            temp_df["particle"] = np.arange(0, len(temp_df), dtype=int)
            data = pd.concat((data, temp_df))
        else:
            previous_data = data.loc[
                (data.frame == frame) & (data.color == color)]
            new_data = data.loc[
                (data.frame == frame) & (data.color == color)].fillna(temp_df)
            data.loc[(data.frame == frame) & (data.color == color)] = new_data
            if len(previous_data) < len(temp_df):
                temp_df["frame"] = frame
                temp_df["color"] = color
                temp_df["particle"] = np.arange(0, len(temp_df), dtype=int)
                idx_to_add = np.arange(len(previous_data), len(temp_df))
                data = pd.concat((data, temp_df.iloc[idx_to_add]))
    data = data.astype({"frame": 'int', "particle": 'int'})
    return data
