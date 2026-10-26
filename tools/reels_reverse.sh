#!/usr/bin/env bash
# The rewind copy of a video for the reels page (tools/reels.py runs this through WSL): the picture played backwards,
# 640 px wide at 30 fps, no sound. Holding the left of a reel plays this forwards at 3x, which is smooth where seeking
# backwards through the original is not. ffmpeg's reverse filter holds every frame in memory, so the video is cut
# into 4 s pieces at forced keyframes, each piece is reversed, and the pieces are joined last to first.
# usage: reels_reverse.sh <ffmpeg> <src.mp4> <out.mp4>
set -e
FF=$1; SRC=$2; OUT=$3
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
"$FF" -loglevel error -y -i "$SRC" -an -vf "scale=640:-2,fps=30" -c:v libx264 -preset veryfast -crf 26 \
  -force_key_frames "expr:gte(t,n_forced*4)" -f segment -segment_time 4 -reset_timestamps 1 "$T/s%04d.mp4"
for f in $(ls "$T"/s*.mp4 | sort -r); do
  r="$T/r_$(basename "$f")"
  "$FF" -loglevel error -y -i "$f" -vf reverse -c:v libx264 -preset veryfast -crf 26 -g 15 "$r"
  echo "file '$r'" >> "$T/list.txt"
done
"$FF" -loglevel error -y -f concat -safe 0 -i "$T/list.txt" -c copy -movflags +faststart "$T/out.mp4"
mv "$T/out.mp4" "$OUT"
