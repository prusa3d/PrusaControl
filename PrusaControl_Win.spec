# -*- mode: python -*-

block_cipher = None

import sys
sys.modules['FixTk'] = None

a = Analysis(['main.py'],
             pathex=['C:\\projects\\slave\\PrusaControl_Windows\\build'],
             binaries=[],
             datas=[
             ('C:\\projects\\slave\\PrusaControl_Windows\\build\\data', 'data'),
             ('C:\\projects\\slave\\PrusaControl_Windows\\build\\translation', 'translation')
             #,('C:\\projects\\slave\\PrusaControl_Windows\\build\\tools', 'tools')
             ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter', 'lib2to3', 'PyQt4.QtNetwork', 'PyQt4.QtSql', 'PyQt4.QtSvg', 'PyQt4.QtXml'],
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
          upx=True,
          console=False ,
          icon='data\\icon\\favicon.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='PrusaControl')
