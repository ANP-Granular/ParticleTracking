import os
import sys
from PyQt5 import QtCore, QtWidgets, Qt
from PyQt5.QtGui import QPixmap, QPen
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import pandas as pd
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QImage
from track_ui import Ui_MainWindow
from rodnumberwidget import RodNumberWidget

GENERAL_STYLE = "background-color: transparent;" \
                    "color: cyan;"
SELECTED_STYLE = "background-color: transparent;" \
                    "color: white;"
CONFLICT_STYLE = "background-color: transparent;" \
                    "color: red;"


class RodTrackWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.setFocus()
        # This is a bit tricky, AcceptDrops is a required function for
        # drag and drop of QLineEdit textbox contents into another textbox
        # but i set this function below to pass, because the function was not
        # found
        self.setAcceptDrops(True)
        # Initialize
        self.startPos = None
        # scale factor for image
        self.scaleFactor = 1.0
        # tracker of the current image that's displayed
        self.CurrentFileIndex = 0
        self.data_files = None
        self.data_file_name = 'rods_df_{:s}.csv'
        self.color = "black"
        self.image = None
        self.rod_pixmap = None
        self.fileList = None
        self.track = True
        self.edits = None
        # TODO: Associate lines with self.edits (e.g. dict(rod_id: [
        #  positions]))
        # TODO: Redraw overlay everytime a rod_id/rod is changed, activated,
        #  deactivated or has conflicts
        # TODO: Update the saving mechanism (include rod_id)
        # TODO: Update the saving mechanism (button required, changes not
        #  directly saved to disc)

        # Signal to activate actions
        self.ui.pushprevious.clicked.connect(self.show_prev)
        self.ui.pushnext.clicked.connect(self.show_next)
        self.ui.overlay.clicked.connect(self.show_overlay)
        self.ui.RodNumber.clicked.connect(lambda: self.show_overlay(
            with_number=True))
        self.ui.ClearSave.clicked.connect(self.clear_screen)
        self.ui.actionzoom_in.triggered.connect(lambda: self.scaleImage(
            factor=1.25))
        self.ui.actionzoom_out.triggered.connect(lambda: self.scaleImage(
            factor=0.8))
        self.ui.actionopen.triggered.connect(self.file_open)
        self.ui.normalSizeAct.triggered.connect(self.normalSize)
        self.ui.fitToWindowAct.triggered.connect(self.fitToWindow)
        self.ui.Photo.mouseMoveEvent = self.move_mouse

    def file_open(self):
        # opens directory to select image
        fileName, _ = QFileDialog.getOpenFileName(None, 'Open an image', '',
                                                  'Images (*.png *.jpeg '
                                                  '*.jpg)')
        file_name = os.path.split(fileName)[-1]
        # File name without extension
        file_name = os.path.splitext(file_name)[0]
        print('File name:', file_name)
        if fileName:
            # open file as image
            self.image = QImage(fileName)
            if self.image.isNull():
                QMessageBox.information(self, "Image Viewer",
                                        "Cannot load %s." % fileName)
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
                if os.path.isfile(fpath) and f.endswith(('.png', '.jpg',
                                                         '.jpeg')):
                    # Add all image files to a list
                    self.fileList.append(fpath)
            # Sort according to name / ascending order
            self.fileList.sort()
            print('Num of items in list:', len(self.fileList))
            # then the image is displayed in this function NoRods
            self.show_pixmap_NoRods()
            print('Open_file {}:'.format(self.CurrentFileIndex), file_name)
            self.ui.label.setText('File opened: {}'.format(file_name))

    def show_pixmap_NoRods(self):
        pixmap = QtGui.QPixmap.fromImage(self.image)
        self.ui.Photo.setPixmap(pixmap)
        self.scaleFactor = 1.0
        self.ui.fitToWindowAct.setEnabled(True)
        self.updateActions()

    def show_overlay(self, with_number=False):
        items = ("black", "blue", "green", "purple", "red", "yellow")
        col_list = ["particle", "frame", "x1_gp3", "x2_gp3", "y1_gp3",
                    "y2_gp3"]
        while True:
            if self.data_files is not None:
                item, ok = QInputDialog.getItem(None,
                                                "Select a color to display",
                                                "list of colors", items, 0,
                                                False)
                if not ok:
                    return
                else:
                    self.color = item
                    file_found = os.path.exists(self.data_files +
                        self.data_file_name.format(item))
                    if file_found:
                        # Overlay rod position data from the file
                        filename = (self.fileList[self.CurrentFileIndex])
                        file_name = os.path.split(filename)[-1]
                        df_part = pd.read_csv(self.data_files +
                                              self.data_file_name.format(
                                                  self.color),
                                              usecols=col_list)
                        df_part2 = df_part[df_part["frame"] ==
                                           int(file_name[1:4])].reset_index()
                        image = QImage(filename)
                        if with_number:
                            # Overlay with colored bars and
                            self.show_rods(image, df_part2)
                            pass
                        else:
                            # Overlay only with colored bars
                            self.show_pixmap(image, df_part2)
                        return
                    else:
                        # If a folder was selected previously, but no
                        # matching file was found
                        msg = QMessageBox()
                        msg.setIcon(QMessageBox.Warning)
                        msg.setText(
                            f"There was no file for '{item}' found in: "
                            f"'{self.data_files}'")
                        msg.setStandardButtons(
                            QMessageBox.Retry | QMessageBox.Cancel)
                        btn_select = msg.addButton("Select Folder",
                                                   QMessageBox.ActionRole)
                        user_decision = msg.exec()
                        if user_decision == QMessageBox.Cancel:
                            # Stop overlaying
                            return
                        elif msg.clickedButton() == btn_select:
                            # Switch to folder selection
                            self.data_files = None
                            continue
                        else:
                            # Retry color selection
                            continue
            else:
                self.data_files = QFileDialog.getExistingDirectory(
                    None, 'Choose Folder with position data', '') + '/'
                if self.data_files == '/':
                    self.data_files = None
                    return

    def show_pixmap(self, image, df_part2):
        # show_pixmap is called to draw the rods over the image
        self.rod_pixmap = QPixmap(image)
        self.rod_pixmap = self.rod_pixmap.scaledToHeight(
            int(self.rod_pixmap.height() * self.scaleFactor),
            QtCore.Qt.SmoothTransformation)

        painter = QPainter(self.rod_pixmap)
        pen = QPen(Qt.cyan, 3)
        painter.setPen(pen)
        # insert for loop
        if self.edits is not None:
            for rn in self.edits:
                rn.deleteLater()
        self.edits = []
        for ind_rod, value in enumerate(df_part2['particle']):
            # saved rod values must be scaled to fit the image shown
            x1 = df_part2['x1_gp3'][ind_rod] * 10.0 * self.scaleFactor
            x2 = df_part2['x2_gp3'][ind_rod] * 10.0 * self.scaleFactor
            y1 = df_part2['y1_gp3'][ind_rod] * 10.0 * self.scaleFactor
            y2 = df_part2['y2_gp3'][ind_rod] * 10.0 * self.scaleFactor
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

            # Add rod numbers to screen
            ident = RodNumberWidget(self.ui.Photo, str(value), QPoint(int(
                x1), int(y1)))
            ident.setStyleSheet(GENERAL_STYLE)
            ident.rod_id = ind_rod
            ident.activated.connect(self.rod_activated)
            ident.setObjectName(f"rn_{ind_rod}")
            ident.show()
            self.edits.append(ident)
        painter.end()
        self.ui.Photo.setPixmap(self.rod_pixmap)
        self.ui.fitToWindowAct.setEnabled(True)
        self.updateActions()
        self.ui.Photo.mousePressEvent = self.getPixel

    def show_rods(self, image, df_part2):
        # this is a helper function for show_overlay
        pixmap = QPixmap(image)
        pixmap = pixmap.scaledToHeight(int(pixmap.height() * self.scaleFactor),
                                       QtCore.Qt.SmoothTransformation)
        painter = QPainter(pixmap)
        pen = QPen(Qt.cyan, 3)
        painter.setPen(pen)
        self.edits = []
        for ind_rod, value in enumerate(df_part2['particle']):
            x1 = df_part2['x1_gp3'][ind_rod] * 10.0 * self.scaleFactor
            x2 = df_part2['x2_gp3'][ind_rod] * 10.0 * self.scaleFactor
            y1 = df_part2['y1_gp3'][ind_rod] * 10.0 * self.scaleFactor
            y2 = df_part2['y2_gp3'][ind_rod] * 10.0 * self.scaleFactor
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            painter.drawText(int(x1), int(y1), 20, 20, Qt.TextSingleLine,
                             str(value))
            # Line edit box
            s = "s" + str(ind_rod)
            s = QLineEdit(self.ui.Photo)
            s.setDragEnabled(True)
            s.resize(20, 20)
            s.move(int(x2) + 5, int(y2) + 5)
            s.show()
            s.setObjectName("s" + str(ind_rod))
            self.edits.append(s)
        painter.end()
        self.ui.Photo.setPixmap(pixmap)
        # self.ui.Photo.resize(pixmap.width(), pixmap.height())
        self.ui.fitToWindowAct.setEnabled(True)
        self.updateActions()

    def clear_screen(self):
        if self.edits is not None:
            for s in self.edits:
                s.deleteLater()
            self.edits = None
            self.ui.Photo.setPixmap(QtGui.QPixmap.fromImage(self.image))
            self.ui.fitToWindowAct.setEnabled(True)
            self.updateActions()

    # drag enter and drop event are event actions for text box content drag
    # and drop
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("text/plain"):
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        event.accept()
        # self.Tbox.setText(event.mimeData().text())

    def move_mouse(self, mouse_event):
        if self.startPos is not None:
            end = mouse_event.pos()
            pixmap = QPixmap(self.rod_pixmap)
            qp = QPainter(pixmap)
            pen = QPen(Qt.white, 5)
            qp.setPen(pen)
            qp.drawLine(self.startPos, end)
            qp.end()
            self.ui.Photo.setPixmap(pixmap)

    # Note: getPixel gets connected to MousePressed event in show_pixmap
    def getPixel(self, event):
        if self.startPos is None:
            if event.button() == QtCore.Qt.RightButton and \
                    self.edits is not None:
                # Deactivate any active rods
                self.rod_activated(-1)
            elif event.button() == QtCore.Qt.LeftButton:
                self.startPos = event.pos()
        else:
            if event.button() == QtCore.Qt.RightButton:
                # Abort current line drawing
                self.startPos = None
                pixmap = QPixmap(self.rod_pixmap)
                self.ui.Photo.setPixmap(pixmap)
            else:
                # Finish line and save it
                self.save_line(self.startPos, event.pos())
                self.startPos = None

    def save_line(self, start, end):
        # Get intended rod number from user
        num, ok = QInputDialog.getInt(self.ui.Photo, 'Choose a rod to '
                                                     'replace', 'Rod number')
        filename = (self.fileList[self.CurrentFileIndex])
        file_name = os.path.split(filename)[-1]
        df_part = pd.read_csv(self.data_files + self.data_file_name.format(
            self.color), index_col=0)
        if ok:
            # num is the number of the rod
            df_part.loc[(df_part.frame == int(file_name[1:4])) &
                        (df_part.particle == num), "x1_gp3"] = \
                start.x()/10.0/self.scaleFactor
            df_part.loc[(df_part.frame == int(file_name[1:4])) &
                        (df_part.particle == num), "x2_gp3"] = \
                end.x()/10.0/self.scaleFactor
            df_part.loc[(df_part.frame == int(file_name[1:4])) &
                        (df_part.particle == num), "y1_gp3"] = \
                start.y()/10.0/self.scaleFactor
            df_part.loc[(df_part.frame == int(file_name[1:4])) &
                        (df_part.particle == num), "y2_gp3"] = \
                end.y()/10.0/self.scaleFactor
            df_part.to_csv(self.data_files + self.data_file_name.format(
                self.color), index_label="")

    def show_next(self):
        if self.fileList:
            try:
                self.CurrentFileIndex += 1  # Increments file index
                # Chooses next image with specified extension
                filename = (self.fileList[self.CurrentFileIndex])
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
                    self.ui.Photo.setPixmap(QtGui.QPixmap.fromImage(
                        image_next))
                    self.scaleFactor = 1.0
                    self.ui.fitToWindowAct.setEnabled(True)
                    self.updateActions()
                    print('Next_file {}:'.format(self.CurrentFileIndex),
                          file_name)
                    # Label stuff
                    self.ui.label.setText('File: {}'.format(file_name))
                    # self.update()
            except IndexError:
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
                # Chooses previous image with specified extension
                filename = (self.fileList[self.CurrentFileIndex])
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
                    self.ui.Photo.setPixmap(QtGui.QPixmap.fromImage(
                        image_prev))
                    self.scaleFactor = 1.0
                    self.ui.fitToWindowAct.setEnabled(True)
                    self.updateActions()
                    print('Prev_file {}:'.format(self.CurrentFileIndex), file_name)
                    self.ui.label.setText('File: {}'.format(file_name))
            except IndexError:
                # the iterator has finished, restart it
                self.CurrentFileIndex = 0
                self.show_prev()
        else:
            # no file list found, select an image file
            self.file_open()

    def normalSize(self):
        self.ui.Photo.adjustSize()
        self.scaleFactor = 1.0

    def fitToWindow(self):
        fitToWindow = self.ui.fitToWindowAct.isChecked()
        self.ui.scrollArea.setWidgetResizable(fitToWindow)
        if not fitToWindow:
            self.normalSize()
        self.updateActions()

    def updateActions(self):
        self.ui.actionzoom_in.setEnabled(not
                                         self.ui.fitToWindowAct.isChecked())
        self.ui.actionzoom_in.setEnabled(not
                                         self.ui.fitToWindowAct.isChecked())
        self.ui.normalSizeAct.setEnabled(not
                                         self.ui.fitToWindowAct.isChecked())

    def scaleImage(self, factor):
        if self.image is None:
            return
        self.scaleFactor = self.scaleFactor * factor
        old_pixmap = QtGui.QPixmap.fromImage(self.image)
        new_pixmap = old_pixmap.scaledToHeight(
            int(old_pixmap.height() * self.scaleFactor),
            QtCore.Qt.SmoothTransformation)
        self.ui.Photo.setPixmap(new_pixmap)

        # Update rod number positions
        if self.edits is not None:
            for rn in self.edits:
                rn.move(QPoint(int(rn.x()*factor), int(rn.y()*factor)))

        if self.rod_pixmap is not None:
            self.rod_pixmap = new_pixmap
        # Disable zoom, if zoomed too much
        self.ui.actionzoom_in.setEnabled(self.scaleFactor < 9.0)
        self.ui.actionzoom_out.setEnabled(self.scaleFactor > 0.11)

    def adjustScrollBar(self, scrollBar, factor):
        scrollBar.setValue(int(factor * scrollBar.value() +
                               ((factor - 1) * scrollBar.pageStep() / 2)))

    def setAcceptDrops(self, param):
        pass

    def rod_activated(self, rod_id):
        # A new rod was activated for position editing. Deactivate all others.
        for rod in self.edits:
            if rod.rod_id != rod_id:
                rod.deactivate_rod()

    def check_rod_conflicts(self, rod_id):
        # TODO: mark numbering conflicts in CONFLICT_STYLE
        pass

    def check_exchange(self, drop_position):
        # TODO: check where rod number was dropped and whether an exchange
        #  is needed.
        pass


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_window = RodTrackWindow()
    main_window.show()
    sys.exit(app.exec_())
