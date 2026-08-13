#!/bin/bash

set -u

APP_SUPPORT_DIR="${HOME}/Library/Application Support/EventInspector"
STATE_FILE_V230="${APP_SUPPORT_DIR}/update_state_v230.json"
CONFIG_FILE_V230="${APP_SUPPORT_DIR}/remote_update_config_v230.json"
UPDATES_DIR_V230="${APP_SUPPORT_DIR}/updates_v230"
STATE_FILE_V240="${APP_SUPPORT_DIR}/update_state_v240.json"
CONFIG_FILE_V240="${APP_SUPPORT_DIR}/remote_update_config_v240.json"
UPDATES_DIR_V240="${APP_SUPPORT_DIR}/updates_v240"
MANIFEST_URL="https://raw.githubusercontent.com/trucbm/Eventchecker/main/Updates_2_3/remote_manifest.json"
TARGET_VERSION="2026-08-13-1-2.4.0-50"

echo "Event Inspector update reset (macOS)"
echo "Target folder: ${APP_SUPPORT_DIR}"
echo

mkdir -p "${APP_SUPPORT_DIR}"

if [ -f "${STATE_FILE_V230}" ]; then
  rm -f "${STATE_FILE_V230}"
  echo "Removed: ${STATE_FILE_V230}"
else
  echo "Skip (not found): ${STATE_FILE_V230}"
fi

if [ -f "${STATE_FILE_V240}" ]; then
  rm -f "${STATE_FILE_V240}"
  echo "Removed: ${STATE_FILE_V240}"
else
  echo "Skip (not found): ${STATE_FILE_V240}"
fi

if [ -d "${UPDATES_DIR_V230}" ]; then
  rm -rf "${UPDATES_DIR_V230}"
  echo "Removed: ${UPDATES_DIR_V230}"
else
  echo "Skip (not found): ${UPDATES_DIR_V230}"
fi

if [ -f "${CONFIG_FILE_V240}" ]; then
  rm -f "${CONFIG_FILE_V240}"
  echo "Removed: ${CONFIG_FILE_V240}"
else
  echo "Skip (not found): ${CONFIG_FILE_V240}"
fi

if [ -d "${UPDATES_DIR_V240}" ]; then
  rm -rf "${UPDATES_DIR_V240}"
  echo "Removed: ${UPDATES_DIR_V240}"
else
  echo "Skip (not found): ${UPDATES_DIR_V240}"
fi

mkdir -p "${UPDATES_DIR_V230}"

cat > "${CONFIG_FILE_V230}" <<JSON
{
  "enabled": true,
  "manifest_url": "${MANIFEST_URL}",
  "manifest_urls": [
    "https://raw.githubusercontent.com/trucbm/Eventchecker/main/Updates_2_3/remote_manifest.json",
    "https://github.com/trucbm/Eventchecker/raw/main/Updates_2_3/remote_manifest.json",
    "https://cdn.jsdelivr.net/gh/trucbm/Eventchecker@main/Updates_2_3/remote_manifest.json"
  ],
  "timeout_sec": 10,
  "min_interval_sec": 0
}
JSON
echo "Wrote: ${CONFIG_FILE_V230}"

cat > "${STATE_FILE_V230}" <<JSON
{
  "last_check": 0,
  "version": "${TARGET_VERSION}",
  "update_dir": "${UPDATES_DIR_V230}",
  "manifest_url": "${MANIFEST_URL}",
  "files": [
    "Log_checker.py",
    "remote_update.py"
  ]
}
JSON
echo "Wrote: ${STATE_FILE_V230}"

echo
echo "Done."
echo "Next steps:"
echo "1. Make sure Event Inspector is fully closed before running this script"
echo "2. Open Event Inspector again"
echo "3. Press Update once so app downloads the latest bridged payload"
echo "4. Reopen app and confirm it shows v2.4.0(20)"
