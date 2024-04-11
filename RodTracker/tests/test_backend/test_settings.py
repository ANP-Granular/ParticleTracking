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

import importlib
import json
import pathlib
import random

import pytest
from pytestqt.qtbot import QtBot

import RodTracker
import RodTracker.backend.settings as se


class TestConfiguration:
    def test_read_default(self, tmp_path: pathlib.Path):
        RodTracker.CONFIG_DIR = tmp_path
        # Force reload to account for the new TEMP_DIR
        importlib.reload(se)

        test_cfg = {f"key{i}": i for i in range(4)}
        with open(tmp_path.joinpath("configurations.json"), "w") as f:
            json.dump(test_cfg, f)
        config = se.Configuration()
        config.read()
        assert config._contents == test_cfg

    def test_read_file(self, tmp_path: pathlib.Path):
        test_cfg = {f"key{i}": i for i in range(4)}
        test_file = tmp_path.joinpath("configurations.json")
        with open(test_file, "w") as f:
            json.dump(test_cfg, f)
        config = se.Configuration()
        config.read(str(test_file))
        assert config._contents == test_cfg

    @pytest.mark.xfail(reason="Known issue.")
    def test_read_empty(self, tmp_path: pathlib.Path):
        test_file = tmp_path.joinpath("configurations.json")
        open(test_file, "w").close()
        config = se.Configuration()
        with pytest.raises(FileNotFoundError):
            # TODO: currently raises JSONDecodeError
            config.read(str(test_file))

    def test_read_nonexistent(self, tmp_path: pathlib.Path):
        config = se.Configuration()
        with pytest.raises(FileNotFoundError):
            config.read(str(tmp_path.joinpath("nonexistent.json")))

    def test_save_default(self, tmp_path: pathlib.Path):
        test_cfg = se.Configuration()
        se.Configuration.path = str(tmp_path.joinpath("configurations.json"))
        test_dict = {f"key{i}": i for i in range(4)}
        se.Configuration._contents = test_dict
        test_cfg.save()
        with open(str(tmp_path.joinpath("configurations.json")), "r") as f:
            read_cfg = json.load(f)
        assert read_cfg == test_dict

    def test_save(self, tmp_path: pathlib.Path):
        se.Configuration._contents = {}
        test_cfg = se.Configuration()
        test_path = str(tmp_path.joinpath("test.json"))
        test_dict = {f"key{i}": i for i in range(4)}
        assert se.Configuration.path != test_path
        assert se.Configuration._contents != test_dict

        test_cfg.save(new_path=test_path, new_data=test_dict)

        assert se.Configuration.path == test_path
        assert se.Configuration._contents == test_dict

        with open(test_path, "r") as f:
            read_cfg = json.load(f)
        assert read_cfg == test_dict


class TestSettings:

    def test_init_default(self, tmp_path: pathlib.Path):
        test_cfg = {
            "visual": {
                "rod_thickness": random.random(),
                "rod_color": random.choices(list(range(256)), k=3),
                "number_offset": random.random(),
                "number_color": random.choices(list(range(256)), k=3),
                "number_size": random.random(),
                "boundary_offset": random.random(),
                "position_scaling": random.random(),
                "number_rods": random.random(),
            },
            "data": {
                "images_root": "./",
                "positions_root": "./",
            },
            "functional": {
                "rod_increment": random.random(),
            },
            "experiment": {
                "number_rods": random.random(),
                "box_width": random.random(),
                "box_height": random.random(),
                "box_depth": random.random(),
            },
        }
        test_path = tmp_path.joinpath("settings.json")
        se.Settings.path = str(test_path)
        with open(test_path, "w") as f:
            json.dump(test_cfg, f)

        config = se.Settings()
        assert config._contents == test_cfg

    def test_init(self, tmp_path: pathlib.Path):
        test_cfg = {
            "visual": {
                "rod_thickness": random.random(),
                "rod_color": random.choices(list(range(256)), k=3),
                "number_offset": random.random(),
                "number_color": random.choices(list(range(256)), k=3),
                "number_size": random.random(),
                "boundary_offset": random.random(),
                "position_scaling": random.random(),
                "number_rods": random.random(),
            },
            "data": {
                "images_root": "./",
                "positions_root": "./",
            },
            "functional": {
                "rod_increment": random.random(),
            },
            "experiment": {
                "number_rods": random.random(),
                "box_width": random.random(),
                "box_height": random.random(),
                "box_depth": random.random(),
            },
        }
        default_cfg = {
            "visual": {
                "rod_thickness": random.random(),
                "rod_color": random.choices(list(range(256)), k=3),
                "number_offset": random.random(),
                "number_color": random.choices(list(range(256)), k=3),
                "number_size": random.random(),
                "boundary_offset": random.random(),
                "position_scaling": random.random(),
                "number_rods": random.random(),
            },
            "data": {
                "images_root": "./",
                "positions_root": "./",
            },
            "functional": {
                "rod_increment": random.random(),
            },
            "experiment": {
                "number_rods": random.random(),
                "box_width": random.random(),
                "box_height": random.random(),
                "box_depth": random.random(),
            },
        }
        test_path = str(tmp_path.joinpath("settings.json"))
        default_path = str(tmp_path.joinpath("default.json"))
        se.Settings.path = default_path
        with open(test_path, "w") as f:
            json.dump(test_cfg, f)
        with open(default_path, "w") as f:
            json.dump(default_cfg, f)

        config = se.Settings(test_path)
        assert config._contents == test_cfg

    @pytest.mark.parametrize(
        "test_cfg",
        [
            {},
            {"category": {f"key{i}": i for i in range(4)}},
            {"visual": {"rod_thickness": 10}},
            {"visual": {f"key{i}": i for i in range(4)}},
            {"visual": {"rod_thickness": 10, "testkey": "test"}},
        ],
    )
    def test_read_file(self, tmp_path: pathlib.Path, qtbot: QtBot, test_cfg):
        test_file = str(tmp_path.joinpath("settings.json"))
        with open(test_file, "w") as f:
            json.dump(test_cfg, f)
        config = se.Settings()
        config._contents = config._default
        prior_state = config._contents
        with qtbot.wait_signal(config.settings_changed) as blocker:
            config.read(test_file)

        all_keys = set([*test_cfg.keys(), *prior_state.keys()])
        for k in all_keys:
            # compare values, that were supposed to be altered
            if k in test_cfg.keys():
                if isinstance(test_cfg[k], dict):
                    assert isinstance(config._contents[k], dict)
                    for k_i, v in test_cfg[k].items():
                        assert config._contents[k][k_i] == v
                continue
            # compare values, that were supposed to be perserved
            if isinstance(prior_state[k], dict):
                assert isinstance(config._contents[k], dict)
                for k_i, v in prior_state[k].items():
                    assert config._contents[k][k_i] == v
            else:
                assert config._contents[k] == prior_state[k]
        assert blocker.args != []

    @pytest.mark.skip("Not implemented.")
    def test_read_default(self, tmp_path: pathlib.Path):
        raise NotImplementedError

    @pytest.mark.skip("Not implemented.")
    def test_read_empty(self, tmp_path: pathlib.Path):
        raise NotImplementedError

    @pytest.mark.skip("Not implemented.")
    def test_read_nonexistent(self, tmp_path: pathlib.Path):
        raise NotImplementedError

    @pytest.mark.parametrize(
        "item",
        [
            ["visual", "rod_thickness", 10],
            ["data", "images_root", "./test"],
            ["functional", "rod_increment", 10.5],
        ],
    )
    def test_update_field(self, tmp_path: pathlib.Path, qtbot: QtBot, item):
        importlib.reload(se)
        out_path = str(tmp_path.joinpath("settings.json"))
        se.Settings.path = out_path
        config = se.Settings()
        with qtbot.wait_signal(config.settings_changed):
            config.update_field(*item)
        assert pathlib.Path(out_path).exists()
        assert pathlib.Path(out_path).is_file()

    def test_reset_defaults(self, qtbot: QtBot):
        config = se.Settings()
        defaults = config._default
        test_cfg = {f"key{i}": i for i in range(4)}
        config._contents = test_cfg
        with qtbot.wait_signal(config.settings_changed):
            config.reset_to_default()
        assert config._contents == defaults

    def test_send_settings(self, qtbot: QtBot):
        config = se.Settings()
        with qtbot.wait_signals(
            [config.settings_changed, config.settings_changed]
        ) as blockers:
            config.send_settings()

        for it in blockers.all_signals_and_args:
            assert (it.args[0] == config._contents["visual"]) or (
                it.args[0] == config._contents["data"]
            )

    def test_save_default(self, tmp_path: pathlib.Path):
        test_cfg = se.Settings()
        se.Settings.path = str(tmp_path.joinpath("configurations.json"))
        test_dict = {f"key{i}": i for i in range(4)}
        se.Settings._contents = test_dict
        test_cfg.save()
        with open(str(tmp_path.joinpath("configurations.json")), "r") as f:
            read_cfg = json.load(f)
        assert read_cfg == test_dict

    def test_save(self, tmp_path: pathlib.Path):
        importlib.reload(se)
        se.Settings._contents = {}
        test_cfg = se.Settings()
        test_path = str(tmp_path.joinpath("test.json"))
        test_dict = {"category": {f"key{i}": i for i in range(4)}}
        assert se.Settings.path != test_path
        assert se.Settings._contents != test_dict

        test_cfg.save(new_path=test_path, new_data=test_dict)

        assert se.Settings.path == test_path
        assert se.Settings._contents == test_dict

        with open(test_path, "r") as f:
            read_cfg = json.load(f)
        assert read_cfg == test_dict
