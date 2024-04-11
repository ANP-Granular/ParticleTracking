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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RodTracker. If not, see <http://www.gnu.org/licenses/>.

"""**TBD**"""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Literal

import importlib_resources

_logger = logging.getLogger(__name__)


def icon_path() -> str:
    """Get a string representation of the path to the application icon.

    Returns
    -------
    str
        String representation of the path to the application icon.
    """
    return str(
        importlib_resources.files("RodTracker.resources").joinpath(
            "icon_windows.ico"
        )
    )


def logo_path() -> str:
    """Get a string representation of the path to the application icon.

    Returns
    -------
    str
        String representation of the path to the application icon.
    """
    return str(
        importlib_resources.files("RodTracker.resources").joinpath("logo.png")
    )


def undo_icon_path() -> str:
    """Get a string representation of the path to the application undo icon.

    Returns
    -------
    str
        String representation of the path to the application undo icon.
    """
    return str(
        importlib_resources.files("RodTracker.resources").joinpath(
            "left-arrow-96.png"
        )
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
