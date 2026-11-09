@echo off
echo === MOJ Compresor - generando ejecutable portable ===
python -m pip install --upgrade py7zr pyppmd pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name "MOJ_Compresor" --collect-all py7zr --collect-all pyppmd --collect-all pybcj --collect-all pyzstd --collect-all inflate64 --collect-all multivolumefile moj_compresor.py
echo.
echo Listo: dist\MOJ_Compresor.exe
pause
