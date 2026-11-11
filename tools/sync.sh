# Sourced by run_v.sh, check.sh and review.sh: copy the shared code and one video folder ($V) from the Windows
# project into ~/slab_render/$V (WSL), then cd there. Narration caches and rendered scenes in ~/slab_render stay.
export PATH="$HOME/.pixi/bin:$HOME/.local/bin:$PATH"
export GX_EXE="${GX_EXE:-/mnt/c/Users/h/manimgx_venv/Scripts/manimgx.exe}"   # ManimGX on the Windows GPU (render_lib.sh)
# The checkout these tools are running from, resolved from this file's own path and never hard-coded. This
# machine holds several checkouts of the project, and a hard-coded SRC made every tool act on one of them
# whatever checkout it was invoked from: a check then reported on somebody else's script and a render wrote
# its mp4s into somebody else's folder. Set SRC in the environment only to aim the tools elsewhere on purpose.
SRC="${SRC:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
: "${V:?set V to a video folder}"
# V is a folder in the project, or a path to one anywhere: a scene writer working in their own copy of a video
# needs the runtime rules too, and those only run from here. Checking by path keeps each writer in its own
# render root (named for the folder), so several can check at once without overwriting each other.
case "$V" in
  */*) VDIR="$V"; V="$(basename "$V")" ;;
  *)   VDIR="$SRC/$V" ;;
esac
export VDIR          # where this video came from: renders and review sheets go back there
[ -f "$VDIR/render.sh" ] || { echo "no video folder $VDIR (no render.sh)"; exit 1; }
mkdir -p ~/slab_render/$V && cd ~/slab_render
if [ -z "${SHARED_SYNCED:-}" ]; then   # check.sh all copies the shared code once, before its videos run side by side
  cp $SRC/pixi.toml $SRC/voices.py $SRC/common.py $SRC/common_ce.py $SRC/common_gx.py $SRC/kit.py .
  [ -f $SRC/vlint.toml ] && cp $SRC/vlint.toml .
  # copied over the top, never rm -rf'd: the render root is shared between videos, so a writer syncing their
  # own copy while another one renders would pull tools/vlint out from under that render's gates mid-run
  mkdir -p tools && cp -r $SRC/tools/. tools/ && find tools -name "*.sh" -exec sed -i 's/\r$//' {} +
fi
cp $VDIR/*.py $VDIR/render.sh $V/
# the staging plan goes too, or the plan-* rules find no plan here and stand down silently -- which is the one
# place they must not, since this is the check the render itself gates on
[ -f $VDIR/plan.md ] && cp $VDIR/plan.md $V/
[ -f $VDIR/vlint.toml ] && cp $VDIR/vlint.toml $V/
[ -f $VDIR/heard_ok.txt ] && cp $VDIR/heard_ok.txt $V/   # words confirmed by ear (tools/voice_prepass.py)
# and the source's text, for the same reason: number-unsourced reads src/*.txt, and without it here the rule
# stood down in check.sh and render.sh and ran only when vlint was pointed at the project folder (geant4)
if ls $VDIR/src/*.txt >/dev/null 2>&1; then mkdir -p $V/src && cp $VDIR/src/*.txt $V/src/; fi
[ -d $VDIR/assets ] && cp -r $VDIR/assets $V/
sed -i 's/\r$//' $V/render.sh
cd $V
# what render.sh declares: the script and the scenes in order
SCRIPT=$(sed -n 's/^SCRIPT=\(.*\)$/\1/p' render.sh | tr -d '"')
[ -n "$SCRIPT" ] || SCRIPT=$(grep -o "[A-Za-z0-9_]*_vo.py" render.sh | head -1)   # older render.sh files name it in the manim line
SCENES_ALL=$(sed -n 's/^SCENES="\(.*\)"$/\1/p' render.sh)
# the narrator a video is pinned to (render.sh: export TTS=...), so check.sh voices it the same way render.sh does
eval "$(grep -E '^export TTS=' render.sh || true)"
