# Regenerate manim_names.txt (the names shadows-manim protects) from the render environment's manim.
# usage: bash tools/vlint/gen_names.sh   (from the repo root, where pixi.toml is)
pixi run python -c "import manim; print('# manim', manim.__version__); print('\n'.join(sorted(n for n in dir(manim) if not n.startswith('_') and n[0].isupper())))" > "$(dirname "$0")/manim_names.txt"
