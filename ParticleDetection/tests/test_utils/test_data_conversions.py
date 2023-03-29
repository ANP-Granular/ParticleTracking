import sys
import shutil
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import ParticleDetection.utils.data_conversions as dc
if sys.version_info < (3, 9):
    # importlib.resources either doesn't exist or lacks the files()
    # function, so use the PyPI version:
    import importlib_resources
else:
    # importlib.resources has files(), so use that:
    import importlib.resources as importlib_resources
csv_files = importlib_resources.files(
    "RodTracker.resources.example_data.csv")


def test_csv_extract_colors(tmp_path: Path):
    test_colors = {"blue", "green", "red"}
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
    assert len(result) == 3
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
    test_colors = {"blue", "green", "red"}
    test_files = [csv_files.joinpath(f"rods_df_{color}.csv")
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


@pytest.mark.parametrize("cut_frames", ([501], [502, 512, 550], []))
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
