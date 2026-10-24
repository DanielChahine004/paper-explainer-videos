#!/usr/bin/env bash
# Render the laser-driven accelerators review explainer. Options (QUALITY, JOBS, FRESH, TTS) and the vlint checks: tools/render_lib.sh.
cd "$(dirname "$0")"
SCRIPT=laser_vo.py
OUT=laser_rt_explainer_narrated.mp4
SCENES="Opening WhyParticles Accelerators Overview LWFA TNSA RPA Compare BeamTime BeamYield UHDR Transport SOBP Biology Challenges Future Takeaway FieldMap"
ROOT=.; for _ in 1 2 3; do [ -f "$ROOT/common.py" ] && break; ROOT="$ROOT/.."; done
source "$ROOT/tools/render_lib.sh"
