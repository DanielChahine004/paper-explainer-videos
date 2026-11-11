#!/usr/bin/env bash
# The kit gallery: every primitive in kit.py drawn once, under both engines. Options and checks: tools/render_lib.sh.
cd "$(dirname "$0")"
SCRIPT=gallery_vo.py
OUT=kit_gallery_explainer_narrated.mp4
SCENES="Snippet Parts Flow Stack Marks Optics"
ROOT=.; for _ in 1 2 3; do [ -f "$ROOT/common.py" ] && break; ROOT="$ROOT/.."; done
source "$ROOT/tools/render_lib.sh"
