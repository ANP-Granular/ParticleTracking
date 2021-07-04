# -*- coding: utf-8 -*-

### Implementation by Adithya & Meera on February 2021.

# based on https://github.com/baoboa/pyqt5/blob/master/examples/widgets/imageviewer.py

# Created by: PyQt5 UI code generator 5.9.12
###

import os
import sys
import glob
from PyQt5 import QtCore, QtGui, QtWidgets, Qt
from PyQt5.QtGui import QPalette, QImage, QPainter, QPixmap, QPen
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import pandas as pd


class Ui_MainWindow(object):
    def __init__(self):
        # Initialize
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.scaleFactor = 0.0
        # self.dirIterator = None
        # self.dirReverser = None
        self.fileList = []
        self.currentfileindex = 0
        # CSV FILE STUFF
        color = 'blue'
        col_list = ["particle", "frame", "x1_gp3", "x2_gp3", "y1_gp3", "y2_gp3"]
        df_col = pd.read_csv('mark_rods/in_csv/rods_df_{:s}.csv'.format(color), usecols=col_list)
        self.df_part = df_col

    # Main Window
    def setup_ui(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1280, 1100)
        MainWindow.setFocus()
        # Label to display content
        self.Photo = QtWidgets.QLabel(self.centralwidget)
        self.centralwidget.setObjectName("centralwidget")
        self.centralwidget.setFocus()
        self.Photo.setBackgroundRole(QPalette.Base)
        self.Photo.setGeometry(QtCore.QRect(50, 0, 1180, 890))
        self.Photo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.Photo.setScaledContents(True)
        self.Photo.setObjectName("Photo")
        # Scroll area properties
        self.scrollArea = QScrollArea(self.centralwidget)
        self.scrollArea.setBackgroundRole(QPalette.Dark)
        self.scrollArea.setGeometry(QtCore.QRect(50, 0, 1180, 890))
        self.scrollArea.setWidget(self.Photo)
        self.scrollArea.setVisible(False)
        MainWindow.setCentralWidget(self.centralwidget)
        # Button properties
        self.pushprevious = QtWidgets.QPushButton(self.centralwidget)
        self.pushprevious.setGeometry(QtCore.QRect(380, 900, 111, 41))
        self.pushprevious.setObjectName("pushprevious")
        self.pushnext = QtWidgets.QPushButton(self.centralwidget)
        self.pushnext.setGeometry(QtCore.QRect(580, 900, 121, 41))
        self.pushnext.setObjectName("pushnext")
        self.overlay = QtWidgets.QPushButton(self.centralwidget)
        self.overlay.setGeometry(QtCore.QRect(780, 900, 131, 41))
        self.overlay.setObjectName("overlay")
        self.rodnum = QtWidgets.QPushButton('Rod number', self.centralwidget)
        self.rodnum.setGeometry(QtCore.QRect(980, 900, 141, 41))
        MainWindow.setCentralWidget(self.centralwidget)
        # Menu properties
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
        # Action properties
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
        # Add actions to menu
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
        # Signal to activate actions
        self.pushprevious.clicked.connect(self.show_prev)
        self.pushnext.clicked.connect(self.show_next)
        self.overlay.clicked.connect(self.show_overlay)
        self.rodnum.clicked.connect(self.choose_rod)
        self.actionzoom_in.triggered.connect(self.zoomIn)
        self.actionzoom_out.triggered.connect(self.zoomOut)
        self.actionopen.triggered.connect(self.file_open)
        self.normalSizeAct.triggered.connect(self.normalSize)
        self.fitToWindowAct.triggered.connect(self.fitToWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        # Information about actions in menu
        self.menufile.setTitle(_translate("MainWindow", "File"))
        self.menuEdit.setTitle(_translate("MainWindow", "Edit"))
        self.menuView.setTitle(_translate("MainWindow", "View"))
        self.pushprevious.setText(_translate("MainWindow", "previous"))
        self.pushprevious.setShortcut(_translate("MainWindow", "Left"))
        self.pushnext.setText(_translate("MainWindow", "next"))
        self.pushnext.setShortcut(_translate("MainWindow", "Right"))
        self.overlay.setText(_translate("MainWindow", "overlay"))
        self.overlay.setShortcut(_translate("MainWindow", "space"))
        self.rodnum.setText(_translate("MainWinsdow", "Rodnum"))
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

        # CSV STUFF
        df_part2 = self.df_part[self.df_part["frame"] == int(file_name[1:4])].reset_index()
        # df_col.sort_values(by=['particle'], inplace=True)

        file_name = os.path.splitext(file_name)[0]          # File name without extension
        print('File name:', file_name)

        if fileName:
            # open file as image
            image = QImage(fileName)

            if image.isNull():
                QMessageBox.information(self, "Image Viewer", "Cannot load %s." % fileName)
                return

            # Directory
            dirpath = os.path.dirname(fileName)
            print('Dir name:', dirpath)
            self.fileList = []
            for idx, f in enumerate(os.listdir(dirpath)):
                f_compare = os.path.splitext(f)[0]
                indx_f = f_compare == file_name
                if indx_f is True:
                    # Set file index
                    self.currentfileindex = idx
                fpath = os.path.join(dirpath, f)
                # print('fpath name:', fpath)
                if os.path.isfile(fpath) and f.endswith(('.png', '.jpg', '.jpeg')):
                    # Add all image files to a list
                    self.fileList.append(fpath)
            # Sort according to name / ascending order
            self.fileList.sort()
            print('Num of items in list:', len(self.fileList))

            # Set read image into Label with Pixmap
            image2 = self.show_pixmap(image, df_part2)
            self.Photo.setPixmap(QtGui.QPixmap.fromImage(image2))
            self.Photo.setScaledContents(True)
            self.scaleFactor = 1.0
            self.scrollArea.setVisible(True)
            self.fitToWindowAct.setEnabled(True)
            self.updateActions()
            print('Open_file {}:'.format(self.currentfileindex), file_name)

    def show_pixmap(self, image, df_part2):
        pixmap = QPixmap(image)
        painter = QPainter(pixmap)
        pen = QPen(Qt.cyan, 3)
        painter.setPen(pen)
        # insert for loop
        for ind_rod, value in enumerate(df_part2['particle']):
            x1 = df_part2['x1_gp3'][ind_rod] * 10.0
            x2 = df_part2['x2_gp3'][ind_rod] * 10.0
            y1 = df_part2['y1_gp3'][ind_rod] * 10.0
            y2 = df_part2['y2_gp3'][ind_rod] * 10.0
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            painter.drawText(int(x1), int(y1), 20, 20, Qt.TextSingleLine, str(value))
        painter.end()
        image2 = QtGui.QPixmap.toImage(pixmap)
        # to do, if seen is 0, then dotted
        return image2

    def show_overlay(self):
        filename = (self.fileList[self.currentfileindex])  # Chooses next image with specified extension
        file_name = os.path.split(filename)[-1]
        image_name = file_name
        pixmap = QPixmap(image_name)
        painter = QPainter(pixmap)
        pen = QPen(Qt.cyan, 3)
        painter.setPen(pen)
        col_list = ["particle", "frame", "x1_gp3", "x2_gp3", "y1_gp3", "y2_gp3"]
        df_col = pd.read_csv('mark_rods/in_csv/rods_df_{:s}.csv'.format(self.color), usecols=col_list)
        df_col = df_col[df_col["frame"] == int(image_name[1:4])].reset_index()  # insert frame name
        #df_col.sort_values(by=['particle'], inplace=True)
        # insert for loop
        for ind_rod, value in enumerate(df_col['particle']):
            x1 = df_col['x1_gp3'][ind_rod] * 10.0
            x2 = df_col['x2_gp3'][ind_rod] * 10.0
            y1 = df_col['y1_gp3'][ind_rod] * 10.0
            y2 = df_col['y2_gp3'][ind_rod] * 10.0
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            #painter.drawText(int(x1), int(y1), 20, 20, Qt.TextSingleLine, str(value))
        painter.end()

        # to do, if seen is 0, then dotted
        self.Photo.setPixmap(pixmap)

    def choose_rod(self):
        num, ok = QInputDialog.getInt(self, 'Choose a rod', 'Rod number')
        if ok:
            rod_choosen = self.setText(str(num))
            print('Rod number:', rod_choosen)
            return rod_choosen

    def show_next(self):
        if self.fileList:
            try:
                self.currentfileindex += 1  # Increments file index
                filename = (self.fileList[self.currentfileindex])  # Chooses next image with specified extension
                file_name = os.path.split(filename)[-1]
                # CSV STUFF
                df_part2 = self.df_part[self.df_part["frame"] == int(file_name[1:4])].reset_index()
                file_name = os.path.splitext(file_name)[0]
                # Create Pixmap operator to display image
                image_next = QImage(filename)
                if image_next.isNull():
                    # the file is not a valid image, remove it from the list
                    # and try to load the next one
                    self.fileList.remove(filename)
                    self.show_next()
                else:
                    # Set the image into Label with Pixmap
                    image2 = self.show_pixmap(image_next, df_part2)
                    #self.Photo.setPixmap(image2)
                    self.Photo.setPixmap(QtGui.QPixmap.fromImage(image2))
                    self.Photo.setScaledContents(True)
                    self.scaleFactor = 1.0
                    self.scrollArea.setVisible(True)
                    self.fitToWindowAct.setEnabled(True)
                    self.updateActions()
                    print('Next_file {}:'.format(self.currentfileindex), file_name)
            except:
                # the iterator has finished, restart it
                self.currentfileindex = -1
                self.show_next()
        else:
            # no file list found, load an image
            self.file_open()

    def show_prev(self):
        if self.fileList:
            try:
                self.currentfileindex -= 1  # Decrements file index
                filename = (self.fileList[self.currentfileindex])    # Chooses previous image with specified extension
                file_name = os.path.split(filename)[-1]
                # CSV STUFF
                df_part2 = self.df_part[self.df_part["frame"] == int(file_name[1:4])].reset_index()
                file_name = os.path.splitext(file_name)[0]
                # Create Pixmap operator to display image
                image_prev = QImage(filename)
                if image_prev.isNull():
                    # the file is not a valid image, remove it from the list
                    # and try to load the next one
                    self.fileList.remove(filename)
                    self.show_prev()
                else:
                    # Set the image into Label with Pixmap
                    image2 = self.show_pixmap(image_prev,df_part2)
                    self.Photo.setPixmap(QtGui.QPixmap.fromImage(image2))
                    self.Photo.setScaledContents(True)
                    self.scaleFactor = 1.0
                    self.scrollArea.setVisible(True)
                    self.fitToWindowAct.setEnabled(True)
                    self.updateActions()
                    print('Prev_file {}:'.format(self.currentfileindex), file_name)
            except:
                # the iterator has finished, restart it
                self.currentfileindex = -1
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
