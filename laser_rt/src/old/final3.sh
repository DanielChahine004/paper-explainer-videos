#!/bin/bash
cd ~/slab_render/laser_rt && for s in Accelerators WhyParticles LWFA TNSA RPA UHDR Transport Future FieldMap; do rm -f m_$s/videos/laser_vo/1080p60/$s.mp4; done
bash /mnt/c/Users/h/Desktop/slab_crlb_narrated_project/laser_rt/src/final2.sh
export PATH="$HOME/.pixi/bin:$PATH"
for t in 12 22; do pixi run ffmpeg -loglevel error -y -ss $t -i m_Accelerators/videos/laser_vo/1080p60/Accelerators.mp4 -frames:v 1 /tmp/a_$t.png; done
pixi run ffmpeg -loglevel error -y -sseof -3 -i m_Transport/videos/laser_vo/1080p60/Transport.mp4 -frames:v 1 /tmp/t_end.png
pixi run ffmpeg -loglevel error -y -i /tmp/a_12.png -i /tmp/t_end.png -filter_complex "[0][1]hstack=2,scale=2400:-1" /mnt/c/Users/h/Desktop/slab_crlb_narrated_project/laser_rt/src/hd_check.png
