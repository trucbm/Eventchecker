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

REM Build EXE
pip install pyinstaller PySide6
pyinstaller --noconfirm --clean --windowed --icon assets\\app.ico --name "EventInspector" ^
  --collect-submodules "engineio" ^
  --collect-submodules "socketio" ^
  --add-data "Default event + Default Params.xlsx;." ^
  --add-data "remote_update_config.json;." ^
  desktop_app.py

REM Build installer (requires Inno Setup installed and ISCC on PATH)
ISCC build\windows\EventChecker.iss

endlocal
popd
