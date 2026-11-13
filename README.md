# paper-explainer-videos

Turn a research paper into a narrated, animated explainer video, with a coding agent doing the work.

**Watch them:** [danielchahine004.github.io/explainers](https://danielchahine004.github.io/explainers/), every explainer made so far, with Reels (each scene as a swipe-through clip).

- **Render:** [ManimGX](https://github.com/academa-labs/manimgx) on the GPU; [Manim Community](https://www.manim.community/) for checks and as fallback.
- **Voice:** [Kokoro](https://huggingface.co/hexgrad/Kokoro-82M) ([Chatterbox](https://github.com/resemble-ai/chatterbox) optional), with Whisper word timings. Visuals land on the word that names them (`<bookmark/>`).
- **Rules:** [`DESIGN.md`](DESIGN.md), the design principles and pitfalls learnt over dozens of videos. The agent follows it.
- **Checks:** `tools/vlint` checks every video before, during and after rendering, and stops on errors.

**Examples:** [examples release](https://github.com/DanielChahine004/paper-explainer-videos/releases/tag/examples-v1): laser-driven accelerators for cancer therapy (13 min), PET detector calibration (12 min).

## Quick start

Needs Linux or WSL2, an NVIDIA GPU (CUDA 12) and [pixi](https://pixi.sh).

```bash
git clone https://github.com/DanielChahine004/paper-explainer-videos
cd paper-explainer-videos
pixi install
mkdir -p ~/kokoro_env && cp tools/kokoro_env/pixi.toml ~/kokoro_env/ && pixi install --manifest-path ~/kokoro_env/pixi.toml
bash tools/check.sh kit_gallery   # smoke test
```

The first run downloads the Kokoro and Whisper weights and TinyTeX. `TTS=chatterbox` switches voice.

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
  (Python 3.13+, `pip install manimgx`); put it on PATH or set `GX_EXE`. Under WSL2, install it on Windows and set
  `GX_EXE=/mnt/c/.../manimgx.exe` (WSL has no NVIDIA Vulkan driver).
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
