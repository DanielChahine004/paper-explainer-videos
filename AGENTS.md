# Instructions for coding agents

This repo turns a research paper (or a topic, or a set of papers) into a narrated, animated explainer
video: Manim Community scenes, a Chatterbox voice with a Whisper check, and visuals synced to the
narration word by word. When asked to make a video, follow this file and `docs/DESIGN.md`.

## Before anything else

1. Read `docs/DESIGN.md` in full. Part I (principles) decides what goes on screen; Parts II–IV are craft,
   workflow and known pitfalls. Most mistakes a new video can make are already written down there.
2. Look at the worked example closest to the task: `videos/laser_rt/` for a single paper,
   `videos/calib/` for a topic drawn from several papers.

## Making a video

1. **Read the source.** For a PDF: `pixi exec -s poppler pdftotext -layout paper.pdf paper.txt`. Check its
   licence (first page or footer) before planning any figure reuse (docs/DESIGN.md §4).
2. **Plan the scenes** (5–8 minutes by default; longer when the content needs it). For each scene, note
   the mechanism it explains, the why before the how, and whether each paper figure is reused or redrawn.
3. **Create the folder:** `cp -r videos/_template videos/<name>`, rename `template_vo.py` to
   `<name>_vo.py`, and set `SCRIPT`, `OUT` and `SCENES` in `render.sh`. Put reused figure crops in
   `videos/<name>/assets/` and keep source PDFs out of git (they are ignored).
4. **Write the scenes.** Every number must come from the source text (grep for it) or be computed in the
   scene and labelled as computed. Run the syntax check from docs/DESIGN.md Part III.
5. **Draft:** `cd videos/<name> && QUALITY=-ql JOBS=2 bash render.sh` (Linux, or WSL with
   `bash tools/wsl_render.sh <name>`). This generates and caches all narration; at most 2 jobs while
   voice is being generated. Then check the voice log as described in `docs/VOICE.md`.
6. **Review every scene** with `bash tools/sheet.sh videos/<name> 480p15 <outdir> <Scene>...` and look at
   the sheets: overlaps, clipped labels, things drawn that the narration doesn't say, and the
   reverse. Fix, delete the changed scenes' mp4s under `m_<Scene>/`, and re-render only those.
7. **Final:** delete the changed scenes' 1080p mp4s too, then `QUALITY=-qh JOBS=<number of scenes> bash
   render.sh`. Never render above 1080p. `render.sh` also writes a `_small.mp4` copy for upload limits.
8. **Learn:** if anything went wrong or worked unusually well, sharpen or add a rule in `docs/DESIGN.md`
   (§0) before reporting the video as done.

## Requirements

Linux or WSL2, an NVIDIA GPU with CUDA 12 (about 4 GB per narration job), and
[pixi](https://pixi.sh). Everything else (manim, ffmpeg, Chatterbox, Whisper, TinyTeX) is installed
by `pixi install` and the first run of `render.sh`.

## Voice

Narration is generated automatically during the draft render. Read [`docs/VOICE.md`](docs/VOICE.md) before writing
narration: it explains the Chatterbox + Whisper check, how to write text the voice reads well, how
to find and fix sentences that failed the check (`grep "\[tts\] best take only" m_*.log`), and the
alternatives (`TTS=espeak`, a robotic voice for checking timing without a GPU, `TTS_VOICE=clip.wav` to clone a voice you have
permission to use).
