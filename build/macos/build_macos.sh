#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

# Create venv if missing
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate

# Build one DMG that runs on both Intel Macs and Apple Silicon Macs.
MACOS_TARGET_ARCH="${MACOS_TARGET_ARCH:-universal2}"

python -m pip install --upgrade pip
pip install -r requirements.txt

# Clean stale artifacts first so every build target is forced to pick up the
# current source instead of silently reusing old output.
rm -rf "dist/EventInspector.app"
rm -f "dist/EventInspector.dmg"
rm -rf "build/EventInspector"

# Build .icns from PNG if possible (requires macOS sips + iconutil)
PNG_SRC="/Users/truc.bui/Downloads/82690-protective-slitherio-personal-wallpaper-equipment-computer-snake.png"
ICON_DIR="assets/EventInspector.iconset"
ICNS_OUT="assets/app.icns"

if [ -f "$PNG_SRC" ]; then
  rm -rf "$ICON_DIR"
  mkdir -p "$ICON_DIR"

  sips -z 16 16     "$PNG_SRC" --out "$ICON_DIR/icon_16x16.png" >/dev/null
  sips -z 32 32     "$PNG_SRC" --out "$ICON_DIR/icon_16x16@2x.png" >/dev/null
  sips -z 32 32     "$PNG_SRC" --out "$ICON_DIR/icon_32x32.png" >/dev/null
  sips -z 64 64     "$PNG_SRC" --out "$ICON_DIR/icon_32x32@2x.png" >/dev/null
  sips -z 128 128   "$PNG_SRC" --out "$ICON_DIR/icon_128x128.png" >/dev/null
  sips -z 256 256   "$PNG_SRC" --out "$ICON_DIR/icon_128x128@2x.png" >/dev/null
  sips -z 256 256   "$PNG_SRC" --out "$ICON_DIR/icon_256x256.png" >/dev/null
  sips -z 512 512   "$PNG_SRC" --out "$ICON_DIR/icon_256x256@2x.png" >/dev/null
  sips -z 512 512   "$PNG_SRC" --out "$ICON_DIR/icon_512x512.png" >/dev/null
  sips -z 1024 1024 "$PNG_SRC" --out "$ICON_DIR/icon_512x512@2x.png" >/dev/null

  iconutil -c icns "$ICON_DIR" -o "$ICNS_OUT"
  rm -rf "$ICON_DIR"
fi

# Build .app
pip install pyinstaller
# MarkupSafe's optional C speedup is arm64-only in the current venv; the
# pure-Python fallback keeps the universal2 bundle architecture-neutral.
pyinstaller --noconfirm --clean --windowed \
  --target-arch "$MACOS_TARGET_ARCH" \
  --exclude-module "markupsafe._speedups" \
  --hidden-import "engineio.async_drivers.threading" \
  --add-data "Log_checker.py:." \
  --add-data "Default event + Default Params.xlsx:." \
  --add-data "sdk_check_presets.json:." \
  --add-data "remote_update_config_v250.json:." \
  --add-data "services_checker:services_checker" \
  --icon assets/app.icns --name "EventInspector" desktop_app.py

# Create DMG (simple)
APP_PATH="dist/EventInspector.app"
DMG_PATH="dist/EventInspector.dmg"
if [ -d "$APP_PATH" ]; then
  hdiutil create -volname "Event Inspector" -srcfolder "$APP_PATH" -ov -format UDZO "$DMG_PATH"
fi
