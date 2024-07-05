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
logger = logging.getLogger()
logger.setLevel(logging.INFO)
f_handle = logging.FileHandler(LOG_FILE, mode="a")
f_handle.setLevel(logging.INFO)
formatter = logging.Formatter(
    "[%(asctime)s] %(name)s %(levelname)s: %(message)s",
    datefmt="%m/%d %H:%M:%S",
)
f_handle.setFormatter(formatter)
logger.addHandler(f_handle)
logging.captureWarnings(True)

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
        self.setModal(True)
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
