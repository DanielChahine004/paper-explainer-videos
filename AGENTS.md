# Instructions for coding agents

This repo turns a research paper (or a topic, or a set of papers) into a narrated, animated explainer
video: Manim scenes rendered on the GPU by ManimGX (or by Manim Community where ManimGX isn't installed), a
Chatterbox voice with a Whisper check, and visuals synced to the narration word by word. Write scenes in the
API both engines share, because vlint's runtime checks always run under Manim Community. When asked to make a video, follow this file and `docs/DESIGN.md`.

## Before anything else

1. Read `docs/DESIGN.md` in full. Part I (principles) decides what goes on screen; Parts II–IV are craft,
   workflow and known pitfalls. Most mistakes a new video can make are already written down there.
2. Look at the worked example closest to the task: `videos/laser_rt/` for a single paper,
   `videos/calib/` for a topic drawn from several papers.

## Making a video

1. **Read the source.** For a PDF: `pixi exec -s poppler pdftotext -layout paper.pdf paper.txt`. Check its
   licence (first page or footer) before planning any figure reuse (docs/DESIGN.md §4).
2. **Infer the intent, then plan the scenes.** Decide what kind of resource it is (survey, new method,
   experiment, thesis, several papers, how-to, clinical study) and what the viewer wants to leave with.
   Write that intent as one sentence, following the table in `docs/DESIGN.md` ("Start here"). A purpose
   stated in the request wins. Then plan the scenes to serve that intent (5–8 minutes by default;
   longer when the content needs it). For each scene, note the mechanism it explains, the why before
   the how, and whether each paper figure is reused or redrawn.
3. **Create the folder:** `cp -r videos/_template videos/<name>`, rename `template_vo.py` to
   `<name>_vo.py`, and set `SCRIPT`, `OUT` and `SCENES` in `render.sh`. Put reused figure crops in
   `videos/<name>/assets/` and keep source PDFs out of git (they are ignored).
4. **Write the scenes.** Every number must come from the source text (grep for it) or be computed in the
   scene and labelled as computed. Then run `python tools/vlint check videos/<name>` and fix every error;
   read the warnings as questions (docs/DESIGN.md Part III, step 3; rules in `tools/vlint/README.md`).
5. **Draft:** `cd videos/<name> && QUALITY=-ql bash render.sh` (Linux, or WSL with
   `bash tools/wsl_render.sh <name>`). Narration is voiced first by `tools/voice_prepass.py` and cached;
   each scene renders as soon as its own narration is ready. Then check the voice log as described in
   `docs/VOICE.md`.
6. **Review every scene** with `bash tools/sheet.sh videos/<name> 480p15 <outdir> <Scene>...` and look at
   the sheets: things drawn that the narration doesn't say, and the reverse, and labels over shapes. The
   `[vlint]` lines in the render output already list clipped or overlapping labels, objects that
   vanished and bookmarks never reached. Fix and run `render.sh` again: it re-renders only the scenes
   whose code, helpers or assets changed.
7. **Final:** `QUALITY=-qh bash render.sh` (all scenes at once by default; `JOBS=n` caps it). It refuses anything above 1080p,
   refuses to join a missing, stale or broken scene, checks the joined file for length and audio drift,
   and writes a `_small.mp4` copy for upload limits. `VLINT_ALLOW=1` reports errors without stopping.
8. **Learn:** if anything went wrong or worked unusually well, sharpen or add a rule in `docs/DESIGN.md`
   (§0) before reporting the video as done. If a program could have caught the mistake, add a vlint
   rule with a planted bug instead (`tools/vlint/README.md`); `python tools/vlint selftest` must pass.

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
