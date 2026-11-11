# sync a video folder ($1) into WSL and run its render.sh with the given QUALITY/JOBS; the videos are copied back
#   wsl bash tools/run_v.sh <video>        (from Windows: MSYS_NO_PATHCONV=1 wsl bash /mnt/c/.../tools/run_v.sh <video>)
V=$1
source "$(dirname "$0")/sync.sh"
# a review sheet for every scene rendered since its last one (look at them before sending), made while render.sh
# encodes the small copy
case "${QUALITY:--qh}" in -ql) RES=480p15 ;; -qm) RES=720p30 ;; *) RES=1080p60 ;; esac
export AFTER_JOIN="RES=$RES NOSYNC=1 bash '$SRC/tools/review.sh' '$V' | tail -1"
date +"START %T" > run.log
bash render.sh >> run.log 2>&1
echo "EXIT $? $(date +%T)" >> run.log
grep -E "START|== |done|FAILED|error\[|warn\[|vlint:|EXIT|wrote|review sheets" run.log
for f in *_explainer_narrated.mp4 *_explainer_small.mp4; do [ -f "$f" ] && cp "$f" "${VDIR:-$SRC/$V}/"; done
ls -la --time-style=+%H:%M "${VDIR:-$SRC/$V}/"*.mp4 2>/dev/null
