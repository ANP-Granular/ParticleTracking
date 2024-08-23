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

import platform
from pathlib import Path
from typing import Union

import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets

import RodTracker.backend.file_locations as fl
from RodTracker import APPNAME
from RodTracker._version import __date__, __version__


class ConfirmDeleteDialog(QtWidgets.QDialog):
    """Confirmation dialog for data that was marked for deletion automatically.

    The user shall confirm/deny the deletion of rows that were automatically
    marked for deletion.

    Parameters
    ----------
    to_delete : DataFrame
        Rows of the main DataFrame that are automatically identified to be
        deleted and shall be confirmed by the user.
    parent : QWidget
        Window/Widget that serves as this dialog's parent.

    Attributes
    ----------
    confirmed_delete : List[bool]
        Entries correspond to a row from the :attr:`to_delete` ``DataFrame``.
        ``True`` -> user confirms deletion
        ``False`` -> user denies deletion
    """

    def __init__(self, to_delete: pd.DataFrame, parent: QtWidgets.QWidget):
        super().__init__(parent=parent)
        self.to_delete = to_delete
        self.confirmed_delete = len(to_delete) * [True]

        # Create visual elements
        self.description = QtWidgets.QLabel("")
        self.table = QtWidgets.QTableWidget(len(to_delete), 3, parent=self)
        self.controls = QtWidgets.QDialogButtonBox()
        self.layout = QtWidgets.QVBoxLayout(self)

        self.setup_ui()

    def setup_ui(self):
        """Setup the UI elements."""
        self.setWindowTitle("Confirm deletions")

        description_text = """
            <p>Please review the rods that were marked for complete deletion
             from the output files. <br><br>
            <b>Caution: The changes made after clicking OK cannot be
             reverted.</b></p>
            """
        self.description.setText(description_text)

        self.table.setHorizontalHeaderLabels(["Number", "Frame", "Color"])
        h_header = self.table.horizontalHeader()
        h_header.setStyleSheet("font: bold;")
        self.table.verticalHeader().hide()

        self.controls.addButton(QtWidgets.QDialogButtonBox.Ok)
        self.controls.addButton(QtWidgets.QDialogButtonBox.Cancel)
        self.controls.accepted.connect(self.accept)
        self.controls.rejected.connect(self.reject)

        self.layout.addWidget(self.description)
        self.layout.addWidget(self.table)
        self.layout.addWidget(self.controls)
        self.layout.addStretch()
        self.table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.Stretch
        )
        self.setLayout(self.layout)

        next_row = 0
        for row in self.to_delete.iterrows():
            next_frame = QtWidgets.QTableWidgetItem(str(row[1].frame))
            next_color = QtWidgets.QTableWidgetItem(str(row[1].color))
            next_particle = QtWidgets.QTableWidgetItem(str(row[1].particle))
            next_frame.setTextAlignment(
                QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter
            )
            next_color.setTextAlignment(
                QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter
            )
            next_particle.setTextAlignment(
                QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter
            )

            self.table.setItem(next_row, 1, next_frame)
            self.table.setItem(next_row, 2, next_color)
            next_particle.setFlags(
                QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled
            )
            next_particle.setCheckState(QtCore.Qt.Checked)
            self.table.setItem(next_row, 0, next_particle)
            next_row += 1
        self.table.itemClicked.connect(self.handle_item_clicked)

    @QtCore.pyqtSlot(QtWidgets.QTableWidgetItem)
    def handle_item_clicked(self, item: QtWidgets.QTableWidgetItem) -> None:
        """Handles the checking/unchecking of rows to mark for deletion.

        Parameters
        ----------
        item : QTableWidgetItem

        Returns
        -------
        None
        """
        if item.checkState() == QtCore.Qt.Checked:
            self.confirmed_delete[item.row()] = True
        else:
            self.confirmed_delete[item.row()] = False


def select_data_folder(
    title: str, start_folder: str, file_type_filter: str
) -> Union[None, Path]:
    """Let users select a folder that shall contain a certain type of data.

    Parameters
    ----------
    title : str
    start_folder : str
        Initially displayed folder.
    file_type_filter : str
        Filter for file types to display.

    Returns
    -------
    Union[None, Path]
        `None` if selection was aborted. Otherwise, the selected folder is
        returned as a `Path`.
    """
    picker_dialog = QtWidgets.QFileDialog(
        None,
        title,
        start_folder,
        file_type_filter,
    )
    picker_dialog.setFileMode(QtWidgets.QFileDialog.Directory)
    picker_dialog.setWindowIcon(QtGui.QIcon(fl.icon_path()))
    picker_dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
    if not picker_dialog.exec():
        return None
    return Path(picker_dialog.selectedFiles()[0]).resolve()


def show_warning(text: str):
    """Display a warning with custom text and Ok button."""
    msg = QtWidgets.QMessageBox()
    msg.setWindowIcon(QtGui.QIcon(fl.icon_path()))
    msg.setIcon(QtWidgets.QMessageBox.Warning)
    msg.setWindowTitle(APPNAME)
    msg.setText(text)
    msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msg.exec()


def show_about(parent: QtWidgets.QWidget):
    dependency_format = """
    <tr>
        <td width="50">
            <p><a href="{}">{}</a>:</p>
        </td>
        <td width="150">{}</td>
        <td width="200"><p>{}</p></td>
    </tr>
    """
    dependencies = [
        # (link, name, version, license(s))
        (
            "https://docutils.sourceforge.io/",
            "docutils",
            "0.18.1",
            "BSD 2, GPL, PSF",
        ),
        ("https://github.com/mtkennerly/dunamai", "dunamai", "1.19.0", "MIT"),
        ("https://github.com/pycqa/flake8", "flake8", "6.1.0", "MIT"),
        (
            "https://github.com/python/importlib_resources",
            "importlib-resources",
            "6.1.0",
            "Apache-2.0",
        ),
        ("https://material.io/", "Material Design", "2", "Apache-2.0"),
        ("https://matplotlib.org/", "matplotlib", "3.8.0", "matplotlib"),
        (
            "https://myst-parser.readthedocs.io/",
            "MyST-Parser",
            "2.0.0",
            "MIT",
        ),
        ("https://numpy.org/", "NumPy", "1.26.0", "BSD 3"),
        ("https://pandas.pydata.org/", "Pandas", "2.1.1", "BSD 3"),
        (
            "https://github.com/ANP-Granular/ParticleTracking",
            "particledetection",
            "0.4.0",
            "GPLv3",
        ),
        ("https://python-pillow.org/", "Pillow", "10.0.1", "HPND"),
        (
            "https://github.com/platformdirs/platformdirs",
            "platformdirs",
            "3.11.0",
            "MIT",
        ),
        ("https://www.pyinstaller.org/", "PyInstaller", "6.0.0", "GPLv2+"),
        (
            "https://www.riverbankcomputing.com/software/pyqt",
            "PyQt3D",
            "5.15.6",
            "GPLv3+",
        ),
        (
            "https://www.riverbankcomputing.com/software/pyqt",
            "PyQt5",
            "5.15.9",
            "GPLv3+",
        ),
        ("https://docs.pytest.org/", "pytest", "7.4.2", "MIT"),
        (
            "https://github.com/pytest-dev/pytest-cov",
            "pytest-cov",
            "4.1.0",
            "MIT",
        ),
        (
            "https://github.com/pytest-dev/pytest-qt",
            "pytest-qt",
            "4.2.0",
            "MIT",
        ),
        ("https://www.qt.io", "Qt5", "5.15.2", "LGPLv3"),
        ("https://www.sphinx-doc.org/", "Sphinx", "7.2.6", "BSD"),
        (
            "https://sphinx-rtd-theme.readthedocs.io/",
            "sphinx_rtd_theme",
            "1.3.0",
            "MIT",
        ),
    ]
    dependency_string = """"""
    for dep in dependencies:
        dependency_string += dependency_format.format(*dep)

    about_txt = (
        """
        <style>
            table { background-color: transparent; }
            a { text-decoration:none; font-weight:bold; }
        </style>
        <table border="0" cellpadding="0" cellspacing="5" width="400"
        align="left" style="margin-top:0px;">
            <tr>
                <td width="200", colspan="2"> <h3>Version:</h3> </td>
        """
        + """   <td width="200"> <p> {} </p> </td>
            </tr>
            <tr>
                <td width="200", colspan="2"> <h3>Date:</h3> </td>
                <td width="200"> <p> {} </p> </td>
            </tr>
        """.format(
            __version__, __date__
        )
        + """
        <tr>
            <td width="200", colspan="2"> <h3><br>Developers:<br></h3> </td>
            <td width="200">
                <p> Adrian Niemann <br>
                    Dmitry Puzyrev <br>
                    Meera Subramanian <br>
                    Adithya Viswanathan
                </p>
            </td>
        </tr>
        <tr>
            <td width="200", colspan="2"> <h3>License:</h3> </td>
            <td width="200">
                <p><a href="https://www.gnu.org/licenses/gpl-3.0.en.html">
                GPLv3</a>
                </p>
            </td>
        </tr>
        <tr>
            <td width="400", colspan="3"> <br><h3>3rd Party Software:</h3>
            <p> This application either uses code and tools from the
                following projects in part or in their entirety as deemed
                permissible by each project's open-source license.</p>
            </td>
        </tr>
        """
        + dependency_string
        + """
        </table>
        <br>
        <br>
        <p>
            Copyright © 2023 Adrian Niemann, Dmitry Puzyrev
        </p>
        """
    )
    if platform.system() == "Darwin":
        QtWidgets.QMessageBox.about(parent, "About RodTracker", about_txt)
    else:
        # Using the logo instead of the icon
        _ = QtWidgets.QWidget()
        _.setWindowIcon(QtGui.QIcon(fl.logo_path()))
        QtWidgets.QMessageBox.about(_, f"About {APPNAME}", about_txt)


class ConflictDialog(QtWidgets.QMessageBox):
    """Dialog for switching rod numbers in various modes."""

    def __init__(self, last_id, new_id, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowIcon(QtGui.QIcon(fl.icon_path()))
        self.setIcon(QtWidgets.QMessageBox.Warning)
        self.setWindowTitle(APPNAME)
        self.setText(
            f"A rod number switching attempt of"
            f"#{last_id} <---> #{new_id} was detected. \nHow shall "
            f"this conflict be resolved?"
        )
        self.btn_switch_all = self.addButton(
            "Switch in:\nBoth views, following frames",
            QtWidgets.QMessageBox.ActionRole,
        )
        self.btn_one_cam = self.addButton(
            "Switch in:\nThis view, following " "frames",
            QtWidgets.QMessageBox.ActionRole,
        )
        self.btn_both_cams = self.addButton(
            "Switch in:\nBoth views, this frame",
            QtWidgets.QMessageBox.ActionRole,
        )
        self.btn_only_this = self.addButton(
            "Switch in:\nThis view, this frame",
            QtWidgets.QMessageBox.ActionRole,
        )
        self.btn_cancel = self.addButton(QtWidgets.QMessageBox.Abort)
        self.setDefaultButton(self.btn_switch_all)
        self.setEscapeButton(self.btn_cancel)
