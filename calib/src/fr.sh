#!/bin/bash
export PATH="$HOME/.pixi/bin:$PATH"; cd ~/slab_render/calib
for t in 8.3 11 13.5; do pixi run ffmpeg -loglevel error -y -ss $t -i m_PencilScan/videos/calib_vo/480p15/PencilScan.mp4 -frames:v 1 /tmp/p_$t.png; done
pixi run ffmpeg -loglevel error -y -i /tmp/p_8.3.png -i /tmp/p_11.png -i /tmp/p_13.5.png -filter_complex hstack=3 /mnt/c/Users/h/Desktop/slab_crlb_narrated_project/calib/src/pencil_shots.png
