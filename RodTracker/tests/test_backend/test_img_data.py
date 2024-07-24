# Copyright (c) 2023-24 Adrian Niemann, Dmitry Puzyrev, and others
#
# This file is part of RodTracker.
# RodTracker is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RodTracker is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RodTracker. If not, see <http://www.gnu.org/licenses/>.

import itertools
import pathlib
import random
import shutil

import importlib_resources
import pytest
from PyQt5 import QtWidgets
from pytest import MonkeyPatch
from pytestqt.qtbot import QtBot

from RodTracker.backend import img_data

EX_DATA = importlib_resources.files("RodTracker.resources").joinpath(
    "example_data"
)


@pytest.fixture(scope="function")
def loaded_images() -> img_data.ImageData:
    img_manager = img_data.ImageData(3)
    img_manager.open_image_folder(EX_DATA / "images/gp3/0500.jpg")
    yield img_manager


class TestImageData:
    @pytest.mark.parametrize("folder", ["", EX_DATA / "images/gp3/0500.jpg"])
    def test_select_images(self, monkeypatch: MonkeyPatch, folder: str):
        def assertions(file_path):
            assert type(file_path) is pathlib.Path
            assert file_path.exists()
            assert file_path.is_file()

        # FIXME: getOpenFileName is not used anymore
        with monkeypatch.context() as mp:
            mp.setattr(
                QtWidgets.QFileDialog, "getOpenFileName", lambda *args: folder
            )
            mp.setattr(img_data.ImageData, "open_image_folder", assertions)

    @pytest.mark.parametrize(
        "file, frame",
        [
            (EX_DATA / "images/gp3/0001.jpg", 1),
            (EX_DATA / "images/gp3/0506.jpg", 506),
        ],
    )
    def test_open_image_folder(
        self,
        monkeypatch: MonkeyPatch,
        qtbot: QtBot,
        loaded_images: img_data.ImageData,
        file: pathlib.Path,
        frame: int,
    ):
        if not file.exists():
            activated_info = False

            def mb_info(*args):
                nonlocal activated_info
                activated_info = True

            with monkeypatch.context() as mp:
                mp.setattr(QtWidgets.QMessageBox, "information", mb_info)
                loaded_images.open_image_folder(file)
            assert activated_info is True
            return

        def check_data_loaded(*args):
            files, id, folder = args
            assert files == 25
            assert id == str(file.parent.stem)
            assert folder == file.parent
            return True

        def check_next_img_ids(*args):
            loaded_frame, idx = args
            assert loaded_frame == loaded_images.frames[idx] == frame
            assert f"{loaded_frame:04d}" in str(file)
            return True

        signals = [loaded_images.data_loaded, loaded_images.next_img[int, int]]
        callbacks = [check_data_loaded, check_next_img_ids]
        with qtbot.wait_signals(signals=signals, check_params_cbs=callbacks):
            loaded_images.open_image_folder(file)
        assert sorted(loaded_images.files) == loaded_images.files
        assert sorted(loaded_images.frames) == loaded_images.frames

    def test_image_at(self, loaded_images: img_data.ImageData, qtbot: QtBot):
        loaded_images.frame_idx = random.randrange(len(loaded_images.frames))
        chosen_idx = random.randrange(len(loaded_images.frames))
        with qtbot.wait_signal(loaded_images.next_img[int, int]) as blocker:
            loaded_images.image_at(chosen_idx)
        assert blocker.args[1] == chosen_idx

    def test_image(self, loaded_images: img_data.ImageData, qtbot: QtBot):
        loaded_images.frame_idx = random.randrange(len(loaded_images.frames))
        chosen_frame = random.choice(loaded_images.frames)
        with qtbot.wait_signal(loaded_images.next_img[int, int]) as blocker:
            loaded_images.image(chosen_frame)
        assert blocker.args[0] == chosen_frame

    @pytest.mark.parametrize(
        "start,direction", list(itertools.product([0, 6, 24], [-1, 1, -3, 3]))
    )
    def test_next_image(
        self,
        loaded_images: img_data.ImageData,
        qtbot: QtBot,
        start: int,
        direction: int,
    ):
        loaded_images.frame_idx = start
        with qtbot.wait_signal(loaded_images.next_img[int, int]) as blocker:
            loaded_images.next_image(direction)

        expected_idx = start + direction
        if expected_idx >= len(loaded_images.frames) - 1:
            expected_idx -= len(loaded_images.frames)
        assert blocker.args[0] == loaded_images.frames[expected_idx]


def test_get_images():
    files, file_ids = img_data.get_images(EX_DATA / "images/gp3")
    assert len(files) == len(file_ids) == 25
    assert sorted(file_ids) == [*list(range(500, 520)), *list(range(696, 701))]


def test_get_images_avoid_wrong():
    files, file_ids = img_data.get_images(EX_DATA / "csv")
    assert len(files) == len(file_ids) == 0


@pytest.mark.parametrize("ending", [".jpg", ".png", ".jpeg"])
def test_get_images_file_types(tmp_path: pathlib.Path, ending):
    dir = EX_DATA / "images/gp3"
    test_ids = [500, 505, 700]
    test_files = [f"{id:04d}.jpg" for id in test_ids]
    dst_files = []
    for f in test_files:
        dst_f = pathlib.Path(f).stem + ending
        dst_files.append(tmp_path.joinpath(dst_f))
        shutil.copy2(dir.joinpath(f), tmp_path.joinpath(dst_f))
    files, file_ids = img_data.get_images(tmp_path)
    assert len(files) == len(test_files)
    assert len(file_ids) == len(test_ids)
    assert sorted(file_ids) == test_ids
    assert sorted(files) == dst_files
