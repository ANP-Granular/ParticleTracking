import sys
import shutil
import pathlib
import pytest
if sys.version_info < (3, 9):
    # importlib.resources either doesn't exist or lacks the files()
    # function, so use the PyPI version:
    import importlib_resources
else:
    # importlib.resources has files(), so use that:
    import importlib.resources as importlib_resources
import RodTracker.backend.file_operations as f_ops


class TestFolderHasData:
    def test_recognizes_files(self):
        dir = importlib_resources.files("RodTracker.resources.example_data")
        assert f_ops.folder_has_data(dir.joinpath("csv"))

    def test_avoids_wrong_files(self):
        dir = importlib_resources.files(
            "RodTracker.resources.example_data")
        assert not f_ops.folder_has_data(dir.joinpath("images"))

    def test_raises_on_file(self):
        dir = importlib_resources.files(
            "RodTracker.resources.example_data.csv")
        file_path = dir.joinpath("rods_df_black.csv")
        with pytest.raises(NotADirectoryError):
            f_ops.folder_has_data(file_path)

    def test_empty_dir(self, tmp_path: pathlib.Path):
        assert not f_ops.folder_has_data(tmp_path)

    def test_non_existent(self):
        dir = importlib_resources.files(
            "RodTracker.resources").joinpath("test")
        assert not f_ops.folder_has_data(dir)


class TestGetImages:
    def test_empty_folder(self, tmp_path: pathlib.Path):
        files, file_ids = f_ops.get_images(tmp_path)
        assert files == []
        assert file_ids == []

    @pytest.mark.parametrize("name", ["text.txt", "0501.txt", "0501.pdf"])
    def test_avoids_wrong_files(self, tmp_path: pathlib.Path, name: str):
        dir = importlib_resources.files(
            "RodTracker.resources.example_data.images.gp3")
        test_ids = [500, 505, 700]
        test_files = [f"{id:04d}.jpg" for id in test_ids]
        dst_files = []
        for f in test_files:
            dst_files.append(tmp_path.joinpath(f))
            shutil.copy2(dir.joinpath(f), tmp_path.joinpath(f))

        # Create empty "bait" file
        open(tmp_path.joinpath(name), "w").close()

        files, file_ids = f_ops.get_images(tmp_path)
        assert len(files) == len(test_files)
        assert len(file_ids) == len(test_ids)
        assert sorted(files) == sorted(dst_files)
        assert sorted(file_ids) == sorted(test_ids)

    @pytest.mark.parametrize("ending", [".jpg", ".png", ".jpeg"])
    def test_recognizes_files(self, tmp_path: pathlib.Path, ending: str):
        dir = importlib_resources.files(
            "RodTracker.resources.example_data.images.gp3")
        test_ids = [500, 505, 700]
        test_files = [f"{id:04d}.jpg" for id in test_ids]
        dst_files = []
        for f in test_files:
            dst_f = pathlib.Path(f).stem + ending
            dst_files.append(tmp_path.joinpath(dst_f))
            shutil.copy2(dir.joinpath(f), tmp_path.joinpath(dst_f))
        files, file_ids = f_ops.get_images(tmp_path)
        assert len(files) == len(test_files)
        assert len(file_ids) == len(test_ids)
        assert sorted(file_ids) == test_ids
        assert sorted(files) == dst_files


class TestGetColorData:
    def test_empty_folder(self, tmp_path: pathlib.Path):
        dst_path = dst_path = pathlib.Path(tmp_path).joinpath("out")
        dst_path.mkdir()
        data, colors = f_ops.get_color_data(tmp_path, dst_path)
        assert data is None
        assert colors == []

    def test_recognizes_files(self, tmp_path: pathlib.Path):
        dir = importlib_resources.files(
            "RodTracker.resources.example_data.csv")
        test_colors = ["blue", "green", "red"]
        read_data = []
        for i in range(1, len(test_colors) + 1):
            dst_path = tmp_path.joinpath(f"out{i}")
            dst_path.mkdir()
            tmp_colors = test_colors[:i]
            test_files = [f"rods_df_{color}.csv" for color in tmp_colors]
            for f in test_files:
                shutil.copy2(dir.joinpath(f), tmp_path.joinpath(f))
            data, colors = f_ops.get_color_data(tmp_path, dst_path)
            read_data.append(data.reset_index(drop=True))
            assert sorted(colors) == sorted(tmp_colors)
            assert data is not None
            assert sorted(data["color"].unique()) == sorted(tmp_colors)

        for i in range(1, len(read_data)):
            tmp_colors = test_colors[:i]
            for color in tmp_colors:
                tmp_small = read_data[i - 1].loc[
                    read_data[i - 1]["color"] == color].reset_index(drop=True)
                tmp_big = read_data[i].loc[
                    read_data[i]["color"] == color].reset_index(drop=True)
                assert tmp_small.isin(tmp_big).all().all()

    @pytest.mark.parametrize("name", ["test.csv", "test.txt", "rods_blue.csv"])
    def test_avoids_wrong_files(self, tmp_path: pathlib.Path, name: str):
        dst_path = tmp_path.joinpath("out")
        dst_path.mkdir()

        dir = importlib_resources.files(
            "RodTracker.resources.example_data.csv")
        test_colors = ["blue", "green", "red"]
        test_files = [f"rods_df_{color}.csv" for color in test_colors]
        for f in test_files:
            shutil.copy2(dir.joinpath(f), tmp_path.joinpath(f))

        # Create empty "bait" file
        open(tmp_path.joinpath(name), "w").close()

        data, colors = f_ops.get_color_data(tmp_path, dst_path)
        assert sorted(colors) == sorted(test_colors)
        assert data is not None
        assert sorted(data["color"].unique()) == sorted(test_colors)
