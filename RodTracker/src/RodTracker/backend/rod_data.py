#  Copyright (c) 2022 Adrian Niemann Dmitry Puzyrev
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

import re
import math
import logging
from typing import List, Tuple, Dict, Iterable, Union
from pathlib import Path
import pandas as pd
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QMessageBox
import RodTracker.backend.logger as lg
import RodTracker.backend.file_locations as fl
import RodTracker.backend.parallelism as pl
import RodTracker.ui.dialogs as dialogs

RE_COLOR_DATA = re.compile('rods_df_\\w+\\.csv')                # noqa: W605
RE_SEEN = re.compile('seen_gp\\d+')                            # noqa: W605
RE_2D_POS = re.compile('[xy][12]_gp\\d+')                      # noqa: W605
RE_3D_POS = re.compile('[xyz][12]')                           # noqa: W605
POSITION_SCALING = 1.0

rod_data: pd.DataFrame = None
lock = QtCore.QReadWriteLock(QtCore.QReadWriteLock.Recursive)
_logger = logging.getLogger(__name__)


class RodData(QtCore.QObject):
    """Object for rod position data management.

    A `RodData` object handles the loading, selection, changing and saving of
    rod position data, that are meant to be displayed by `RodImageWidget`s and
    `View3D` objects.

    Parameters
    ----------
    *args : iterable
        Positional arguments for the `QObject` superclass.
    **kwargs : dict
        Keyword arguments for the `QObject` superclass.

    Attributes
    ----------
    folder : Path | None
        Path to the folder the position data is loaded from.
    out_folder : Path | None
        Path to the (automatically) selected folder for later output of the
        corrected dataset.
    threads : QThreadPool
        Thread pool for asynchronous tasks.
    frame : int | None
        Frame number of the currently provided position data.
    color_2D : str | None
        Color of the currently provided 2D position data.
    color_3D : str | None
        Color of the currently provided 3D position data. None, if all colors
        are provided.
    rod_2D : str | None
        Rod number of the corrently provided 2D position data. None, if all
        rods are provided.
    rod_3D : str | None
        Rod number of the corrently provided 3D position data. None, if all
        rods are provided.
    cols_2D : List[str]
        Columns of the loaded DataFrame relevant for 2D data display.
    cols_3D : List[str]
        Columns of the loaded DataFrame relevant for 3D data display.
    show_2D : bool
        Flag, whether to provide 2D data.
        Default is True.
    show_3D : bool
        Flag, whether to provide 3D data.
        Default is True.

    Signals
    -------
    data_2d(DataFrame, str)
        Provide 2D rod position data for other objects to display, defined by
        'frame', 'color_2D', and 'rod_2D'.
    data_3d(DataFrame)
        Provide 2D rod position data for other objects to display, defined by
        'frame', 'color_3D', and 'rod_3D'.
    seen_loaded(dict, list)
        Information of the rod dataset about a rod being 'seen' or 'unseen' for
        display as a tree.
        Dict[Dict[Dict[list]]] -> (frame, color, particle, camera)
        list -> List of 'camera' IDs on which a rod can be "seen"/"unseen".
    data_update(dict)
        Notify objects about updates in the 'seen'/'unseen' status of rods.
        dict -> Information about the rod, whos 'seen' status has changed.
                Mandatory keys: "frame", "cam_id", "color", "seen", "rod_id"
    saved()
        Notify objects, that all changed data has been saved successfully.

    Slots
    -----
    catch_data(Action)
    catch_number_switch(NumberChangeActions, int, int, str)
    catch_number_switch(NumberChangeActions, int, int, str, str, int)
    save_changes()
    save_changes(bool)
    select_rods()
    select_rods(str)
    update_frame(int, int)
    update_color_2D(str)
    update_color_3D(str, bool)
    update_rod_2D(int)
    update_rod_3D(int, bool)
    update_settings(dict)
    """
    data_2d = QtCore.pyqtSignal([pd.DataFrame, str], name="data_2d")
    data_3d = QtCore.pyqtSignal([pd.DataFrame], name="data_3d")
    data_loaded = QtCore.pyqtSignal([Path, Path, list], [int, int, list],
                                    [str, str],
                                    name="data_loaded")
    seen_loaded = QtCore.pyqtSignal((dict, list), name="seen_loaded")
    data_update = QtCore.pyqtSignal((dict), name="data_update")
    saved = QtCore.pyqtSignal(name="saved")
    requested_data = QtCore.pyqtSignal([pd.DataFrame], name="requested_data")

    _logger: lg.ActionLogger = None
    _logger_id: str = "RodData"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.folder: Path = None
        self.out_folder: Path = None
        self._allow_overwrite: bool = False
        self.threads = QtCore.QThreadPool()

        # Controls which data to provide
        self._show_2D = True
        self._show_3D = True
        self.frame: int = None
        self.color_2D: str = None
        self.color_3D: str = None
        self.rod_3D: int = None
        self.rod_2D: int = None
        self.cols_3D: List[str] = []
        self.cols_2D: List[str] = []

    @property
    def show_2D(self) -> bool:
        """Flag, whether to send updates of 2D rod data.

        Returns
        -------
        bool
        """
        return self._show_2D

    @show_2D.setter
    def show_2D(self, flag: bool) -> None:
        self._show_2D = flag
        self.provide_data(data_3d=False)

    @property
    def show_3D(self) -> bool:
        """Flag, whether to send updates of 3D rod data.

        Returns
        -------
        bool
        """
        return self._show_3D

    @show_3D.setter
    def show_3D(self, flag: bool) -> None:
        self._show_3D = flag
        self.provide_data(data_2d=False)

    def set_out_folder(self, new_folder: Union[str, Path]):
        """Set the output folder for data saving.

        Parameters
        ----------
        new_folder : str | Path
        """
        self.out_folder = Path(new_folder).resolve()

    @QtCore.pyqtSlot()
    @QtCore.pyqtSlot(str)
    def select_rods(self, pre_selection: str = ""):
        """Lets the user select a folder with rod position data.

        Lets the user select a folder with rod position data. The selected
        folder is probed for eligable files and the user can otherwise try the
        selection again.
        After that an attempt to loading the data is started, if that fails,
        users can try to open another directory.

        Parameters
        ----------
        pre_selection : str
            Path to a folder that the `QFileDialog` is attempted to be opened
            with. By default and as a fallback the current working directory is
            used.
            Default is "".

        Returns
        -------
        None
        """
        try_again = True
        while try_again:
            chosen_folder = QtWidgets.QFileDialog.getExistingDirectory(
                None, 'Choose folder with position data', pre_selection)
            if chosen_folder == '':
                return
            chosen_folder = Path(chosen_folder).resolve()
            # Check for eligible files
            eligible_files = self.folder_has_data(chosen_folder)
            if not eligible_files:
                # No matching file was found
                msg = QMessageBox()
                msg.setWindowIcon(QtGui.QIcon(fl.icon_path()))
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("Rod Tracker")
                msg.setText(f"There were no useful files found in: "
                            f"'{chosen_folder}'")
                msg.setStandardButtons(
                    QMessageBox.Retry | QMessageBox.Cancel)
                user_decision = msg.exec()
                if user_decision == QMessageBox.Cancel:
                    # Stop folder selection
                    self._allow_overwrite = False
                    return
                else:
                    # Retry folder selection
                    continue

            try_again = not self.open_rod_folder(chosen_folder)

    def open_rod_folder(self, chosen_folder: Path) -> bool:
        """Attempts to open a folder with potential rod position data.

        It is evaluated which files in the folder are valid data files and what
        colors they describe. The data discovery/loading is logged.

        Parameters
        ----------
        chosen_folder : Path
            Path to a folder with files in the format of `RE_COLOR_DATA`.

        Returns
        -------
        bool
            True, if loading successful.
            False, if loading aborted.
        """
        self._allow_overwrite = False
        # Check whether there is already corrected data
        out_folder = chosen_folder.stem + "_corrected"
        out_folder = chosen_folder.parent / out_folder

        self.folder = chosen_folder
        self.out_folder = out_folder
        corrected_files = self.folder_has_data(out_folder)
        if corrected_files:
            msg = QMessageBox()
            msg.setWindowIcon(QtGui.QIcon(fl.icon_path()))
            msg.setIcon(QMessageBox.Question)
            msg.setWindowTitle("Rod Tracker")
            msg.setText("There seems to be corrected data "
                        "already. Do you want to use that "
                        "instead of the selected data?")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            user_decision = msg.exec()
            if user_decision == QMessageBox.Yes:
                self.folder = out_folder
                self._allow_overwrite = True
            else:
                return False

        # Load data
        global rod_data
        lock.lockForWrite()
        rod_data, found_colors = self.get_color_data(self.folder)
        frame_min = rod_data.frame.min()
        frame_max = rod_data.frame.max()
        columns = list(rod_data.columns)
        lock.unlock()

        cams = [col.split("_")[-1] for col in columns
                if re.fullmatch(RE_SEEN, col)]
        cols_pos_2d = [col for col in columns if re.fullmatch(RE_2D_POS, col)]
        cols_seen = [col for col in columns if re.fullmatch(RE_SEEN, col)]
        cols_pos_3d = [col for col in columns if re.fullmatch(RE_3D_POS, col)]
        self.cols_2D = [*cols_pos_2d, *cols_seen, "particle", "frame"]
        self.cols_3D = [*cols_pos_3d, "particle", "frame", "color"]

        self.data_loaded[Path, Path, list].emit(
            self.folder, self.out_folder, found_colors)
        self.data_loaded[int, int, list].emit(
            frame_min, frame_max, found_colors)
        self.data_loaded[str, str].emit(*cams)

        # Display as a tree
        worker = pl.Worker(self.extract_seen_information)
        worker.signals.result.connect(lambda ret: self.seen_loaded.emit(*ret))
        worker.signals.error.connect(lambda ret: lg.exception_logger(*ret))
        self.threads.start(worker)

        # Rod position data was selected correctly
        if self._logger is not None:
            action = lg.FileAction(self.folder, lg.FileActions.LOAD_RODS,
                                   parent_id=self._logger_id)
            self._logger.add_action(action)
        return True

    @QtCore.pyqtSlot()
    @QtCore.pyqtSlot(bool)
    def save_changes(self, temp_only: bool = False):
        """Saves the currently loaded (and altered) position data to disk.

        Saves the loaded data with changes made in all views to disk. A
        warning is issued, if the user tries to overwrite the original data
        files and they can decide to actually overwrite it or are given a
        chance to change the output folder.

        Parameters
        ----------
        temp_only : bool
            Flag to either save to the temporary files only or permanently
            to the (user-)chosen location.
            (Default is False)
        """
        # TODO: move saving to different Thread(, if it still takes too long)
        if rod_data is None:
            return
        # Clean up data from unused rods before permanent saving
        if not temp_only:
            self.clean_data()
        if self.out_folder == self.folder and not self._allow_overwrite:
            msg = QMessageBox()
            msg.setWindowIcon(QtGui.QIcon(fl.icon_path()))
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Rod Tracker")
            msg.setText("The saving path points to the original data!"
                        "Do you want to overwrite it?")
            msg.addButton("Overwrite", QMessageBox.ActionRole)
            btn_cancel = msg.addButton("Cancel",
                                       QMessageBox.ActionRole)
            msg.exec()
            if msg.clickedButton() == btn_cancel:
                return
        self.out_folder.mkdir(exist_ok=True)
        lock.lockForRead()
        for color in rod_data.color.unique():
            out_file = self.out_folder / f"rods_df_{color}.csv"
            df_out = rod_data.loc[rod_data.color == color].copy()
            df_out = df_out.astype({"frame": 'int', "particle": 'int'})
            df_out.to_csv(out_file, index_label="")
            if self._logger is not None:
                action = lg.FileAction(out_file, lg.FileActions.SAVE)
                action.parent_id = self._logger_id
                self._logger.add_action(action)
        lock.unlock()
        self.saved.emit()

    @QtCore.pyqtSlot(int, int)
    def update_frame(self, frame: int, _: int = None):
        """Update the frame for data sending and trigger data sending.

        Parameters
        ----------
        frame : int
            Frame to send data for.
        _ : int
            Index of the frame in the loaded dataset.
            Is not used here and just there to match a signal signature.
        """
        self.frame = frame
        self.provide_data()

    @QtCore.pyqtSlot(str)
    def update_color_2D(self, color: str = None):
        """Update the color for 2D data sending and trigger sending of 2D data.

        Parameters
        ----------
        color : str | None
            Color to display in 2D.
            Default is None.
        """
        self.color_2D = color
        self.provide_data(data_3d=False)

    @QtCore.pyqtSlot(int)
    def update_rod_2D(self, rod: int = None):
        """Update the rod for 2D data sending and trigger sending of 2D data.

        Parameters
        ----------
        rod : int | None
            Rod number to display in 2D. If no number is given all rods are
            selected.
            Default is None.
        """
        self.rod_2D = rod
        self.provide_data(data_3d=False)

    @QtCore.pyqtSlot(int, bool)
    def update_rod_3D(self, rod: int = None, send: bool = True):
        """Update the rod for 3D data sending(, trigger sending of 3D data).

        Parameters
        ----------
        rod : int | None
            Rod number to display in 3D. If no number is given all rods are
            selected.
            Default is None.
        send : bool
            Flag, whether to send a signal with the updated 3D data.
            Default is True.
        """
        self.rod_3D = rod
        if send:
            self.provide_data(data_2d=False)

    @QtCore.pyqtSlot(str, bool)
    def update_color_3D(self, color: str = None, send: bool = True):
        """Update the color for 3D data sending(, trigger sending of 3D data).

        Parameters
        ----------
        color : str | None
            Color to display in 3D. If no color is given all colors are
            selected.
            Default is None.
        send : bool
            Flag, whether to send a signal with the updated 3D data.
            Default is True.
        """
        self.color_3D = color
        if send:
            self.provide_data(data_2d=False)

    def provide_data(self, data_2d: bool = True, data_3d: bool = True):
        """Slice the loaded `DataFrame` and send update signals for 2D/3D data.

        Slice the loaded data according to `frame`, `color_2D`, `rod_2D`,
        `color_3D`, `rod_3D` and send signals with this payload for
        2D and 3D display.

        Parameters
        ----------
        data_2d : bool, optional
            Flag, whether to send 2D data.
            By default True.
        data_3d : bool, optional
            Flag, whether to send 3D data.
            By default True.
        """
        if self.frame is None or rod_data is None:
            return

        lock.lockForRead()
        out_data = rod_data.loc[rod_data.frame == self.frame]
        lock.unlock()

        if self._show_2D and data_2d:
            out_2d = out_data
            if self.color_2D is not None:
                out_2d = out_2d.loc[out_2d.color == self.color_2D]
            if self.rod_2D is not None:
                out_2d = out_2d.loc[out_2d.particle == self.rod_2D]
            self.data_2d.emit(out_2d[self.cols_2D].copy(), self.color_2D)
            if not len(out_2d):
                _logger.info(f"No 2D rod position data available for "
                             f"frame #{self.frame}.")

        if self._show_3D and data_3d:
            out_3d = out_data
            if self.color_3D is not None:
                out_3d = out_3d.loc[out_3d.color == self.color_3D]
            if self.rod_3D is not None:
                out_3d = out_3d.loc[out_3d.particle == self.rod_3D]
            out_3d = out_3d[self.cols_3D].copy()
            scale = out_3d.columns.difference(["particle", "frame", "color"])
            out_3d[scale] = out_3d[scale] * POSITION_SCALING
            self.data_3d.emit(out_3d)

    def get_data(self, frames: List[int] = None, colors: List[str] = None,
                 rods: List[int] = None, callback: callable = None,
                 data_2d: bool = True, data_3d: bool = True) -> pd.DataFrame:

        """Get part of the loaded rod position data.

        Currently not implemented.

        Parameters
        ----------
        frames : List[int], optional
            List of frames to select from the loaded dataset. All are returned,
            if no list is given.
            By default None.
        colors : List[str], optional
            List of colors to select from the loaded dataset. All are returned,
            if no list is given.
            By default None.
        rods : List[int], optional
            List of rod numbers to select from the loaded dataset. All are
            returned, if no list is given.
            By default None.

        Returns
        -------
        pd.DataFrame
            Copy of a slice of the loaded data.

        Raises
        ------
        NotImplementedError
        """
        # Provide data as requested, will return the requested data
        lock.lockForRead()
        out_data = rod_data
        lock.unlock()
        if out_data is None:
            return

        if frames is not None:
            out_data = rod_data.loc[rod_data.frame.isin(frames)]
        if colors is not None:
            out_data = out_data.loc[out_data.color.isin(colors)]
        if rods is not None:
            out_data = out_data.loc[out_data.particle.isin(rods)]

        if data_3d and data_2d:
            self.requested_data.emit(out_data.copy())
        elif data_3d:
            self.requested_data.emit(out_data[self.cols_3D].copy())
        elif data_2d:
            self.requested_data.emit(out_data[self.cols_2D].copy())

    @QtCore.pyqtSlot(pd.DataFrame)
    def receive_updated_data(self, data: pd.DataFrame):
        """Receives an updated part of the rod position data.

        Integrates the received rod position data into the previously loaded
        dataset, i.e. replacing updated data and appending new data.

        Parameters
        ----------
        data : pd.DataFrame
            Updated/New rod position data
        """
        with QtCore.QWriteLocker(lock):
            rod_data.set_index(["color", "frame", "particle"], inplace=True)
            rod_data.update(data.set_index(["color", "frame", "particle"]))
            rod_data.reset_index(inplace=True)
        if self.frame in data.frame.unique():
            self.provide_data()

    @QtCore.pyqtSlot(lg.Action)
    def catch_data(self, change: lg.Action) -> None:
        """Change the loaded data according to the performed `Action`.

        Change the loaded data according to the performed `Action` and notify
        other objects about this update.

        Parameters
        ----------
        change : Action
        """
        new_data = change.to_save()
        if new_data is None:
            return

        worker = pl.Worker(change_data, new_data=new_data)
        worker.signals.result.connect(
            lambda _: self.provide_data(data_3d=False))
        worker.signals.error.connect(lambda ret: lg.exception_logger(*ret))
        self.threads.start(worker)

        if isinstance(new_data["frame"], Iterable):
            tmp_data = {}
            for i in range(len(new_data["frame"])):
                tmp_data = {
                    "frame": new_data["frame"][i],
                    "cam_id": new_data["cam_id"][i],
                    "color": new_data["color"][i],
                    "position": new_data["position"][i],
                    "rod_id": new_data["rod_id"][i],
                    "seen": new_data["seen"][i]
                }
                self.data_update.emit(tmp_data)
        else:
            self.data_update.emit(new_data)

    @QtCore.pyqtSlot(lg.NumberChangeActions, int, int, str)
    @QtCore.pyqtSlot(lg.NumberChangeActions, int, int, str, str, int)
    def catch_number_switch(self, mode: lg.NumberChangeActions, old_id: int,
                            new_id: int, cam_id: str, color: str = None,
                            frame: int = None):
        """Change of rod numbers for more than one frame or camera.

        Exchanges rod numbers in more than one frame or camera according to the
        given mode.

        Parameters
        ----------
        mode : NumberChangeActions
            Possible modes are `ALL`, `ALL_ONE_CAM`, and `ONE_BOTH_CAMS`.
        old_id : int
        new_id : int
        cam_id : str
        color : str, optional
            By default None.
        frame : int, optional
            By default None.
        """
        if color is None:
            color = self.color_2D
        if frame is None:
            frame = self.frame

        worker = pl.Worker(rod_number_swap, mode=mode,
                           previous_id=old_id, new_id=new_id, color=color,
                           frame=frame, cam_id=cam_id)
        worker.signals.result.connect(
            lambda _: self.provide_data(data_3d=False))
        worker.signals.error.connect(lambda ret: lg.exception_logger(*ret))
        self.threads.start(worker)
        return

    @staticmethod
    def folder_has_data(path: Path) -> bool:
        """Checks a folder for file(s) that match the rod position data naming.

        Parameters
        ----------
        path : Path
            Folder path that shall be checked for files matching the pattern in
            `RE_COLOR_DATA`.

        Returns
        -------
        bool
            True, if at least 1 file matching the pattern was found.
            False, if no file was found or the folder does not exist.

        Raises
        ------
        NotADirectoryError
            Is raised if the given path exists but is not a directory.
        """
        if not path.exists():
            return False
        if not path.is_dir():
            raise NotADirectoryError
        for file in path.iterdir():
            if not file.is_file():
                continue
            if re.fullmatch(RE_COLOR_DATA, file.name) is not None:
                return True
        return False

    @staticmethod
    def get_color_data(read_dir: Path) -> Tuple[pd.DataFrame, List[str]]:
        """Reads rod data files from a directory.

        Checks all *.csv files for the rod data naming convention
        (see `RE_COLOR_DATA`), loads and concatenates them, and extracts the
        corresponding color from the file names.

        Parameters
        ----------
        read_dir : str
            Path to the directory to read position data files from.

        Returns
        -------
        Tuple[DataFrame, List[str]]
            Concatenated dataset and list of all found colors.
        """
        found_colors = []
        dataset = None
        for src_file in read_dir.iterdir():
            if not src_file.is_file():
                continue
            if re.fullmatch(RE_COLOR_DATA, src_file.name) is not None:
                found_color = src_file.stem.split("_")[-1]
                found_colors.append(found_color)

                data_chunk = pd.read_csv(src_file, index_col=0)
                data_chunk["color"] = found_color
                if dataset is None:
                    dataset = data_chunk.copy()
                else:
                    dataset = pd.concat([dataset, data_chunk])
        if dataset is not None:
            dataset.sort_values(["color", "frame", "particle"], inplace=True)
            dataset.reset_index(drop=True, inplace=True)
            dataset.fillna(0, inplace=True)
        return dataset, found_colors

    @staticmethod
    def extract_seen_information() -> Tuple[Dict[int, Dict[str, dict]], list]:
        """Extracts the seen/unseen parameter for all rods in `rod_data`.

        Returns
        -------
        Dict[Dict[dict]]
            Frame[Color[RodNo.]] -> out[501]["red"][1] = ["seen", "unseen"]
        list
            out_list = ["gp1_seen", "gp2_seen"]
        """
        global rod_data
        lock.lockForRead()
        seen_data = {}
        col_list = ["particle", "frame", "color"]
        to_include = [
            col for col in rod_data.columns if re.fullmatch(RE_SEEN, col)]
        col_list.extend(to_include)

        df_part = rod_data[col_list]
        for item in df_part.iterrows():
            item = item[1]
            current_seen = ['seen' if item[gp] else 'unseen' for gp in
                            to_include]
            if item.frame in seen_data.keys():
                if item.color in seen_data[item.frame].keys():
                    seen_data[item.frame][item.color][item.particle] = \
                        current_seen
                else:
                    seen_data[item.frame][item.color] = {item.particle:
                                                         current_seen}
            else:
                seen_data[item.frame] = \
                    {item.color: {item.particle: current_seen}}
        lock.unlock()
        return seen_data, [cam.split("_")[-1] for cam in to_include]

    def clean_data(self):
        """Deletes unused rods from the loaded dataset.

        Unused rods are identified by not having positional data in the
        *gp_* columns of the dataset. This assumed when only NaN or 0 is
        present in all these columns for a given rod/row. The user is asked
        to confirm these deletions and has the opportunity to exclude
        identified candidates from deletion. All confirmed rows are then
        deleted from the main dataset in RAM and therefore propagated to
        disk on the next saving operation.

        Returns
        -------
        None
        """
        global rod_data
        if rod_data is None:
            # No position data loaded
            return
        to_delete = self.find_unused_rods()
        if len(to_delete):
            confirm = dialogs.ConfirmDeleteDialog(to_delete, parent=None)
            if confirm.exec():
                delete_idx = to_delete.index[confirm.confirmed_delete]
                if len(delete_idx):
                    lock.lockForWrite()
                    rod_data = rod_data.drop(index=delete_idx)
                    lock.unlock()
                    action = lg.PermanentRemoveAction(len(delete_idx))
                    self._logger.add_action(action)
                    # Update rods and tree display
                    worker = pl.Worker(self.extract_seen_information)
                    worker.signals.result.connect(
                        lambda ret: self.seen_loaded.emit(*ret))
                    worker.signals.error.connect(
                        lambda ret: lg.exception_logger(*ret))
                    self.threads.start(worker)

                    self.provide_data()
                else:
                    _logger.info("No rods confirmed for permanent deletion.")
            else:
                # Aborted data cleaning
                return
        else:
            # No unused rods found for deletion
            return

    @staticmethod
    def find_unused_rods() -> pd.DataFrame:
        """Searches for unused rods in the `rod_data` dataset.

        Marks and returns unused rods by verifying that the columns "*_gp*"
        in the dataset contain only 0 or NaN.

        Returns
        -------
        DataFrame
            The rows from the given dataset that were identified as not being
            used.
        """
        global rod_data
        lock.lockForRead()
        to_include = []
        for col in rod_data.columns:
            if re.fullmatch(RE_2D_POS, col):
                to_include.append(col)

        has_nans = rod_data[rod_data.isna().any(axis=1)]
        has_data = has_nans.loc[:, has_nans.columns.isin(to_include)].any(
            axis=1)
        unused = has_nans.loc[has_data == False]                # noqa: E712
        lock.unlock()
        return unused

    @QtCore.pyqtSlot(dict)
    def update_settings(self, settings: dict):
        """Catches updates of the settings from a `Settings` class.

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
        global POSITION_SCALING
        settings_changed = False
        if "position_scaling" in settings and \
                POSITION_SCALING != settings["position_scaling"]:
            settings_changed = True
            POSITION_SCALING = settings["position_scaling"]

        if settings_changed:
            self.provide_data()


def change_data(new_data: dict) -> None:
    """Changes or extends the `rod_data` dataset with the given new data.

    Parameters
    ----------
    new_data : dict
        Dictionary describing the new/changed rod data. Must contain the fields
        ["frame", "cam_id", "color", "position", "rod_id"]
    """
    global rod_data
    lock.lockForWrite()
    frame = new_data["frame"]
    cam_id = new_data["cam_id"]
    color = new_data["color"]
    points = new_data["position"]
    rod_id = new_data["rod_id"]
    seen = new_data["seen"]

    if isinstance(rod_id, Iterable):
        for i in range(len(rod_id)):
            tmp_data = {
                "frame": frame[i],
                "cam_id": cam_id[i],
                "color": color[i],
                "position": points[i],
                "rod_id": rod_id[i],
                "seen": seen[i]
            }
            change_data(tmp_data)
        lock.unlock()
        return

    data_unavailable = rod_data.loc[(rod_data.frame == frame) & (
        rod_data.particle == rod_id) & (rod_data.color == color),
        [f"x1_{cam_id}", f"y1_{cam_id}", f"x2_{cam_id}", f"y2_{cam_id}"]].empty
    if data_unavailable:
        new_idx = rod_data.index.max() + 1
        rod_data.loc[new_idx] = len(rod_data.columns) * [math.nan]
        rod_data.loc[new_idx, [f"x1_{cam_id}", f"y1_{cam_id}",
                               f"x2_{cam_id}", f"y2_{cam_id}", "frame",
                               f"seen_{cam_id}", "particle", "color"]] \
            = [*points, frame, seen, rod_id, color]
    else:
        rod_data.loc[(rod_data.frame == frame) &
                     (rod_data.particle == rod_id) &
                     (rod_data.color == color),
                     [f"x1_{cam_id}", f"y1_{cam_id}",
                     f"x2_{cam_id}", f"y2_{cam_id}", f"seen_{cam_id}"]] = \
            [*points, seen]
    rod_data = rod_data.astype({"frame": 'int', "particle": 'int'})
    lock.unlock()
    return


def rod_number_swap(mode: lg.NumberChangeActions, previous_id: int,
                    new_id: int, color: str, frame: int,
                    cam_id: str = None) -> pd.DataFrame:
    """Change of rod numbers for more than one frame or camera.

    Exchanges rod numbers in more than one frame or camera according to the
    given mode.

    Parameters
    ----------
    mode: NumberChangeActions
        Possible modes are `ALL`, `ALL_ONE_CAM`, and `ONE_BOTH_CAMS`.
    previous_id : int
    new_id : int
    color : str
    frame : int
    cam_id : str, optional
        Default is None.
    """
    global rod_data
    lock.lockForWrite()
    tmp_set = rod_data.copy()
    if mode == lg.NumberChangeActions.ALL:
        rod_data.loc[(tmp_set.color == color) &
                     (tmp_set.particle == previous_id) &
                     (tmp_set.frame >= frame), "particle"] = new_id
        rod_data.loc[(tmp_set.color == color) &
                     (tmp_set.particle == new_id) &
                     (tmp_set.frame >= frame), "particle"] = previous_id
    elif mode == lg.NumberChangeActions.ALL_ONE_CAM:
        cols = rod_data.columns
        mask_previous = (tmp_set.color == color) & \
                        (tmp_set.particle == previous_id) & \
                        (tmp_set.frame >= frame)
        mask_new = (tmp_set.color == color) & \
                   (tmp_set.particle == new_id) & \
                   (tmp_set.frame >= frame)
        cam_cols = [c for c in cols if cam_id in c]
        rod_data.loc[mask_previous, cam_cols] = \
            tmp_set.loc[mask_new, cam_cols].values
        rod_data.loc[mask_new, cam_cols] = \
            tmp_set.loc[mask_previous, cam_cols].values
    elif mode == lg.NumberChangeActions.ONE_BOTH_CAMS:
        rod_data.loc[(tmp_set.color == color) &
                     (tmp_set.particle == previous_id) &
                     (tmp_set.frame == frame), "particle"] = new_id
        rod_data.loc[(tmp_set.color == color) &
                     (tmp_set.particle == new_id) &
                     (tmp_set.frame == frame), "particle"] = previous_id
    else:
        # Unknown mode
        pass
    lock.unlock()
    return
