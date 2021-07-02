import os
import sys
import glob
from PyQt5 import QtCore, QtGui, QtWidgets, Qt
from PyQt5.QtGui import QPalette, QImage, QPainter, QPixmap, QPen
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
import pandas as pd
from PyQt5.QtGui import QMouseEvent
from PyQt5 import QtGui
from PyQt5.QtCore import QRect, Qt, QMimeData
from PyQt5.QtGui import QPainter, QImage, QDrag
from PyQt5.QtWidgets import QApplication, QMainWindow
import numpy as np

class Ui_MainWindow(object):
    def __init__(self):
        # super is needed to track mouse movements
        super().__init__()
        # This is a bit tricky, AcceptDrops is a required function for
        # drag and drop of QLineEdit textbox contents into another textbox
        # but i set this function below to pass, because the function was not found
        self.setAcceptDrops(True)
        # Initialize
        self.CentralWidget = QtWidgets.QWidget(MainWindow)
        # start position set to none, did not check if the code works without this statement
        self.startPos = None
        # scale factor for image
        self.scaleFactor = 0.0
        # very important variable that keeps track of the current image that's displayed
        self.CurrentFileIndex = 0
        # initializations for widgets
        self.RodNumber = QtWidgets.QPushButton('Rod Number', self.CentralWidget)
        self.ClearSave = QtWidgets.QPushButton('Clear/Save', self.CentralWidget)
        self.overlay = QtWidgets.QPushButton(self.CentralWidget)
        self.pushnext = QtWidgets.QPushButton(self.CentralWidget)
        self.pushprevious = QtWidgets.QPushButton(self.CentralWidget)
        self.scrollArea = QScrollArea(self.CentralWidget)
        self.label = QLabel(self.CentralWidget)
        self.Photo = QtWidgets.QLabel(self.CentralWidget)

    def setup_ui(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setWindowState(QtCore.Qt.WindowMaximized)
        # MainWindow.resize(1280, 1100)
        MainWindow.setFocus()
        # Label to display content
        self.CentralWidget.setObjectName("centralized")
        self.CentralWidget.setFocus()
        self.Photo.setBackgroundRole(QPalette.Base)
        self.Photo.setGeometry(QtCore.QRect(50, 0, 1180, 890))
        self.Photo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.Photo.setObjectName("Photo")
        # New label is a small transparent box above the image that says your current actions
        self.label.setGeometry(QtCore.QRect(600, 0, 1180, 30))
        self.label.setText('Open image in folder')
        MainWindow.setCentralWidget(self.CentralWidget)
        # Scroll area properties
        self.scrollArea.setBackgroundRole(QPalette.Dark)
        self.scrollArea.setGeometry(QtCore.QRect(50, 50, 1180, 890))
        self.scrollArea.setWidget(self.Photo)
        self.scrollArea.setVisible(False)
        MainWindow.setCentralWidget(self.CentralWidget)
        # Button properties
        self.pushprevious.setGeometry(QtCore.QRect(140, 980, 111, 41))
        self.pushprevious.setObjectName("pushprevious")
        self.pushnext.setGeometry(QtCore.QRect(340, 980, 131, 41))
        self.pushnext.setObjectName("pushnext")
        self.overlay.setGeometry(QtCore.QRect(540, 980, 121, 41))
        self.overlay.setObjectName("overlay")
        self.RodNumber.setGeometry(QtCore.QRect(740, 980, 141, 41))
        self.RodNumber.setObjectName("NumberChange")
        self.ClearSave.setGeometry(QtCore.QRect(940, 980, 141, 41))
        self.ClearSave.setObjectName("Clear/Save")

        MainWindow.setCentralWidget(self.CentralWidget)
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
        self.RodNumber.clicked.connect(self.choose_rod)
        self.ClearSave.clicked.connect(self.clear_screen)
        self.actionzoom_in.triggered.connect(self.zoomIn)
        self.actionzoom_out.triggered.connect(self.zoomOut)
        self.actionopen.triggered.connect(self.file_open)
        self.normalSizeAct.triggered.connect(self.normalSize)
        self.fitToWindowAct.triggered.connect(self.fitToWindow)
        self.Photo.mousePressEvent = self.getPixel

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        # Information about actions in menu
        # we dont need o set shortcuts for any reason,
        # basically i have no idea what this thing does
        # delete if not useful
        self.menufile.setTitle(_translate("MainWindow", "File"))
        self.menuEdit.setTitle(_translate("MainWindow", "Edit"))
        self.menuView.setTitle(_translate("MainWindow", "View"))
        self.pushprevious.setText(_translate("MainWindow", "previous"))
        self.pushprevious.setShortcut(_translate("MainWindow", "Left"))
        self.pushnext.setText(_translate("MainWindow", "next"))
        self.pushnext.setShortcut(_translate("MainWindow", "Right"))
        self.overlay.setText(_translate("MainWindow", "overlay"))
        self.overlay.setShortcut(_translate("MainWindow", "space"))
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
        # opens directory to select image
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(None, 'QFileDialog.getOpenFileName()', '',
                                                  'Images (*.png *.jpeg *.jpg)', options=options)
        file_name = os.path.split(fileName)[-1]
        # File name without extension
        file_name = os.path.splitext(file_name)[0]
        print('File name:', file_name)
        if fileName:
            # open file as image
            self.image = QImage(fileName)
            if self.image.isNull():
                QMessageBox.information(self, "Image Viewer", "Cannot load %s." % fileName)
                return
            # Directory
            dirpath = os.path.dirname(fileName)
            print('Dir_name:', dirpath)
            self.fileList = []
            # this loop is kinda tricky
            # it loop through all the images
            # checks for some condition
            # and appends it to a file List
            for idx, f in enumerate(os.listdir(dirpath)):
                f_compare = os.path.splitext(f)[0]
                indx_f = f_compare == file_name
                if indx_f is True:
                    # Set file index
                    self.CurrentFileIndex = idx
                fpath = os.path.join(dirpath, f)
                # print('fpath name:', fpath)
                if os.path.isfile(fpath) and f.endswith(('.png', '.jpg', '.jpeg')):
                    # Add all image files to a list
                    self.fileList.append(fpath)
            # Sort according to name / ascending order
            self.fileList.sort()
            print('Num of items in list:', len(self.fileList))
            # then the image is displayed in this function NoRods
            self.show_pixmap_NoRods()
            print('Open_file {}:'.format(self.CurrentFileIndex), file_name)
            self.label.setText('File opened: {}'.format(file_name))

    def show_pixmap_NoRods(self):
        pixmap = QtGui.QPixmap.fromImage(self.image)
        self.Photo.setPixmap(pixmap)
        self.Photo.setScaledContents(True)
        self.scrollArea.setVisible(True)
        self.Photo.resize(pixmap.width(), pixmap.height())
        # Resize window to image size
        # self.scaleFactor = 1.0
        self.fitToWindowAct.setEnabled(True)
        # 1180, 890
        self.updateActions()

    def show_overlay(self):
        # when overlay button is clicked, it asked for color and
        # overlays the image rods with the csv rods of specified color
        items = ("black", "blue", "green", "purple", "red", "yellow")
        item, ok = QInputDialog.getItem(self.CentralWidget, "select input dialog",
                                        "list of colors", items, 0, False)
        filename = (self.fileList[self.CurrentFileIndex])  # Chooses next image with specified extension
        file_name = os.path.split(filename)[-1]
        # file_name = os.path.splitext(file_name)[0]

        col_list = ["particle", "frame", "x1_gp3", "x2_gp3", "y1_gp3", "y2_gp3"]
        if ok and item:
            self.color = item
            df_part = pd.read_csv('mark_rods/in_csv/rods_df_{:s}.csv'.format(self.color), usecols=col_list)
            df_part2 = df_part[df_part["frame"] == int(file_name[1:4])].reset_index()
            image = QImage(filename)
            self.show_pixmap(image, df_part2)

    def show_pixmap(self, image, df_part2):
        # show_pixmap is called to draw the rods over the image
        self.rod_pixmap = QPixmap(image)
        painter = QPainter(self.rod_pixmap)
        pen = QPen(Qt.cyan, 3)
        painter.setPen(pen)
        # insert for loop
        for ind_rod, value in enumerate(df_part2['particle']):
            # theres some problem with the dimension scaling
            # So Dimtry asked us to multiple the rod values by 10
            x1 = df_part2['x1_gp3'][ind_rod] * 10.0
            x2 = df_part2['x2_gp3'][ind_rod] * 10.0
            y1 = df_part2['y1_gp3'][ind_rod] * 10.0
            y2 = df_part2['y2_gp3'][ind_rod] * 10.0
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            painter.drawText(int(x1) + 5, int(y1) + 5, 20, 20, Qt.TextSingleLine, str(value))
        painter.end()
        self.Photo.setPixmap(self.rod_pixmap)
        self.Photo.setScaledContents(True)
        self.scrollArea.setVisible(True)
        self.Photo.resize(self.rod_pixmap.width(), self.rod_pixmap.height())
        self.fitToWindowAct.setEnabled(True)
        self.updateActions()
        self.Photo.mousePressEvent = self.getPixel
        self.Photo.mouseReleaseEvent = self.drawthat

    def choose_rod(self):
        # button click on number overlay calls choose rod
        # it shows rods the same way but also adds a text box at the end of every rod
        filename = (self.fileList[self.CurrentFileIndex])
        file_name = os.path.split(filename)[-1]
        image = QImage(filename)
        items = ("black", "blue", "green", "purple", "red", "yellow")
        item, ok = QInputDialog.getItem(self.CentralWidget, "select input dialog",
                                        "list of colors", items, 0, False)
        # file_name = os.path.splitext(file_name)[0]
        col_list = ["particle", "frame", "x1_gp3", "x2_gp3", "y1_gp3", "y2_gp3"]
        if ok and item:
            self.color = item
        else:
            self.color = 'blue'
        df_part = pd.read_csv('mark_rods/in_csv/rods_df_{:s}.csv'.format(self.color), usecols=col_list)
        df_part2 = df_part[df_part["frame"] == int(file_name[1:4])].reset_index()
        self.show_rods(image, df_part2)

    def show_rods(self, image, df_part2):
        # this is a sub function of choose_rod below
        pixmap = QPixmap(image)
        painter = QPainter(pixmap)
        pen = QPen(Qt.cyan, 3)
        painter.setPen(pen)
        self.edits = []
        for ind_rod, value in enumerate(df_part2['particle']):
            x1 = df_part2['x1_gp3'][ind_rod] * 10.0
            x2 = df_part2['x2_gp3'][ind_rod] * 10.0
            y1 = df_part2['y1_gp3'][ind_rod] * 10.0
            y2 = df_part2['y2_gp3'][ind_rod] * 10.0
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            painter.drawText(int(x1), int(y1), 20, 20, Qt.TextSingleLine, str(value))
            # Line edit box
            s = "s" + str(ind_rod)
            s = QLineEdit(self.Photo)
            s.setDragEnabled(True)
            s.resize(20, 20)
            s.move(int(x2) + 5, int(y2) + 5)
            s.show()
            s.setObjectName("s" + str(ind_rod))
            self.edits.append(s)
        painter.end()
        self.Photo.setPixmap(pixmap)
        self.Photo.setScaledContents(True)
        self.scrollArea.setVisible(True)
        self.Photo.resize(pixmap.width(), pixmap.height())
        self.fitToWindowAct.setEnabled(True)
        self.updateActions()

    def clear_screen(self):

        # if self.edits exists or if its empty
        for s in self.edits:
            s.deleteLater()
        self.Photo.setPixmap(QtGui.QPixmap.fromImage(self.image))
        self.Photo.setScaledContents(True)
        self.scrollArea.setVisible(True)
        self.Photo.resize(self.image.width(), self.image.height())
        self.fitToWindowAct.setEnabled(True)
        self.updateActions()

    # drag enter and drop event are event actions for text box content drag and drop

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("text/plain"):
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        event.accept()
        # self.Tbox.setText(event.mimeData().text())

    # get pixel = mouse press event
    # and draw that = mouse release event for rod drawing

    def getPixel(self, event):
        self.startPos = self.Photo.mapFromParent(event.pos())

    def drawthat(self, event):
        start = self.startPos
        end = event.pos()
        # Magic happens here
        pixmap = QPixmap(self.rod_pixmap)
        qp = QPainter(pixmap)
        pen = QPen(Qt.white, 5)
        qp.setPen(pen)
        # qp.drawText(start.x(), start.y(), str(self.CurrentFileIndex))
        qp.drawLine(start, end)
        # qp.drawPixmap(start, pixmap, overlay)
        qp.end()
        self.Photo.setPixmap(pixmap)
        self.Photo.setScaledContents(True)
        self.scrollArea.setVisible(True)
        self.Photo.resize(self.image.width(), self.image.height())
        self.fitToWindowAct.setEnabled(True)
        self.updateActions()
        # saving
        num, ok = QInputDialog.getInt(self.Photo, 'Choose a rod to replace', 'Rod number')
        filename = (self.fileList[self.CurrentFileIndex])
        file_name = os.path.split(filename)[-1]
        col_list = ["particle", "frame", "x1_gp3", "x2_gp3", "y1_gp3", "y2_gp3"]
        df_part = pd.read_csv('mark_rods/in_csv/rods_df_{:s}.csv'.format(self.color))
        df_part2 = df_part[df_part["frame"] == int(file_name[1:4])].reset_index()
        if ok:
            # num is the number of the rod
            df_part2['x1_gp3'][df_part2["particle"] == num] = int(start.x())
            df_part2['x2_gp3'][df_part2["particle"] == num] = int(start.y())
            df_part2['y1_gp3'][df_part2["particle"] == num] = int(end.x())
            df_part2['y2_gp3'][df_part2["particle"] == num] = int(end.y())
            df_part[df_part["frame"] == int(file_name[1:4])] = df_part2
            df_part.to_csv('mark_rods/in_csv/rods_df_{:s}.csv'.format(self.color))

    def show_next(self):
        if self.fileList:
            try:
                self.CurrentFileIndex += 1  # Increments file index
                filename = (self.fileList[self.CurrentFileIndex])  # Chooses next image with specified extension
                file_name = os.path.split(filename)[-1]
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
                    # insert you function here
                    # self.Photo.setPixmap(image2)
                    self.Photo.setPixmap(QtGui.QPixmap.fromImage(image_next))
                    self.Photo.setScaledContents(True)
                    # self.scaleFactor = 1.0
                    self.scrollArea.setVisible(True)
                    self.fitToWindowAct.setEnabled(True)
                    self.updateActions()
                    print('Next_file {}:'.format(self.CurrentFileIndex), file_name)
                    # Label stuff
                    self.label.setText('File: {}'.format(file_name))
                    # self.update()
            except:
                # the iterator has finished, restart it
                self.CurrentFileIndex = -1
                self.show_next()
        else:
            # no file list found, load an image
            self.file_open()

    def show_prev(self):
        if self.fileList:
            try:
                self.CurrentFileIndex -= 1  # Decrements file index
                filename = (self.fileList[self.CurrentFileIndex])  # Chooses previous image with specified extension
                file_name = os.path.split(filename)[-1]
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
                    self.Photo.setPixmap(QtGui.QPixmap.fromImage(image_prev))
                    self.Photo.setScaledContents(True)
                    # self.scaleFactor = 1.0
                    self.scrollArea.setVisible(True)
                    self.fitToWindowAct.setEnabled(True)
                    self.updateActions()
                    print('Prev_file {}:'.format(self.CurrentFileIndex), file_name)
                    self.label.setText('File: {}'.format(file_name))

            except:
                # the iterator has finished, restart it
                self.CurrentFileIndex = -1
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

    def setAcceptDrops(self, param):
        pass


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setup_ui(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
