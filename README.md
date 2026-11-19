# paper-explainer-videos

Turn a research paper into a narrated, animated explainer video, with a coding agent doing the work.

**Watch them:** [danielchahine004.github.io/explainers](https://danielchahine004.github.io/explainers/), every explainer made so far, with Reels (each scene as a swipe-through clip).

- **Render:** [ManimGX](https://github.com/academa-labs/manimgx) on the GPU; [Manim Community](https://www.manim.community/) for checks and as fallback.
- **Voice:** [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M) ([Chatterbox](https://github.com/resemble-ai/chatterbox) optional), with Whisper word timings. Visuals land on the word that names them (`<bookmark/>`).
- **Rules:** [`DESIGN.md`](DESIGN.md), the design principles and pitfalls learnt over dozens of videos. The agent follows it.
- **Checks:** `tools/vlint` checks every video before, during and after rendering, and stops on errors.

**Examples:** [examples release](https://github.com/DanielChahine004/paper-explainer-videos/releases/tag/examples-v1): laser-driven accelerators for cancer therapy (13 min), PET detector calibration (12 min).

## Quick start

Runs on Linux, macOS (Apple silicon) and Windows. Needs [pixi](https://pixi.sh) and bash: on Windows, the Git Bash
that comes with [Git for Windows](https://git-scm.com/download/win) (run every command below in it). No GPU needed:
Manim Community and the Kokoro voice run on the CPU; a GPU only speeds things up (ManimGX, below).

```bash
git clone https://github.com/DanielChahine004/paper-explainer-videos
cd paper-explainer-videos
bash tools/check.sh kit_gallery                            # smoke test: installs everything on its first run
ENGINE=ce QUALITY=-ql bash tools/run_v.sh kit_gallery      # a 480p draft render
```

The first run installs the render env, the Kokoro voice env (`~/kokoro_env`) and TinyTeX, and downloads the Kokoro
and Whisper weights. Renders happen in `~/slab_render` (`RENDER_ROOT`), where narration and scenes stay cached.
`TTS=chatterbox` switches voice: it needs an NVIDIA GPU with CUDA 12 (Linux or Windows, about 4 GB per narration job).
CI runs the smoke test on all three systems (`.github/workflows/platforms.yml`).

## Making a video

Open the repo in Claude Code (or any agent that reads `AGENTS.md`):

> Make a narrated explainer video of `paper.pdf`, following AGENTS.md.

The steps the agent follows are in [`AGENTS.md`](AGENTS.md). By hand:

```bash
bash tools/prep.sh <video> paper.pdf     # inputs + <video>/brief.md (fill its TODOs)
bash tools/brief.sh <video>              # the prompt a building agent starts from
bash tools/check.sh <video>              # static + skip-mode checks
QUALITY=-ql bash tools/run_v.sh <video>  # draft; -qh for the 1080p final
bash tools/watch.sh <video>              # sample the finished video
```

Feedback on one video goes into `DESIGN.md`, so the next starts from it.

## Rendering engines

- **ManimGX** (`ENGINE=gx`, default when found): about 4x faster than Manim Community, and about 50x for 3D. Install it in its own env
  (Python 3.13+, `pip install manimgx`); put it on PATH or set `GX_EXE`. A venv at `~/manimgx_venv` on Windows is
  found by itself, from Git Bash or from WSL (WSL has no NVIDIA Vulkan driver of its own, so it borrows Windows').
- **Manim Community** (`ENGINE=ce`): CPU fallback. vlint's runtime checks always run here, so write scenes in
  the shared API. ManimGX typesets LaTeX through Typst; packages mitex lacks fail.

## Checks (vlint)

- **Static** (~1 s): LaTeX strings, bookmarks, cues, unsourced numbers, `SCENES` vs script, >1080p.
- **Runtime** (each scene, skip mode): clipped or overlapping labels, vanished objects, crowded or off-centre layout.
- **Join:** missing or stale scenes, audio drift, length. Only scenes whose code changed re-render.

`python tools/vlint rules` lists them all; `python tools/vlint selftest` runs each rule's planted bug.
Adding a rule: [`tools/vlint/README.md`](tools/vlint/README.md).

## Layout

| Path | What |
|---|---|
| `DESIGN.md`, `AGENTS.md` | design rules; agent instructions |
| `kit.py`, `KIT.md`, `kit_gallery/` | shared drawing primitives, their catalogue, a video drawing each |
| `common*.py`, `voices.py` | engine shim and scene base; speech services |
| `tools/render_lib.sh`, `tools/voice_prepass.py` | the render pipeline every `render.sh` sources; narration first |
| `tools/prep.sh`, `brief.sh`, `writers.py` | inputs, agent prompt, per-scene writers |
| `tools/check.sh`, `run_v.sh`, `watch.sh`, `review.sh` | check, render, sample, review sheets |
| `tools/vlint/` | the checks and their tests |
| `tools/catalog.py`, `reels.py`, `timelog.py` | home-network player with feedback notes; build timings |
| `laser_rt/`, `calib/` | worked examples (scripts; videos on the release) |
| `private/` | your own videos, a git repository of their own (ignored here) |

## Your own videos

Make your videos under `private/`, which this repo ignores, and make that folder a git repository of its own
(private, if you like). The tools find a video by name there as well as at the root, so you work from the root as
usual (`bash tools/check.sh myvideo`), and a change to the pipeline is a commit here that everyone gets, not a
copy to keep in step. `private/playlists.json`, when there is one, is the catalogue's playlists; each video's
`timelog.json` and `feedback.json` are yours and never tracked here. A `CLAUDE.local.md` at the root (ignored)
containing `@private/CLAUDE.md` gives a coding agent your own notes.

## Examples

| Folder | Kind | Source |
|---|---|---|
| `laser_rt` | survey, 18 scenes, 13 min | Alabd & Franklin, laser-driven accelerators for cancer therapy, PMB 2026 (CC BY 4.0) |
| `calib` | topic across papers, 21 scenes, 12 min | PET detector calibration: Casey & Nutt 1986, Maas 2009, Borghi 2016, Cucarella 2026, Freire 2026 |

Every number comes from the cited sources. Reused figure crops are from CC BY papers only, credited on screen,
and keep their licences. Other figures are redrawn.

## Licence

Code and docs: MIT (`LICENSE`). Manim, ManimGX (GPL, not bundled), Kokoro, Chatterbox, Whisper and TinyTeX
keep their own licences.
