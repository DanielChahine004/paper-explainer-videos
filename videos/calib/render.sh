#!/usr/bin/env bash
# Render the PET detector calibration explainer. Options (QUALITY, JOBS, FRESH, TTS) and the vlint checks: tools/render_lib.sh.
cd "$(dirname "$0")"
SCRIPT=calib_vo.py
OUT=calib_explainer_narrated.mp4
SCENES="Opening Block FloodSetup Flood EnergyWhy EnergyHow Drift TimingWhy TimingHow NormWhy NormHow NoPeaks PencilScan KNN Cheaper FanScan FloodDOI MonoEnergyTime Semi Upkeep Takeaway"
ROOT=.; for _ in 1 2 3; do [ -f "$ROOT/common.py" ] && break; ROOT="$ROOT/.."; done
source "$ROOT/tools/render_lib.sh"
