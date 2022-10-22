"""Pre- and post-user-action test code."""
import pathlib
from typing import Union
import numpy as np
from PyQt5 import QtCore
from RodTracker.ui.mainwindow import RodTrackWindow
import RodTracker.backend.data_operations as d_ops
import RodTracker.backend.file_operations as f_ops
import RodTracker.ui.rodnumberwidget as rn
from RodTracker.backend.logger import NumberChangeActions


def get_rod_position(main_window: RodTrackWindow, rod_id: int):
    rods = main_window.current_camera.edits
    for rod in rods:
        if rod.rod_id == rod_id:
            return rod.rod_points
    return None


def compute_desired_position(main_window: RodTrackWindow, start: QtCore.QPoint,
                             end: QtCore.QPoint) -> np.ndarray:
    cam = main_window.current_camera
    position_scaling = cam._position_scaling
    image_scaling = cam._scale_factor
    image_offset = np.asarray(cam._offset)
    intended_pos = np.array([start.x(), start.y(), end.x(), end.y()])
    intended_pos = intended_pos - np.concatenate((image_offset, image_offset))
    intended_pos = intended_pos / (position_scaling * image_scaling)
    return intended_pos


def pre_create(main_window: RodTrackWindow, new_id: int):
    cam = main_window.current_camera
    frame = main_window.logger.frame
    color = main_window.get_selected_color()
    # rod not loaded on the screen
    rod_ids = [rod.rod_id for rod in cam.edits]
    assert new_id not in rod_ids
    # rod not in loaded dataset
    with QtCore.QReadLocker(d_ops.lock):
        relevant_data = d_ops.rod_data.loc[
            (d_ops.rod_data.frame == frame) &
            (d_ops.rod_data.color == color), "particle"]
        assert new_id not in relevant_data
    return


def post_create(main_window: RodTrackWindow, new_id: int,
                start: QtCore.QPoint, end: QtCore.QPoint):
    cam = main_window.current_camera
    frame = main_window.logger.frame
    color = main_window.get_selected_color()

    # rod loaded on the screen
    rod_ids = [rod.rod_id for rod in cam.edits]
    assert new_id in rod_ids

    # rod is still selected
    selected_id = [rod.rod_id for rod in cam.edits if rod.rod_state ==
                   rn.RodState.SELECTED]
    assert (len(selected_id) == 1) and (selected_id[0] == new_id)

    # rod was inserted in the tree view
    items_tree = main_window.ui.tv_rods.findItems(str(new_id),
                                                  QtCore.Qt.MatchContains)
    assert len(items_tree) == 1

    # rod is correctly positioned
    new_pos = get_rod_position(main_window, new_id)
    intended_pos = compute_desired_position(main_window, start, end)
    np.testing.assert_allclose(np.asarray(new_pos), intended_pos)

    # rod is inserted in the loaded dataset
    with QtCore.QReadLocker(d_ops.lock):
        relevant_data = d_ops.rod_data.loc[
            (d_ops.rod_data.frame == frame) &
            (d_ops.rod_data.color == color)]
        assert new_id in relevant_data.particle
        data_pos = relevant_data.loc[relevant_data.particle == new_id,
                                     [f"x1_{cam.cam_id}", f"y1_{cam.cam_id}",
                                      f"x2_{cam.cam_id}", f"y2_{cam.cam_id}"]]
        np.testing.assert_allclose(np.asarray(data_pos).squeeze(),
                                   intended_pos)
    return


def pre_delete(main_window: RodTrackWindow, rod_id: int):
    cam = main_window.current_camera
    rod_ids = [rod.rod_id for rod in cam.edits]
    assert rod_id in rod_ids


def post_delete(main_window: RodTrackWindow, rod_id: int):
    cam = main_window.current_camera
    for rod in cam.edits:
        if rod.rod_id == rod_id:
            assert rod.rod_points == 4 * [0]
            return
    raise AssertionError(f"Rod #{rod_id} was not found but should be at"
                         f" [0, 0, 0, 0]")


def pre_pos_change(main_window: RodTrackWindow, rod_id: int):
    cam = main_window.current_camera
    rod_ids = [rod.rod_id for rod in cam.edits]
    assert rod_id in rod_ids


def post_pos_change(main_window: RodTrackWindow, rod_id: int,
                    start: QtCore.QPoint, end: QtCore.QPoint):
    new_pos = get_rod_position(main_window, rod_id)
    intended_pos = compute_desired_position(main_window, start, end)
    np.testing.assert_allclose(np.asarray(new_pos), intended_pos)


def pre_number_switch(main_window: RodTrackWindow, rod_id: int, new_id: int)\
        -> dict:
    cam = main_window.current_camera
    rod_ids = [rod.rod_id for rod in cam.edits]
    assert rod_id in rod_ids
    initial_state = {}
    with QtCore.QReadLocker(d_ops.lock):
        data = d_ops.rod_data.copy()
        initial_state["dataset"] = data.loc[data.color ==
                                            main_window.get_selected_color()]
    initial_state["rod1_pos"] = get_rod_position(main_window, rod_id)

    if new_id in rod_ids:
        initial_state["rod2_pos"] = get_rod_position(main_window, new_id)
    else:
        initial_state["rod2_pos"] = 4 * [0]
    return initial_state


def post_number_switch(main_window: RodTrackWindow, rod_id: int, new_id: int,
                       mode: Union[NumberChangeActions, None],
                       initial_state: dict):
    # currently displayed/loaded
    rod1_new_pos = get_rod_position(main_window, rod_id)
    if mode is not None:
        rod2_new_pos = get_rod_position(main_window, new_id)
        assert rod1_new_pos == initial_state["rod2_pos"]
        assert rod2_new_pos == initial_state["rod1_pos"]
    else:
        cam = main_window.current_camera
        rod_ids = [rod.rod_id for rod in cam.edits]
        if new_id in rod_ids:
            rod2_new_pos = get_rod_position(main_window, new_id)
            assert rod1_new_pos == initial_state["rod1_pos"]
            assert rod2_new_pos == initial_state["rod2_pos"]
        else:
            assert rod1_new_pos == initial_state["rod1_pos"]

    with QtCore.QReadLocker(d_ops.lock):
        new_data = d_ops.rod_data.copy()
    new_data = new_data.loc[new_data.color == main_window.get_selected_color()]
    frame = main_window.logger.frame
    cam_id = main_window.current_camera.cam_id
    if cam_id == "gp3":
        cam2_id = "gp4"
    elif cam_id == "gp4":
        cam2_id = "gp3"
    else:
        raise AssertionError(f"Unknown camera combination used: "
                             f"cam1 = {cam_id}")
    cam1_cols = [f"x1_{cam_id}", f"y1_{cam_id}", f"x2_{cam_id}",
                 f"y2_{cam_id}"]
    cam2_cols = [f"x1_{cam2_id}", f"y1_{cam2_id}", f"x2_{cam2_id}",
                 f"y2_{cam2_id}"]
    if mode is None:
        assert (new_data == initial_state["dataset"]).all(axis=None)

    elif mode is NumberChangeActions.ALL:
        # Check not altered frames
        unchanged = new_data.loc[new_data.frame < frame]
        unchanged_init = initial_state["dataset"].loc[
            initial_state["dataset"].frame < frame]
        assert (unchanged == unchanged_init).all(axis=None)

        # Check altered frames
        changed_frame = new_data.loc[(new_data.frame >= frame)]
        changed_frame_init = initial_state["dataset"].loc[
            initial_state["dataset"].frame >= frame]

        ch_r1 = changed_frame.loc[(changed_frame.particle == rod_id),
                                  [*cam1_cols, *cam2_cols]]
        ch_r2 = changed_frame.loc[(changed_frame.particle == new_id),
                                  [*cam1_cols, *cam2_cols]]
        in_r1 = changed_frame_init.loc[(changed_frame_init.particle == rod_id),
                                       [*cam1_cols, *cam2_cols]]
        in_r2 = changed_frame_init.loc[(changed_frame_init.particle == new_id),
                                       [*cam1_cols, *cam2_cols]]

        assert (ch_r1.to_numpy() == in_r2.to_numpy()).all(axis=None)
        assert (ch_r2.to_numpy() == in_r1.to_numpy()).all(axis=None)

    elif mode is NumberChangeActions.ALL_ONE_CAM:
        # Check not altered frames
        unchanged = new_data.loc[new_data.frame < frame]
        unchanged_init = initial_state["dataset"].loc[
            initial_state["dataset"].frame < frame]
        assert (unchanged == unchanged_init).all(axis=None)

        # Check second, unaltered camera in altered frames
        changed_frame = new_data.loc[(new_data.frame >= frame)]
        changed_frame_init = initial_state["dataset"].loc[
            initial_state["dataset"].frame >= frame]

        cam2_data = changed_frame[cam2_cols]
        cam2_data_init = changed_frame_init[cam2_cols]
        assert (cam2_data == cam2_data_init).all(axis=None)

        # Check altered camera in altered frame
        ch_r1 = changed_frame.loc[(changed_frame.particle == rod_id),
                                  cam1_cols]
        ch_r2 = changed_frame.loc[(changed_frame.particle == new_id),
                                  cam1_cols]
        in_r1 = changed_frame_init.loc[(changed_frame_init.particle == rod_id),
                                       cam1_cols]
        in_r2 = changed_frame_init.loc[(changed_frame_init.particle == new_id),
                                       cam1_cols]

        assert (ch_r1.to_numpy() == in_r2.to_numpy()).all(axis=None)
        assert (ch_r2.to_numpy() == in_r1.to_numpy()).all(axis=None)

    elif mode is NumberChangeActions.ONE_BOTH_CAMS:
        # Check not altered frames
        unchanged = new_data.loc[new_data.frame != frame]
        unchanged_init = initial_state["dataset"].loc[
            initial_state["dataset"].frame != frame]
        assert (unchanged == unchanged_init).all(axis=None)

        # Check altered frame
        changed_frame = new_data.loc[(new_data.frame == frame)]
        changed_frame_init = initial_state["dataset"].loc[
            initial_state["dataset"].frame == frame]
        ch_r1 = changed_frame.loc[(changed_frame.particle == rod_id),
                                  [*cam1_cols, *cam2_cols]]
        ch_r2 = changed_frame.loc[(changed_frame.particle == new_id),
                                  [*cam1_cols, *cam2_cols]]
        in_r1 = changed_frame_init.loc[(changed_frame_init.particle == rod_id),
                                       [*cam1_cols, *cam2_cols]]
        in_r2 = changed_frame_init.loc[(changed_frame_init.particle == new_id),
                                       [*cam1_cols, *cam2_cols]]
        assert (ch_r1.to_numpy() == in_r2.to_numpy()).all(axis=None)
        assert (ch_r2.to_numpy() == in_r1.to_numpy()).all(axis=None)

    elif mode is NumberChangeActions.CURRENT:
        # Check not altered frames
        unchanged = new_data.loc[new_data.frame != frame]
        unchanged_init = initial_state["dataset"].loc[
            initial_state["dataset"].frame != frame]
        assert (unchanged == unchanged_init).all(axis=None)

        # Check second, unaltered camera in altered frame
        changed_frame = new_data.loc[(new_data.frame == frame)]
        changed_frame_init = initial_state["dataset"].loc[
            initial_state["dataset"].frame == frame]
        cam2_data = changed_frame[cam2_cols]
        cam2_data_init = changed_frame_init[cam2_cols]
        assert (cam2_data == cam2_data_init).all(axis=None)

        # Check altered camera in altered frame
        ch_r1 = changed_frame.loc[(changed_frame.particle == rod_id),
                                  cam1_cols]
        ch_r2 = changed_frame.loc[(changed_frame.particle == new_id),
                                  cam1_cols]
        in_r1 = changed_frame_init.loc[(changed_frame_init.particle == rod_id),
                                       cam1_cols]
        in_r2 = changed_frame_init.loc[(changed_frame_init.particle == new_id),
                                       cam1_cols]

        assert (ch_r1.to_numpy() == in_r2.to_numpy()).all(axis=None)
        assert (ch_r2.to_numpy() == in_r1.to_numpy()).all(axis=None)

    else:
        raise AssertionError(f"Unknown mode ({mode}) supplied.")


def pre_save(main_window: RodTrackWindow):
    """Collection of assertions before saving. Currently not used."""
    return


def post_save(main_window: RodTrackWindow, save_path: pathlib.Path,
              inital_state):
    # No more "unsaved changes"
    # Note: The following check for unsaved actions was made complicated
    #       because in the current setup multiple tests are run in one test
    #       function. The RodTrackerWindow object therefore does not get
    #       destroyed & recomputed but reused. This leads to a buildup of
    #       logger objects with potentially unsaved actions.
    #       unsaved = len(main_window.ui.lv_actions_list.unsaved_changes)
    unsaved = len([action for logger in
                   main_window.ui.lv_actions_list._loggers[-3:]
                   for action in logger.unsaved_changes])
    assert unsaved == 0

    # Marker for unsaved changes is removed
    for tab_idx in range(main_window.ui.camera_tabs.count()):
        tab_txt = main_window.ui.camera_tabs.tabText(tab_idx)
        assert not tab_txt.endswith("*")

    # Written data matches currently loaded data
    out_dir = save_path / "unused"
    out_dir.mkdir(exist_ok=True)
    w_data, _ = f_ops.get_color_data(save_path, out_dir)
    # Replace truth values represented as strings
    w_data.replace(["True", "1", "1.0"], 1., inplace=True)
    w_data.replace(["False", "0", "0.0"], 0., inplace=True)
    w_data.sort_values(by=["color", "frame", "particle"], inplace=True)
    w_data.reset_index(drop=True, inplace=True)
    w_data_np = w_data.drop(columns="color").to_numpy()
    with QtCore.QReadLocker(d_ops.lock):
        rod_data = d_ops.rod_data
        rod_data.sort_values(by=["color", "frame", "particle"], inplace=True)
        rod_data.reset_index(drop=True, inplace=True)
        rod_data_np = rod_data.drop(columns="color").to_numpy(
            dtype=float, na_value=np.nan)
        # accounts for loss of precision during saving
        np.testing.assert_allclose(w_data_np, rod_data_np, equal_nan=True)
        assert (w_data.color == d_ops.rod_data.color).all()


def pre_undo(main_window: RodTrackWindow):
    # TODO
    pass


def post_undo(main_window: RodTrackWindow, inital_state):
    # TODO
    pass


def pre_redo(main_window: RodTrackWindow):
    # TODO
    pass


def post_redo(main_window: RodTrackWindow, inital_state):
    # TODO
    pass


def pre_switch_frame(main_window: RodTrackWindow):
    initial_state = {
        "frame": main_window.logger.frame,
    }
    return initial_state


def post_switch_frame(main_window: RodTrackWindow, direction: int,
                      inital_state: dict):
    id_idx = main_window.current_file_ids.index(inital_state["frame"])
    intended_frame = main_window.current_file_ids[id_idx + direction]
    assert main_window.current_camera.logger.frame == intended_frame
    assert main_window.logger.frame == intended_frame


def pre_switch_color(main_window: RodTrackWindow):
    initial_state = {
        "rb_color": main_window.get_selected_color(),
        "rod_color": main_window.current_camera.edits[0].color
    }
    assert initial_state["rb_color"] == initial_state["rod_color"]
    return initial_state


def post_switch_color(main_window: RodTrackWindow, color: str,
                      initial_state: dict):
    assert main_window.get_selected_color() == color
    for rod in main_window.current_camera.edits:
        assert rod.color == color


def pre_switch_cam(main_window: RodTrackWindow) -> dict:
    initial_state = {
        "tab_pos": main_window.ui.camera_tabs.currentIndex(),
        "cam_id": main_window.current_camera.cam_id
    }
    return initial_state


def post_switch_cam(main_window: RodTrackWindow, inital_state: dict):
    assert inital_state["tab_pos"] != main_window.ui.camera_tabs.currentIndex()


def pre_length_adjustment(main_window: RodTrackWindow):
    # TODO
    pass


def post_length_adjustment(main_window: RodTrackWindow, initial_state):
    # TODO
    pass
