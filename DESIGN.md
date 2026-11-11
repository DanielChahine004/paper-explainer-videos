# Design rules for the narrated explainer videos

Read this before writing any video in this folder. Part I is the attitude, the few ideas every
other rule comes from. Parts II–IV are how to carry it out without repeating past mistakes.

The audience is a PET physics PhD and colleagues. A video should leave them understanding *how*
the work was done and *why* its numbers come out as they do, as if a sharp colleague had walked
them through the paper at a whiteboard.

## 0. This file learns

Each video should leave this file better than it found it, and this is part of finishing a video.
- **After a mistake** (a clash, a wrong number, a crash, something the user found unclear, wasted
  render time), find the rule that should have caught it. If the rule exists but did not fire,
  sharpen it. If none exists, add one aimed at the whole class of mistake.
- **After something that worked**, add it where it belongs.
- **Feedback from watching.** The user leaves timestamped notes in the catalog player; `python tools/feedback.py` lists
  the open ones with the scene, the time inside it and a frame grab. Triage every note before fixing anything:
  *incidental* (this video only), *design* (a class a reader must judge: add or sharpen a rule here), *vlint* (a class
  a program can catch: add a rule with a planted bug), or *wontfix* with the reason. Close each one with
  `feedback.py resolve <video> <nid> <kind> "<what changed>"`, so the record shows which notes became rules.
- **pet_entangled (a physics idea, then its test).** The idea was one picture before it was any number: the rate
  against the angle between two scatter planes, whose peak height is R. The same `dphi_plot` axes then carried the ceiling
  (1.63), the theory (2.85), the measurement (1.85), the loss on a prior scatter and the recap, so five scenes
  shared one figure. Plan-first held: four Sonnet writers, 13 scenes, merged with one refusal (a writer's
  module-level name `R_MAX`, which had to be `_idea_R_MAX`). What cost time: the shared helper `dphi_plot` put
  its |Δϕ| label on the "180°" tick, and all four writers worked round it separately (it is fixed by shifting `xt`
  right in the helper before the next split, not after); the plan's `plain` versus `new:`/`side:` prefixes were
  re-chosen by every writer (a cue that draws a leg or frame is `new:`); and a figure's y levels (Fig. 2's 1.63
  line) had to be measured from pixels, which the plan should hand over.
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

**The video ends on a recap of the whole paper** (user, after `geant4` and `si_psf`: "try to have the videos end
with a recap of the whole paper/takeaways so the viewer leaves with a summation of the content in mind"). The
last scene walks back through everything the video covered, in the video's own order and in a sentence
each: the question, the idea, how it works, what it achieved, and what limits it. It is not only the last
result, a list of caveats or a look ahead; those belong in it, after the summary, not instead of it. A viewer
who watched nothing but the last scene should be able to say what the paper did. Budget it when the words
are counted (Part III step 1): about a tenth of the narration, 90 to 130 words in a 5 to 8 minute video.
Its pictures are the ones the viewer already knows, brought back as each is named (below, "the closing scene
returns to the video's main picture"), never a bullet list of the claims.

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

## Order: the paper's order is not the explanation's order

A paper is written in the order that makes it defensible: definitions, then method, then results.
That is the correct logical order and it is rarely the order that teaches. Grant Sanderson's advice
for exposition (`3blue1brown.com/faq`) is the rule here.

- **Concrete before abstract.** Give the example before the general framework, and open with the key
  case instead of saving it for the end. One real trial, one real recording, one number the paper
  actually reports, before the machinery that produced it.
- **Never start with definitions.** A definition is an ending point, not a starting point. Name a
  thing once the viewer has watched it do something, so the name is a handle for something they
  already hold rather than something to memorise before they can follow.
- **The best pedagogical order is often very different from the correct logical order**, and it is
  typically backwards to how the material looks to someone who already understands it.

For these videos that cuts against the obvious route. A walkthrough that visits pages in page order
inherits the paper's logical order wholesale, and the viewer meets every definition before they have
any reason to want it. **The page order is chosen by the explanation, not by the page numbers.** Go
to page 35 early when the result is what makes the question worth asking, and come back to page 8
for the method once the viewer wants to know how it was done. Visiting pages out of order is the
normal case, not a licence to be claimed.

**The closing map serves the route; it must never choose it** (capstone A/B, 2026-11-10: one build
picked 27 pages as three rows of nine so the map's group boxes would not straddle a row -- a layout
rule deciding which pages of the report a viewer visits). Lay the map out around whatever route the
explanation needed, however ragged that leaves it.

**Every movement on screen is deliberate, and makes the same point the narration is making**, so the
two reinforce each other instead of competing for the viewer's attention. This is the reason behind
the cue rules in Part II rather than a separate idea: motion with no identifiable purpose spends
attention that was being paid to the sentence. It does not contradict "neither repeats the other" in
§1 -- the picture must not repeat the *words*, but it must be about the *same thing* at the same
moment. When a scene's arrows, tiles and gauges are each defensible yet the viewer cannot tell where
to look, the scene is competing with itself (capstone A/B: Separation, five arrows fanning to
unlabelled tiles while five more curve back).

**Know the genre.** These are not lectures and not conference talks: a reader who will probably never
open the paper is being told what is in it and shown how it works, by someone who has read it. Pacing
and depth follow from that and from the brief's audience line. Habits borrowed from another genre --
a lecture series, a research talk, a channel teaching a subject from scratch -- can be actively wrong
here, however well they work there.

## 1. The voice explains; the screen shows

Narration carries the argument. The picture does two jobs the voice can't: it shows the viewer
**where to look**, and it gives them **a way to picture the idea**, a form they can think with after the
voice has moved on. Neither repeats the other. Every rule below serves one of those two jobs.
- **Draw, don't write.** Text on screen is a label or a **bold number**, never prose. That means
  about 3 short lines per scene besides titles and diagram labels. A spec list becomes a drawing of
  the object with dimension arrows. A pipeline becomes the data passing through its stages. Specs that
  differ in kind become tiles, each a picture of the thing plus a number. Any `Tex` holding more than
  about 3 words is a candidate for a shape (vlint: `long-text` warns past 8 prose words; numbers and
  units don't count).
- **Script the picture in the viewer's head, moment by moment** (user, after `pet_diffusion`: "what should the
  user be envisioning reading this section, what image should they have in their head at every moment and how
  can i illustrate that best so they have a faithful mental model of everything"). For every sentence, write down
  the image a listener would form if they understood it perfectly, and put that image on screen while it is said.
  A sentence about a mechanism (a step that jumps, a weight that trades two terms, a starting point that is moved)
  gets that mechanism drawn on the running picture the viewer already holds, not a highlight and a label. In
  `pet_diffusion` the shared picture was the plane of images with plausible ones on a curve: D D I M became fewer,
  longer hops along the same path; Bayes became two arrows adding at one point; D D S became the jump to the clean
  estimate before the data step; a hot start became a path that begins halfway down; the prior-versus-data weight
  became samples sliding from the line onto the curve. Check a scene by listing its sentences next to what is on
  screen during each: a sentence whose row says "page highlight" or "label" alone is a gap, unless it is only
  pointing at where something is in the paper.
- **One central figure, mutated** (user, `lnp_comet`: "have a central figure of interest which constitutes the
  focus of the scene's content, and focus on mutating, transforming, interacting with, and overall just employing
  that central visualisation ... a central entity which gets transformed and interacted with as it would in
  reality"). Each scene is about one thing: name it before writing the scene, draw it once, and let every block of
  narration do something **to that same object** rather than introduce a panel of its own. If the scene is about
  what a recipe fixes, the particle is on screen the whole time and the four lipid classes are placed into its
  shell, the percentages are its shell's composition, the knobs are turned on it. If it is about ablating a
  model's inputs, the input bundle is the figure and each ablated property leaves it and comes back. If it is
  about what a membrane is made of, the membrane is drawn and the pieces are taken out of it. The object changes
  as it would in reality: a part is removed, a quantity in it grows, it is cut open, it is stacked, it travels.
  Graphs, bars and metrics live alongside it when the scene is about a measurement, and the figure stays put while
  they come and go. The failure this replaces is a scene of four unrelated panels, each built on its own
  bookmark and faded out before the next (vlint: `scene-protagonist` warns when the busiest picture in a scene is
  acted on in under 60% of its narration blocks; calibrated on this repo, where the median scene reaches half and
  a scene built round one figure reaches three quarters). A decorative copy of the subject parked in a corner and
  never touched is the tell: that is the thing the scene should have been built on.
- **Every visual does work: draw the form the viewer should think in** (user, after `flow_match` and
  `subseasonal_pbc`: "use the visuals functionally not just illustratively ... not just an icon placeholder";
  "the visuals show the viewer where to look and how to envision and conceptualise the information").
  Before a scene, decide what mental picture the viewer should leave with, then draw that picture and use
  it. A visual earns its place when the narration acts on it:
  - **point at a property** of it (its width, its peak, the part that moves, the term that matters);
  - **change it** while the voice says what changes (a parameter sweeping, a curve deforming, a cloud sharpening);
  - **measure on it** (a number on the length it is, a double arrow across the gap).

  If no sentence will touch it, it is an icon standing in for a word: drop it and let the label stand, or
  draw the real object at work. A row of pictograms labelled "field, loss, steps" (`flow_match` Intro) says
  nothing the words don't; the actual field turning as t runs, the real loss curve falling and the same
  samples sharpening as the step count grows do (vlint: `icon-idle`). Choose the form by the kind of
  information:

  | The narration is about | Draw it as | So the viewer can |
  |---|---|---|
  | a quantity | a length, area or count on the thing it measures | see its size, and what it is the size of |
  | a comparison | both on one scale, side by side or overlaid, the difference drawn as the gap | see which is bigger and by how much |
  | a dependence (X affects Y) | X moved on screen, Y responding live | feel the direction and steepness |
  | a process or algorithm | the data passing through it, inputs → box → outputs; one item slowly, then many | follow what each stage takes and gives |
  | uncertainty or a distribution | a cloud of samples, a spread, the overlap of two clouds | see how likely and how separable |
  | an abstract space (parameters, features, channels) | each case a point, similarity a distance, a family a curve or sheet | reason about it as geometry |
  | a constraint or an optimisation | the allowed region as a shape, the landscape and the path down it | see why the answer lands where it does |
  | an equation | each term tied to the part of the picture it describes (same colour, pointed at as read) | read the maths as the picture |
  | a structure (taxonomy, hierarchy, design space) | a layout whose position means something: axes, nesting, branches | locate each item by its properties |
  | a sequence in time | left to right at real durations, with the moment in question marked | see order and proportion |
  | a physical mechanism | the event itself, animated (a photon converting, light spreading, a charge moving) | replay it in the mind |
  | a claim ("better", "fails", "converges") | the evidence that makes it true: the gap, the overlap, the residual, the curve flattening | check the claim with their own eyes |

  The closing scene returns to the video's main picture rather than a bullet list of the claims: `pet_explorer`'s
  takeaway pulses each claim's arrow on the count-budget ruler the viewer already knows, instead of five lines of text.
  Keep the picture alive across the scene and the video: build on it, transform it into the next form,
  and keep one colour per concept, so the viewer's picture accumulates and is never replaced by a fresh
  one. Test: mute the sound and freeze any frame. A viewer should be able to say what is being discussed,
  point at it, and guess what would change if the quantity changed.
- **No words pointing at words** (user, recon video). A flow diagram whose nodes are text boxes
  ("sinogram → OSEM → CNN → image") explains nothing the narration doesn't. Each node is a picture of the
  thing with a one-word label under it: the sinogram as a thumbnail, the reconstruction as a detector ring
  with lines, a network as layers of nodes joined by edges, the image as the image. Keep a text box only
  where there is nothing to draw (vlint: `text-chain` warns at 3 text-only boxes joined by arrows).
- **Build on what is already on screen.** Once a thing is drawn, its properties are shown on it rather
  than beside it: an edge is a band on the profile across the object, a blur is that profile going soft,
  a width is a double arrow across the thing, contrast lost is a bar from the peak reached to the true
  peak, a weight is the shading of the voxels a line crosses. A dashed line on the image shows where
  the profile runs. The narration word that names the property carries the cue (vlint: `property-scope`
  warns when "width", "edge", "contrast" and the like have no bookmark within 6 words before them).
- **One thing that reports two readings is drawn once** (user, `pet_nn_timestamp` Intro: "using two sipm arrays here
  wasn't good illustrative use to show the recording of counts and timing"). Two copies of the same detector, one
  shaded by each reading, read as two detectors. Draw the one array, open up one element beside it (its pulse: the
  height is the light caught, the crossing of a fixed level is when it fired), and show the second reading across the
  array as an event on it (a ring spreading from the hit in firing order).
- **A number sits on what it measures** (user, `subseasonal_pbc`: "printing a number in a box on screen doesn't
  show where in the image it is or what in the graph it is speaking to"). A value goes on its bar's end, a score on
  the distance it measures, a gain on an arrow from the old level up to the new top, a ratio as copies of the
  smaller bar laid end to end along the larger, a percentage of cells as a grid of cells. Where it cannot sit on
  the thing, a leader line joins them. A number in a corner, or a "+30%" floating over a group of bars, is a
  caption, and the eye has to guess what it refers to. Test: cover the narration; can the viewer still point at
  what each number is the size of?
  Every number the voice says with a unit is drawn while it is said (user, `pet_explorer`: "annotate 22 cm", "show
  57 degrees", "the 430 and 645 keV window edges on the x axis"): a length is a dimension line with end ticks, an angle
  an arc between its two rays, a window or threshold a tick on the axis it lives on. If a spoken number has no place
  in the picture, say it without the unit or cut it (vlint: `number-undrawn` warns when a spoken number with a unit
  is nowhere on screen during its sentence).
  A spec read out as a line of text beside the drawing breaks the same rule (user, `pet_nn_timestamp` Clock: "'3mm each'
  coulda been labelled on the diagram, and even the 64 sipms could've been numbered"). A count is the things
  themselves, numbered as they appear; a size per item is a dimension line on one item; a thickness is a side view with
  the dimension on it.
  A number that changes keeps the old value readable: say the old value on one bookmark and the change on the next,
  and when the comparison is the point, leave the old value on screen beside the new (user, `pet_nanocomposites`
  Composite: "the 1.02 -> 1.5 bar expansion happened too quickly, couldn't read 1.02"; it now shows a grey "plain"
  bar under which the "with grains" bar grows). vlint: `number-flash` warns when a number is replaced or removed
  less than 1.5 s after it appeared.
- **Name every colour series on screen** (user, `pet_explorer` Coverage: "a key for the blue and orange lines").
  When two or more colours mean different things (two scanners, two methods, measured and simulated), each gets its
  name on screen as it appears: a label beside the curve, or a key entry (a short swatch of the line and its name).
  Colour named only by the voice is lost as soon as the voice moves on.
- **Animate the event, not a pulse on its picture** (user, `pet_explorer` Acceptance: "show the two photons
  emanating"; "the shake doesn't show most leaving through the open ends"). When the voice says something happens
  (photons fly apart, most escape, a bolus moves), show it happening: dots travelling along their paths, the escaping
  ones leaving through the gap. A `Wiggle` or `Indicate` on a static drawing says "this", never "this happens".
  Raising a fresh arrow and a fresh box beside the thing is the same failure wearing a different coat: the object
  the viewer is already holding has to be the one that moves (user, `lnp_comet` Intro: "instead of an arrow the
  lipid nanoparticle should've gone into the cell, dissolved or whatever it does, and the mRNA released as the
  narration says"). The particle travels to the cell, its shell comes apart, the message slides out inside.
  Turn it around too: **cue a thing only where the narration gives the cue a purpose.** A pulse that marks
  nothing the voice is doing anything with is decoration, and it teaches the eye to ignore the next one
  (vlint: `pulse-for-event` warns when a clause says something is done to a thing on screen and the cue neither
  moves nor changes anything — `CHANGE` lists what counts).
- **Write the cue before the picture.** For each clause ask what the viewer should see *happen*, then build the
  object that can do it. A scene whose cues are mostly "something new appears" is a slideshow with a voice over
  it; one whose cues are mostly "the thing on screen does something" is an explanation. `vlint cues <video>`
  prints the split and lists every cue that only points at something, with the clause it fires on. There is no
  threshold and no gate -- a thing named for the first time *should* appear, and a thing named again *should* be
  pulsed -- it is there to be read while writing. `lnp_comet` sits at roughly a third change, a half
  introduction, and under a tenth pure pulse; a scene far off that is worth a second look.
- **Appear as it is named; pulse it when it is named again.** Each thing arrives on the word that names it
  and not before. When the narration names something already on screen (a crystal, a detector pair, a
  number), it gets an `Indicate` or `Circumscribe` on that word, so the eye always knows where to look. When a
  sentence names three things, that is three cues. Equations are lit term by term as they are read.
  Write an equation in its parts (`MathTex(a, b, c)`), each part on the word that names it, and while the
  voice reads or reuses a term already on screen, keep the **term marker** on it: `point(self, eq[k])` (common)
  moves one box from term to term on each bookmark, and `unpoint(self)` at the next block's first cue. A
  whole equation written at once and then talked over leaves the viewer hunting for "that minimum" or "the
  exponent" (user, `zzb_slab`: "when speaking about parts of the equations they don't pulse or get signalled
  in any way, so it's hard to track"). Every symbol the voice names (a term, a factor, a limit, an
  inequality sign) is a cue (vlint: `equation-talked-over` warns when a multi-part `MathTex` is written
  whole in a block that cues none of its parts).
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
    the width or a bar between two levels, and pulse that (user, recon video: "when speaking of a width show
    the width on the entity");
  - **a method with two readings** (sinogram and list mode, matrix and event by event): show both, the
    sinogram view and the individual lines being traced, so either intuition lands.
  - **feedback loops in a box diagram:** route the return arrow above or below the row as straight
    segments, never a `CurvedArrow` across the boxes. No arrow's shaft may cross a label: end it at the
    label's side (vlint: `arrow-over-label`).

  While a part of the picture is being discussed, dim everything else to about 30% opacity, then
  restore it. Target at least one cue per sentence. A voiceover block with fewer bookmarks than
  sentences is a sign the eye is being left alone (vlint: `cue-gap`, `bookmark-unused`).
- **One idea at a time.** One development per scene, with the diagram left and labels right. Build
  the whole panel, fit it to the frame, then reveal it piece by piece so nothing jumps.

## 2. Explain the mechanism, not just the name

Naming a technique explains nothing. For any method that matters (a solver, a loss, a calibration,
a reconstruction), show the problem, what the naive approach does and why it fails, and the fix as
concrete choices (what is computed, what is kept). Give derivations one line at a time.
- **Technical means the mechanism, not the algebra: lead with the picture** (user, `zzb_slab`: "I still
  don't understand how the ZZB and Bhattacharyya work, bit too much equations and maths; focus on the
  intuition in the geometry and distributions"). A derivation shown step by step can still leave the
  idea unseen. Find the picture in which the method is obvious, and let equations be at most one label
  on it. For statistics: an event is a dot, a hypothesis is a cloud of dots, a test is a boundary, its
  error is the dots on the wrong side; a bound is a statement about how clouds overlap (square-rooting
  Poisson counts makes every cloud round and the same size, so overlap is just distance); an unknown
  parameter sliding is a path traced by the cloud's centre, and local versus global bounds are "near the
  truth" versus "every rival on the path". Draw the distribution, not its formula. A constraint is a shape and
  enforcing it is the nearest point on that shape: valid 3-threshold CDFs fill a tetrahedron whose corners are the
  possible observations, so a score is a distance to a corner and projecting onto the convex shape moves closer to
  every corner at once (`subseasonal_pbc` Project).
- **Why before how, then what it costs** (user, calibration video). Before a procedure, show the failure
  it prevents, as an animation with a live number (a gain error pushing the photopeak out of the window,
  "photopeak kept 10%"). Then show the procedure step by step. Then say how often it is redone and how
  long it takes, using reported times only. A topic the viewer can't yet see the need for gets a why-scene
  of its own. Length follows the content: going past 8 minutes is fine when each scene earns its place.
- **Name each component by what goes in and what comes out** (user, flow_match). When a process or
  computation has parts (a network, a solver, a training step, a sampler, a reconstruction), say for each
  one what it receives and what it produces ("takes a noisy point and a time, outputs a velocity"), and
  draw it as inputs → box → outputs, with the inputs and outputs as pictures (a dot for a point, an arrow
  for a velocity, a cloud for noise). When two methods are compared, compare their inputs and outputs
  side by side (flow matching outputs a velocity; a diffusion model, given the same input, outputs the
  noise). Use `io_box` in `flow_match` as the pattern.
- **A whole process is one picture that grows, not icons joined by arrows** (user, `pet_nn_monolithic`).
  When the intro or a scene runs through a chain of steps (detector hit → readout → algorithm → answer),
  build it in one place: draw the detector, show the hit, let the readout light up beneath it, carry those
  readout values into the network (TransformFromCopy from each value to its input node), and land the
  answer back in the detector next to the true hit. Each step adds to what is already on screen. Draw
  the real readout geometry the paper uses (an 8 × 8 sensor grid with its row and column sums), never a
  generic bar distribution standing in for "the signals". Intro of `pet_nn_monolithic` is the pattern.
- **Method before result.** Name the simulation code and settings, the detector model, the
  reconstruction and its update equation, and the standard test (NEMA etc.), with the numbers that
  define them. Results come after the method that produced them.
- **Recompute what you can.** If the paper states a model (a cost formula, a coverage criterion, a
  neuron equation), run it in numpy inside the scene and label the result "computed here". This means
  evaluating a model the source states, not building a simulator the source didn't need; for that, see
  "Illustrative is a valid answer" in §4.
- **A short draft needs more explanation, not padding.** Under 5 minutes, find a mechanism the
  narration only names and give it its own scene (`mouse_pet` Motion).
- **Show the algebra move by move** (user, liquid_tc). When the narration substitutes, rearranges,
  expands, factors, cancels or solves, the terms move on screen; one equation never fades out for the
  next to appear. Map the parts by hand (split the MathTex into the pieces that move):
  - substitute: light the symbol and its definition, then `TransformFromCopy(defn[k], new[j])` flies
    the definition into the slot while the old symbol fades out, `ReplacementTransform` for the rest;
  - expand, collect, rearrange, divide through: `TransformMatchingShapes(old, new)` (or
    `TransformMatchingTex` when the parts carry the same strings), pulsing the terms that move first;
  - factor: light the common factor in every term, then transform to the factored form;
  - cancel: `Cross` the pair, then remove it;
  - keep the earlier line on screen when the derivation is a stack (`TransformMatchingShapes(d2.copy(), d3)`).
  In ManimGX, `key_map` together with a `TransformFromCopy` into the same target crashes: map the parts
  explicitly instead (vlint: `algebra-shown` warns when such a block moves no term).

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
- **Show where many channels go** (user, zzb_slab: "how are the counts of the 64 SiPMs encoded into this
  abstract space?"). When a 2-channel picture stands in for N channels, add the real N-dimensional version:
  - the model's output as one point with N coordinates (io_box → heat map → point);
  - the family of possible outputs as a curve or sheet, drawn on the 2–3 principal axes, with the share of
    variance they keep as a bold number;
  - the per-channel terms as a map that adds up to the one number;
  - the Jacobian's columns as maps, so "the Fisher matrix" is dot products of things on screen.

  When a global projection dwarfs the effect (a sheet 36 units wide around a cloud of half a unit), redraw
  it in a local frame at true lengths: two tangent directions and the normal (`zzb_slab` Space, OffSurface).

## 4. Every mark is true

Everything on screen is either from the source, computed from the source's own model, or
labelled illustrative/schematic.
- **Numbers come from the extracted text or tables, never from memory or a summary.** Grep the
  source for every number in the script before the draft (`shell_pet`: 3.66 from memory was 3.59).
  Work counts out from the source. Show the source's precision, formatted per metric, not per
  magnitude (`liquid_tc`: 1.512 became 1.51). (vlint: `number-unsourced`, which reads `src/*.txt` and
  holds every decimal and every whole number from 13 up, spoken or on screen, against it. A correct
  rounding of the source's number passes, and so does the same number written another way ("ten million"
  for "10 million", 0.93 for 93%); a page or figure number is a place, not a value. A table the PDF holds
  as an image is not in the text at all, so its numbers are flagged too (`pet_hetero_nn`, Tables II and
  IV): read them off the page render and say so on the line. A number the
  video computed keeps its line with `# vlint: ignore[number-unsourced] computed: ...`, which is also
  the list of what the screen must label as ours.)
  **The rule being silent is not the numbers being right** (geant4, its first real build: it raised nothing,
  and planted errors showed why). Three holes, closed the same day: `tools/sync.sh` did not copy `src/` to
  the render root, so under `check.sh` and `render.sh` the rule found no source and stood down; a label
  helper that wraps its argument (`num(t)` builds `r"\textbf{" + t + "}"`) was not recognised as one, so
  every bold number on screen, which is every headline number, went unread (a planted 17 000 and 972 400
  passed); and the reference list and the `[12, 13]` citation marks hold nearly every year and small whole
  number (a planted 1997, 238 and 70 all "matched"), so both are now left out of the source. What remains
  cannot be closed: a wrong number that the paper prints somewhere else, or that is a rounding of one, still
  passes (the planted 1700 does). The rule catches a number from nowhere, not a number in the wrong place,
  so the grep by hand for the headline numbers stays.
- **Narrate a computed number only after computing it.** If a scene's own model produces a value
  (an error, a fraction), run the model before writing the sentence. The calibration video's k-NN
  demo was scripted as "about a millimetre", but the computed error was 0.4 mm.
- **Animate through reported values only.** Use `np.interp` between them, with no invented curve
  shapes. Keep scales fixed during a move.
- **When your own model contradicts your script, the script changes.** In the i3M Light scene, the
  model showed reflective walls do not compress positions more than black paint, so that claim
  was cut. The same goes for a drawn example: a claim made in general ("at 2 keV the likelihood grows a second
  peak") must be visible in the one case on screen (`zzb_slab` Local showed one peak; the scene was cut).
- **Illustrative is a valid answer; ask before building a simulator.** When the source's data are
  missing, a schematic labelled illustrative often explains the method as well as a computed one. The
  user's reaction to `zzb_slab`'s from-scratch light Monte Carlo and GPU Monte Carlo of P_min: "no need
  to code it all yourself; it could just be theoretical/illustrative". Compute only what the argument
  needs, and say on screen which parts are computed here and on what assumptions.
- **A shape on a scale states a value, label or no label.** A second bar standing on the axis a measured bar
  stands on is read off that axis: its height is a claim whether or not a number sits on it, and leaving the
  number off hides the claim rather than withdrawing it. capstone's rebuild drew "the subject it does best on"
  as a bar 0.35 high beside a real 0.18 -- the report gives that subject's confidence (0.922 and 0.913 against
  0.897) and no separation at all. When the thing is named but not measured, draw it as a thing and not as a
  quantity: it is now a person standing where the bar stood, with the dial that is the point of the sentence
  above them. Ask it of every unlabelled shape that shares a scale with a labelled one.
  **A drawing to scale states a value too, so compute what it states before drawing it** (pet_g4_configs). The
  obvious picture of acceptance was the scanner from the side with gamma pairs fanning out of the centre, the caught
  ones lit. At the paper's own geometry that picture says about 45% for Ring-PET, 16% for Ring-PET2 (its four rings
  of 5 mm crystals are a third as long) and 4% for the flat modules; the paper reports 17.41, 14.54 and 14.49%. Any
  fan drawn to scale would have contradicted the bars beside it. The picture became a grid of a hundred
  annihilations with seventeen lit, which states only the reported number, and the mismatch went where a reader can
  use it: a caveat in Limits, crystal area drawn as area (21,600 against 3,200 mm2, computed) beside acceptances
  within a fifth of each other. Five lines of arithmetic on the paper's stated geometry, done while planning,
  decided both scenes.
- **Real data stays real.** Reuse the paper's own figure for real data (photos, reconstructions,
  measured maps or spectra), for dense plots that would be slow to rebuild faithfully, and for the
  result the paper is known for. Redraw mechanisms and schematics, and pull out
  the 2–4 numbers that matter from busy figures and tables. Decide this per figure, in the plan.
  Use about 2–4 reused figures per video, each highlighted and given time to read.

## 5. Clarity before spectacle

- **Reach for 3D.** When something has a shape, show it in 3D: detectors, geometry, surfaces,
  fields, a function of two variables. A slow camera move gives depth for free, and ManimGX makes
  it cheap. Stay flat only when the idea is a 1D plot or a diagram. Check draw order (§III-3D).
- **Readable at 1080p.** Keep everything 0.3 units inside the frame, with text at least 24 pt and
  labels in empty space. Nothing overlaps; check every frame of the contact sheet.
- **One look across videos.** Dark background, one accent colour per concept used consistently,
  and a shared palette and helpers in `common.py`, with the drawing primitives in `kit.py` (`KIT.md`).

---

# Part II: Craft

## Sync (manim-voiceover)
- Put `<bookmark mark='x'/>` directly before the noun or number, glued to it:
  `"captured at a <bookmark mark='act'/>luminescence centre"`. Then use `self.at("x", anim)` from
  `common.Narrated`, which waits for the bookmark and plays the animation. Cues follow the text's order,
  each bookmark once (vlint: `bookmark-missing`, `-order`, `-duplicate`, `narration-markup`, and
  `bookmark-unfired` at render time).
- **Things appear in the order the sentence names them** (user, `pet_3dcnn_tof`: "should've shown the
  crystal first since it was first mentioned, and then shown the sipms - in step with the words"). Give
  each named part its own bookmark, even inside one sentence, and lay the parts out in that order, left
  to right, so the eye reads them as the ear hears them.
- **Nothing is said for long over a still picture** (user, `lnp_comet`: "place more emphasis on
  illustrating what is being narrated as it's being narrated such that when something is said, it happens
  visually, synchronised"). Every clause that names a thing, a step or a number gets its own bookmark and
  its own cue, so the picture moves roughly every three to four seconds and never stands still for ten.
  Count words, not sentences: a block can look busy on average and still hold one frame through
  thirty words of talking (vlint: `cue-gap`, 24 words ≈ 9 s). The tail of a block counts too — a last
  sentence delivered over a finished picture is the commonest dead stretch.
- A cue is something **happening**, not a label landing: the step the voice describes is performed on the
  picture at the moment it is described — the mixer turns, the frames shuffle, the bar grows, the dot walks
  the path. Where the voice says a thing is shuffled, shifted, split, stacked or averaged, show that verb
  being done to the thing on screen; a static picture of the result with a word beside it is the mistake
  (user, `brain_swin`: "showing the shuffling of the frames would've been more illustratively supportive
  for the graph").
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
- **Name a curve beside it, never inside it** (user, `pet_3dcnn_tof`: "over lap on the plot here"). Put
  the name just off the curve's shoulder, where no other curve passes. Silence the warning on the
  curves and lines alone (`d[0]`), never on a group that holds the label, or the lint cannot see it.
- **A chain of shrinking stages has even gaps** (user, `pet_3dcnn_tof`: "the spacing between the cubes
  and the arrival time dot seems a bit weird"). Space stage to stage the same, join a dense layer to its
  output with wires, and put the output's name beside it, not under the stage before.
- Place labels with explicit coordinates (`ax.c2p`) when curves could cross them. If lines will
  pass through a label, give it a background rectangle and `set_z_index(3)`. The y-axis title needs
  `buff >= 0.95`.
- The bottom 0.5 units belong to the footnote or credit, so keep plots above y = -3.3.
- **Use the space, evenly** (user, recon video). Lay panels out on a grid that fills the frame below
  the title: columns for things compared side by side, rows for stages, flow left to right and top to
  bottom. Keep at least ~0.3 units between panels; when they nearly touch while part of the screen is
  empty, spread them out instead of shrinking them. When a scene builds in two halves, centre the first
  half while it is alone and slide it up when the second arrives (recon `Unrolled`). (vlint:
  `layout-crowded`, `layout-balance`, checked at the end of every narration block.)
- **Line things up** (user, recon video). Items in a row share the centre line of their pictures,
  not of their labelled groups (a label under an icon drops the group centre), so place a labelled
  group by its image or icon (`place(g, p)` in recon) and draw arrows from `g[0]` to `g[0]`. An arrow
  joining a row is exactly horizontal, one joining a column exactly vertical; a deliberate branch is
  clearly diagonal (> ~12 degrees). Titles sit at `to_edge(UP, buff=0.85)`, clear of the nav chips.
  (vlint: `arrow-skew` warns at 0.6-12 degrees off axis, `title-margin` when a title's top is
  within 0.75 of the frame edge.)
- **Air under the title** (user, laser_rt BeamTime). When the title moves, the content below moves with it: keep
  ~0.2 between the title's baseline and any shape, image or diagram (a subtitle may sit closer).
  (vlint: `title-gap`.)
- **Label curves beside them, never on them** (user, recon video). A curve label goes next to one data point on
  the open side (left of a rising stretch, below-right of the last points), not centred on the peak
  where the line runs through it. A comparison arrow between two captions runs straight between
  them; it never ends inside a caption. (vlint: `label-on-ink` for a label with something else's ink
  through a text; `arrow-over-label` also flags an arrow that ends inside a text.)
- **A reading goes beside a bar thinner than the number** (user, capstone 1:19). A number belongs on the
  thing it measures, but "on" means beside it at the right height once the thing is narrower than the text:
  capstone's `53%` was centred on a 0.42-wide score bar, so both of the bar's edges ran through the digits.
  `label-on-ink` cannot see this -- it asks what share of the label's box is foreign ink, and a two-pixel
  outline is three percent of it. (vlint: `label-overhang`, which asks the narrow question that survived the
  corpus: a drawn shape of real width, much narrower than the text, at least twice its height -- a bar, a
  column, a gauge -- lying strictly inside the text's box. Asked loosely it is the bounding-box question
  `shape-overlap` and `line-over-label` were cut for: 106 findings, of which a `+` inside its own circle and
  sixty hairlines crossing a number. Narrowed, 8 over 45 videos, one per video, each one readable.)
- **Moving curves are polylines** (user, laser_rt Bragg sweep). A curve rebuilt every frame (`always_redraw`) is drawn
  with `VMobject().set_points_as_corners(points)` from a fixed, dense sample set, extra-dense around
  any peak or edge. `ax.plot` at a fixed step samples a narrow peak at a different height each frame
  and its Bezier smoothing overshoots at the edge, so a sweeping Bragg peak flickers. (vlint:
  `redraw-plot`.)
  The function itself must also be smooth in the parameter: a singular core sampled on a grid that
  moves with it (a Bragg peak at z = R, renormalised by its sampled maximum) pumps the whole curve
  as the peak crosses grid points. Average singular parts over each grid cell (integrate them
  exactly). (vlint: `redraw-jitter` steps each animated ValueTracker through its range, redraws the
  curves and flags heights that reverse direction again and again.)
- **Space rows by what is drawn in them** (user, laser_rt beam-spread cones). A row of shapes drawn to scale (cones, bars,
  spectra) gets the room its biggest member needs: compute each shape's real extent and place the
  rows from that, never on a fixed pitch. A caption sits above the tallest shape, not above the
  row's anchor point. (`shape-overlap` and `line-over-label` were cut in the 2026-11-09 audit: between
  them they had been switched off by hand 366 times and had not found anything in 45 videos. A composed
  picture overlaps itself on purpose, which a bounding box cannot tell from an accident; `label-on-ink`
  asks the same question of the rendered pixels and is the one that still earns its place.)
- Generated images need an alpha channel, otherwise they are opaque black squares
  (`shell_pet` Images).

## Style
- Background `#0f1117`, with diagram colours defined at the top of each script.
- Key numbers go in `\textbf{}` (or `\mathbf{}` in maths), in the concept's accent colour.
- Schematic drawings say so.
- **A recognisable object is drawn as one silhouette, not as primitives stuck together** (user,
  `bone_putty`: "making the shapes raw like with circles for the bone looks a bit unpolished"). A bar with
  a circle at each end reads as a bar with circles on it; the same bone drawn as a single outline reads as
  a bone. Where the shape is a union of simple parts, walk the boundary of that union once and keep the
  points (`femur()` in `bone_putty/bp_vo.py`: four condyles and a shaft, softly unioned, marched around),
  which also lets the joins be rounded instead of crossed. Abstract things — a token, a well, a dataset —
  stay abstract; this is for objects the viewer already knows the look of.

## Sounds beside the voice (user, guitar_theory)
- Synthesise them in the script (numpy into a cached wav, `self.add_sound`), and play them between narration blocks.
- Make them audible on laptop and phone speakers, which play little below ~300 Hz. A pure low tone (a guitar's 82 Hz
  low E) is silent there. Give the sound strong harmonics above 300 Hz, match its RMS to the voice (~0.2), and let
  it ring for as long as the scene waits. Measure the joined mp4 (energy above 300 Hz while the sound plays) rather
  than trusting the wav.

## Narration (Kokoro af_heart; Chatterbox before metamono)
- The narrator is Kokoro `af_heart` (the user's pick from the voice A/B and sampler in `voice_ab/`). Every
  video made before the switch pins `export TTS="${TTS:-chatterbox}"` in its render.sh, so a re-render keeps
  its voice; `TTS=chatterbox` or `chatterbox-turbo` still works for a new one.
- Spell out what must be said:
  - numbers: "one point eight two";
  - units: "millimetres";
  - acronyms letter by letter: "L S O", "E M", "M R", "O S E M". Written in capitals, the voice reads them as
    words ("EM" came out as "em", "MR" as "mister", `pet_fbsem`). Only the ones said as words stay, such as PET
    and MAP (vlint: `acronym-unspelled`, whose list is `SAID_AS_WORD`). The spacing is for the voice only: on
    screen the acronym is written as the paper writes it, "MRI", "DDIM", "HFS-SDE" (user, `pet_diffusion`: "the
    letters may need to be seperated for the pronounciation but not in the videos text"; vlint:
    `acronym-spaced-on-screen`). An abbreviation a viewer may not know is said in full the first time, "magnetic
    resonance, or M R, scan" (user, `pet_dl_recon`: "build for mr? - you mean MR like magnetic resonance?");
  - chemical names: "caesium iodide", not "CsI".
- **Full spoken sentences** (user, `subseasonal_pbc`: "more full sentences, less ';-style' appendages"). A clause
  tacked on after a colon, semicolon or dash ("Then a live test: ECMWF's quest"; "post-processing, not a better
  model") reads like slide notes, and the voice delivers it flatly. Give it a verb and its own sentence: "Then came
  a live test in ECMWF's quest." (vlint: `narration-appendage`).
- Use short sentences and avoid a bare "l". After the draft, read the Whisper check (the
  `== narration heard wrong` lines `voice_prepass.py` prints for any voice, in check.sh's output and in
  `run.log`: each word of a line that its own transcript has differently or not at all; Whisper
  also mishears jargon that was said correctly, so listen before rewriting), which catches
  real mispronunciations ("Poisson" was heard as "Hwasong").
  Most of what it reports is spelling, not sound: on geant4 all three lines it flagged differed from the
  script only in how Whisper writes numbers and acronyms ("1994" for "nineteen ninety-four", "LHC" for
  "L H C", "C++" for "C plus plus"), which costs enough of the score to cross 0.95 in any sentence with two
  dates in it. The one real signal was buried inside one of them: "Geant" heard as "Gint". So the check no
  longer scores the line: `tools/heard.py` leaves numbers out, however either side writes them, and reports
  each *word* the transcript has differently or not at all. Run again on geant4 it reported one word and
  nothing else, eighteen times over fifteen scenes: `'geant' heard as 'gint'` (or 'jeant'). The user listened: the voice had it right, and it was
  Whisper spelling a name it does not know. So the same word across many scenes means listen once, not
  rewrite. If it is said wrongly, respell it for the voice; if it is right, put it in `<video>/heard_ok.txt`
  (one word per line), which stops that word being reported and leaves the next real one visible.
- **No watch order** (user, `pet_hetero_nn`: "the videos dont have a particular watch order"). Never say "the
  previous video" or "the next video": viewers arrive from the catalogue, a playlist or the reels feed in any
  order. Name the other paper, or say it "has a video of its own" (vlint: `watch-order`).
- **Name the subject again when a scene opens** (user, `pet_explorer`: "try to avoid pronouns/indirect references if they haven't been mentioned recently"). A pronoun or a back-reference ("each caught pair", "their",
  "this") points only at something said in the last sentence or two; after a cut, a new title or a pause, say the
  thing in full: "When an annihilation sends its two photons into the ring, the two detectors they strike define a
  line", not "Each caught pair defines a line".

## 3D, when it is used
- **Draw order is by face centre, and flat objects are drawn after all 3D faces.** Don't mix the
  two in one region. Either keep everything 3D, or make the scene flat (`shade_in_3d = False` on
  the whole family) and add in physical order: underneath first, then a translucent fill, then
  the insides, and the outline `Line`s last with `bring_to_front` after each addition (`wt_pet`
  Block). Markers that must sit in front (arrows, rays) get `shade_in_3d = False` (`slab_crlb` Intro).
- **Cost** (under CE; ManimGX renders 3D ~50× faster, see Tooling). A rotating scene with hundreds of prisms took about 40 minutes at 1080p. Stop the
  rotation before the last voiceover, so a static camera reuses frames. Use flat `Dot`s for clouds
  and render 3D scenes first. Recolouring a surface every frame costs about 10 minutes
  (`brain_swin`).
- Scale every part from one unit and write the conversion down (`wt_pet` Sparse was built 10× too
  big). Fix text in frame with `add_fixed_in_frame_mobjects`, which shows it at once: `self.remove`
  it straight after, then FadeIn/Write it on its cue (vlint: `fixed-frame-early`). Rotate at about
  0.1 rad/s, and only while the object is being discussed.
- Ambient camera rotation turns the camera about the origin, so an object placed off-centre (a globe shifted left
  to leave room for fixed-in-frame text) orbits across the screen and under that text. Turn the object about its
  own centre instead (`m.add_updater(lambda m, dt: m.rotate(0.15 * dt, axis=OUT, about_point=C))`) and keep the
  camera still (`subseasonal_pbc` Intro).
- A label or overlay that sits inside a solid is hidden by the depth test: put it on an outer face
  or fix it in frame. Under ManimGX even a fixed-in-frame label is covered where a solid's screen footprint lies
  over it, so keep fixed labels clear of the solid on screen (`pet_explorer` Scanner: the block hid its own spec label).
- Put the face the narration names towards the camera: a readout drawn under a block seen from above is invisible
  (`pet_explorer` Scanner moved the SiPMs to the top face).
- **Draw a length where the camera sees it at true length** (user, `pet_explorer`: "78.6 cm bore not a good
  perspective"). A dimension seen edge on or foreshortened reads as a smaller number. Move the camera so the length
  lies across the view: side on for lengths along an axis (the 24 cm units), face on, down the bore, for a ring's
  diameter. Lay the dimension and its label in that plane (`to_xz`, `to_yz` in `pet_explorer`), and turn a label on
  an oblique view to face the camera (`facing`). A detail too small for the scale (a 2.5 mm gap on a 2 m scanner)
  gets a magnified inset joined to its spot by a leader.
- **Aim the camera at the relation the scene is about, fill the frame with it, and hold still while it is measured**
  (user, `zzb_slab` OffSurface: "the angle of viewing in this scene is very awkward"). A point "just off a sheet" seen
  from above sits on the sheet; a small sheet turning all scene long keeps flipping its apparent bend, and the
  distance lines vanish into the cloud. Before choosing phi and theta, name the one direction the narration measures
  (off the sheet, along the bore) and put it across the screen, usually up; keep a little tilt for depth; zoom until
  the subject spans about half the width. Rotate only to show the shape, and stop before the first distance is drawn.
- **Set draw order between plays, never before a cue** (user, `pet_explorer`: "the half circle flickers"; "the
  person reappears"). Adding something to fix the order (back arcs, body, front arcs) and then introducing it on a
  later cue shows it whole until the cue, then the intro restarts it from nothing. Re-add at the cue instead, in the
  same step as the play: `self.remove(front); self.play(FadeIn(body), Animation(front))` puts the body between
  the halves with no frame between (vlint: `intro-of-visible`, an error, fires when a frame showed the thing before
  its intro). Split a ring into two contiguous arcs, the half behind the axis and the half in front; points picked
  by a sign test from one loop join across the gap with a chord.
- When a title moves down, content placed at fixed y values can collide with it; place content with
  `top_at()` instead (scintillation's stage headings overlapped the lowered title by 84%).
- Small marks need contrast against what lies under them; a dot dimmed below half opacity is a ghost
  and may recede (vlint: `faint-mark`; guitar Notes' sharps were grey on the dark neck).

## Reusing a figure
- **Place a frame by reading numbers, never by eye** (pet_g4_configs, pet_entangled: frames cut through tick
  labels or were set by eye, and writers measured plot levels themselves). `pixi exec -s pillow python
  tools/figgrid.py <video>/assets/<fig>.png` writes a copy with a labelled fraction grid; read `fig_box` fractions
  and any plot level off it while planning, and put them in the plan note. A frame holds a whole label or none of it.
- **Pointer boxes on a lifted figure are never white** (user, `pet_dl_recon`: "white bounding box on white image -
  not a good idea"). Paper figures sit on white, so use the colour of what is pointed at (the method's colour,
  BAD_C for the worse result) or TEAL_L as the neutral (vlint: `pointer-white-on-page`).
- **Open on the paper's front page** (user, `pet_explorer`: "show a shot of the front page of the paper at the start too so it's recognisable"): a video that explains a paper or a resource shows page 1 in its first
  seconds, so a viewer who has seen the paper recognises it. `tools/front_page.sh <video>` writes
  `assets/front.png` from the first `src/*.pdf`, and `front_page()` (common) frames it. The voice names the journal,
  the year and the authors while a box marks the author line, then the box moves to the title as the voice says
  what the paper reports (`pet_explorer` Intro) (vlint: `front-page`, a warning, fires when a script credits an "et al." paper and
  never calls `front_page()`).
  Make those boxes with `ink_box(page, y0, y1, color)`, not a hand-set `px_box` (user, `pet_neuroexplorer`: "the bounding box cuts into the title here"): it grows the
  rows to whole lines and spans the widest one, so no letter sits on the frame (vlint: `front-box-cut`).
  Its padding also backs off any edge that would land on ink, because a superscript or a descender from the
  neighbouring line sits a few pixels outside the band and a fixed pad drops the frame straight onto it
  (`lnp_comet`: the author block's affiliation superscripts, 8 px above the names). A title printed just under
  the running head may still leave no clear gap at all; box the abstract's opening claim instead, which the
  voice can name just as well.
  Say the authors in one short clause (user, `pet_recon_free`: "no need to speak about the authors for too long"): the first author or the group, never a list of
  names and institutions. The front page already shows them all (vlint: `authors-brief`, a warning, fires on an
  author sentence in the first scene longer than 20 words or naming three or more people).
- **Nothing of ours is drawn on top of a picture** (user, `lnp_comet`: "text overlaying images or nearby",
  "the text overlapping the well plate"). Checked in the rendered pixels rather than by geometry: a label on
  clear background is background plus its own strokes, so if over half of its box is neither, something is
  showing through between its letters. It does not matter what — a figure, a plate of wells, a ring, a curve,
  another label (vlint: `label-on-ink`, measured in the skip-mode check, so it costs a check and not a render).
  How close a label sits to its neighbours is left to the eye: a label is *meant* to be near the thing it
  names, so no rule can tell a knob's label from a collision.
- **Keep the video's own words clear of the card** (user, `lnp_comet`: "there seems to be text overlaying images
  or nearby in the video"). A reused figure is somebody else's picture on white paper, so a label laid over it is
  unreadable and reads as part of the paper, and a label pressed against its edge reads as the figure's own
  caption. Leave about a quarter of a unit between the card and any word of ours: a caption goes under the card
  with room to breathe, a name or a count goes out to the side. Remember the card is bigger than the image, by
  0.08 all round (vlint: `text-on-figure`, `figure_clear`, default 0.18). A word that really does belong on the
  picture, such as a panel letter being replaced, is marked `vlint_ok(t, "text-on-figure")`.
- **Any figure in a supplied paper may be shown** (user, `pet_explorer`: "these videos are not shown to the public ...
  if we've gotten access to the paper and given it to you treat that as confirmation that it's allowed for everything
  in the paper to be used and shown"). The videos are for private viewing, so the licence never forces a redraw:
  the per-figure choice in §4 decides (real data and dense plots reused, mechanisms redrawn). Credit each reused
  figure on screen while it shows ("Fig. 3: Badawi et al., J Nucl Med 2019", `credit()`).
- **Cut the printed labels off a reused panel and draw them** (times, doses, panel letters): a `Tex` under each
  panel matches the video's type, can carry the accent colour and a cue, and is visible to vlint's number checks
  (`pet_explorer` Figs. 3 and 7, cropped in `src/crop.py`). A panel's region is outlined with a frame placed in the
  source image's pixels (`px_box`).
- **Redrawing a bar chart:** measure each bar's end in a 300 dpi render against the axis tick rows (a short numpy
  scan by colour), keep the values in `src/compute.py` with their figure, and check them against every gain the
  text states before using them (`subseasonal_pbc`: "+26–37 %" and "0.023" both matched). Credit "redrawn from …".
- Render with `pdftoppm -r 300 -x -y -W -H` (poppler, through pixi), crop to the panel, and save to
  `<video>/assets/`. Show it on a white `card()`. Check for stray panel letters. Read figure-only
  numbers from a zoomed render.
- **Crop on white space** (user, `pet_neuroexplorer` Fig. 3A: "the graph sourced for here seems cut off"; the crop had dropped the tick numbers and the axis title): every edge of a reused plot or drawing runs through white
  paper, never through tick numbers, an axis title or a slice. Find the bounds with a numpy scan of the dark rows and
  columns, not by eye. A neighbour's panel letter that falls inside the box is painted white in `src/crop.py`
  (`WHITEN`), not cut through (vlint: `image-edge-cut`, a warning: ink touching an edge of a mostly white image).
- Anything holding an image is a `Group`, not a `VGroup`, including inside `fit_frame` (vlint:
  `vgroup-non-vmobject`).

## Walking through the paper (a trial format, `pet_hetero_nanocomposites`)
The user asked for a video that goes "through every page of the paper ... so by the end the viewer has seen the paper
and knows where to look for information". It is laid out like this:
- **The page stays on the left (about 7.4 tall), and the right-hand half explains it.** A yellow highlighter stroke
  marks the passage the voice is reading. A frame marks a figure or an equation. The page turns (slides off left)
  on the sentence that moves to it. Boxes live in `regions.py` in 300 dpi page pixels. `src/crops.py` snaps text
  boxes to whole lines, so a highlight never cuts a line in half, and writes the crops. Helpers `hl`, `lift` and
  `turn` take the cue as their first argument; vlint counts them as cues (a helper that forwards its argument to
  `self.at`), and `plan-action` reads the animation out of the helper's body *and* its call site, so the helpers
  can be used instead of re-implemented per scene, and can carry the extras that belong on the same word
  (`self.turn(10, "c", FadeOut(ring))`). `scene-protagonist` counts the figures handed to one of them too: a
  scene that does its work through the format's helpers is not a scene without a central figure.
- **Every page is seen; the order they are seen in is the explanation's.** The user's ask is that by the
  end the viewer has seen the paper and knows where to look, which is about coverage, not sequence. Pick
  the order from "Order" in Part I, and let the closing map put the pages back in document order so the
  viewer still leaves with the paper's own shape.
- **A page cue is `new:` in the plan.** A highlighter stroke, a page turn, a frame and a lift all bring something
  on (`GrowFromEdge`, `FadeIn`, `Create`), so `side:` is the wrong declaration for them even though they act on
  the page rather than on the scene's focus. The unprefixed and `side:` lines belong to the right-hand picture.
- **The page's footer carries the credit**, so the scene does not also add `credit()`: the two land in the same
  corner and overlap on every page.
- **Lift a piece off the page only when the enlargement shows something the highlight cannot**: a figure whose
  dots the voice follows, an equation whose terms it points at, a reference the viewer should be able to read (user, `pet_hetero_nanocomposites` Intro: "'Here is that last sentence up close' didn't really
  have a purpose"; the sentence had already been highlighted and read aloud). A highlighted sentence that the voice
  reads aloud needs no enlargement. Give the right-hand side a drawing of what the sentence says instead: the
  abstract's four steps became four small cells (grains in plastic, bright, stacked with BGO, 115 ps).
- **A methods passage gets drawn as well as highlighted** (user, `pet_hetero_nanocomposites` Methods: "a
  visualisation would've been good here"). Draw each step by what goes in, what is done and what comes out. The
  recipe became three rows: raw grains into an oven at 950 °C for 2 h and out rounder; syrup spread by a doctor
  blade into a 100 μm film; layers stacked by hand into a reflector-lined Teflon cube. In this format, every page
  the voice spends a sentence on needs a picture on the right, not only a highlight on the left.
- **Close on the paper as a map** (user, `pet_hetero_nanocomposites` Takeaway: "i like this paper as a map at the
  end"): all pages as thumbnails, each labelled with what it holds, with a box moving over the groups as the voice
  sums up where the story, the material, the device, the result and the recipe are.
  **Lay the thumbnails out so each group the voice names is a block of one row**, and draw the box as one
  rectangle that moves and resizes, not a bundle of per-cell boxes transformed into a bundle of another size.
  capstone's map went from six columns to nine for exactly this reason: at six, "the results" straddled two rows
  and no single rectangle could hold it.
- **A scene that takes the page away must take what is standing on it** (capstone Map). The highlighter stroke
  belongs to the page, so `FadeOut(self.pg)` by hand leaves a yellow band hanging in empty space -- on capstone it
  outlived the report by forty seconds and no rule saw it, because a translucent rectangle in a legal place is not
  a finding. `Walk.turn` already fades `self.left`; the fix is that every other way out does too
  (`Walk.clear_page()` in `capstone/ak_vo.py`), so a scene cannot forget. The general shape of this mistake:
  **a helper that owns a group of objects needs one exit, not two.**
- **Lift a figure at full width before shrinking it to share the half.** capstone's Result lifted the report's
  five-panel separation figure straight to 4.3 units so the ladder of targets could sit beside it, and at that
  size its bars are a texture, not evidence. Lifting it to the full 6.3 for its first block, then setting it down
  beside the ladder on the next cue, costs one beat and is the difference between showing the result and
  gesturing at it.

---

# Part III: Workflow

0. **A video is made by one agent, started from the video's brief and nothing else.** Write
   `<video>/brief.md` -- the source, who is watching, the format the video is in, and what has already been
   cut out of the source (page renders, crops, generators, and how to make more). Then start a fresh agent
   whose whole prompt is `bash tools/brief.sh <video>`, which prints that handoff: read DESIGN.md, read the
   brief, do steps 1 to 8. Not a fork of the conversation -- a fresh one, with no history.
   The conversation that starts it is the wrong place to make the video from. It holds the old version, the
   user's reactions to it, abandoned drafts and whatever was being argued about an hour ago, so a video
   written there is written partly out of all that, and the pipeline can no longer be judged: a good video
   may be good because the context carried it, and a bad one bad for the same reason. capstone is the case
   twice over. Its first rebuild lost the walkthrough format, because the format was in the deleted script
   and the brief never carried it. Its second kept the first version's narration *word for word* -- 1878
   words, identical -- because `narration.md` had been lifted out of the old script and handed back in as an
   input, and because the old words were sitting in the orchestrating context where nobody had to decide
   anything to reuse them (user: 'Is seems the script is the same as the old video?').
   So: **`brief.md` is the input; `narration.md`, `plan.md`, the `_vo.py` and `render.sh` are outputs.** A
   rebuild deletes its outputs and its `runtime` record in `vlint/baseline.json` first and commits that
   teardown, so there is nothing in the folder to copy; prior renders move out of the folder too. What
   survives a teardown is the brief and the inputs it names -- the source, the page renders, the crops and
   the scripts in `src/` that make more of them. Those are spare parts, not a route: which pages the video
   visits and which passages it highlights are decided again each time.
   The agent fans out its own scene writers once `plan.md` exists (step 2), so one agent is not one worker.
1. Read the source, identify the kind of resource, and write the viewer's intent in one sentence
   (Part I, "Start here"). Then plan the scenes to serve it (5–8 min by default). For each scene, note
   the mechanism it explains and whether each figure is reused or redrawn.
   **A video's length is its word count, and the time to decide it is here.** The finished file runs at about
   **0.37 s per spoken word** -- 160 words per minute including every animation, measured over
   `pet_hetero_nanocomposites` (1455 words, 8:55) and capstone (1277 words, 7:58). So 5–8 minutes is 800–1300
   words, and a scene is about 90. An explainer is almost all speech: capstone's scenes held under two seconds
   of silence each, so there is no slack to cut later and trimming means cutting clauses. capstone was written
   at 1654 words, which is ten minutes, and had to be cut twice after it had already been staged and rendered.
   Count the draft before staging it.
2. **Write the narration first, then stage it in a separate pass.** Writing the words and the pictures at the
   same time lets the pictures lose: a clause gets whichever cue is cheap on whatever is already on screen, so
   the scene fills up with pulses, fresh arrows and another panel beside the last one. Write the narration
   alone, scene by scene; then ask, clause by clause and with nothing else to do, what the scene's own figure
   *does* as each one is said.
   **Which format the video is in is in `brief.md`** (step 0), because staging cannot infer it from the words
   and a rebuild loses it otherwise. Most videos are the default (one drawn figure per scene); a walk through
   the paper is a different thing entirely -- page on the left, highlighted where the voice reads, explained on
   the right -- and it lives in the margins, not in the narration. capstone was a walk through the report;
   rebuilding it from the narration produced a conventional explainer that never opens a page, with its
   twenty-seven page renders and fifty-seven highlight regions untouched in `assets/`, because the staging brief
   never said so and the one line that did was in the script that had just been deleted. Whatever a clean-room
   rebuild is meant to forget, the format is not a prior -- it is the brief. Repeat it at the top of
   `narration.md` as you write it, so the staging pass has it too.
   The answers go in `<video>/plan.md` before any manim exists (the format is
   documented in `tools/vlint/plan.py`): per scene one `focus:` naming the variable that will hold the scene's
   figure, the narration in `>` blocks with `[mark]` where each cue fires, and one line per mark of the form
   `<mark>  what happens  -- why`. The why says what the viewer is meant to take from the cue, and it is the
   half that keeps a scene honest: a cue whose only honest why restates the words is a cue to delete, which is
   how a scene stops filling with animation nobody can account for (user, mc_recon: 'there seems to be too
   many unnecessary [or un]explainable animations in the video now').
   A plain line means the focus itself changes -- the kind worth having, so it needs no prefix;
   `side:` is a change to something else on screen, `new:` something arriving, `mark:` a pulse on something
   already there, and `morph:` one object on screen becoming another, which has to be asked for because a
   thing that turns into a different thing is a thing the viewer stops tracking: object permanence is the
   default and a metamorphosis is a decision (user, mc_recon: 'some entities just straight up turn into
   different ones (e.g. a detector turns into an arrow) which is confusing to track, try to have some object
   permanence'). Cue at the scale the words are at: a clause about a property or a part gets the property or
   the part, not the whole thing it belongs to -- the four lipid kinds come out of the shell one at a time as
   they are named, and a width is a width arrow across the thing, not a flash on the thing
   (user, mc_recon: 'if mentioning a property of a thing try to only cue that property (or something
   indicative of that property) rather than the whole thing in question').
   Give the staging pass to a separate writer if you can (a subagent with the narration, the
   rules in Part I §1 and the scene's object inventory, and no job but to answer that one question per
   clause): the split is what makes the question get asked at all. `lnp_comet` was staged this way.
   vlint then ties the two together (`plan-missing`, `plan-narration`, `plan-focus`, `plan-action`): the
   spoken words must be the planned words, so neither side can be edited alone and the plan cannot rot into
   documentation; every mark must be cued; and a line saying the focus changes cannot ship as an `Indicate`
   on it. `plan-why` wants the second half of every line, and `object-morph` and `property-scope` hold the
   last two rules with or without a plan: a Transform from one kind of object to another kind is a warning
   unless its line says `morph:`, and a pulse on a whole object under a clause about one of its properties is
   a warning wherever it happens. Without a plan.md the heuristics stand in and can only guess
   (`scene-protagonist`, `pulse-for-event`), so a new video gets a plan. `vlint plan <video> --draft` prints
   the skeleton for a script that already exists.
   **A line is `new:` whenever the cue brings the thing on, even when the thing is the focus being built.**
   Most of a plan's mistakes are this one: capstone was written with plain lines for cues that could only ever
   be a `Create` or a `FadeIn`, and all four of its scene writers had to come back and re-prefix them before
   `plan-action` would pass. Write the plan asking, per line, "does this arrive, change, pulse, or morph?" --
   the four prefixes are the question, not a label applied afterwards.
   **Keep the words in one place and generate the other.** The plan's quoted lines and the script's
   `voiceover(text=...)` are the same sentences in two formats, and `plan-narration` is an error, so trimming a
   clause late means editing both by hand across different line wrapping -- which is how a late cut turns into
   an afternoon. capstone's cuts (two passes, 90 words) went through a 100-line tool that reads the script's
   joined narration, applies the edits, re-wraps the string literals, and rewrites the plan's `>` blocks from
   the script. Thirty-two edits, zero mismatches. Build it the first time a video needs trimming and keep it.
   Writing the plan first is also what makes the build cheap. A scene writer then needs the plan, the palette
   and the helper inventory and nothing else -- not the paper, which is the bulk of what each writer reads --
   and every rule above runs on the script with no GPU and no voice, so the shape of a scene is settled before
   anything is rendered. A writer working in its own copy of a video folder checks that copy by path --
   `bash tools/check.sh /path/to/the/copy` -- which syncs it under its own name, so several writers can check
   at once without overwriting each other. Have them do it: on `mc_recon`'s rebuild the two writers who ran
   the skip-mode check before handing back accounted for 13 of the 107 layout warnings, and the four scenes
   whose writers ran only `vlint check` accounted for 94. That is the difference between a layout pass
   afterwards and none, and the check is eleven seconds.
   **Diff each writer's copy against the base you gave them, never against the master you are merging into.**
   Merging writer by writer against a master that is already changing produced 18 false "wandered outside its
   scenes" accusations. Give each writer a `render.sh` listing only its scenes up front, so there is no edit
   to hand back.
   **Give each writer a folder of its own named differently, three scenes, and the plan as its whole brief.**
   capstone's rebuild ran four writers on a cheap model over twelve of its fourteen scenes, each in
   `slab_work/cap_<a-d>` with a `render.sh` listing only its own scenes, and the twelve classes spliced into
   the master in one pass with no conflicts. Two things made that work: the writers never saw the source (the
   plan holds every spoken word and every number, so there is nothing to look up and nothing to re-decide),
   and they own **disjoint sections of plan.md**, so when a writer has to re-prefix an action line it can edit
   its own copy and the four copies merge line by line. Tell them which prefix lines they may touch and that
   they may not change a spoken word; then diff each copy against the base before splicing, so a writer that
   wandered outside its scenes is caught rather than merged. Expect every writer to also edit its copy's
   `render.sh` so `run_v.sh` will run, and to hand that edit back: do not take it.
   **A writer's copy holds only what its `render.sh` lists.** geant4 handed five writers a base script that
   still carried two finished scenes as examples of the house style, and a `render.sh` naming only the
   writer's own. `scene-list` is an error (a class defined and not in SCENES), so every one of the five hit
   the static gate on their first draft render and went round it with `VLINT_ALLOW=1` -- five writers each
   independently switching the gate off is the gate teaching people to switch it off. The example scenes
   go in a file of their own that nothing lints or renders. **`python tools/writers.py split <video>` now
   cuts the copies that way** (`--per 3`, or `a=Scene,Scene b=...`): the script with every scene taken out
   and a marker line, `examples.py`, a `render.sh` and a `plan.md` holding only that writer's scenes, and a
   `WRITER.md` that is the writer's whole brief. `python tools/writers.py merge <video>` splices what comes
   back and refuses, by name and with the reason, a copy that edited above the marker, wrote a scene that is
   not its own, added a shared name, or changed a spoken word. What did work, and what the tool does: shared helpers above one marker line that writers may not edit, scenes
   appended below it, private helpers named `_<scene>_<what>`. Five copies then spliced by checking each one
   still *starts with* the base byte for byte and taking the remainder -- no diff to read, no name collisions,
   no plan edits (every prefix had been decided in the plan, with a per-scene note of coordinates and exact
   on-screen strings beside it; none of the five had to re-prefix a line).
   **Lint the words while they can still change** (si_psf). A writer may not change a spoken word, so every
   rule that reads the narration has to pass before the plan is split, and at that point there is no script
   to run it on. Generate one: a throwaway script made from `plan.md`, one empty scene per section with every
   mark cued on a dot, put through `vlint check`. On si_psf that found two `cue-gap`s (33 and 25 words) and
   the one number the source's text does not hold, in a second, before three writers would each have had to
   report them back. The plan-only check (`vlint plan --check`) reads structure, not the words.
   **A figure driven by a number carries the number.** A plain action line passes `plan-action` only if the cue
   changes something that names the focus, and a `ValueTracker` swept on its own names nothing, which pushes
   honest "the focus changes" lines towards `side:`. si_psf's `live(build, d=...)` hangs the tracker on the
   figure it redraws, so the cue is `wav.d.animate.set_value(154.9)`: the code says what the plan says, and
   several figures can share one tracker. Per-scene notes went into the plan as one-line `<!-- -->` comments
   (coordinates, exact strings, which helper), which the parser skips and `writers.py` carries with the
   section: three writers, eight scenes, no prefix changed and nothing refused at the merge. What the split
   did get wrong is now fixed in the tool: the copies had no `src/*.txt`, so `number-unsourced` stood down in
   every writer's check exactly as it once did under `check.sh`, and WRITER.md printed its commands with the
   Windows path, which WSL cannot open. An ignore comment for a spoken number goes on the
   `with self.voiceover(` line, where the finding lands, not on the line of the string that says it.
   **A shared helper is part of the plan, so it is tested before the split and placed by a named anchor**
   (g4_tutorial: a tutorial, not a paper, so every picture was drawn and eleven of twelve scenes were built
   from one helper set by four writers who could not edit it). What held: the lead wrote the helpers and one
   scene, rendered a throwaway scene that used every helper once under both engines, and only then split;
   the four copies merged with nothing refused, no prefix changed and no `VLINT_ALLOW`. What did not, each
   found by two writers independently, which is the sign it was the helper and not the writer:
   `kernel()` returned a group whose centre was the body *plus* its sockets, so "centred (0, -2.5)" in a
   plan note put the body 0.4 lower than the note meant (`slab()` re-centres itself on the crystal and nobody
   tripped on it: say in the docstring what `move_to` moves, and write notes against that); and `gone(m)`,
   a helper returning `m.animate...` so that a thing could *leave* on a cue, is invisible to `plan-action`,
   which reads animation names off the cue's own call and does not follow a script's helper into its body
   unless the helper *is* the cue. A leaving object needs a cue kind of its own, because a `FadeOut` is
   none of change, arrival or pulse; until it has one, write the `.animate` inline. Smaller: a point helper
   takes 3-D points or says so (`polyline` crashed on `(x, y)`), and a note that says "four labels" lists four.
   **Plant a wrong number in the throwaway script before trusting a silent `number-unsourced`.** The source
   here was markdown, a kind the rule had never read; "four point nine" for 4.7 and "twelve thousand nine
   hundred" for 12 800 both came back as findings, so the silence over the real script meant something. All
   three `narration heard wrong` lines were Whisper's spelling ('here'/'hear', 'metres'/'meters', 'mev' for
   "M E V") and went to `heard_ok.txt`.
   **Measure the pace of the voice you are using.** 1464 words came to 8:23, 0.34 s a word and not 0.37, so a
   plan aimed at nine minutes for a brief that said "8 to 12" landed a third of a minute from being short.
   Short declarative sentences with few numbers run faster than a paper's; when the brief gives a floor, aim
   the word count at the middle of the range, not at its low end.
   **A thumbnail is not evidence.** On the watch sheet the scintillation rays looked as if they left the
   crystal, and ten minutes went on the path model before one full-size frame showed every ray inside it.
   Pull the frame (`ffmpeg -ss t -frames:v 1`) before reading code.
   **Voice the whole narration once, before the split, and hand every writer the cache** (g4_inside: eighteen
   scenes, 2906 words, six writers on a cheaper model, seventeen scenes merged with nothing refused, one prefix
   changed and no `VLINT_ALLOW`). The throwaway script made from `plan.md` to lint the words is also a script
   `check.sh` can voice: one pass, 112 s, and every `narration heard wrong` line was in hand while the words
   could still change. Copying its `m_<Scene>/voiceovers` into each writer's render root
   (`~/slab_render/<video>_<writer>/`) meant six writers' checks never loaded a voice model side by side.
   What that build found, each worth keeping:
   - **`number-unsourced` cannot read a number that follows a count word.** "Fire one five hundred and eleven
     kilo electron volt gamma" is one run of number words that parses as nothing, so the rule skipped it, and
     a planted "five hundred and twelve" passed while three other planted numbers were caught. Plant an error
     in *every* headline number, not one; and keep a count word off the front of a spoken number ("a single").
   - **Code on screen is `Text(font="monospace")`, as written, under both engines**: `_`, `->`, `::`, `&`
     and `*` need no escaping in either. The two engines set it at different widths, so scale it to a
     character width measured from a reference string, and place lines by a two-glyph strut stripped off each
     line or their baselines wander with the descenders (`mono()` and `code()` in `g4_inside/g4i_vo.py`). At
     0.125 units a character a line holds about 100 characters; wrap a longer statement at a comma.
   - **Walking a snippet is a cue helper, not a function returning animations**: `self.read(mark, cd, k,
     *more)` forwards its mark to `self.at`, so vlint counts it as a cue and finds the `.animate` in its body.
   - **A helper is tested at the sizes and angles the plan will ask of it, not once.** Found by writers who
     could not edit them: `dim_line`'s label lands on the line when the line is diagonal; `flag_at` below
     h = 0.36 hangs its pennant under its own foot; `under()` writes its layer names where a scene's top-left
     label goes; `stack_frame`'s centre includes its name. And `lab("+")`, `lab("=")` are Typst markup again
     (they set as "1." and nothing); write `$+$`, `$=$`.
   - **A note that gives a size has to be added up by whoever writes it.** "A dashed column to the top of the
     frame" above a six-place stack left one unit of column, and the ghost pile floated in it clear of the real
     tokens; two cards "at y = -1.9" and a call name "at y = -3.0" summed to more than the frame's width. No
     rule saw either; the lead's watch pass did. Sum the widths of everything a note puts on one row.
   - The pace again: 2906 words came to 16:03, 0.33 s a word. `run_v.sh` on three scenes takes longer than
     a two-minute foreground command; tell writers to run it in the background.
   **Generate the script's side of the words from the plan, for the lead and for every writer** (g4_setup:
   eighteen scenes, 2381 words, six writers on a cheaper model, sixteen scenes merged with nothing refused, no
   prefix changed, no `VLINT_ALLOW` and not one `plan-narration` error). `g4_setup/src/planvo.py` reads
   `plan.md` and prints either the throwaway script that lints and voices the words, or a `skeleton.py` per
   writer: each scene's `voiceover` blocks word for word, with an empty `self.at()` per mark and the plan's
   action line as its comment. Nobody typed a spoken word twice, so nobody could mistype one. It belongs in
   `tools/` beside `writers.py`, which should drop the skeleton into each copy itself. What else that build
   found:
   - **Three more holes in `number-unsourced`, each found by planting.** "a hundred and one lines" is a run
     that opens on a scale word, which the parser gives up on, so a planted "a hundred and two" passed: say
     "one hundred and one". A number a hundred times one the source prints passes as a percentage (a planted
     "four thousand events" matched the source's 40 ns). And a round number passes as a rounding of a
     neighbour ("sixty millimetres" for the source's 64). Plant in every headline number, and read the
     list of what was *not* caught as carefully as the list of what was.
   - **A kit scene that is not laid out cannot show a helper landing in the wrong place.** The throwaway
     scene called `lput()` on a folder tree, the tree landed 0.9 too high, and nobody saw it because the kit
     was a heap of overlapping pieces; three writers then found it independently and each worked round it.
     Give every helper in the kit a marked target (a small cross at the coordinate it was asked for) and
     look for the gap.
   - **A plan note is rewritten once the lead has stopped deciding.** The first draft of the notes still
     held the arithmetic ("at (5.9... keep both inside x < 6.7: centres (3.3, -2.3)"); a writer cannot tell
     which half of such a sentence is the instruction. Grep the plan for `??` and `...` before the split.
     The notes that still did not add up were found by writers and reported, not silently obeyed, because
     the brief said to move the minimum and say so (a frame 2.3 tall round tags that hung below it).
   - **A thing alone on screen is sized for the frame, not for a label.** Wrong shows one failure at a time
     under a road of five stations; at label size (a message at 0.14 a character, a crystal 3 units wide)
     sixty per cent of the frame was empty in every settled sheet, and no rule minds: `layout-balance` is a
     note. The lead's sheet pass scaled each one up.
   - `GrowArrow` on a `CurvedArrow` crashes CE (`scale_tips`): `Create` it. `QUALITY=-ql wsl bash ...` from
     Git Bash does not carry QUALITY into WSL, so a writer following WRITER.md to the letter renders at
     1080p; `writers.py` now prints the command with the variable inside. A shell heredoc holding an
     apostrophe fails under this harness's Git Bash: write the file with the Write tool.
   - Whisper again, on a video full of file names: `'dot' not heard`, `'c make lists dot' heard as
     'cmakelist'`, `'dot jason' heard as 'json'`, `'num pie' heard as 'numpy'` are all the voice saying it
     right and Whisper writing the name. A transcript that spells the term the script was aiming at is
     the best evidence there is that it was said.
   - The pace: 2381 words came to 13:55, 0.35 s a word, slower than the last three. Sentences that walk
     through code and file names carry more bookmarks and more pauses; for a code video count 0.35.
   The checks measure; they do not see. On `mc_recon` a loop arrow was drawn 1.33 units off the centre of the
   ring it was meant to circle: geometrically valid, no rule against it, caught by the viewer in the
   delivered video. So the writer also looks. `QUALITY=-ql bash tools/run_v.sh /path/to/the/copy` renders
   that copy's own scenes at 480p and leaves a review sheet per scene in the copy's `review/`, which the
   writer reads before handing back -- while the scene is still in the context that built it, which is also
   the cheapest moment to fix anything. Measured rules and a pair of eyes answer different questions: the
   monitor checks geometry at every `play()` boundary for eleven seconds and no tokens, a sheet samples about
   five frames of a fifty-second scene but has no rule to be inside. Neither replaces the other.
3. Write `<video>/<name>_vo.py` and `<video>/render.sh` (copy one, then change `SCRIPT`, `OUT` and
   `SCENES`; the pipeline itself is `tools/render_lib.sh`). The script starts with
   `sys.path.insert(0, str(Path(__file__).resolve().parent.parent))` before `from kit import *`, or every
   scene crashes with "No module named 'kit'" (si_psf, written from this file alone). Lay out with common.py's helpers rather
   than by eye: `title()` (every title on one line), `CONTENT_TOP`/`top_at()` (content starts under it),
   `place()` (a labelled group centred by its picture) and `grid()` (fixed pitch, short rows centred).
   **Draw with `kit.py` before writing a helper of your own; `KIT.md` lists what it has.** kit holds the
   primitives that more than one video needed: code set as written and lit line by line, call trees, files,
   folders, terminals, slots, stacks, records, dimension lines at any angle, tracks, Gaussians, bars, a slab
   with its photodetectors, a ray at an interface. Each was written by one video, needed again by another, and
   is drawn under both engines by `kit_gallery`. Before kit, every video wrote its own: g4_tutorial, g4_inside
   and g4_setup wrote 28, 37 and 32 helpers, and four of the same ones three times over (`lab`, `num`,
   `kernel`, the monospace code block, the last tested under both engines twice), and their scene writers hit
   the same helper bugs one by one (a dimension label on a slanted line, a flag whose pennant fell under its
   foot). What a video draws is still its own decision: kit has parts, never scenes, and a primitive that is
   wrong for a picture is passed different arguments or left alone, not bent until it fits.
4. Check: `bash tools/check.sh <video> [Scene ...]` in WSL after every edit: the static checks, then
   every scene in skip mode (each play() jumps to its end; ~25 s for a whole video, nothing rendered)
   with all the runtime rules, as one sorted list. Fix every error. Read the warnings as questions (is
   this label a sentence? is the eye left alone here?). Findings a video is already recorded as making are
   held back and counted on one line, so a finished video does not reprint its layout debt on every check;
   anything above the recorded count prints in full, marked `[9 of a recorded 7]`, because a count cannot
   say which of them is new, and an error is never held back. `RECORD=1 bash tools/check.sh <video>` accepts
   what it finds now as that video's record -- the only way debt is ever taken on, and a deliberate act.
   **Rebuilding a video drops its record**: the debt was accepted against code that no longer exists, and
   capstone's v1 numbers (6 layout-crowded among them) sat on the rebuilt video holding back findings that
   were a day old, mine, and unexamined. Delete the video's entry under `runtime` in `vlint/baseline.json`
   when its script is replaced, and let it earn a new one. The
   whole corpus was recorded on 2026-11-09 (686 findings over 45 videos), which is why `check.sh all` prints
   one line per video instead of 1178 warnings. render.sh runs the same checks and stops on
   errors. When the rules change, render.sh re-checks the scenes it would not re-render (the rule set
   is part of each record), so old findings never pass for current ones; `check.sh all` re-checks
   every video.
5. Draft: `QUALITY=-ql bash tools/run_v.sh <video>` in WSL, run through a `.sh` file. Narration is
   generated before any scene renders, by `tools/voice_prepass.py` (check.sh and render.sh both call
   it): two workers (`VOICE_WORKERS`; for Chatterbox ~4.6 GB of GPU each, for Kokoro one kept-alive process each) share out whole scenes and fill
   each scene's cache, so the scenes themselves only read audio. The pre-pass starts before anything else, so the voice model loads while vlint checks the script. A scene starts rendering as soon as its own narration is cached, while the rest is still being voiced. By default every scene renders at once: ManimGX up to 8, CE capped by cores and RAM; `JOBS=n` overrides. **A page-walk video needs `JOBS=3`**: each scene holds several 2484x3509 page renders, and 8 at `-qh` dies with a PIL `MemoryError` and a pyo3 panic. The slowest scene by its last render time goes first. Each scene's CE check runs beside its GPU render. The small copy is encoded scene by scene in parallel while the review sheets (8 at once) are made. Profiled 2026-10-25: the GPU stays under 35% busy. The limits are each scene's Python (an `always_redraw` doing heavy numpy every frame) and Kokoro's ~7 s start-up. metamono rebuilds in 1:31 with its sheets.
   **Never let scenes generate their own voice side by side**: one model per scene overflows the 11 GB
   card, and 15 copies made no audio at all in 25 minutes.
6. Review the sheets in `<video>/review/` before sending: run_v.sh writes one per newly rendered
   scene (`tools/review.sh <video> [Scene ...]` by hand), cut where it matters: the settled frame at the
   end of each narration block and four frames across each moving-curve sweep, each stamped with its
   time. They catch what no rule does (a crowded corner, a wrong colour); when one does, ask whether a
   rule could have, and add it. Fix and run render.sh again: it re-renders exactly the scenes whose code, shared
   helpers or assets changed (each scene's fingerprint is stored beside its video), so there is nothing
   to delete by hand.
   **A scene spoken as one block has a sheet of two frames** (si_psf: eight of ten scenes were a single
   `voiceover`, so each sheet held the empty opening and the finished picture and nothing of the forty seconds
   between; one writer cut frames out of the draft by hand to see their own scene). The sheet samples the end
   of each narration block, so give a scene two or three blocks at its natural pauses, or read `watch.sh`
   for it, which is what caught everything here.
   **"Not heard" with the words' timings piled into a fifth of a second is the voice, not Whisper** (si_psf
   Track: 'the fitted diffusion coefficient' missing from the transcript, its six words all stamped inside
   0.2 s after a 2.7 s hole). A spelling difference ('centre' as 'center', 'widefield' as 'wide filled') is
   Whisper; a hole is not. Rewording the sentence, here a comma turned into a full stop, re-voices the line,
   and the finding went away.
   A review sheet samples where the picture has settled, so it cannot see what happens on the way there.
   On capstone a head faded in over the still-full-size front page and smeared grey across the report's
   title, entirely between two narration blocks: no settled frame held it, and no rule forbids it.
   `bash tools/watch.sh <video>` is the pass for that, run on the joined file before sending. It scores
   every frame against the one before it and keeps a frame once enough has changed since the last one
   kept (`tools/watch_times.py`; `T=` lower to look harder), so a moving stretch is sampled every few
   tenths of a second and a still one barely at all. That matters because an explainer is mostly still:
   on capstone, 3423 of 5252 frames sampled at 8 fps were identical to their predecessor, and the whole
   video came to 149 frames worth looking at, ten sheets, against 263 at a flat 2.5 s -- fewer frames,
   and the transitions actually in them. Sheets go to `<video>/watch/` (not kept in git).
   It earns its keep on the frames no settled sample can hold: on capstone's rebuild it caught the closing map
   dissolving into grey tiles, because `FadeOut(group_of_images, scale=…)` drops an `ImageMobject`'s texture
   under ManimGX and leaves blank quads for half a second. Fade images plainly; the scale is not worth it.
   Two more of the same family, both from geant4 and both invisible on the settled sheets. **A pointer box
   leaves with the thing it points at**: the title's ink box was faded out in the same play that shrank the
   front page, so for half a second it hung in mid-air at full size while the page slid out from under it;
   it now rides the page down (`Group(page, box).animate...`). **An arrival waits for the move that makes room
   for it**: Fig. 8 faded in while Fig. 7 was still sliding left through the place it lands, and the two cards
   were on top of each other for the length of the cue. Two plays, the move and then the FadeIn.
   **Read a scene's own duration from `list.txt`, never from `m_<Scene>/videos/*/*/<Scene>.mp4`.** The render
   root is shared between videos and keeps old quality folders, so that glob can match a stale 1080p60 file
   from a version that no longer exists. On capstone it made three scenes look thirty seconds too long and
   nearly cost three rewrites of scenes that were fine. `list.txt` is what the join actually used.
7. Final: `QUALITY=-qh`. **Never above 1080p** (render.sh refuses more). The join is
   refused if a scene is missing, stale or has a runtime error, and the joined file is checked for size,
   length and audio drift. Send a 1080p crf 26 re-encode (`_small.mp4`) when the file is over 30 MB,
   never a downscale. A video rendered before vlint existed: `vlint adopt` its unchanged scenes once,
   so only the edited ones re-render.
8. Update this file (§0), then report. **Then promote what a second video needed.** For each helper the
   script defines above its scenes, `python tools/kit_promote.py <video>` says whether another video defines
   one of the same name or the same body. A helper that two videos needed, and that draws a part rather than
   a scene, moves into `kit.py`: general arguments in place of the video's colours and sizes, its parts named
   on the group, a docstring that says what `move_to` centres, a line in `KIT.md`, and a part in one of
   `kit_gallery`'s scenes. Then `check.sh kit_gallery` and a `-ql` render of it, and read its sheets. The video
   that promoted it is not edited to use it (its render is current); the next one starts from it. Say in the
   report what was promoted and what was a near miss. A change to an existing primitive is checked the same
   way, and is a change to every video that uses it: make it backwards-compatible, a new argument with the old
   behaviour as its default.
   **Promote by what a primitive is for, and only where its kind of video needs it** (pet_g4_configs, the first
   video built on kit). Videos differ in kind (a code walk, a detector paper, a page walk), so kit is sectioned by
   kind and a primitive goes in the section of the videos that need it; a picture only one kind draws is promoted
   for that kind, never pressed on the others. kit.py's fingerprint now counts only the kit functions a script
   reaches, so a promotion stales only the videos that draw with what changed, and the build that promotes can
   switch its own copy over and re-render that scene. `kit_promote` reports a name that kit uses for another thing
   (kit's `card` is an object card; six videos' `card(path, h)` is a figure on paper, now kit's `figcard`).
   **Write a plan note's helper calls with keywords** (pet_g4_configs): "pair_side(face, u=0.15, colour)" put the
   colour in the slot of `depth_mm`; the writer noticed and called it with `color=`, but a writer who had not would
   have drawn a crystal 0.15 mm deep.
   **A random shape that shares a space with its siblings has its placement decided, not left to the seed.** Four
   positron walks from one centre, each rescaled to its reach but leaving in whatever direction its seed gave, tangled
   into one knot over the sphere's middle; the writer hand-placed the four names round it and two still sat on ink.
   `walk(..., angle=)` now turns each track to end in a direction of its own. A name for a mark inside a filled
   shape goes outside the shape on the mark's line, never on its edge, where the outline strikes through it.

Tooling (since 2026-10-25): **ManimGX renders, Manim CE checks.** `ENGINE=gx` (the default) renders each
scene with ManimGX on the Windows GPU, called from WSL through interop (`GX_EXE`; inside WSL it has no GPU).
`common.py` dispatches to `common_gx.py`, whose `Narrated` replays the voice pre-pass cache with
`add_sound` and times `self.at()` from the word timings. vlint's runtime record still comes from CE in
skip mode (`ENGINE=ce`, seconds per scene), so **every scene must run under both engines**: write the
API they share, and check new idioms with check.sh (CE) and a render (GX). ManimGX typesets with Typst
(LaTeX converted by mitex); common_gx patches `\'` accents, `\&`, `\ ` (as `\;` in maths), and in
Tex text the macros mitex prints as words or crashes on (`\quad`, `\,`, `~`, `\dots`, `\checkmark`,
`\textperiodcentered`, `\_`, ``` ``quotes'' ```). A LaTeX package or macro mitex lacks fails the GX render:
use plain LaTeX or Unicode. Every video renders with GX since the 2026-10-25 design pass (old ones keep
`TTS=chatterbox`). GX gotchas, each of which cost a render:
- Typst sets maths a little larger than CE's LaTeX, so a stack that just fits in the CE check can be
  cut off in the render (liquid_tc Solver's last equation). Keep ~0.3 from the edges; vlint `frame-margin`
  warns in the check, and `gx-frame-edge` refuses the join when ManimGX's own layout pass (the
  "layout: N problems" list in m_<Scene>.log) finds anything past an edge.
- `$a$$b$` (two maths runs touching) crashes Typst; `\$` prints "dollar"; a Tex text starting with `+ `, `- ` or
  `1. ` is Typst list markup ("+ PBC" came out as "1. PBC") (vlint: `gx-tex`, which also follows a script's label
  helpers such as `lab(t)`). A `\\` line break in Tex works. A text starting with `= ` is a Typst heading:
  the sign is dropped and nothing fails (g4_tutorial: "= channel" rendered as "channel", seen only on the
  writer's sheet; write `$=$ channel`. `gx-tex` looks for it now, and its first run over the corpus found
  one that had shipped: laser_rt's "= clinical linac").
- A MathTex with several underbraces or repeated substrings can fail with "cannot tell these parts
  apart": build the parts as separate MathTex.
- A wait that ends between frames is held as a frame sampled just inside the next animation, so the
  first stroke of a Write sat on screen for the whole pause. `Narrated.wait` now snaps every wait to
  the frame grid; a scene not built on `Narrated` must do the same.
- No scipy in the GX venv (write the numpy), no `rate_functions` module (common_gx gives a
  namespace), and a translucent fill can come out opaque (`slab_crlb` Intro's grease hid the SiPMs:
  lower `fill_opacity`).
metamono (15 scenes, 10 min) builds in 1:49, against 6:07 on CE. 3D gains most (a 20 s 3D scene:
CE 607 s, GX 12 s). ManimGL was ruled out: different API, no voiceover.

---

# Part IV: Pitfalls

**Drawing order**
- A thing placed inside an opaque shape that is built later is painted over by it and simply disappears.
  capstone's link readings were moved from under the boxes to inside them and vanished, because `links()`
  is built in the scene after the readings and its boxes carry a solid fill. `set_z_index(n)` on the thing
  that must stay visible; both engines honour it, and several videos already rely on it.
- A doubled edge is a placement, not a style: a frame whose edge lands on another frame's edge draws two
  parallel lines a pixel apart and reads as two objects stuck together. Inside, or clear of it.
- **An opaque decoration built behind something declares `set_z_index` where it is built**, not where the
  clash shows. A page-stack fan built after page 1 painted over the report for the 16 seconds the voice
  spent introducing it. No rule sees this: the frame is legal, nothing vanishes at its own intro, and a
  settled-frame sheet samples the moment it looks deliberate. `tools/watch.sh` catches it.

**Editing scripts**
- Any edit touching a LaTeX backslash goes through the Edit tool, never a Python replace script.
  In a non-raw string, `"\t"` in `\textbf` or `\tau` becomes a tab and the match silently fails;
  this happened in three videos, twice more while writing vlint itself, and again in the 2026-10-25
  design pass, where a quoted bash heredoc also halved `\\` (Git Bash). Python scripts are fine for
  backslash-free changes such as numbers and positions. For whole scenes, Write the new classes to a
  scratchpad file and splice them in. `sed` is no safer: `s/.../.../` eats the backslash in `\l`, so
  `\lambda'_i` became `\ambda'_i` (`zzb_slab`).
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
  the pulse (recon video, four images). Pulse its frame (`framed(...)[1]`) or `Circumscribe` it
  (vlint: `indicate-image`).
- Dimming the rest of the screen (a spotlight helper) must only touch `VMobject`s. `scene.mobjects`
  also holds `ValueTracker`s, and fading or restoring them crashes with "Please override in a
  child class" (`laser_rt` retrofit). Skip mobjects that have updaters too.
- Two labels attached to the same edge of a box (`next_to(box, UP)`) will overlap unless they are
  aligned to opposite ends (`align_to(box, LEFT)` / `align_to(box, RIGHT)`). Check a late frame of the scene
  (vlint: `text-overlap` and `frame-clip` catch label-on-label and cut-off labels; a label over a shape, such
  as a bar, is still for the eye).
- `set_opacity` on a line sets its *fill* opacity too, and a polyline with a fill is a polygon: dimming an
  unfocused track with `ev.animate.set_opacity(0.3)` turned it into a grey wedge between its corners (geant4
  Toolkit and Close; only under ManimGX, so the CE check saw nothing and only the review sheet did). Dim
  anything made of open lines with `set_stroke(opacity=...)`.
- `d.get(k, f"{k:g}")` evaluates the default even for string keys; use a conditional.
- Narration built with an f-string (`f"{say(x)} times the bound"`) is a computed text: `voice_prepass.py` skips
  it and ManimGX only reads the cache, so the render fails with `KeyError: '<the sentence>'`. After changing
  such a line, voice it with a CE pass, `tools/check.sh <video> <Scene>`, then rerun `run_v.sh`
  (`zzb_slab` Model and Threshold). Re-running the pre-pass does not help; it reports "all cached".
- Under ManimGX, `TransformFromCopy(a, target)` and `Transform` reshape `target` itself, so its parts
  (`target[3]`) no longer match the glyphs drawn: a box or `Indicate` on them lands on nothing (`zzb_slab`
  ClosedForm, where an earlier `Indicate(prod[3])` had been invisible too). Transform into `target.copy()`
  when you will point at the target's parts later.
- A `self.play` after the last `self.at` in a voiceover runs at once, not when the speech ends. A closing
  fade there (`unpoint`, a dim restore) removes the cue while its words are still being spoken; put it at
  the next block's first bookmark instead.
- ManimGX `Axes` whose ranges do not start at 0 drew the x axis through y = 1 on a log plot. Shift the ranges
  to start at 0 (keep the offset as `ax.lo`), hide the axes' stroke and draw your own frame lines. `add` the
  hidden axes rather than `Create` them, or `vanished-after-intro` fails (`zzb_slab` Threshold).
- `ArcBetweenPoints(p, q, angle)` turns counter-clockwise from p to q, so a left-to-right arc with a positive
  angle dips below the chord and a negative one bulges above (`flow_match` Recipe: the arc rose through the
  label meant for the straight line above it). It also works its centre out from the chord and the angle, and
  two centres fit any such pair: past half a turn it takes the other one. A loop drawn round a figure that way
  hangs off it (`mc_recon` Intro, a `CurvedArrow` meant to circle the detector ring, which swung outside it and
  cut through the crystals). To circle something, say so: `Arc(radius=, start_angle=, angle=, arc_center=)` and
  put your own tip at the end, rotated to the tangent (`end - PI` for a clockwise sweep).
- A point cloud drawn at the scale of a full-frame scene looks lost in half a frame: size each panel from its
  data's real extent, filling its half (`flow_match` Likelihood, Average, Reflow were redrawn bigger).
- When a title changes, `ReplacementTransform` it.
- A wait that *ends* a GX scene writes no frames, so narration still being spoken over a last still frame has
  no picture to sit on: the scene file comes out shorter than its own audio, and in the concat that pushes
  every later scene's narration late (`mc_recon` Intro, Loop and Hardware, caught by `av-sync` and
  `join-duration` on the joined video, not by anything per scene). `render_lib.sh` now holds the last frame
  out to the audio before joining; a scene that wants to end on a held frame should still earn it with
  something that moves.
- Whatever the CE scene gets from vlint's runtime monitor, the GX scene needs too, even as a no-op:
  `self.vlint_off("rule-id")` existed only under CE, so a scene that switched a layout rule off for a block
  passed every check and then died on the GPU with `AttributeError` (`mc_recon` Scatter). It is in
  `common_gx.Narrated` now. The pattern to watch for is any API that only the checking engine defines.
- ManimGX animations have no `set_run_time`, `set_rate_func` or `set_name`; CE's do, so such a line passes
  every check and then kills the GPU render (`mc_recon` Hardware: `'Rotate' object has no attribute
  'set_run_time'`). Give the animation the value in its constructor (`run_time=`, `rate_func=`), or wrap an
  `.animate` chain in `AnimationGroup(..., run_time=...)` (vlint: `gx-anim-setter`).

**Shell (Windows → WSL)**
- `wsl bash -lc '... $var ...'` from Git Bash loses variables, so put loops in a `.sh` file.
  Run it with `MSYS_NO_PATHCONV=1 wsl bash /mnt/c/.../x.sh`, otherwise Git Bash rewrites `/mnt/c`.
- Git Bash's `/tmp` is not Windows Python's `/tmp`; use the scratchpad.
