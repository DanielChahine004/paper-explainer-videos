# Shared render pipeline, sourced by each video's render.sh after it sets SCRIPT, OUT and SCENES.
# Linux / WSL with an NVIDIA GPU; needs pixi. First run downloads Chatterbox and Whisper weights from
# huggingface.co and installs TinyTeX into ~/.TinyTeX (no sudo needed).
#   QUALITY=-ql   480p draft (generates and caches all narration); default -qh = 1080p60, the maximum allowed
#   JOBS=n        scenes rendered at once (CPU only: narration comes from tools/voice_prepass.py, so no scene
#                 loads the voice model); default: all of them, capped by cores - 2 and ~1.2 GB of RAM each
#   FRESH=1       re-render every scene; otherwise only missing scenes and scenes whose code changed
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
: "${SCRIPT:?render.sh must set SCRIPT}" "${OUT:?render.sh must set OUT}" "${SCENES:?render.sh must set SCENES}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VLINT="python $ROOT/tools/vlint"

if ! command -v dvisvgm >/dev/null && [ ! -x "$HOME/.local/bin/dvisvgm" ]; then
  wget -qO- "https://yihui.org/tinytex/install-bin-unix.sh" | sh
  "$HOME/.local/bin/tlmgr" install standalone preview dvisvgm doublestroke babel-english cm-super lm amsfonts
fi
export PATH="$HOME/.local/bin:$PATH"
pixi install

export QUALITY="${QUALITY:--qh}"
# ManimGX when it is installed (GX_EXE, or manimgx on PATH; a Windows manimgx.exe works from WSL), else Manim CE
GX_EXE="${GX_EXE:-$(command -v manimgx || true)}"
if [ -z "${ENGINE:-}" ]; then [ -n "$GX_EXE" ] && ENGINE=gx || ENGINE=ce; fi
if [ "$ENGINE" = gx ] && [ ! -x "$GX_EXE" ]; then echo "ENGINE=gx needs ManimGX: set GX_EXE (README)"; exit 1; fi
export ENGINE GX_EXE
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
order="$(pixi run python "$ROOT/tools/voice_prepass.py" --order "$SCRIPT" $SCENES 2>/dev/null | sed -n "s/^ORDER: //p")"
order="${order:-$SCENES}"
pixi run python "$ROOT/tools/voice_prepass.py" "$SCRIPT" $order > voice.log 2>&1 &
export VPID=$!
trap 'kill $VPID 2>/dev/null || true' EXIT

echo "== vlint: static checks"
pixi run $VLINT check -q "$SCRIPT"

if [ -n "${FRESH:-}" ]; then stale="$SCENES"; else
  stale="$(pixi run $VLINT stale . --script "$SCRIPT" --res "$RES" $SCENES)"
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
  mem_gb=$(awk '/MemAvailable/ {print int($2 / 1048576)}' /proc/meminfo)
  jobs=$(( $(nproc) - 2 )); [ $(( mem_gb * 10 / 12 )) -lt $jobs ] && jobs=$(( mem_gb * 10 / 12 ))
  [ "$n_todo" -lt "$jobs" ] && jobs=$n_todo; [ "$jobs" -lt 1 ] && jobs=1
  [ "$ENGINE" = gx ] && [ $jobs -gt 8 ] && jobs=8
  jobs="${JOBS:-$jobs}"
  export STEM GX_RES SCRIPT
  echo "== voicing and rendering ($jobs at once):" $todo
  echo $todo | tr ' ' '\n' | xargs -P "$jobs" -I{} sh -c \
    'while [ ! -f "m_{}/voiceovers/.ready" ] && kill -0 $VPID 2>/dev/null; do sleep 2; done
     [ -f "m_{}/voiceovers/.ready" ] || { echo "FAILED {}: no narration (see voice.log)"; exit 1; }
     if [ "$ENGINE" = gx ]; then
       # the CE skip-mode check (vlint runtime record) runs beside the GPU render; marked a re-check, since it may
       # finish after the video it describes
       d="m_{}/videos/$STEM/'"$RES"'"; mkdir -p "$d"
       ENGINE=ce VLINT_RECHECK=1 VLINT_OUT="$d" pixi run manim -ql -s --disable_caching --progress_bar none \
         --media_dir "m_{}" "$SCRIPT" "{}" > "m_{}.check.log" 2>&1 & ck=$!
       p() { case "$GX_EXE" in *.exe) wslpath -w "$1" ;; *) echo "$1" ;; esac; }   # a Windows .exe takes Windows paths
       "$GX_EXE" render "$(p "$PWD/$SCRIPT")" "{}" -o "$(p "$PWD/$d/{}.mp4")" $GX_RES --crf 14 --preset slow \
         > "m_{}.log" 2>&1 || { echo "FAILED {} (see m_{}.log)"; kill $ck 2>/dev/null; exit 1; }
       # ManimGX stores each pause as one frame lasting the whole pause (variable frame rate, ~18 fps on
       # average); players stutter when motion resumes after such a frame, so re-encode to a constant rate
       pixi run ffmpeg -loglevel error -y -i "$d/{}.mp4" -c:v libx264 -crf 14 -preset slow -fps_mode cfr \
         -r '"${RES##*p}"' -c:a copy "$d/{}.cfr.mp4" && mv "$d/{}.cfr.mp4" "$d/{}.mp4" \
         || { echo "FAILED {}: constant-rate re-encode"; kill $ck 2>/dev/null; exit 1; }
       wait $ck || { echo "FAILED {}: CE skip-mode check (see m_{}.check.log)"; exit 1; }
       rm -f "$d/{}".storyboard*.png; echo "done {}"
     else
       pixi run manim "$QUALITY" --disable_caching --progress_bar none --media_dir "m_{}" "$SCRIPT" "{}" > "m_{}.log" 2>&1 \
       && echo "done {}" || { echo "FAILED {} (see m_{}.log)"; exit 1; }
     fi'
fi
wait $VPID || { echo "voice pre-pass FAILED (see voice.log)"; exit 1; }
grep "^== narration" voice.log || true

# Scenes whose video is current but whose findings predate a rule change: re-check them in skip mode
# (manim -s jumps every play() to its end; seconds per scene) instead of re-rendering them.
recheck="$(pixi run $VLINT recheck . --script "$SCRIPT" --res "$RES" $SCENES)"
if [ -n "$recheck" ]; then
  echo "== re-checking with the current rules:" $recheck
  echo $recheck | tr ' ' '\n' | xargs -P "$(nproc)" -I{} sh -c \
    'ENGINE=ce VLINT_RECHECK=1 VLINT_OUT="m_{}/videos/'"$STEM/$RES"'" pixi run manim -ql -s --disable_caching --progress_bar none \
       --media_dir "m_{}" "'"$SCRIPT"'" "{}" > "m_{}.check.log" 2>&1 || echo "re-check FAILED {} (see m_{}.check.log)"'
fi

echo "== vlint: scenes before the join"
pixi run $VLINT parts . --script "$SCRIPT" --res "$RES" $SCENES

: > list.txt
for s in $SCENES; do echo "file '$PWD/m_$s/videos/$STEM/$RES/$s.mp4'" >> list.txt; done
# Each scene's audio ends ~1 s before its video (the closing fade is silent). A stream copy stores each gap
# as one AAC packet stretched to ~1 s, which most players play as 21 ms, so the narration drifts ahead scene
# by scene; re-encoding the audio fills the gaps with real silence.
pixi run ffmpeg -loglevel error -y -f concat -safe 0 -i list.txt -c:v copy \
  -af aresample=async=1:first_pts=0 -c:a aac -b:a 192k -movflags +faststart "$OUT"

echo "== vlint: joined video"
pixi run $VLINT final "$OUT" --script "$SCRIPT" --res "$RES" $SCENES
echo "wrote $OUT"
if [ "$RES" = 1080p60 ]; then
  # A smaller copy for upload limits: same 1080p, stronger compression (never a downscale).
  SMALL="${OUT%_narrated.mp4}"; SMALL="${SMALL%.mp4}_small.mp4"
  # Encoded scene by scene, all at once (one encode of the whole video is bound by decoding a single stream: ~90 s
  # for 10 min), each kept as m_<Scene>/small.mp4 until its scene changes, then joined with the joined video's
  # audio; in the background while AFTER_JOIN (run_v.sh: the review sheets) runs.
  ( echo $SCENES | tr ' ' '\n' | RES=$RES xargs -P "$(nproc)" -I{} sh -c \
      'f="m_{}/videos/$STEM/$RES/{}.mp4"; s="m_{}/small.mp4"; [ -f "$s" ] && [ "$s" -nt "$f" ] && exit 0
       pixi run ffmpeg -loglevel error -y -i "$f" -an -c:v libx264 -crf 26 -preset slow "$s.tmp.mp4" && mv "$s.tmp.mp4" "$s"'
    : > list_small.txt; for s in $SCENES; do echo "file '$PWD/m_$s/small.mp4'" >> list_small.txt; done
    pixi run ffmpeg -loglevel error -y -f concat -safe 0 -i list_small.txt -i "$OUT" -map 0:v -map 1:a -c:v copy \
      -c:a aac -b:a 128k -movflags +faststart "$SMALL" ) & SP=$!
fi
[ -n "${AFTER_JOIN:-}" ] && { eval "$AFTER_JOIN" || echo "AFTER_JOIN failed (the video is fine)"; }
if [ -n "${SP:-}" ]; then wait $SP; echo "wrote $SMALL"; fi
