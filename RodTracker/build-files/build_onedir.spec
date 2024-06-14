# -*- mode: python ; coding: utf-8 -*-
# TODO: make exe( ... name='RodTrackerApp',...) dependent on the platform
#       i.e. RodTracker (Win, Darwin) & RodTrackerApp (linux)
# TODO: remove additional data/binary/module collections that should be handled
#       by extensions that require those files to function

import platform
import site
from typing import List

from RodTracker import INSTALLED_EXTS_FILE
from RodTracker._version import __version__

block_cipher = None
binaries = []
icon_file = None
version_info = None
site_packages = None

for dir in site.getsitepackages():
    if dir.endswith("site-packages"):
        site_packages = dir
        break

if platform.system() == "Darwin":
    from PyInstaller.utils.hooks import collect_dynamic_libs

    binaries += collect_dynamic_libs("torch")
    binaries += [
        (
            site_packages + "/torchaudio/lib/libtorchaudio.so",
            "./torchaudio/lib",
        ),
        (
            site_packages + "/torchaudio/lib/libtorchaudio_sox.so",
            "./torchaudio/lib",
        ),
        # FIXME: Causes the application to crash because of a version mismatch:
        # ImportError: dlopen(/Users/.../ParticleTracking/RodTracker/dist/unix/RodTracker.app/Contents/Resources/cv2/cv2.abi3.so, 2): Library not loaded: @rpath/libpng16.16.dylib
        #   Referenced from: /Users/.../ParticleTracking/RodTracker/dist/unix/RodTracker.app/Contents/Frameworks/PIL/__dot__dylibs/libfreetype.6.dylib
        #   Reason: Incompatible library version: libfreetype.6.dylib requires version 57.0.0 or later, but libpng16.16.dylib provides version 56.0.0
        # (site_packages + '/torchvision/image.so', './torchvision'),
    ]
    icon_file = "../src/RodTracker/resources/icon_macOS.icns"
elif platform.system() == "Windows":
    icon_file = "../src/RodTracker/resources/icon_windows.ico"
    version_info = "version_info.txt"
    binaries += [
        (site_packages + "/torchvision/image.pyd", "./torchvision"),
    ]
elif platform.system() == "Linux":
    binaries += [
        (
            site_packages + "/torchaudio/lib/libtorchaudio.so",
            "./torchaudio/lib",
        ),
        # appears to have been removed in newer versions of torchaudio
        # (site_packages + '/torchaudio/lib/libtorchaudio_ffmpeg.so', './torchaudio/lib'),
        (
            site_packages + "/torchaudio/lib/libtorchaudio_sox.so",
            "./torchaudio/lib",
        ),
        (site_packages + "/torchvision/image.so", "./torchvision"),
    ]

# read which extensions are installed and for adding as hidden imports
with open(INSTALLED_EXTS_FILE, "r") as f:
    ext_imports: List[str] = [
        "extensions." + line.strip() for line in f.readlines()
    ]

a = Analysis(
    ["../src/RodTracker/main.py"],
    pathex=["."],
    binaries=binaries,
    datas=[
        ("../src/RodTracker/resources/example_data", "./example_data"),
        (site_packages + "/pulp", "./pulp"),
    ],
    hiddenimports=[
        *ext_imports,
        "skimage.transform.hough_transform",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
a.datas += extensions_toc
a.datas += docs_toc


pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RodTrackerApp",
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
    name="RodTracker",
)

app = BUNDLE(
    coll,
    name="RodTracker.app",
    icon=icon_file,
    bundle_identifier=None,
    version=__version__,
)
