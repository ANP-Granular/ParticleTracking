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
from PyQt5 import QtCore, QtWidgets


class RodTree(QtWidgets.QTreeWidget):
    """A custom ``QTreeWidget`` to display all loaded rods as a tree.

    Parameters
    ----------
    *args : iterable
        Positional arguments for the ``QTreeWidget`` superclass.
    **kwargs : dict
        Keyword arguments for the ``QTreeWidget`` superclass.

    Attributes
    ----------
    rod_info : None | Dict[Dict[Dict[list]]]
        Holds the loaded information of the rod dataset about a rod being
        ``'seen'`` or ``'unseen'``.\n
        Dimensions: ``(frame, color, particle, camera)``


    .. admonition:: Signals

        - :attr:`data_loaded`
    """

    data_loaded = QtCore.pyqtSignal(name="data_loaded")
    """Indicates the successful generation of the tree."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.rod_info = None

    @QtCore.pyqtSlot(dict, list)
    def setup_tree(self, rod_info: dict, columns: list):
        """Handles the setup of the treeview from extracted rod data.

        Accepts a new ``rod_info`` dataset and (re-)sets the tree display of
        it.

        Parameters
        ----------
        rod_info : Dict[Dict[Dict[list]]]
            Information of the rod dataset about a rod being ``'seen'`` or
            ``'unseen'``.\n
            Dimensions: ``(frame, color, particle, camera)``
        columns : list
            List of *camera* IDs on which a rod can be ``'seen'``/``'unseen'``.
        """
        self.rod_info = rod_info
        self.clear()
        self.setColumnCount(len(columns) + 1)
        headers = [self.headerItem().text(0), *columns]
        self.setHeaderLabels(headers)
        self.generate_tree()
        self.data_loaded.emit()

    def generate_tree(self):
        """(Re)generates the tree for display of loaded rod data."""
        self.clear()
        for frame in self.rod_info.keys():
            current_frame = QtWidgets.QTreeWidgetItem(self)
            current_frame.setText(0, f"Frame: {frame}")
            for color in self.rod_info[frame].keys():
                current_color = QtWidgets.QTreeWidgetItem(current_frame)
                current_color.setText(0, color)
                for particle in self.rod_info[frame][color].keys():
                    current_particle = QtWidgets.QTreeWidgetItem(current_color)
                    current_particle.setText(0, f"Rod{particle:3d}: ")
                    for idx, gp in enumerate(
                        self.rod_info[frame][color][particle]
                    ):
                        current_particle.setText(idx + 1, gp)
                current_color.sortChildren(0, QtCore.Qt.AscendingOrder)
            current_frame.sortChildren(0, QtCore.Qt.AscendingOrder)

    @QtCore.pyqtSlot(dict)
    def update_tree(self, new_data: dict):
        """Update the *seen* status in the rod data tree.

        Parameters
        ----------
        new_data : dict
            Information about the rod, whos *seen* status has changed.
            Mandatory keys:\n
            ``"frame"``, ``"cam_id"``, ``"color"``, ``"seen"``, ``"rod_id"``
        """
        header = self.headerItem()
        headings = []
        for i in range(1, header.columnCount()):
            headings.append(header.text(i))
        insert_idx = headings.index(new_data["cam_id"])
        try:
            self.rod_info[new_data["frame"]][new_data["color"]][
                new_data["rod_id"]
            ][insert_idx] = ("seen" if new_data["seen"] else "unseen")
        except KeyError:
            self.new_rod(
                new_data["frame"], new_data["color"], new_data["rod_id"]
            )
            self.rod_info[new_data["frame"]][new_data["color"]][
                new_data["rod_id"]
            ][insert_idx] = ("seen" if new_data["seen"] else "unseen")

        # Update visual elements
        f_it = self.findItems(
            str(new_data["frame"]), QtCore.Qt.MatchFlag.MatchEndsWith
        )[0]
        for i in range(f_it.childCount()):
            color = f_it.child(i)
            if new_data["color"] in color.text(0):
                particle_updated = False
                for k in range(color.childCount()):
                    rod = color.child(k)
                    if f"Rod{new_data['rod_id']:3d}:" in rod.text(0):
                        rod.setText(
                            insert_idx + 1,
                            ("seen" if new_data["seen"] else "unseen"),
                        )
                        particle_updated = True
                        break
                if not particle_updated:
                    # Add new particle as row
                    new_particle = QtWidgets.QTreeWidgetItem(color)
                    new_particle.setText(0, f"Rod{new_data['rod_id']:3d}: ")
                    for idx, gp in enumerate(
                        self.rod_info[new_data["frame"]][new_data["color"]][
                            new_data["rod_id"]
                        ]
                    ):
                        new_particle.setText(idx + 1, gp)
                    color.sortChildren(0, QtCore.Qt.AscendingOrder)
                    new_particle.setSelected(True)
                break

    def batch_update_tree(self, new_data: dict, cam_ids: list):
        """Updates the displayed tree with multiple changed or new particles.

        Unlike :meth:`update_tree` this method is capable of updating multiple
        particles in a previously setup tree, this includes previously not
        existing particles.

        Parameters
        ----------
        new_data : Dict[int, Dict[str, Dict[int, list]]]
            Information of the rod dataset about a rod being ``'seen'`` or
            ``'unseen'``.\n
            Dimensions: ``(frame, color, particle, camera)``
        cam_ids : list
            List of *camera* IDs on which a rod can be ``'seen'``/``'unseen'``.

        See also
        --------
        :meth:`.extract_seen_information`, :meth:`update_tree`
        """
        header = self.headerItem()
        headings = []
        for i in range(1, header.columnCount()):
            headings.append(header.text(i))
        insert_idx = headings.index(cam_ids[0])
        for frame in new_data.keys():
            try:
                current_frame = self.findItems(
                    str(frame), QtCore.Qt.MatchFlag.MatchEndsWith
                )[0]
            except IndexError:
                current_frame = QtWidgets.QTreeWidgetItem(self)
                current_frame.setText(0, f"Frame: {frame}")
                self.rod_info[frame] = {}
            for color in new_data[frame].keys():
                current_color = None
                for c_idx in range(current_frame.childCount()):
                    c_child = current_frame.child(c_idx)
                    if c_child.text(0) == color:
                        current_color = c_child
                if current_color is None:
                    current_color = QtWidgets.QTreeWidgetItem(current_frame)
                    current_color.setText(0, color)
                    self.rod_info[frame][color] = {}
                for particle in new_data[frame][color].keys():
                    current_particle = None
                    for p_idx in range(current_color.childCount()):
                        p_child = current_color.child(p_idx)
                        if p_child.text(0) == f"Rod{particle:3d}: ":
                            current_particle = p_child
                    if current_particle is None:
                        current_particle = QtWidgets.QTreeWidgetItem(
                            current_color
                        )
                        current_particle.setText(0, f"Rod{particle:3d}: ")
                        self.rod_info[frame][color][particle] = len(
                            headings
                        ) * ["unseen"]
                    current_particle.setText(
                        insert_idx + 1, new_data[frame][color][particle][0]
                    )

    def update_tree_folding(self, frame: int, color: str):
        """Updates the folding of the tree view.

        The tree view is updated in synchrony with the UI switching frames
        and colors. The corresponding portion of the tree is expanded and
        moved into view.

        Parameters
        ----------
        frame : int
        color : str
        """
        self.collapseAll()
        root = self.invisibleRootItem()
        frames = [
            int(root.child(i).text(0)[7:]) for i in range(root.childCount())
        ]
        try:
            expand_frame = root.child(frames.index(frame))
        except ValueError:
            # Frame not found in list -> unable to update the list
            return
        colors = [
            expand_frame.child(i).text(0)
            for i in range(expand_frame.childCount())
        ]

        try:
            to_expand = colors.index(color)
        except ValueError:
            to_expand = 0
        expand_color = expand_frame.child(to_expand)

        self.expandItem(expand_frame)
        self.expandItem(expand_color)
        self.scrollToItem(
            expand_frame, QtWidgets.QAbstractItemView.PositionAtTop
        )
        return

    def new_rod(self, frame: int, color: str, rod_number: int):
        """Insert a new rod into the loaded dataset.

        Parameters
        ----------
        frame : int
        color : str
        rod_number : int
        """
        if self.rod_info is None:
            return
        self.rod_info[frame][color][rod_number] = ["unseen", "unseen"]
