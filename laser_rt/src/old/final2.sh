#!/bin/bash
QUALITY=-qh JOBS=18 bash /mnt/c/Users/h/Desktop/slab_crlb_narrated_project/tools/run_v.sh laser_rt
export PATH="$HOME/.pixi/bin:$PATH"
cd ~/slab_render/laser_rt
OUT=/mnt/c/Users/h/Desktop/slab_crlb_narrated_project/laser_rt
cp laser_rt_explainer_narrated.mp4 $OUT/
pixi run ffmpeg -loglevel error -y -i laser_rt_explainer_narrated.mp4 -c:v libx264 -crf 26 -preset slow -c:a aac -b:a 128k -movflags +faststart $OUT/laser_rt_explainer_small.mp4
ls -la $OUT/*.mp4
pixi run ffprobe -v error -select_streams v:0 -show_entries stream=width,height:format=duration -of csv=p=0 $OUT/laser_rt_explainer_small.mp4
