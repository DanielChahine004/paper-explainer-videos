#!/usr/bin/env bash
# Contact sheets for reviewing rendered scenes: a 3x3 grid per scene (8 evenly spaced frames + the last).
# usage: bash tools/sheet.sh videos/<name> <res: 480p15|1080p60> <outdir> <Scene> [<Scene> ...]
set -euo pipefail
V=$(cd "$1" && pwd); R=$2; O=$3; shift 3
mkdir -p "$O"; O=$(cd "$O" && pwd)
cd "$V"
STEM=$(basename "$(ls *_vo.py | head -1)" .py)
tot=0
for s in "$@"; do
  f=m_$s/videos/$STEM/$R/$s.mp4
  d=$(pixi run ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
  tot=$(python3 -c "print($tot + $d)")
  pixi run ffmpeg -loglevel error -y -i "$f" -vf "fps=8/$d,scale=427:-1" -frames:v 8 "$O/_$s%d.png"
  pixi run ffmpeg -loglevel error -y -sseof -1.2 -i "$f" -frames:v 1 -vf scale=427:-1 "$O/_${s}9.png"
  pixi run ffmpeg -loglevel error -y -i "$O/_$s%d.png" -vf tile=3x3 "$O/$s.png" && rm -f "$O/_$s"*.png
  echo "$O/$s.png"
done
echo "total ${tot} s"
