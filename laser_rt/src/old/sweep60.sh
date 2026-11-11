# 16 consecutive 60 fps frames of WhyParticles from $1 seconds into the scene, tiled
export PATH=$HOME/.pixi/bin:$PATH
cd ~/slab_render/laser_rt
pixi run ffmpeg -loglevel error -y -ss $1 -i m_$2/videos/laser_vo/1080p60/$2.mp4 -vf "scale=480:-1,tile=4x4" -frames:v 1 /mnt/c/Users/h/Desktop/slab_crlb_narrated_project/laser_rt/src/sweep60_$2.png
