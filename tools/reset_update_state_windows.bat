@echo off
setlocal

set "APP_SUPPORT_DIR=%LOCALAPPDATA%\EventInspector"
set "STATE_FILE=%APP_SUPPORT_DIR%\update_state_v230.json"
set "CONFIG_FILE=%APP_SUPPORT_DIR%\remote_update_config_v230.json"
set "UPDATES_DIR=%APP_SUPPORT_DIR%\updates_v230"

echo Event Inspector update reset (Windows)
echo Target folder: %APP_SUPPORT_DIR%
echo.

if exist "%STATE_FILE%" (
  del /f /q "%STATE_FILE%"
  echo Removed: %STATE_FILE%
) else (
  echo Skip (not found): %STATE_FILE%
)

if exist "%CONFIG_FILE%" (
  del /f /q "%CONFIG_FILE%"
  echo Removed: %CONFIG_FILE%
) else (
  echo Skip (not found): %CONFIG_FILE%
)

if exist "%UPDATES_DIR%" (
  rmdir /s /q "%UPDATES_DIR%"
  echo Removed: %UPDATES_DIR%
) else (
  echo Skip (not found): %UPDATES_DIR%
)

echo.
echo Done.
echo Next steps:
echo 1. Open Event Inspector again
echo 2. Press Check Update
pause
