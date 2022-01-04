import copy
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
from Python.ui import rodnumberwidget as rn, rodimagewidget as ri

ICON_PATH = "./resources/icon_main.ico"


class SettingsDialog(QtWidgets.QDialog):
    """Dialog to let users adjust settings.

    Parameters
    ----------
    contents : dict
        The settings that will be editable by the user.
    parent : QWidget
        Window/Widget that serves as this dialog's parent.
    defaults : dict
        The default values/settings which can be restored in the dialog
        using a button.

    Attributes
    ----------
    tmp_contents : dict
        The settings that are/were edited by the user. This is initially a
        copy of `contents`.
    """
    tmp_contents: dict
    heading_style = "font-weight: bold;" \
                    "font: 20px;" \
                    "color: black;"
    item_style = "font: 14px;" \
                 "color: black;"

    def __init__(self, contents: dict, parent: QtWidgets.QWidget,
                 defaults: dict = None):
        super().__init__(parent)
        self.tmp_contents = copy.deepcopy(contents)
        self.defaults = defaults
        self.preview_rod_number = None

        self.setWindowTitle("Settings")
        main_layout = QtWidgets.QVBoxLayout(self)
        visual_layout = QtWidgets.QHBoxLayout(self)

        visual_items_layout = QtWidgets.QVBoxLayout(self)
        visual_layout.addLayout(visual_items_layout)

        # Visual Settings
        v_header = QtWidgets.QLabel("Visual Settings")
        v_header.setStyleSheet(self.heading_style)
        reset = QtWidgets.QPushButton("Restore defaults", parent=self)
        reset.clicked.connect(self.restore_defaults)
        header_spacer_0 = QtWidgets.QSpacerItem(
            10, 20, hPolicy=QtWidgets.QSizePolicy.Expanding,
            vPolicy=QtWidgets.QSizePolicy.Fixed)
        v_header_layout = QtWidgets.QHBoxLayout(self)
        v_header_layout.addWidget(v_header)
        v_header_layout.addItem(header_spacer_0)
        v_header_layout.addWidget(reset)

        # Preview
        self.preview = ri.RodImageWidget()
        self.preview.setParent(self)
        visual_layout.addWidget(self.preview)
        number_color = self.tmp_contents["visual"]["number_color"]
        self.preview_rod_number = rn.RodNumberWidget(
            number_color, self.preview)
        self.preview_rod_number.rod_id = 99
        self.preview_rod_number.rod_points = [2, 2, 8, 8]
        self.preview_rod_number.setVisible(True)
        self.update_preview()

        # Rod Thickness
        lbl_thickness = QtWidgets.QLabel("Rod Thickness")
        lbl_thickness.setStyleSheet(self.item_style)
        self.thickness = QtWidgets.QSpinBox()
        self.thickness.setValue(self.tmp_contents["visual"]["rod_thickness"])
        self.thickness.setMaximum(15)
        self.thickness.lineEdit().setReadOnly(True)
        inner_layout = QtWidgets.QHBoxLayout()
        inner_layout.addWidget(lbl_thickness)
        item_spacer_0 = QtWidgets.QSpacerItem(
            10, 20, hPolicy=QtWidgets.QSizePolicy.Expanding,
            vPolicy=QtWidgets.QSizePolicy.Fixed)
        inner_layout.addItem(item_spacer_0)
        inner_layout.addWidget(self.thickness)
        visual_items_layout.addLayout(inner_layout)
        self.thickness.valueChanged.connect(self.handle_rod_thickness)
        self.thickness.lineEdit().selectionChanged.connect(self.clear_select)

        # Rod Color
        lbl_rod_color = QtWidgets.QLabel("Rod Color")
        lbl_rod_color.setStyleSheet(self.item_style)
        self.rod_color = QtWidgets.QToolButton()
        self.rod_color.setObjectName("rod_color")
        self.rod_color.setFixedSize(QtCore.QSize(35, 25))
        color_vals = self.tmp_contents["visual"]["rod_color"]
        to_icon = QtGui.QPixmap(35, 25)
        painter = QtGui.QPainter(to_icon)
        painter.fillRect(QtCore.QRect(0, 0, 35, 25), QtGui.QColor(*color_vals))
        painter.end()
        self.rod_color.setIcon(QtGui.QIcon(to_icon))
        self.rod_color.setIconSize(QtCore.QSize(28, 15))
        self.rod_color.clicked.connect(lambda: self.handle_color_pick(
            self.rod_color))
        inner_layout = QtWidgets.QHBoxLayout()
        inner_layout.addWidget(lbl_rod_color)
        item_spacer_1 = QtWidgets.QSpacerItem(
            10, 20, hPolicy=QtWidgets.QSizePolicy.Expanding,
            vPolicy=QtWidgets.QSizePolicy.Fixed)
        inner_layout.addItem(item_spacer_1)
        inner_layout.addWidget(self.rod_color)
        visual_items_layout.addLayout(inner_layout)

        # Number Offset
        lbl_offset = QtWidgets.QLabel("Number Offset")
        lbl_offset.setStyleSheet(self.item_style)
        self.offset = QtWidgets.QSpinBox()
        self.offset.setValue(self.tmp_contents["visual"]["number_offset"])
        self.offset.setMaximum(50)
        self.offset.lineEdit().setReadOnly(True)
        inner_layout = QtWidgets.QHBoxLayout()
        inner_layout.addWidget(lbl_offset)
        item_spacer_2 = QtWidgets.QSpacerItem(
            10, 20, hPolicy=QtWidgets.QSizePolicy.Expanding,
            vPolicy=QtWidgets.QSizePolicy.Fixed)
        inner_layout.addItem(item_spacer_2)
        inner_layout.addWidget(self.offset)
        visual_items_layout.addLayout(inner_layout)
        self.offset.valueChanged.connect(self.handle_number_offset)
        self.offset.lineEdit().selectionChanged.connect(self.clear_select)

        # Number Color
        lbl_number_color = QtWidgets.QLabel("Number Color")
        lbl_number_color.setStyleSheet(self.item_style)
        self.number_color = QtWidgets.QToolButton()
        self.number_color.setObjectName("number_color")
        self.number_color.setFixedSize(QtCore.QSize(35, 25))
        color_vals = self.tmp_contents["visual"]["number_color"]
        to_icon = QtGui.QPixmap(35, 25)
        painter = QtGui.QPainter(to_icon)
        painter.fillRect(QtCore.QRect(0, 0, 35, 25), QtGui.QColor(*color_vals))
        painter.end()
        self.number_color.setIcon(QtGui.QIcon(to_icon))
        self.number_color.setIconSize(QtCore.QSize(28, 15))
        self.number_color.clicked.connect(lambda: self.handle_color_pick(
            self.number_color))
        inner_layout = QtWidgets.QHBoxLayout()
        inner_layout.addWidget(lbl_number_color)
        item_spacer_3 = QtWidgets.QSpacerItem(
            10, 20, hPolicy=QtWidgets.QSizePolicy.Expanding,
            vPolicy=QtWidgets.QSizePolicy.Fixed)
        inner_layout.addItem(item_spacer_3)
        inner_layout.addWidget(self.number_color)
        visual_items_layout.addLayout(inner_layout)

        # Number Size
        lbl_number_size = QtWidgets.QLabel("Number Size")
        lbl_number_size.setStyleSheet(self.item_style)
        self.number_size = QtWidgets.QSpinBox()
        self.number_size.setValue(self.tmp_contents["visual"]["number_size"])
        self.number_size.setMaximum(30)
        self.number_size.lineEdit().setReadOnly(True)
        inner_layout = QtWidgets.QHBoxLayout()
        inner_layout.addWidget(lbl_number_size)
        item_spacer_4 = QtWidgets.QSpacerItem(
            10, 20, hPolicy=QtWidgets.QSizePolicy.Expanding,
            vPolicy=QtWidgets.QSizePolicy.Fixed)
        inner_layout.addItem(item_spacer_4)
        inner_layout.addWidget(self.number_size)
        visual_items_layout.addLayout(inner_layout)
        self.number_size.valueChanged.connect(self.handle_number_size)
        self.number_size.lineEdit().selectionChanged.connect(self.clear_select)

        # Position Scaling
        rod_scaling = QtWidgets.QLabel("Position Scaling")
        rod_scaling.setStyleSheet(self.item_style)
        self.position_scaling = QtWidgets.QLineEdit()
        self.position_scaling.setInputMask("00.00;0")
        self.position_scaling.setMaximumWidth(35)
        self.position_scaling.setText(
            f"{self.tmp_contents['visual']['position_scaling']:05.2f}")
        self.position_scaling.setAlignment(QtCore.Qt.AlignRight)
        inner_layout = QtWidgets.QHBoxLayout()
        inner_layout.addWidget(rod_scaling)
        item_spacer_5 = QtWidgets.QSpacerItem(
            10, 20, hPolicy=QtWidgets.QSizePolicy.Expanding,
            vPolicy=QtWidgets.QSizePolicy.Fixed)
        inner_layout.addItem(item_spacer_5)
        inner_layout.addWidget(self.position_scaling)
        visual_items_layout.addLayout(inner_layout)
        self.position_scaling.textChanged.connect(self.handle_scaled_position)

        # Control Buttons
        btns = QtWidgets.QDialogButtonBox.Save | \
            QtWidgets.QDialogButtonBox.Cancel
        self.controls = QtWidgets.QDialogButtonBox(btns)
        self.controls.accepted.connect(self.accept)
        self.controls.rejected.connect(self.reject)

        # Main composition
        main_layout.addLayout(v_header_layout)
        main_layout.addLayout(visual_layout)
        main_layout.addWidget(self.controls)

    def update_preview(self):
        """Updates the preview widget with the currently selected settings."""
        # Initialize
        if not self.preview.image:
            preview_size = QtCore.QSize(100, 100)
            preview = QtGui.QPixmap(preview_size)
            painter = QtGui.QPainter(preview)
            painter.fillRect(QtCore.QRect(QtCore.QPoint(0, 0), preview_size),
                             QtGui.QColor(200, 200, 200))
            painter.end()
            self.preview.image = QtGui.QImage(preview)
        if not self.preview.edits:
            self.preview.edits = [self.preview_rod_number]

        # Update the settings
        self.preview_rod_number.update_settings(self.tmp_contents["visual"])
        self.preview.update_settings(self.tmp_contents["visual"])

    def clear_select(self):
        """Helper to clear selections of QSpinBoxes after values changed."""
        self.number_size.lineEdit().deselect()
        self.offset.lineEdit().deselect()
        self.thickness.lineEdit().deselect()

    def handle_rod_thickness(self, new_val: int):
        """Handles changes of the rod thickness by the dialog's controls."""
        self.tmp_contents["visual"]["rod_thickness"] = new_val
        self.update_preview()

    def handle_number_offset(self, new_val: int):
        """Handles changes of the number offset by the dialog's controls."""
        self.tmp_contents["visual"]["number_offset"] = new_val
        self.update_preview()

    def handle_number_size(self, new_val: int):
        """Handles changes of the number size by the dialog's controls."""
        self.tmp_contents["visual"]["number_size"] = new_val
        self.update_preview()

    def handle_color_pick(self, target: QtWidgets.QToolButton):
        """Lets the user select a color."""
        color_vals = self.tmp_contents["visual"][target.objectName()]
        color = QtWidgets.QColorDialog(QtGui.QColor(*color_vals), self)
        if color.exec():
            color = color.selectedColor()
            self.draw_icon(QtGui.QColor(color), target)
            self.tmp_contents["visual"][target.objectName()] = \
                [color.red(), color.green(), color.blue()]
            self.update_preview()

    def handle_scaled_position(self, _: str):
        """Handles changes of the position scaling by the dialog's controls."""
        try:
            converted_val = float(self.position_scaling.displayText())
        except ValueError:
            converted_val = 1.0
        self.tmp_contents["visual"]["position_scaling"] = converted_val
        self.update_preview()

    @staticmethod
    def draw_icon(color: QtGui.QColor, target: QtWidgets.QToolButton):
        """Helper method to set the color selection button's background."""
        to_icon = QtGui.QPixmap(35, 25)
        painter = QtGui.QPainter(to_icon)
        painter.fillRect(QtCore.QRect(0, 0, 35, 25),
                         QtGui.QColor(color))
        painter.end()
        target.setIcon(QtGui.QIcon(to_icon))
        target.setIconSize(QtCore.QSize(28, 15))

    def restore_defaults(self):
        """Resets the displayed settings to the default values."""
        if self.defaults is None:
            QtWidgets.QMessageBox.critical(
                self, "Restore defaults",
                "There are no defaults present! To reset the settings "
                "delete the file %temp%/RodTracker/settings.json and "
                "restart the application.")
        else:
            self.tmp_contents = copy.deepcopy(self.defaults)
            self.offset.setValue(self.tmp_contents["visual"]["number_offset"])
            self.thickness.setValue(
                self.tmp_contents["visual"]["rod_thickness"])
            self.number_size.setValue(
                self.tmp_contents["visual"]["number_size"])
            self.draw_icon(QtGui.QColor(*self.tmp_contents["visual"][
                "rod_color"]), self.rod_color)
            self.draw_icon(QtGui.QColor(*self.tmp_contents["visual"][
                "number_color"]), self.number_color)
            self.position_scaling.setText(str(self.tmp_contents["visual"]
                                              ["position_scaling"]))
            self.update_preview()


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
        self.confirmed_delete = len(to_delete)*[True]

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
    msg.setWindowIcon(QtGui.QIcon(ICON_PATH))
    msg.setIcon(QtWidgets.QMessageBox.Warning)
    msg.setWindowTitle("Rod Tracker")
    msg.setText(text)
    msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msg.exec()
