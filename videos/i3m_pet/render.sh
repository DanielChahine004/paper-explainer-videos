#!/usr/bin/env bash
# Render the i3M Valencia i3M programme explainer at 1080p60 with the Chatterbox voice.
# Linux / WSL with an NVIDIA GPU; needs pixi. First run downloads Chatterbox and Whisper
# weights from huggingface.co and installs TinyTeX into ~/.TinyTeX (no sudo needed).
#   TTS=kokoro|espeak  other voices;  TTS_VOICE=clip.wav  clone a voice with Chatterbox
#   QUALITY=-ql        480p draft (generates and caches all narration)
#   JOBS=2             scenes rendered at once while voice is generated (~4 GB GPU each; 3 overflows
#                      an 11 GB card and crawls). Once narration is cached, use JOBS=<number of scenes>
#   FRESH=1            re-render scenes that already have a video
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v dvisvgm >/dev/null && [ ! -x "$HOME/.local/bin/dvisvgm" ]; then
  wget -qO- "https://yihui.org/tinytex/install-bin-unix.sh" | sh
  "$HOME/.local/bin/tlmgr" install standalone preview dvisvgm doublestroke babel-english cm-super lm amsfonts
fi
export PATH="$HOME/.local/bin:$PATH"
pixi install

export QUALITY="${QUALITY:--qh}"   # -qh = 1920x1080 at 60 fps
SCENES="Opening Light Mammi Preclinical TubeIdea Tube SemiMono DeepBreast Positioning BreastResults Compton Takeaway"
case "$QUALITY" in -qp) RES=1440p60 ;; -qk) RES=2160p60 ;; -qh) RES=1080p60 ;; -qm) RES=720p30 ;; *) RES=480p15 ;; esac
video() { echo "m_$1/videos/i3m_vo/$RES/$1.mp4"; }

todo=""
for s in $SCENES; do
  if [ -n "${FRESH:-}" ] || [ ! -f "$(video "$s")" ]; then todo="$todo $s"; fi
done
# Each scene is its own manim process (cairo draws on one core), so they run side by side.
# --disable_caching skips manim's frame cache only; narration stays cached in m_<Scene>/voiceovers.
if [ -n "$todo" ]; then
  echo $todo | tr ' ' '\n' | xargs -P "${JOBS:-2}" -I{} sh -c \
    'pixi run manim "$QUALITY" --disable_caching --progress_bar none --media_dir "m_{}" i3m_vo.py "{}" > "m_{}.log" 2>&1 \
     && echo "done {}" || { echo "FAILED {} (see m_{}.log)"; exit 1; }'
fi

: > list.txt
for s in $SCENES; do echo "file '$PWD/$(video "$s")'" >> list.txt; done
# Each scene's audio ends ~1 s before its video (the closing fade is silent). A stream copy
# stores each gap as one AAC packet stretched to ~1 s, which most players play as 21 ms, so the
# narration drifts ahead scene by scene; re-encoding the audio fills the gaps with real silence.
pixi run ffmpeg -loglevel error -y -f concat -safe 0 -i list.txt -c:v copy \
  -af aresample=async=1:first_pts=0 -c:a aac -b:a 192k -movflags +faststart i3m_pet_explainer_narrated.mp4
echo "wrote i3m_pet_explainer_narrated.mp4"
