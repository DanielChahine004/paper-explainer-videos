# vlint: design rules that check themselves

DESIGN.md says what a good video is. vlint makes the rules that can be checked by a program fail the build,
so they no longer depend on whoever writes the script remembering them. Every rule comes from a mistake
that already reached a render.

## Three stages, all gated by `tools/render_lib.sh`

| stage | when | reads | catches (examples) |
|---|---|---|---|
| static | before rendering, ~1 s, no manim needed | `*_vo.py`, `render.sh`, `plan.md`, `src/*.txt` (`number-unsourced`) | non-raw `\tau`, `FadeIn(x)` + `Indicate(x)` in one play, images in a `VGroup`, a scene named `Flash`, bookmark typos/order, SCENES vs classes, >1080p |
| runtime | inside every scene while it renders (`common.Narrated`) | the real mobjects after each `play` | labels cut by the frame edge, overlapping labels, an introduced object that ends invisible, bookmarks never reached |
| output | before and after the join | scene videos, their `.vlint.json` records, the joined mp4 | missing or stale scenes, A/V drift, wrong length, >1080p |

Each scene's record stores a **fingerprint**: a hash of its class, the script's shared code, `common.py`
(and `common_ce.py`, `common_gx.py`), `voices.py` and `assets/`, ignoring comments and whitespace. `render.sh` re-renders exactly the scenes whose
fingerprint changed, so nothing needs deleting by hand and an old scene can't slip into the join.

## Commands

```bash
python tools/vlint check <video>          # static; run after every edit (plain Python 3.11+, no manim)
python tools/vlint rules                  # every rule, its stage, default severity, DESIGN.md section
python tools/vlint selftest               # each rule against its planted bug (runtime part needs manim)
python tools/vlint cues <video>           # what each cue does: change / intro / pulse, with the clause
python tools/vlint plan <video> --draft    # skeleton plan.md (the staging pass) for an existing script
python tools/vlint baseline               # what every static rule finds across all 44 videos vs baseline.json
python tools/vlint baseline --write       # record the corpus as it stands now
python tools/vlint adopt <video> --script x_vo.py --res 1080p60 SCENES...   # trust renders made before vlint
```

`render.sh` runs the rest (`stale`, `parts`, `final`). Use `VLINT_ALLOW=1` to see errors without stopping,
and `VLINT=0` to switch the runtime monitor off.

## Tuning without editing code

`vlint.toml` in the project root, overridden by one in the video folder:

```toml
[rules]
long-text = "off"            # error | warn | info | off
text-overlap = "error"
[options]
max_words = 10               # long-text
min_cues_per_sentence = 0.5  # cue-density
overlap_fraction = 0.15      # text-overlap
image_factories = ["card"]   # helpers vgroup-non-vmobject should treat as images (it also infers them)
[scenes.Opening]
ignore = ["frame-clip"]      # runtime/output rules, one scene
```

One-off exceptions live next to the code they excuse, with the reason:
- `# vlint: ignore[rule-id] reason` on the line, `# vlint: ignore-next[rule-id]` above it,
  `# vlint: ignore-file[rule-id]` anywhere;
- in a scene, `vlint_ok(mob, "text-overlap")` exempts a mobject and its children, and
  `with self.vlint_off("frame-clip"):` switches a rule off for a block.

## Adding a rule

1. Write a function in `rules_static.py`, `rules_runtime.py` or `rules_output.py` (or a video's own
   `vlint_rules.py`) and decorate it:
   ```python
   @rule("my-rule", "static", "warn", "One line: what is wrong and what it costs.",
         "Part IV, Manim 0.19", "the fix in a few words")
   def my_rule(s):                  # static: s is a Script (tree, voiceovers, render_sh, resolve_str...)
       for node in ast.walk(s.tree):
           if ...:
               yield node, "message"
   ```
   Runtime rules take `(monitor, event, payload)` and yield `(key, message)`; output rules take an `OutputCtx`.
2. Plant the bug: a line ending in `# expect: my-rule` in `tests/static_bad/` (runtime: `tests/runtime/rt_vo.py`
   and its `EXPECT`). `selftest` fails for any rule without one, and for any finding in `tests/static_good/`.
   The expect comment goes on the line the finding lands on — for a static rule that yields a cue call, that is
   the `self.at(...)` line, not the `with self.voiceover(` above it.
3. Run `vlint baseline` before and after, and `--write` the new numbers in the same commit.
   The planted bug proves the rule fires once in a toy scene; it cannot tell you the rule still fires on the
   real videos. A rule that quietly matches nothing reports every video clean, which looks exactly like
   success — that is how a regex whose `\b` had become literal backspace bytes shipped. The baseline turns
   that into a `LOST`/`SHRANK` line naming the videos that changed.
4. Point DESIGN.md's rule at it ("checked by vlint: `my-rule`").

The runtime stage really does run: `selftest`'s fixture renders under Manim CE, which needs LaTeX from TinyTeX,
so **`PATH` must include `~/.local/bin`** (`tools/sync.sh` sets it). Without it the fixture fails to render and
you are verifying nothing; on a machine with no manim at all, `selftest` now says `NOT VERIFIED HERE` rather
than `ok`.

## The staging plan

A video with a `plan.md` (DESIGN.md Part III step 2, format in `plan.py`) has its narration staged in a pass
of its own, before any manim: one `focus:` per scene, the narration with `[mark]` where each cue fires, and a
line per mark saying what happens. The `plan-*` rules then tie the plan and the code together, so neither can
be edited alone and the plan cannot rot into documentation. They are errors, not warnings, because they read
the intent off a declaration instead of guessing it from the narration's verbs the way `scene-protagonist`
and `pulse-for-event` have to. Videos without a plan.md are checked exactly as before.

Prefer rules that are certain: when the code is ambiguous (a name sometimes a `VGroup`, a computed bookmark),
a rule stays silent rather than guess. A false alarm teaches people to ignore the checker.
