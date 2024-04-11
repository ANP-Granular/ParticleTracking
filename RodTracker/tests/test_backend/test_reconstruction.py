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

import importlib_resources
import matplotlib.pyplot as plt
import pandas as pd
import ParticleDetection.utils.data_loading as dl
import pytest
from conftest import load_rod_data
from ParticleDetection.reconstruct_3D import match2D
from pytest import LogCaptureFixture, MonkeyPatch
from pytestqt.qtbot import QtBot

from RodTracker.backend import reconstruction
from RodTracker.backend.reconstruction import Plotter, Reconstructor, Tracker

_logger = logging.getLogger(__name__)
calibration_folder = importlib_resources.files(
    "RodTracker.resources.example_data.calibrations"
)


@pytest.fixture()
def default_reconstructor(
    monkeypatch: MonkeyPatch, testing_data: pd.DataFrame
) -> Reconstructor:
    frames = list(range(500, 503))
    calibration = dl.load_camera_calibration(
        calibration_folder.joinpath("gp34.json")
    )
    transformation = dl.load_world_transformation(
        calibration_folder.joinpath("transformation.json")
    )
    cams = ["gp3", "gp4"]
    color = "red"
    monkeypatch.setattr(
        match2D, "match_frame", lambda *args, **kwargs: pd.DataFrame()
    )
    yield Reconstructor(
        testing_data, frames, calibration, transformation, cams, color
    )


@pytest.fixture()
def default_tracker(
    monkeypatch: MonkeyPatch, testing_data: pd.DataFrame
) -> Tracker:
    frames = list(range(500, 503))
    calibration = dl.load_camera_calibration(
        calibration_folder.joinpath("gp34.json")
    )
    transformation = dl.load_world_transformation(
        calibration_folder.joinpath("transformation.json")
    )
    cams = ["gp3", "gp4"]
    color = "red"
    monkeypatch.setattr(
        match2D, "match_frame", lambda *args, **kwargs: pd.DataFrame()
    )
    yield Tracker(
        testing_data, frames, calibration, transformation, cams, color
    )


@pytest.fixture()
def default_plotter(testing_data: pd.DataFrame) -> Plotter:
    yield Plotter(testing_data)
    plt.close("all")


class TestPlotter:
    def test_run(self, qtbot: QtBot, default_plotter: Plotter):
        calibration = dl.load_camera_calibration(
            calibration_folder.joinpath("gp34.json")
        )
        signals = 3 * [default_plotter.signals.result_plot]
        default_plotter.kwargs = {
            "calibration": calibration,
            "cam_ids": ["gp3", "gp4"],
        }
        with qtbot.wait_signals(signals):
            default_plotter.run()

    def test_error_propagation(self, qtbot: QtBot, default_plotter: Plotter):
        signals = 3 * [default_plotter.signals.error]
        # default_plotter.data = None
        default_plotter.kwargs = {
            "colors": -1,
            "position_scaling": "error",
            "cam_ids": None,
            "calibration": -1,
        }
        with qtbot.wait_signals(signals, timeout=2000):
            default_plotter.run()

    def test_plot_displacements(self, qtbot: QtBot, default_plotter: Plotter):
        with qtbot.wait_signal(default_plotter.signals.result_plot):
            default_plotter.plot_displacements_3d(default_plotter.data)

    def test_displacements_multi_color(
        self, qtbot: QtBot, default_plotter: Plotter
    ):
        test_colors = ["red", "blue"]
        test_data = load_rod_data(test_colors)
        with qtbot.wait_signals(
            len(test_colors) * [default_plotter.signals.result_plot]
        ):
            default_plotter.plot_displacements_3d(test_data, test_colors)

    def test_displacements_no_data(
        self, qtbot: QtBot, default_plotter: Plotter
    ):
        test_data = load_rod_data(
            [
                "red",
            ]
        )
        with qtbot.assert_not_emitted(
            default_plotter.signals.result_plot, wait=1000
        ):
            default_plotter.plot_displacements_3d(test_data, "green")

    def test_displacements_bad_frames(
        self, qtbot: QtBot, default_plotter: Plotter, caplog: LogCaptureFixture
    ):
        test_data = load_rod_data(
            [
                "red",
            ]
        )
        with qtbot.assert_not_emitted(
            default_plotter.signals.result_plot, wait=1000
        ):
            default_plotter.plot_displacements_3d(
                test_data, start_frame=100, end_frame=100
            )
        assert caplog.record_tuples == [
            (
                "RodTracker.backend.reconstruction",
                logging.ERROR,
                "Only received data for one frame. "
                "Cannot compute a 3D displacement "
                "plot.",
            )
        ]

    def test_plot_reprojections(self, qtbot: QtBot, default_plotter: Plotter):
        calibration = dl.load_camera_calibration(
            calibration_folder.joinpath("gp34.json")
        )
        with qtbot.wait_signal(default_plotter.signals.result_plot):
            default_plotter.plot_reprojection_errors(
                default_plotter.data, ["gp3", "gp4"], calibration
            )

    def test_reprojections_no_data(
        self, qtbot: QtBot, default_plotter: Plotter, caplog: LogCaptureFixture
    ):
        with qtbot.assert_not_emitted(
            default_plotter.signals.result_plot, wait=1000
        ):
            default_plotter.plot_reprojection_errors(None, ["gp3", "gp4"])
        assert len(caplog.records) == 2

    def test_reprojections_no_calibration(
        self, qtbot: QtBot, default_plotter: Plotter, caplog: LogCaptureFixture
    ):
        with qtbot.assert_not_emitted(
            default_plotter.signals.result_plot, wait=1000
        ):
            default_plotter.plot_reprojection_errors(
                default_plotter.data, ["gp3", "gp4"]
            )
        assert caplog.record_tuples == [
            (
                "RodTracker.backend.reconstruction",
                logging.ERROR,
                f"Insufficient calibration data was " f"provided: {None}",
            )
        ]

    def test_plot_lengths(self, qtbot: QtBot, default_plotter: Plotter):
        with qtbot.wait_signal(default_plotter.signals.result_plot):
            default_plotter.plot_rod_lengths(default_plotter.data, None)

    def test_lengths_no_data(self, qtbot: QtBot, default_plotter: Plotter):
        test_data = default_plotter.data.copy()
        test_data["l"] = float("NaN")
        with qtbot.assert_not_emitted(
            default_plotter.signals.result_plot, wait=1000
        ):
            default_plotter.plot_rod_lengths(test_data)


class TestReconstructor:
    def test_abort(self, qtbot: QtBot, default_reconstructor: Reconstructor):
        reconstruction.abort_reconstruction = True
        with qtbot.assert_not_emitted(
            default_reconstructor.signals.progress, wait=1000
        ):
            with qtbot.wait_signal(default_reconstructor.signals.result):
                default_reconstructor.run()
        reconstruction.abort_reconstruction = False

    def test_finished(
        self, qtbot: QtBot, default_reconstructor: Reconstructor
    ):
        expected_emitted = len(default_reconstructor.frames) * [
            default_reconstructor.signals.progress
        ]
        expected_emitted.append(default_reconstructor.signals.result)
        with qtbot.wait_signals(expected_emitted, order="strict"):
            default_reconstructor.run()

    def test_error(
        self,
        qtbot: QtBot,
        monkeypatch: MonkeyPatch,
        default_reconstructor: Reconstructor,
    ):
        with monkeypatch.context() as mp:
            mp.setattr(default_reconstructor, "calibration", None)
            with qtbot.wait_signal(default_reconstructor.signals.error):
                default_reconstructor.run()


class TestTracker:
    def test_abort(self, qtbot: QtBot, default_tracker: Tracker):
        reconstruction.abort_reconstruction = True
        with qtbot.assert_not_emitted(
            default_tracker.signals.progress, wait=1000
        ):
            with qtbot.wait_signal(default_tracker.signals.result):
                default_tracker.run()
        reconstruction.abort_reconstruction = False

    def test_finished(self, qtbot: QtBot, default_tracker: Tracker):
        expected_emitted = len(default_tracker.frames) * [
            default_tracker.signals.progress
        ]
        expected_emitted.append(default_tracker.signals.result)
        with qtbot.wait_signals(expected_emitted, order="strict"):
            default_tracker.run()

    def test_error(
        self, qtbot: QtBot, monkeypatch: MonkeyPatch, default_tracker: Tracker
    ):
        with monkeypatch.context() as mp:
            mp.setattr(default_tracker, "calibration", None)
            with qtbot.wait_signal(default_tracker.signals.error):
                default_tracker.run()
