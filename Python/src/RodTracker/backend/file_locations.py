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

_icon_path = "/resources/icon_main.ico"
_readme_path = "/README.md"
_undo_icon_path = "/resources/left-arrow-96.png"
try:
    _base_path = sys._MEIPASS
except AttributeError:
    _base_path = "./Python"


def icon_path() -> str:
    return _base_path + _icon_path


def readme_path() -> str:
    if hasattr(sys, "_MEIPASS"):
        return _base_path + _readme_path
    return _base_path + "/.." + _readme_path


def undo_icon_path() -> str:
    return _base_path + _undo_icon_path
