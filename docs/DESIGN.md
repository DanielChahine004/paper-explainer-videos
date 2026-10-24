# Design rules for the narrated explainer videos

Read this before writing any video in this repo. Part I is the attitude, the few ideas every
other rule comes from. Parts II–IV are how to carry it out without repeating past mistakes.
Bracketed names such as (`wt_pet` Block) point to the video where a rule was learnt; some of those
videos are not in this repo, but the lesson stands.

The default audience is a researcher in the paper's field (the rules grew from PET physics videos for a
PhD audience); adjust the depth to yours. A video should leave them understanding *how*
the work was done and *why* its numbers come out as they do, as if a sharp colleague had walked
them through the paper at a whiteboard.

## 0. This file learns

Each video should leave this file better than it found it, and this is part of finishing a video.
- **After a mistake** (a clash, a wrong number, a crash, something the user found unclear, wasted
  render time), find the rule that should have caught it. If the rule exists but did not fire,
  sharpen it. If none exists, add one aimed at the whole class of mistake.
- **After something that worked**, add it where it belongs.
- Prefer deepening a principle in Part I over adding a new rule. Rules carry a short example in
  brackets so a later reader can judge when they apply.
- **If a program could have caught it, make the program catch it.** A rule here relies on someone remembering
  it; a vlint rule (`tools/vlint/README.md`) fails the build. Add one with a planted bug in its tests, and mark
  the rule here with its id, as in "(vlint: `intro-and-pulse`)". Judgement stays in this file; anything that
  can be decided from the code or the frames moves into vlint.

---

# Part I: Principles

## Start here: why is this being watched?

Before planning a single scene, infer what the viewer wants to leave with, and shape the whole video
around that. The kind of resource is the first clue. If the request states a purpose ("for my
literature review", "I need to reproduce this"), that purpose wins. Write the inferred intent as one
sentence at the top of the scene plan. The opening scene promises it, every scene serves it, and the
closing scene delivers it. If the intent is genuinely unclear and would change the video, ask.

| Resource | What the viewer wants to leave with | Shape of the video |
|---|---|---|
| **Survey / review** | a map of the field: the taxonomy of approaches, how they relate, where each wins, the state of the results, and the open problems | build the map branch by branch, one scene per branch; keep a small map on screen as navigation; end on the full map with gaps marked (`laser_rt`: three mechanisms, then energy reached vs needed) |
| **New method / architecture** | what is new compared with the baseline, how it works, which design choices matter, and what the results do and don't show | problem; why the baseline fails; the idea, mechanism step by step; training and implementation details; results against baselines and ablations; limits |
| **Experiment / measurement** | what was measured, how, how well, and what it implies | question; setup drawn as the apparatus; method; results with uncertainty; implications and caveats |
| **Thesis** | the arc of the argument and each chapter's contribution | the question; one movement per contribution; how they connect; what remains |
| **Group or programme (several papers)** | the trajectory: what each system changed and what is still open | timeline of systems, each scene one step and why it was taken; the gap they leave |
| **Topic / how-to** (how something is done) | the intuition for the procedure: why it is needed, how it is done, and what it costs | why (the failure it prevents); how (on the bench); how often and how long (`calib`) |
| **Clinical / biological study** | the question, design, cohort, outcome, and how far to trust it | question; design and cohort; endpoints; results with confidence; bias and caveats |

The same paper can call for different videos. A survey read to pick a method for a thesis should spend
more time on the comparison between methods, while a survey read as an introduction should spend more
time on the taxonomy.

## 1. The voice explains; the screen shows

Narration carries the argument. The picture carries what the eye must hold while the voice moves
on: the object, the shape of the effect and the key number. Neither repeats the other.
- **Draw, don't write.** Text on screen is a label or a **bold number**, never prose. That means
  about 3 short lines per scene besides titles and diagram labels. A spec list becomes a drawing of
  the object with dimension arrows. A pipeline becomes shapes joined by arrows. A list of ideas
  becomes a row of icons, each with one word. A timeline carries pictograms. Specs that differ in
  kind become tiles, each an icon plus a number. Any `Tex` holding more than about 3 words is a
  candidate for a shape (vlint: `long-text` warns past 8 prose words; numbers and units don't count).
- **No words pointing at words.** A flow diagram whose nodes are text boxes ("sinogram → OSEM → CNN →
  image") explains nothing the narration doesn't. Each node is a picture of the thing with a one-word
  label under it: the sinogram as a thumbnail, the reconstruction as a detector ring with lines, a network
  as layers of nodes joined by edges, the image as the image. Keep a text box only where there is nothing
  to draw (vlint: `text-chain` warns at 3 text-only boxes joined by arrows).
- **Build on what is already on screen.** Once a thing is drawn, its properties are shown on it rather
  than beside it: an edge is a band on the profile across the object, a blur is that profile going soft,
  a width is a double arrow across the thing, contrast lost is a bar from the peak reached to the true
  peak, a weight is the shading of the voxels a line crosses. A dashed line on the image shows where
  the profile runs. The narration word that names the property carries the cue (vlint: `property-cue`
  warns when "width", "edge", "contrast" and the like have no bookmark within 6 words before them).
- **Appear as it is named; pulse it when it is named again.** Each thing arrives on the word that names it
  and not before. When the narration names something already on screen (a crystal, a detector pair, a
  number), it gets an `Indicate` or `Circumscribe` on that word, so the eye always knows where to look. When a
  sentence names three things, that is three cues. Equations are lit term by term as they are read.
  Leave the end of a line free: after the last cue, let the speech finish over a still frame.
- **Steer the eye the whole time** (user, laser review). The voice should never talk about one part of the
  screen while the eye is free to wander elsewhere. Every object, region or number the narration names
  gets a visible cue on that word, even if it was introduced earlier. Choose the cue by what is meant:
  - **the object:** `Indicate` (pulse) or `Flash`;
  - **an outline or region:** `Circumscribe`, or a `SurroundingRectangle` that stays while it is discussed;
  - **a direction or path:** a dot or highlight travelling along it (`MoveAlongPath`, `ShowPassingFlash`);
  - **a comparison:** pulse both items in turn;
  - **a quantity changing:** a `ValueTracker` animated across the phrase that says it;
  - **a size (a width, a spread, a gap, a ratio):** draw it on the object itself, as a double arrow across
    the width or a bar between two levels, and pulse that;
  - **a method with two readings** (sinogram and list mode, matrix and event by event): show both, the
    sinogram view and the individual lines being traced, so either intuition lands.
  - **feedback loops in a box diagram:** route the return arrow above or below the row as straight
    segments, never a `CurvedArrow` across the boxes. No arrow's shaft may cross a label: end it at the
    label's side (vlint: `arrow-over-label`).

  While a part of the picture is being discussed, dim everything else to about 30% opacity, then
  restore it. Target at least one cue per sentence. A voiceover block with fewer bookmarks than
  sentences is a sign the eye is being left alone (vlint: `cue-density`, `bookmark-unused`).
- **One idea at a time.** One development per scene, with the diagram left and labels right. Build
  the whole panel, fit it to the frame, then reveal it piece by piece so nothing jumps.

## 2. Explain the mechanism, not just the name

Naming a technique explains nothing. For any method that matters (a solver, a loss, a calibration,
a reconstruction), show the problem, what the naive approach does and why it fails, and the fix as
concrete choices (what is computed, what is kept). Give derivations one line at a time.
- **Why before how, then what it costs** (user, calibration video). Before a procedure, show the failure
  it prevents, as an animation with a live number (a gain error pushing the photopeak out of the window,
  "photopeak kept 10%"). Then show the procedure step by step. Then say how often it is redone and how
  long it takes, using reported times only. A topic the viewer can't yet see the need for gets a why-scene
  of its own. Length follows the content: going past 8 minutes is fine when each scene earns its place.
- **Method before result.** Name the simulation code and settings, the detector model, the
  reconstruction and its update equation, and the standard test (NEMA etc.), with the numbers that
  define them. Results come after the method that produced them.
- **Recompute what you can.** If the paper states a model (a cost formula, a coverage criterion, a
  neuron equation), run it in numpy inside the scene and label the result "computed here".
- **A short draft needs more explanation, not padding.** Under 5 minutes, find a mechanism the
  narration only names and give it its own scene (`mouse_pet` Motion).

## 3. Make the physics visible

- **Draw fields as arrows** (user, laser review). Whenever the narration invokes an electric or magnetic
  field, or a force, draw it rather than naming it:
  - **E fields:** arrows from + toward −, with length showing strength (`ArrowVectorField`, or a few
    hand-placed arrows).
  - **B fields:** ⊙/⊗ symbols for a field into or out of the page, or circulating arrows around a
    current.
  - **Forces on a moving charge:** an arrow on the particle, with the force (for example qv×B) shown at
    right angles to the velocity as the track bends.
  - **Changing fields:** animate the arrows growing, flipping or rotating as the narration describes.

  Pulse the field arrows on the words "field", "force" and "pushes".

A number is a summary of something physical, so show that thing.
A number is a summary of something physical, so show that thing.
- **Show what a number does, then vary its cause.** Put the cause in the scene as a movable object
  (a source's position, a thickness, a timing value, an activity). Draw the effect as the thing the
  metric measures, in a fixed-scale inset with a live value:
  - resolution: a bell curve with a half-max arrow;
  - energy resolution: a photopeak;
  - timing: a TOF kernel;
  - sensitivity: the fraction of rays that hit;
  - count rate: pulses piling up;
  - uncertainty: an ellipse or a point cloud.

  If the paper plots the trend, a dot rides that plot as the cause moves. Use this for the one or
  two dependences that carry the argument (MAMMI: a source moves from the centre to 75 mm and its
  curve widens from 1.8 to 6.0 mm; `fwhm_inset` in `i3m_pet`).
- **Show the procedure on the bench before naming it** (user, calibration video). When the topic is a
  measurement or calibration, animate the apparatus doing it:
  - the source and collimator, and the stage stepping;
  - individual events arriving one by one (a gamma flies, light spreads, a dot lands);
  - the result accumulating as the counter climbs (a flood map growing from scattered dots to a grid);
  - the effect of a better method shown as the same task going faster (a fan stripe sweeping vs a pencil crawling).

  Play the first event slowly with every step visible, then speed up, then jump ahead in stages.
  Explain the result after the viewer has watched it form (`calib` FloodSetup, PencilScan, FanScan).
- **Make differences visible at screen scale.** A wrong and a right answer must be at least about
  0.3 units apart where it matters. Exaggerate the geometry and label it schematic. Avoid symmetric
  setups where the error cancels, and check the gap numerically (`wt_pet` Depth, `prism_pet` Parallax).
- **The drawing does what the words say.** "Escapes through the gaps" means the arrow goes through
  a computed gap. "Clamped to the crystal" means the points are clipped in code. "Light stops at an
  air gap" means the rays end at the joint. Five drawn arrows need five labels or brackets. When the
  paper counts more than it names, say so and group what is known (MAMMI's 5 signals).

## 4. Every mark is true

Everything on screen is either from the source, computed from the source's own model, or
labelled illustrative/schematic.
- **Numbers come from the extracted text or tables, never from memory or a summary.** Grep the
  source for every number in the script before the draft (`shell_pet`: 3.66 from memory was 3.59).
  Work counts out from the source. Show the source's precision, formatted per metric, not per
  magnitude (`liquid_tc`: 1.512 became 1.51).
- **Narrate a computed number only after computing it.** If a scene's own model produces a value
  (an error, a fraction), run the model before writing the sentence. The calibration video's k-NN
  demo was scripted as "about a millimetre", but the computed error was 0.4 mm.
- **Animate through reported values only.** Use `np.interp` between them, with no invented curve
  shapes. Keep scales fixed during a move.
- **When your own model contradicts your script, the script changes.** In the i3M Light scene, the
  model showed reflective walls do not compress positions more than black paint, so that claim
  was cut.
- **Real data stays real.** Reuse the paper's own figure for real data (photos, reconstructions,
  measured maps or spectra), for dense plots that would be slow to rebuild faithfully, and for the
  result the paper is known for, licence permitting. Redraw mechanisms and schematics, and pull out
  the 2–4 numbers that matter from busy figures and tables. Decide this per figure, in the plan.
  Use about 2–4 reused figures per video, each highlighted and given time to read.

## 5. Clarity before spectacle

- **2D by default.** Use 3D only when depth itself is the point (a whole system's geometry,
  hardware moving in 3D), and only in one or two scenes per video. 3D costs render time and
  draw-order bugs (§III-3D).
- **Readable at 1080p.** Keep everything 0.3 units inside the frame, with text at least 24 pt and
  labels in empty space. Nothing overlaps; check every frame of the contact sheet.
- **One look across videos.** Dark background, one accent colour per concept used consistently,
  and a shared palette and helpers in `common.py`.

---

# Part II: Craft

## Sync (manim-voiceover)
- Put `<bookmark mark='x'/>` directly before the noun or number, glued to it:
  `"captured at a <bookmark mark='act'/>luminescence centre"`. Then use `self.at("x", anim)` from
  `common.Narrated`, which waits for the bookmark and plays the animation. Cues follow the text's order,
  each bookmark once (vlint: `bookmark-missing`, `-order`, `-duplicate`, `narration-markup`, and
  `bookmark-unfired` at render time).
- Animations run 0.4–0.8 s. Pick the verb by what is happening:
  - a new object: `Create` for lines, `FadeIn` for labels, `GrowArrow`, `Write` for equations;
  - an object named again: `Indicate` or `Circumscribe`, never redraw;
  - a value changing: a `ValueTracker` across the phrase;
  - a process: a dot moving along the path.
- Bookmarks don't change the audio and are stripped before the cache lookup. Only changed words
  re-synthesise, so keep narration verbatim when only the visuals change.

## Layout
- **Call `fit_frame(group)` (common.py) on every panel once it is built.** It moves only what is in
  the group, so include everything placed relative to it (MAMMI's anode grid stayed behind). Fit
  the widest part, including titles and legends (`liquid_tc` Results).
- Font sizes: 24 for footnotes, 26–30 for labels, 36+ for headings. Wrap with `\\` instead of
  shrinking. One title per scene, `to_edge(UP)`.
- Place labels with explicit coordinates (`ax.c2p`) when curves could cross them. If lines will
  pass through a label, give it a background rectangle and `set_z_index(3)`. The y-axis title needs
  `buff >= 0.95`.
- The bottom 0.5 units belong to the footnote or credit, so keep plots above y = -3.3.
- **Use the space, evenly.** Lay panels out on a grid that fills the frame below the title: columns for
  things compared side by side, rows for stages, flow left to right and top to bottom. Keep at least
  ~0.3 units between panels; when they nearly touch while part of the screen is empty, spread them out
  instead of shrinking them. When a scene builds in two halves, centre the first half while it is alone
  and slide it up when the second arrives. (vlint: `layout-crowded`, `layout-balance`, checked at the
  end of every narration block.)
- **Line things up**. Items in a row share the centre line of their pictures,
  not of their labelled groups (a label under an icon drops the group centre), so place a labelled
  group by its image or icon (a `place(g, p)` helper) and draw arrows from `g[0]` to `g[0]`. An arrow
  joining a row is exactly horizontal, one joining a column exactly vertical; a deliberate branch is
  clearly diagonal (> ~12 degrees). Titles sit at `to_edge(UP, buff=0.85)`, clear of the nav chips.
  (vlint: `arrow-skew` warns at 0.6-12 degrees off axis, `title-margin` when a title's top is
  within 0.75 of the frame edge.)
- **Air under the title**. When the title moves, the content below moves with it: keep
  ~0.2 between the title's baseline and any shape, image or diagram (a subtitle may sit closer).
  (vlint: `title-gap`.)
- **Label curves beside them, never on them**. A curve label goes next to one data point on
  the open side (left of a rising stretch, below-right of the last points), not centred on the peak
  where the line runs through it. A comparison arrow between two captions runs straight between
  them; it never ends inside a caption. (vlint: `line-over-label` for any curve, line or outline
  through a text; `arrow-over-label` also flags an arrow that ends inside a text.)
- **Moving curves are polylines**. A curve rebuilt every frame (`always_redraw`) is drawn
  with `VMobject().set_points_as_corners(points)` from a fixed, dense sample set, extra-dense around
  any peak or edge. `ax.plot` at a fixed step samples a narrow peak at a different height each frame
  and its Bezier smoothing overshoots at the edge, so a sweeping Bragg peak flickers. (vlint:
  `redraw-plot`.)
  The function itself must also be smooth in the parameter: a singular core sampled on a grid that
  moves with it (a Bragg peak at z = R, renormalised by its sampled maximum) pumps the whole curve
  as the peak crosses grid points. Average singular parts over each grid cell (integrate them
  exactly). (vlint: `redraw-jitter` steps each animated ValueTracker through its range, redraws the
  curves and flags heights that reverse direction again and again.)
- **Space rows by what is drawn in them**. A row of shapes drawn to scale (cones, bars,
  spectra) gets the room its biggest member needs: compute each shape's real extent and place the
  rows from that, never on a fixed pitch. A caption sits above the tallest shape, not above the
  row's anchor point. (vlint: `shape-overlap` measures the real overlap of filled shapes and flags
  partial overlaps; `line-over-label` samples long straight edges densely.)
- Generated images need an alpha channel, otherwise they are opaque black squares
  (`shell_pet` Images).

## Style
- Background `#0f1117`, with diagram colours defined at the top of each script.
- Key numbers go in `\textbf{}` (or `\mathbf{}` in maths), in the concept's accent colour.
- Schematic drawings say so.

## Narration (Chatterbox)
- Spell out what must be said:
  - numbers: "one point eight two";
  - units: "millimetres";
  - acronyms letter by letter: "L S O";
  - chemical names: "caesium iodide", not "CsI".
- Use short sentences and avoid a bare "l". After the draft, read the Whisper check, which catches
  real mispronunciations ("Poisson" was heard as "Hwasong").

## 3D, when it is used
- **Draw order is by face centre, and flat objects are drawn after all 3D faces.** Don't mix the
  two in one region. Either keep everything 3D, or make the scene flat (`shade_in_3d = False` on
  the whole family) and add in physical order: underneath first, then a translucent fill, then
  the insides, and the outline `Line`s last with `bring_to_front` after each addition (`wt_pet`
  Block). Markers that must sit in front (arrows, rays) get `shade_in_3d = False` (`slab_crlb` Intro).
- **Cost.** A rotating scene with hundreds of prisms took about 40 minutes at 1080p. Stop the
  rotation before the last voiceover, so a static camera reuses frames. Use flat `Dot`s for clouds
  and render 3D scenes first. Recolouring a surface every frame costs about 10 minutes
  (`brain_swin`).
- Scale every part from one unit and write the conversion down (`wt_pet` Sparse was built 10× too
  big). Fix text in frame with `add_fixed_in_frame_mobjects`. Rotate at about 0.1 rad/s, and only
  while the object is being discussed.

## Reusing a figure
- **Licence first.** "All rights reserved" means redraw (`liquid_tc`, Moliner 2012). CC BY means
  reuse with an on-screen credit ("Fig. 3: Sun et al., IEEE JBHI 2025 (CC BY 4.0)"). Your own
  manuscripts are fine to reuse.
- Render with `pdftoppm -r 300 -x -y -W -H` (poppler, through pixi), crop to the panel, and save to
  `<video>/assets/`. Show it on a white `card()`. Check for stray panel letters. Read figure-only
  numbers from a zoomed render.
- Anything holding an image is a `Group`, not a `VGroup`, including inside `fit_frame` (vlint:
  `vgroup-non-vmobject`).

---

# Part III: Workflow

1. Read the source, identify the kind of resource, and write the viewer's intent in one sentence
   (Part I, "Start here"). Then plan the scenes to serve it (5–8 min by default). For each scene, note
   the mechanism it explains and whether each figure is reused or redrawn.
2. Copy `videos/_template/` to `videos/<name>/`, rename the script, and set `SCRIPT`, `OUT` and
   `SCENES` in its `render.sh` (the pipeline itself is `tools/render_lib.sh`). Lay out with common.py's
   helpers rather than by eye: `title()` (every title on one line), `CONTENT_TOP`/`top_at()` (content
   starts under it), `place()` (a labelled group centred by its picture) and `grid()` (fixed pitch,
   short rows centred).
3. Check: `python tools/vlint check <video>` after every edit. Fix every error. Read the warnings as
   questions (is this label a sentence? is the eye left alone here?). For the runtime rules without
   rendering, run a scene in skip mode inside the video folder (each play() jumps to its end; seconds
   per scene, narration from the cache): `VLINT_OUT=chk pixi run manim -ql -s --media_dir m_<Scene>
   <script> <Scene>`, findings in `chk/<Scene>.vlint.json`. render.sh runs the same checks and stops
   on errors, then checks every scene while it renders and the joined file after. When the rules
   change, it re-checks in skip mode the scenes it would not re-render (the rule set is part of each
   record), so old findings never pass for current ones.
4. Draft: `QUALITY=-ql bash render.sh` inside the video folder (Linux or WSL). Narration is
   generated before any scene renders, by `tools/voice_prepass.py`: two Chatterbox copies
   (`VOICE_WORKERS`, ~4.6 GB of GPU each; use 1 on a smaller card) share out whole scenes and fill each
   scene's cache, so the scenes only read audio and render CPU-only (by default all at once, longest narration first, capped by cores and RAM; `JOBS=n` to override); a scene starts rendering as soon as its own narration is cached, while the rest is still being voiced. Never let
   scenes generate their own voice side by side: one model per scene overflows the card and crawls.
   On WSL, rendering from the Linux filesystem is much faster than from `/mnt/c`
   (`tools/wsl_render.sh` copies the repo there and renders).
5. Review with `bash tools/sheet.sh videos/<name> <res> <outdir> <scenes...>` (a 3×3 sheet per scene),
   plus frames around dense moments, and the `[vlint]` runtime findings (clipped or overlapping labels,
   vanished objects). Fix and run render.sh again: it re-renders exactly the scenes whose code, shared
   helpers or assets changed (each scene's fingerprint is stored beside its video), so there is nothing
   to delete by hand.
6. Final: `QUALITY=-qh`. **Never above 1080p** (render.sh refuses more). The join is
   refused if a scene is missing, stale or has a runtime error, and the joined file is checked for size,
   length and audio drift. Send a 1080p crf 26 re-encode (`_small.mp4`) when the file is over 30 MB,
   never a downscale. A video rendered before vlint existed: `vlint adopt` its unchanged scenes once,
   so only the edited ones re-render.
7. Update this file (§0), then report.

Tooling: **ManimGX renders, Manim CE checks.** `ENGINE=gx` (the default) renders each scene with
[ManimGX](https://github.com/academa-labs/manimgx) on the GPU. Under WSL it calls a Windows install through
interop (`GX_EXE`), because WSL has no NVIDIA Vulkan driver. `ENGINE=ce` renders with Manim CE and needs no
ManimGX. `common.py` dispatches to `common_gx.py`, whose `Narrated` replays the voice pre-pass cache with
`add_sound` and times `self.at()` from the word timings. vlint's runtime record still comes from CE in skip
mode, so **every scene must run under both engines**: write the API they share. ManimGX typesets with Typst
(LaTeX converted by mitex); common_gx patches `\'` accents, `\&` and `\ `, and a LaTeX package mitex lacks
fails the render. A 10-minute, 15-scene video builds in under 2 minutes instead of 6, and 3D scenes render
~50× faster. ManimGL was ruled out: different API, no voiceover.

---

# Part IV: Pitfalls

**Editing scripts**
- Any edit touching a LaTeX backslash goes through the Edit tool, never a Python replace script.
  In a non-raw string, `"\t"` in `\textbf` or `\tau` becomes a tab and the match silently fails;
  this happened in three videos, and twice more while writing vlint itself. Python scripts are fine for
  backslash-free changes such as numbers and positions. For whole scenes, Write the new classes to a
  scratchpad file and splice them in.
- Every `Tex`/`MathTex` string with a backslash is raw (`r"et al.\ 2020"`) (vlint: `tex-not-raw`,
  `control-char`, `syntax-warning`).
- Adjacent raw strings join with no space.
- Keep a variable for anything you will remove later. An object created inline in `play` can't be
  faded out.

**Naming**
- Never name a scene class after a manim object (`Flash`, `Circle`, `Dot`, `Line`...). A scene called
  `Flash` shadowed manim's `Flash` animation, and another scene in the same file crashed with
  "Scene.__init__() got an unexpected keyword argument 'color'" (laser review video) (vlint: `shadows-manim`).

**Manim 0.19**
- `LaggedStartMap` crashes; use `LaggedStart(*[...])`.
- `MathTex("")` fails.
- `Tex` options are set at creation.
- `match_y` takes a Mobject; for a point use `.set_y(p[1])`.
- Never `FadeIn(x)` and `Indicate(x)` (or `Circumscribe`) on the same mobject in one `play`. The pulse
  overrides the fade, and the object ends up invisible: map boxes, B symbols, an image charge and a label
  all vanished this way (Feynman Vol. II; the synchrotron magnets in `laser_rt`). Fade in first, then
  pulse in a separate `play` (vlint: `intro-and-pulse`, and `vanished-after-intro` at render time; the
  first run found four more in `laser_rt` that had shipped).
- Never `Indicate` an image. It recolours the whole picture into a flat yellow or white wash for the length of
  the pulse. Pulse its frame or `Circumscribe` it (vlint: `indicate-image`).
- Dimming the rest of the screen (a spotlight helper) must only touch `VMobject`s. `scene.mobjects`
  also holds `ValueTracker`s, and fading or restoring them crashes with "Please override in a
  child class" (`laser_rt` retrofit). Skip mobjects that have updaters too.
- Two labels attached to the same edge of a box (`next_to(box, UP)`) will overlap unless they are
  aligned to opposite ends (`align_to(box, LEFT)` / `align_to(box, RIGHT)`). Check a late frame of the scene
  (vlint: `text-overlap` and `frame-clip` catch label-on-label and cut-off labels; a label over a shape, such
  as a bar, is still for the eye).
- `d.get(k, f"{k:g}")` evaluates the default even for string keys; use a conditional.
- When a title changes, `ReplacementTransform` it.

**Shell (Windows → WSL)**
- `wsl bash -lc '... $var ...'` from Git Bash loses variables, so put loops in a `.sh` file.
  Run it with `MSYS_NO_PATHCONV=1 wsl bash /mnt/c/.../x.sh`, otherwise Git Bash rewrites `/mnt/c`.
- Git Bash's `/tmp` is not Windows Python's `/tmp`; write temporary files inside the repo instead.
