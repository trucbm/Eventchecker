@echo off
setlocal

REM Go to project root (two levels up from this script)
pushd "%~dp0\\..\\.."

REM Create venv
if not exist ".venv" (
  py -3 -m venv .venv
)

call .venv\Scripts\activate.bat

REM Install deps
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Clean old build output (in case files are locked)
if exist "dist\EventInspector" rmdir /s /q "dist\EventInspector"
if exist "build\EventInspector" rmdir /s /q "build\EventInspector"

REM Build portable EXE folder
pip install pyinstaller PySide6
pyinstaller --noconfirm --clean --windowed --icon assets\app.ico --name "EventInspector" ^
  --collect-submodules "engineio" ^
  --collect-submodules "socketio" ^
  --add-data "Default event + Default Params.xlsx;." ^
  desktop_app.py

REM Output: dist\EventInspector\EventInspector.exe
endlocal
popd
