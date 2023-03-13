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

import sys
import pathlib
import importlib


def test_path_addition():
    import RodTracker.RodTracker
    assert str(pathlib.Path(RodTracker.RodTracker.__file__).parent.parent)\
        in sys.path


def test_tmp_dir_create():
    # Clean temporary files from potential previous RodTracker runs/imports
    import RodTracker
    for handler in RodTracker.logger.handlers:
        RodTracker.logger.removeHandler(handler)
        handler.close()
    for file in RodTracker.TEMP_DIR.iterdir():
        if file.is_file():
            file.unlink()
        elif file.is_dir():
            for inner_file in file.iterdir():
                inner_file.unlink()
            file.rmdir()
    RodTracker.TEMP_DIR.rmdir()

    importlib.reload(RodTracker)
    assert RodTracker.TEMP_DIR.exists()
    assert RodTracker.LOG_PATH.exists()
