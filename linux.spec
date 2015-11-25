# -*- mode: python -*-
from kivy.tools.packaging.pyinstaller_hooks import install_hooks 
install_hooks(globals()) 

a = Analysis(['main.py'],
             pathex=['/home/tibor/projects/PrusaControll'],
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='main',
          debug=False,
          strip=None,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='main')
