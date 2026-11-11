# Make the public repo (DanielChahine004/paper-explainer-videos) this repo's code, with its demo videos only.
#   bash tools/sync_public.sh                   copy, and show what changed (Git Bash, from the project folder)
#   bash tools/sync_public.sh "commit message"  ... then commit and push
# Everything git tracks here is copied, except the video folders not in DEMOS, each video's feedback.json and
# timelog.json, CLAUDE.md, playlists.json, voice_ab and wilson_check (this machine's). The public repo keeps its own README.md, LICENSE,
# AGENTS.md, CLAUDE.md, docs/VOICE.md, .gitattributes and pixi.lock. Run the vlint selftest first.
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
PUB="${PUB:-$HERE/../paper-explainer-videos}"
DEMOS="calib laser_rt kit_gallery"
KEEP="README.md LICENSE AGENTS.md CLAUDE.md docs/VOICE.md .gitattributes pixi.lock"
cd "$HERE"
is_video() { ls "$1"/*_vo.py >/dev/null 2>&1; }
files() {
  git ls-files | while IFS= read -r f; do
    top=${f%%/*}
    case "$f" in voice_ab/*|wilson_check/*|*/feedback.json|*/timelog.json|CLAUDE.md|playlists.json) continue ;; esac
    if [ "$top" != "$f" ] && is_video "$top" && [[ " $DEMOS " != *" $top "* ]]; then continue; fi
    echo "$f"
  done
}
cd "$PUB"
git ls-files | while IFS= read -r f; do [[ " $KEEP " == *" $f "* ]] || rm -f "$f"; done
cd "$HERE"
files | while IFS= read -r f; do mkdir -p "$PUB/$(dirname "$f")"; cp "$f" "$PUB/$f"; done
cd "$PUB"
find . -type d -empty -not -path "./.git*" -delete
git add -A
echo "== public repo:"
git status --short | cut -c1-3 | sort | uniq -c
if [ -n "${1:-}" ] && [ -n "$(git status --porcelain)" ]; then
  git -c user.name="Daniel Chahine" -c user.email="danielchahine001@gmail.com" commit -q -m "$1" \
    -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
  git push -q && git log --oneline -1
fi
