# final 1080p render of laser_rt, copied back to Windows
D=/mnt/c/Users/h/Desktop/slab_crlb_narrated_project
QUALITY=-qh JOBS=12 bash $D/tools/run_v.sh laser_rt 2>&1 | grep -E 'vlint: [0-9]|warn\[|error\[|Error' | tail -15
cp ~/slab_render/laser_rt/laser_rt_explainer_narrated.mp4 ~/slab_render/laser_rt/laser_rt_explainer_small.mp4 $D/laser_rt/
ls ~/slab_render/laser_rt/*.mp4
