# Instructions for coding agents

This repo turns a research paper (or a topic, or a set of papers) into a narrated, animated explainer
video: Manim scenes rendered on the GPU by ManimGX (or by Manim Community where ManimGX isn't installed), a
Chatterbox voice with a Whisper check, and visuals synced to the narration word by word. Write scenes in the
API both engines share, because vlint's runtime checks always run under Manim Community. When asked to make a video, follow this file and `DESIGN.md`.

## Before anything else

1. Read `DESIGN.md` in full. Part I (principles) decides what goes on screen; Parts II–IV are craft,
   workflow and known pitfalls. Most mistakes a new video can make are already written down there.
2. Look at the worked example closest to the task: `laser_rt/` for a single paper,
   `calib/` for a topic drawn from several papers.

## Making a video

One folder per video, at the repo root (`calib/` and `laser_rt/` are worked examples).

1. **Inputs:** `bash tools/prep.sh <video> <paper.pdf>` writes the paper's text, every page at 300 and
   80 dpi, the front page and `<video>/brief.md`. Fill in its TODO lines (audience, format, length).
2. **Prompt:** `bash tools/brief.sh <video>` prints the whole prompt a building agent starts from. One agent
   makes one video from `brief.md` and `DESIGN.md`; `narration.md`, `plan.md`, `<name>_vo.py` and
   `render.sh` are its outputs. It follows DESIGN Part III, steps 1 to 8.
3. **Draw with kit:** scenes use `from kit import *`; read `KIT.md` before writing a helper.
   `python tools/kit_promote.py <video>` names the helpers another video also wrote.
4. **Scene writers (optional):** once `plan.md` exists, `python tools/writers.py split <video>` cuts one folder
   per writer and `python tools/writers.py merge <video>` splices them back.
5. **Check and render** (in WSL or Linux, through the `.sh` files, never manim directly):
   - `bash tools/check.sh <video>`: static checks, then every scene in skip mode (~25 s).
   - `QUALITY=-ql bash tools/run_v.sh <video>` to draft, `QUALITY=-qh` for the final. Never above 1080p.
   - `bash tools/watch.sh <video>`: the finished video sampled where the picture changes.
6. **Learn:** sharpen or add a rule in `DESIGN.md` (§0) before calling the video done. If a program could have
   caught the mistake, add a vlint rule with a planted bug (`tools/vlint/README.md`); `python tools/vlint selftest`
   must pass.

## Requirements

Linux or WSL2, an NVIDIA GPU with CUDA 12 (about 4 GB per narration job), and
[pixi](https://pixi.sh). Everything else (manim, ffmpeg, Chatterbox, Whisper, TinyTeX) is installed
by `pixi install` and the first run of `render.sh`. Optional: [ManimGX](https://github.com/academa-labs/manimgx)
for GPU rendering (Python 3.13+, its own environment); see the README's "Rendering engines" section.

## Voice

Narration is generated automatically during the draft render. Read [`docs/VOICE.md`](docs/VOICE.md) before writing
narration: it explains the Chatterbox + Whisper check, how to write text the voice reads well, how
to find and fix sentences that failed the check (`grep "\[tts\] best take only" m_*.log`), and the
alternatives (`TTS=espeak`, a robotic voice for checking timing without a GPU, `TTS_VOICE=clip.wav` to clone a voice you have
permission to use).
