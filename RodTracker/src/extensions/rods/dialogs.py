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
