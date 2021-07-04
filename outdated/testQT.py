import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import os

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.title = 'Document Analysis'
        self.left = 30
        self.top = 30
        self.width = 640
        self.height = 480
        self.imagenumber=0
        self.initUI()

    def keyPressEvent(self, event):
        key=event.key()
        if key==Qt.Key_Right:
            self.imagenumber=self.imagenumber+1
            self.showimage(self.imagenumber)
            # self.show()
        else:
            super(self).keyPressEvent(event)

    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.label = QLabel(self)
        layout.addWidget(self.label)

        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.showimage(0)
        self.show()

    def showimage(self,imagenumber):
        # label = QLabel(self)

        directory = "C:\\Users\\Meera Subramanian\\PycharmProjects\\pythonProject\\pictures"
        imagelist = os.listdir(directory)
        pixmap = QPixmap(directory + '\\' + imagelist[imagenumber])

        # label.setPixmap(pixmap)
        self.label.setPixmap(pixmap)
        self.resize(pixmap.width() + 500, pixmap.height())
        # self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())