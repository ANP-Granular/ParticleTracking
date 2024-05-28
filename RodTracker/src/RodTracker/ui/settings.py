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

# TODO: add docs
from abc import abstractmethod
from typing import Any, Tuple

from PyQt5 import QtCore, QtGui, QtWidgets


# TODO: add docs (specifically how to use it)
class Setting(QtWidgets.QWidget):
    setting_updated = QtCore.pyqtSignal([str, object], name="setting_updated")

    def __init__(self, id: str, default_value: Any, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = id
        self.default_val = default_value

    @abstractmethod
    def set_value_silently(self, new_value: Any): ...  # noqa: E704

    def restore_default(self):
        self.set_value_silently(self.default_val)
        self.setting_updated.emit(self.id, self.default_val)


# TODO: add docs
class BoolSetting(Setting):
    def __init__(
        self,
        id: str,
        default_value: bool = True,
        description: str = "",
        *args,
        **kwargs,
    ):
        super().__init__(id=id, default_value=default_value, *args, **kwargs)

        # Setup UI:
        settings_layout = QtWidgets.QHBoxLayout(self)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(settings_layout)
        label = QtWidgets.QLabel(description, self)
        self.editable = QtWidgets.QCheckBox("", self)
        self.editable.setChecked(default_value)
        settings_layout.addWidget(label)
        settings_layout.addWidget(self.editable, 0, QtCore.Qt.AlignRight)

        # Connect signal to communicate value changes of the setting
        self.editable.stateChanged.connect(
            lambda new_state: self.setting_updated.emit(self.id, new_state)
        )

    def set_value_silently(self, new_value: bool):
        try:
            self.editable.stateChanged.disconnect()
        except TypeError:
            # In case no signal is connected
            pass

        self.editable.setChecked(new_value)
        self.editable.stateChanged.connect(
            lambda new_state: self.setting_updated.emit(self.id, new_state)
        )


# TODO: add docs
class IntSetting(Setting):
    def __init__(
        self,
        id: str,
        default_value: int = 0,
        description: str = "",
        min_value: int = 0,
        max_value: int = 1000,
        *args,
        **kwargs,
    ):
        super().__init__(id=id, default_value=default_value, *args, **kwargs)
        # Setup UI:
        settings_layout = QtWidgets.QHBoxLayout(self)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(settings_layout)
        label = QtWidgets.QLabel(description, self)
        label.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred
        )
        self.editable = QtWidgets.QSpinBox(self)
        self.editable.setMinimum(min_value)
        self.editable.setMaximum(max_value)
        self.editable.setValue(default_value)

        settings_layout.addWidget(label)
        settings_layout.addWidget(self.editable, 0, QtCore.Qt.AlignRight)

        # Connect signal to communicate value changes of the setting
        self.editable.valueChanged.connect(
            lambda new_val: self.setting_updated.emit(self.id, new_val)
        )

    def set_value_silently(self, new_value: int):
        self.editable.valueChanged.disconnect()
        self.editable.setValue(new_value)
        self.editable.valueChanged.connect(
            lambda new_value: self.setting_updated.emit(self.id, new_value)
        )


# TODO: add docs
class FloatSetting(Setting):
    def __init__(
        self,
        id: str,
        default_value: float = 0.0,
        description: str = "",
        input_mask: str = "00.00;0",
        *args,
        **kwargs,
    ):
        super().__init__(id=id, default_value=default_value, *args, **kwargs)

        # Setup UI:
        settings_layout = QtWidgets.QHBoxLayout(self)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(settings_layout)
        label = QtWidgets.QLabel(description, self)
        label.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred
        )
        self.editable = QtWidgets.QLineEdit(self)
        self.editable.setInputMask(input_mask)
        self.editable.setText(f"{default_value:05.2f}")

        settings_layout.addWidget(label)
        settings_layout.addWidget(self.editable, 0, QtCore.Qt.AlignRight)

        # Connect signal to communicate value changes of the setting
        self.editable.textChanged.connect(self.value_changed)

    def value_changed(self, _):
        try:
            converted_val = float(self.editable.displayText())
        except ValueError:
            converted_val = 0.0
        self.setting_updated.emit(self.id, converted_val)

    def set_value_silently(self, new_value: float):
        self.editable.textChanged.disconnect()
        self.editable.setText(f"{new_value:05.2f}")
        self.editable.textChanged.connect(self.value_changed)


# TODO: add docs
class ColorSetting(Setting):
    def __init__(
        self,
        id: str,
        default_value: Tuple[int, int, int] = (0, 0, 0),
        description: str = "",
        *args,
        **kwargs,
    ):
        super().__init__(id=id, default_value=default_value, *args, **kwargs)
        self.color = QtGui.QColor(*default_value)

        # Setup UI:
        settings_layout = QtWidgets.QHBoxLayout(self)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(settings_layout)
        label = QtWidgets.QLabel(description, self)
        label.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred
        )
        self.editable = QtWidgets.QToolButton(self)
        self.draw_icon(self.color)

        settings_layout.addWidget(label)
        settings_layout.addWidget(self.editable, 0, QtCore.Qt.AlignRight)

        # Connect signal to communicate value changes of the setting
        self.editable.clicked.connect(self.color_selection)

    def draw_icon(self, color: QtGui.QColor):
        new_icon = QtGui.QPixmap(35, 25)
        painter = QtGui.QPainter(new_icon)
        painter.fillRect(QtCore.QRect(0, 0, 35, 25), color)
        painter.end()
        self.editable.setIcon(QtGui.QIcon(new_icon))
        self.editable.setIconSize(QtCore.QSize(28, 15))

    def color_selection(self):
        color_selector = QtWidgets.QColorDialog(self.color, self)
        if color_selector.exec():
            self.color = color_selector.selectedColor()
            self.setting_updated.emit(
                self.id,
                (self.color.red(), self.color.green(), self.color.blue()),
            )
            self.draw_icon(self.color)

    def set_value_silently(self, new_value: Tuple[int, int, int]):
        self.color = QtGui.QColor(*new_value)
        self.draw_icon(self.color)
