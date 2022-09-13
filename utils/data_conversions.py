import os
from typing import List
import numpy as np
import pandas as pd

def mat2csv(input_folders: str, output_file: str):
    pass

def csv2mat(input_file: str, output_folders: List[str]):
    pass

def csv_extract_colors(input_file: str):
    """Extract the rod position data into one file per color.

    This functions saves a new file for each color that is present in the given
    data. The original file name is thereby extended by the name of the 
    respective color, i.e. "old_name_foundcolor.csv"

    Parameters
    ----------
    input_file : str
        *.csv file that contains rod position data for multiple colors, i.e. 
        has a column "color".
    """
    data_main = pd.read_csv(input_file, sep=",")
    colors = data_main.color.unique()
    file_base = os.path.splitext(input_file)[0]
    for color in colors:
        new_file = file_base + f"_{color}.csv"
        colored_data = data_main.loc[data_main.color==color]
        colored_data.to_csv(new_file, sep=",")
    return

def csv_combine_colors(input_files: List[str]):
    pass

if __name__ == "__main__":
    csv_extract_colors("/home/niemann/Documents/ParticleDetection/experiments/MityaData/testrods_df.csv")