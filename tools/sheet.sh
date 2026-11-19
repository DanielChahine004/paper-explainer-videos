# usage: sheet2.sh <video folder> <script stem> <res> <outdir> scenes...
source "$(dirname "$0")/platform.sh"
V=$1; N=$2; R=$3; O=$4; shift 4
cd "$RENDER_ROOT/$V"; mkdir -p $O
tot=0
for s in "$@"; do
  f=m_$s/videos/$N/$R/$s.mp4
  d=$(pixi run ffprobe -v error -show_entries format=duration -of csv=p=0 $f | tr -d '\r'); tot=$(awk -v a="$tot" -v b="$d" 'BEGIN { print a + b }')
  pixi run ffmpeg -loglevel error -y -i $f -vf "fps=8/$d,scale=427:-1" -frames:v 8 $O/_$s%d.png
  pixi run ffmpeg -loglevel error -y -sseof -1.2 -i $f -frames:v 1 -vf scale=427:-1 $O/_${s}9.png
  pixi run ffmpeg -loglevel error -y -i $O/_$s%d.png -vf tile=3x3 $O/$s.png && rm -f $O/_$s*.png
done
echo "total $tot s"
