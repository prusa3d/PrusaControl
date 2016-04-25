DEL /F /Q c:\projects\slave\Windows_All\build\build\ c:\projects\slave\Windows_All\build\dist\
pyinstaller -y --windowed --name=PrusaControl c:\projects\slave\Windows_All\build\main.py
xcopy gui dist\PrusaControl\gui\
xcopy translation dist\PrusaControl\translation\