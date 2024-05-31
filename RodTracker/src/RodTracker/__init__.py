# Copyright (c) 2023-24 Adrian Niemann, and others
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

import logging
import sys
from pathlib import Path
from types import TracebackType

import platformdirs
from PyQt5 import QtGui, QtWidgets

import RodTracker.backend.file_locations as fl
import RodTracker.backend.miscellaneous as misc
from RodTracker._version import __version__  # noqa: F401

APPNAME = "RodTracker"
APPAUTHOR = "ANP-Granular"

LOG_DIR: Path = platformdirs.user_log_path(
    APPNAME, APPAUTHOR, opinion=False, ensure_exists=True
)
LOG_FILE = LOG_DIR / "RodTracker.log"
LOG_LEVEL = logging.DEBUG
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
f_handle = logging.FileHandler(LOG_FILE, mode="a")
f_handle.setLevel(LOG_LEVEL)
formatter = logging.Formatter(
    "[%(asctime)s] %(name)s %(levelname)s: %(message)s",
    datefmt="%m/%d %H:%M:%S",
)
f_handle.setFormatter(formatter)
logger.addHandler(f_handle)
logging.captureWarnings(True)


def _set_log_level(level: int):
    logger.setLevel(level)
    f_handle.setLevel(level)


CONFIG_DIR = platformdirs.user_config_path(
    APPNAME, APPAUTHOR, roaming=False, ensure_exists=True
)
SETTINGS_FILE = CONFIG_DIR / "settings.json"

DATA_DIR = platformdirs.user_data_path(
    APPNAME, APPAUTHOR, roaming=False, ensure_exists=True
)
ERROR_LOGGER = logging.getLogger(APPNAME)


class ErrorDialog(QtWidgets.QMessageBox):
    """Dialog to display errors during program execution."""

    def __init__(
        self,
        e_type: type = None,
        e_value: str = None,
        e_tb: TracebackType = None,
        parent: QtWidgets.QWidget = None,
    ):
        super().__init__(parent=parent)
        self.setWindowIcon(QtGui.QIcon(fl.icon_path()))
        self.setModal(False)
        self.setIcon(QtWidgets.QMessageBox.Warning)
        self.setWindowTitle(APPNAME)
        self.setText(
            "<b>An unexpected error occured:</b><br><br>"
            f"({e_type.__name__}) {e_value}"
        )
        self.btn_close = self.addButton(
            "Close", QtWidgets.QMessageBox.AcceptRole
        )
        self.btn_report = self.addButton(
            "Report Bug ", QtWidgets.QMessageBox.ActionRole
        )
        self.btn_logs = self.addButton(
            "Show logs", QtWidgets.QMessageBox.ActionRole
        )
        self.setDefaultButton(self.btn_close)
        self.setEscapeButton(self.btn_close)

        self.btn_logs.clicked.connect(misc.open_logs)
        self.btn_report.clicked.connect(misc.report_issue)


def exception_logger(
    e_type: type, e_value: str, e_tb: TracebackType, use_exec: bool = False
):
    """Handler for logging uncaught exceptions during the program flow."""
    ERROR_LOGGER.exception(
        "Uncaught exception:", exc_info=(e_type, e_value, e_tb)
    )
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    if use_exec:
        ErrorDialog(e_type, e_value, e_tb, app.desktop()).exec()
    else:
        ErrorDialog(e_type, e_value, e_tb, app.desktop()).show()


# TODO: add docs
class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(
                *args, **kwargs
            )
        return cls._instances[cls]


if sys.version_info < (3, 12):
    import inspect
    import re

    def override(method):
        stack = inspect.stack()
        base_classes = re.search(
            r"class.+\((.+)\)\s*\:", stack[2][4][0]
        ).group(1)

        # handle multiple inheritance
        base_classes = [s.strip() for s in base_classes.split(",")]
        if not base_classes:
            raise ValueError(
                "override decorator: unable to determine base class"
            )

        # stack[0]=overrides, stack[1]=inside class def'n,
        #   stack[2]=outside class def'n
        derived_class_locals = stack[2][0].f_locals

        # replace each class name in base_classes with the actual class type
        for i, base_class in enumerate(base_classes):
            if "." not in base_class:
                base_classes[i] = derived_class_locals[base_class]

            else:
                components = base_class.split(".")

                # obj is either a module or a class
                obj = derived_class_locals[components[0]]

                for c in components[1:]:
                    assert inspect.ismodule(obj) or inspect.isclass(obj)
                    obj = getattr(obj, c)

                base_classes[i] = obj

        assert any(hasattr(cls, method.__name__) for cls in base_classes)
        return method
