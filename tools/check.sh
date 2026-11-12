# Fast design check of a video, no rendering: the static checks, then every scene in skip mode (manim -s jumps
# each play() to its end state), side by side. Narration missing from the cache is generated first, in one process.
#   wsl bash tools/check.sh <video> [Scene ...]    all of render.sh's scenes when none are named
#   wsl bash tools/check.sh all                    every video folder (old ones show their design debt)
# Findings print as one sorted list; exit 1 if any error. (From Windows: MSYS_NO_PATHCONV=1 wsl bash /mnt/c/...)
# `all` checks VIDEOS (default 4) videos side by side, the cores split between them: one at a time, each video
# waited on its slowest scene while most cores sat idle. Each video's report prints whole, in folder order.
here="$(cd "$(dirname "$0")" && pwd)"
if [ "${1:-}" = all ]; then
  SRC="${SRC:-$(cd "$here/.." && pwd)}"   # the checkout these tools run from (tools/sync.sh)
  vids=$(for d in "$SRC"/*/render.sh; do basename "$(dirname "$d")"; done)
  (V=$(echo "$vids" | head -1); source "$here/sync.sh") >/dev/null   # the shared code, once: side-by-side copies would race
  out=$(mktemp -d)
  n=${VIDEOS:-4}
  echo "$vids" | SHARED_SYNCED=1 JOBS=${JOBS:-$(( ($(nproc) + n - 1) / n ))} xargs -P "$n" -I{} sh -c \
    'bash "'"$here"'/check.sh" "{}" > "'"$out"'/{}.out" 2>&1; echo $? > "'"$out"'/{}.rc"'
  rc=0
  for v in $vids; do
    echo "######## $v"
    cat "$out/$v.out"
    [ "$(cat "$out/$v.rc")" = 0 ] || rc=1
  done
  rm -rf "$out"
  exit $rc
fi
V=$1; shift || true
source "$here/sync.sh"
scenes="${*:-$SCENES_ALL}"
echo "== $V: static"
static="$(pixi run python ../tools/vlint check -q "$SCRIPT" 2>&1 | grep -vE "^\s*$")"; rc=${PIPESTATUS[0]}
echo "$static" | sed 's/^/  /'
n_static=$(echo "$static" | grep -c ": error\[" || true)
# the checker crashing is not a clean video: without this, a traceback printed no findings and read as a pass
[ "$rc" = 0 ] || { echo "  vlint check itself failed (exit $rc)"; n_static=$((n_static + 1)); }
# the plan's own checks too, so a writer who re-prefixes a line sees the rule the merged plan is held to
# (rydberg_radar: a writer's side: passed check.sh here and failed `plan --check` after the merge)
if [ -f plan.md ]; then
  pc="$(pixi run python ../tools/vlint plan plan.md --check 2>&1)"
  np=$(echo "$pc" | sed -n 's/.* \([0-9][0-9]*\) problem(s).*/\1/p' | tail -1)
  if [ "${np:-0}" != 0 ]; then echo "$pc" | grep -v "problem(s)" | sed 's/^/  plan: /'; n_static=$((n_static + np)); fi
fi
pixi run python ../tools/voice_prepass.py "$SCRIPT" $scenes   # one voice model for all scenes, not one per scene
rm -rf chk && mkdir -p chk
echo "== $V: scenes (skip mode):" $scenes
start=$(date +%s)
echo $scenes | tr ' ' '\n' | xargs -P "${JOBS:-$(nproc)}" -I{} sh -c \
  'ENGINE=ce VLINT_OUT=chk pixi run manim -ql -s --disable_caching --progress_bar none --media_dir "m_{}" "'"$SCRIPT"'" "{}" \
     > "chk/{}.log" 2>&1 || { echo "  CRASHED {}:"; grep -E "Error|error:" "chk/{}.log" | tail -3 | sed "s/^/    /"; }'
# findings this video is already recorded as making are held back and counted (vlint/baseline.py); errors
# never are. RECORD=1 accepts what is found now as the new record, which is the only way debt is taken on.
python3 "$here/vlint_list.py" chk --all --known "$V"
n_err=$(( $(python3 "$here/vlint_list.py" chk --all --known "$V" | grep -c "^error" || true) + n_static ))
[ -n "${RECORD:-}" ] && python3 -c "import sys; sys.path.insert(0, '$here'); from vlint.baseline import record; record('$V', 'chk')"
missing=""
for s in $scenes; do [ -f "chk/$s.vlint.json" ] || missing="$missing $s"; done
[ -n "$missing" ] && echo "  no record (crashed, or a scene without the vlint monitor):$missing"
echo "== $V: $(ls chk/*.vlint.json 2>/dev/null | wc -l) scenes checked in $(( $(date +%s) - start )) s, $n_err error(s)"
[ "$n_err" = 0 ] && ! grep -l "Traceback" chk/*.log >/dev/null 2>&1
