# vlint: design rules that check themselves

DESIGN.md says what a good video is. vlint makes the rules that can be checked by a program fail the build,
so they no longer depend on whoever writes the script remembering them. Every rule comes from a mistake
that already reached a render.

## Three stages, all gated by `tools/render_lib.sh`

| stage | when | reads | catches (examples) |
|---|---|---|---|
| static | before rendering, ~1 s, no manim needed | `*_vo.py`, `render.sh` | non-raw `\tau`, `FadeIn(x)` + `Indicate(x)` in one play, images in a `VGroup`, a scene named `Flash`, bookmark typos/order, SCENES vs classes, >1080p |
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
3. Point DESIGN.md's rule at it ("checked by vlint: `my-rule`").

Prefer rules that are certain: when the code is ambiguous (a name sometimes a `VGroup`, a computed bookmark),
a rule stays silent rather than guess. A false alarm teaches people to ignore the checker.
