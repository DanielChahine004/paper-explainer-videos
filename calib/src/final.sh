#!/bin/bash
QUALITY=-qh JOBS=12 bash /home/h/Code/manim_video_generation/tools/run_v.sh calib
export PATH="$HOME/.pixi/bin:$PATH"
cd ~/slab_render/calib
OUT=/home/h/Code/manim_video_generation/calib
cp calib_explainer_narrated.mp4 $OUT/
pixi run ffmpeg -loglevel error -y -i calib_explainer_narrated.mp4 -c:v libx264 -crf 26 -preset slow -c:a aac -b:a 128k -movflags +faststart $OUT/calib_explainer_small.mp4
ls -la $OUT/*.mp4
pixi run ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 $OUT/calib_explainer_small.mp4
bash /home/h/Code/manim_video_generation/tools/sheet.sh calib calib_vo 1080p60 $OUT/src/sheets_hd NormWhy Drift
