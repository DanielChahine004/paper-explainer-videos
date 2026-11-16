#!/bin/bash
L="FloodSetup Flood PencilScan KNN FanScan"
cd ~/slab_render/calib && for s in $L; do rm -f m_$s/videos/calib_vo/480p15/$s.mp4 m_$s/videos/calib_vo/1080p60/$s.mp4; done
QUALITY=-ql JOBS=2 bash /home/h/Code/manim_video_generation/tools/run_v.sh calib
bash /home/h/Code/manim_video_generation/tools/sheet.sh calib calib_vo 480p15 /home/h/Code/manim_video_generation/calib/src/sheets $L
