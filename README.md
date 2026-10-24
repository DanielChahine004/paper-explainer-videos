# paper-explainer-videos

Turn a research paper into a narrated, animated explainer video, with a coding agent doing the work.

The pipeline is [Manim Community](https://www.manim.community/) for the animation,
[manim-voiceover](https://github.com/ManimCommunity/manim-voiceover) for word-level sync, and
[Chatterbox](https://github.com/resemble-ai/chatterbox) for the narrator voice. Each sentence is
transcribed back with Whisper and re-synthesised if the words don't match. Visuals appear on the word that
names them, using `<bookmark/>` tags in the narration.

What makes it work with an agent is [`DESIGN.md`](DESIGN.md): a set of design principles and hard-won
rules, written and refined across a dozen videos. It covers what to show and what to say, how to
explain a mechanism, how to keep every number honest, when to reuse a paper's figure, and a long list
of pitfalls that broke earlier renders.

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

The agent reads `DESIGN.md`, plans the scenes, writes `videos/<name>/<name>_vo.py`, renders a draft,
reviews contact sheets of every scene, fixes what it finds, and renders the final 1080p video. The
workflow is in [`AGENTS.md`](AGENTS.md). Feedback you give on one video goes into `DESIGN.md`, so the
next video starts from it.

## Layout

| Path | What it is |
|---|---|
| `DESIGN.md` | the design rules: principles, craft, workflow, pitfalls |
| `AGENTS.md`, `CLAUDE.md` | instructions for coding agents |
| `common.py` | shared look, the `Narrated` scene base, `self.at()` cues, `fit_frame()` |
| `voices.py` | Chatterbox / Kokoro / espeak speech services with Whisper word timings |
| `pixi.toml` | the environment |
| `tools/sheet.sh` | 3×3 contact sheets for reviewing scenes |
| `tools/wsl_render.sh` | renders from the WSL filesystem (much faster than `/mnt/c`) |
| `videos/_template/` | a two-scene starting point |
| `videos/*/` | worked examples (scripts only; rendered videos are not in git) |

## Examples

| Folder | Source |
|---|---|
| `laser_rt` | R. Alabd & D. R. Franklin, laser-driven particle accelerators for cancer therapy, Phys. Med. Biol. 2026 (review, CC BY 4.0) |
| `calib` | topic video: how PET detectors are calibrated, pixelated vs (semi-)monolithic (Casey & Nutt 1986; Maas 2009; Borghi 2016; Cucarella 2026; Freire 2026) |
| `i3m_pet` | the i3M Valencia monolithic PET programme (MAMMI, single-crystal tube, DeepBreast) |
| `brain_swin` | Sun et al., voxel-level brain state prediction with a Swin transformer, IEEE JBHI 2025 (CC BY 4.0) |
| `liquid_tc` | Hasani et al., Liquid Time-constant Networks, AAAI 2021 |
| `wt_pet` | the Ghent walk-through / flat-panel PET programme |
| `mouse_pet` | the University of Sydney open-field mouse brain PET programme |
| `prism_pet` | the Prism-PET programme |
| `shell_pet` | K. Wilson, continuous cylindrical shell PET, PhD thesis, UTS 2020 |

The example narrations summarise third-party work, and every number in them comes from the cited
sources. Figure crops in `assets/` come only from CC BY papers, are shown with an on-screen credit, and
remain under their original licences. Figures from papers that don't allow reuse are redrawn from scratch.

## Licence

Code and documentation: MIT (see `LICENSE`). Third-party tools and model weights (Manim, Chatterbox,
Whisper, Kokoro, TinyTeX) are under their own licences.
