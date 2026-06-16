#!/usr/bin/env bash
# Meta Quest APK 빌드 스크립트
# 사전 요구: Godot 4.6+, Android SDK/NDK, export templates, JDK 17
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

GODOT_BIN="${GODOT_BIN:-godot4}"
PRESET="${QUEST_EXPORT_PRESET:-Meta Quest}"
OUT_DIR="$ROOT/build"
APK_PATH="$OUT_DIR/cpow-quest.apk"

echo "==> CPoW Quest APK build"
echo "    Godot: $GODOT_BIN"
echo "    Preset: $PRESET"
echo "    Output: $APK_PATH"

if ! command -v "$GODOT_BIN" &>/dev/null; then
  echo "ERROR: Godot not found. Set GODOT_BIN=/path/to/godot"
  echo "  Example: GODOT_BIN=/opt/godot/Godot_v4.6-stable_linux.x86_64"
  exit 1
fi

mkdir -p "$OUT_DIR"

# export_presets.cfg는 .gitignore — Quest 템플릿 복사
if [[ ! -f export_presets.cfg ]]; then
  echo "==> Copying export_presets.quest.cfg → export_presets.cfg"
  cp export_presets.quest.cfg export_presets.cfg
fi

# Android export templates 확인
if ! "$GODOT_BIN" --headless --version &>/dev/null; then
  echo "WARN: Godot headless check failed — GUI Godot may still work"
fi

echo "==> Exporting APK (release)..."
"$GODOT_BIN" --headless --path "$ROOT" --export-release "$PRESET" "$APK_PATH"

if [[ -f "$APK_PATH" ]]; then
  echo "==> SUCCESS: $APK_PATH"
  ls -lh "$APK_PATH"
  echo ""
  echo "Install on Quest (USB debugging + developer mode):"
  echo "  adb install -r $APK_PATH"
  echo ""
  echo "Set API server (dev PC LAN IP):"
  echo "  adb push quest_api_url.txt.example /sdcard/Download/api_url.txt"
  echo "  # Or set ELDORIA_API_URL at build time in api_config.gd"
else
  echo "ERROR: APK not produced. Open Godot Editor → Export → fix SDK/template errors."
  exit 1
fi
