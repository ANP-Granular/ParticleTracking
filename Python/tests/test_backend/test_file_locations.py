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

import importlib
import os
import sys
from pytest import MonkeyPatch
import RodTracker.backend.file_locations as fl


def test_icon_exists():
    assert os.path.exists(fl.icon_path())


def test_readme_exists():
    assert os.path.exists(fl.readme_path())


def test_undo_icon_exists():
    assert os.path.exists(fl.undo_icon_path())


def test_readme_bundled(monkeypatch: MonkeyPatch):
    with monkeypatch.context() as m:
        m.setattr(sys, "_MEIPASS", "test_path", raising=False)
        import RodTracker.backend.file_locations as fl
        # Force reload to achieve code execution with proper environment
        importlib.reload(fl)
        readme_path = fl.readme_path()
    assert readme_path.startswith("test_path")
