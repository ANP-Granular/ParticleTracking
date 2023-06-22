#  Copyright (c) 2023 Adrian Niemann Dmitry Puzyrev
#
#  This file is part of ParticleDetection.
#  ParticleDetection is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  ParticleDetection is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with ParticleDetection.  If not, see <http://www.gnu.org/licenses/>.

import shutil
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import ParticleDetection.utils.data_conversions as dc
from conftest import EXAMPLES as csv_files


def test_csv_extract_colors(tmp_path: Path):
    test_colors = {"black", "green"}
    base_name = "test"
    test_file = tmp_path / (base_name + ".csv")
    test_data = pd.DataFrame()
    for color in test_colors:
        tmp_data = pd.read_csv(csv_files.joinpath(f"rods_df_{color}.csv"))
        tmp_data["color"] = color
        test_data = pd.concat([test_data, tmp_data])
    test_data.reset_index(drop=True, inplace=True)
    test_data.to_csv(test_file)

    result = dc.csv_extract_colors(test_file)
    assert len(result) == 2
    saved_colors = set()
    for file in result:
        result_frame = pd.read_csv(file, index_col=0)
        assert len(result_frame["color"].unique()) == 1
        color = result_frame["color"].unique()[0]
        assert color in test_colors and color not in saved_colors
        saved_colors.add(color)

        original = pd.read_csv(csv_files.joinpath(f"rods_df_{color}.csv"))
        result_frame.drop(columns=["color"], inplace=True)
        pd.testing.assert_frame_equal(original, result_frame)


def test_csv_combine(tmp_path: Path):
    test_colors = {"black", "green"}
    test_files = [csv_files / (f"rods_df_{color}.csv")
                  for color in test_colors]
    output_file = tmp_path / "test.csv"
    result = dc.csv_combine(test_files, str(output_file))
    saved_file = pd.read_csv(output_file, index_col=0)
    assert result == str(output_file.resolve())
    lens = [len(pd.read_csv(file)) for file in test_files]
    assert np.sum(lens) == len(saved_file)


def test_csv_combine_unknown_files(tmp_path: Path):
    test_colors = {"test0", "test1"}
    test_files = [csv_files.joinpath(f"rods_df_{color}.csv")
                  for color in test_colors]
    output_file = tmp_path / "test.csv"
    result = dc.csv_combine(test_files, str(output_file))
    assert result == ""
    assert output_file.exists() is False


@pytest.mark.parametrize("cut_frames", ([501], [502, 504, 510], []))
def test_csv_split_by_frames(tmp_path: Path, cut_frames: list):
    test_file = tmp_path / "rods_df_black.csv"
    shutil.copy(csv_files.joinpath("rods_df_black.csv"), test_file)
    result = dc.csv_split_by_frames(test_file, cut_frames)
    assert len(result) == len(cut_frames) + 1
    original = pd.read_csv(test_file, index_col=0)
    original_frames = original.frame.unique()
    for idx, file in enumerate(result):
        result_data = pd.read_csv(file, index_col=0)
        result_frames = result_data.frame.unique()
        assert np.isin(result_frames, original_frames).all()
        if idx == 0:
            assert result_frames.min() == original_frames.min()
        elif idx < len(cut_frames):
            assert result_frames.max() == cut_frames[idx] - 1
            assert result_frames.min() == cut_frames[idx - 1]
        else:
            assert result_frames.max() == original_frames.max()
