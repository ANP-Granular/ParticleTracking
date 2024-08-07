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

"""Tests for typical usecases and cases where problems occurred in the past."""
import os
import pathlib
from typing import List

import conftest
import gui_actions as ga
import importlib_resources
import pytest
from PyQt5 import QtCore, QtWidgets
from pytest import MonkeyPatch
from pytestqt.qtbot import QtBot

import RodTracker.backend.logger as lg
from RodTracker.ui.mainwindow import RodTrackWindow

if os.getenv("GITHUB_ACTIONS"):
    pytestmark = pytest.mark.skip(
        "Tests requiring interaction with GUI elements cannot be run properly "
        "with GitHub Actions at the moment. Have a look this issue for "
        "more information: "
        "https://github.com/ANP-Granular/ParticleTracking/issues/87"
    )


def teardown_replacements(mp: MonkeyPatch):
    """Replaces QMessageBox behaviour to be able to automatically close the
    RodTracker, when it has unsaved changes."""
    mp.setattr(
        QtWidgets.QMessageBox, "clickedButton", lambda *args, **kwargs: None
    )
    mp.setattr(QtWidgets.QMessageBox, "exec", lambda *args, **kwargs: None)


# =============================================================================
# =============================================================================


@pytest.mark.filterwarnings("ignore:")
def test_typical(
    main_window: RodTrackWindow,
    qtbot: QtBot,
    monkeypatch: MonkeyPatch,
    tmp_path: pathlib.Path,
):
    """Attempt a typical workflow."""
    try:
        scenario = [
            ga.OpenData(conftest.csv_data),
            ga.OpenImage(
                importlib_resources.files(
                    "RodTracker.resources.example_data.images"
                ).joinpath("gp3")
            ),
            ga.SwitchCamera(),
            ga.OpenImage(
                importlib_resources.files(
                    "RodTracker.resources.example_data.images"
                ).joinpath("gp4")
            ),
            ga.SwitchRodNumber(12, 7, lg.NumberChangeActions.ALL_ONE_CAM),
            ga.SwitchCamera(),
            ga.SwitchRodNumber(7, 12, lg.NumberChangeActions.CURRENT),
            ga.SwitchFrame(1),
            ga.SwitchFrame(1),
            ga.ChangeRodPosition(12),
            ga.CreateRod(25),
            ga.SwitchCamera(),
            ga.LengthAdjustment(QtCore.Qt.Key_T),
            ga.SwitchColor("blue"),
            ga.DeleteRod(12),
            ga.SaveChanges(),
        ]
        for action in scenario:
            main_window = action.run(main_window, qtbot, monkeypatch, tmp_path)
    finally:
        # teardown
        teardown_replacements(monkeypatch)


# =============================================================================
# =============================================================================


@pytest.mark.xfail(reason="Not (fully) implemented.")
def test_open_rods_wo_imgs():
    raise NotImplementedError


# =============================================================================
# =============================================================================


attempted_saving = [
    pytest.param(
        [
            ga.SaveChanges(),
        ],
        id="ImmediateSaving",
    ),
    pytest.param(
        [
            ga.ChangeRodPosition(12),
            ga.SaveChanges(),
            ga.SaveChanges(),
        ],
        id="RepeatedSaving",
    ),
    pytest.param(
        [
            ga.ChangeRodPosition(12),
            ga.Undo(),
            ga.SaveChanges(),
        ],
        id="PostUndoSaving",
    ),
]


@pytest.mark.xfail(reason="Not (fully) implemented.")
@pytest.mark.parametrize("scenario", attempted_saving)
def test_save_wo_changes(
    both_cams: RodTrackWindow,
    qtbot: QtBot,
    monkeypatch: MonkeyPatch,
    tmp_path: pathlib.Path,
    scenario: List[ga.UserAction],
):
    try:
        for action in scenario:
            both_cams = action.run(both_cams, qtbot, monkeypatch, tmp_path)
    finally:
        # teardown
        teardown_replacements(monkeypatch)
    raise NotImplementedError


# =============================================================================
# =============================================================================


def test_open_rod_after_changes(
    both_cams: RodTrackWindow,
    qtbot: QtBot,
    monkeypatch: MonkeyPatch,
    tmp_path: pathlib.Path,
):
    try:
        both_cams = ga.ChangeRodPosition(12).run(
            both_cams, qtbot, monkeypatch, tmp_path
        )
        # TODO: assert a warning is issued, that usaved changes are available
        both_cams = ga.OpenData(conftest.csv_data).run(
            both_cams, qtbot, monkeypatch, tmp_path
        )
    finally:
        # teardown
        teardown_replacements(monkeypatch)


# =============================================================================
# =============================================================================


def test_undo_after_save(
    both_cams: RodTrackWindow,
    qtbot: QtBot,
    monkeypatch: MonkeyPatch,
    tmp_path: pathlib.Path,
):
    """Attempt to revert an action that has been saved already."""
    scenario = [
        ga.ChangeRodPosition(12),
        ga.SaveChanges(),
        ga.Undo(),
        ga.SaveChanges(),
    ]
    try:
        for action in scenario:
            both_cams = action.run(both_cams, qtbot, monkeypatch, tmp_path)
    finally:
        # teardown
        teardown_replacements(monkeypatch)


# =============================================================================
# =============================================================================


def test_save_on_unloaded_img(
    one_cam: RodTrackWindow,
    qtbot: QtBot,
    monkeypatch: MonkeyPatch,
    tmp_path: pathlib.Path,
):
    """
    Attempt saveing changes from 2nd view without having images loaded
    there.
    """
    scenario = [ga.ChangeRodPosition(12), ga.SwitchCamera(), ga.SaveChanges()]
    try:
        for action in scenario:
            one_cam = action.run(one_cam, qtbot, monkeypatch, tmp_path)
    finally:
        # teardown
        teardown_replacements(monkeypatch)


# =============================================================================
# =============================================================================
