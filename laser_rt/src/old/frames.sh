# consecutive 60 fps frames of the final video from $1 seconds, $2 frames, tiled
export PATH=$HOME/.pixi/bin:$PATH
cd /mnt/c/Users/h/Desktop/slab_crlb_narrated_project/laser_rt
pixi run --manifest-path ~/slab_render/pixi.toml ffmpeg -loglevel error -y -ss $1 -i laser_rt_explainer_narrated.mp4 -vf "fps=4,scale=640:-1,tile=3x3" -frames:v 1 src/f_tile.png
