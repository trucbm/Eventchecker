#!/bin/bash

set -u

APP_SUPPORT_DIR="${HOME}/Library/Application Support/EventInspector"
STATE_FILE="${APP_SUPPORT_DIR}/update_state_v230.json"
CONFIG_FILE="${APP_SUPPORT_DIR}/remote_update_config_v230.json"
UPDATES_DIR="${APP_SUPPORT_DIR}/updates_v230"
MANIFEST_URL="https://raw.githubusercontent.com/trucbm/Eventchecker/main/Updates_2_3/remote_manifest.json"

echo "Event Inspector update reset (macOS)"
echo "Target folder: ${APP_SUPPORT_DIR}"
echo

mkdir -p "${APP_SUPPORT_DIR}"

if [ -f "${STATE_FILE}" ]; then
  rm -f "${STATE_FILE}"
  echo "Removed: ${STATE_FILE}"
else
  echo "Skip (not found): ${STATE_FILE}"
fi

if [ -d "${UPDATES_DIR}" ]; then
  rm -rf "${UPDATES_DIR}"
  echo "Removed: ${UPDATES_DIR}"
else
  echo "Skip (not found): ${UPDATES_DIR}"
fi

cat > "${CONFIG_FILE}" <<JSON
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
echo "Wrote: ${CONFIG_FILE}"

echo
echo "Done."
echo "Next steps:"
echo "1. Make sure Event Inspector is fully closed before running this script"
echo "2. Open Event Inspector again"
echo "3. Press Check Update"
