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
pip install pyinstaller PySide6 qtpy
pyinstaller --noconfirm --clean --windowed --icon assets\\app.ico --name "EventInspector" ^
  --collect-submodules "engineio" ^
  --collect-submodules "socketio" ^
  --collect-submodules "webview" ^
  --collect-submodules "androguard.core" ^
  --collect-data "androguard" ^
  --hidden-import "androguard.core.axml" ^
  --hidden-import "qtpy" ^
  --hidden-import "qtpy.QtCore" ^
  --hidden-import "qtpy.QtGui" ^
  --hidden-import "qtpy.QtWidgets" ^
  --hidden-import "qtpy.QtNetwork" ^
  --hidden-import "qtpy.QtWebChannel" ^
  --hidden-import "qtpy.QtWebEngineCore" ^
  --hidden-import "qtpy.QtWebEngineWidgets" ^
  --hidden-import "PySide6.QtCore" ^
  --hidden-import "PySide6.QtGui" ^
  --hidden-import "PySide6.QtWidgets" ^
  --hidden-import "PySide6.QtNetwork" ^
  --hidden-import "PySide6.QtWebChannel" ^
  --hidden-import "PySide6.QtWebEngineCore" ^
  --hidden-import "PySide6.QtWebEngineWidgets" ^
  --hidden-import "shiboken6" ^
  --add-data "Default event + Default Params.xlsx;." ^
  --add-data "sdk_check_presets.json;." ^
  --add-data "remote_update_config_v250.json;." ^
  --add-data "services_checker\app.py;services_checker" ^
  --add-data "services_checker\axml_fallback.py;services_checker" ^
  --add-data "services_checker\bundletool-all-1.18.1.jar;services_checker" ^
  --add-data "services_checker\apk_check_presets.json;services_checker" ^
  --add-data "services_checker\gradle_check_presets.json;services_checker" ^
  --add-data "services_checker\podfile_check_presets.json;services_checker" ^
  --add-data "services_checker\manifest_check_presets.json;services_checker" ^
  --add-data "services_checker\my-key.keystore;services_checker" ^
  desktop_app.py

REM Build installer (requires Inno Setup installed and ISCC on PATH)
ISCC build\windows\EventChecker.iss

endlocal
popd
