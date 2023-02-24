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

import os
import subprocess
from pathlib import Path
import sys
if sys.version_info < (3, 9):
    # importlib.resources either doesn't exist or lacks the files()
    # function, so use the PyPI version:
    import importlib_resources
    importlib_resources.path = (
        lambda module, file: importlib_resources.files(module).joinpath(file)
    )
else:
    # importlib.resources has files(), so use that:
    import importlib.resources as importlib_resources

# use the online documentation unless the RodTracker is bundled
_docs_url = "https://particletracking.readthedocs.io/"
if hasattr(sys, "_MEIPASS"):
    _docs_url = Path("./docs/index.html")


def icon_path() -> str:
    """Get a string representation of the path to the application icon.

    Returns
    -------
    str
        String representation of the path to the application icon.
    """
    return str(importlib_resources.path("RodTracker.resources",
                                        "icon_main.ico"))


def undo_icon_path() -> str:
    """Get a string representation of the path to the application undo icon.

    Returns
    -------
    str
        String representation of the path to the application undo icon.
    """
    return str(importlib_resources.path("RodTracker.resources",
                                        "left-arrow-96.png"))


def open_docs() -> None:
    """Open the documenation for the RodTracker."""
    if sys.platform == 'win32':
        os.startfile(_docs_url)
    else:
        subprocess.Popen(['xdg-open', _docs_url])
