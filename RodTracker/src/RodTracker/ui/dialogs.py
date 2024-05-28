# Copyright (c) 2023-24 Adrian Niemann, and others
#
# This file is part of RodTracker.
# RodTracker is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RodTracker is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RodTracker. If not, see <http://www.gnu.org/licenses/>.

"""**TBD**"""

import platform

from PyQt5 import QtGui, QtWidgets

import RodTracker.backend.file_locations as fl
from RodTracker import APPNAME
from RodTracker._version import __date__, __version__


def show_warning(text: str):
    """Display a warning with custom text and Ok button."""
    msg = QtWidgets.QMessageBox()
    msg.setWindowIcon(QtGui.QIcon(fl.icon_path()))
    msg.setIcon(QtWidgets.QMessageBox.Warning)
    msg.setWindowTitle(APPNAME)
    msg.setText(text)
    msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msg.exec()


def show_about(parent: QtWidgets.QWidget):
    dependency_format = """
    <tr>
        <td width="50">
            <p><a href="{}">{}</a>:</p>
        </td>
        <td width="150">{}</td>
        <td width="200"><p>{}</p></td>
    </tr>
    """
    dependencies = [
        # (link, name, version, license(s))
        (
            "https://docutils.sourceforge.io/",
            "docutils",
            "0.18.1",
            "BSD 2, GPL, PSF",
        ),
        ("https://github.com/mtkennerly/dunamai", "dunamai", "1.19.0", "MIT"),
        ("https://github.com/pycqa/flake8", "flake8", "6.1.0", "MIT"),
        (
            "https://github.com/python/importlib_resources",
            "importlib-resources",
            "6.1.0",
            "Apache-2.0",
        ),
        ("https://material.io/", "Material Design", "2", "Apache-2.0"),
        ("https://matplotlib.org/", "matplotlib", "3.8.0", "matplotlib"),
        (
            "https://myst-parser.readthedocs.io/",
            "MyST-Parser",
            "2.0.0",
            "MIT",
        ),
        ("https://numpy.org/", "NumPy", "1.26.0", "BSD 3"),
        ("https://pandas.pydata.org/", "Pandas", "2.1.1", "BSD 3"),
        (
            "https://github.com/ANP-Granular/ParticleTracking",
            "particledetection",
            "0.4.0",
            "GPLv3",
        ),
        ("https://python-pillow.org/", "Pillow", "10.0.1", "HPND"),
        (
            "https://github.com/platformdirs/platformdirs",
            "platformdirs",
            "3.11.0",
            "MIT",
        ),
        ("https://www.pyinstaller.org/", "PyInstaller", "6.0.0", "GPLv2+"),
        (
            "https://www.riverbankcomputing.com/software/pyqt",
            "PyQt3D",
            "5.15.6",
            "GPLv3+",
        ),
        (
            "https://www.riverbankcomputing.com/software/pyqt",
            "PyQt5",
            "5.15.9",
            "GPLv3+",
        ),
        ("https://docs.pytest.org/", "pytest", "7.4.2", "MIT"),
        (
            "https://github.com/pytest-dev/pytest-cov",
            "pytest-cov",
            "4.1.0",
            "MIT",
        ),
        (
            "https://github.com/pytest-dev/pytest-qt",
            "pytest-qt",
            "4.2.0",
            "MIT",
        ),
        ("https://www.qt.io", "Qt5", "5.15.2", "LGPLv3"),
        ("https://www.sphinx-doc.org/", "Sphinx", "7.2.6", "BSD"),
        (
            "https://sphinx-rtd-theme.readthedocs.io/",
            "sphinx_rtd_theme",
            "1.3.0",
            "MIT",
        ),
    ]
    dependency_string = """"""
    for dep in dependencies:
        dependency_string += dependency_format.format(*dep)

    about_txt = (
        """
        <style>
            table { background-color: transparent; }
            a { text-decoration:none; font-weight:bold; }
        </style>
        <table border="0" cellpadding="0" cellspacing="5" width="400"
        align="left" style="margin-top:0px;">
            <tr>
                <td width="200", colspan="2"> <h3>Version:</h3> </td>
        """
        + """   <td width="200"> <p> {} </p> </td>
            </tr>
            <tr>
                <td width="200", colspan="2"> <h3>Date:</h3> </td>
                <td width="200"> <p> {} </p> </td>
            </tr>
        """.format(
            __version__, __date__
        )
        + """
        <tr>
            <td width="200", colspan="2"> <h3><br>Developers:<br></h3> </td>
            <td width="200">
                <p> Adrian Niemann <br>
                    Dmitry Puzyrev <br>
                    Meera Subramanian <br>
                    Adithya Viswanathan
                </p>
            </td>
        </tr>
        <tr>
            <td width="200", colspan="2"> <h3>License:</h3> </td>
            <td width="200">
                <p><a href="https://www.gnu.org/licenses/gpl-3.0.en.html">
                GPLv3</a>
                </p>
            </td>
        </tr>
        <tr>
            <td width="400", colspan="3"> <br><h3>3rd Party Software:</h3>
            <p> This application either uses code and tools from the
                following projects in part or in their entirety as deemed
                permissible by each project's open-source license.</p>
            </td>
        </tr>
        """
        + dependency_string
        + """
        </table>
        <br>
        <br>
        <p>
            Copyright © 2023-2024 Adrian Niemann, Dmitry Puzyrev, and others
        </p>
        """
    )
    if platform.system() == "Darwin":
        QtWidgets.QMessageBox.about(parent, "About RodTracker", about_txt)
    else:
        # Using the logo instead of the icon
        _ = QtWidgets.QWidget()
        _.setWindowIcon(QtGui.QIcon(fl.logo_path()))
        QtWidgets.QMessageBox.about(_, f"About {APPNAME}", about_txt)
