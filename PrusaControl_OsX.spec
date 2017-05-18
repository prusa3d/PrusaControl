# -*- mode: python -*-
# /opt/local/Library/Frameworks/Python.framework/Versions/3.5/bin/pyinstaller PrusaControl_OsX.spec

block_cipher = None

import sys
sys.modules['FixTk'] = None

a = Analysis(['main.py'],
             pathex=['/Users/prusa3d/Documents/projects/tmp/PrusaControl'],
             binaries=[],
             datas=[
             ('/Users/prusa3d/Documents/projects/tmp/prusacontrol/data', 'data'),
             ('/Users/prusa3d/Documents/projects/tmp/prusacontrol/translation', 'translation')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter', 'PyQt4.QtNetwork', 'PyQt4.QtSql', 'PyQt4.QtSvg', 'PyQt4.QtXml'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='PrusaControl',
          debug=False,
          strip=False,
          upx=False,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='PrusaControl')
app = BUNDLE(coll,
             name='PrusaControl.app',
             icon='/Users/prusa3d/Documents/projects/tmp/prusacontrol/data/icon/favicon.ico',
             bundle_identifier=None)
