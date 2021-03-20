import sys
from PyQt5.QtGui import QMouseEvent
from PyQt5 import QtGui
from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QPainter, QImage
from PyQt5.QtWidgets import QApplication, QMainWindow


image_path = "0100.jpg"


class Window(QMainWindow):

    def __init__(self):
        super().__init__()
        self.image = QImage(image_path)
        # self.showFullScreen()
        self.startPos = None
        self.rect = QRect()


    def mousePressEvent(self, event):
        self.startPos = event.pos()
        self.rect = QRect(self.startPos, self.startPos)
        self.update()

    def paintEvent(self, event):
        pen = QtGui.QPen()
        pen.setWidth(3)
        pen.setColor(QtGui.QColor(255, 0, 0))

        brush = QtGui.QBrush()
        brush.setColor(QtGui.QColor(255, 0, 0))
        # brush.setStyle(Qt.SolidPattern)
        painter = QPainter(self)
        painter.drawImage(0, 0, self.image)
        painter.setBrush(brush)
        painter.setPen(pen)
        if not self.rect.isNull():
            painter.drawRect(self.rect)
            painter.drawText(self.startPos.x(), self.startPos.y(), 20, 20, Qt.TextSingleLine, '22')
        painter.end()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    app.exec()
    """
        # const QRect rectangle = QRect(0, 0, 100, 50);
        # QRect boundingRect;
        # painter.drawText(rectangle, 0, tr("Hello"), & boundingRect);

        # QPen
        # pen = painter.pen();
        # pen.setStyle(Qt::DotLine);
        # painter.setPen(pen);
        # painter.drawRect(boundingRect.adjusted(0, 0, -pen.width(), -pen.width()));
    """
