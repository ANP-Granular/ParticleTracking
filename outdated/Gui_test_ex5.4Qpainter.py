from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QRect, Qt, QPoint
from PyQt5.QtGui import QImage, QPainter, QPen, QPixmap, QPalette
from PyQt5.QtWidgets import *
import sys
import os


class Ui_MainWindow(object):
    # Constructor
    def __init__(self):
        # Initialize
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.top = 300
        self.left = 50
        self.width = 720
        self.height = 640
        self.drawing = False
        self.brushsize = 2
        self.rect = QRect()
        self.startPos = QPoint()

    # Main Window
    def setup_ui(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(self.width, self.height)
        MainWindow.setFocus()
        self.centralwidget.setObjectName("centralwidget")
        self.centralwidget.setFocus()
        # Label to display content
        self.Photo = QtWidgets.QLabel(self.centralwidget)
        self.Photo.setBackgroundRole(QPalette.Base)
        self.Photo.setGeometry(QtCore.QRect(50, 0, self.width - 10, self.height - 10))
        self.Photo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.Photo.setScaledContents(True)
        self.Photo.setObjectName("Photo")
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
        # Action properties
        self.actionopen = QtWidgets.QAction(MainWindow)
        self.actionopen.setObjectName("actionopen")
        # Add actions to menu
        self.menufile.addAction(self.actionopen)
        self.menubar.addAction(self.menufile.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())
        self.menubar.addAction(self.menuView.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        # Signal to activate actions
        self.actionopen.triggered.connect(self.file_open)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        # Information about actions in menu
        self.menufile.setTitle(_translate("MainWindow", "File"))
        self.menuEdit.setTitle(_translate("MainWindow", "Edit"))
        self.menuView.setTitle(_translate("MainWindow", "View"))
        self.actionopen.setText(_translate("MainWindow", "open"))
        self.actionopen.setStatusTip(_translate("MainWindow", "opens new file "))
        self.actionopen.setShortcut(_translate("MainWindow", "Ctrl+O"))

    def file_open(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(None, 'QFileDialog.getOpenFileName()', '',
                                                  'Images (*.png *.jpeg *.jpg)', options=options)
        file_name = os.path.split(fileName)[-1]
        file_name = os.path.splitext(file_name)[0]  # File name without extension
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
            self.Photo.setPixmap(QtGui.QPixmap.fromImage(image))
            self.Photo.setScaledContents(True)
            # Call mouse press event to get points
            self.Photo.mousePressEvent = self.getPos
            self.Photo.paintEvent = self.drawLines  # <<<----- make this callable

    def getPos(self, event):
        self.startPos = event.pos()
        self.rect = QRect(self.startPos, self.startPos)
        print('pos_x:{}, pos_y:{}'.format(self.startPos.x(), self.startPos.y()))

    def drawLines(self, event):  # <<<----- make this callable
        self.pen = QtGui.QPen()
        self.pen.setWidth(3)
        self.pen.setColor(QtGui.QColor(255, 0, 0))
        self.brush = QtGui.QBrush()
        self.brush.setColor(QtGui.QColor(255, 0, 0))
        self.painter = QPainter(self)
        self.painter.drawImage(0, 0, self.Photo)
        self.painter.setBrush(self.brush)
        self.painter.setPen(self.pen)
        if not self.rect.isNull():
            self.painter.drawRect(self.rect)
            self.painter.drawText(self.startPos.x(), self.startPos.y(), 20, 20, Qt.TextSingleLine, '1')
        self.painter.end()


# Create an instance of QApplication and object of Window class
if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setup_ui(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
