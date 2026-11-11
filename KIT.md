# KIT: the shared drawing primitives

`kit.py` holds the parts that more than one video needed, written once and drawn under both engines by
`kit_gallery` (its review sheets are the pictures of everything below). A script uses it with
`from kit import *` in place of `from common import *`; kit re-exports all of common.

**Not every video needs every section.** Videos differ in kind: a code walk uses the code and structure
sections, a detector paper the plots and detectors, a page walk the reused figures. A primitive goes in the
section of the kind of video that needs it, and no video is asked to use one that does not fit its picture.
A script's fingerprint counts only the kit functions it reaches, so changing one primitive re-renders only the
videos that draw with it.

**Read this list before writing a helper.** If a primitive does the job, use it. If it nearly does, pass it
arguments. If it is wrong for the picture, write your own and say why in the report. A helper of yours that
another video also needed is promoted here at the end of the build (DESIGN Part III, step 8;
`python tools/kit_promote.py <video>`).

Every primitive is built at ORIGIN and returns a VGroup with its parts named on it (`g.box`, `g.label`).
The docstring in kit.py says what `move_to` centres. Point functions (`g.at(d)`, `g.slot(i)`, `g.pt(x, z)`)
read the live geometry, so they hold after a move or a scale. Colours are always arguments, and nothing is
added to the scene for you. Dim an open polyline (poly, wavy, a stack's frame) with `set_stroke(opacity=...)`,
never `set_opacity`, which fills it.

## Text and code

| Primitive | What it draws | Parts and points |
|---|---|---|
| `P(x, y)` | a 3-D point from 2 or 3 numbers, a tuple or a point | |
| `lab(t, size=26, color, shows=())` | a Tex label; a leading `+ `, `- ` or `= ` is set as a sign under Typst | `shows`: numbers a highlight displays |
| `num(t, size=28, color)` | a bold number with its unit, `num("511 keV")` | |
| `credit(t)`, `note(t)` | a figure's source, bottom right; "schematic" or "computed here", bottom left | |
| `mono(s, cw=0.15, color)` | one name or one line of code in monospace, each character `cw` wide (0.15 is about 20 pt, 0.18 about 24 pt; under 0.13 is small on a phone) | `m.src` |
| `code(lines, cw, pitch, color, colors)` | a snippet; leading spaces indent | `cd[k]` is line k |
| `lit(cd, k, dim=0.35)` | animations lighting line k (or a tuple, or None) and dimming the rest: `self.at("m", *lit(cd, 2))` | |
| `part(line, piece, nth=0)` | the glyphs of `piece` inside a mono line, to colour or point at | |
| `lput(m, x, y)` | puts m's left ink edge at x and its first row (code, term, tree) or root (ftree) at y | |
| `term(lines, w, cw, pitch, color)` | a terminal with output lines | `g.panel`, `g.bar`, `g.lines[k]` |

## Reused figures

| Primitive | What it draws | Parts and points |
|---|---|---|
| `figcard(path, h, w)` | a figure cut from the source on white paper (a Group); pulse the card, not the image | `g.card`, `g.img` |
| `fig_box(g, x0, y0, x1, y1, color)` | a frame on a figcard, the region in fractions of the image; frame a whole label or none of it | |

## Objects, files and structure

| Primitive | What it draws | Parts and points |
|---|---|---|
| `card(name, color, sub=None, w, h)` | an object or class: tinted box, monospace name, optional method line | `g.box`, `g.name`, `g.sub` |
| `fcard(name, color)` | a file: a page with a folded corner | `g.page`, `g.name` |
| `ftree(root, names, colors)` | a folder with its files | `g.root`, `g.twigs[k]`, `g.cards[k]` |
| `slots_box(names, n, w, h, title, color)` | a framework your objects plug into: dashed slots along the bottom | `g.slots[i]`, `g.names`, `g.title`, `g.free` (area above the slots) |
| `nest(names, w, h, row, inset, color)` | levels one inside another (run > event > step) | `g.levels[i]` = (box, name), `g.hook(i, LEFT/RIGHT)`, `g.inside` |
| `tree(rows, cw, pitch, indent)` | a call tree, `rows = [(depth, text, colour)]` | `g[k]` = (twig, label) |
| `rowpt(tr, k)`, `runner(color)` | where the "control is here" marker sits on row k, and the marker | |
| `lane(name, w, h, color)` | a swim lane: a thread, a worker, a channel | `g.strip`, `g.name`, `g.x(f)` |
| `stack_frame(n, w, cell, color, name)` | an open-topped stack; move_to centres frame and name together | `g.frame`, `g.name`, `g.slot(i)` (0 at the bottom) |
| `token(text, color, w, h)` | an item on a stack or in a queue | `g.box`, `g.label` |
| `cells(names, w, h, color)` | a record as a row of named cells | `g.boxes[k]`, `g.names` |
| `icon(kind, color, s)`, `tool(kind, name)` | a pictogram (`gear`, `tri`, `star`, `books`, `grid`), and one with a name under it; an icon must be pointed at, changed or measured | `g.icon`, `g.name` |

## Lines, marks and plots

| Primitive | What it draws | Parts and points |
|---|---|---|
| `poly(pts, color, sw)` | an open polyline: a track, a sampled curve | |
| `wavy(p, q, color, amp, wl)` | a photon's or a gamma's flight, tapering at both ends | |
| `arr(p, q)`, `carr(p, q, angle)` | a straight arrow, a curved one (left to right, a negative angle bulges up) | |
| `dashed(m)` | m drawn dashed | |
| `dim(a, b, text, side, bold=True)` | a dimension line at any angle, the length beside its middle on `side` | `g.line`, `g.label` |
| `flag_at(p, color, h)` | a flag planted on a point: a status, a milestone | `g.pole`, `g.pennant` |
| `step_seg(a, b, color)` | one step: hollow pre-step point, filled post-step point | `g.seg`, `g.pre`, `g.post` |
| `burst(p)`, `xmark(p)` | a flash; a cross for refused, absorbed or wrong | |
| `gauss(x0, y0, fwhm, h, color)` | a Gaussian of a given FWHM on a baseline | |
| `bars(rows, x0, y_top, unit, step)` | horizontal bars, `rows = [(name, value, text, colour)]`; a list of (bar, value, name) | |
| `time_axis(w, name)`, `tick_at(axis, f)` | a clock without numbers, and an event on it | `g.line`, `g.name`, `g.t(f)` |
| `gauge(n0, n_max, unit, name, color)` | a quantity that rises or runs down, driven by a tracker | `g.n` (ValueTracker), `g.frame`, `g.fill` |

## Detectors and light

| Primitive | What it draws | Parts and points |
|---|---|---|
| `sipm_grid(n=8, size)` | an n x n photodetector array face on; `g[k]` is channel k, row by row from the top left | |
| `slab_side(w, mm=(50, 10), n_tiles=8)` | a scintillator slab from the side: crystal, wrap, coupling, window, tiles (not to scale) | `g.crystal`, `g.coupling`, `g.window`, `g.tiles`, `g.wrap`, `g.pt(x_mm, z_mm)` |
| `snell(ratio, w, hh, R, theta)` | a ray at a flat interface, driven by `g.th`: refraction by Snell's law, reflection as bright as the Fresnel probability, total internal reflection past the critical angle | `g.th`, `g.O()`, `g.T()`, `g.crit`, and every ray and arc |

## Promoted from

g4_setup (the code helpers, files, folders, trees, terminals, lanes, icons), g4_inside (stack, token, cells,
time axis, gauge, slab, SiPM array, interface, dimension line, flag, step), and the corpus's most copied
helpers (`lab` in 31 videos, `poly` in 24, `dim` in 20, `wavy` in 15, `gauss` in 12, `bars` in 9).
Not yet promoted, though defined in many videos: the page walk (`page`, `mark`, `frame`, `crop`, `on`, `spot`,
`head`, `foot` and the `Walk` scene, copied into 15 videos), `pulse`, `tile`. `credit`, `note`, `figcard` and `fig_box` came from pet_g4_configs (`card(path, h)` in six videos).
