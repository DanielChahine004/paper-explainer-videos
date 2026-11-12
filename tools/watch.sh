# Watch a finished video: the frames that differ from the one before them, tiled sixteen to a sheet with their
# timestamps, into <video>/watch/. Read the sheets before sending -- this is the pass that catches what happens
# BETWEEN the narration blocks, which the review sheets (tools/review.sh, one frame per settled block) cannot
# see: a head fading in over the front page, a label crossing another on its way, a shape still sliding when the
# next cue starts. Which frames to take is tools/watch_times.py.
#   wsl bash tools/watch.sh <video>            the joined 1080p video in the project folder
#   T=0.012 wsl bash tools/watch.sh <video>    look harder (lower = more frames; 0.02 is ~150 for ten minutes)
#   FPS=12 ...                                 sample the video more finely before choosing (default 8)
# Needs no render root and no GPU: it reads the finished mp4.
export PATH="$HOME/.pixi/bin:$PATH"
here="$(cd "$(dirname "$0")" && pwd)"
SRC="$(cd "$here/.." && pwd)"
V=${1:?usage: watch.sh <video>}
F="$SRC/$V/${V}_explainer_narrated.mp4"
[ -f "$F" ] || { echo "no joined video at $F"; exit 1; }
OUT="$SRC/$V/watch"; rm -rf "$OUT"; mkdir -p "$OUT/f"
# pixi from the render root, as review.sh does: the checkout's own .pixi may be a stale copy of another folder's env
# (celeritas_optical: "environment directory has moved", 0 frames)
cd ~/slab_render 2>/dev/null || cd "$SRC"
FF="$(pixi run which ffmpeg)"
# one scene score per sampled frame: how much the picture moved since the frame before it
"$FF" -nostdin -loglevel error -y -i "$F" -an \
  -vf "fps=${FPS:-8},scale=480:-1,select='gte(scene,0)',metadata=print:file=$OUT/scores.txt" -f null -
python3 "$here/watch_times.py" "$OUT/scores.txt" "${T:-0.02}" > "$OUT/times.txt"
n=$(wc -l < "$OUT/times.txt")
d=$(pixi run ffprobe -v error -show_entries format=duration -of csv=p=0 "$F")
echo "== $V: $n frames worth looking at over ${d%.*}s"
i=0
while read -r t; do
  i=$((i + 1))
  printf "%s %04d\n" "$t" "$i"
done < "$OUT/times.txt" > "$OUT/jobs.txt"
# each frame cut on its own (a seek per frame is cheaper than decoding the whole file), eight at a time
xargs -P 8 -n 2 sh -c '
  "'"$FF"'" -nostdin -loglevel error -y -ss "$0" -i "'"$F"'" -frames:v 1 \
    -vf "scale=480:-1,drawtext=text='"'"'$0 s'"'"':x=6:y=4:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.65" \
    "'"$OUT"'/f/$1.png"' < "$OUT/jobs.txt"
k=0
s=1
while [ "$s" -le "$n" ]; do
  k=$((k + 1)); rm -rf "$OUT/t"; mkdir -p "$OUT/t"; j=0
  e=$((s + 15)); [ "$e" -gt "$n" ] && e=$n
  for idx in $(seq "$s" "$e"); do
    j=$((j + 1)); cp "$OUT/f/$(printf %04d "$idx").png" "$OUT/t/$(printf %03d $j).png"
  done
  rows=$(( (j + 3) / 4 ))
  "$FF" -nostdin -loglevel error -y -framerate 1 -i "$OUT/t/%03d.png" \
    -vf "tile=4x$rows:padding=4:color=gray" -frames:v 1 "$OUT/sheet$(printf %02d $k).png"
  echo "  sheet$(printf %02d $k): $(sed -n "${s}p" "$OUT/times.txt")s - $(sed -n "${e}p" "$OUT/times.txt")s"
  s=$((e + 1))
done
rm -rf "$OUT/t" "$OUT/f" "$OUT/jobs.txt"
echo "== $V: $k sheet(s) in $V/watch"
