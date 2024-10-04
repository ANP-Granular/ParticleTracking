# Copyright (c) 2023-24 Adrian Niemann, Dmitry Puzyrev, and others
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
Collection of function to convert between different file formats used over the
course of the particle detection project, e.g. camera calibrations from MATLAB
to the now used json-format.

**Authors:**    Adrian Niemann (adrian.niemann@ovgu.de)\n
**Date:**       02.11.2022

"""
import json
import logging
import os
from pathlib import Path
from typing import Iterable, List

import numpy as np
import pandas as pd
import scipy.io as sio

import ParticleDetection.utils.data_loading as dl
import ParticleDetection.utils.datasets as ds

_logger = logging.getLogger(__name__)


def txt2mat(
    input_folder: Path,
    frames: Iterable[int],
    expected_rods: int,
    cam1_id: str = "gp1",
    cam2_id: str = "gp2",
    output_folder: Path = None,
) -> None:
    """Read rod position data in old ``*.txt`` format and save it in ``*.mat``
    format.

    Converts the rod positions from the ``*.txt`` format to ``*.mat`` format
    assuming, that only one color is saved in the given input folder.
    The converted files are then saved to two subfolders of the output folder,
    named after ``cam1_id`` and ``cam2_id``.

    Parameters
    ----------
    input_folder : Path
        Folder containing the 3D data in txt-files of format:
        ``{frame:05d}.txt``
    frames : Iterable[int]
        Frame numbers found in the input folder and intended to be converted.
    expected_rods : int
        Number of rods to expect in one frame.
    cam1_id : str, optional
        First camera's identifier in the given dataset.
        By default ``"gp1"``.
    cam2_id : str, optional
        Second camera's identifier in the given dataset.
        By default ``"gp2"``.
    output_folder : Path, optional
        Parent folder of the two output folders.
        By default set to the parent folder of the input folder.
    """
    col_names = [
        col.format(id1=cam1_id, id2=cam2_id)
        for col in ds.DEFAULT_COLUMNS
        if "seen" not in col
    ]
    data_format = str(input_folder.resolve()) + "/{:05d}.txt"
    if output_folder is None:
        output_folder = input_folder.parent
    output_format = str(output_folder.resolve()) + "/{cam:s}/{frame:05d}.mat"
    dt = np.dtype([("Point1", np.float, (2,)), ("Point2", np.float, (2,))])

    data = dl.load_positions_from_txt(data_format, col_names, frames)
    rods_cam1 = data[
        [f"x1_{cam1_id}", f"y1_{cam1_id}", f"x2_{cam1_id}", f"y2_{cam1_id}"]
    ].to_numpy()
    rods_cam2 = data[
        [f"x1_{cam2_id}", f"y1_{cam2_id}", f"x2_{cam2_id}", f"y2_{cam2_id}"]
    ].to_numpy()
    rods_cam1 = rods_cam1.reshape((-1, expected_rods, 4))
    rods_cam2 = rods_cam2.reshape((-1, expected_rods, 4))

    # Create output directories
    test_out = output_format.format(cam=cam1_id, frame=0)
    Path(test_out).parent.mkdir(parents=True, exist_ok=True)
    test_out = output_format.format(cam=cam2_id, frame=0)
    Path(test_out).parent.mkdir(parents=True, exist_ok=True)

    for r_c1, r_c2, fr in zip(rods_cam1, rods_cam2, frames):
        arr = np.zeros((expected_rods,), dtype=dt)
        arr[:]["Point1"] = r_c1[:, 0:2]
        arr[:]["Point2"] = r_c1[:, 2:]
        out_file1 = output_format.format(cam=cam1_id, frame=fr)
        sio.savemat(out_file1, {"rod_data_links": arr})
        arr2 = np.zeros((expected_rods,), dtype=dt)
        arr2[:]["Point1"] = r_c2[:, 0:2]
        arr2[:]["Point2"] = r_c2[:, 2:]
        out_file2 = output_format.format(cam=cam2_id, frame=fr)
        sio.savemat(out_file2, {"rod_data_links": arr2})


def csv_extract_colors(input_file: str) -> List[str]:
    """Extract the rod position data into one file per color.

    This functions saves a new file for each color that is present in the given
    data. The original file name is thereby extended by the name of the
    respective color, i.e. ``old_name_foundcolor.csv``.

    Parameters
    ----------
    input_file : str
        ``*.csv`` file that contains rod position data for multiple colors,
        i.e. has a column ``"color"``.

    Returns
    -------
    List[str]
        Returns a list of paths to the files, that were written.
    """
    data_main = pd.read_csv(input_file, sep=",", index_col=0)
    colors = data_main.color.unique()
    file_base = os.path.splitext(input_file)[0]
    written = []
    for color in colors:
        new_file = file_base + f"_{color}.csv"
        colored_data = data_main.loc[data_main.color == color]
        colored_data.reset_index(drop=True, inplace=True)
        colored_data = colored_data.astype({"frame": "int", "particle": "int"})
        colored_data.to_csv(new_file, sep=",")
        written.append(new_file)
    return written


def csv_combine(
    input_files: List[str], output_file: str = "rods_df.csv"
) -> str:
    """Concatenates multiple ``*.csv`` files to a single one.

    The given input files are combined into a single one. The function does not
    distinguish what data it is given and might fail, if it is not rod position
    data in all given files. The function does NOT check for duplicates.

    Parameters
    ----------
    input_files : List[str]
        ``*.csv`` files that contains rod position data.
    output_file : str, optional
        Path to the output file. If this is just a file name without a path,
        the parent directory of the first input file is taken as the intended
        file location.
        By default ``"rods_df.csv"``.

    Returns
    -------
    str
        Path to the written, combined file. The string is empty, if nothing has
        been written.
    """
    combined = pd.DataFrame()
    written = ""
    for file in input_files:
        if not os.path.exists(file):
            _logger.warning(f"The file {file} does not exist.")
            continue
        new_data = pd.read_csv(file, sep=",", index_col=0)
        combined = pd.concat([combined, new_data])
    if len(combined) > 0:
        if not os.path.dirname(output_file):
            output_file = os.path.join(
                os.path.dirname(input_files[0]), output_file
            )
        combined.reset_index(drop=True, inplace=True)
        combined.to_csv(output_file, sep=",")
        written = output_file
    return written


def csv_split_by_frames(input_file: str, cut_frames: List[int]) -> List[str]:
    """Splits the rod data at the given frames.

    Splits the given ``*.csv`` file into individual files at the given frame
    numbers.

    Example:\n
    The data has frames from 0 to 33.\n
    ``cut_frames = [15, 20, 25]``\n
    -> ``out_0_14.csv``, ``out_15_19.csv``, ``out_20_24.csv``,
    ``out_25_33.csv``

    Parameters
    ----------
    input_file : str
        Path to a ``*.csv file`` containing rod position data.
    cut_frames : List[int]
        Frames at which to partition the data. All frames in the original data
        are perserved.
        The lower bound is inclusive, while the upper bound is exclusive.

    Returns
    -------
    List[str]
        List of paths to the written files. This list is empty, if no files
        were written.
    """
    written = []
    data_main = pd.read_csv(input_file, sep=",", index_col=0)
    base_path = os.path.splitext(input_file)[0]
    for i in range(0, len(cut_frames) + 1):
        if (i - 1) >= 0:
            next_min = cut_frames[i - 1]
        else:
            next_min = data_main.frame.min()
        try:
            next_max = cut_frames[i]
        except IndexError:
            next_max = data_main.frame.max() + 1

        next_slice = data_main.loc[
            (data_main.frame >= next_min) & (data_main.frame < next_max)
        ]
        if len(next_slice) == 0:
            continue
        next_slice.reset_index(drop=True, inplace=True)
        new_path = base_path + f"_{next_min}_{next_max - 1}.csv"
        next_slice.to_csv(new_path, sep=",")
        written.append(new_path)
    return written


def convert_txt_config(folder: Path):
    """Convert camera calibrations from MATLAB's ``*.txt``/``*.mat`` to
    ``*.json`` format.

    This function converts a stereo camera calibration saved by MATLAB to
    ``*.txt`` and ``*.mat`` files into the ``*.json`` format used by functions
    in this package.

    The resulting files are saved as ``converted.json`` and
    ``world_transformations_converted.json``.

    Parameters
    ----------
    folder : Path
        Folder containing the stereo calibration output, consisting of the
        following files: \n
        ``c.txt``, ``f.txt``, ``c2.txt``, ``f2.txt``, ``kc.txt``, ``kc2.txt``,
        ``R.txt``, ``transvek.txt``, ``transformations.mat``
    """
    cm1 = np.zeros((3, 3))
    cm1[[0, 1], [2, 2]] = np.loadtxt(folder / "c.txt")
    cm1[[0, 1], [0, 1]] = np.loadtxt(folder / "f.txt")
    cm1[2, 2] = 1.0
    cm2 = np.zeros((3, 3))
    cm2[[0, 1], [2, 2]] = np.loadtxt(folder / "c2.txt")
    cm2[[0, 1], [0, 1]] = np.loadtxt(folder / "f2.txt")
    cm2[2, 2] = 1.0

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

    trafos = sio.loadmat(folder / "transformations.mat")["transformations"][0][
        0
    ]
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
