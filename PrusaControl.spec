# -*- mode: python -*-

block_cipher = None


a = Analysis(['main.py'],
             pathex=['C:\\projects\\prusacontrol_new'],
             binaries=[],
             datas=[
		('C:\\projects\\prusacontrol_new\\data', 'data'),
		('C:\\projects\\prusacontrol_new\\translation', 'translation'),
		('C:\\projects\\prusacontrol_new\\tools\\Slic3r-Lite', 'tools\\Slic3r-Lite')
		],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=['tcl', 'tkinter', 'lib2to3', 'PyQt5.QtSvg', 'PyQt5.QtPrintSupport'],
             win_no_prefer_redirects=True,
             win_private_assemblies=True,
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
          console=False , icon='data\\icon\\favicon.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name='PrusaControl')
