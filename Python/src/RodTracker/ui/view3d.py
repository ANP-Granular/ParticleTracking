from typing import List, Tuple
from enum import Enum
import numpy as np
import matplotlib.colors as mpl_colors
from PyQt5 import Qt3DCore, QtCore, QtWidgets, QtGui
from PyQt5.Qt3DRender import QDirectionalLight, QCamera
from PyQt5.Qt3DExtras import QPhongMaterial, \
    QCylinderMesh, Qt3DWindow, QOrbitCameraController, QCuboidMesh, \
    QExtrudedTextMesh, QPhongAlphaMaterial
import RodTracker.backend.data_operations as d_ops


class DisplayModes3D(Enum):
    ALL = 1
    COLOR = 2
    ONE = 3


POSITION_SCALING = 1.
BOX_WIDTH = 112.
BOX_HEIGHT = 80.
BOX_DEPTH = 80.
ROD_RADIUS = 0.5


class View3D(QtWidgets.QWidget):
    rods: List[Qt3DCore.QEntity] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.threads = QtCore.QThreadPool()
        self.view = Qt3DWindow()
        self.container = self.createWindowContainer(self.view)

        vboxlayout = QtWidgets.QHBoxLayout()
        vboxlayout.addWidget(self.container)
        self.setLayout(vboxlayout)

        # Create 3D scene
        self.scene = Qt3DCore.QEntity()
        self.box, self.top, self.top_t, self.front, self.front_t = \
            self.create_box(self.scene)
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

        # Controls
        self.current_frame = None
        self.current_rod = None
        self.show_3d = False
        self.current_color = None
        self.mode = DisplayModes3D.ALL
        self.mode_group = QtWidgets.QButtonGroup()
        self.mode_group.setExclusive(True)
        self.mode_group.buttonToggled.connect(self.mode_changed)

    def set_mode_group(self, *mode_btns: QtWidgets.QRadioButton):
        """Initializes the buttons group for selection of display mode."""
        for old_btn in self.mode_group.buttons():
            self.mode_group.removeButton(old_btn)
        for btn in mode_btns:
            self.mode_group.addButton(btn)
            self.mode_changed(btn, btn.isChecked())

    @QtCore.pyqtSlot(str)
    def rod_changed(self, number: str):
        """Handles a change in rod number for single rod display.

        Parameters
        ----------
        number : str
        """
        self.current_rod = int(number)
        self.clear()
        self.update_rods(self.current_frame)

    def mode_changed(self, btn: QtWidgets.QRadioButton, state: bool):
        if not state:
            return
        if "all" in btn.objectName():
            self.mode = DisplayModes3D.ALL
        elif "color" in btn.objectName():
            self.mode = DisplayModes3D.COLOR
        elif "one" in btn.objectName():
            self.mode = DisplayModes3D.ONE
        else:
            raise ValueError("Unknown 3D mode button.")
        self.clear()
        self.update_rods(self.current_frame)

    def show_front(self):
        """Move the camera to display the front for the experiment box."""
        self.camera.setViewCenter(
            QtGui.QVector3D(0.0, 0.0, 0.0)
        )
        self.camera.setPosition(
            QtGui.QVector3D(0.0, 0.0, 1.5 * BOX_WIDTH)
        )
        self.camera.setUpVector(
            QtGui.QVector3D(0.0, 1.0, 0.0)
        )

    def show_top(self):
        """Move the camera to display the top for the experiment box."""
        self.camera.setViewCenter(
            QtGui.QVector3D(0.0, 0.0, 0.0)
        )
        self.camera.setPosition(
            QtGui.QVector3D(0.0, 1.5 * BOX_WIDTH, 0.0)
        )
        self.camera.setUpVector(
            QtGui.QVector3D(0.0, 0.0, -1.0)
        )

    @QtCore.pyqtSlot(int)
    def update_rods(self, frame: int) -> None:
        """Updates the displayed rods.

        Which rods are eventually displayed depends on the `mode` selected
        during call time of this function.

        Parameters
        ----------
        frame : int
            Frame number that shall be displayed.
        """
        self.current_frame = frame
        if frame is None or not self.show_3d:
            return

        with QtCore.QReadLocker(d_ops.lock):
            if d_ops.rod_data is None:
                return
            disp_data = d_ops.rod_data.loc[d_ops.rod_data.frame == frame]
        if not len(disp_data):
            self.clear()
            return
        available_rods = len(self.rods)
        i = 0
        cm_rod = QCylinderMesh()
        cm_rod.setRadius(ROD_RADIUS)
        for color in disp_data.color.unique():
            if (self.mode == DisplayModes3D.COLOR or
                self.mode == DisplayModes3D.ONE) and\
                    color != self.current_color:
                continue
            data = disp_data.loc[disp_data.color == color]
            rod_color = mpl_colors.to_rgba(color, alpha=1.0)
            material = QPhongMaterial(self.scene)
            material.setDiffuse(QtGui.QColor.fromRgbF(*rod_color))
            xs = data[["x1", "x2"]].to_numpy() * POSITION_SCALING
            ys = data[["y1", "y2"]].to_numpy() * POSITION_SCALING
            zs = data[["z1", "z2"]].to_numpy() * POSITION_SCALING
            dxs = np.diff(xs, axis=1)
            dys = np.diff(ys, axis=1)
            dzs = np.diff(zs, axis=1)
            k = 0
            for idx in range(len(data)):
                if self.mode == DisplayModes3D.ONE and \
                        self.current_rod != data.particle.iloc[idx]:
                    continue
                if i + k >= available_rods:
                    self.rods.append(Qt3DCore.QEntity(self.scene))
                rod = self.rods[i + k]
                rod.setEnabled(True)
                cm_rod.setLength(
                    np.linalg.norm(np.array((dxs[idx], dys[idx], dzs[idx]))))
                transformation = Qt3DCore.QTransform()
                new_pos = QtGui.QVector3D(xs[idx, 0] + dxs[idx] / 2,
                                          ys[idx, 0] + dys[idx] / 2,
                                          zs[idx, 0] + dzs[idx] / 2)
                transformation.setTranslation(new_pos)
                rod_rot = QtGui.QQuaternion.rotationTo(
                    QtGui.QVector3D(0., 1., 0.),
                    QtGui.QVector3D(dxs[idx], dys[idx], dzs[idx]))
                transformation.setRotation(rod_rot)
                rod.addComponent(cm_rod)
                rod.addComponent(transformation)
                rod.addComponent(material)
                k += 1
            i += len(data)

    @QtCore.pyqtSlot(object)
    def integrate_rods(
            self, rods_components: List[List[Qt3DCore.QComponent]]) -> None:
        rods = []
        for components in rods_components:
            new_rod = Qt3DCore.QEntity(self.scene)
            new_rod.addComponent(components[0])
            new_rod.addComponent(components[1])
            new_rod.addComponent(components[2])
            rods.append(new_rod)
        self.rods = rods

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
        camera.setPosition(QtGui.QVector3D(0.0, 1.5 * BOX_HEIGHT,
                                           1.5 * BOX_DEPTH))
        camera.setViewCenter(QtGui.QVector3D(0.0, 0.0, 0.0))

        # Camera controls
        camController = QOrbitCameraController(scene)
        camController.setLinearSpeed(250.0)
        camController.setLookSpeed(180.0)
        camController.setCamera(camera)
        return camera

    @staticmethod
    def create_box(root: Qt3DCore.QEntity) ->\
        Tuple[QCuboidMesh, QExtrudedTextMesh, Qt3DCore.QTransform,
              QExtrudedTextMesh, Qt3DCore.QTransform]:
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
        top_txt.setDepth(.1)
        ind_font = top_txt.font()
        ind_font.setPixelSize(int(BOX_WIDTH / 10))
        ind_metric = QtGui.QFontMetrics(ind_font)
        top_txt.setFont(ind_font)

        top_transform = Qt3DCore.QTransform()
        top_transform.setTranslation(
            QtGui.QVector3D(-BOX_WIDTH / 2, BOX_HEIGHT / 2, -BOX_DEPTH / 2))
        q1 = QtGui.QQuaternion.fromAxisAndAngle(
            QtGui.QVector3D(0.0, 1.0, 0.0), 180.0)
        q2 = QtGui.QQuaternion.fromAxisAndAngle(
            QtGui.QVector3D(1.0, 0.0, 0.0), -90.0)
        top_transform.setRotation(q1 * q2)

        text_obj = Qt3DCore.QEntity(root)
        text_obj.addComponent(top_txt)
        text_obj.addComponent(top_transform)
        text_obj.addComponent(material)

        front_txt = QExtrudedTextMesh()
        front_txt.setText("FRONT")
        front_txt.setDepth(.1)
        front_txt.setFont(ind_font)
        front_transform = Qt3DCore.QTransform()
        front_transform.setTranslation(
            QtGui.QVector3D(
                (-BOX_WIDTH / 2), (-BOX_HEIGHT / 2) - ind_metric.capHeight(),
                BOX_DEPTH / 2))
        q_front = QtGui.QQuaternion.fromAxisAndAngle(
            QtGui.QVector3D(0.0, 0.0, 1.0), 180.0)
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
                (-BOX_WIDTH / 2), (-BOX_HEIGHT / 2) - tmp_metric.capHeight(),
                BOX_DEPTH / 2)
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
            QtGui.QVector3D(BOX_WIDTH / 2, BOX_HEIGHT / 2, -BOX_DEPTH)
        ]
        rotations = [
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 0.0), 0.0),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 0.0), 0.0),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 0.0), 0.0),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 0.0), 0.0),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(1.0, 0.0, 0.0), 90.0),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(1.0, 0.0, 0.0), 90.0),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 1.0), 90.0),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 1.0), 90.0),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(1.0, 0.0, 0.0), 90.0),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(1.0, 0.0, 0.0), 90.0),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 1.0), 90.0),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 1.0), 90.0)
        ]

        cm_tmp = QCylinderMesh()
        cm_tmp.setRadius(0.1)
        cm_tmp.setLength(1.1 * np.max((BOX_WIDTH, BOX_HEIGHT, BOX_DEPTH)))
        for i in range(12):
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
            QtGui.QVector3D(0, 0, -BOX_HEIGHT / 2)
        ]
        plate_rotations = [
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 0.0), 0.0),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 1.0), 90.0),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(0.0, 0.0, 1.0), 90.0),
            QtGui.QQuaternion.fromAxisAndAngle(
                QtGui.QVector3D(1.0, 0.0, 0.0), 90.0)
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
        global BOX_WIDTH, BOX_HEIGHT, BOX_DEPTH, POSITION_SCALING
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
        if "position_scaling" in settings and \
                POSITION_SCALING != settings["position_scaling"]:
            settings_changed = True
            POSITION_SCALING = settings["position_scaling"]

        if settings_changed:
            self.update_box()
            self.update_rods(self.current_frame)

    def toggle_display(self, state: int):
        """Update whether to display particles in the 3D view.

        Parameters
        ----------
        state : int
            0   ->  Do not show particles.
            !=0 ->  Show particles.
        """
        self.show_3d = bool(state)
        if not self.show_3d:
            self.clear()
        self.update_rods(self.current_frame)

    def update_color(self, color: str):
        """Updates the color for displaying particles.

        Parameters
        ----------
        color : str
        """
        self.current_color = color
        self.update_rods(self.current_frame)

    def clear(self):
        """Discards all currently loaded rods and regenerates the box."""
        self.rods = []
        self.scene = Qt3DCore.QEntity()
        self.box, self.top, self.top_t, self.front, self.front_t = \
            self.create_box(self.scene)
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
        camController = QOrbitCameraController(self.scene)
        camController.setLinearSpeed(250.0)
        camController.setLookSpeed(180.0)
        camController.setCamera(self.camera)
        self.view.setRootEntity(self.scene)
