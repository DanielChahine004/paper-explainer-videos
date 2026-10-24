# Shared render pipeline, sourced by each video's render.sh after it sets SCRIPT, OUT and SCENES.
# Linux / WSL with an NVIDIA GPU; needs pixi. First run downloads Chatterbox and Whisper weights from
# huggingface.co and installs TinyTeX into ~/.TinyTeX (no sudo needed).
#   QUALITY=-ql   480p draft (generates and caches all narration); default -qh = 1080p60, the maximum allowed
#   JOBS=6        scenes rendered at once (CPU only: narration is generated first, in one process, by
#                 tools/voice_prepass.py, so no scene loads the voice model)
#   FRESH=1       re-render every scene; otherwise only missing scenes and scenes whose code changed
#   TTS=espeak    timing check only;  TTS_VOICE=clip.wav  clone a voice with Chatterbox
#   VLINT_ALLOW=1 report vlint errors without stopping
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
case "$QUALITY" in
  -qh) RES=1080p60 ;; -qm) RES=720p30 ;; -ql) RES=480p15 ;;
  *) echo "QUALITY=$QUALITY is not allowed: 1080p (-qh) is the maximum"; exit 1 ;;
esac
STEM="${SCRIPT%.py}"

echo "== vlint: static checks"
pixi run $VLINT check -q "$SCRIPT"

if [ -n "${FRESH:-}" ]; then todo="$SCENES"; else
  todo="$(pixi run $VLINT stale . --script "$SCRIPT" --res "$RES" $SCENES)"
fi
# Each scene is its own manim process (cairo draws on one core), so they run side by side (JOBS).
# --disable_caching skips manim's frame cache only; narration stays cached in m_<Scene>/voiceovers.
# Narration is voiced first on the GPU (tools/voice_prepass.py, in the background); each scene renders on the CPU
# as soon as its own narration is cached (m_<Scene>/voiceovers/.ready), so voicing and rendering overlap.
if [ -n "$todo" ]; then
  echo "== voicing and rendering:" $todo
  pixi run python "$ROOT/tools/voice_prepass.py" "$SCRIPT" $todo > voice.log 2>&1 &
  export VPID=$!
  trap 'kill $VPID 2>/dev/null || true' EXIT
  echo $todo | tr ' ' '\n' | xargs -P "${JOBS:-6}" -I{} sh -c \
    'while [ ! -f "m_{}/voiceovers/.ready" ] && kill -0 $VPID 2>/dev/null; do sleep 2; done
     [ -f "m_{}/voiceovers/.ready" ] || { echo "FAILED {}: no narration (see voice.log)"; exit 1; }
     pixi run manim "$QUALITY" --disable_caching --progress_bar none --media_dir "m_{}" "'"$SCRIPT"'" "{}" > "m_{}.log" 2>&1 \
     && echo "done {}" || { echo "FAILED {} (see m_{}.log)"; exit 1; }'
  wait $VPID || { echo "voice pre-pass FAILED (see voice.log)"; exit 1; }
  grep "^== narration" voice.log || true
fi

# Scenes whose video is current but whose findings predate a rule change: re-check them in skip mode
# (manim -s jumps every play() to its end; seconds per scene) instead of re-rendering them.
recheck="$(pixi run $VLINT recheck . --script "$SCRIPT" --res "$RES" $SCENES)"
if [ -n "$recheck" ]; then
  echo "== re-checking with the current rules:" $recheck
  echo $recheck | tr ' ' '\n' | xargs -P "$(nproc)" -I{} sh -c \
    'VLINT_RECHECK=1 VLINT_OUT="m_{}/videos/'"$STEM/$RES"'" pixi run manim -ql -s --disable_caching --progress_bar none \
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
  pixi run ffmpeg -loglevel error -y -i "$OUT" -c:v libx264 -crf 26 -preset slow -c:a aac -b:a 128k \
    -movflags +faststart "$SMALL"
  echo "wrote $SMALL"
fi
