from typing import List
import numpy as np
import matplotlib.colors as mpl_colors
from PyQt5 import Qt3DCore, QtCore, QtWidgets, QtGui
from PyQt5.Qt3DRender import QDirectionalLight, QCamera
from PyQt5.Qt3DExtras import QPhongMaterial, \
    QCylinderMesh, Qt3DWindow, QOrbitCameraController, QCuboidMesh, \
    QExtrudedTextMesh, QPhongAlphaMaterial
import RodTracker.backend.data_operations as d_ops


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

        # Camera.
        self.camera = self.init_camera(self.view, self.scene)
        self.view.setRootEntity(self.scene)

        self.current_frame = None

    def show_front(self):
        self.camera.setPosition(
            QtGui.QVector3D(0.0, 0.0, 1.5 * BOX_WIDTH)
        )
        self.camera.setUpVector(
            QtGui.QVector3D(0.0, 1.0, 0.0)
        )
        self.camera.set

    def show_top(self):
        self.camera.setPosition(
            QtGui.QVector3D(0.0, 1.5 * BOX_WIDTH, 0.0)
        )
        self.camera.setUpVector(
            QtGui.QVector3D(0.0, 0.0, -1.0)
        )

    @QtCore.pyqtSlot(int)
    def update_rods(self, frame: int) -> None:
        if frame is None:
            return

        with QtCore.QReadLocker(d_ops.lock):
            if d_ops.rod_data is None:
                return
            disp_data = d_ops.rod_data.loc[d_ops.rod_data.frame == frame]

        available_rods = len(self.rods)
        for i in range(len(disp_data)):
            if i >= available_rods:
                self.rods.append(Qt3DCore.QEntity(self.scene))
            rod = self.rods[i]
            rod.setEnabled(True)
            data = disp_data.iloc[i]
            cm_rod = QCylinderMesh()
            cm_rod.setRadius(ROD_RADIUS)
            # cm_rod.setLength(rod_representation_len)
            color = mpl_colors.to_rgba(data["color"], alpha=1.0)
            material = QPhongMaterial(self.scene)
            material.setDiffuse(QtGui.QColor.fromRgbF(*color))

            x = data[["x1", "x2"]].to_numpy() * POSITION_SCALING
            y = data[["y1", "y2"]].to_numpy() * POSITION_SCALING
            z = data[["z1", "z2"]].to_numpy() * POSITION_SCALING
            dx = np.diff(x)
            dy = np.diff(y)
            dz = np.diff(z)
            cm_rod.setLength(np.linalg.norm(np.array((dx, dy, dz))))

            transformation = Qt3DCore.QTransform()
            new_pos = QtGui.QVector3D(x[0] + dx / 2, y[0] + dy / 2,
                                      z[0] + dz / 2)
            transformation.setTranslation(new_pos)
            rod_rot = QtGui.QQuaternion.rotationTo(
                QtGui.QVector3D(0., 1., 0.), QtGui.QVector3D(dx, dy, dz))
            transformation.setRotation(rod_rot)
            rod.addComponent(cm_rod)
            rod.addComponent(transformation)
            rod.addComponent(material)
        self.frame = frame

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
    def create_rods(frame: int) -> List[List[Qt3DCore.QComponent]]:
        with QtCore.QReadLocker(d_ops.lock):
            if d_ops.rod_data is None:
                return
            disp_data = d_ops.rod_data.loc[d_ops.rod_data.frame == frame]
        rods = []
        for i in range(len(disp_data)):
            # rods.append(Qt3DCore.QEntity())             # TODO: set scene
            # rod = rods[i]
            # rod.setEnabled(True)
            data = disp_data.iloc[i]
            cm_rod = QCylinderMesh()
            cm_rod.setRadius(ROD_RADIUS)
            color = mpl_colors.to_rgba(data["color"], alpha=1.0)
            material = QPhongMaterial()                 # TODO: set scene
            material.setDiffuse(QtGui.QColor.fromRgbF(*color))

            x = data[["x1", "x2"]].to_numpy() * POSITION_SCALING
            y = data[["y1", "y2"]].to_numpy() * POSITION_SCALING
            z = data[["z1", "z2"]].to_numpy() * POSITION_SCALING
            dx = np.diff(x)
            dy = np.diff(y)
            dz = np.diff(z)
            cm_rod.setLength(np.linalg.norm(np.array((dx, dy, dz))))

            transformation = Qt3DCore.QTransform()
            new_pos = QtGui.QVector3D(x[0] + dx, y[0] + dy, z[0] + dz)
            transformation.setTranslation(new_pos)
            rod_rot = QtGui.QQuaternion.rotationTo(
                QtGui.QVector3D(0., 1., 0.), QtGui.QVector3D(dx, dy, dz))
            transformation.setRotation(rod_rot)

            rods.append([cm_rod, transformation, material])

            # rod.addComponent(cm_rod)
            # rod.addComponent(transformation)
            # rod.addComponent(material)
        return rods

    @staticmethod
    def init_camera(view: Qt3DWindow, scene: Qt3DCore.QEntity) -> QCamera:
        # Camera
        camera = view.camera()
        camera.lens().setPerspectiveProjection(45.0, 16.0 / 9.0, 0.1, 1000.0)
        camera.setPosition(QtGui.QVector3D(0.0, 1.5 * BOX_HEIGHT,
                                           1.5 * BOX_DEPTH))
        camera.setViewCenter(QtGui.QVector3D(0.0, 0.0, 0.0))

        # Camera controls
        camController = QOrbitCameraController(scene)
        camController.setLinearSpeed(50.0)
        camController.setLookSpeed(180.0)
        camController.setCamera(camera)
        return camera

    @staticmethod
    def create_box(root: Qt3DCore.QEntity):
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
