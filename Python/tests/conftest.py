"""Put fixtures here, that should be available to (all) tests."""
import sys
import pytest
from pytestqt.qtbot import QtBot
from RodTracker.ui.mainwindow import RodTrackWindow
import gui_actions as ga

if sys.version_info < (3, 9):
    # importlib.resources either doesn't exist or lacks the files()
    # function, so use the PyPI version:
    import importlib_resources
else:
    # importlib.resources has files(), so use that:
    import importlib.resources as importlib_resources

cam1_img1 = importlib_resources.files(
    "RodTracker.resources.example_data.images.gp3").joinpath("0500.jpg")
cam2_img1 = importlib_resources.files(
    "RodTracker.resources.example_data.images.gp4").joinpath("0500.jpg")
csv_data = importlib_resources.files(
    "RodTracker.resources.example_data").joinpath("csv")


@pytest.fixture()
def main_window(qtbot: QtBot) -> RodTrackWindow:
    """Provides the a RodTracker GUI without loaded rods or images
    The first camera view is active.
    """
    main_window = RodTrackWindow()
    main_window.show()
    qtbot.addWidget(main_window)

    def wait_maximized():
        assert main_window.isMaximized()

    qtbot.waitUntil(wait_maximized)
    yield main_window


@pytest.fixture()
def one_cam(qtbot: QtBot, main_window: RodTrackWindow) -> RodTrackWindow:
    """Provides a RodTracker GUI with loaded rods and images for first camera.
    The first camera view is active.
    """
    # Open images in the first camera
    main_window.open_image_folder(cam1_img1)
    main_window.original_size()

    # Open rod position data
    main_window.original_data = csv_data
    main_window.open_rod_folder()
    qtbot.wait(200)
    yield main_window


@pytest.fixture()
def both_cams(qtbot: QtBot, main_window: RodTrackWindow) -> RodTrackWindow:
    """Provides a RodTracker GUI with loaded rods and images for both cameras.
    The first camera view is active.
    """
    # Open images in the first camera
    main_window.open_image_folder(cam1_img1)
    main_window.original_size()
    qtbot.wait(50)
    # Open images in the second camera
    main_window = ga.SwitchCamera().run(main_window, qtbot)
    main_window.open_image_folder(cam2_img1)
    main_window.original_size()
    qtbot.wait(50)
    main_window = ga.SwitchCamera().run(main_window, qtbot)
    # Open rod position data
    main_window.original_data = csv_data
    main_window.open_rod_folder()
    qtbot.wait(200)

    yield main_window
