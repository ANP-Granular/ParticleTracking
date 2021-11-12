import copy
from PyQt5 import QtCore, QtGui, QtWidgets
from Python.ui import rodnumberwidget as rn, rodimagewidget as ri


class SettingsDialog(QtWidgets.QDialog):
    tmp_contents: dict
    heading_style = "font-weight: bold;" \
                    "font: 20px;" \
                    "color: black;"
    item_style = "font: 14px;" \
                 "color: black;"

    def __init__(self, contents: dict, parent: QtWidgets.QWidget,
                 defaults: dict = None):
        super().__init__(parent)
        self.tmp_contents = contents
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
        self.tmp_contents["visual"]["rod_thickness"] = new_val
        self.update_preview()

    def handle_number_offset(self, new_val: int):
        self.tmp_contents["visual"]["number_offset"] = new_val
        self.update_preview()

    def handle_number_size(self, new_val: int):
        self.tmp_contents["visual"]["number_size"] = new_val
        self.update_preview()

    def handle_color_pick(self, target: QtWidgets.QToolButton):
        color_vals = self.tmp_contents["visual"][target.objectName()]
        color = QtWidgets.QColorDialog(QtGui.QColor(*color_vals), self)
        if color.exec():
            color = color.selectedColor()
            self.draw_icon(QtGui.QColor(color), target)
            self.tmp_contents["visual"][target.objectName()] = \
                [color.red(), color.green(), color.blue()]
            self.update_preview()

    @staticmethod
    def draw_icon(color: QtGui.QColor, target: QtWidgets.QToolButton):
        to_icon = QtGui.QPixmap(35, 25)
        painter = QtGui.QPainter(to_icon)
        painter.fillRect(QtCore.QRect(0, 0, 35, 25),
                         QtGui.QColor(color))
        painter.end()
        target.setIcon(QtGui.QIcon(to_icon))
        target.setIconSize(QtCore.QSize(28, 15))

    def restore_defaults(self):
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
            self.update_preview()
