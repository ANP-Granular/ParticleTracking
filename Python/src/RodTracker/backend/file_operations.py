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

import pathlib
import re
from typing import Tuple, List
import shutil
import pandas as pd

COLOR_DATA_REGEX = re.compile('rods_df_\w+\.csv')               # noqa: W605


def get_images(read_dir: pathlib.Path) -> Tuple[List[pathlib.Path], List[int]]:
    """Reads image files from a directory.

    Checks all files for naming convention according to the selected file
    and generates the frame IDs from them.

    Parameters
    ----------
    read_dir : str
        Path to the directory to read image files from.

    Returns
    -------
    Tuple[List[str], List[int]]
        Full paths to the found image files and frame numbers extracted from
        the file names.
    """

    files = []
    file_ids = []
    for f in read_dir.iterdir():
        if f.is_file() and f.suffix in ['.png', '.jpg', '.jpeg']:
            # Add all image files to a list
            files.append(f)
            file_ids.append(int(f.stem))
    return files, file_ids


def get_color_data(read_dir: pathlib.Path, write_dir: pathlib.Path) -> \
        Tuple[pd.DataFrame, List[str]]:
    """Reads rod data files from a directory.

    Checks all *.csv files for the rod data naming convention, loads and
    concatenates them, and extracts the corresponding color from the file
    names. The matching files are copied to the given write directory.

    Parameters
    ----------
    read_dir : str
        Path to the directory to read position data files from.
    write_dir : str
        Path to the temporary directory to write copies of the found files to.

    Returns
    -------
    Tuple[DataFrame, List[str]]
        Concatenated dataset and list of all found colors.
    """
    found_colors = []
    dataset = None
    for src_file in read_dir.iterdir():
        if not src_file.is_file():
            continue
        if re.fullmatch(COLOR_DATA_REGEX, src_file.name) is not None:
            found_color = src_file.stem.split("_")[-1]
            found_colors.append(found_color)
            # Copy file to temporary storage
            dst_file = write_dir / src_file.name
            shutil.copy2(src=src_file, dst=dst_file)

            data_chunk = pd.read_csv(src_file, index_col=0)
            data_chunk["color"] = found_color
            if dataset is None:
                dataset = data_chunk.copy()
            else:
                dataset = pd.concat([dataset, data_chunk])
    return dataset, found_colors


def folder_has_data(path: pathlib.Path) -> bool:
    """Checks a folder for file(s) that match the rod position data naming.

    Parameters
    ----------
    path : str
        Folder path that shall be checked for files matching the pattern in
        `file_regex`.

    Returns
    -------
    bool
        True, if at least 1 file matching the pattern was found.
        False, if no file was found or the folder does not exist.

    Raises
    ------
    NotADirectoryError
        Is raised if the given path exists but is not a directory.
    """
    if not path.exists():
        return False
    if not path.is_dir():
        raise NotADirectoryError
    for file in path.iterdir():
        if not file.is_file():
            continue
        if re.fullmatch(COLOR_DATA_REGEX, file.name) is not None:
            return True
    return False
