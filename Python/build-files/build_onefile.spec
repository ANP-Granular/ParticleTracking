# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['../src/RodTracker/RodTracker.py'],
             pathex=['.'],
             binaries=[],
             datas=[('../src/RodTracker/ui/*', './RodTracker/ui'),
             ('../src/RodTracker/backend/*', './RodTracker/backend'),
             ('../src/RodTracker/resources/*', './RodTracker/resources'),
             ('../README.md', '.')],
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

splash = Splash('../src/RodTracker/resources/splash.png',
                binaries=a.binaries,
                datas=a.datas,
                text_pos=(250, 450),
                text_size=12,
                text_color='white',
                text_default='Initializing ...',
                minify_script=True)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          splash,
          splash.binaries,
          [],
          name='RodTracker',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None,
          icon='../src/RodTracker/resources/icon_main.ico')
