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

import site

import PyInstaller.utils.hooks as hookutils
from PyInstaller import compat

binaries = []
datas = []
hiddenimports = []

datas += hookutils.collect_data_files(
    "extensions.detection", include_py_files=True, excludes=["__pyinstaller"]
)

for dir in site.getsitepackages():
    if dir.endswith("site-packages"):
        site_packages = dir
        break

# Collection of binary files for torch/torchaudio/torchvision that were missed
# by their pyinstaller hooks
if compat.is_win:
    binaries += [
        (site_packages + "/torchvision/image.pyd", "./torchvision"),
    ]
elif compat.is_linux:
    binaries += [
        (
            site_packages + "/torchaudio/lib/libtorchaudio.so",
            "./torchaudio/lib",
        ),
        # appears to have been removed in newer versions of torchaudio
        # (site_packages + '/torchaudio/lib/libtorchaudio_ffmpeg.so', './torchaudio/lib'),  # noqa: E501
        (
            site_packages + "/torchaudio/lib/libtorchaudio_sox.so",
            "./torchaudio/lib",
        ),
        (site_packages + "/torchvision/image.so", "./torchvision"),
    ]
elif compat.is_darwin:
    binaries += hookutils.collect_dynamic_libs("torch")
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
        # ImportError: dlopen(/Users/.../ParticleTracking/RodTracker/dist/unix/RodTracker.app/Contents/Resources/cv2/cv2.abi3.so, 2): Library not loaded: @rpath/libpng16.16.dylib  # noqa: E501
        #   Referenced from: /Users/.../ParticleTracking/RodTracker/dist/unix/RodTracker.app/Contents/Frameworks/PIL/__dot__dylibs/libfreetype.6.dylib  # noqa: E501
        #   Reason: Incompatible library version: libfreetype.6.dylib requires version 57.0.0 or later, but libpng16.16.dylib provides version 56.0.0  # noqa: E501
        # (site_packages + '/torchvision/image.so', './torchvision'),
    ]
else:
    hookutils.logger.error(
        "Running on unsupported OS! Binary collection for 'torch' might not "
        "work correctly."
    )
