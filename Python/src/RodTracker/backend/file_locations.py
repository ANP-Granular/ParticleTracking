#  Copyright (c) 2021 Adrian Niemann Dmitry Puzyrev
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

import sys
if sys.version_info < (3, 9):
    # importlib.resources either doesn't exist or lacks the files()
    # function, so use the PyPI version:
    import importlib_resources
else:
    # importlib.resources has files(), so use that:
    import importlib.resources as importlib_resources

_readme_path = "/README.md"
try:
    _base_path = sys._MEIPASS
except AttributeError:
    _base_path = "./Python"


def icon_path() -> str:
    return str(importlib_resources.files(
        "RodTracker.resources").joinpath("icon_main.ico"))


def readme_path() -> str:
    if hasattr(sys, "_MEIPASS"):
        return _base_path + _readme_path
    return _base_path + "/.." + _readme_path


def undo_icon_path() -> str:
    return str(importlib_resources.files(
        "RodTracker.resources").joinpath("left-arrow-96.png"))


def cam1_image1_path() -> str:
    return str(importlib_resources.files(
        "RodTracker.resources.example_data.images.gp3").joinpath("00500.jpg"))
