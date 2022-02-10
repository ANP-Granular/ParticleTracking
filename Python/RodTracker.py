import os
import sys

import inspect

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 

from PyQt5 import QtWidgets

from Python.backend import logger as al
from Python.ui import mainwindow as mw


ICON_PATH = "./resources/icon_main.ico"

HAS_SPLASH = False
try:
    import pyi_splash
    HAS_SPLASH = True
except ModuleNotFoundError:
    # Application not bundled
    HAS_SPLASH = False


if __name__ == "__main__":
    if HAS_SPLASH:
        pyi_splash.update_text("Updating environment...")
    if not os.path.exists(al.TEMP_DIR):
        os.mkdir(al.TEMP_DIR)
    if HAS_SPLASH:
        pyi_splash.update_text("Loading UI...")

    app = QtWidgets.QApplication(sys.argv)
    main_window = mw.RodTrackWindow()

    if HAS_SPLASH:
        # Close the splash screen.
        pyi_splash.close()

    main_window.show()
    sys.exit(app.exec_())
