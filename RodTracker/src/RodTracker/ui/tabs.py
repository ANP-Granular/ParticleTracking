# Copyright (c) 2023-24 Adrian Niemann, and others
#
# This file is part of RodTracker.
# RodTracker is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RodTracker is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RodTracker. If not, see <http://www.gnu.org/licenses/>.

# TODO: add docs
import logging
from typing import Any, Iterable, Tuple

from PyQt5 import QtCore, QtGui, QtWidgets

import RodTracker.backend.file_locations as fl
import RodTracker.backend.logger as lg
import RodTracker.backend.miscellaneous as misc
import RodTracker.backend.settings as se
from RodTracker.backend.data import ImageData
from RodTracker.ui import settings

_logger = logging.getLogger(__name__)


# TODO: add class documentation
class ImageInteractionTab(QtWidgets.QLabel):
    _logger: lg.ActionLogger = None
    _id: str = "unknown"

    _image: QtGui.QImage = None
    _pixmap: QtGui.QPixmap = None
    _scale_factor: float = 1.0
    _offset: Tuple[int, int] = [0, 0]

    # TODO: add docstring
    image_manager: ImageData = None

    _particles: Iterable = []
    """List of particles that are displayed by this widget (can/will be of a
    specialized class)."""
    loaded_particles = QtCore.pyqtSignal(int, name="loaded_particles")
    """pyqtSignal(int) : Notifies objects, how many particles have just been
    loaded for display.
    """
    is_busy = QtCore.pyqtSignal(bool)
    """pyqtSignal(bool) : Notifies when a background task is started/finished.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        se.Settings().setting_signals.setting_changed.connect(
            self.update_settings
        )

        self.logger = lg.MainLogger().get_new_logger(self._id)
        self.image_manager = ImageData()
        self.image_manager.data_loaded.connect(
            lambda num, id, folder: self._set_id(id)
        )
        self.image_manager.next_img[QtGui.QImage].connect(self.image)

        # Widget behaviour changes
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)
        self.setMouseTracking(True)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setFrameShadow(QtWidgets.QFrame.Plain)
        self.setText("")
        self.setPixmap(QtGui.QPixmap(fl.logo_path()))
        self.setScaledContents(False)
        self.setAlignment(QtCore.Qt.AlignCenter)

    def _set_id(self, new_id: str):
        self.ID = new_id

    def __str__(self) -> str:
        return (
            f"{self.__class__.__module__}.{self.__class__.__name__}"
            f"('{self._id}')"
        )

    @property
    def logger(self) -> lg.ActionLogger:
        """
        A logger object keeping track of users' actions performed on this
        widget and its contents.

        Returns
        -------
        ActionLogger
        """
        return self._logger

    @logger.setter
    def logger(self, new_logger: lg.ActionLogger):
        if self._logger:
            self._logger.undo_action.disconnect()
        self._logger = new_logger
        self._logger.undo_action.connect(self.undo_action)

    @property
    def ID(self) -> str:
        """
        Property that holds a string used as and ID for logging and data
        selection.

        It must be human readable as it is used for labelling the performed
        actions displayed in the GUI.

        Returns
        -------
        str
        """
        return self._id

    @ID.setter
    def ID(self, new_id: str):
        # TODO: evaluate, whether to change the ImageData ID here as well
        self._id = new_id
        try:
            self._logger.parent_id = new_id
        except AttributeError:
            raise AttributeError(
                "There is no ActionLogger set for this Widget yet."
            )

    @property
    def particles(self) -> Iterable:
        """
        Property that hold representations of the particles that are
        displayable on this widget.

        Returns
        -------
        Iterables
        """
        return self._particles

    @particles.setter
    def particles(self, new_particles: Iterable):
        raise NotImplementedError

    @particles.deleter
    def particles(self):
        raise NotImplementedError

    @QtCore.pyqtSlot(QtGui.QImage)
    def image(self, new_image: QtGui.QImage):
        """Show a new image in this widget.

        Parameters
        ----------
        new_image : QImage

        Raises
        ------
        ValueError
            If the image is Null.
        """
        if new_image.isNull():
            raise ValueError("Assigned image cannot be 'Null'.")
        self._image = new_image
        self._pixmap = QtGui.QPixmap.fromImage(new_image)
        self._scale_image()

    @property
    def scale_factor(self) -> float:
        """
        Property that holds the scaling factor by which the original image
        is scaled when displayed.

        Returns
        -------
        float
        """
        return self._scale_factor

    @scale_factor.setter
    def scale_factor(self, factor: float):
        if factor <= 0:
            raise ValueError("factor must be >0")
        self._scale_factor = factor
        self._scale_image()

    def _scale_image(self) -> None:
        if self._image is None:
            return
        old_pixmap = QtGui.QPixmap.fromImage(self._image)
        new_pixmap = old_pixmap.scaledToHeight(
            int(old_pixmap.height() * self._scale_factor),
            QtCore.Qt.SmoothTransformation,
        )
        self.setPixmap(new_pixmap)
        self._pixmap = new_pixmap

        # Handle the pixmap's shift to the center of the widget, in cases
        #  the surrounding scrollArea is larger than the pixmap
        x_off = (self.width() - self._pixmap.width()) // 2
        y_off = (self.height() - self._pixmap.height()) // 2
        self._offset = [x_off if x_off > 0 else 0, y_off if y_off > 0 else 0]

        # Update the particle display to the new image size
        self.update_particle_display()

    def scale_to_size(self, new_size: QtCore.QSize):
        """Scales the image to a specified size.

        Scales the image to a specified size, while retaining the image's
        aspect ratio.

        Parameters
        ----------
        new_size : QSize

        Returns
        -------
        None
        """
        if self._image is None:
            return
        old_pixmap = QtGui.QPixmap.fromImage(self._image)
        height_ratio = new_size.height() / old_pixmap.height()
        width_ratio = new_size.width() / old_pixmap.width()
        if height_ratio > width_ratio:
            # Use width
            self.scale_factor = width_ratio
            return
        else:
            # Use height
            self.scale_factor = height_ratio
            return

    def update_particle_display(self) -> Any:
        # TODO: document
        _logger.debug(
            "ImageInteractionTab.update_particle_display() is not "
            "implemented!",
        )

    def clear_screen(self) -> None:
        """Removes the displayed rods and deletes them.

        Returns
        -------
        None
        """
        _logger.debug(
            "ImageInteractionTab.clear_screen() is not implemented!",
        )

    def activate(self):
        """Is triggered when this tab is activate in the GUI.

        (Re-)Connect all signals between e.g. MenuItems, data providers, etc.
        so that this widget gets all necessary control to be considered active.
        """
        _logger.debug(
            f"ImageInteractionTab('{self.ID}').activate() is not implemented!",
        )

    @QtCore.pyqtSlot(lg.Action)
    def undo_action(self, action: lg.Action) -> Any:
        """Reverts an :class:`.Action` performed on a particle.

        Reverts the :class:`.Action` given to this function, if it was
        constructed by this object. It returns without further actions, if the
        :class:`.Action` was not originally performed on this object or if it
        is of an unknown type.

        Parameters
        ----------
        action : Action
            An :class:`.Action` that was logged previously. It will only be
            reverted, if it associated with this object.

        Returns
        -------
        None
        """
        _logger.warning(
            "ImageInteractionTab.undo_action() is not implemented!",
        )

    # TODO: adjust docstring
    @QtCore.pyqtSlot(str, object)
    def update_settings(self, key: str, new_value: Any) -> None:
        """Catches updates of the settings from a :class:`.Settings` class.

        Checks for the keys relevant to itself and updates the corresponding
        attributes. Redraws itself with the new settings in place.

        Parameters
        ----------
        settings : dict

        Returns
        -------
        None
        """
        pass

    # TODO: add docs
    def extract_particles(self, data):
        _logger.debug(
            f"ImageDisplayTab('{self.ID}').extract_particles() is not "
            "implemented!"
        )


# TODO: add class documentation
class UtilityTab(QtWidgets.QWidget):
    _logger: lg.ActionLogger = None
    _id: str = "unknown"

    is_busy = QtCore.pyqtSignal(bool)
    """pyqtSignal(bool) : Notifies when a background task is started/finished.
    """

    def __init__(self, id: str = "unknown", *args, **kwargs):
        super().__init__(*args, **kwargs)
        se.Settings().setting_signals.setting_changed.connect(
            self.update_settings
        )
        self._id = id
        self.logger = lg.MainLogger().get_new_logger(self._id)

    def __str__(self) -> str:
        return (
            f"{self.__class__.__module__}.{self.__class__.__name__}"
            f"('{self._id}')"
        )

    @property
    def logger(self) -> lg.ActionLogger:
        """
        A logger object keeping track of users' actions performed on this
        widget and its contents.

        Returns
        -------
        ActionLogger
        """
        return self._logger

    # TODO: the connection to self.undo_action might not be good
    @logger.setter
    def logger(self, new_logger: lg.ActionLogger):
        if self._logger:
            self._logger.undo_action.disconnect()
        self._logger = new_logger
        self._logger.undo_action.connect(self.undo_action)

    @property
    def ID(self) -> str:
        """
        Property that holds a string used as and ID for logging and data
        selection.

        It must be human readable as it is used for labelling the performed
        actions displayed in the GUI.

        Returns
        -------
        str
        """
        return self._id

    @ID.setter
    def ID(self, new_id: str):
        self._id = new_id
        try:
            self._logger.parent_id = new_id
        except AttributeError:
            raise AttributeError(
                "There is no ActionLogger set for this " "Widget yet."
            )

    def activate(self):
        """Is triggered when this tab is activate in the GUI.

        (Re-)Connect all signals between e.g. MenuItems, data providers, etc.
        so that this widget gets all necessary control to be considered active.
        """
        _logger.debug(
            f"UtilityTab('{self.ID}').activate() is not implemented!",
        )

    @QtCore.pyqtSlot(lg.Action)
    def undo_action(self, action: lg.Action) -> Any:
        """Reverts an :class:`.Action` performed on a particle.

        Reverts the :class:`.Action` given to this function, if it was
        constructed by this object. It returns without further actions, if the
        :class:`.Action` was not originally performed on this object or if it
        is of an unknown type.

        Parameters
        ----------
        action : Action
            An :class:`.Action` that was logged previously. It will only be
            reverted, if it associated with this object.

        Returns
        -------
        None
        """
        _logger.debug(
            "UtilityTab.undo_action() is not implemented!",
        )

    @QtCore.pyqtSlot(str, object)
    def update_settings(self, key: str, new_value: Any) -> None:
        # TODO: adjust docstring
        """Catches updates of the settings from a :class:`.Settings` class.

        Checks for the keys relevant to itself and updates the corresponding
        attributes. Redraws itself with the new settings in place.

        Parameters
        ----------
        settings : dict

        Returns
        -------
        None
        """
        pass


# TODO: add/update docs
class HistoryTab(UtilityTab):
    """A custom widget to display :class:`.Action` objects in the GUI.

    This widget displays the actions performed by the user in the GUI. It also
    updates when they are un-/redone.

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Setup UI:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.lw_actions = QtWidgets.QListWidget(self)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Expanding
        )
        self.lw_actions.setSizePolicy(sizePolicy)
        self.lw_actions.setMaximumSize(QtCore.QSize(16777214, 16777215))
        layout.addWidget(self.lw_actions)
        self.pb_undo = QtWidgets.QPushButton(self)
        self.pb_undo.setMinimumSize(QtCore.QSize(0, 0))
        self.pb_undo.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.pb_undo.setText("Undo")
        self.pb_undo.setIcon(QtGui.QIcon(fl.undo_icon_path()))
        layout.addWidget(self.pb_undo)

        main_logger = lg.MainLogger()
        main_logger.history_ui = self
        # connect to all previously created loggers
        for prev_logger in main_logger._loggers:
            self.connect_to_logger(prev_logger)

    @property
    def logger(self) -> lg.ActionLogger:
        """
        A logger object keeping track of users' actions performed on this
        widget and its contents.

        Returns
        -------
        ActionLogger
        """
        return self._logger

    @logger.setter
    def logger(self, new_logger: lg.ActionLogger):
        self._logger = new_logger

    @QtCore.pyqtSlot(lg.Action)
    def add_action(self, new_action: lg.Action) -> None:
        """Adds a new action to the list being displayed in the GUI."""
        # if not lg.MainLogger()._loggers:
        #     # No loggers exist yet/anymore
        #     return
        self.lw_actions.insertItem(self.lw_actions.count(), new_action)
        self.lw_actions.scrollToBottom()
        _logger.info(str(new_action))

    @QtCore.pyqtSlot(lg.Action)
    def remove_action(self, undo_action: lg.Action) -> None:
        """Removes an Action from the displayed list and deletes it."""
        item_pos = self.lw_actions.row(undo_action)
        undo_item = self.lw_actions.takeItem(item_pos)
        _logger.warning(f"Removed action: {undo_action}")
        del undo_item
        self.lw_actions.scrollToBottom()

    # TODO: add docs
    def connect_to_logger(self, logger: lg.ActionLogger):
        logger.added_action.connect(self.add_action)
        logger.undo_action.connect(self.remove_action)
        logger.undone_action.connect(self.remove_action)
        _logger.debug(f"Connected to: {logger}")


class SettingsTab(UtilityTab):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Setup UI:
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.sa_settings = QtWidgets.QScrollArea(self)
        self.sa_settings.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.sa_settings.setWidgetResizable(True)
        size_policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self.sa_settings.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.sa_settings.setSizePolicy(size_policy)
        self.inner_layout = QtWidgets.QVBoxLayout(self.sa_settings)
        self.inner_layout.setSpacing(3)

        self.sa_settings.setLayout(self.inner_layout)
        self.pb_defaults = QtWidgets.QPushButton(self)
        self.pb_defaults.setMinimumSize(QtCore.QSize(0, 0))
        self.pb_defaults.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.pb_defaults.setText("Restore Defaults")

        self.pb_open_settings = QtWidgets.QPushButton(self)
        self.pb_open_settings.setMinimumSize(QtCore.QSize(0, 0))
        self.pb_open_settings.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.pb_open_settings.setText("Open Settings File")
        self.pb_open_settings.clicked.connect(lambda _: misc.open_settings())

        outer_layout.addWidget(self.pb_open_settings)
        outer_layout.addWidget(self.sa_settings)
        outer_layout.addWidget(self.pb_defaults)

        spacer = QtWidgets.QSpacerItem(
            10,
            10,
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Expanding,
        )
        self.inner_layout.addItem(spacer)

    # TODO: add docs
    def add_setting(self, settings_widget: settings.Setting):
        key = settings_widget.id
        section, item = key.split(".", maxsplit=1)
        insert_idx = None
        for idx in range(self.inner_layout.count()):
            try:
                obj_name = self.inner_layout.itemAt(idx).widget().objectName()
            except AttributeError:
                continue
            if obj_name == section:
                insert_idx = idx + 1
                break
        if insert_idx is None:
            insert_idx = self.inner_layout.count()
            section_label = QtWidgets.QLabel(section, self)
            section_label.setStyleSheet(
                "font-weight: bold;font: 20px;color: black;"
            )
            section_label.setObjectName(section)
            self.inner_layout.insertWidget(insert_idx - 1, section_label)
        self.inner_layout.insertWidget(insert_idx, settings_widget)

        # get value from storage
        try:
            saved_value = se.Settings().get_setting(settings_widget.id)
            settings_widget.set_value_silently(saved_value)
        except se.UnknownSettingError:
            se.Settings().add_setting(
                settings_widget.id, settings_widget.default_val
            )
        # connect 'Restore Defaults'-button
        self.pb_defaults.clicked.connect(
            lambda _: settings_widget.restore_default()
        )

        settings_widget.setting_updated.connect(se.Settings().setting_updated)
        settings_widget.setting_updated.connect(
            lambda id, value: _logger.info(f"Setting ({id}) updated: {value}")
        )
