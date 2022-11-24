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

from pathlib import Path
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
import RodTracker.backend.file_locations as fl


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
        Entries correspond to a row from the `to_delete` DataFrame.
        True -> user confirms deletion
        False -> user denies deletion
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
            QtWidgets.QHeaderView.Stretch)
        self.setLayout(self.layout)

        next_row = 0
        for row in self.to_delete.iterrows():
            next_frame = QtWidgets.QTableWidgetItem(str(row[1].frame))
            next_color = QtWidgets.QTableWidgetItem(str(row[1].color))
            next_particle = QtWidgets.QTableWidgetItem(
                str(row[1].particle))
            next_frame.setTextAlignment(QtCore.Qt.AlignHCenter |
                                        QtCore.Qt.AlignVCenter)
            next_color.setTextAlignment(QtCore.Qt.AlignHCenter |
                                        QtCore.Qt.AlignVCenter)
            next_particle.setTextAlignment(QtCore.Qt.AlignHCenter |
                                           QtCore.Qt.AlignVCenter)

            self.table.setItem(next_row, 1, next_frame)
            self.table.setItem(next_row, 2, next_color)
            next_particle.setFlags(QtCore.Qt.ItemIsUserCheckable |
                                   QtCore.Qt.ItemIsEnabled)
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


def show_warning(text: str):
    """Display a warning with custom text and Ok button."""
    msg = QtWidgets.QMessageBox()
    msg.setWindowIcon(QtGui.QIcon(fl.icon_path()))
    msg.setIcon(QtWidgets.QMessageBox.Warning)
    msg.setWindowTitle("Rod Tracker")
    msg.setText(text)
    msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msg.exec()


def show_about(parent: QtWidgets.QWidget):
    about_txt = """
    <style>
        table { background-color: transparent; }
        a { text-decoration:none; font-weight:bold; }
    </style>
    <table border="0" cellpadding="0" cellspacing="5" width="400"
     align="left" style="margin-top:0px;">
        <tr>
            <td width="200", colspan="2"> <h3>Version:</h3> </td>
            <td width="200"> <p> 0.0.1 - beta </p> </td>
        </tr>
        <tr>
            <td width="200", colspan="2"> <h3>Date:</h3> </td>
            <td width="200"> <p> 20.08.2022 </p> </td>
        </tr>
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
        <tr>
            <td width="50">
                <p><a href="https://pandas.pydata.org/">Pandas</a>:</p>
            </td>
            <td width="150">1.2.5</td>
            <td width="200"><p> BSD3 </p></td>
        </tr>
        <tr>
            <td width="50">
                <p><a  href="https://www.riverbankcomputing.com/software
                /pyqt">PyQt5</a>:</p>
            </td>
            <td width="150">5.15.4</td>
            <td width="200"><p> GPLv3+ </p></td>
        </tr>
        <tr>
            <td width="50">
                <p><a href="https://www.qt.io">Qt5</a>:</p>
            </td>
            <td width="150">5.15.2</td>
            <td width="200"><p> LGPLv3 </p></td>
        </tr>
        <tr>
            <td width="50">
                <p><a href="https://material.io/">Material Design</a>:</p>
            </td>
            <td width="150">2</td>
            <td width="200"><p> Apache-2.0 </p></td>
        </tr>
        <tr>
            <td width="50">
                <p><a href="https://www.pyinstaller.org/">PyInstaller</a>:</p>
            </td>
            <td width="150">5.3</td>
            <td width="200"><p> GPLv2+ </p></td>
        </tr>
    </table>
    <br>
    <br>
    <p>
        Copyright © 2022 Otto-von-Guericke University Magdeburg
    </p>"""
    QtWidgets.QMessageBox.about(parent, "About RodTracker", about_txt)


def show_readme(parent: QtWidgets.QWidget):
    docs_dialog = QtWidgets.QDialog(parent)
    docs_dialog.resize(600, 600)
    docs_dialog.setWindowTitle("README")

    docs_dialog.docs = QtWidgets.QTextEdit(parent=docs_dialog)
    docs_dialog.docs.setReadOnly(True)
    docs_dialog.docs.setStyleSheet("background-color: transparent;")
    docs_dialog.docs.setFrameShape(QtWidgets.QFrame.NoFrame)

    docs_dialog.layout = QtWidgets.QVBoxLayout()
    docs_dialog.layout.addWidget(docs_dialog.docs)
    docs_dialog.setLayout(docs_dialog.layout)

    readme_md = Path(fl.readme_path()).read_text()
    docs_dialog.docs.setMarkdown(readme_md)
    docs_dialog.show()


class ConflictDialog(QtWidgets.QMessageBox):
    """Dialog for switching rod numbers in various modes."""
    def __init__(self, last_id, new_id, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWindowIcon(QtGui.QIcon(fl.icon_path()))
        self.setIcon(QtWidgets.QMessageBox.Warning)
        self.setWindowTitle("Rod Tracker")
        self.setText(
            f"A rod number switching attempt of"
            f"#{last_id} <---> #{new_id} was detected. \nHow shall "
            f"this conflict be resolved?")
        self.btn_switch_all = self.addButton(
            "Switch in:\nBoth views, following frames",
            QtWidgets.QMessageBox.ActionRole)
        self.btn_one_cam = self.addButton("Switch in:\nThis views, following "
                                          "frames",
                                          QtWidgets.QMessageBox.ActionRole)
        self.btn_both_cams = self.addButton(
            "Switch in:\nBoth views, this frame",
            QtWidgets.QMessageBox.ActionRole)
        self.btn_only_this = self.addButton(
            "Switch in:\nThis view, this frame",
            QtWidgets.QMessageBox.ActionRole)
        self.btn_cancel = self.addButton(QtWidgets.QMessageBox.Abort)
        self.setDefaultButton(self.btn_switch_all)
        self.setEscapeButton(self.btn_cancel)
