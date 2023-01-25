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

import pytest
from pytestqt.qtbot import QtBot
from functools import partial
from PyQt5 import QtCore
import RodTracker.ui.rodnumberwidget as rn

number = 12
color = "red"
init_pos = QtCore.QPoint(5, 5)
confirm_btns = [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]


@pytest.fixture()
def basic_number_widget(qtbot: QtBot) -> rn.RodNumberWidget:
    n_widget = rn.RodNumberWidget(color, None, str(number),
                                  init_pos)
    n_widget.rod_id = number
    n_widget.show()
    qtbot.addWidget(n_widget)
    yield n_widget


def test_init(qtbot: QtBot):
    n_widget = rn.RodNumberWidget(color, None, str(number), init_pos)
    n_widget.show()
    qtbot.addWidget(n_widget)
    assert n_widget.text() == str(number)
    assert n_widget.initial_pos == init_pos


def test_copy(qtbot: QtBot):
    n_widget = rn.RodNumberWidget(color, None, str(number),
                                  init_pos)
    n_widget.rod_id = number
    n_widget.show()
    copied = n_widget.copy()

    def check_exists(var: str):
        assert var not in locals()
    n_widget.deleteLater()
    del n_widget
    test_func = partial(check_exists, "n_widget")
    qtbot.waitUntil(test_func)
    assert copied


def test_activation(basic_number_widget: rn.RodNumberWidget, qtbot: QtBot):
    with qtbot.waitSignal(basic_number_widget.activated) as blocker:
        qtbot.mouseClick(basic_number_widget, QtCore.Qt.MouseButton.LeftButton)
    assert blocker.args == [number]


def test_enter_editing(basic_number_widget: rn.RodNumberWidget, qtbot: QtBot):
    qtbot.mouseDClick(basic_number_widget, QtCore.Qt.MouseButton.LeftButton)
    assert not basic_number_widget.isReadOnly()
    qtbot.keyClicks(basic_number_widget, "34")
    assert basic_number_widget.text() == "34"


@pytest.mark.parametrize("btn", confirm_btns)
def test_confirm_editing(basic_number_widget: rn.RodNumberWidget, qtbot: QtBot,
                         btn):
    new_val = 34
    qtbot.mouseDClick(basic_number_widget, QtCore.Qt.MouseButton.LeftButton)
    qtbot.keyClicks(basic_number_widget, str(new_val))
    with qtbot.waitSignal(basic_number_widget.id_changed) as blocker:
        qtbot.keyClick(basic_number_widget, btn)
    assert blocker.args[-1] == number
    assert basic_number_widget.isReadOnly()
    assert basic_number_widget.text() == str(new_val)


def test_abort_editing(basic_number_widget: rn.RodNumberWidget, qtbot: QtBot):
    qtbot.mouseDClick(basic_number_widget, QtCore.Qt.MouseButton.LeftButton)
    qtbot.keyClicks(basic_number_widget, "34")
    with qtbot.assertNotEmitted(basic_number_widget.id_changed, wait=100):
        qtbot.keyClick(basic_number_widget, QtCore.Qt.Key_Escape)
    assert basic_number_widget.isReadOnly()
    assert basic_number_widget.text() == str(number)


@pytest.mark.parametrize("btn", confirm_btns)
def test_delete(basic_number_widget, qtbot, btn):
    qtbot.mouseDClick(basic_number_widget, QtCore.Qt.MouseButton.LeftButton)
    qtbot.keyClick(basic_number_widget, QtCore.Qt.Key_Delete)
    with qtbot.waitSignal(basic_number_widget.request_delete):
        qtbot.keyClick(basic_number_widget, btn)


@pytest.mark.skip("Not implemented.")
def test_settings_update_instance():
    raise NotImplementedError


@pytest.mark.skip("Not implemented.")
def test_settings_update_class():
    raise NotImplementedError
