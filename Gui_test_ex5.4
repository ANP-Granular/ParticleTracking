# -*- coding: utf-8 -*-

### Implementation by Adithya Viswanathan on February 2021.

# based on https://github.com/baoboa/pyqt5/blob/master/examples/widgets/imageviewer.py

# Created by: PyQt5 UI code generator 5.9.12
###

import os
import sys
import glob
from PyQt5 import QtCore, QtGui, QtWidgets, Qt
from PyQt5.QtGui import QPalette, QImage
from PyQt5.QtWidgets import *


class Ui_MainWindow(object):
    def __init__(self):

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.scaleFactor = 0.0
        self.imagenumber = 0
        self.dirIterator = None
        self.dirReverser = None
        self.fileList = []

    def setup_ui(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1080, 740)
        MainWindow.setFocus()

        self.Photo = QtWidgets.QLabel(self.centralwidget)
        self.centralwidget.setObjectName("centralwidget")
        self.centralwidget.setFocus()
        self.Photo.setBackgroundRole(QPalette.Base)
        self.Photo.setGeometry(QtCore.QRect(100, 0, 840, 620))
        self.Photo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.Photo.setScaledContents(True)
        self.Photo.setObjectName("Photo")
        MainWindow.setCentralWidget(self.centralwidget)
        self.pushprevious = QtWidgets.QPushButton(self.centralwidget)
        self.pushprevious.setGeometry(QtCore.QRect(320, 625, 121, 41))
        self.pushprevious.setObjectName("pushprevious")
        self.pushnext = QtWidgets.QPushButton(self.centralwidget)
        self.pushnext.setGeometry(QtCore.QRect(640, 625, 131, 41))
        self.pushnext.setObjectName("pushnext")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 22))
        self.menubar.setObjectName("menubar")
        self.menufile = QtWidgets.QMenu(self.menubar)
        self.menufile.setObjectName("menufile")
        self.menuEdit = QtWidgets.QMenu(self.menubar)
        self.menuEdit.setObjectName("menuEdit")
        self.menuView = QtWidgets.QMenu(self.menubar)
        self.menuView.setObjectName("menuView")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.openFile = QtWidgets.QAction(MainWindow)
        self.actionopen = QtWidgets.QAction(MainWindow)
        self.actionopen.setObjectName("actionopen")
        self.actionsave = QtWidgets.QAction(MainWindow)
        self.actionsave.setObjectName("actionsave")
        self.actionzoom_in = QtWidgets.QAction(MainWindow)
        self.actionzoom_in.setObjectName("actionzoom_in")
        self.actionzoom_out = QtWidgets.QAction(MainWindow)
        self.actionzoom_out.setObjectName("actionzoom_out")
        self.normalSizeAct = QtWidgets.QAction(MainWindow)
        self.normalSizeAct.setObjectName("Normal Size")
        self.fitToWindowAct = QtWidgets.QAction(MainWindow)
        self.fitToWindowAct.setObjectName("Fit to Window")

        self.scrollArea = QScrollArea(self.centralwidget)
        self.scrollArea.setBackgroundRole(QPalette.Dark)
        self.scrollArea.setGeometry(QtCore.QRect(100, 0, 840, 620))
        self.scrollArea.setWidget(self.Photo)
        self.scrollArea.setVisible(False)

        self.menufile.addAction(self.actionopen)
        self.menufile.addAction(self.actionsave)
        self.menuView.addAction(self.actionzoom_in)
        self.menuView.addAction(self.actionzoom_out)
        self.menuView.addAction(self.normalSizeAct)
        self.menuView.addAction(self.fitToWindowAct)
        self.menubar.addAction(self.menufile.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())
        self.menubar.addAction(self.menuView.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        self.pushprevious.clicked.connect(self.show_prev)
        self.pushnext.clicked.connect(self.show_next)
        self.actionzoom_in.triggered.connect(self.zoomIn)
        self.actionzoom_out.triggered.connect(self.zoomOut)
        self.actionopen.triggered.connect(self.file_open)
        self.normalSizeAct.triggered.connect(self.normalSize)
        self.fitToWindowAct.triggered.connect(self.fitToWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.menufile.setTitle(_translate("MainWindow", "File"))
        self.menuEdit.setTitle(_translate("MainWindow", "Edit"))
        self.menuView.setTitle(_translate("MainWindow", "View"))
        self.pushprevious.setText(_translate("MainWindow", "previous"))
        self.pushprevious.setShortcut(_translate("MainWindow", "Left"))
        self.pushnext.setText(_translate("MainWindow", "next"))
        self.pushnext.setShortcut(_translate("MainWindow", "Right"))
        self.actionopen.setText(_translate("MainWindow", "open"))
        self.actionopen.setStatusTip(_translate("MainWindow", "opens new file "))
        self.actionopen.setShortcut(_translate("MainWindow", "Ctrl+O"))
        self.actionsave.setText(_translate("MainWindow", "save"))
        self.actionsave.setStatusTip(_translate("MainWindow", "save a file "))
        self.actionsave.setShortcut(_translate("MainWindow", "Ctrl+S"))
        self.actionzoom_in.setText(_translate("MainWindow", "zoom-in"))
        self.actionzoom_in.setStatusTip(_translate("MainWindow", "zooming in"))
        self.actionzoom_in.setShortcut(_translate("MainWindow", "Ctrl+="))
        self.actionzoom_out.setText(_translate("MainWindow", "zoom-out"))
        self.actionzoom_out.setStatusTip(_translate("MainWindow", "zooming out"))
        self.actionzoom_out.setShortcut(_translate("MainWindow", "Ctrl+-"))
        self.normalSizeAct.setStatusTip(_translate("MainWindow", "Original size"))
        self.normalSizeAct.setShortcut(_translate("MainWindow", "Ctrl+R"))
        self.normalSizeAct.setText(_translate("MainWindow", "Original Size"))
        self.fitToWindowAct.setStatusTip(_translate("MainWindow", "Fit to Window"))
        self.fitToWindowAct.setShortcut(_translate("MainWindow", "Ctrl+F"))
        self.fitToWindowAct.setText(_translate("MainWindow", "Fit to Window"))

    def file_open(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(None, 'QFileDialog.getOpenFileName()', '',
                                                  'Images (*.png *.jpeg *.jpg)', options=options)
        file_name = os.path.split(fileName)[-1]
        # File name without extension
        file_name = os.path.splitext(file_name)[0]
        print('File name:', file_name)

        if fileName:
            # image = QtGui.QPixmap(fileName).scaled(self.Photo.size(), QtCore.Qt.KeepAspectRatio)
            image = QImage(fileName)

            if image.isNull():
                QMessageBox.information(self, "Image Viewer", "Cannot load %s." % fileName)
                return

            dirpath = os.path.dirname(fileName)
            print('Dir name:', dirpath)
            self.fileList = []
            for f in os.listdir(dirpath):
                fpath = os.path.join(dirpath, f)
                # print('fpath name:', fpath)
                if os.path.isfile(fpath) and f.endswith(('.png', '.jpg', '.jpeg')):
                    self.fileList.append(fpath)
            self.fileList.sort()
            print('Num of items in list:', len(self.fileList))
            self.dirIterator = iter(self.fileList)
            self.dirReverser = reversed(self.fileList)

            # while True:
            # cycle through the iterator until the current file with specified extension is found
            # if next(self.dirIterator) == fileName:
            #   break

            self.Photo.setPixmap(QtGui.QPixmap.fromImage(image))
            self.Photo.setScaledContents(True)
            self.scaleFactor = 1.0
            self.scrollArea.setVisible(True)
            self.fitToWindowAct.setEnabled(True)
            self.updateActions()

            # if not self.fitToWindowAct.isChecked():  #     self.Photo.adjustSize()

    def show_next(self):
        if self.fileList:
            try:
                filename = next(self.dirIterator)  # Chooses next image with specified extension
                file_name = os.path.split(filename)[-1]
                file_name = os.path.splitext(file_name)[0]
                image_next = QtGui.QPixmap(filename).scaled(self.Photo.size(), QtCore.Qt.KeepAspectRatio)
                if image_next.isNull():
                    # the file is not a valid image, remove it from the list
                    # and try to load the next one
                    self.fileList.remove(filename)
                    self.show_next()
                else:
                    self.Photo.setPixmap(image_next)
                    self.imagenumber = self.imagenumber + 1
                    print('Next_file {}:'.format(self.imagenumber), file_name)
            except:
                # the iterator has finished, restart it
                self.dirIterator = iter(self.fileList)
                self.show_next()
        else:
            # no file list found, load an image
            self.file_open()

    def show_prev(self):
        if self.fileList:
            try:
                filename = next(self.dirReverser)  # NEEDS TO BE SOLVED to call PREVIOUS IMAGE!!!!
                file_name = os.path.split(filename)[-1]
                file_name = os.path.splitext(file_name)[0]
                image_prev = QtGui.QPixmap(filename).scaled(self.Photo.size(), QtCore.Qt.KeepAspectRatio)
                if image_prev.isNull():
                    # the file is not a valid image, remove it from the list
                    # and try to load the next one
                    self.fileList.remove(filename)
                    self.show_prev()
                else:
                    self.Photo.setPixmap(image_prev)
                    self.imagenumber = self.imagenumber - 1
                    print('Prev_file {}:'.format(self.imagenumber), file_name)
            except:
                # the iterator has finished, restart it
                self.dirReverser = reversed(self.fileList)
                self.show_prev()
        else:
            # no file list found, load an image
            self.file_open()

    def zoomIn(self):
        self.scaleImage(1.25)

    def zoomOut(self):
        self.scaleImage(0.8)

    def normalSize(self):
        self.Photo.adjustSize()
        self.scaleFactor = 1.0

    def fitToWindow(self):
        fitToWindow = self.fitToWindowAct.isChecked()
        self.scrollArea.setWidgetResizable(fitToWindow)
        if not fitToWindow:
            self.normalSize()

        self.updateActions()

    def updateActions(self):
        self.actionzoom_in.setEnabled(not self.fitToWindowAct.isChecked())
        self.actionzoom_in.setEnabled(not self.fitToWindowAct.isChecked())
        self.normalSizeAct.setEnabled(not self.fitToWindowAct.isChecked())

    def scaleImage(self, factor):
        self.scaleFactor *= factor
        self.Photo.resize(self.scaleFactor * self.Photo.pixmap().size())
        self.adjustScrollBar(self.scrollArea.horizontalScrollBar(), factor)
        self.adjustScrollBar(self.scrollArea.verticalScrollBar(), factor)
        self.actionzoom_in.setEnabled(self.scaleFactor < 3.0)
        self.actionzoom_out.setEnabled(self.scaleFactor > 0.333)

    def adjustScrollBar(self, scrollBar, factor):
        scrollBar.setValue(int(factor * scrollBar.value() + ((factor - 1) * scrollBar.pageStep() / 2)))


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setup_ui(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
