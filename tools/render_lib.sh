# Shared render pipeline, sourced by each video's render.sh after it sets SCRIPT, OUT and SCENES.
# Linux / WSL with an NVIDIA GPU; needs pixi. First run downloads Chatterbox and Whisper weights from
# huggingface.co and installs TinyTeX into ~/.TinyTeX (no sudo needed).
#   QUALITY=-ql   480p draft (generates and caches all narration); default -qh = 1080p60, the maximum allowed
#   JOBS=2        scenes rendered at once while voice is generated (~4 GB GPU each); once narration is cached,
#                 use JOBS=<number of scenes>
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
# Each scene is its own manim process (cairo draws on one core), so they run side by side.
# --disable_caching skips manim's frame cache only; narration stays cached in m_<Scene>/voiceovers.
if [ -n "$todo" ]; then
  echo "== rendering:" $todo
  echo $todo | tr ' ' '\n' | xargs -P "${JOBS:-2}" -I{} sh -c \
    'pixi run manim "$QUALITY" --disable_caching --progress_bar none --media_dir "m_{}" "'"$SCRIPT"'" "{}" > "m_{}.log" 2>&1 \
     && echo "done {}" || { echo "FAILED {} (see m_{}.log)"; exit 1; }'
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
