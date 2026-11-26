# Shared render pipeline, sourced by each video's render.sh after it sets SCRIPT, OUT and SCENES.
# Linux, macOS, or Windows from Git Bash (tools/platform.sh); needs pixi. The first run installs TinyTeX (no admin
# rights needed) and downloads the voice and Whisper weights from huggingface.co. Chatterbox needs an NVIDIA GPU;
# the default voice, Kokoro, runs on the CPU anywhere.
#   QUALITY=-ql   480p draft (generates and caches all narration); default -qh = 1080p60, the maximum allowed
#   JOBS=n        scenes rendered at once (CPU only: narration comes from tools/voice_prepass.py, so no scene
#                 loads the voice model); default: all of them, capped by cores - 2 and ~1.2 GB of RAM each
#   FRESH=1       re-render every scene; otherwise only missing scenes and scenes whose code changed
#   MIX_ENGINES=1 keep scenes the other engine rendered (default: they are re-rendered, one look per video)
#   TTS=espeak    timing check only;  TTS_VOICE=clip.wav  clone a voice with Chatterbox
#   VLINT_ALLOW=1 report vlint errors without stopping
#   ENGINE=gx     (default when ManimGX is found: GX_EXE, or manimgx on PATH) ManimGX on the GPU. From WSL, point
#                 GX_EXE at a Windows install's manimgx.exe (WSL has no NVIDIA Vulkan driver, so a WSL install runs
#                 on the CPU). Each scene's CE skip-mode check (vlint's runtime record) runs beside its ManimGX
#                 render, which writes the file CE would.
#   ENGINE=ce     Manim CE (Cairo, one core per scene); older videos pin it in render.sh
# Gates (tools/vlint): static checks before rendering, runtime and freshness checks before the join, and
# resolution / sync / length checks after it. Any error stops the build.
set -euo pipefail
# set -e stops without a word: name the line that stopped it (a macOS run ended silently after "== engine")
trap 'echo "render_lib.sh: stopped at line $LINENO: $BASH_COMMAND" >&2' ERR
: "${SCRIPT:?render.sh must set SCRIPT}" "${OUT:?render.sh must set OUT}" "${SCENES:?render.sh must set SCENES}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VLINT="python $ROOT/tools/vlint"

source "$ROOT/tools/platform.sh"
ensure_tex
pixi install

export QUALITY="${QUALITY:--qh}"
# How long renders take, per video (tools/timelog.py report). It goes to the video's own folder in the
# project ($VDIR), not to the render root's copy of it, which nothing ever copies back: without this the
# report shows a video that was never rendered.
TLOG="${VDIR:-.}"
pyhost "$ROOT/tools/timelog.py" event "$TLOG" "render_start $QUALITY" 2>/dev/null || true
# ManimGX when it is installed (GX_EXE, or manimgx on PATH; a Windows manimgx.exe works from WSL), else Manim CE
GX_EXE="${GX_EXE:-$(command -v manimgx || true)}"
if [ -z "${ENGINE:-}" ]; then [ -n "$GX_EXE" ] && ENGINE=gx || ENGINE=ce; fi
if [ "$ENGINE" = gx ] && [ ! -x "$GX_EXE" ]; then echo "ENGINE=gx needs ManimGX: set GX_EXE (README)"; exit 1; fi
export ENGINE GX_EXE
export VLINT_ENGINE="$ENGINE"   # saved in each scene's record: a scene made by the other engine is re-rendered (vlint stale)
# Cores this render may use: the job manager's share when it runs under one ($JOB_THREADS), else the machine's.
# Every parallel step below is sized from it; steps sized from ncpu took a shared machine's every core.
BUDGET="${JOB_THREADS:-$(ncpu)}"; [ "$BUDGET" -ge 1 ] 2>/dev/null || BUDGET=1
echo "== engine: $ENGINE"
case "$QUALITY" in
  -qh) RES=1080p60; GX_RES="-r 1920x1080 --fps 60" ;; -qm) RES=720p30; GX_RES="-r 1280x720 --fps 30" ;;
  -ql) RES=480p15; GX_RES="-r 854x480 --fps 15" ;;
  *) echo "QUALITY=$QUALITY is not allowed: 1080p (-qh) is the maximum"; exit 1 ;;
esac
export STEM="${SCRIPT%.py}"

# Narration is voiced first on the GPU (tools/voice_prepass.py, in the background) and starts before anything else, so
# the voice model loads while vlint checks the script; scenes already voiced are marked ready at once. Longest
# narration first: the last scene to finish is then a short one.
order="$( (pixi run python "$ROOT/tools/voice_prepass.py" --order "$SCRIPT" $SCENES 2>voice_order.log || true) | tr -d '\r' | sed -n "s/^ORDER: //p")"
order="${order:-$SCENES}"
# Clear last run's markers here, not only in the pre-pass: it clears them after its imports, by which time a scene whose
# narration changed could already have started on its stale marker and failed on the missing line (pet_explorer).
for s in $SCENES; do rm -f "m_$s/voiceovers/.ready"; done
pixi run python "$ROOT/tools/voice_prepass.py" "$SCRIPT" $order > voice.log 2>&1 &
export VPID=$!
trap 'kill $VPID 2>/dev/null || true' EXIT

echo "== vlint: static checks"
pixi run $VLINT check -q "$SCRIPT"

if [ -n "${FRESH:-}" ]; then stale="$SCENES"; else
  stale="$(pixi run $VLINT stale . --script "$SCRIPT" --res "$RES" $SCENES | tr -d '\r')"
fi
stale="$(echo $stale)"; todo=""; for s in $order; do case " $stale " in *" $s "*) todo="$todo $s" ;; esac; done; todo="${todo# }"
# Render order: scenes never rendered first (in narration order), then the rest by their last render time, slowest
# first (ManimGX logs "rendered in N s"), so the slowest scene never starts last.
todo="$(for s in $todo; do t=$(grep -o "rendered in [0-9.]*" "m_$s.log" 2>/dev/null | tail -1 | awk '{print $3}')
  echo "${t:-9999} $s"; done | sort -s -k1,1nr | awk '{print $2}' | tr '\n' ' ')"; todo="${todo% }"
# Each scene is its own process, so they run side by side (JOBS); each starts as soon as its own narration is cached
# (m_<Scene>/voiceovers/.ready), so voicing and rendering overlap. By default every scene at once, capped by cores
# (two kept for the voice workers) and memory (~1.2 GB per 1080p scene); ManimGX at most 8 (profiled 2026-10-25:
# 4 at once left the GPU under 25% busy and the CPU under 70%, the limit being each scene's Python and x264).
# --disable_caching skips manim's frame cache only; narration stays cached in m_<Scene>/voiceovers.
if [ -n "$todo" ]; then
  n_todo=$(echo $todo | wc -w)
  mem_gb=$(mem_gb)
  jobs=$(( BUDGET - 2 )); [ $(( mem_gb * 10 / 12 )) -lt $jobs ] && jobs=$(( mem_gb * 10 / 12 ))
  [ "$n_todo" -lt "$jobs" ] && jobs=$n_todo; [ "$jobs" -lt 1 ] && jobs=1
  [ "$ENGINE" = gx ] && [ $jobs -gt 8 ] && jobs=8
  jobs="${JOBS:-$jobs}"
  ENC_T=$(( BUDGET / jobs )); [ "$ENC_T" -ge 1 ] || ENC_T=1   # threads for each scene's own x264 pass (ManimGX)
  export STEM GX_RES SCRIPT ENC_T
  echo "== voicing and rendering ($jobs at once):" $todo
  echo $todo | tr ' ' '\n' | xargs -P "$jobs" -n 1 sh -c \
    'while [ ! -f "m_$1/voiceovers/.ready" ] && kill -0 $VPID 2>/dev/null; do sleep 2; done
     [ -f "m_$1/voiceovers/.ready" ] || { echo "FAILED $1: no narration (see voice.log)"; exit 1; }
     if [ "$ENGINE" = gx ]; then
       # the CE skip-mode check (vlint runtime record) runs beside the GPU render; marked a re-check, since it may
       # finish after the video it describes
       d="m_$1/videos/$STEM/'"$RES"'"; mkdir -p "$d"
       ENGINE=ce VLINT_RECHECK=1 VLINT_OUT="$d" pixi run manim -ql -s --disable_caching --progress_bar none \
         --media_dir "m_$1" "$SCRIPT" "$1" > "m_$1.check.log" 2>&1 & ck=$!
       p() { case "$GX_EXE" in *.exe) if [ "$OS" = windows ]; then cygpath -w "$1"; else wslpath -w "$1"; fi ;; *) echo "$1" ;; esac; }   # a Windows .exe takes Windows paths
       "$GX_EXE" render "$(p "$PWD/$SCRIPT")" "$1" -o "$(p "$PWD/$d/$1.mp4")" $GX_RES --crf 14 --preset slow \
         > "m_$1.log" 2>&1 || { echo "FAILED $1 (see m_$1.log)"; kill $ck 2>/dev/null; exit 1; }
       # ManimGX stores each pause as one frame lasting the whole pause (variable frame rate, ~18 fps on
       # average); players stutter when motion resumes after such a frame, so re-encode to a constant rate
       pixi run ffmpeg -nostdin -loglevel error -y -i "$d/$1.mp4" -c:v libx264 -threads "$ENC_T" -crf 14 -preset slow -fps_mode cfr \
         -r '"${RES##*p}"' -c:a copy "$d/$1.cfr.mp4" && mv "$d/$1.cfr.mp4" "$d/$1.mp4" \
         || { echo "FAILED $1: constant-rate re-encode"; kill $ck 2>/dev/null; exit 1; }
       wait $ck || { echo "FAILED $1: CE skip-mode check (see m_$1.check.log)"; exit 1; }
       rm -f "$d/$1".storyboard*.png; echo "done $1"
     else
       pixi run manim "$QUALITY" --disable_caching --progress_bar none --media_dir "m_$1" "$SCRIPT" "$1" > "m_$1.log" 2>&1 \
       && echo "done $1" || { echo "FAILED $1 (see m_$1.log)"; exit 1; }
     fi' _
fi
wait $VPID || { echo "voice pre-pass FAILED (see voice.log)"; exit 1; }
grep "^== narration" voice.log || true

# Scenes whose video is current but whose findings predate a rule change: re-check them in skip mode
# (manim -s jumps every play() to its end; seconds per scene) instead of re-rendering them.
recheck="$(pixi run $VLINT recheck . --script "$SCRIPT" --res "$RES" $SCENES | tr -d '\r')"
if [ -n "$recheck" ]; then
  echo "== re-checking with the current rules:" $recheck
  echo $recheck | tr ' ' '\n' | xargs -P "${JOBS:-$BUDGET}" -n 1 sh -c \
    'ENGINE=ce VLINT_RECHECK=1 VLINT_KEEP_ENGINE=1 VLINT_OUT="m_$1/videos/'"$STEM/$RES"'" pixi run manim -ql -s --disable_caching --progress_bar none \
       --media_dir "m_$1" "'"$SCRIPT"'" "$1" > "m_$1.check.log" 2>&1 || echo "re-check FAILED $1 (see m_$1.check.log)"' _
fi

echo "== vlint: scenes before the join"
pixi run $VLINT parts . --script "$SCRIPT" --res "$RES" $SCENES

: > list.txt
for s in $SCENES; do
  f="m_$s/videos/$STEM/$RES/$s.mp4"
  # ManimGX writes no frames for a wait that ends a scene, so a scene whose last words are spoken over a still
  # frame comes out shorter than its own narration. Concatenated, that pushes every later scene's audio late
  # (vlint: av-sync, join-duration), so hold the last frame until the sound has finished. Only the scenes that
  # need it are touched; the usual case is a video that outlasts its audio by the closing fade.
  v=$(pixi run ffprobe -v error -select_streams v:0 -show_entries stream=duration -of csv=p=0 "$f" | tr -d '\r')
  a=$(pixi run ffprobe -v error -select_streams a:0 -show_entries stream=duration -of csv=p=0 "$f" | tr -d '\r')
  pad=$(awk -v a="$a" -v v="$v" 'BEGIN { d = a - v; printf "%.3f", (d > 0 ? d : 0) }')
  if awk -v p="$pad" 'BEGIN { exit !(p > 0.01) }'; then
    echo "   $s: holding the last frame ${pad}s, for narration that outlasts the picture"
    pixi run ffmpeg -nostdin -loglevel error -y -i "$f" -vf "tpad=stop_mode=clone:stop_duration=$pad" \
      -c:v libx264 -preset veryfast -crf 16 -pix_fmt yuv420p -c:a copy "${f%.mp4}.pad.mp4" \
      && mv "${f%.mp4}.pad.mp4" "$f"
  fi
  # A stream-copy concat keeps the first part's video timescale; a part written with another (CE wrote kit_gallery's
  # Figures at 1/15360 among 1/90000) loses its picture in the join. Remux it to the first part's, no re-encode.
  tb=$(pixi run ffprobe -v error -select_streams v:0 -show_entries stream=time_base -of csv=p=0 "$f" | tr -d '\r'); tb=${tb#*/}
  if [ -z "${tb0:-}" ]; then tb0=$tb; elif [ "$tb" != "$tb0" ]; then
    echo "   $s: video timescale 1/$tb, remuxed to 1/$tb0 for the join"
    pixi run ffmpeg -nostdin -loglevel error -y -i "$f" -c copy -video_track_timescale "$tb0" "${f%.mp4}.tb.mp4" \
      && mv "${f%.mp4}.tb.mp4" "$f"
  fi
  echo "file '$(natpath "$PWD")/$f'" >> list.txt   # ffmpeg reads it: a native path on Windows
done
# Each scene's audio ends ~1 s before its video (the closing fade is silent). A stream copy stores each gap
# as one AAC packet stretched to ~1 s, which most players play as 21 ms, so the narration drifts ahead scene
# by scene; re-encoding the audio fills the gaps with real silence. Every ffmpeg here runs with -nostdin: run from a
# background job it otherwise reads the terminal for keys and can spin forever (pet_nanocomposites, 2026-10-26).
pixi run ffmpeg -nostdin -loglevel error -y -f concat -safe 0 -i list.txt -c:v copy \
  -af aresample=async=1:first_pts=0 -c:a aac -b:a 192k -movflags +faststart "$OUT"

echo "== vlint: joined video"
pixi run $VLINT final "$OUT" --script "$SCRIPT" --res "$RES" $SCENES
echo "wrote $OUT"
pyhost "$ROOT/tools/timelog.py" event "$TLOG" render_end 2>/dev/null || true
if [ "$RES" = 1080p60 ]; then
  # A smaller copy for upload limits: same 1080p, stronger compression (never a downscale).
  SMALL="${OUT%_narrated.mp4}"; SMALL="${SMALL%.mp4}_small.mp4"
  # Encoded scene by scene (one encode of the whole video is bound by decoding a single stream: ~90 s for 10 min),
  # each kept as m_<Scene>/small.mp4 until its scene changes, then joined with the joined video's audio; in the
  # background while AFTER_JOIN (run_v.sh: the review sheets) runs. Three at a time, splitting the thread budget
  # between them: one per scene with x264's own thread count ran 12 encodes of 77 threads and 1.4 GB each on a
  # shared machine (sbs_theory, 16 GB and every core).
  SMALL_P=3; SMALL_T=$(( BUDGET / SMALL_P )); [ "$SMALL_T" -ge 1 ] || SMALL_T=1
  ( echo $SCENES | tr ' ' '\n' | RES=$RES SMALL_T=$SMALL_T xargs -P "$SMALL_P" -n 1 sh -c \
      'f="m_$1/videos/$STEM/$RES/$1.mp4"; s="m_$1/small.mp4"; [ -f "$s" ] && [ "$s" -nt "$f" ] && exit 0
       pixi run ffmpeg -nostdin -loglevel error -threads "$SMALL_T" -y -i "$f" -an -c:v libx264 -crf 26 -preset slow \
         -threads "$SMALL_T" "$s.tmp.mp4" && mv "$s.tmp.mp4" "$s"' _
    : > list_small.txt; for s in $SCENES; do echo "file '$(natpath "$PWD")/m_$s/small.mp4'" >> list_small.txt; done
    pixi run ffmpeg -nostdin -loglevel error -y -f concat -safe 0 -i list_small.txt -i "$OUT" -map 0:v -map 1:a -c:v copy \
      -c:a aac -b:a 128k -movflags +faststart "$SMALL" ) & SP=$!
fi
[ -n "${AFTER_JOIN:-}" ] && { eval "$AFTER_JOIN" || echo "AFTER_JOIN failed (the video is fine)"; }
if [ -n "${SP:-}" ]; then wait $SP; echo "wrote $SMALL"; fi
