import os
import sys
import logging
from typing import List
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


def mat2csv(input_folders: str, output_file: str):
    pass


def csv2mat(input_file: str, output_folders: List[str]):
    pass


def csv_extract_colors(input_file: str) -> List[str]:
    """Extract the rod position data into one file per color.

    This functions saves a new file for each color that is present in the given
    data. The original file name is thereby extended by the name of the
    respective color, i.e. "old_name_foundcolor.csv"

    Parameters
    ----------
    input_file : str
        *.csv file that contains rod position data for multiple colors, i.e.
        has a column "color".

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
        colored_data = colored_data.astype({"frame": 'int', "particle": 'int'})
        colored_data.to_csv(new_file, sep=",")
        written.append(new_file)
    return written


def csv_combine(input_files: List[str], output_file: str = "rods_df.csv") \
        -> str:
    """Concatenates multiple *.csv files to a single one.

    The given input files are combined into a single one. The function does not
    distinguish what data it is given and might fail, if it is not rod position
    data in all given files. The function does NOT check for duplicates.

    Parameters
    ----------
    input_files : List[str]
        *.csv files that contains rod position data.
    output_file : str, optional
        Path to the output file. If this is just a file name without a path,
        the parent directory of the first input file is taken as the intended
        file location.
        By default "rods_df.csv"

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
            output_file = os.path.join(os.path.dirname(input_files[0]),
                                       output_file)
        combined.reset_index(drop=True, inplace=True)
        combined.to_csv(output_file, sep=",")
        written = output_file
    return written


def csv_split_by_frames(input_file: str, cut_frames: List[int]) -> List[str]:
    """Splits the rod data at the given frames.

    Splits the given *.csv file into individual files at the given frame
    numbers.
    Example:
    The data has frames from 0 to 33.
    cut_frames = [15, 20, 25] -> out_0_14.csv, out_15_19.csv, out_20_24.csv,
                                 out_25_33.csv

    Parameters
    ----------
    input_file : str
        Path to a *.csv file containing rod position data.
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
    for i in range(0, len(cut_frames)+1):
        if (i-1) >= 0:
            next_min = cut_frames[i-1]
        else:
            next_min = data_main.frame.min()
        try:
            next_max = cut_frames[i]
        except IndexError:
            next_max = data_main.frame.max() + 1

        next_slice = data_main.loc[
            (data_main.frame >= next_min) & (data_main.frame < next_max)]
        if len(next_slice) == 0:
            continue
        next_slice.reset_index(drop=True, inplace=True)
        new_path = base_path + f"_{next_min}_{next_max-1}.csv"
        next_slice.to_csv(new_path, sep=",")
        written.append(new_path)
    return written


if __name__ == "__main__":
    pass
