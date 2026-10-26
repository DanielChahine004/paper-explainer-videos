# Page 1 of a video's paper (the first src/*.pdf) as <video>/assets/front.png, which common.front_page() shows at the
# start so the viewer knows which paper the video is about (docs/DESIGN.md §1, vlint: front-page). Run in WSL:
#   bash tools/front_page.sh <video dir, relative to the repo>
export PATH="$HOME/.pixi/bin:$PATH"
D=$(cd "$(dirname "$0")/.." && pwd)/${1:?usage: front_page.sh <video>}
pdf=$(ls "$D"/src/*.pdf 2>/dev/null | head -1)
[ -n "$pdf" ] || { echo "no PDF in $D/src"; exit 1; }
mkdir -p "$D/assets"
pixi exec -s poppler pdftoppm -f 1 -l 1 -r 110 -png -singlefile "$pdf" "$D/assets/front" && echo "wrote $D/assets/front.png from $(basename "$pdf")"
