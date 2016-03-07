DEL /F /Q c:\projects\slave\Windows_All\build\build\ c:\projects\slave\Windows_All\build\dist\
pyinstaller -y --windowed --name=PrusaControll c:\projects\slave\Windows_All\build\main.py
