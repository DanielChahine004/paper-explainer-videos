#!/bin/bash
cd ~/slab_render/laser_rt && rm -f m_Transport/videos/laser_vo/1080p60/Transport.mp4
bash /mnt/c/Users/h/Desktop/slab_crlb_narrated_project/laser_rt/src/final2.sh
export PATH="$HOME/.pixi/bin:$PATH"
pixi run ffmpeg -loglevel error -y -sseof -3 -i m_Transport/videos/laser_vo/1080p60/Transport.mp4 -frames:v 1 -vf scale=1200:-1 /mnt/c/Users/h/Desktop/slab_crlb_narrated_project/laser_rt/src/hd_check.png
