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
from PyQt5 import QtCore, QtWidgets


class RodTree(QtWidgets.QTreeWidget):
    """A custom QTreeWidget to display all loaded rods as a tree.

    Parameters
    ----------
    *args
    **kwargs

    Attributes
    ----------
    rod_info : None | Dict[Dict[Dict[list]]]
        Holds the loaded information of the rod dataset about a rod being
        'seen' or 'unseen'.
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.rod_info = None

    @QtCore.pyqtSlot(object)
    def setup_tree(self, inputs):
        """Handles the setup of the treeview from extracted rod data."""
        assert len(inputs) == 2
        rod_info, columns = inputs[:]
        assert type(columns) is list
        assert type(rod_info) is dict

        self.rod_info = rod_info
        self.clear()
        self.setColumnCount(len(columns) + 1)
        headers = [self.headerItem().text(0), *columns]
        self.setHeaderLabels(headers)
        self.generate_tree()
        self.update_tree_folding()

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
                    current_particle = QtWidgets.QTreeWidgetItem(
                        current_color)
                    current_particle.setText(
                        0, f"Rod{particle:3d}: "
                    )
                    for idx, gp in enumerate(
                            self.rod_info[frame][color][particle]):
                        current_particle.setText(idx + 1, gp)
                current_color.sortChildren(0, QtCore.Qt.AscendingOrder)
            current_frame.sortChildren(0, QtCore.Qt.AscendingOrder)
        self.update_tree_folding()

    def update_tree(self, new_data: dict, no_gen=False):
        """Update the "seen" status in the displayed rod data tree.
        Skip updating of the tree by using no_gen=True."""
        header = self.headerItem()
        headings = []
        for i in range(1, header.columnCount()):
            headings.append(header.text(i))
        insert_idx = headings.index(new_data["cam_id"])
        self.rod_info[new_data["frame"]][new_data["color"]][new_data[
            "rod_id"]][insert_idx] = "seen" if new_data["seen"] else "unseen"
        if no_gen:
            return
        self.generate_tree()

    def update_tree_folding(self, frame: int, color: str):
        """Updates the folding of the tree view.

        The tree view is updated in synchrony with the UI switching frames
        and colors. The corresponding portion of the tree is expanded and
        moved into view.
        """
        self.collapseAll()
        root = self.invisibleRootItem()
        frames = [int(root.child(i).text(0)[7:])
                  for i in range(root.childCount())]
        try:
            expand_frame = root.child(frames.index(frame))
        except ValueError:
            # frame not found in list -> unable to update the list
            return
        colors = [expand_frame.child(i).text(0)
                  for i in range(expand_frame.childCount())]

        try:
            to_expand = colors.index(color)
        except ValueError:
            to_expand = 0
        expand_color = expand_frame.child(to_expand)

        self.expandItem(expand_frame)
        self.expandItem(expand_color)
        self.scrollToItem(expand_frame,
                          QtWidgets.QAbstractItemView.PositionAtTop)
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
