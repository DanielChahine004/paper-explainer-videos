# Review sheets: one tiled PNG per rendered scene, cut at the moments that matter (the settled frame at the end of
# each narration block, four frames across each moving-curve sweep; the times come from the scene's vlint record).
# Look at them before sending a video: they catch what no rule does. Written to <video>/review/<Scene>.png.
#   wsl bash tools/review.sh <video> [Scene ...]   only scenes rendered since their sheet when none are named
#   RES=480p15 wsl bash tools/review.sh ...        sheets of a draft render (default 1080p60)
here="$(cd "$(dirname "$0")" && pwd)"
V=$1; shift || true
if [ -z "${NOSYNC:-}" ]; then source "$here/sync.sh"; else
  export PATH="$HOME/.pixi/bin:$HOME/.local/bin:$PATH"; SRC="${SRC:-$(cd "$here/.." && pwd)}"
  cd ~/slab_render/$V; SCRIPT=$(sed -n 's/^SCRIPT=\(.*\)$/\1/p' render.sh | tr -d '"'); SCENES_ALL=$(sed -n 's/^SCENES="\(.*\)"$/\1/p' render.sh)
fi
RES=${RES:-1080p60}; STEM="${SCRIPT%.py}"; OUT="${VDIR:-$SRC/$V}/review"; mkdir -p "$OUT" review_tmp
# ffmpeg called directly (pixi run costs ~0.4 s a call, and a sheet takes a dozen), up to 8 scenes at once
FF="$(pixi run which ffmpeg)"; FP="$(pixi run which ffprobe)"
sheet() {
  s=$1; f=m_$s/videos/$STEM/$RES/$s.mp4; rec=m_$s/videos/$STEM/$RES/$s.vlint.json; tmp=review_tmp/$s
  [ -f "$rec" ] || rec=-
  d=$("$FP" -v error -show_entries format=duration -of csv=p=0 "$f")
  ts=$(python3 "$here/review_times.py" "$rec" "$d")
  rm -rf "$tmp"; mkdir -p "$tmp"; i=0
  for t in $ts; do
    i=$((i+1))
    "$FF" -nostdin -loglevel error -y -ss "$t" -i "$f" -frames:v 1       -vf "scale=480:-1,drawtext=text='$t s':x=6:y=4:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.6" "$tmp/$(printf %03d $i).png"
  done
  n=$i; cols=4; [ $n -le 4 ] && cols=$n; rows=$(( (n + cols - 1) / cols ))
  "$FF" -nostdin -loglevel error -y -framerate 1 -i "$tmp/%03d.png" -vf "tile=${cols}x${rows}:padding=4:color=gray"     -frames:v 1 "$OUT/$s.png" && touch "review_tmp/$s.made"
  echo "$s: $n frames at" $ts
}
for s in ${*:-$SCENES_ALL}; do
  f=m_$s/videos/$STEM/$RES/$s.mp4
  [ -f "$f" ] || continue
  [ -z "$*" ] && [ -f "$OUT/$s.png" ] && [ "$OUT/$s.png" -nt "$f" ] && continue
  sheet "$s" &
  while [ "$(jobs -rp | wc -l)" -ge 8 ]; do wait -n; done
done
wait
made=""; for s in ${*:-$SCENES_ALL}; do [ -f "review_tmp/$s.made" ] && made="$made $s"; done
rm -rf review_tmp
echo "== review sheets in $V/review:${made:- none new}"
