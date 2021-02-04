# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Gui_test_ex5.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

DATA_PATH = "/Volumes/Macintosh_HD/Germany/OVGU_MSE/HiWi/Granular/2020_12_Fallturm/shot9/GP3/"


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(872, 628)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.Photo = QtWidgets.QLabel(self.centralwidget)
        self.Photo.setGeometry(QtCore.QRect(50, 0, 761, 521))
        self.Photo.setText("")
        self.Photo.setPixmap(QtGui.QPixmap("{}GP3_00550.jpg".format(DATA_PATH)))
        self.Photo.setScaledContents(True)
        self.Photo.setObjectName("Photo")
        self.pushprevious = QtWidgets.QPushButton(self.centralwidget)
        self.pushprevious.setGeometry(QtCore.QRect(260, 530, 121, 41))
        self.pushprevious.setObjectName("pushprevious")
        self.pushnext = QtWidgets.QPushButton(self.centralwidget)
        self.pushnext.setGeometry(QtCore.QRect(450, 530, 131, 41))
        self.pushnext.setObjectName("pushnext")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 872, 22))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        self.pushprevious.clicked.connect(self.show_prev)
        self.pushnext.clicked.connect(self.show_next)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.pushprevious.setText(_translate("MainWindow", "previous"))
        self.pushprevious.setShortcut(_translate("MainWindow", "Left"))
        self.pushnext.setText(_translate("MainWindow", "next"))
        self.pushnext.setShortcut(_translate("MainWindow", "Right"))

    def show_prev(self):
        self.Photo.setPixmap(QtGui.QPixmap("{}GP3_00550.jpg".format(DATA_PATH)))

    def show_next(self):
        self.Photo.setPixmap(QtGui.QPixmap("{}GP3_00551.jpg".format(DATA_PATH)))


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
