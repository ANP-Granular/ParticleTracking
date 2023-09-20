# -*- mode: python ; coding: utf-8 -*-
# TODO: make exe( ... name='RodTrackerApp',...) dependent on the platform
#       i.e. RodTracker (Win, Darwin) & RodTrackerApp (linux)

import platform
import pulp
from RodTracker._version import __version__

block_cipher = None
binaries = []
icon_file = None

if platform.system() == "Darwin":
    from PyInstaller.utils.hooks import collect_dynamic_libs
    binaries += collect_dynamic_libs('torch')
    icon_file = '../src/RodTracker/resources/icon_macOS.icns'
elif platform.system() == "Windows":
    icon_file = '../src/RodTracker/resources/icon_windows.ico'

a = Analysis(['../src/RodTracker/RodTracker.py'],
             pathex=['.'],
             binaries=binaries,
             datas=[('../src/RodTracker/ui/*', './RodTracker/ui'),
             ('../src/RodTracker/backend/*', './RodTracker/backend'),
             ('../src/RodTracker/resources/*', './RodTracker/resources'),
             ('../../docs/build/html/', './docs/'),
             ('../../docs/build/html/_modules', './docs/_modules'),
             ('../../docs/build/html/_sources', './docs/_sources'),
             ('../../docs/build/html/_static', './docs/_static'),
             (pulp.__path__[0], './pulp')],
             hiddenimports=[],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure,
          a.zipped_data,
          cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='RodTrackerApp',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None ,
          icon=icon_file,
          version='version_info.txt',
          )

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='RodTracker')

app = BUNDLE(
    coll,
    name="RodTracker.app",
    icon=icon_file,
    bundle_identifier=None,
    version=__version__,
)
