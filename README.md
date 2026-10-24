# paper-explainer-videos

Turn a research paper into a narrated, animated explainer video, with a coding agent doing the work.

The pipeline is [Manim Community](https://www.manim.community/) for the animation,
[manim-voiceover](https://github.com/ManimCommunity/manim-voiceover) for word-level sync, and
[Chatterbox](https://github.com/resemble-ai/chatterbox) for the narrator voice. Each sentence is
transcribed back with Whisper and re-synthesised if the words don't match. Visuals appear on the word that
names them, using `<bookmark/>` tags in the narration.

What makes it work with an agent is [`docs/DESIGN.md`](docs/DESIGN.md): a set of design principles and hard-won
rules, written and refined across a dozen videos. It covers what to show and what to say, how to
explain a mechanism, how to keep every number honest, when to reuse a paper's figure, and a long list
of pitfalls that broke earlier renders.

**Example output:** two finished videos made with this pipeline are attached to the
[examples release](https://github.com/DanielChahine004/paper-explainer-videos/releases/tag/examples-v1):
a review of laser-driven particle accelerators for cancer therapy (11 min), and a topic video on how PET
detectors are calibrated (12 min).

## Quick start

Requirements: Linux or WSL2, an NVIDIA GPU with CUDA 12 (about 4 GB per narration job), and
[pixi](https://pixi.sh).

```bash
git clone https://github.com/DanielChahine004/paper-explainer-videos
cd paper-explainer-videos
pixi install
cd videos/_template && QUALITY=-ql JOBS=1 bash render.sh   # a 2-scene smoke test at 480p
```

The first run downloads the Chatterbox and Whisper weights and installs TinyTeX into `~/.TinyTeX`.

## Making a video with a coding agent

Open the repo in Claude Code (or any agent that reads `AGENTS.md`) and ask, for example:

> Make a narrated explainer video of `paper.pdf`, following AGENTS.md.

The agent reads `docs/DESIGN.md`, plans the scenes, writes `videos/<name>/<name>_vo.py`, renders a draft,
reviews contact sheets of every scene, fixes what it finds, and renders the final 1080p video. The
workflow is in [`AGENTS.md`](AGENTS.md). Feedback you give on one video goes into `docs/DESIGN.md`, so the
next video starts from it.

## Voice

The narrator voice is generated automatically during the draft render and cached, so later renders
reuse it. Each sentence is synthesised by Chatterbox, transcribed back by Whisper, and regenerated with
a new seed if it doesn't match the script. Bookmarks are timed from Whisper's word timestamps. See
[`docs/VOICE.md`](docs/VOICE.md) for how it works, how to write narration it reads well, how to check and fix
failed sentences, how to clone a voice.

## Layout

| Path | What it is |
|---|---|
| `docs/DESIGN.md` | the design rules: principles, craft, workflow, pitfalls |
| `AGENTS.md`, `CLAUDE.md` | instructions for coding agents |
| `common.py` | shared look, the `Narrated` scene base, `self.at()` cues, `fit_frame()` |
| `voices.py` | the Chatterbox speech service (plus an espeak timing check) with Whisper word timings |
| `docs/VOICE.md` | how the narration voice is generated, checked and tuned |
| `pixi.toml` | the environment |
| `tools/sheet.sh` | 3×3 contact sheets for reviewing scenes |
| `tools/wsl_render.sh` | renders from the WSL filesystem (much faster than `/mnt/c`) |
| `videos/_template/` | a two-scene starting point |
| `videos/laser_rt/`, `videos/calib/` | two worked examples (scripts only; videos are on the release) |

## Examples

Two worked examples, both made after the design rules were consolidated, so they follow them most
closely. Their rendered videos are on the [examples release](https://github.com/DanielChahine004/paper-explainer-videos/releases/tag/examples-v1).

| Folder | Kind | Source | Shows |
|---|---|---|---|
| `laser_rt` | single paper (review), 16 scenes, 11 min | R. Alabd & D. R. Franklin, laser-driven particle accelerators for cancer therapy, Phys. Med. Biol. 2026 (CC BY 4.0) | mechanisms redrawn as animations; computed ranges and magnet radii; a spread-out Bragg peak solved in the scene |
| `calib` | topic across papers, 21 scenes, 12 min | how PET detectors are calibrated, pixelated vs (semi-)monolithic: Casey & Nutt 1986, Maas 2009, Borghi 2016, Cucarella 2026, Freire 2026 | bench demonstrations (flood, pencil beam, fan beam); "why before how" scenes; reused CC BY figures with credits |

The example narrations summarise third-party work, and every number in them comes from the cited
sources. Figure crops in `assets/` come only from CC BY papers, are shown with an on-screen credit, and
remain under their original licences. Figures from papers that don't allow reuse are redrawn from scratch.

## Licence

Code and documentation: MIT (see `LICENSE`). Third-party tools and model weights (Manim, Chatterbox,
Whisper, TinyTeX) are under their own licences.
