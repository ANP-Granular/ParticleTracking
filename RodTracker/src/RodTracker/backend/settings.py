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

import json
import logging
from typing import Any

from PyQt5 import QtCore

from RodTracker import SETTINGS_FILE, Singleton

_logger = logging.getLogger(__name__)


class UnknownSettingError(KeyError):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class SettingSignals(QtCore.QObject):
    setting_changed = QtCore.pyqtSignal([str, object], name="setting_changed")


class Settings(metaclass=Singleton):
    _settings: dict = {}
    setting_signals: SettingSignals

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setting_signals = SettingSignals()
        try:
            with open(SETTINGS_FILE, "r") as f:
                contents = json.load(f)
            if contents is None:
                raise FileNotFoundError
            self._settings = contents
        except FileNotFoundError:
            self._settings = {}
        # TODO: validate all keys/values
        # TODO: show warning, if keys do not match new schema

    # TODO: add docs
    def get_setting(self, key: str):
        try:
            return self._settings[key]
        except KeyError:
            raise UnknownSettingError(key)

    # TODO: add docs (is only convenience method)
    def add_setting(self, key: str, value: Any):
        self.setting_updated(key, value)

    # TODO: add docs
    def setting_updated(self, key: str, new_value: Any):
        self._settings[key] = new_value
        # save to file
        to_file = json.dumps(self._settings, indent=2)
        with open(SETTINGS_FILE, "w") as out:
            out.write(to_file)
        self.setting_signals.setting_changed.emit(key, new_value)
