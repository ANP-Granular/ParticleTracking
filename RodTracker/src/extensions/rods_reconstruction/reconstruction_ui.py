# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '.\reconstruction_ui.ui'
#
# Created by: PyQt5 UI code generator 5.15.10
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_reconstruction_ui(object):
    def setupUi(self, reconstruction_ui):
        reconstruction_ui.setObjectName("reconstruction_ui")
        reconstruction_ui.resize(706, 661)
        self.verticalLayout = QtWidgets.QVBoxLayout(reconstruction_ui)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.verticalLayout_11 = QtWidgets.QVBoxLayout()
        self.verticalLayout_11.setObjectName("verticalLayout_11")
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.lbl_start = QtWidgets.QLabel(reconstruction_ui)
        self.lbl_start.setObjectName("lbl_start")
        self.horizontalLayout_6.addWidget(self.lbl_start)
        self.start_frame = QtWidgets.QSpinBox(reconstruction_ui)
        self.start_frame.setObjectName("start_frame")
        self.horizontalLayout_6.addWidget(self.start_frame)
        self.verticalLayout_11.addLayout(self.horizontalLayout_6)
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.lbl_end = QtWidgets.QLabel(reconstruction_ui)
        self.lbl_end.setObjectName("lbl_end")
        self.horizontalLayout_7.addWidget(self.lbl_end)
        self.end_frame = QtWidgets.QSpinBox(reconstruction_ui)
        self.end_frame.setObjectName("end_frame")
        self.horizontalLayout_7.addWidget(self.end_frame)
        self.verticalLayout_11.addLayout(self.horizontalLayout_7)
        self.group_colors_reconstruction = QtWidgets.QGroupBox(reconstruction_ui)
        self.group_colors_reconstruction.setObjectName("group_colors_reconstruction")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.group_colors_reconstruction)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.cb_purple = QtWidgets.QCheckBox(self.group_colors_reconstruction)
        self.cb_purple.setObjectName("cb_purple")
        self.gridLayout_2.addWidget(self.cb_purple, 0, 1, 1, 1)
        self.cb_green = QtWidgets.QCheckBox(self.group_colors_reconstruction)
        self.cb_green.setObjectName("cb_green")
        self.gridLayout_2.addWidget(self.cb_green, 1, 1, 1, 1)
        self.cb_red = QtWidgets.QCheckBox(self.group_colors_reconstruction)
        self.cb_red.setObjectName("cb_red")
        self.gridLayout_2.addWidget(self.cb_red, 1, 0, 1, 1)
        self.cb_black = QtWidgets.QCheckBox(self.group_colors_reconstruction)
        self.cb_black.setObjectName("cb_black")
        self.gridLayout_2.addWidget(self.cb_black, 0, 0, 1, 1)
        self.cb_yellow = QtWidgets.QCheckBox(self.group_colors_reconstruction)
        self.cb_yellow.setObjectName("cb_yellow")
        self.gridLayout_2.addWidget(self.cb_yellow, 2, 1, 1, 1)
        self.cb_blue = QtWidgets.QCheckBox(self.group_colors_reconstruction)
        self.cb_blue.setObjectName("cb_blue")
        self.gridLayout_2.addWidget(self.cb_blue, 2, 0, 1, 1)
        self.verticalLayout_11.addWidget(self.group_colors_reconstruction)
        self.cb_tracking = QtWidgets.QCheckBox(reconstruction_ui)
        self.cb_tracking.setObjectName("cb_tracking")
        self.verticalLayout_11.addWidget(self.cb_tracking)
        self.horizontalLayout_5.addLayout(self.verticalLayout_11)
        self.pb_solve = QtWidgets.QPushButton(reconstruction_ui)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pb_solve.sizePolicy().hasHeightForWidth())
        self.pb_solve.setSizePolicy(sizePolicy)
        self.pb_solve.setObjectName("pb_solve")
        self.horizontalLayout_5.addWidget(self.pb_solve)
        self.verticalLayout.addLayout(self.horizontalLayout_5)
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.lbl_calibration = QtWidgets.QLabel(reconstruction_ui)
        self.lbl_calibration.setObjectName("lbl_calibration")
        self.horizontalLayout_8.addWidget(self.lbl_calibration)
        self.le_calibration = QtWidgets.QLineEdit(reconstruction_ui)
        self.le_calibration.setObjectName("le_calibration")
        self.horizontalLayout_8.addWidget(self.le_calibration)
        self.tb_calibration = QtWidgets.QToolButton(reconstruction_ui)
        self.tb_calibration.setObjectName("tb_calibration")
        self.horizontalLayout_8.addWidget(self.tb_calibration)
        self.verticalLayout.addLayout(self.horizontalLayout_8)
        self.horizontalLayout_10 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        self.lbl_transformation = QtWidgets.QLabel(reconstruction_ui)
        self.lbl_transformation.setObjectName("lbl_transformation")
        self.horizontalLayout_10.addWidget(self.lbl_transformation)
        self.le_transformation = QtWidgets.QLineEdit(reconstruction_ui)
        self.le_transformation.setObjectName("le_transformation")
        self.horizontalLayout_10.addWidget(self.le_transformation)
        self.tb_transformation = QtWidgets.QToolButton(reconstruction_ui)
        self.tb_transformation.setObjectName("tb_transformation")
        self.horizontalLayout_10.addWidget(self.tb_transformation)
        self.verticalLayout.addLayout(self.horizontalLayout_10)
        self.horizontalLayout_9 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_9.setObjectName("horizontalLayout_9")
        self.lbl_solver = QtWidgets.QLabel(reconstruction_ui)
        self.lbl_solver.setObjectName("lbl_solver")
        self.horizontalLayout_9.addWidget(self.lbl_solver)
        self.le_solver = QtWidgets.QLineEdit(reconstruction_ui)
        self.le_solver.setObjectName("le_solver")
        self.horizontalLayout_9.addWidget(self.le_solver)
        self.tb_solver = QtWidgets.QToolButton(reconstruction_ui)
        self.tb_solver.setObjectName("tb_solver")
        self.horizontalLayout_9.addWidget(self.tb_solver)
        self.verticalLayout.addLayout(self.horizontalLayout_9)
        self.horizontalLayout_11 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_11.setObjectName("horizontalLayout_11")
        self.lbl_plots = QtWidgets.QLabel(reconstruction_ui)
        self.lbl_plots.setObjectName("lbl_plots")
        self.horizontalLayout_11.addWidget(self.lbl_plots)
        self.pb_update_plots = QtWidgets.QPushButton(reconstruction_ui)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pb_update_plots.sizePolicy().hasHeightForWidth())
        self.pb_update_plots.setSizePolicy(sizePolicy)
        self.pb_update_plots.setObjectName("pb_update_plots")
        self.horizontalLayout_11.addWidget(self.pb_update_plots)
        self.tb_plots_left = QtWidgets.QToolButton(reconstruction_ui)
        self.tb_plots_left.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
        self.tb_plots_left.setArrowType(QtCore.Qt.LeftArrow)
        self.tb_plots_left.setObjectName("tb_plots_left")
        self.horizontalLayout_11.addWidget(self.tb_plots_left)
        self.lbl_current_plot = QtWidgets.QLabel(reconstruction_ui)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lbl_current_plot.sizePolicy().hasHeightForWidth())
        self.lbl_current_plot.setSizePolicy(sizePolicy)
        self.lbl_current_plot.setObjectName("lbl_current_plot")
        self.horizontalLayout_11.addWidget(self.lbl_current_plot)
        self.tb_plots_right = QtWidgets.QToolButton(reconstruction_ui)
        self.tb_plots_right.setArrowType(QtCore.Qt.RightArrow)
        self.tb_plots_right.setObjectName("tb_plots_right")
        self.horizontalLayout_11.addWidget(self.tb_plots_right)
        self.verticalLayout.addLayout(self.horizontalLayout_11)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.stacked_plots = QtWidgets.QStackedWidget(reconstruction_ui)
        self.stacked_plots.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.stacked_plots.setObjectName("stacked_plots")
        self.verticalLayout.addWidget(self.stacked_plots)
        self.progress_reconstruction = QtWidgets.QProgressBar(reconstruction_ui)
        self.progress_reconstruction.setProperty("value", 24)
        self.progress_reconstruction.setInvertedAppearance(False)
        self.progress_reconstruction.setObjectName("progress_reconstruction")
        self.verticalLayout.addWidget(self.progress_reconstruction)

        self.retranslateUi(reconstruction_ui)
        QtCore.QMetaObject.connectSlotsByName(reconstruction_ui)

    def retranslateUi(self, reconstruction_ui):
        _translate = QtCore.QCoreApplication.translate
        reconstruction_ui.setWindowTitle(_translate("reconstruction_ui", "Form"))
        self.lbl_start.setText(_translate("reconstruction_ui", "Start Frame:"))
        self.lbl_end.setText(_translate("reconstruction_ui", "End Frame:"))
        self.group_colors_reconstruction.setTitle(_translate("reconstruction_ui", "Particle Color"))
        self.cb_purple.setText(_translate("reconstruction_ui", "purple"))
        self.cb_green.setText(_translate("reconstruction_ui", "green"))
        self.cb_red.setText(_translate("reconstruction_ui", "red"))
        self.cb_black.setText(_translate("reconstruction_ui", "black"))
        self.cb_yellow.setText(_translate("reconstruction_ui", "yellow"))
        self.cb_blue.setText(_translate("reconstruction_ui", "blue"))
        self.cb_tracking.setText(_translate("reconstruction_ui", "Tracking"))
        self.pb_solve.setText(_translate("reconstruction_ui", "Solve"))
        self.lbl_calibration.setText(_translate("reconstruction_ui", "Camera Calibration:"))
        self.tb_calibration.setText(_translate("reconstruction_ui", "..."))
        self.lbl_transformation.setText(_translate("reconstruction_ui", "World Transformation:"))
        self.tb_transformation.setText(_translate("reconstruction_ui", "..."))
        self.lbl_solver.setText(_translate("reconstruction_ui", "Custom solver:"))
        self.tb_solver.setText(_translate("reconstruction_ui", "..."))
        self.lbl_plots.setText(_translate("reconstruction_ui", "Reconstruction performances:"))
        self.pb_update_plots.setText(_translate("reconstruction_ui", "Update Plots"))
        self.tb_plots_left.setText(_translate("reconstruction_ui", "..."))
        self.lbl_current_plot.setText(_translate("reconstruction_ui", "(0/0)"))
        self.tb_plots_right.setText(_translate("reconstruction_ui", "..."))