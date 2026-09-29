import json

from PyQt5 import QtCore
from pytest import MonkeyPatch

from RodTracker.ui.mainwindow import RodTrackWindow


def test_fit_inactive_camera_uses_visible_viewport(
    main_window: RodTrackWindow,
    monkeypatch: MonkeyPatch,
):
    main_window.ui.camera_tabs.setCurrentIndex(0)
    fitted_sizes = []
    monkeypatch.setattr(
        main_window.cameras[1], "scale_to_size", fitted_sizes.append
    )

    main_window.fit_to_window(1)

    visible_size = main_window.ui.sa_camera_0.size()
    assert fitted_sizes == [
        QtCore.QSize(visible_size.width() - 20, visible_size.height() - 20)
    ]


def test_session_round_trip(
    main_window: RodTrackWindow,
    monkeypatch: MonkeyPatch,
    tmp_path,
):
    image_folders = [tmp_path / "camera_0", tmp_path / "camera_1"]
    for folder in image_folders:
        folder.mkdir()
    rod_data_folder = tmp_path / "rod_data"
    rod_data_folder.mkdir()
    calibration = tmp_path / "calibration.json"
    calibration.write_text("{}")
    transformation = tmp_path / "transformation.json"
    transformation.write_text("{}")
    session_path = tmp_path / "session.json"
    last_session_path = tmp_path / "last_session.json"
    monkeypatch.setattr(
        RodTrackWindow,
        "_last_session_path",
        property(lambda _: last_session_path),
    )

    for manager, folder in zip(main_window.image_managers, image_folders):
        manager.folder = folder
    main_window.rod_data.folder = rod_data_folder
    main_window.ui.le_calibration.setText(str(calibration))
    main_window.ui.le_transformation.setText(str(transformation))
    main_window.save_session(session_path)
    main_window.ui.camera_tabs.setCurrentIndex(1)

    with session_path.open() as session_file:
        manifest = json.load(session_file)
    assert manifest["image_folders"] == [
        str(folder) for folder in image_folders
    ]
    assert manifest["rod_data_folder"] == str(rod_data_folder)

    loaded_images = []
    loaded_data = []
    loaded_calibration = []
    loaded_transformation = []
    fitted_cameras = []
    monkeypatch.setattr(
        main_window,
        "fit_to_window",
        lambda camera_index=None: fitted_cameras.append(camera_index),
    )

    def image_folder_opened(camera_index, folder):
        loaded_images.append((camera_index, folder))
        manager = main_window.image_managers[camera_index]
        manager.data_loaded.emit(10, folder.name, folder)
        manager.next_img[int, int].emit(500, 0)

    monkeypatch.setattr(
        main_window.image_managers[0],
        "open_image_folder",
        lambda folder: image_folder_opened(0, folder),
    )
    monkeypatch.setattr(
        main_window.image_managers[1],
        "open_image_folder",
        lambda folder: image_folder_opened(1, folder),
    )
    monkeypatch.setattr(
        main_window.rod_data,
        "open_rod_folder",
        lambda folder: loaded_data.append(folder),
    )
    if main_window.reconstructor is not None:
        monkeypatch.setattr(
            main_window.reconstructor,
            "set_calibration",
            lambda path: loaded_calibration.append(path),
        )
        monkeypatch.setattr(
            main_window.reconstructor,
            "set_transformation",
            lambda path: loaded_transformation.append(path),
        )

    assert main_window.open_session(session_path)
    assert loaded_images == list(enumerate(image_folders))
    assert main_window.ui.camera_tabs.currentIndex() == 1
    assert [cam.cam_id for cam in main_window.cameras] == [
        folder.name for folder in image_folders
    ]
    assert [cam.logger.frame for cam in main_window.cameras] == [500, 500]
    assert fitted_cameras == [0, 1]
    assert loaded_data == [rod_data_folder]
    assert loaded_calibration == [str(calibration)]
    assert loaded_transformation == [str(transformation)]

    main_window.open_last_session()
    assert loaded_images == list(enumerate(image_folders)) * 2
    assert fitted_cameras == [0, 1, 0, 1]
    assert loaded_data == [rod_data_folder] * 2
