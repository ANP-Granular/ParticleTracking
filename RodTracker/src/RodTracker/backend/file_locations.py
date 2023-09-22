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

"""**TBD**"""

import logging
import os
from pathlib import Path
import subprocess
import sys
from typing import Literal

if sys.version_info < (3, 9):
    # importlib.resources either doesn't exist or lacks the files()
    # function, so use the PyPI version:
    import importlib_resources

    importlib_resources.path = lambda module, file: importlib_resources.files(
        module
    ).joinpath(file)
else:
    # importlib.resources has files(), so use that:
    import importlib.resources as importlib_resources

    if sys.version_info >= (3, 11):
        importlib_resources.path = (
            lambda module, file: importlib_resources.files(module).joinpath(
                file
            )
        )
_logger = logging.getLogger(__name__)


def icon_path() -> str:
    """Get a string representation of the path to the application icon.

    Returns
    -------
    str
        String representation of the path to the application icon.
    """
    return str(
        importlib_resources.path("RodTracker.resources", "icon_windows.ico")
    )


def logo_path() -> str:
    """Get a string representation of the path to the application icon.

    Returns
    -------
    str
        String representation of the path to the application icon.
    """
    return str(importlib_resources.path("RodTracker.resources", "logo.png"))


def undo_icon_path() -> str:
    """Get a string representation of the path to the application undo icon.

    Returns
    -------
    str
        String representation of the path to the application undo icon.
    """
    return str(
        importlib_resources.path("RodTracker.resources", "left-arrow-96.png")
    )


def open_docs(location: Literal["online", "local"] = "online") -> None:
    """Open the documenation for the RodTracker."""
    _docs_url = "https://particletracking.readthedocs.io/"
    if location == "local":
        local_docs = (
            Path(__file__).parent / "../../../../docs/build/html/index.html"
        ).resolve()
        if hasattr(sys, "_MEIPASS"):
            local_docs = Path(sys._MEIPASS).resolve() / "docs/index.html"
        if local_docs.exists():
            _docs_url = local_docs
        else:
            _logger.warning(
                "Local documentation not found at expected location "
                f"({local_docs}).\n"
                "Falling back to online version."
            )

    if sys.platform == "win32":
        os.startfile(_docs_url)
    elif sys.platform == "linux":
        subprocess.Popen(["xdg-open", _docs_url])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", _docs_url])
    else:
        _logger.warning(
            f"Unknown platform ({sys.platform}) ... can't open documentation."
        )
