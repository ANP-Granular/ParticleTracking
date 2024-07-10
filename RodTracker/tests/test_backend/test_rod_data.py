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

import logging
import random
import shutil
from pathlib import Path

import importlib_resources
import pandas as pd
import pytest
from conftest import load_rod_data
from PyQt5 import QtWidgets
from pytest import MonkeyPatch
from pytestqt.qtbot import QtBot

import RodTracker.ui.dialogs as dialogs
from RodTracker.backend import logger as lg
from RodTracker.backend import rod_data
from RodTracker.backend.rod_data import RodData

_logger = logging.getLogger()


@pytest.fixture(scope="function")
def rod_manager() -> RodData:
    manager = RodData()
    folder = importlib_resources.files(
        "RodTracker.resources.example_data"
    ).joinpath("csv")
    manager.open_rod_folder(folder)
    yield manager
    rod_data.rod_data = None
    rod_data.POSITION_SCALING = 1.0


class TestRodData:
    @pytest.mark.parametrize("show", [False, True])
    def test_show_2D_setter(
        self, qtbot: QtBot, rod_manager: RodData, show: bool
    ):
        rod_manager.frame = 500
        with qtbot.assert_not_emitted(rod_manager.data_3d):
            if show:
                with qtbot.wait_signal(rod_manager.data_2d):
                    rod_manager.show_2D = show
            else:
                with qtbot.assert_not_emitted(rod_manager.data_2d):
                    rod_manager.show_2D = show

    @pytest.mark.parametrize("show", [False, True])
    def test_show_3D_setter(
        self, qtbot: QtBot, rod_manager: RodData, show: bool
    ):
        rod_manager.frame = 500
        with qtbot.assert_not_emitted(rod_manager.data_2d):
            if show:
                with qtbot.wait_signal(rod_manager.data_3d):
                    rod_manager.show_3D = show
            else:
                with qtbot.assert_not_emitted(rod_manager.data_3d):
                    rod_manager.show_3D = show

    @pytest.mark.parametrize(
        "folders,abort,retries",
        [
            (
                [
                    "",
                    importlib_resources.files(
                        "RodTracker.resources.example_data"
                    ).joinpath("images"),
                ],
                True,
                1,
            ),
            (
                [
                    "",
                    importlib_resources.files(
                        "RodTracker.resources.example_data"
                    ).joinpath("csv"),
                ],
                False,
                0,
            ),
        ],
    )
    def test_select_rods(
        self,
        qtbot: QtBot,
        monkeypatch: MonkeyPatch,
        rod_manager: RodData,
        folders: list,
        abort: bool,
        retries: int,
    ):
        def assertions(chosen_folder):
            assert issubclass(type(chosen_folder), Path)
            assert chosen_folder.is_dir()
            return True

        entered = 0

        def mb_exec_replacement(*args, **kwargs):
            nonlocal entered
            entered += 1
            if abort:
                return QtWidgets.QMessageBox.Cancel

        for folder in folders:
            with monkeypatch.context() as mp:
                mp.setattr(
                    dialogs,
                    "select_data_folder",
                    lambda *args, **kwargs: (
                        Path(folder).resolve() if folder != "" else None
                    ),
                )
                mp.setattr(QtWidgets.QMessageBox, "exec", mb_exec_replacement)
                mp.setattr(rod_manager, "open_rod_folder", assertions)
                prev_retries = entered
                rod_manager.select_rods()
                if folder == "":
                    assert entered == prev_retries
        assert entered == retries

    def test_open_rod_folder(self, qtbot: QtBot, tmp_path: Path):
        chosen_folder = tmp_path / "test"
        chosen_folder.mkdir(exist_ok=True)
        ex_folder = importlib_resources.files(
            "RodTracker.resources.example_data.csv"
        )
        ex_file = "rods_df_black.csv"
        shutil.copy2(
            ex_folder.joinpath(ex_file), chosen_folder.joinpath(ex_file)
        )
        manager = RodData()
        with qtbot.wait_signals(
            [manager.data_loaded[int, int, list], manager.seen_loaded],
        ) as bl_outer:
            # This had to be nested, as otherwise only one data_loaded signal
            # was detected (pytest-qt: 4.2.0)
            with qtbot.wait_signal(
                manager.data_loaded[Path, Path, list]
            ) as bl_inner:
                manager.open_rod_folder(chosen_folder)
        ret_dl = bl_outer.all_signals_and_args[0].args
        ret_sl = bl_outer.all_signals_and_args[1].args

        assert ret_dl[0] == 500
        assert ret_dl[1] == 550
        assert ret_dl[2] == [
            "black",
        ]

        assert list(ret_sl[0].keys()) == list(range(500, 551))
        assert ret_sl[1] == ["gp3", "gp4"]

        assert bl_inner.args[0] == chosen_folder
        assert bl_inner.args[1] == Path(str(chosen_folder) + "_corrected")

        assert len(manager.cols_2D) == 12
        assert len(manager.cols_3D) == 9

    @pytest.mark.parametrize(
        "decision,expected_return",
        [
            (QtWidgets.QMessageBox.Yes, True),
            (QtWidgets.QMessageBox.No, True),
            (QtWidgets.QMessageBox.Abort, False),
        ],
    )
    def test_open_folder_corrected(
        self,
        qtbot: QtBot,
        monkeypatch: MonkeyPatch,
        tmp_path: Path,
        rod_manager: RodData,
        decision: QtWidgets.QMessageBox.StandardButton,
        expected_return: bool,
    ):
        chosen_folder = tmp_path / "test"
        corrected_folder = tmp_path / "test_corrected"
        chosen_folder.mkdir(exist_ok=True)
        corrected_folder.mkdir(exist_ok=True)

        ex_folder = importlib_resources.files(
            "RodTracker.resources.example_data.csv"
        )
        ex_file = "rods_df_black.csv"
        shutil.copy2(
            ex_folder.joinpath(ex_file), chosen_folder.joinpath(ex_file)
        )
        shutil.copy2(
            ex_folder.joinpath(ex_file), corrected_folder.joinpath(ex_file)
        )
        monkeypatch.setattr(
            QtWidgets.QMessageBox, "exec", lambda *args, **kwargs: decision
        )
        result = rod_manager.open_rod_folder(chosen_folder)
        if decision == QtWidgets.QMessageBox.Yes:
            assert rod_manager._allow_overwrite is True
            assert rod_manager.folder == corrected_folder
        elif decision == QtWidgets.QMessageBox.No:
            assert rod_manager.folder == chosen_folder
            assert rod_manager._allow_overwrite is False
        else:
            assert rod_manager._allow_overwrite is False
        assert result == expected_return

    @pytest.mark.parametrize("subfolder", ["", "missing"])
    def test_save_changes(
        self,
        qtbot: QtBot,
        tmp_path: Path,
        rod_manager: RodData,
        subfolder: str,
    ):
        test_folder = tmp_path / subfolder
        rod_manager.out_folder = test_folder
        with qtbot.wait_signal(rod_manager.saved):
            rod_manager.save_changes()
        assert (
            len([file for file in test_folder.iterdir() if file.is_file()])
            == 8
        )

    @pytest.mark.parametrize("overwrite", [True, False])
    def test_save_overwrite(
        self,
        qtbot: QtBot,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        rod_manager: RodData,
        overwrite: bool,
    ):
        rod_manager.folder = tmp_path
        rod_manager.out_folder = tmp_path
        rod_manager._allow_overwrite = False

        def msg_clicked_btn(msg_box):
            return msg_box.buttons()[int(not overwrite)]

        monkeypatch.setattr(QtWidgets.QMessageBox, "exec", lambda args: None)
        monkeypatch.setattr(
            QtWidgets.QMessageBox, "clickedButton", msg_clicked_btn
        )

        if overwrite:
            with qtbot.wait_signal(rod_manager.saved):
                rod_manager.save_changes()
            assert (
                len([file for file in tmp_path.iterdir() if file.is_file()])
                == 8
            )
        else:
            with qtbot.assert_not_emitted(rod_manager.saved):
                rod_manager.save_changes()
            assert (
                len([file for file in tmp_path.iterdir() if file.is_file()])
                == 0
            )

    def test_save_no_folder(
        self, monkeypatch: MonkeyPatch, tmp_path: Path, rod_manager: RodData
    ):
        monkeypatch.setattr(rod_manager, "out_folder", None)
        monkeypatch.setattr(
            QtWidgets.QFileDialog,
            "getExistingDirectory",
            lambda *args: str(tmp_path.absolute()),
        )
        rod_manager.save_changes()
        assert len([file for file in tmp_path.iterdir() if file.is_file()])

    def test_save_no_folder_abort(
        self, monkeypatch: MonkeyPatch, rod_manager: RodData
    ):
        monkeypatch.setattr(rod_manager, "out_folder", None)
        monkeypatch.setattr(
            QtWidgets.QFileDialog, "getExistingDirectory", lambda *args: ""
        )
        rod_manager.save_changes()
        assert rod_manager.out_folder is None

    def test_update_frame(self, qtbot: QtBot, rod_manager: RodData):
        frames = rod_data.rod_data.frame.unique()
        chosen_frame = random.choice(frames)
        with qtbot.wait_signals([rod_manager.data_2d, rod_manager.data_3d]):
            rod_manager.update_frame(
                chosen_frame, random.randrange(len(frames))
            )
        assert chosen_frame == rod_manager.frame

    @pytest.mark.parametrize("color", [None, "black", "stuff"])
    def test_update_color_2D(
        self, qtbot: QtBot, rod_manager: RodData, color: str
    ):
        rod_manager.frame = 500
        with qtbot.assert_not_emitted(rod_manager.data_3d):
            with qtbot.wait_signal(rod_manager.data_2d):
                rod_manager.update_color_2D(color)
        assert rod_manager.color_2D == color

    def test_update_color_2D_defaults(
        self, qtbot: QtBot, rod_manager: RodData
    ):
        rod_manager.frame = 500
        with qtbot.assert_not_emitted(rod_manager.data_3d):
            with qtbot.wait_signal(rod_manager.data_2d):
                rod_manager.update_color_2D()
        assert rod_manager.color_2D is None

    @pytest.mark.parametrize("send", [True, False])
    @pytest.mark.parametrize("color", [None, "black", "stuff"])
    def test_update_color_3D(
        self, qtbot: QtBot, rod_manager: RodData, color: str, send: bool
    ):
        rod_manager.frame = 500
        with qtbot.assert_not_emitted(rod_manager.data_2d):
            if send:
                with qtbot.wait_signal(rod_manager.data_3d):
                    rod_manager.update_color_3D(color, send)
            else:
                with qtbot.assert_not_emitted(rod_manager.data_3d):
                    rod_manager.update_color_3D(color, send)
        assert rod_manager.color_3D == color

    def test_update_color_3D_defaults(
        self, qtbot: QtBot, rod_manager: RodData
    ):
        rod_manager.frame = 500
        with qtbot.assert_not_emitted(rod_manager.data_2d):
            with qtbot.wait_signal(rod_manager.data_3d):
                rod_manager.update_color_3D()
        assert rod_manager.color_3D is None

    @pytest.mark.parametrize("use_number", [True, False])
    def test_update_rod_2D(
        self, qtbot: QtBot, rod_manager: RodData, use_number: bool
    ):
        rod_manager.frame = 500
        if use_number:
            rod = random.randrange(0, 24)
        else:
            rod = None
        with qtbot.assert_not_emitted(rod_manager.data_3d):
            with qtbot.wait_signal(rod_manager.data_2d):
                rod_manager.update_rod_2D(rod)
        assert rod_manager.rod_2D == rod

    def test_update_rod_2D_defaults(self, qtbot: QtBot, rod_manager: RodData):
        rod_manager.frame = 500
        with qtbot.assert_not_emitted(rod_manager.data_3d):
            with qtbot.wait_signal(rod_manager.data_2d):
                rod_manager.update_rod_2D()
        assert rod_manager.rod_2D is None

    @pytest.mark.parametrize("use_number", [True, False])
    @pytest.mark.parametrize("send", [True, False])
    def test_update_rod_3D(
        self, qtbot: QtBot, rod_manager: RodData, use_number: bool, send: bool
    ):
        rod_manager.frame = 500
        if use_number:
            rod = random.randrange(0, 24)
        else:
            rod = None
        with qtbot.assert_not_emitted(rod_manager.data_2d):
            if send:
                with qtbot.wait_signal(rod_manager.data_3d):
                    rod_manager.update_rod_3D(rod, send)
            else:
                with qtbot.assert_not_emitted(rod_manager.data_3d):
                    rod_manager.update_rod_3D(rod, send)
        assert rod_manager.rod_3D == rod

    def test_update_rod_3D_defaults(self, qtbot: QtBot, rod_manager: RodData):
        rod_manager.frame = 500
        with qtbot.assert_not_emitted(rod_manager.data_2d):
            with qtbot.wait_signal(rod_manager.data_3d):
                rod_manager.update_rod_3D()
        assert rod_manager.rod_3D is None

    def test_provide_data_default(self, qtbot: QtBot, rod_manager: RodData):
        rod_manager.frame = 500
        with qtbot.wait_signals([rod_manager.data_2d, rod_manager.data_3d]):
            rod_manager.provide_data()

    @pytest.mark.parametrize(
        "frame,data", [(False, True), (True, False), (False, False)]
    )
    def test_provide_data_abort(
        self, qtbot: QtBot, rod_manager: RodData, frame: bool, data: bool
    ):
        if not frame:
            rod_manager.frame = None
        else:
            rod_manager.frame = 500
        if not data:
            rod_data.rod_data = None
        else:
            assert rod_data.rod_data is not None

        with qtbot.assert_not_emitted(rod_manager.data_3d):
            with qtbot.assert_not_emitted(rod_manager.data_2d):
                rod_manager.provide_data()

    @pytest.mark.parametrize("all_colors", [True, False])
    @pytest.mark.parametrize("all_rods", [True, False])
    def test_provide_data_2d(
        self,
        qtbot: QtBot,
        rod_manager: RodData,
        all_colors: bool,
        all_rods: bool,
    ):
        rod_manager.frame = 500
        assert rod_data.rod_data is not None
        if all_colors:
            rod_manager.color_2D = None
            expected_colors = list(rod_data.rod_data.color.unique())
        else:
            expected_colors = [
                random.choice(rod_data.rod_data.color.unique()),
            ]
            rod_manager.color_2D = expected_colors[0]
        if all_rods:
            expected_rods = list(
                rod_data.rod_data.loc[
                    rod_data.rod_data.frame == 500
                ].particle.unique()
            )
            rod_manager.rod_2D = None
        else:
            expected_rods = [
                random.choice(
                    rod_data.rod_data.loc[
                        rod_data.rod_data.frame == 500
                    ].particle.unique()
                ),
            ]
            rod_manager.rod_2D = expected_rods[0]

        with qtbot.wait_signal(rod_manager.data_2d) as bl:
            rod_manager.provide_data(data_3d=False)

        sent_data = bl.args[0]
        sent_color = bl.args[1]
        if all_colors:
            assert sent_color == ""
        else:
            assert sent_color == expected_colors[0]
        assert sorted(expected_rods) == sorted(sent_data.particle.unique())
        assert len(sent_data.frame.unique()) == 1
        assert sent_data.frame.unique()[0] == 500

    @pytest.mark.parametrize("all_colors", [True, False])
    @pytest.mark.parametrize("all_rods", [True, False])
    def test_provide_data_3d(
        self,
        qtbot: QtBot,
        rod_manager: RodData,
        all_colors: bool,
        all_rods: bool,
    ):
        rod_manager.frame = 500
        assert rod_data.rod_data is not None
        if all_colors:
            rod_manager.color_3D = None
            expected_colors = list(rod_data.rod_data.color.unique())
        else:
            expected_colors = [
                random.choice(rod_data.rod_data.color.unique()),
            ]
            rod_manager.color_3D = expected_colors[0]
        if all_rods:
            expected_rods = list(
                rod_data.rod_data.loc[
                    rod_data.rod_data.frame == 500
                ].particle.unique()
            )
            rod_manager.rod_3D = None
        else:
            expected_rods = [
                random.choice(
                    rod_data.rod_data.loc[
                        rod_data.rod_data.frame == 500
                    ].particle.unique()
                ),
            ]
            rod_manager.rod_3D = expected_rods[0]

        with qtbot.wait_signal(rod_manager.data_3d) as bl:
            rod_manager.provide_data(data_2d=False)

        sent_data = bl.args[0]
        sent_colors = sent_data.color.unique()
        assert sorted(sent_colors) == sorted(expected_colors)
        assert sorted(expected_rods) == sorted(sent_data.particle.unique())
        assert len(sent_data.frame.unique()) == 1
        assert sent_data.frame.unique()[0] == 500

    @pytest.mark.parametrize(
        "data3d, data2d, rods",
        [(False, True, [1, 2, 4]), (True, False, [1, 2, 4])],
    )
    def test_get_data(
        self, qtbot: QtBot, rod_manager: RodData, data3d, data2d, rods
    ):
        with qtbot.wait_signal(rod_manager.requested_data) as blocker:
            rod_manager.get_data(rods=rods, data_2d=data2d, data_3d=data3d)
        particles = blocker.args[0]["particle"].unique()
        columns = blocker.args[0].columns
        assert list(particles) == rods
        assert (list(columns) == rod_manager.cols_2D) == data2d
        assert (list(columns) == rod_manager.cols_3D) == data3d

    def test_get_data_missing_data(
        self, qtbot: QtBot, monkeypatch: MonkeyPatch, rod_manager: RodData
    ):
        monkeypatch.setattr(rod_data, "rod_data", None)
        with qtbot.assert_not_emitted(rod_manager.requested_data):
            rod_manager.get_data()

    def test_receive_updated_data(self, rod_manager: RodData):
        test_data = rod_data.rod_data.loc[
            rod_data.rod_data["frame"] == 500
        ].copy()
        test_particles = test_data.particle.unique()[0]
        columns = [
            col
            for col in test_data.columns
            if col not in ["particle", "color", "frame"]
        ]
        test_data.loc[test_data.particle == test_particles, columns] = 1
        rod_manager.receive_updated_data(test_data)
        changed_data = rod_data.rod_data.loc[rod_data.rod_data.frame == 500]
        pd.testing.assert_frame_equal(
            changed_data[test_data.columns], test_data, check_dtype=False
        )

    def test_receive_updated_data_current_frame(
        self, qtbot: QtBot, rod_manager: RodData
    ):
        test_data = rod_data.rod_data.loc[
            rod_data.rod_data["frame"] == 500
        ].copy()
        test_particles = test_data.particle.unique()[0]
        columns = [
            col
            for col in test_data.columns
            if col not in ["particle", "color", "frame"]
        ]
        test_data.loc[test_data.particle == test_particles, columns] = 1
        rod_manager.frame = 500
        with qtbot.wait_signals([rod_manager.data_2d, rod_manager.data_3d]):
            rod_manager.receive_updated_data(test_data)

    def test_add_data(self, rod_manager: RodData):
        rod_data.rod_data = load_rod_data(["red"])
        test_data = load_rod_data(["blue"])
        rod_manager.add_data(test_data)
        # raise NotImplementedError

    def test_add_data_not_loaded(
        self, qtbot: QtBot, monkeypatch: MonkeyPatch, rod_manager: RodData
    ):
        rod_data.rod_data = None
        test_data = load_rod_data(["red"])
        expected = [rod_manager.is_busy, rod_manager.data_loaded[list]]
        monkeypatch.setattr(rod_manager.threads, "start", lambda *args: None)
        with qtbot.wait_signals(expected):
            rod_manager.add_data(test_data)
        pd.testing.assert_frame_equal(rod_data.rod_data, test_data)

    def test_catch_data_single(self, qtbot: QtBot, rod_manager: RodData):
        test_data = {
            "frame": 500,
            "cam_id": "gp3",
            "color": "black",
            "position": [0, 0, 0, 0],
            "rod_id": 0,
            "seen": False,
        }
        test_action = lg.Action()
        test_action.to_save = lambda: test_data
        rod_manager.frame = 500

        with qtbot.wait_signals(
            [rod_manager.data_update, rod_manager.data_2d]
        ) as bl:
            rod_manager.catch_data(test_action)
        assert len(bl.all_signals_and_args) == 2
        for sig in bl.all_signals_and_args:
            if "data_update" in sig.signal_name:
                assert sig.args[0] == test_data

    def test_catch_data_multi(self, qtbot: QtBot, rod_manager: RodData):
        test_data = {
            "frame": [500, 502, 530],
            "cam_id": ["gp3", "gp4", "gp3"],
            "color": ["black", "black", "green"],
            "position": [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]],
            "rod_id": [0, 5, 5],
            "seen": [False, False, False],
        }
        test_action = lg.Action()
        test_action.to_save = lambda: test_data
        rod_manager.frame = 500
        with qtbot.wait_signals(
            [rod_manager.data_update, rod_manager.data_2d]
        ) as bl:
            rod_manager.catch_data(test_action)
        assert len(bl.all_signals_and_args) == 4

    def test_catch_data_empty(self, qtbot: QtBot, rod_manager: RodData):
        test_action = lg.Action()
        test_action.to_save = lambda: None
        rod_manager.frame = 500
        with qtbot.assert_not_emitted(rod_manager.data_update):
            with qtbot.assert_not_emitted(rod_manager.data_2d):
                rod_manager.catch_data(test_action)

    @pytest.mark.parametrize(
        "action",
        [
            lg.NumberChangeActions.ALL,
            lg.NumberChangeActions.ALL_ONE_CAM,
            lg.NumberChangeActions.ONE_BOTH_CAMS,
        ],
    )
    def test_catch_number_switch(
        self,
        qtbot: QtBot,
        rod_manager: RodData,
        action: lg.NumberChangeActions,
    ):
        rod_manager.frame = 501
        rod_manager.color_2D = "green"
        with qtbot.wait_signal(rod_manager.data_2d):
            rod_manager.catch_number_switch(action, 0, 1, "gp3", "black", 500)

    @pytest.mark.parametrize(
        "action",
        [
            lg.NumberChangeActions.ALL,
            lg.NumberChangeActions.ALL_ONE_CAM,
            lg.NumberChangeActions.ONE_BOTH_CAMS,
        ],
    )
    def test_catch_number_switch_default(
        self,
        qtbot: QtBot,
        rod_manager: RodData,
        action: lg.NumberChangeActions,
    ):
        rod_manager.frame = 500
        with qtbot.wait_signal(rod_manager.data_2d):
            rod_manager.catch_number_switch(action, 0, 1, "gp3")

    def test_folder_has_data(self):
        dir = importlib_resources.files("RodTracker.resources.example_data")
        assert RodData.folder_has_data(dir.joinpath("csv"))

    def test_has_data_avoid_wrong_files(self):
        dir = importlib_resources.files("RodTracker.resources.example_data")
        assert not RodData.folder_has_data(dir.joinpath("images"))

    def test_has_data_raises_on_file(self):
        dir = importlib_resources.files(
            "RodTracker.resources.example_data.csv"
        )
        file_path = dir.joinpath("rods_df_black.csv")
        with pytest.raises(NotADirectoryError):
            RodData.folder_has_data(file_path)

    def test_has_data_empty_folder(self, tmp_path: Path):
        assert not RodData.folder_has_data(tmp_path)

    def test_has_data_non_existent(self):
        dir = importlib_resources.files("RodTracker.resources").joinpath(
            "test"
        )
        assert not RodData.folder_has_data(dir)

    def test_get_color_data(self, tmp_path: Path):
        dir = importlib_resources.files(
            "RodTracker.resources.example_data.csv"
        )
        test_colors = ["blue", "green", "red"]
        read_data = []
        for i in range(1, len(test_colors) + 1):
            dst_path = tmp_path.joinpath(f"out{i}")
            dst_path.mkdir()
            tmp_colors = test_colors[:i]
            test_files = [f"rods_df_{color}.csv" for color in tmp_colors]
            for f in test_files:
                shutil.copy2(dir.joinpath(f), tmp_path.joinpath(f))
            data, colors = RodData.get_color_data(tmp_path)
            read_data.append(data.reset_index(drop=True))
            assert sorted(colors) == sorted(tmp_colors)
            assert data is not None
            assert sorted(data["color"].unique()) == sorted(tmp_colors)

        for i in range(1, len(read_data)):
            tmp_colors = test_colors[:i]
            for color in tmp_colors:
                tmp_small = (
                    read_data[i - 1]
                    .loc[read_data[i - 1]["color"] == color]
                    .reset_index(drop=True)
                )
                tmp_big = (
                    read_data[i]
                    .loc[read_data[i]["color"] == color]
                    .reset_index(drop=True)
                )
                assert tmp_small.isin(tmp_big).all().all()

    def test_color_data_empty_folder(self, tmp_path: Path):
        dst_path = tmp_path.joinpath("out")
        dst_path.mkdir()
        data, colors = RodData.get_color_data(tmp_path)
        assert data is None
        assert colors == []

    @pytest.mark.parametrize(
        "name", ["test.csv", "testing.txt", "rods_blue.csv"]
    )
    def test_color_data_avoid_wrong_files(self, tmp_path: Path, name: str):
        dir = importlib_resources.files(
            "RodTracker.resources.example_data.csv"
        )
        test_colors = ["blue", "green", "red"]
        avoid_color = "black"
        test_files = [
            f"rods_df_{color}.csv" for color in [*test_colors, avoid_color]
        ]
        for f in test_files:
            shutil.copy2(dir.joinpath(f), tmp_path.joinpath(f))

        # Create "bait" file
        (tmp_path / test_files[-1]).rename(tmp_path / name)

        data, colors = RodData.get_color_data(tmp_path)
        assert sorted(colors) == sorted(test_colors)
        assert data is not None
        assert sorted(data["color"].unique()) == sorted(test_colors)

    def test_extract_seen_information(
        self, qtbot: QtBot, rod_manager: RodData
    ):
        expected_cams = ["gp3", "gp4"]
        seen_cols = ["seen_" + cam for cam in expected_cams]
        expected_seen = [
            random.choices([0, 1], k=2) for _ in range(len(rod_data.rod_data))
        ]
        rod_data.rod_data[seen_cols] = expected_seen
        previous = rod_data.rod_data.copy()
        previous.set_index(["color", "frame", "particle"], inplace=True)
        seen_info, cams = rod_data.RodData.extract_seen_information()
        assert sorted(expected_cams) == sorted(cams)
        for frame in seen_info.keys():
            for color in seen_info[frame].keys():
                for particle in seen_info[frame][color].keys():
                    expect = previous.loc[(color, frame, particle), seen_cols]
                    real = [
                        1 if item == "seen" else 0
                        for item in seen_info[frame][color][particle]
                    ]
                    assert (expect == real).all(None)

    @pytest.mark.skip("Function under test needs adjustments.")
    def test_clean_data(self):
        raise NotImplementedError

    @pytest.mark.skip("Function under test needs adjustments.")
    def test_find_unused_rods(self):
        raise NotImplementedError

    @pytest.mark.parametrize(
        "settings",
        [
            {"position_scaling": random.random() - 1.0},
            {
                "position_scaling": random.random() - 1.0,
                "other": random.random() - 1.0,
            },
            {"other": random.random() - 1.0},
        ],
        ids=["relevant", "with_distraction", "irrelevant"],
    )
    def test_update_settings(
        self, qtbot: QtBot, rod_manager: RodData, settings: dict
    ):
        rod_manager.frame = 500
        if "position_scaling" in settings:
            with qtbot.wait_signals(
                [rod_manager.data_2d, rod_manager.data_3d]
            ):
                rod_manager.update_settings(settings)
            assert settings["position_scaling"] == rod_data.POSITION_SCALING
        else:
            pos_scale_pre = rod_data.POSITION_SCALING
            with qtbot.assert_not_emitted(rod_manager.data_2d):
                with qtbot.assert_not_emitted(rod_manager.data_3d):
                    rod_manager.update_settings(settings)
            assert pos_scale_pre == rod_data.POSITION_SCALING


def test_change_data(qtbot: QtBot, rod_manager: RodData):
    test_data = {
        "frame": 500,
        "cam_id": "gp3",
        "color": "black",
        "position": [random.random() for _ in range(4)],
        "rod_id": 0,
        "seen": 1,
    }
    frame = test_data["frame"]
    color = test_data["color"]
    particle = test_data["rod_id"]
    position = test_data["position"]
    seen = test_data["seen"]
    cam_cols = [
        col for col in rod_data.rod_data.columns if test_data["cam_id"] in col
    ]

    # Ensure, that some values will be changed by the function under test.
    previous = rod_data.rod_data.copy()
    assert (
        previous.loc[
            (previous.frame == frame)
            & (previous.particle == particle)
            & (previous.color == color),
            cam_cols,
        ]
        != [*position, seen]
    ).any(axis=None)

    rod_data.change_data(test_data)
    changed = rod_data.rod_data
    assert (
        changed.loc[
            (changed.frame == frame)
            & (changed.particle == particle)
            & (changed.color == color),
            cam_cols,
        ]
        == [*position, seen]
    ).all(None)
    assert (
        changed.loc[
            (changed.frame != frame)
            | (changed.particle != particle)
            | (changed.color != color)
        ]
        == previous.loc[
            (previous.frame != frame)
            | (previous.particle != particle)
            | (previous.color != color)
        ]
    ).all(None)


def test_change_data_multiple(qtbot: QtBot, rod_manager: RodData):
    test_data = {
        "frame": [500, 502, 530],
        "cam_id": ["gp3", "gp4", "gp3"],
        "color": ["black", "black", "green"],
        "position": [[random.random() for _ in range(4)] for _ in range(3)],
        "rod_id": [0, 5, 5],
        "seen": [False, False, False],
    }
    # Ensure, that some values will be changed by the function under test.
    previous = rod_data.rod_data.copy()
    for i in range(3):
        frame = test_data["frame"][i]
        color = test_data["color"][i]
        particle = test_data["rod_id"][i]
        position = test_data["position"][i]
        seen = test_data["seen"][i]
        cam_cols = [
            col
            for col in rod_data.rod_data.columns
            if test_data["cam_id"][i] in col
        ]
        assert (
            previous.loc[
                (previous.frame == frame)
                & (previous.particle == particle)
                & (previous.color == color),
                cam_cols,
            ]
            != [*position, seen]
        ).any(axis=None)

    rod_data.change_data(test_data)
    changed = rod_data.rod_data

    for i in range(3):
        frame = test_data["frame"][i]
        color = test_data["color"][i]
        particle = test_data["rod_id"][i]
        position = test_data["position"][i]
        seen = test_data["seen"][i]
        cam_cols = [
            col
            for col in rod_data.rod_data.columns
            if test_data["cam_id"][i] in col
        ]
        assert (
            changed.loc[
                (changed.frame == frame)
                & (changed.particle == particle)
                & (changed.color == color),
                cam_cols,
            ]
            == [*position, seen]
        ).all(None)


def test_change_data_new(qtbot: QtBot, rod_manager: RodData):
    test_data = {
        "frame": 500,
        "cam_id": "gp3",
        "color": "black",
        "position": [random.random() for _ in range(4)],
        "rod_id": 30,
        "seen": True,
    }
    frame = test_data["frame"]
    color = test_data["color"]
    particle = test_data["rod_id"]
    position = test_data["position"]
    seen = test_data["seen"]
    cam_cols = [
        col for col in rod_data.rod_data.columns if test_data["cam_id"] in col
    ]
    # Ensure, the test data rod does not exist yet.
    previous = rod_data.rod_data.copy()
    assert (
        particle
        not in previous.loc[
            (previous.frame == frame) & (previous.color == color)
        ].particle.unique()
    )
    rod_data.change_data(test_data)
    changed = rod_data.rod_data
    assert (
        changed.loc[
            (changed.frame == frame)
            & (changed.particle == particle)
            & (changed.color == color),
            cam_cols,
        ]
        == [*position, seen]
    ).all(None)
    assert (
        changed.loc[
            (changed.frame != frame)
            | (changed.particle != particle)
            | (changed.color != color)
        ]
        == previous.loc[
            (previous.frame != frame)
            | (previous.particle != particle)
            | (previous.color != color)
        ]
    ).all(None)


@pytest.mark.parametrize(
    "mode",
    [
        lg.NumberChangeActions.ALL,
        lg.NumberChangeActions.ALL_ONE_CAM,
        lg.NumberChangeActions.ONE_BOTH_CAMS,
    ],
)
def test_rod_number_swap(
    qtbot: QtBot, rod_manager: RodData, mode: lg.NumberChangeActions
):
    old_id = 4
    new_id = 2
    color = "black"
    cam = "gp3"
    frame = 545
    prev_data = rod_data.rod_data.copy()
    rod_data.rod_number_swap(mode, old_id, new_id, color, frame, cam)
    prev_unchanged = prev_data.loc[prev_data.frame < frame]
    unchanged = rod_data.rod_data.loc[rod_data.rod_data.frame < frame]
    assert (prev_unchanged == unchanged).all(None)
    prev_unchanged_color = prev_data.loc[
        (prev_data.frame >= frame) & (prev_data.color != color)
    ]
    unchanged_color = rod_data.rod_data.loc[
        (rod_data.rod_data.frame >= frame) & (rod_data.rod_data.color != color)
    ]
    assert (
        prev_unchanged_color.reset_index() == unchanged_color.reset_index()
    ).all(None)

    if mode == lg.NumberChangeActions.ALL:
        changed = rod_data.rod_data.loc[rod_data.rod_data.frame >= frame]
        prev_old = prev_data.loc[
            (prev_data.particle == old_id)
            & (prev_data.frame >= frame)
            & (prev_data.color == color)
        ].drop(columns=["particle"])
        prev_new = prev_data.loc[
            (prev_data.particle == new_id)
            & (prev_data.frame >= frame)
            & (prev_data.color == color)
        ].drop(columns=["particle"])
        changed_old = changed.loc[
            (changed.particle == old_id) & (changed.color == color)
        ].drop(columns=["particle"])
        changed_new = changed.loc[
            (changed.particle == new_id) & (changed.color == color)
        ].drop(columns=["particle"])
        assert (
            prev_old.reset_index(drop=True)
            == changed_new.reset_index(drop=True)
        ).all(None)
        assert (
            prev_new.reset_index(drop=True)
            == changed_old.reset_index(drop=True)
        ).all(None)

    elif mode == lg.NumberChangeActions.ALL_ONE_CAM:
        changed_cols = [col for col in prev_data.columns if cam in col]
        unchanged_cols = [col for col in prev_data.columns if cam not in col]

        unchanged = rod_data.rod_data.loc[
            rod_data.rod_data.frame >= frame, unchanged_cols
        ]
        prev_unchanged = prev_data.loc[
            prev_data.frame >= frame, unchanged_cols
        ]
        assert (
            prev_unchanged.reset_index(drop=True)
            == unchanged.reset_index(drop=True)
        ).all(None)

        changed = rod_data.rod_data.loc[rod_data.rod_data.frame >= frame]
        prev_old = prev_data.loc[
            (prev_data.particle == old_id)
            & (prev_data.frame >= frame)
            & (prev_data.color == color),
            changed_cols,
        ]
        prev_new = prev_data.loc[
            (prev_data.particle == new_id)
            & (prev_data.frame >= frame)
            & (prev_data.color == color),
            changed_cols,
        ]
        changed_old = changed.loc[
            (changed.particle == old_id) & (changed.color == color),
            changed_cols,
        ]
        changed_new = changed.loc[
            (changed.particle == new_id) & (changed.color == color),
            changed_cols,
        ]
        assert (
            prev_old.reset_index(drop=True)
            == changed_new.reset_index(drop=True)
        ).all(None)
        assert (
            prev_new.reset_index(drop=True)
            == changed_old.reset_index(drop=True)
        ).all(None)

    elif mode == lg.NumberChangeActions.ONE_BOTH_CAMS:
        prev_unchanged = prev_data.loc[prev_data.frame != frame]
        unchanged = rod_data.rod_data.loc[rod_data.rod_data.frame != frame]
        assert (prev_unchanged == unchanged).all(None)

        changed = rod_data.rod_data.loc[rod_data.rod_data.frame == frame]
        prev_old = prev_data.loc[
            (prev_data.particle == old_id)
            & (prev_data.frame == frame)
            & (prev_data.color == color)
        ].drop(columns=["particle"])
        prev_new = prev_data.loc[
            (prev_data.particle == new_id)
            & (prev_data.frame == frame)
            & (prev_data.color == color)
        ].drop(columns=["particle"])
        changed_old = changed.loc[
            (changed.particle == old_id) & (changed.color == color)
        ].drop(columns=["particle"])
        changed_new = changed.loc[
            (changed.particle == new_id) & (changed.color == color)
        ].drop(columns=["particle"])
        assert (
            prev_old.reset_index(drop=True)
            == changed_new.reset_index(drop=True)
        ).all(None)
        assert (
            prev_new.reset_index(drop=True)
            == changed_old.reset_index(drop=True)
        ).all(None)
