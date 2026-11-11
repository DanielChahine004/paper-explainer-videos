# render single scenes at 480p in the WSL copy and print vlint lines
export PATH="$HOME/.pixi/bin:$HOME/.local/bin:$PATH"
SRC=/mnt/c/Users/h/Desktop/slab_crlb_narrated_project
cd ~/slab_render && rm -rf tools && cp -r $SRC/tools . && cp $SRC/common.py . && cp $SRC/laser_rt/laser_vo.py laser_rt/ && cd laser_rt
for s in "$@"; do pixi run manim -ql --disable_caching --progress_bar none --media_dir q_$s laser_vo.py $s 2>&1 | grep -E "\[vlint\]|Error|Traceback" | cut -c1-230; done
