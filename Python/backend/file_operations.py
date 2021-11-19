import os
import re
from typing import Tuple, List
import shutil
import pandas as pd

COLOR_DATA_REGEX = re.compile('rods_df_\w+\.csv')


def get_images(read_dir: str) -> Tuple[List[str], List[int]]:
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
    for idx, f in enumerate(os.listdir(read_dir)):
        f_id = os.path.splitext(f)[0]
        fpath = os.path.join(read_dir, f)
        if os.path.isfile(fpath) and f.endswith(('.png', '.jpg',
                                                 '.jpeg')):
            # Add all image files to a list
            files.append(fpath)
            file_ids.append(int(f_id))
    return files, file_ids


def get_color_data(read_dir: str, write_dir: str) -> \
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
    for file in os.listdir(read_dir):
        whole_path = os.path.join(read_dir, file)
        if not os.path.isfile(whole_path):
            continue
        if re.fullmatch(COLOR_DATA_REGEX, file) is not None:
            found_color = os.path.splitext(file)[0].split("_")[-1]
            found_colors.append(found_color)
            # Copy file to temporary storage
            src_file = os.path.join(read_dir, file)
            dst_file = os.path.join(write_dir, file)
            shutil.copy2(src=src_file, dst=dst_file)

            data_chunk = pd.read_csv(src_file, index_col=0)
            data_chunk["color"] = found_color
            if dataset is None:
                dataset = data_chunk.copy()
            else:
                dataset = pd.concat([dataset, data_chunk])
    return dataset, found_colors


def folder_has_data(path) -> bool:
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
    if not os.path.exists(path):
        return False
    if not os.path.isdir(path):
        raise NotADirectoryError
    for file in os.listdir(path):
        whole_path = os.path.join(path, file)
        if not os.path.isfile(whole_path):
            continue
        if re.fullmatch(COLOR_DATA_REGEX, file) is not None:
            return True
    return False
