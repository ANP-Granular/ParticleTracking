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
from typing import List, Tuple

import matplotlib.colors as mpl_colors
import numpy as np
import pandas as pd
from PyQt5 import Qt3DCore, QtCore, QtGui, QtWidgets
from PyQt5.Qt3DExtras import (
    QCuboidMesh,
    QCylinderMesh,
    QExtrudedTextMesh,
    QOrbitCameraController,
    QPhongAlphaMaterial,
    QPhongMaterial,
    Qt3DWindow,
)
from PyQt5.Qt3DRender import QCamera, QDirectionalLight

BOX_WIDTH = 112.0
BOX_HEIGHT = 80.0
BOX_DEPTH = 80.0
ROD_RADIUS = 0.5
_logger = logging.getLogger(__name__)


class View3D(QtWidgets.QWidget):
    """A custom ``QWidget`` for display of 3D rod data.

    Parameters
    ----------
    *args : iterable
        Positional arguments for the ``QWidget`` superclass.
    **kwargs : dict
        Keyword arguments for the ``QWidget`` superclass.


    .. admonition:: Slots

        - :meth:`update_rods`
        - :meth:`update_settings`

    Attributes
    ----------
    view : Qt3DWindow
    camera : QOrbitCameraController
    scene : QEntity
        Root entity for the 3D scene.

    """

    rods: List[Qt3DCore.QEntity] = []
    """List[QEntity] : Entities that resemble a rod each.

    Default is ``[]``.
    """
    _components: List[List[Qt3DCore.QEntity]] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.view = Qt3DWindow()
        self.container = self.createWindowContainer(self.view)

        vboxlayout = QtWidgets.QHBoxLayout()
        vboxlayout.addWidget(self.container)
        self.setLayout(vboxlayout)

        # Create 3D scene
        self.scene = Qt3DCore.QEntity()
        (
            self.box,
            self.top,
            self.top_t,
            self.front,
            self.front_t,
        ) = self.create_box(self.scene)
        self.fences = self.create_fences(self.scene)

        front_light = QDirectionalLight()
        front_light.setWorldDirection(QtGui.QVector3D(0, 0, -1))
        top_light = QDirectionalLight()
        top_light.setWorldDirection(QtGui.QVector3D(0, -1, 0))
        right_light = QDirectionalLight()
        right_light.setWorldDirection(QtGui.QVector3D(1, 0, 0))
        left_light = QDirectionalLight()
        left_light.setWorldDirection(QtGui.QVector3D(-1, 0, 0))
        back_light = QDirectionalLight()
        back_light.setWorldDirection(QtGui.QVector3D(0, 0, 1))
        bottom_light = QDirectionalLight()
        bottom_light.setWorldDirection(QtGui.QVector3D(0, 1, 0))

        self.scene.addComponent(front_light)
        self.scene.addComponent(top_light)
        self.scene.addComponent(right_light)
        self.scene.addComponent(left_light)
        self.scene.addComponent(back_light)
        self.scene.addComponent(bottom_light)

        # Camera
        self.camera = self.init_camera(self.view, self.scene)
        self.view.setRootEntity(self.scene)

    def show_front(self):
        """Move the camera to display the front for the experiment box."""
        self.camera.setViewCenter(QtGui.QVector3D(0.0, 0.0, 0.0))
        self.camera.setPosition(QtGui.QVector3D(0.0, 0.0, 1.5 * BOX_WIDTH))
        self.camera.setUpVector(QtGui.QVector3D(0.0, 1.0, 0.0))

    def show_top(self):
        """Move the camera to display the top for the experiment box."""
        self.camera.setViewCenter(QtGui.QVector3D(0.0, 0.0, 0.0))
        self.camera.setPosition(QtGui.QVector3D(0.0, 1.5 * BOX_WIDTH, 0.0))
        self.camera.setUpVector(QtGui.QVector3D(0.0, 0.0, -1.0))

    @QtCore.pyqtSlot(pd.DataFrame)
    def update_rods(self, data: pd.DataFrame) -> None:
        """Updates the displayed 3D rods.

        Parameters
        ----------
        data : DataFrame
            3D position data of one frame. Required columns:\n
            ``"x1"``, ``"x2"``, ``"y1"``, ``"y2"``, ``"z1"``, ``"z2"``,
            ``"color"``
        """
        if not len(data):
            self.clear()
            return
        available_rods = len(self.rods)
        i = 0
        for color in data.color.unique():
            c_data = data.loc[data.color == color]
            try:
                rod_color = QtGui.QColor.fromRgbF(
                    *mpl_colors.to_rgba(color, alpha=1.0)
                )
            except ValueError as e:
                _logger.warning(
                    f"Unknown color for 3D display!\n{e.args}\n"
                    f"Using 'pink' instead."
                )
                rod_color = QtGui.QColor.fromRgbF(
                    *mpl_colors.to_rgba("pink", alpha=1.0)
                )
            xs = c_data[["x1", "x2"]].to_numpy()
            ys = c_data[["y1", "y2"]].to_numpy()
            zs = c_data[["z1", "z2"]].to_numpy()
            dxs = np.diff(xs, axis=1).squeeze(axis=1)
            dys = np.diff(ys, axis=1).squeeze(axis=1)
            dzs = np.diff(zs, axis=1).squeeze(axis=1)
            k = 0
            for idx in range(len(c_data)):
                if i + k < available_rods:
                    try:
                        rod = self.rods[i + k]
                        cm_rod, transformation, material = self._components[
                            i + k
                        ]
                        cm_rod.setRadius(ROD_RADIUS)
                        cm_rod.setLength(
                            np.linalg.norm(
                                np.array((dxs[idx], dys[idx], dzs[idx]))
                            )
                        )
                        new_pos = QtGui.QVector3D(
                            xs[idx, 0] + dxs[idx] / 2,
                            ys[idx, 0] + dys[idx] / 2,
                            zs[idx, 0] + dzs[idx] / 2,
                        )
                        transformation.setTranslation(new_pos)
                        rod_rot = QtGui.QQuaternion.rotationTo(
                            QtGui.QVector3D(0.0, 1.0, 0.0),
                            QtGui.QVector3D(dxs[idx], dys[idx], dzs[idx]),
                        )
                        transformation.setRotation(rod_rot)
                        material.setDiffuse(rod_color)
                        k += 1
                        continue
                    except RuntimeError as e:
                        if "wrapped C/C++ object" not in e.args[0]:
                            raise e
                cm_rod = QCylinderMesh()
                transformation = Qt3DCore.QTransform()
                material = QPhongMaterial(self.scene)
                rod = Qt3DCore.QEntity(self.scene)

                cm_rod.setRadius(ROD_RADIUS)
                material.setDiffuse(rod_color)
                cm_rod.setLength(
                    np.linalg.norm(np.array((dxs[idx], dys[idx], dzs[idx])))
                )
                new_pos = QtGui.QVector3D(
                    xs[idx, 0] + dxs[idx] / 2,
                    ys[idx, 0] + dys[idx] / 2,
                    zs[idx, 0] + dzs[idx] / 2,
                )
                transformation.setTranslation(new_pos)
                rod_rot = QtGui.QQuaternion.rotationTo(
                    QtGui.QVector3D(0.0, 1.0, 0.0),
                    QtGui.QVector3D(dxs[idx], dys[idx], dzs[idx]),
                )
                transformation.setRotation(rod_rot)

                rod.addComponent(cm_rod)
                rod.addComponent(transformation)
                rod.addComponent(material)
                self._components.append([cm_rod, transformation, material])
                rod.setEnabled(True)
                self.rods.append(rod)
                k += 1
            i += len(c_data)

    @staticmethod
    def init_camera(view: Qt3DWindow, scene: Qt3DCore.QEntity) -> QCamera:
        """Initilizes the 3D view camera and camera controller.

        Parameters
        ----------
        view : Qt3DWindow
        scene : Qt3DCore.QEntity
            Root entity for the whole displayed 3D scene.

        Returns
        -------
        QCamera
        """
        # Camera
        camera = view.camera()
        camera.lens().setPerspectiveProjection(45.0, 16.0 / 9.0, 0.1, 1000.0)
        camera.setPosition(
            QtGui.QVector3D(0.0, 1.5 * BOX_HEIGHT, 1.5 * BOX_DEPTH)
        )
        camera.setViewCenter(QtGui.QVector3D(0.0, 0.0, 0.0))

        # Camera controls
        camController = QOrbitCameraController(scene)
        camController.setLinearSpeed(250.0)
        camController.setLookSpeed(180.0)
        camController.setCamera(camera)
        return camera

    @staticmethod
    def create_box(
        root: Qt3DCore.QEntity,
    ) -> Tuple[
        QCuboidMesh,
        QExtrudedTextMesh,
        Qt3DCore.QTransform,
        QExtrudedTextMesh,
        Qt3DCore.QTransform,
    ]:
        """Creates a shaded box as the representation of the experiment
        container.

        The container and the descriptive text meshes and transformations are
        returned for later adjustment of dimensions, e.g. during settings
        changes.

        Parameters
        ----------
        root : Qt3DCore.QEntity
            Root entity for the whole displayed 3D scene.

        Returns
        -------
        Tuple[QCuboidMesh, QExtrudedTextMesh, Qt3DCore.QTransform,
              QExtrudedTextMesh, Qt3DCore.QTransform]
            Returns the box mesh, the top text mesh, the top text
            transformation, the front text mesh, and the front text
            transformation.
        """
        material = QPhongMaterial(root)

        # Experiment container
        ex_cont_ent = Qt3DCore.QEntity(root)
        exp_cont = QCuboidMesh(ex_cont_ent)
        exp_cont.setXExtent(BOX_WIDTH)
        exp_cont.setYExtent(BOX_HEIGHT)
        exp_cont.setZExtent(BOX_DEPTH)
        exp_mat = QPhongAlphaMaterial(ex_cont_ent)
        exp_mat.setAlpha(0.4)
        ex_cont_ent.addComponent(exp_cont)
        ex_cont_ent.addComponent(exp_mat)

        # Adding indicative text
        top_txt = QExtrudedTextMesh()
        top_txt.setText("TOP")
        top_txt.setDepth(0.1)
        ind_font = top_txt.font()
        ind_font.setPixelSize(int(BOX_WIDTH / 10))
        ind_metric = QtGui.QFontMetrics(ind_font)
        top_txt.setFont(ind_font)

        top_transform = Qt3DCore.QTransform()
        top_transform.setTranslation(
            QtGui.QVector3D(-BOX_WIDTH / 2, BOX_HEIGHT / 2, -BOX_DEPTH / 2)
        )
        q1 = QtGui.QQuaternion.fromAxisAndAngle(
            QtGui.QVector3D(0.0, 1.0, 0.0), 180.0
        )
        q2 = QtGui.QQuaternion.fromAxisAndAngle(
            QtGui.QVector3D(1.0, 0.0, 0.0), -90.0
        )
        top_transform.setRotation(q1 * q2)

        text_obj = Qt3DCore.QEntity(root)
        text_obj.addComponent(top_txt)
        text_obj.addComponent(top_transform)
        text_obj.addComponent(material)

        front_txt = QExtrudedTextMesh()
        front_txt.setText("FRONT")
        front_txt.setDepth(0.1)
        front_txt.setFont(ind_font)
        front_transform = Qt3DCore.QTransform()
        front_transform.setTranslation(
            QtGui.QVector3D(
                (-BOX_WIDTH / 2),
                (-BOX_HEIGHT / 2) - ind_metric.capHeight(),
                BOX_DEPTH / 2,
            )
        )
        q_front = QtGui.QQuaternion.fromAxisAndAngle(
            QtGui.QVector3D(0.0, 0.0, 1.0), 180.0
        )
        front_transform.setRotation(q_front)
        front_obj = Qt3DCore.QEntity(root)
        front_obj.addComponent(front_txt)
        front_obj.addComponent(front_transform)
        front_obj.addComponent(material)

        return exp_cont, top_txt, top_transform, front_txt, front_transform

    def update_box(self):
        """Update the experiment containers displayed dimensions."""
        tmp_font = self.front.font()
        tmp_font.setPixelSize(int(BOX_WIDTH / 10))
        tmp_metric = QtGui.QFontMetrics(tmp_font)

        self.front.setFont(tmp_font)
        self.top.setFont(tmp_font)

        self.front_t.setTranslation(
            QtGui.QVector3D(
                (-BOX_WIDTH / 2),
                (-BOX_HEIGHT / 2) - tmp_metric.capHeight(),
                BOX_DEPTH / 2,
            )
        )
        self.top_t.setTranslation(
            QtGui.QVector3D(-BOX_WIDTH / 2, BOX_HEIGHT / 2, -BOX_DEPTH / 2)
        )

        self.box.setXExtent(BOX_WIDTH)
        self.box.setYExtent(BOX_HEIGHT)
        self.box.setZExtent(BOX_DEPTH)
        for bar in self.fences:
            bar.setEnabled(False)
        self.fences = self.create_fences(self.scene)

    @staticmethod
    def create_fences(root: Qt3DCore.QEntity) -> List[Qt3DCore.QEntity]:
        """Create bars that act as visual indicators for the edges of the
        experiment container.

        Parameters
        ----------
        root : Qt3DCore.QEntity
            Root entity for the whole displayed 3D scene.

        Returns
        -------
        List[Qt3DCore.QEntity]
            List of bars.
        """
        material = QPhongMaterial(root)

        fences = [Qt3DCore.QEntity(root) for i in range(12)]

        off_set = QtGui.QVector3D(-BOX_WIDTH / 2, 0, BOX_DEPTH / 2)
        lens = [
            BOX_HEIGHT,
            BOX_HEIGHT,
            BOX_HEIGHT,
            BOX_HEIGHT,
            BOX_DEPTH,
            BOX_DEPTH,
            BOX_WIDTH,
            BOX_WIDTH,
            BOX_DEPTH,
            BOX_DEPTH,
            BOX_WIDTH,
            BOX_WIDTH,
        ]
        positions = [
            QtGui.QVector3D(0, 0, 0),
            QtGui.QVector3D(BOX_WIDTH, 0, 0),
            QtGui.QVector3D(BOX_WIDTH, 0, -BOX_DEPTH),
            QtGui.QVector3D(0, 0, -BOX_DEPTH),
            QtGui.QVector3D(0, -BOX_HEIGHT / 2, -BOX_DEPTH / 2),
            QtGui.QVector3D(BOX_WIDTH, -BOX_HEIGHT / 2, -BOX_DEPTH / 2),
            QtGui.QVector3D(BOX_WIDTH / 2, -BOX_HEIGHT / 2, 0),
            QtGui.QVector3D(BOX_WIDTH / 2, -BOX_HEIGHT / 2, -BOX_DEPTH),
            QtGui.QVector3D(0, BOX_HEIGHT / 2, -BOX_DEPTH / 2),
            QtGui.QVector3D(BOX_WIDTH, BOX_HEIGHT / 2, -BOX_DEPTH / 2),
            QtGui.QVector3D(BOX_WIDTH / 2, BOX_HEIGHT / 2, 0),
            QtGui.QVector3D(BOX_WIDTH / 2, BOX_HEIGHT / 2, -BOX_DEPTH),
        ]
        rotations = [
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 0.0), 0.0
            ),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 0.0), 0.0
            ),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 0.0), 0.0
            ),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 0.0), 0.0
            ),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(1.0, 0.0, 0.0), 90.0
            ),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(1.0, 0.0, 0.0), 90.0
            ),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 1.0), 90.0
            ),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 1.0), 90.0
            ),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(1.0, 0.0, 0.0), 90.0
            ),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(1.0, 0.0, 0.0), 90.0
            ),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 1.0), 90.0
            ),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 1.0), 90.0
            ),
        ]

        for i in range(12):
            cm_tmp = QCylinderMesh()
            cm_tmp.setRadius(0.1)
            cm_tmp.setLength(lens[i])

            bar_transform = Qt3DCore.QTransform()
            bar_transform.setTranslation(positions[i] + off_set)
            bar_transform.setRotation(rotations[i])
            fences[i].addComponent(cm_tmp)
            fences[i].addComponent(bar_transform)
            fences[i].addComponent(material)
        return fences

    @staticmethod
    def create_walls(root: Qt3DCore.QEntity):
        """Create walls for the experimental container, except top and front.

        Parameters
        ----------
        root : Qt3DCore.QEntity
            Root entity for the whole displayed 3D scene.
        """
        material = QPhongMaterial(root)
        cm_plate = QCuboidMesh()
        cm_plate.setXExtent(BOX_WIDTH)
        cm_plate.setYExtent(0.01)
        cm_plate.setZExtent(BOX_HEIGHT)
        plate_positions = [
            QtGui.QVector3D(0, -BOX_HEIGHT / 2, 0),
            QtGui.QVector3D(-BOX_WIDTH / 2, 0, 0),
            QtGui.QVector3D(BOX_WIDTH / 2, 0, 0),
            QtGui.QVector3D(0, 0, -BOX_HEIGHT / 2),
        ]
        plate_rotations = [
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 0.0), 0.0
            ),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 1.0), 90.0
            ),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 1.0), 90.0
            ),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(1.0, 0.0, 0.0), 90.0
            ),
        ]
        for i in range(4):
            plate_transform = Qt3DCore.QTransform()
            plate_transform.setTranslation(plate_positions[i])
            plate_transform.setRotation(plate_rotations[i])
            plate = Qt3DCore.QEntity(root)
            plate.addComponent(cm_plate)
            plate.addComponent(plate_transform)
            plate.addComponent(material)

    @QtCore.pyqtSlot(dict)
    def update_settings(self, settings: dict):
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
        global BOX_WIDTH, BOX_HEIGHT, BOX_DEPTH
        settings_changed = False
        if "box_width" in settings and BOX_WIDTH != settings["box_width"]:
            settings_changed = True
            BOX_WIDTH = settings["box_width"]
        if "box_height" in settings and BOX_HEIGHT != settings["box_height"]:
            settings_changed = True
            BOX_HEIGHT = settings["box_height"]
        if "box_depth" in settings and BOX_DEPTH != settings["box_depth"]:
            settings_changed = True
            BOX_DEPTH = settings["box_depth"]

        if settings_changed:
            self.update_box()

    def clear(self):
        """Discard all currently loaded rods."""
        for rod in self.rods:
            try:
                rod.setParent(None)
            except RuntimeError as e:
                if "wrapped C/C++ object" not in e.args[0]:
                    raise e
        self.rods = []
        self._components = []
