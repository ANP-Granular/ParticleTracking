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

"""**TBD**"""

import logging
import os
from pathlib import Path
from typing import Any, List, Tuple, Union

from PyQt5 import QtCore, QtGui, QtWidgets

import RodTracker.backend.logger as lg
import RodTracker.backend.settings as se

_logger = logging.getLogger(__name__)


# TODO: change the docstrings to be generalized
class ImageData(QtCore.QObject):
    """Object for image data management for associated with a `RodImageWidget`.

    An `ImageData` object handles the loading and selection of images that are
    meant to be displayed using a `RodImageWidget`. One `ImageData` object is
    supposed to be responsible for the image dataset of one `RodImageWidget`.

    Parameters
    ----------
    cam_number : int
        The 'index' of the camera in the GUI this object is associated with.


    .. admonition:: Signals

        - :attr:`next_img`
        - :attr:`data_loaded`

    Attributes
    ----------
    folder : Path
        The path to the loaded image dataset folder.
        By default None.
    frames : List[int]
        List of loaded frames in the image dataset.
        By default [].
    files : List[Path]
        List of paths to the images in the loaded image dataset.
        By default [].
    data_id : str
        ID of the loaded image dataset. For this the selected folder's name is
        used. This is can also be used for identification of position data.
        Example value: "gp1". By default "".
    frame_idx : int
        Index of the currently displayed frame/image.
        By default None.
    """

    data_loaded = QtCore.pyqtSignal((int, str, Path))
    """pyqtSignal(int, str, Path) : A new image containing folder has been
    loaded successfully.

    Is emitted after successful loading of an image containing folder. It
    sends\n
    - the number of loaded frames,
    - the 'ID' of the loaded folder, and
    - the absolute path of the loaded folder.
    """

    next_img = QtCore.pyqtSignal([int, int], [QtGui.QImage], name="next_img")
    """pyqtSignal([QImage], [int, int]) : Loading of the *next* image file has
    been successful.

    Is emitted after successful loading of an image file. Two different
    variants are sent. The first carries the loaded image as a ``QImage``.
    The second variant carries the frame number and the index of the
    loaded frame.
    """

    logger: lg.ActionLogger = None
    """A logger object keeping track of users' actions performed with this
    object. This is set by the main application.
    """
    _id: str = ""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        se.Settings().setting_signals.setting_changed.connect(
            self.update_settings
        )

        self.folder = None
        self.frames: List[int] = []
        self.files: List[Path] = []
        self.data_id = ""
        self.frame_idx = None
        self.logger = lg.MainLogger().get_new_logger(self._id)

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
            self.logger.parent_id = new_id
        except AttributeError:
            raise AttributeError(
                "There is no ActionLogger set for this " "Widget yet."
            )

    def select_images(self, pre_selection: str = ""):
        """Lets the user select an image folder to show images from.

        Lets the user select an image from folder out of which all images
        are marked for later display. The selected image is opened
        immediately.

        Parameters
        ----------
        pre_selection : str
            String representation of a folder that is supposed to be used as
            the initial directory for the image selection dialog.
            By default "".

        Returns
        -------
        None
        """
        kwargs = {}
        # handle file path issue when running on linux as a snap
        if "SNAP" in os.environ:
            kwargs["options"] = QtWidgets.QFileDialog.DontUseNativeDialog
        chosen_file, _ = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Open an image",
            pre_selection,
            "Images (*.png *.jpeg *.jpg)",
            **kwargs,
        )
        if chosen_file == "":
            # File selection was aborted
            return
        chosen_file = Path(chosen_file).resolve()
        self.open_image_folder(chosen_file)

    def open_image_folder(self, chosen_file: Path):
        """Tries to open an image folder to show the given image.

        All images of the folder from the chosen file's folder are marked for
        later display. The selected image is opened immediately. It tries to
        extract a camera id from the selected folder and logs the
        opening action.

        Parameters
        ----------
        chosen_file: Path
            Path to image file chosen for immediate display.

        Returns
        -------
        None


        .. Hint::

            **Emits**

            - :attr:`next_img` [QImage]
            - :attr:`next_img` [int, int]
            - :attr:`data_loaded`
        """
        if not chosen_file:
            return
        chosen_file = chosen_file.resolve()
        frame = int(chosen_file.stem.split("_")[-1])
        # Open file
        loaded_image = QtGui.QImage(str(chosen_file))
        if loaded_image.isNull():
            QtWidgets.QMessageBox.information(
                None, "Image Viewer", f"Cannot load {chosen_file}"
            )
            return
        # Directory
        self.folder = chosen_file.parent
        self.files, self.frames = self.get_images(self.folder)
        self.frame_idx = self.frames.index(frame)

        # Sort according to name / ascending order
        desired_file = self.files[self.frame_idx]
        self.files.sort()
        self.frame_idx = self.files.index(desired_file)
        self.frames.sort()

        # Get camera id for data display
        self.data_id = self.folder.name

        # Send update signals
        self.data_loaded.emit(len(self.files), self.data_id, self.folder)
        self.next_img[QtGui.QImage].emit(loaded_image)
        self.next_img[int, int].emit(
            self.frames[self.frame_idx], self.frame_idx
        )
        if self.logger is not None:
            action = lg.FileAction(
                self.folder,
                lg.FileActions.LOAD_IMAGES,
                len(self.files),
                cam_id=self.data_id,
                parent_id=self._id,
            )
            action.parent_id = self._id
            self.logger.add_action(action)

    def image_at(self, index: int) -> None:
        """Open an image by its index in the loaded image dataset.

        Parameters
        ----------
        index : int
            Index of the image, that is supposed to be opened.
        """
        self.next_image(index - self.frame_idx)

    def image(self, frame: int) -> None:
        """Open an image by its frame number.

        Parameters
        ----------
        frame : int
            Frame number of the image, that is supposed to be opened.
        """
        self.next_image(self.frames.index(frame) - self.frame_idx)

    def next_image(self, direction: int) -> None:
        """Attempts to open the next image.

        Attempts to open the next image in the direction provided relative
        to the currently opened image.

        Parameters
        ----------
        direction : int
            Direction of the image to open next. Its the index relative to
            the currently opened image.\n
            | a) direction = 3    ->  opens the image three positions further
            | b) direction = -1   ->  opens the previous image
            | c) direction = 0    ->  keeps the current image open

        Returns
        -------
        None


        .. Hint::

            **Emits**

            - :attr:`next_img` [QImage]
            - :attr:`next_img` [int, int]
        """
        if direction == 0:
            # No change necessary
            return
        if self.files:
            # Switch images
            self.frame_idx += direction
            if self.frame_idx > (len(self.files) - 1):
                self.frame_idx -= len(self.files)
            elif self.frame_idx < 0:
                self.frame_idx += len(self.files)
            # Chooses next image with specified extension
            filename = self.files[self.frame_idx]
            image_next = QtGui.QImage(str(filename))
            if image_next.isNull():
                # The file is not a valid image, remove it from the list
                # and try to load the next one
                _logger.warning(
                    f"The image {filename.stem} is corrupted and "
                    f"therefore excluded."
                )
                self.files.remove(filename)
                self.data_loaded.emit(
                    len(self.files), self.data_id, self.folder
                )
                self.next_image(1)
            else:
                self.next_img[QtGui.QImage].emit(image_next)
                self.next_img[int, int].emit(
                    self.frames[self.frame_idx], self.frame_idx
                )
        else:
            # No files loaded yet. Let the user select images.
            self.select_images()

    # TODO: might be moved to the extension!
    @classmethod
    def get_images(cls, read_dir: Path) -> Tuple[List[Path], List[int]]:
        """Reads image files from a directory.

        Checks all files for naming convention according to the selected file
        and generates the frame IDs from them.

        Parameters
        ----------
        read_dir : Path
            Path to the directory to read image files from.

        Returns
        -------
        Tuple[List[Path], List[int]]
            Full paths to the found image files and frame numbers extracted
            from the file names.
        """

        files = []
        file_ids = []
        for f in read_dir.iterdir():
            if f.is_file() and f.suffix in [".png", ".jpg", ".jpeg"]:
                # Add all image files to a list
                files.append(f)
                # Split any non-frame describing part of the filename
                tmp_id = f.stem.split("_")[-1]
                file_ids.append(int(tmp_id))
        return files, file_ids

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


class PositionData(QtCore.QObject):
    # FIXME: currently its private (previously `_logger_id`), make it public
    logger_id: str
    # FIXME: currently its private (previously `_logger`), make it public
    logger: lg.ActionLogger = None

    # FIXME: currently its private (previously `_show_2D`), make it public
    # FIXME: rename to a better name
    show_particles: bool = True
    # FIXME: rename for generalization (previously `folder`)
    input: Path = None
    """Path to file/folder from which the position data is initially loaded."""
    # FIXME: rename for generalization (previously `out_folder`)
    output: Path = None
    """Path to selected file/folder for later saving of the changed position
    data."""

    # FIXME: main app only requires [Path, Path, list] -> change the use of
    #   [list] such that it uses the available option instead when
    #   communicating with the main app!
    data_loaded: QtCore.pyqtSignal(
        [Path, Path, list],  # input, output, classes
        name="data_loaded",
    )
    """pyqtSignal : Propagates information about loaded position data.

    - **[Path, Path, list]**:\n
      The payload is the folder the loaded data is read from (see `input`),
      the folder any data changes will be written to (see `output`), and a
      list of the particle classes found during reading of the data.
    """

    # FIXME: renamed for clarification (previously `data_2d`)
    # TODO: update docstring
    position_data_2d = QtCore.pyqtSignal([object], name="position_data_2d")
    """pyqtSignal : Provide 2D particle position data for other objects to
    display,

    <mark>**defined by :attr:`frame`, :attr:`color_2D`, and :attr:`rod_2D`.**
    </mark>
    """

    # TODO: potentially change signature such that object is identified from it
    saved = QtCore.pyqtSignal(name="saved")
    """pyqtSignal : Notify objects, that all changed data has been saved
    successfully.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = lg.MainLogger().get_new_logger(self.logger_id)
        se.Settings().setting_signals.setting_changed.connect(
            self.update_settings
        )

    # FIXME: rename for generalization (previously `select_rods`)
    def select_data(self, pre_selection: str = "") -> None:
        """Lets the user select a folder with particle position data.

        Lets the user select a file/folder with particle position data. The
        selected folder/file is probed for eligable data and the user can
        otherwise retry the selection.
        After that an attempt to loading the data is started, if that fails,
        users can retry to open another file/folder.

        Parameters
        ----------
        pre_selection : str
            Path to a folder that the ``QFileDialog`` is attempted to be opened
            with. By default and as a fallback the current working directory is
            used.\n
            Default is ``""``.

        Returns
        -------
        None
        """
        _logger.debug(
            f"PositionData('{self.logger_id}').select_data() is not "
            "implemented!",
        )

    def save(self) -> None:
        """Saves the currently loaded (and altered) position data to disk.

        Saves the loaded data with changes made in all available perspectives
        to disk.
        A warning is issued, if the user attempts to overwrite the original
        data files and they can decide to actually overwrite it or are given a
        chance to change the output location.

        .. hint::

            **Emits**

            - :attr:`data_loaded` [Path, Path, list]
            - :attr:`saved`
        """
        _logger.debug(
            f"PositionData('{self.logger_id}').save() is not implemented!",
        )

    def set_output(self, new_folder: Union[str, Path]):
        """Set the output folder for data saving.

        Parameters
        ----------
        new_folder : str | Path
        """
        _logger.debug(
            f"PositionData('{self.logger_id}').set_output() is not "
            "implemented!",
        )

    def set_frame(self, new_frame: int):
        """Set the frame for data sending and trigger data sending.

        Parameters
        ----------
        frame : int
            Frame to send data for.
        """
        _logger.debug(
            f"PositionData('{self.logger_id}').set_frame() is not "
            "implemented!",
        )

    def data_changed(self, change: lg.Action) -> None:
        """Change the loaded data according to the performed :class:`.Action`.

        Change the loaded data according to the performed :class:`.Action` and
        notify other objects about this update.

        Parameters
        ----------
        change : Action


        .. hint::

            **Emits**

            - :attr:`data_update`               **(potentially repeatedly)**
        """
        _logger.debug(
            f"PositionData('{self.logger_id}').data_changed() is not "
            "implemented!",
        )

    # FIXME: rename & merge for generalization (`update_rod_2D`,
    #        `update_color_2D()`)
    # TODO: signature has been changed to allow 3 modes of operation
    #   all, class, individual
    #   Signature might need to change again to be more efficient.
    def update_2D_data(self, class_ID: str = None, particle_ID: int = None):
        """Update the particle(s) for 2D data sending and trigger sending of
        2D data.

        Parameters
        ----------
        class_ID : str | None
            Class of particle(s) to display in 2D.
            Default is ``None``, i.e. all available classes.
        particle_ID : int | None
            Particle number to display in 2D.
            Default is ``None``, i.e. all available particles.
        """
        _logger.debug(
            f"PositionData('{self.logger_id}').update_2D_data() is not "
            "implemented!",
        )

    def update_settings(self, key: str, new_value: Any) -> None:
        # TODO: adjust docstring
        """Catches updates of the settings from a :class:`.Settings` class.

        Checks for the keys relevant to itself and updates the corresponding
        attributes. Redraws itself with the new settings in place, if
        settings were changed.

        Parameters
        ----------
        settings : dict

        Returns
        -------
        None
        """
        pass
