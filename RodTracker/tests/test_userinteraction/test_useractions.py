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

"""Tests to verify the basic functionality of user actions before further
tests.
"""

import os
import pathlib
from typing import List

import gui_actions as ga
import importlib_resources
import pandas as pd
import pytest
from PyQt5 import QtCore, QtGui, QtWidgets
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


def test_original_and_smoothed_3d_projection_overlays(
    main_window: RodTrackWindow,
):
    data = {"frame": [12], "color": ["black"]}
    for camera_index, camera in enumerate(main_window.cameras):
        camera.cam_id = f"cam{camera_index}"
        camera._current_color = "black"
        camera._position_scaling = 1.0
        camera.frame(12)
        camera.base_pixmap = QtGui.QPixmap(80, 80)
        camera.base_pixmap.fill(QtCore.Qt.white)
        for suffix, y_coord in (("smooth", 40), ("original", 65)):
            data[f"x1_{camera.cam_id}_{suffix}"] = [10]
            data[f"y1_{camera.cam_id}_{suffix}"] = [y_coord]
            data[f"x2_{camera.cam_id}_{suffix}"] = [30]
            data[f"y2_{camera.cam_id}_{suffix}"] = [y_coord]

    main_window.update_original_projection_data(pd.DataFrame(data))
    control = main_window.reconstructor
    control._available_colors = ["black"]
    control._calibration = {}
    control._transformation = {}
    control.cam_ids = ["cam0", "cam1"]
    control._update_original_projection_enabled()
    assert control.cb_original_projection.isEnabled()
    assert not control.cb_smoothed_projection.isEnabled()
    assert main_window.original_projection_shortcut.key().toString() == "J"
    assert main_window.smoothing_shortcut.key().toString() == "K"
    control.cb_original_projection.blockSignals(True)
    control.cb_original_projection.setChecked(True)
    control.cb_original_projection.blockSignals(False)
    main_window.set_original_projection_visible(True)

    for camera in main_window.cameras:
        image = camera.pixmap().toImage()
        assert camera._smoothed_data is None
        assert image.pixelColor(10, 65) == QtGui.QColor(144, 238, 144)

    control.cb_original_projection.blockSignals(True)
    control.cb_original_projection.setChecked(False)
    control.cb_original_projection.blockSignals(False)
    main_window.set_original_projection_visible(False)
    main_window.update_smoothed_data(pd.DataFrame(data))
    control.cb_smoothed_projection.setEnabled(True)
    control.cb_smoothed_projection.setChecked(True)

    for camera in main_window.cameras:
        image = camera.pixmap().toImage()
        assert image.pixelColor(10, 40) == QtGui.QColor(255, 0, 255)

    control.cb_original_projection.blockSignals(True)
    control.cb_original_projection.setChecked(True)
    control.cb_original_projection.blockSignals(False)
    main_window.set_original_projection_visible(True)
    for camera in main_window.cameras:
        image = camera.pixmap().toImage()
        assert image.pixelColor(10, 10) == QtGui.QColor(QtCore.Qt.white)
        assert image.pixelColor(10, 40) == QtGui.QColor(255, 0, 255)
        assert image.pixelColor(10, 65) == QtGui.QColor(144, 238, 144)

    control.cb_smoothed_projection.setChecked(False)
    for camera in main_window.cameras:
        image = camera.pixmap().toImage()
        assert image.pixelColor(10, 40) == QtGui.QColor(QtCore.Qt.white)
        assert image.pixelColor(10, 65) == QtGui.QColor(144, 238, 144)

    control.cb_original_projection.setChecked(False)
    for camera in main_window.cameras:
        assert camera.pixmap().toImage().pixelColor(10, 65) == QtGui.QColor(
            QtCore.Qt.white
        )


def test_data_changes_invalidate_smoothed_overlays(
    main_window: RodTrackWindow,
):
    control = main_window.reconstructor
    data = {"frame": [12], "color": ["black"]}
    for camera_index, camera in enumerate(main_window.cameras):
        camera.cam_id = f"cam{camera_index}"
        camera._current_color = "black"
        camera.frame(12)
        camera.base_pixmap = QtGui.QPixmap(80, 80)
        camera.base_pixmap.fill(QtCore.Qt.white)
        for suffix in ("overlay", "smooth", "original"):
            for endpoint in (1, 2):
                data[f"x{endpoint}_{camera.cam_id}_{suffix}"] = [10 * endpoint]
                data[f"y{endpoint}_{camera.cam_id}_{suffix}"] = [10]

    control._finish_smoothing(pd.DataFrame(data))
    control.cb_smoothed_projection.setChecked(True)
    control.cb_original_projection.setChecked(True)

    control.invalidate_smoothed_data()

    assert control.smoothed_data is None
    assert not control.cb_smoothed_projection.isChecked()
    assert not control.cb_original_projection.isChecked()
    assert not control.cb_smoothed_projection.isEnabled()
    assert not control.pb_save_smoothed.isEnabled()
    assert all(camera._smoothed_data.empty for camera in main_window.cameras)
    assert all(
        camera._original_projection_data.empty
        for camera in main_window.cameras
    )


data_opening = [
    pytest.param(
        [
            ga.OpenData(
                importlib_resources.files(
                    "RodTracker.resources.example_data"
                ).joinpath("csv")
            ),
        ],
        id="open-positions",
    ),
    pytest.param(
        [
            ga.OpenImage(
                importlib_resources.files(
                    "RodTracker.resources.example_data.images"
                ).joinpath("gp3")
            ),
        ],
        id="open-image",
    ),
]


@pytest.mark.parametrize("actions", data_opening)
def test_data_opening(
    main_window: RodTrackWindow,
    qtbot: QtBot,
    monkeypatch: MonkeyPatch,
    tmp_path: pathlib.Path,
    actions: List[ga.UserAction],
):
    try:
        for action in actions:
            main_window = action.run(main_window, qtbot, monkeypatch, tmp_path)
    finally:
        # teardown
        teardown_replacements(monkeypatch)


position_operations = [
    pytest.param(
        [
            ga.CreateRod(25),
        ],
        id="create rod",
    ),
    pytest.param(
        [
            ga.DeleteRod(12),
        ],
        id="delete rod",
    ),
    pytest.param(
        [
            ga.ChangeRodPosition(12),
        ],
        id="change position",
    ),
]


@pytest.mark.parametrize("actions", position_operations)
def test_position_operations(
    one_cam: RodTrackWindow,
    qtbot: QtBot,
    monkeypatch: MonkeyPatch,
    tmp_path: pathlib.Path,
    actions: List[ga.UserAction],
):
    try:
        for action in actions:
            one_cam = action.run(one_cam, qtbot, monkeypatch, tmp_path)
    finally:
        # teardown
        teardown_replacements(monkeypatch)


number_changing = [
    pytest.param([ga.SwitchRodNumber(12, 7)], id="switch number-abort"),
    pytest.param(
        [ga.SwitchRodNumber(12, 7, lg.NumberChangeActions.ALL)],
        id="switch number-all",
    ),
    pytest.param(
        [ga.SwitchRodNumber(12, 7, lg.NumberChangeActions.ALL_ONE_CAM)],
        id="switch number-one cam",
    ),
    pytest.param(
        [ga.SwitchRodNumber(12, 7, lg.NumberChangeActions.ONE_BOTH_CAMS)],
        id="switch number-one frame",
    ),
    pytest.param(
        [ga.SwitchRodNumber(12, 7, lg.NumberChangeActions.CURRENT)],
        id="switch number-this frame/cam",
    ),
]


@pytest.mark.parametrize("actions", number_changing)
def test_number_changing(
    one_cam: RodTrackWindow,
    qtbot: QtBot,
    monkeypatch: MonkeyPatch,
    tmp_path: pathlib.Path,
    actions: List[ga.UserAction],
):
    try:
        for action in actions:
            one_cam = action.run(one_cam, qtbot, monkeypatch, tmp_path)
    finally:
        # teardown
        teardown_replacements(monkeypatch)


length_adjustment = [
    pytest.param(
        [
            ga.LengthAdjustment(QtCore.Qt.Key_A, 12),
        ],
        id="Lengthen-single",
    ),
    pytest.param(
        [
            ga.LengthAdjustment(QtCore.Qt.Key_S, 12),
        ],
        id="Shorten-single",
    ),
    pytest.param(
        [
            ga.LengthAdjustment(QtCore.Qt.Key_R, 12),
        ],
        id="Lengthen-all",
    ),
    pytest.param(
        [
            ga.LengthAdjustment(QtCore.Qt.Key_T, 12),
        ],
        id="Shorten-all",
    ),
]


@pytest.mark.parametrize("actions", length_adjustment)
def test_length_adjustment(
    both_cams: RodTrackWindow,
    qtbot: QtBot,
    monkeypatch: MonkeyPatch,
    tmp_path: pathlib.Path,
    actions: List[ga.UserAction],
):
    try:
        for action in actions:
            both_cams = action.run(both_cams, qtbot, monkeypatch, tmp_path)
    finally:
        # teardown
        teardown_replacements(monkeypatch)


display_operations = [
    pytest.param(
        [
            ga.SwitchColor("blue"),
        ],
        id="switch color",
    ),
    pytest.param([ga.SwitchFrame(2)], id="switch frame - positive, multi"),
    pytest.param([ga.SwitchFrame(-2)], id="switch frame - negative, multi"),
    pytest.param([ga.SwitchCamera()], id="switch camera"),
]


@pytest.mark.parametrize("actions", display_operations)
def test_display_operations(
    both_cams: RodTrackWindow,
    qtbot: QtBot,
    monkeypatch: MonkeyPatch,
    tmp_path: pathlib.Path,
    actions: List[ga.UserAction],
):
    try:
        for action in actions:
            both_cams = action.run(both_cams, qtbot, monkeypatch, tmp_path)
    finally:
        # teardown
        teardown_replacements(monkeypatch)


amendment_operations = [
    pytest.param(
        [
            ga.DeleteRod(12),
            ga.Undo(),
        ],
        id="undo",
    ),
    pytest.param([ga.DeleteRod(12), ga.Undo(), ga.Redo()], id="redo"),
]


@pytest.mark.parametrize("actions", amendment_operations)
def test_amendment_operations(
    one_cam: RodTrackWindow,
    qtbot: QtBot,
    monkeypatch: MonkeyPatch,
    tmp_path: pathlib.Path,
    actions: List[ga.UserAction],
):
    try:
        for action in actions:
            one_cam = action.run(one_cam, qtbot, monkeypatch, tmp_path)
    finally:
        # teardown
        teardown_replacements(monkeypatch)


operations = [
    ga.CreateRod(25),
    ga.DeleteRod(12),
    ga.ChangeRodPosition(12),
    ga.SwitchRodNumber(12, 7),
    ga.SwitchRodNumber(12, 7, lg.NumberChangeActions.ALL),
    ga.SwitchRodNumber(12, 7, lg.NumberChangeActions.ALL_ONE_CAM),
    ga.SwitchRodNumber(12, 7, lg.NumberChangeActions.ONE_BOTH_CAMS),
    ga.SwitchRodNumber(12, 7, lg.NumberChangeActions.CURRENT),
    ga.LengthAdjustment(QtCore.Qt.Key_A, 12),
    ga.LengthAdjustment(QtCore.Qt.Key_S, 12),
    ga.LengthAdjustment(QtCore.Qt.Key_R, 12),
    ga.LengthAdjustment(QtCore.Qt.Key_T, 12),
]
undo_operations = []
redo_operations = []
for op in operations:
    mark_condition = isinstance(op, (ga.LengthAdjustment,)) or (
        isinstance(op, ga.SwitchRodNumber) and op.mode is None
    )
    mark = pytest.mark.xfail(
        condition=mark_condition,
        reason=f"Incomplete {op.__class__.__name__}.undo() implementation",
        strict=True,
    )
    undo_operations.append(
        pytest.param([op, ga.Undo()], id=f"undo-{op}", marks=mark)
    )
    redo_operations.append(
        pytest.param([op, ga.Undo(), ga.Redo()], id=f"redo-{op}", marks=mark)
    )


@pytest.mark.parametrize("actions", [*undo_operations, *redo_operations])
def test_amendmendable_operations(
    both_cams: RodTrackWindow,
    qtbot: QtBot,
    monkeypatch: MonkeyPatch,
    tmp_path: pathlib.Path,
    actions: List[ga.UserAction],
):
    try:
        for action in actions:
            both_cams = action.run(both_cams, qtbot, monkeypatch, tmp_path)
    finally:
        # teardown
        teardown_replacements(monkeypatch)


save_operations = []
for op in operations:
    save_operations.append(
        pytest.param([op, ga.SaveChanges()], id=f"save-{op}")
    )


@pytest.mark.parametrize("actions", save_operations)
def test_savable_operations(
    both_cams: RodTrackWindow,
    qtbot: QtBot,
    monkeypatch: MonkeyPatch,
    tmp_path: pathlib.Path,
    actions: List[ga.UserAction],
):
    try:
        for action in actions:
            both_cams = action.run(both_cams, qtbot, monkeypatch, tmp_path)
    finally:
        # teardown
        teardown_replacements(monkeypatch)
