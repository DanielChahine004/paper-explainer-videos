# run vlint selftest (all three stages) inside the render environment
export PATH="$HOME/.pixi/bin:$HOME/.local/bin:$PATH"   # latex lives in ~/.local/bin
SRC="${SRC:-$(cd "$(dirname "$0")/../.." && pwd)}"   # the checkout this script lives in
cd ~/slab_render && rm -rf tools && cp -r $SRC/tools . && cp $SRC/common.py $SRC/voices.py .
pixi run python tools/vlint selftest
