@echo off
setlocal

set "APP_SUPPORT_DIR=%LOCALAPPDATA%\EventInspector"
set "STATE_FILE=%APP_SUPPORT_DIR%\update_state_v230.json"
set "CONFIG_FILE=%APP_SUPPORT_DIR%\remote_update_config_v230.json"
set "UPDATES_DIR=%APP_SUPPORT_DIR%\updates_v230"
set "MANIFEST_URL=https://raw.githubusercontent.com/trucbm/Eventchecker/main/Updates_2_3/remote_manifest.json"

echo Event Inspector update reset (Windows)
echo Target folder: %APP_SUPPORT_DIR%
echo.

if not exist "%APP_SUPPORT_DIR%" mkdir "%APP_SUPPORT_DIR%"

if exist "%STATE_FILE%" (
  del /f /q "%STATE_FILE%"
  echo Removed: %STATE_FILE%
) else (
  echo Skip (not found): %STATE_FILE%
)

if exist "%UPDATES_DIR%" (
  rmdir /s /q "%UPDATES_DIR%"
  echo Removed: %UPDATES_DIR%
) else (
  echo Skip (not found): %UPDATES_DIR%
)

(
  echo {
  echo   "enabled": true,
  echo   "manifest_url": "%MANIFEST_URL%",
  echo   "manifest_urls": [
  echo     "https://raw.githubusercontent.com/trucbm/Eventchecker/main/Updates_2_3/remote_manifest.json",
  echo     "https://github.com/trucbm/Eventchecker/raw/main/Updates_2_3/remote_manifest.json",
  echo     "https://cdn.jsdelivr.net/gh/trucbm/Eventchecker@main/Updates_2_3/remote_manifest.json"
  echo   ],
  echo   "timeout_sec": 10,
  echo   "min_interval_sec": 0
  echo }
) > "%CONFIG_FILE%"
echo Wrote: %CONFIG_FILE%

echo.
echo Done.
echo Next steps:
echo 1. Make sure Event Inspector is fully closed before running this script
echo 2. Open Event Inspector again
echo 3. Press Check Update
pause
