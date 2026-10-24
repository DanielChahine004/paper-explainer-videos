#!/usr/bin/env bash
# Render this video. Set the three names below; the pipeline (QUALITY, JOBS, FRESH, TTS options) and the vlint
# checks that gate it are in tools/render_lib.sh. Defaults: 1080p60 (the maximum), Chatterbox voice.
#   QUALITY=-ql JOBS=2 bash render.sh     480p draft; generates and caches all narration
#   QUALITY=-qh JOBS=<n> bash render.sh   final; re-renders only scenes whose code changed, writes a _small.mp4 too
cd "$(dirname "$0")"
SCRIPT=template_vo.py                 # the scene file in this folder
OUT=template_explainer_narrated.mp4   # the joined video
SCENES="Opening Mechanism"            # scene classes, in order
ROOT=.; for _ in 1 2 3; do [ -f "$ROOT/common.py" ] && break; ROOT="$ROOT/.."; done
source "$ROOT/tools/render_lib.sh"
