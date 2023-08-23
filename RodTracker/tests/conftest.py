#  Copyright (c) 2023 Adrian Niemann Dmitry Puzyrev
#
#  This file is part of RodTracker.
#  RodTracker is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  RodTracker is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with RodTracker.  If not, see <http://www.gnu.org/licenses/>.

"""Put fixtures here, that should be available to (all) tests."""
import sys
import random
from typing import List
from pathlib import Path
import pandas as pd
import pytest
from pytestqt.qtbot import QtBot
from RodTracker.ui.mainwindow import RodTrackWindow
import RodTracker.backend.rod_data as r_data
import gui_actions as ga

if sys.version_info < (3, 9):
    # importlib.resources either doesn't exist or lacks the files()
    # function, so use the PyPI version:
    import importlib_resources
else:
    # importlib.resources has files(), so use that:
    import importlib.resources as importlib_resources

    if sys.version_info >= (3, 11):
        importlib_resources.path = (
            lambda module, file: importlib_resources.files(module).joinpath(
                file
            )
        )


random.seed(1)

cam1_img1 = importlib_resources.files(
    "RodTracker.resources.example_data.images.gp3"
).joinpath("0500.jpg")
cam2_img1 = importlib_resources.files(
    "RodTracker.resources.example_data.images.gp4"
).joinpath("0500.jpg")
csv_data = importlib_resources.files(
    "RodTracker.resources.example_data"
).joinpath("csv")


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
    previous_settings = main_window.settings._contents.copy()
    main_window.settings.update_field(
        category="visual", field="position_scaling", value=10.0
    )
    yield main_window
    main_window.settings.save(new_data=previous_settings)
    r_data.lock.lockForRead()
    r_data.rod_data = None
    r_data.lock.unlock()


@pytest.fixture()
def one_cam(qtbot: QtBot, main_window: RodTrackWindow) -> RodTrackWindow:
    """Provides a RodTracker GUI with loaded rods and images for first camera.
    The first camera view is active.
    """
    # Open images in the first camera
    main_window.image_managers[0].open_image_folder(cam1_img1)
    main_window.original_size()

    # Open rod position data
    main_window.rod_data.open_rod_folder(Path(csv_data))
    qtbot.wait(200)
    yield main_window
    r_data.lock.lockForRead()
    r_data.rod_data = None
    r_data.lock.unlock()


@pytest.fixture()
def both_cams(qtbot: QtBot, main_window: RodTrackWindow) -> RodTrackWindow:
    """Provides a RodTracker GUI with loaded rods and images for both cameras.
    The first camera view is active.
    """
    # Open images in the first camera
    main_window.image_managers[0].open_image_folder(cam1_img1)
    main_window.original_size()
    qtbot.wait(50)
    # Open images in the second camera
    main_window = ga.SwitchCamera().run(main_window, qtbot)
    qtbot.wait(50)
    main_window.image_managers[1].open_image_folder(cam2_img1)
    main_window.original_size()
    qtbot.wait(50)
    main_window = ga.SwitchCamera().run(main_window, qtbot)
    qtbot.wait(50)

    # Open rod position data
    main_window.rod_data.open_rod_folder(Path(csv_data))
    qtbot.wait(1000)

    yield main_window
    r_data.lock.lockForRead()
    r_data.rod_data = None
    r_data.lock.unlock()


def load_rod_data(colors: List[str]):
    data = pd.DataFrame()
    folder = importlib_resources.files("RodTracker.resources.example_data.csv")
    for color in colors:
        tmp_data_file = folder.joinpath(f"rods_df_{color}.csv")
        tmp_data = pd.read_csv(tmp_data_file, index_col=0)
        tmp_data["color"] = color
        data = pd.concat([data, tmp_data])
    data.reset_index(inplace=True)
    return data


@pytest.fixture()
def testing_data() -> pd.DataFrame:
    return load_rod_data(
        [
            "red",
        ]
    )
