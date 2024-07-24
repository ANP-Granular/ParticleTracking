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

import importlib
import pathlib
import shutil
import sys


def test_path_addition():
    import RodTracker.main

    assert (
        str(pathlib.Path(RodTracker.main.__file__).parent.parent) in sys.path
    )


def test_tmp_dir_create(tmp_path: pathlib.Path):
    # Clean temporary files from potential previous RodTracker runs/imports
    import RodTracker

    for handler in RodTracker.logger.handlers:
        RodTracker.logger.removeHandler(handler)
        handler.close()

    # copy files from LOG_DIR to restore them after the test
    log_dir_storage = tmp_path / "log_dir_copy"
    shutil.copytree(RodTracker.LOG_DIR, log_dir_storage)

    for file in RodTracker.LOG_DIR.iterdir():
        if file.is_file():
            file.unlink()
        elif file.is_dir():
            for inner_file in file.iterdir():
                inner_file.unlink()
            file.rmdir()
    RodTracker.LOG_DIR.rmdir()

    try:
        importlib.reload(RodTracker)
        assert RodTracker.LOG_DIR.exists()
        assert RodTracker.LOG_FILE.exists()
    finally:
        # restore files to LOG_DIR
        shutil.copytree(
            log_dir_storage, RodTracker.LOG_DIR, dirs_exist_ok=True
        )
