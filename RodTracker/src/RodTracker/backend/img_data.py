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
from pathlib import Path
from typing import List, Tuple

from PyQt5 import QtCore, QtGui

import RodTracker.backend.logger as lg
import RodTracker.ui.dialogs as dialogs

_logger = logging.getLogger(__name__)


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

    _logger: lg.ActionLogger = None
    _logger_id: str

    def __init__(self, cam_number: int, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.folder = None
        self.frames: List[int] = []
        self.files: List[Path] = []
        self.data_id = ""
        self.frame_idx = None
        self._logger_id = f"camera_{cam_number}"

    def select_images(self, pre_selection: str = ""):
        """Lets the user select an image folder to show images from.

        Lets the user select a folder out of which all images are loaded for
        later display. The first image in this folder is opened immediately.

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
        chosen_folder = dialogs.select_data_folder(
            "Open a folder of images",
            pre_selection,
            "Directory with Images (*.gif *.jpeg *.jpg *.png *.tiff)",
        )
        if chosen_folder is None:
            # File selection was aborted
            return
        self.open_image_folder(chosen_folder)

    def open_image_folder(self, chosen_folder: Path):
        """Attempts to open an image folder and show the first image.

        All images of the folder from the chosen file's folder are marked for
        later display. The first image is opened immediately. It tries to
        extract a camera id from the selected folder and logs the opening
        action.

        Parameters
        ----------
        chosen_folder: Path
            Path to chosen folder.

        Returns
        -------
        None


        .. Hint::

            **Emits**

            - :attr:`next_img` [QImage]
            - :attr:`next_img` [int, int]
            - :attr:`data_loaded`
        """
        if not chosen_folder:
            return
        chosen_folder = chosen_folder.resolve()
        files, frames = get_images(chosen_folder)
        if len(files) == 0:
            _logger.warning(
                "No valid frames found in the selected folder: "
                f"{chosen_folder}"
            )
            dialogs.show_warning(
                "No valid frames found in the selected folder:\n"
                f"{chosen_folder}"
            )
            return
        # Sort according to name / ascending order
        files.sort()
        frames.sort()

        # Open file
        loaded_image = QtGui.QImage(str(files[0]))
        if loaded_image.isNull():
            dialogs.show_warning(f"Cannot load {files[0]}")
            return

        self.folder = chosen_folder
        self.files = files
        self.frames = frames
        self.frame_idx = 0

        # Get camera id for data display
        self.data_id = self.folder.name

        # Send update signals
        self.data_loaded.emit(len(self.files), self.data_id, self.folder)
        self.next_img[QtGui.QImage].emit(loaded_image)
        self.next_img[int, int].emit(
            self.frames[self.frame_idx], self.frame_idx
        )
        if self._logger is not None:
            action = lg.FileAction(
                self.folder,
                lg.FileActions.LOAD_IMAGES,
                len(self.files),
                cam_id=self.data_id,
                parent_id=self._logger_id,
            )
            action.parent_id = self._logger_id
            self._logger.add_action(action)

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


def get_images(read_dir: Path) -> Tuple[List[Path], List[int]]:
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
        Full paths to the found image files and frame numbers extracted from
        the file names.
    """

    files = []
    file_ids = []
    for f in read_dir.iterdir():
        if f.is_file() and f.suffix in [".png", ".jpg", ".jpeg"]:
            try:
                # Split any non-frame describing part of the filename and
                # convert to integer (frame number)
                tmp_id = int(f.stem.split("_")[-1])
            except ValueError:
                _logger.debug(f"Invalid file naming: {f}")
                continue
            # Add all image files and frame IDs to a output
            file_ids.append(tmp_id)
            files.append(f)
    return files, file_ids
