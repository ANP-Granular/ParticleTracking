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

import logging
import tempfile
from typing import List

from PyQt5 import QtCore, QtWidgets

import RodTracker.backend.logger as lg
from RodTracker import DATA_DIR

_logger = logging.getLogger(__name__)


class LoggerWidget(QtWidgets.QListWidget):
    """A custom widget to maintain :class:`.ActionLogger` objects and display
    :class:`.Action` objects in the GUI.

    This class maintains the :class:`.ActionLogger` objects that are used in
    the program. It also manages the location for any temporary files that are
    program session specific. This widget displays the logged actions in the
    GUI. Use an instance of this class to create new loggers for other
    objects of the GUI that perform actions that can be logged or reverted.

    Parameters
    ----------
    *args : iterable
        Positional arguments for the ``QListWidget`` superclass.
    **kwargs : dict
        Keyword arguments for the ``QListWidget`` superclass.


    .. admonition:: Slots

        - :meth:`add_action`
        - :meth:`remove_action`
    """

    temp_manager: tempfile.TemporaryDirectory
    _loggers: List[lg.ActionLogger] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.temp_manager = tempfile.TemporaryDirectory(
            prefix="Session_", dir=str(DATA_DIR)
        )
        _logger.info(self.temp_manager.name)

    @property
    def unsaved_changes(self) -> List[lg.Action]:
        """Collects the unsaved changes from all loggers and returns them
        collectively.

        An ordered list of all actions that were logged by the
        :class:`.ActionLogger` objects maintained by this :class:`LoggerWidget`
        instance. Do NOT try to insert performed actions in here directly.
        This property only derives its contents from the :class:`.ActionLogger`
        objects.

        Returns
        -------
        List[Action]
        """
        all_unsaved = [
            item
            for changes in self._loggers
            for item in changes.unsaved_changes
        ]
        return all_unsaved

    @property
    def repeatable_changes(self) -> List[lg.Action]:
        """Collects the repeatable changes from all loggers and returns them
        collectively.

        An ordered list of all currently redoable/repeatable actions that were
        logged by the :class:`.ActionLogger` objects maintained by this
        :class:`LoggerWidget` instance. Do NOT try to insert performed actions
        in here directly. This property only derives its contents from the
        :class:`.ActionLogger` objects.

        Returns
        -------
        List[Action]
        """
        all_repeatable = [
            item
            for changes in self._loggers
            for item in changes.repeatable_changes
        ]
        return all_repeatable

    def get_new_logger(self, parent_id: str) -> lg.ActionLogger:
        """
        Creates a new :class:`ActionLogger`, registers its signals for
        displaying the actions logged by it and returns it.

        Parameters
        ----------
        parent_id : str
            A unique name that indicates the object from which actions will
            be logged in the :class:`ActionLogger`.

        Returns
        -------
        ActionLogger
        """
        new_logger = lg.ActionLogger(parent_id)
        new_logger.added_action.connect(self.add_action)
        new_logger.undo_action.connect(self.remove_action)
        new_logger.undone_action.connect(self.remove_action)
        self._loggers.append(new_logger)
        return new_logger

    @QtCore.pyqtSlot(lg.Action)
    def add_action(self, new_action: lg.Action) -> None:
        """Adds a new action to the list being displayed in the GUI."""
        if not self._loggers:
            # No loggers exist yet/anymore
            return
        self.insertItem(self.count(), new_action)
        self.scrollToBottom()
        _logger.info(str(new_action))

    @QtCore.pyqtSlot(lg.Action)
    def remove_action(self, undo_action: lg.Action) -> None:
        """Removes an Action from the displayed list and deletes it."""
        item_pos = self.row(undo_action)
        undo_item = self.takeItem(item_pos)
        _logger.warning(f"Removed action: {undo_action}")
        del undo_item
        self.scrollToBottom()

    def discard_changes(self):
        """Discard unsaved changes in all maintained :class`ActionLogger`
        objects."""
        for logger in self._loggers:
            logger.discard_changes()
