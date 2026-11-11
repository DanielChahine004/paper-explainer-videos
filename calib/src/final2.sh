#!/bin/bash
cd ~/slab_render/calib && for s in FloodSetup PencilScan; do rm -f m_$s/videos/calib_vo/1080p60/$s.mp4; done
bash /mnt/c/Users/h/Desktop/slab_crlb_narrated_project/calib/src/final.sh
export PATH="$HOME/.pixi/bin:$PATH"
for t in 9 13; do pixi run ffmpeg -loglevel error -y -ss $t -i m_PencilScan/videos/calib_vo/1080p60/PencilScan.mp4 -frames:v 1 /tmp/q_$t.png; done
pixi run ffmpeg -loglevel error -y -sseof -2 -i m_FloodSetup/videos/calib_vo/1080p60/FloodSetup.mp4 -frames:v 1 /tmp/q_f.png
pixi run ffmpeg -loglevel error -y -i /tmp/q_9.png -i /tmp/q_13.png -i /tmp/q_f.png -filter_complex "[0][1][2]hstack=3,scale=2400:-1" /mnt/c/Users/h/Desktop/slab_crlb_narrated_project/calib/src/hd_check.png
