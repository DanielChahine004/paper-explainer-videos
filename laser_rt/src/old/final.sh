#!/bin/bash
cd ~/slab_render/laser_rt && for s in UHDR Transport; do rm -f m_$s/videos/laser_vo/480p15/$s.mp4; done
QUALITY=-ql JOBS=2 bash /home/h/Code/manim_video_generation/tools/run_v.sh laser_rt
bash /home/h/Code/manim_video_generation/tools/sheet.sh laser_rt laser_vo 480p15 /home/h/Code/manim_video_generation/laser_rt/src/sheets UHDR Transport
QUALITY=-qh JOBS=16 bash /home/h/Code/manim_video_generation/tools/run_v.sh laser_rt
export PATH="$HOME/.pixi/bin:$PATH"
cd ~/slab_render/laser_rt
OUT=/home/h/Code/manim_video_generation/laser_rt
cp laser_rt_explainer_narrated.mp4 $OUT/
pixi run ffmpeg -loglevel error -y -i laser_rt_explainer_narrated.mp4 -c:v libx264 -crf 26 -preset slow -c:a aac -b:a 128k -movflags +faststart $OUT/laser_rt_explainer_small.mp4
ls -la $OUT/*.mp4
pixi run ffprobe -v error -select_streams v:0 -show_entries stream=width,height:format=duration -of csv=p=0 $OUT/laser_rt_explainer_small.mp4
