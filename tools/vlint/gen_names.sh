# Regenerate manim_names.txt (the names shadows-manim protects) from the render environment's manim.
export PATH="$HOME/.pixi/bin:$PATH"
OUT="$(cd "$(dirname "$0")" && pwd)/manim_names.txt"   # the checkout this script lives in
cd ~/slab_render/recon
pixi run python -c "import manim; print(manim.__version__); print('\n'.join(sorted(n for n in dir(manim) if not n.startswith('_') and n[0].isupper())))" > "$OUT"
