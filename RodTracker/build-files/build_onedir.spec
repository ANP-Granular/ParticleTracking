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

# -*- mode: python ; coding: utf-8 -*-
import platform
from pathlib import Path
from typing import List

from PyInstaller.building.api import EXE, PYZ, COLLECT
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.datastruct import Tree
from PyInstaller.building.osx import BUNDLE

from RodTracker import APPNAME, INSTALLED_EXTS_FILE
from RodTracker._version import __version__

block_cipher = None
icon_file = None
version_info = None

if platform.system() == "Darwin":
    icon_file = "../src/RodTracker/resources/icon_macOS.icns"
elif platform.system() == "Windows":
    icon_file = "../src/RodTracker/resources/icon_windows.ico"
    version_info = "version_info.txt"

# read which extensions are installed and for adding as hidden imports
with open(INSTALLED_EXTS_FILE, "r") as f:
    ext_imports: List[str] = []
    ext_hooks: List[str] = []
    ext_path = Path("./src/extensions")
    for line in f.readlines():
        ext_name = line.strip()
        ext_imports.append("extensions." + ext_name)
        hook_path = (ext_path / (ext_name + "/__pyinstaller")).resolve()
        if hook_path.exists():
            ext_hooks.append(str(hook_path))

a = Analysis(
    ["../src/RodTracker/main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("../src/RodTracker/resources/example_data", "./example_data"),
    ],
    hiddenimports=[
        *ext_imports,
        # TODO: is this still needed? Couldn't find occurences in RodTracker or
        #       ParticleDetection code
        "skimage.transform.hough_transform",
    ],
    hookspath=[*ext_hooks],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["sphinx"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

docs_toc = Tree("../docs/build/html", prefix="docs", excludes=[])
rodtracker_toc = Tree(
    "./src/RodTracker",
    prefix="RodTracker",
    excludes=["__pycache__", "*.pyc", "*.ui", "example_data"],
)
extensions_toc = Tree(
    "./src/extensions", prefix="extensions", excludes=["__pycache__", "*.pyc"]
)
a.datas += rodtracker_toc
a.datas += docs_toc


pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APPNAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
    version=version_info,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APPNAME,
)

app = BUNDLE(
    coll,
    name=APPNAME + ".app",
    icon=icon_file,
    bundle_identifier=None,
    version=__version__,
)
