#!/bin/bash

set -u

APP_SUPPORT_DIR="${HOME}/Library/Application Support/EventInspector"
STATE_FILE="${APP_SUPPORT_DIR}/update_state_v230.json"
CONFIG_FILE="${APP_SUPPORT_DIR}/remote_update_config_v230.json"
UPDATES_DIR="${APP_SUPPORT_DIR}/updates_v230"

echo "Event Inspector update reset (macOS)"
echo "Target folder: ${APP_SUPPORT_DIR}"
echo

if [ -f "${STATE_FILE}" ]; then
  rm -f "${STATE_FILE}"
  echo "Removed: ${STATE_FILE}"
else
  echo "Skip (not found): ${STATE_FILE}"
fi

if [ -f "${CONFIG_FILE}" ]; then
  rm -f "${CONFIG_FILE}"
  echo "Removed: ${CONFIG_FILE}"
else
  echo "Skip (not found): ${CONFIG_FILE}"
fi

if [ -d "${UPDATES_DIR}" ]; then
  rm -rf "${UPDATES_DIR}"
  echo "Removed: ${UPDATES_DIR}"
else
  echo "Skip (not found): ${UPDATES_DIR}"
fi

echo
echo "Done."
echo "Next steps:"
echo "1. Open Event Inspector again"
echo "2. Press Check Update"
