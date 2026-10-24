#!/usr/bin/env bash
# WSL helper: rendering from /mnt/c is slow, so copy the repo's shared files and one video folder
# into the Linux filesystem, render there, and copy the finished videos back.
# usage (inside WSL):  QUALITY=-ql JOBS=2 bash tools/wsl_render.sh <video name>
#   RENDER_ROOT  where to render (default ~/paper-explainer-render); narration caches persist there
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
V=$1
DEST=${RENDER_ROOT:-$HOME/paper-explainer-render}
mkdir -p "$DEST/videos/$V"
cp "$REPO/pixi.toml" "$REPO/common.py" "$REPO/voices.py" "$DEST/"
rm -rf "$DEST/tools" && cp -r "$REPO/tools" "$DEST/" && find "$DEST/tools" -name "*.sh" -exec sed -i 's/\r$//' {} +
[ -f "$REPO/vlint.toml" ] && cp "$REPO/vlint.toml" "$DEST/"
[ -f "$REPO/pixi.lock" ] && cp "$REPO/pixi.lock" "$DEST/"
cp -r "$REPO/videos/$V/." "$DEST/videos/$V/"
find "$DEST/videos/$V" -name "*.sh" -exec sed -i 's/\r$//' {} +
cd "$DEST/videos/$V"
bash render.sh
cp -f "$DEST/videos/$V/"*.mp4 "$REPO/videos/$V/" 2>/dev/null || true
echo "videos copied back to $REPO/videos/$V"
