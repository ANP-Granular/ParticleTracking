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

"""A collection of actions performed by users in the GUI."""
import pathlib
from typing import Protocol
from warnings import warn

import action_assertions as aa
from PyQt5 import QtCore, QtWidgets
from pytest import MonkeyPatch
from pytestqt.qtbot import QtBot

from RodTracker.backend.logger import NumberChangeActions
from RodTracker.ui import dialogs
from RodTracker.ui.mainwindow import RodTrackWindow


class UserAction(Protocol):
    def run(
        self,
        main_window: RodTrackWindow,
        qtbot: QtBot,
        monkeypatch: MonkeyPatch,
        tmp_path: pathlib.Path,
    ) -> RodTrackWindow:
        pass


class CreateRod:
    """Create a new rod with the given ID in the currently active camera."""

    def __init__(
        self,
        new_id: int,
        start: QtCore.QPoint = QtCore.QPoint(500, 500),
        end: QtCore.QPoint = QtCore.QPoint(550, 550),
        assertions: bool = True,
    ) -> None:
        self.new_id = new_id
        self.start = start
        self.end = end
        self.assertions = assertions

    def __str__(self):
        return f"CreateRod({self.new_id})"

    def run(
        self,
        main_window: RodTrackWindow,
        qtbot: QtBot,
        monkeypatch: MonkeyPatch,
        tmp_path: pathlib.Path,
    ) -> RodTrackWindow:
        if self.assertions:
            aa.pre_create(main_window, self.new_id)

        cam_idx = main_window.ui.camera_tabs.currentIndex()
        cam = main_window.cameras[cam_idx]

        # Deactivate rod, if necessary
        qtbot.mouseClick(
            cam, QtCore.Qt.MouseButton.RightButton, pos=self.start
        )

        with monkeypatch.context() as mp:
            # Mock number selection
            mp.setattr(
                QtWidgets.QInputDialog,
                "getInt",
                lambda *args, **kwargs: (
                    self.new_id,
                    QtWidgets.QDialog.Accepted,
                ),
            )
            # Create rod
            with qtbot.wait_signals(
                [
                    main_window.rod_data.data_2d,
                    main_window.rod_data.data_update,
                ]
            ):
                qtbot.mouseClick(
                    cam, QtCore.Qt.MouseButton.LeftButton, pos=self.start
                )
                qtbot.mouseMove(cam, self.end)
                qtbot.mouseClick(
                    cam, QtCore.Qt.MouseButton.LeftButton, pos=self.end
                )
        if self.assertions:
            aa.post_create(main_window, self.new_id, self.start, self.end)
        return main_window


class DeleteRod:
    def __init__(self, rod_id: int, assertions: bool = True) -> None:
        self.rod_id = rod_id
        self.assertions = assertions

    def __str__(self):
        return f"DeleteRod({self.rod_id})"

    def run(
        self,
        main_window: RodTrackWindow,
        qtbot: QtBot,
        monkeypatch: MonkeyPatch = None,
        tmp_path: pathlib.Path = None,
    ) -> RodTrackWindow:
        """Delete the rod with the given ID in the currently active camera."""
        if self.assertions:
            aa.pre_delete(main_window, self.rod_id)
        cam_idx = main_window.ui.camera_tabs.currentIndex()
        cam = main_window.cameras[cam_idx]
        rods = cam.rods
        act_count = main_window.ui.lv_actions_list.count()

        def increase_count():
            """Callback for waiting until a new action has been logged."""
            assert main_window.ui.lv_actions_list.count() > act_count

        for rod in rods:
            if rod.rod_id == self.rod_id:
                qtbot.mouseDClick(rod, QtCore.Qt.MouseButton.LeftButton)
                qtbot.keyClick(rod, QtCore.Qt.Key_Delete)
                qtbot.keyClick(rod, QtCore.Qt.Key_Enter)
                qtbot.wait_until(increase_count, timeout=2000)
                if self.assertions:
                    aa.post_delete(main_window, self.rod_id)
                return main_window
        warn(f"The rod #{self.rod_id} was not found. No rod has been deleted.")
        return main_window


class ChangeRodPosition:
    def __init__(
        self,
        rod_id: int,
        start: QtCore.QPoint = QtCore.QPoint(500, 500),
        end: QtCore.QPoint = QtCore.QPoint(550, 550),
        assertions: bool = True,
    ) -> None:
        self.rod_id = rod_id
        self.start = start
        self.end = end
        self.assertions = assertions

    def __str__(self):
        return f"ChangeRodPosition({self.rod_id})"

    def run(
        self,
        main_window: RodTrackWindow,
        qtbot: QtBot,
        monkeypatch: MonkeyPatch = None,
        tmp_path: pathlib.Path = None,
    ) -> RodTrackWindow:
        if self.assertions:
            aa.pre_pos_change(main_window, self.rod_id)
        cam_idx = main_window.ui.camera_tabs.currentIndex()
        cam = main_window.cameras[cam_idx]
        rods = cam.rods
        act_count = main_window.ui.lv_actions_list.count()

        def increased_count():
            """Callback for waiting until a new action has been logged."""
            assert main_window.ui.lv_actions_list.count() > act_count

        for rod in rods:
            if rod.rod_id == self.rod_id:
                qtbot.mouseClick(rod, QtCore.Qt.MouseButton.LeftButton)
                qtbot.mouseClick(
                    cam, QtCore.Qt.MouseButton.LeftButton, pos=self.start
                )
                qtbot.mouseClick(
                    cam, QtCore.Qt.MouseButton.LeftButton, pos=self.end
                )
                qtbot.keyClick(rod, QtCore.Qt.Key_Enter)
                qtbot.wait_until(increased_count, timeout=2000)
                if self.assertions:
                    aa.post_pos_change(
                        main_window, self.rod_id, self.start, self.end
                    )
                return main_window

        warn(
            f"The rod #{self.rod_id} was not found. "
            "No position update has been performed."
        )
        return main_window


class SwitchRodNumber:
    def __init__(
        self,
        rod_id: int,
        new_id: int,
        mode: NumberChangeActions = None,
        assertions: bool = True,
    ) -> None:
        self.rod_id = rod_id
        self.new_id = new_id
        self.mode = mode
        self.assertions = assertions

    def __str__(self):
        return f"SwitchRodNumber({self.rod_id}->{self.new_id})"

    def run(
        self,
        main_window: RodTrackWindow,
        qtbot: QtBot,
        monkeypatch: MonkeyPatch,
        tmp_path: pathlib.Path = None,
    ) -> RodTrackWindow:
        if self.assertions:
            state = aa.pre_number_switch(main_window, self.rod_id, self.new_id)
        cam_idx = main_window.ui.camera_tabs.currentIndex()
        cam = main_window.cameras[cam_idx]
        rods = cam.rods
        act_count = main_window.ui.lv_actions_list.count()

        def increased_count():
            """Callback for waiting until a new action has been logged."""
            assert main_window.ui.lv_actions_list.count() > act_count

        for rod in rods:
            if rod.rod_id == self.rod_id:
                my_dialog = dialogs.ConflictDialog(self.rod_id, self.new_id)
                mode_possibilities = {
                    NumberChangeActions.ALL: my_dialog.btn_switch_all,
                    NumberChangeActions.ALL_ONE_CAM: my_dialog.btn_one_cam,
                    NumberChangeActions.ONE_BOTH_CAMS: my_dialog.btn_both_cams,
                    NumberChangeActions.CURRENT: my_dialog.btn_only_this,
                    None: my_dialog.btn_cancel,
                }
                with monkeypatch.context() as mp:
                    mp.setattr(
                        dialogs,
                        "ConflictDialog",
                        lambda *args, **kwargs: my_dialog,
                    )
                    mp.setattr(my_dialog, "exec", lambda: None)
                    mp.setattr(
                        my_dialog,
                        "clickedButton",
                        lambda: mode_possibilities[self.mode],
                    )
                    qtbot.mouseDClick(rod, QtCore.Qt.MouseButton.LeftButton)
                    qtbot.keyClicks(rod, str(self.new_id))
                    qtbot.keyClick(rod, QtCore.Qt.Key_Enter)
                    if self.mode is not None:
                        qtbot.wait_until(increased_count, timeout=2000)
                    if self.assertions:
                        qtbot.wait(150)
                        aa.post_number_switch(
                            main_window,
                            self.rod_id,
                            self.new_id,
                            self.mode,
                            state,
                        )
                return main_window

        warn(
            f"The rod #{self.rod_id} was not found. "
            "No number switch has been performed."
        )
        return main_window


class SaveChanges:
    def __init__(self, assertions: bool = True) -> None:
        self.assertions = assertions

    def __str__(self) -> str:
        return "SaveChanges()"

    def run(
        self,
        main_window: RodTrackWindow,
        qtbot: QtBot,
        monkeypatch: MonkeyPatch,
        tmp_path: pathlib.Path,
    ) -> RodTrackWindow:
        if self.assertions:
            state = aa.pre_save(main_window)

        def contents_written():
            """Callback for waiting until files are written to the given
            path."""
            assert len(list(tmp_path.iterdir())) > 0

        main_window.ui.le_save_dir.clear()
        qtbot.keyClicks(main_window.ui.le_save_dir, str(tmp_path))
        with qtbot.wait_signal(main_window.rod_data.saved):
            qtbot.keyClick(
                main_window,
                QtCore.Qt.Key_S,
                modifier=QtCore.Qt.ControlModifier,
            )
        qtbot.wait_until(contents_written, timeout=2000)
        if self.assertions:
            aa.post_save(main_window, tmp_path, state)
        return main_window


class Undo:
    def __init__(self, assertions: bool = True) -> None:
        self.assertions = assertions

    def __str__(self) -> str:
        return "Undo()"

    def run(
        self,
        main_window: RodTrackWindow,
        qtbot: QtBot,
        monkeypatch: MonkeyPatch = None,
        tmp_path: pathlib.Path = None,
    ) -> RodTrackWindow:
        """Undo the last logged action in the current camera view."""
        if self.assertions:
            state = aa.pre_undo(main_window)

        cam_idx = main_window.ui.camera_tabs.currentIndex()
        cam = main_window.cameras[cam_idx]
        prev_act_count = main_window.ui.lv_actions_list.count()

        def decrease_count():
            """Callback for waiting until an action has been
            reverted/removed."""
            assert main_window.ui.lv_actions_list.count() < prev_act_count

        qtbot.keyClick(
            cam, QtCore.Qt.Key_Z, modifier=QtCore.Qt.ControlModifier
        )
        qtbot.wait_until(decrease_count, timeout=2000)
        qtbot.wait(250)
        if self.assertions:
            aa.post_undo(main_window, state)
        return main_window


class Redo:
    def __init__(self, assertions: bool = True) -> None:
        self.assertions = assertions

    def __str__(self) -> str:
        return "Redo()"

    def run(
        self,
        main_window: RodTrackWindow,
        qtbot: QtBot,
        monkeypatch: MonkeyPatch = None,
        tmp_path: pathlib.Path = None,
    ) -> RodTrackWindow:
        """Redo the last undone action in the current camera view."""
        if self.assertions:
            state = aa.pre_redo(main_window)

        cam_idx = main_window.ui.camera_tabs.currentIndex()
        cam = main_window.cameras[cam_idx]
        prev_act_count = main_window.ui.lv_actions_list.count()

        def increased_count():
            """Callback for waiting until an action has been
            reverted/removed."""
            assert main_window.ui.lv_actions_list.count() > prev_act_count

        qtbot.keyClick(
            cam,
            QtCore.Qt.Key_Z,
            modifier=(QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier),
        )
        qtbot.wait_until(increased_count, timeout=2000)
        qtbot.wait(250)

        if self.assertions:
            aa.post_undo(main_window, state)
        return main_window


class SwitchFrame:
    def __init__(self, direction: int, assertions: bool = True) -> None:
        self.direction = direction
        self.assertions = assertions

    def __str__(self) -> str:
        return f"SwitchFrame({self.direction})"

    def run(
        self,
        main_window: RodTrackWindow,
        qtbot: QtBot,
        monkeypatch: MonkeyPatch = None,
        tmp_path: pathlib.Path = None,
    ) -> RodTrackWindow:
        """Switch `direction` number of frames."""
        if self.assertions:
            state = aa.pre_switch_frame(main_window)

        direction_key = QtCore.Qt.Key_Right
        if self.direction < 0:
            direction_key = QtCore.Qt.Key_Left
        for _ in range(abs(self.direction)):
            qtbot.keyClick(main_window, direction_key)
            qtbot.wait(150)
        if self.assertions:
            aa.post_switch_frame(main_window, self.direction, state)
        return main_window


class SwitchColor:
    def __init__(self, color: str, assertions: bool = True) -> None:
        self.color = color
        self.assertions = assertions

    def __str__(self) -> str:
        return f"SwitchColor({self.color})"

    def run(
        self,
        main_window: RodTrackWindow,
        qtbot: QtBot,
        monkeypatch: MonkeyPatch = None,
        tmp_path: pathlib.Path = None,
    ) -> RodTrackWindow:
        """Switch the displayed rod color."""
        if self.assertions:
            state = aa.pre_switch_color(main_window)

        color_buttons = main_window.ui.group_rod_color
        to_press = None
        for rb in color_buttons.findChildren(QtWidgets.QRadioButton):
            if rb.objectName()[3:] == self.color:
                to_press = rb
        if to_press is None:
            warn(
                f"The color '{self.color}' was not found. "
                "No color switch has been performed."
            )
            return main_window
        qtbot.mouseClick(to_press, QtCore.Qt.MouseButton.LeftButton)
        qtbot.wait(150)
        if self.assertions:
            aa.post_switch_color(main_window, self.color, state)
        return main_window


class SwitchCamera:
    def __init__(self, assertions: bool = True) -> None:
        self.assertions = assertions

    def __str__(self) -> str:
        return "SwitchCamera()"

    def run(
        self,
        main_window: RodTrackWindow,
        qtbot: QtBot,
        monkeypatch: MonkeyPatch = None,
        tmp_path: pathlib.Path = None,
    ) -> RodTrackWindow:
        if self.assertions:
            state = aa.pre_switch_cam(main_window)

        with qtbot.wait_signal(main_window.ui.camera_tabs.currentChanged):
            qtbot.keyClick(
                main_window,
                QtCore.Qt.Key_Tab,
                modifier=QtCore.Qt.KeyboardModifier.ControlModifier,
            )

        if self.assertions:
            aa.post_switch_cam(main_window, state)

        return main_window


class LengthAdjustment:
    allowed_shortcuts = [
        QtCore.Qt.Key_A,
        QtCore.Qt.Key_S,
        QtCore.Qt.Key_R,
        QtCore.Qt.Key_T,
    ]

    def __init__(
        self, shortcut: int, rod: int = None, assertions: bool = True
    ) -> None:
        if shortcut not in self.allowed_shortcuts:
            raise ValueError(f"Given shortcut {shortcut} is not recognized.")
        self.rod = rod
        self.method = shortcut
        self.assertions = assertions

    def __str__(self):
        return f"LengthAdjustment({self.rod})"

    def run(
        self,
        main_window: RodTrackWindow,
        qtbot: QtBot,
        monkeypatch: MonkeyPatch = None,
        tmp_path: pathlib.Path = None,
    ) -> RodTrackWindow:
        if self.assertions:
            state = aa.pre_length_adjustment(main_window)
        if self.rod is not None:
            cam_idx = main_window.ui.camera_tabs.currentIndex()
            cam = main_window.cameras[cam_idx]
            rods = cam.rods
            for rod in rods:
                if rod.rod_id == self.rod:
                    qtbot.mouseClick(rod, QtCore.Qt.MouseButton.LeftButton)
                    break

        qtbot.keyClick(main_window, self.method)
        if self.assertions:
            aa.post_length_adjustment(main_window, state)
        return main_window


class SelectInTree:
    def __init__(self) -> None:
        # TODO
        pass

    def __str__(self) -> str:
        return "SelectInTree()"

    def run(
        self,
        main_window: RodTrackWindow,
        qtbot: QtBot = None,
        monkeypatch: MonkeyPatch = None,
        tmp_path: pathlib.Path = None,
    ) -> RodTrackWindow:
        # TODO
        return main_window


class OpenImage:
    def __init__(
        self, img_path: pathlib.Path, assertions: bool = True
    ) -> None:
        self.img_path = img_path
        self.assertions = assertions

    def __str__(self) -> str:
        return f"OpenImage({self.img_path.name})"

    def run(
        self,
        main_window: RodTrackWindow,
        qtbot: QtBot,
        monkeypatch: MonkeyPatch,
        tmp_path: pathlib.Path = None,
    ) -> RodTrackWindow:
        # TODO: wait for loading complete
        with monkeypatch.context() as mp:
            mp.setattr(
                QtWidgets.QFileDialog,
                "getOpenFileName",
                lambda *args, **kwargs: (str(self.img_path), None),
            )
            qtbot.mouseClick(
                main_window.ui.pb_load_images, QtCore.Qt.MouseButton.LeftButton
            )
        main_window.original_size()
        qtbot.wait(50)
        return main_window


class OpenData:
    def __init__(
        self, data_path: pathlib.Path, assertions: bool = True
    ) -> None:
        self.data_path = data_path
        self.assertions = assertions

    def __str__(self) -> str:
        return f"OpenData({self.data_path.name})"

    def run(
        self,
        main_window: RodTrackWindow,
        qtbot: QtBot,
        monkeypatch: MonkeyPatch,
        tmp_path: pathlib.Path = None,
    ) -> RodTrackWindow:
        # TODO: wait for loading complete
        with monkeypatch.context() as mp:
            mp.setattr(
                QtWidgets.QFileDialog,
                "getExistingDirectory",
                lambda *args, **kwargs: str(self.data_path),
            )
            # avoid blocking
            mp.setattr(dialogs, "show_warning", lambda *args, **kwargs: None)
            qtbot.mouseClick(
                main_window.ui.pb_load_rods, QtCore.Qt.MouseButton.LeftButton
            )
        qtbot.wait(200)
        return main_window
