"""kit: drawing primitives shared by the videos, written once and tested under both engines.

A script uses it with `from kit import *` in place of `from common import *` (kit re-exports all of common).
Read KIT.md before writing a helper of your own: if a primitive here does the job, use it, and if it nearly does,
pass it arguments rather than copying it. A helper that a second video also needs is promoted here (DESIGN Part
III, step 8), with an entry in KIT.md and a part in kit_gallery's scenes, so it is drawn under both engines.

Conventions every primitive keeps:
  - It is built at ORIGIN and returns a VGroup with its parts hung on it by name (g.box, g.label ...); its
    docstring says what `move_to` centres. Point functions (g.at(d), g.slot(i)) read the live geometry, so they
    still hold after the group is moved or scaled.
  - Colours are arguments. Nothing here knows a video's palette.
  - Nothing is added to the scene and nothing is animated, except `lit`, which returns animations to play.
  - An open polyline (poly, wavy, a stack's frame) is dimmed with set_stroke(opacity=...), never set_opacity,
    which would fill it.
"""
import re

from common import *  # noqa: F401,F403

# ---- points ----------------------------------------------------------------------------------------------------


def P(x, y=None, z=None):
    """A 3-D point from (x, y), (x, y, z), a 2-tuple or a 3-D point. z is dropped: the videos are flat."""
    if y is None:
        x, y = x[0], x[1]
    return np.array([float(x), float(y), 0.0])


# ---- labels ----------------------------------------------------------------------------------------------------
# Typst (ManimGX) reads a text that starts "+ ", "- " or "= " as a list item or a heading and drops the sign, and
# "1. " as a numbered item. lab and num put a leading sign in maths, where both engines set it as a sign.
_SIGN = re.compile(r"^(\s*)([+\-=]+)(\s|$)")


def _safe(t):
    return _SIGN.sub(lambda m: f"{m.group(1)}${m.group(2)}${m.group(3)}", t, count=1)


def lab(t, size=26, color=GREY_B, shows=()):
    """A label (Tex). `shows` lists the numbers it displays when the text does not spell them (a highlight)."""
    m = Tex(_safe(t), font_size=size, color=color)
    if shows:
        m._shows = shows
    return m


def num(t, size=28, color=WHITE, shows=()):
    """A bold number with its unit: num("511 keV")."""
    return lab(r"\textbf{" + t + "}", size, color, shows)


def credit(t, size=18, color=GREY_C):
    """The source of a reused or redrawn figure, small, bottom right (defined in 15 videos before this)."""
    return lab(t, size, color).to_corner(DR, buff=0.25)


def note(t, size=22, color=GREY_C):
    """The line that says a drawing is a schematic, or a number was computed here, bottom left."""
    return lab(t, size, color).to_corner(DL, buff=0.28)


# ---- reused figures: a page or a figure cut from the source -----------------------------------------------------


def figcard(path, h=None, w=None, pad=0.08):
    """A figure cut from the source (a png) on white paper. A Group, not a VGroup: g.card the paper, g.img the
    image; move_to centres both. Pulse the card, never the image (Indicate recolours an image)."""
    im = ImageMobject(str(path))
    im.set_height(h) if h else im.set_width(w) if w else None
    back = Rectangle(width=im.width + 2 * pad, height=im.height + 2 * pad, fill_color=WHITE, fill_opacity=1,
                     stroke_color=GREY_D, stroke_width=1.5).move_to(im)
    g = Group(back, im)
    g.card, g.img = back, im
    return g


def fig_box(g, x0, y0, x1, y1, color=YELLOW, sw=4):
    """A frame on a figcard around a region given as fractions of the image (0, 0 top left; 1, 1 bottom right).
    Read the fractions off the png, and frame a whole label or none of it: a frame through a digit misreads."""
    im = g.img
    ul = im.get_corner(UL)
    a = ul + RIGHT * x0 * im.width + DOWN * y0 * im.height
    b = ul + RIGHT * x1 * im.width + DOWN * y1 * im.height
    return Rectangle(width=b[0] - a[0], height=a[1] - b[1], stroke_color=color, stroke_width=sw).move_to((a + b) / 2)


# ---- code: names and code as they are written ---------------------------------------------------------------
# Text, not Tex: _, ->, ::, &, *, $ and # mean nothing to Text under either engine.
_ADV = []


def _adv():
    """One character's advance at Text's default size (the engines set the face at different sizes)."""
    if not _ADV:
        ref = Text("M" * 20, font="monospace")
        _ADV.append((ref.submobjects[19].get_center()[0] - ref.submobjects[0].get_center()[0]) / 19)
    return _ADV[0]


def _line(s, cw, color):
    """The glyphs of s at character width cw, pen origin at x = 0 and text midline at y = 0. A two-glyph strut
    (a capital and a descender) is set in front and stripped, so every line has the same midline whatever letters
    it holds."""
    t = Text("Hg" + s, font="monospace")
    t.scale(cw / _adv())
    g = t.submobjects
    y0 = (g[0].get_top()[1] + g[1].get_bottom()[1]) / 2
    x0 = g[0].get_center()[0] + 1.5 * cw
    out = VGroup(*g[2:])
    out.shift(LEFT * x0 + DOWN * y0)
    out.set_color(color)
    out.src = s
    out._text = True             # glyphs lifted out of a Text: vlint's layout rules read it as words, not a panel
    return out


def mono(s, cw=0.15, color=WHITE):
    """One name or one line of code in monospace, each character `cw` wide: 0.15 is about 20 pt and 0.18 about
    24 pt, the label size; under 0.13 it is small on a phone. Centred in x on ORIGIN, text midline on y = 0, so
    lines placed at the same y share a baseline. m.src is the string. A VGroup of glyphs (spaces have none)."""
    out = _line(s, cw, color)
    out.shift(LEFT * out.get_center()[0])
    return out


def code(lines, cw=0.15, pitch=0.44, color=WHITE, colors=None):
    """A snippet: cd[k] is line k (a mono, with .src). Lines share a left pen edge, leading spaces indent, and
    sit `pitch` apart. Place it with lput(cd, x, y) (left ink edge at x, FIRST line's midline at y) or move_to.
    Walk it with lit(): bring it on dimmed and light the line the voice is reading."""
    out = VGroup()
    for k, s in enumerate(lines):
        out.add(_line(s, cw, colors[k] if colors else color).shift(DOWN * k * pitch))
    out.rows = True
    return out


def part(line, piece, nth=0):
    """The glyphs of `piece` inside a mono line (its nth occurrence), as a VGroup: to colour, point at or swap."""
    s, i = line.src, -1
    for _ in range(nth + 1):
        i = s.index(piece, i + 1)
    a = len(s[:i].replace(" ", ""))
    return VGroup(*line.submobjects[a:a + len(piece.replace(" ", ""))])


def lit(cd, k, dim=0.35):
    """Animations that light line k of a code() block (k: an int, a tuple of ints, or None for none) and dim the
    rest. Play them on the word: self.at("m", *lit(cd, 2), other_anim)."""
    on = () if k is None else (k if isinstance(k, (tuple, list)) else (k,))
    return [ln.animate.set_opacity(1.0 if i in on else dim) for i, ln in enumerate(cd)]


def lput(m, x, y):
    """Shift m so its left ink edge is at x and its reference row is at y: the first line of a code() or term()
    block, the first row's label of a tree(), the root label of an ftree(), and m's own centre for anything else."""
    rows = getattr(m, "rows", False)
    ref = m
    if rows is True:
        ref = m[0]
    elif rows == "tree":
        ref = m[0][1]
    elif rows == "ftree":
        ref = m[0]
    return m.shift(RIGHT * (x - m.get_left()[0]) + UP * (y - ref.get_center()[1]))


# ---- boxes, files, folders, terminals ------------------------------------------------------------------------


def card(name, color=BLUE_L, sub=None, w=None, h=0.6, cw=0.15, fill=0.22):
    """An object or a class: a tinted rounded box with its name in monospace and, if `sub` is given, a second,
    smaller line under it (a method). `w` defaults to the name's width plus a margin. move_to centres the box.
    g.box, g.name, g.sub (None without one). The box is tinted: save_state() and set_opacity to dim it."""
    nm = mono(name, cw, WHITE)
    sb = mono(sub, cw * 0.86, GREY_B) if sub else None
    inner = VGroup(nm, sb).arrange(DOWN, buff=0.08) if sb else nm
    box = RoundedRectangle(width=w or inner.width + 0.4, height=max(h, inner.height + 0.24), corner_radius=0.1,
                           stroke_color=color, stroke_width=2.5, fill_color=color, fill_opacity=fill)
    inner.move_to(box)
    g = VGroup(box, nm) if sb is None else VGroup(box, nm, sb)
    g.box, g.name, g.sub = box, nm, sb
    return g


def _page(w, h, color, fold=0.14, sw=2):
    """A sheet with a folded corner, as separate lines: a line has no area, so dimming it cannot fill it."""
    a, b, c, d, e = P(-w / 2, h / 2), P(w / 2 - fold, h / 2), P(w / 2, h / 2 - fold), P(w / 2, -h / 2), P(-w / 2, -h / 2)
    f = P(w / 2 - fold, h / 2 - fold)
    return VGroup(*[Line(p, q, stroke_color=color, stroke_width=sw)
                    for p, q in ((a, b), (b, c), (c, d), (d, e), (e, a), (b, f), (f, c))])


def fcard(name, color=WHITE, cw=0.14, w=None, h=0.46):
    """A file: a page with a folded corner and its name in monospace. move_to centres the page.
    g.page, g.name. set_color and set_opacity both do what they say (the page is lines only)."""
    nm = mono(name, cw, color)
    pg = _page(w or nm.width + 0.44, h, color)
    g = VGroup(pg, nm)
    g.page, g.name = pg, nm
    return g


def ftree(root, names, colors=None, cw=0.14, pitch=0.6, h=0.46, line_color=GREY_B):
    """A folder: its name, then one fcard per file under it, joined by twigs. g.root, g.twigs, g.cards;
    g.cards[k] is file k and g.twigs[k] its twig. Place with lput (the root label is the reference row)."""
    lb = _line(root, cw, line_color)
    twigs, cards = VGroup(), VGroup()
    xt, xc = 0.2, 0.6
    for k, n in enumerate(names):
        y = -(k + 1) * pitch
        c = fcard(n, colors[k] if colors else WHITE, cw, h=h)
        c.shift(P(xc, y) - c[0].get_left())
        top = -0.22 if k == 0 else y + pitch
        twigs.add(VGroup(Line(P(xt, top), P(xt, y), stroke_color=line_color, stroke_width=2),
                         Line(P(xt, y), P(xc, y), stroke_color=line_color, stroke_width=2)))
        cards.add(c)
    g = VGroup(lb, twigs, cards)
    g.root, g.twigs, g.cards = lb, twigs, cards
    g.rows = "ftree"
    return g


def term(lines, w=4.6, cw=0.15, pitch=0.42, color=GREEN_L, frame_color=GREY_B):
    """A terminal: a dark panel with three dots on its title bar and lines of output. move_to centres the panel.
    g.panel, g.bar, g.lines (a code() block: g.lines[k] is line k; bring lines on one by one as they are printed)."""
    h = len(lines) * pitch + 0.7
    panel = RoundedRectangle(width=w, height=h, corner_radius=0.12, stroke_color=frame_color, stroke_width=2,
                             fill_color="#05070b", fill_opacity=1)
    bar = VGroup(*[Dot(radius=0.05, color=frame_color).move_to(P(-w / 2 + 0.25 + 0.18 * i, h / 2 - 0.2)) for i in range(3)])
    ls = code(lines, cw, pitch, color)
    lput(ls, -w / 2 + 0.3, h / 2 - 0.62)
    g = VGroup(panel, bar, ls)
    g.panel, g.bar, g.lines = panel, bar, ls
    return g


def lane(name, w=8.0, h=0.72, color=GREY_B, cw=0.13):
    """A swim lane (a thread, a worker, a channel): a long faint strip with its name inside the left end.
    move_to centres the strip. g.strip, g.name. g.x(f): the x a fraction f (0..1) along the free part."""
    strip = RoundedRectangle(width=w, height=h, corner_radius=0.14, stroke_color=color, stroke_width=2,
                             fill_color=color, fill_opacity=0.07)
    nm = mono(name, cw, color)
    nm.shift(P(-w / 2 + 0.25 + nm.width / 2, 0))
    g = VGroup(strip, nm)
    g.strip, g.name = strip, nm
    g.x = lambda f: nm.get_right()[0] + 0.25 + f * (strip.get_right()[0] - 0.2 - nm.get_right()[0] - 0.25)
    return g


def icon(kind, color=WHITE, s=0.42):
    """A small pictogram, about 2s across: "gear" (a compiler, a machine), "tri" (a build tool), "star" (a runner),
    "books" (a library), "grid" (a table, data). An icon must be pointed at, changed or measured (vlint icon-idle)."""
    if kind == "gear":
        pts = []
        for i in range(8):
            a = TAU * i / 8
            for da, r in ((-0.2, 0.74), (-0.12, 1.0), (0.12, 1.0), (0.2, 0.74)):
                pts.append(s * r * P(np.cos(a + da), np.sin(a + da)))
        return VGroup(Polygon(*pts, stroke_color=color, stroke_width=2.5, fill_color=color, fill_opacity=0.2),
                      Circle(radius=0.3 * s, stroke_color=color, stroke_width=2.5))
    if kind == "tri":
        v = [s * 1.1 * P(np.cos(a), np.sin(a)) + DOWN * 0.12 * s for a in (PI / 2, PI / 2 + TAU / 3, PI / 2 + 2 * TAU / 3)]
        c = DOWN * 0.12 * s
        return VGroup(Polygon(*v, stroke_color=color, stroke_width=2.5, fill_color=color, fill_opacity=0.2),
                      *[Line(c, p, stroke_color=color, stroke_width=2) for p in v])
    if kind == "star":
        pts = [s * (1.0 if i % 2 == 0 else 0.36) * P(np.cos(TAU * i / 8 + PI / 4), np.sin(TAU * i / 8 + PI / 4)) for i in range(8)]
        return VGroup(Polygon(*pts, stroke_color=color, stroke_width=2.5, fill_color=color, fill_opacity=0.2),
                      Circle(radius=0.12 * s, stroke_color=color, stroke_width=2.5))
    if kind == "books":
        return VGroup(*[Rectangle(width=2.0 * s, height=0.5 * s, stroke_color=color, stroke_width=2.5, fill_color=color,
                                  fill_opacity=0.2).shift(P(dx * s, (1 - i) * 0.58 * s))
                        for i, dx in enumerate((0.12, -0.1, 0.05))])
    if kind == "grid":
        return VGroup(*[Rectangle(width=0.62 * s, height=0.44 * s, stroke_color=color, stroke_width=2, fill_color=color,
                                  fill_opacity=0.2 if j == 0 else 0.0).shift(P((i - 1) * 0.62 * s, (1 - j) * 0.44 * s))
                        for j in range(3) for i in range(3)])
    raise ValueError(f"icon kind {kind!r}: gear, tri, star, books or grid")


def tool(kind, name, color=WHITE, cw=0.13, s=0.42):
    """An icon with its name in monospace under it. move_to centres the pair; g.icon, g.name."""
    ic = icon(kind, color, s)
    nm = mono(name, cw, color)
    nm.shift(P(ic.get_center()[0], ic.get_bottom()[1] - 0.24))
    g = VGroup(ic, nm)
    g.icon, g.name = ic, nm
    return g


# ---- structure: slots, nesting, call trees, stacks, records --------------------------------------------------


def slots_box(names=(), n=None, w=8.0, h=2.2, slot_w=None, slot_h=0.6, cw=0.12, title=None, color=GREY_B,
              title_cw=0.15):
    """A framework that your objects plug into: a rounded box with a row of dashed slots along its bottom, each
    named above in monospace (`names`), or `n` unnamed slots. A card() of the slot's size plugs in with
    card.animate.move_to(g.slots[i]). move_to centres the box. g.box, g.title, g.slots, g.names.
    g.free: an invisible rectangle over the area above the slots, for what the framework builds or runs."""
    k = n or len(names)
    box = RoundedRectangle(width=w, height=h, corner_radius=0.18, stroke_color=color, stroke_width=3,
                           fill_color=color, fill_opacity=0.08)
    sw = slot_w or (w - 0.5 - (k - 1) * 0.2) / k
    gap = (w - k * sw) / (k + 1)
    slots, nms = VGroup(), VGroup()
    for i in range(k):
        r = dashed(RoundedRectangle(width=sw, height=slot_h, corner_radius=0.1, stroke_color=color, stroke_width=2))
        r.move_to(P(-w / 2 + gap + sw / 2 + i * (sw + gap), -h / 2 + 0.2 + slot_h / 2))
        slots.add(r)
        if names:
            nms.add(mono(names[i], cw, color).next_to(r, UP, buff=0.1))
    ttl = VGroup()
    if title:
        ttl = mono(title, title_cw, color)
        ttl.shift(P(-w / 2 + 0.3 + ttl.width / 2, h / 2 - 0.34))
    top = box.get_top()[1] - (0.62 if title else 0.15)
    bot = (nms.get_top()[1] if names else slots.get_top()[1]) + 0.12
    free = Rectangle(width=w - 0.5, height=max(top - bot, 0.1), stroke_width=0).move_to(P(0, (top + bot) / 2))
    g = VGroup(box, ttl, slots, nms, free)
    g.box, g.title, g.slots, g.names, g.free = box, ttl, slots, nms, free
    return g


def nest(names, w=12.0, h=5.4, row=0.7, inset=0.45, color=GREY_B, size=26):
    """Levels one inside the other (run > event > track > step; study > patient > scan): one box per name, each
    named at the top left of its own row. move_to centres the outer box. g.levels[i] is VGroup(box, name).
    g.hook(i, side): a point on level i's row, just right of its name (side=LEFT) or just inside its right edge
    (side=RIGHT), to hang a label there with next_to(..., RIGHT or LEFT, buff=0). g.inside: the innermost box's
    free area."""
    levels = VGroup()
    for i, nm in enumerate(names):
        bw, bh = w - 2 * i * inset, h - i * (row + 0.14)
        b = RoundedRectangle(width=bw, height=bh, corner_radius=0.14, stroke_color=color, stroke_width=2.5,
                             fill_color=color, fill_opacity=0.05)
        b.move_to(DOWN * (h / 2 - 0.14 * i - bh / 2))
        t = lab(nm, size, WHITE)
        t.move_to(b.get_corner(UL) + RIGHT * (0.3 + t.width / 2) + DOWN * row / 2)
        levels.add(VGroup(b, t))
    inner = levels[-1][0]
    inside = Rectangle(width=inner.width - 0.5, height=max(inner.height - row - 0.2, 0.1), stroke_width=0).move_to(
        inner.get_bottom() + UP * (0.15 + max(inner.height - row - 0.2, 0.1) / 2))
    g = VGroup(levels, inside)
    g.levels, g.inside = levels, inside

    def hook(i, side=LEFT):
        x = levels[i][1].get_right()[0] + 0.3 if np.dot(side, RIGHT) < 0 else levels[i][0].get_right()[0] - 0.3
        return P(x, levels[i][1].get_center()[1])
    g.hook = hook
    return g


def tree(rows, cw=0.15, pitch=0.5, indent=0.45, line_color=GREY_B):
    """A call tree (or any indented outline): rows = [(depth, text, colour)], depth 0 at the left. Text is set in
    monospace. g[k] = VGroup(twig, label) for row k; a row at depth d hangs from the nearest row above at depth
    d - 1. Place with lput (the first row is the reference). rowpt(g, k) is where a runner() dot sits."""
    out = VGroup()
    for k, (d, s, c) in enumerate(rows):
        lb = _line(s, cw, c).shift(P(d * indent, -k * pitch))
        tw = VGroup()
        if d > 0:
            p = max(j for j in range(k) if rows[j][0] == d - 1)
            x = (d - 1) * indent + 0.14
            tw.add(Line(P(x, -p * pitch - 0.19), P(x, -k * pitch), stroke_color=line_color, stroke_width=2),
                   Line(P(x, -k * pitch), P(d * indent - 0.08, -k * pitch), stroke_color=line_color, stroke_width=2))
        out.add(VGroup(tw, lb))
    out.rows = "tree"
    return out


def rowpt(tr, k):
    """The point just left of row k's label in a tree(): where the runner() sits while that row runs."""
    return tr[k][1].get_left() + LEFT * 0.2


def runner(color=YELLOW):
    """A marker for "control is here": a dot in a ring. Move it from row to row of a tree()."""
    return VGroup(Dot(radius=0.08, color=color), Circle(radius=0.15, stroke_color=color, stroke_width=2, stroke_opacity=0.6))


def stack_frame(n=6, w=2.1, cell=0.52, color=GREY_B, name="stack", size=26):
    """A stack: an open-topped box with room for n token()s, named underneath. move_to centres frame AND name;
    use g.frame to place the box alone. g.slot(i): the centre of place i, 0 at the bottom. Push with
    tok.animate.move_to(g.slot(i)); pop by moving it out over the top."""
    hh = n * cell + 0.16
    fr = poly([P(-w / 2, hh / 2), P(-w / 2, -hh / 2), P(w / 2, -hh / 2), P(w / 2, hh / 2)], color, 3.5)
    nm = lab(name, size, color).next_to(fr, DOWN, buff=0.14)
    g = VGroup(fr, nm)
    g.frame, g.name = fr, nm
    g.slot = lambda i: fr.get_bottom() + UP * (0.08 + cell * (i + 0.5))
    return g


def token(text, color, w=1.8, h=0.42, size=24):
    """An item in a stack or a queue: a small filled tile with a Tex label (r"$\\gamma$", r"e$^-$"). g.box, g.label."""
    box = RoundedRectangle(width=w, height=h, corner_radius=0.08, stroke_color=color, stroke_width=2.5,
                           fill_color=color, fill_opacity=0.28)
    t = vlint_ok(lab(text, size, WHITE).move_to(box), "label-on-ink")     # a label on its own tile, on purpose
    g = VGroup(box, t)
    g.box, g.label = box, t
    return g


def cells(names, w=1.0, h=0.5, color=ORANGE_L, size=24):
    """A record as a row of empty cells, each named above it: cells(("x", "y", "z", "t", "e")). move_to centres
    the row. g.boxes, g.names. Fill a cell as its value is read: g.boxes[k].animate.set_fill(color, opacity=0.6)."""
    boxes = VGroup(*[Rectangle(width=w, height=h, stroke_color=color, stroke_width=2.5, fill_color=color, fill_opacity=0)
                     .move_to(RIGHT * k * w) for k in range(len(names))])
    nm = VGroup(*[lab(n, size, color).next_to(boxes[k], UP, buff=0.1) for k, n in enumerate(names)])
    g = VGroup(boxes, nm)
    g.boxes, g.names = boxes, nm
    g.move_to(ORIGIN)
    return g


# ---- lines and marks ----------------------------------------------------------------------------------------


def poly(pts, color=WHITE, sw=3):
    """An open polyline through points (a track, a curve from samples)."""
    return VMobject(stroke_color=color, stroke_width=sw).set_points_as_corners([P(p) if len(p) == 2 else np.array(p, dtype=float) for p in pts])


def wavy(p, q, color=YELLOW, amp=0.07, wl=0.3, sw=3):
    """A photon's (or a gamma's) flight from p to q: a sine that tapers to nothing at both ends. An open polyline.
    Keeps z, like poly, so it lands on a point inside a 3D scene (lxe_tpc: the gamma stopped short of its hit)."""
    p, q = [P(x) if len(x) == 2 else np.array(x, dtype=float) for x in (p, q)]
    L = np.linalg.norm(q - p)
    u = (q - p) / L
    v = np.array([-u[1], u[0], 0.0])
    n = max(int(L / 0.02), 2)
    pts = [p + u * L * i / n + v * amp * np.sin(TAU * L * i / n / wl) * min(1, 6 * i / n, 6 * (n - i) / n) for i in range(n + 1)]
    return VMobject(stroke_color=color, stroke_width=sw).set_points_as_corners(pts)


def arr(p, q, color=WHITE, sw=3):
    """A straight arrow from p to q with a small tip, touching both ends."""
    return Arrow(P(p), P(q), buff=0, color=color, stroke_width=sw, tip_length=0.17, max_tip_length_to_length_ratio=0.5)


def carr(p, q, angle=-PI / 3, color=WHITE, sw=3):
    """A curved arrow from p to q. Going left to right, a negative angle bulges upward."""
    return CurvedArrow(P(p), P(q), angle=angle, color=color, stroke_width=sw, tip_length=0.17)


def dashed(m, n=None):
    """m drawn dashed, with a dash count that suits its size."""
    return DashedVMobject(m, num_dashes=n or max(int(11 * (m.width + m.height)), 14))


def dim(a, b, text, side=UP, color=WHITE, size=26, buff=0.12, tick=0.1, bold=True):
    """A dimension line from a to b, at any angle, with end ticks and its length written beside its middle, on
    the side of the line that `side` points to. g.line (line and ticks), g.label."""
    a, b = P(a), P(b)
    u = (b - a) / np.linalg.norm(b - a)
    nrm = np.array([-u[1], u[0], 0.0])
    if np.dot(nrm, side) < 0:
        nrm = -nrm
    ln = Line(a, b, stroke_color=color, stroke_width=2.5)
    ticks = VGroup(*[Line(p - tick * nrm, p + tick * nrm, stroke_color=color, stroke_width=2.5) for p in (a, b)])
    t = (num(text, size, color) if bold else lab(text, size, color))
    reach = abs(nrm[0]) * t.width / 2 + abs(nrm[1]) * t.height / 2          # the label's half-extent across the line
    t.move_to((a + b) / 2 + nrm * (tick + buff + reach))
    g = VGroup(VGroup(ln, ticks), t)
    g.line, g.label = g[0], t
    return g


def flag_at(p, color=GREEN_L, h=0.42):
    """A small flag planted with its foot on point p (a status set on a point, a milestone). Any h works: the
    pennant is never taller than the pole."""
    p = P(p)
    ph = min(0.36, 0.8 * h)
    pole = Line(p, p + UP * h, color=color, stroke_width=3)
    pen = Polygon(p + UP * h, p + UP * (h - ph / 2) + RIGHT * 0.26 * ph / 0.36, p + UP * (h - ph),
                  color=color, fill_color=color, fill_opacity=1, stroke_width=1)
    g = VGroup(pole, pen).set_z_index(6)
    g.pole, g.pennant = pole, pen
    return g


def burst(p, color=YELLOW, r=0.22, n=8):
    """A flash at p (an interaction, a detection): n short rays."""
    p = P(p)
    return VGroup(*[Line(p + 0.35 * r * P(np.cos(a), np.sin(a)), p + r * P(np.cos(a), np.sin(a)), stroke_color=color, stroke_width=3)
                    for a in np.linspace(0, TAU, n, endpoint=False)])


def xmark(p, s=0.12, color=RED):
    """A cross at p: refused, absorbed, killed, wrong."""
    p = P(p)
    return VGroup(Line(p + s * P(-1, -1), p + s * P(1, 1), stroke_color=color, stroke_width=4),
                  Line(p + s * P(-1, 1), p + s * P(1, -1), stroke_color=color, stroke_width=4))


def step_seg(a, b, color=WHITE, bg="#0f1117"):
    """One step of a track: a hollow point at a, a filled point at b, a straight segment between. g.seg, g.pre, g.post."""
    a, b = P(a), P(b)
    seg = Line(a, b, color=color, stroke_width=3.5)
    pre = Circle(radius=0.09, color=color, stroke_width=3).move_to(a).set_fill(bg, opacity=1).set_z_index(4)
    post = Dot(b, radius=0.09, color=color).set_z_index(4)
    g = VGroup(seg, pre, post)
    g.seg, g.pre, g.post = seg, pre, post
    return g


# ---- plots without axes ---------------------------------------------------------------------------------------


def gauss(x0, y0, fwhm, h, color=WHITE, sw=4, n=81):
    """A Gaussian of full width `fwhm` (scene units) and height h, centred at x0 on the baseline y = y0, drawn to
    3.2 sigma each side. An open polyline."""
    s = fwhm / 2.3548
    xs = np.linspace(-3.2 * s, 3.2 * s, n)
    return poly([[x0 + x, y0 + h * np.exp(-0.5 * (x / s) ** 2), 0] for x in xs], color, sw)


def bars(rows, x0, y_top, unit, step=1.0, h=0.34, name_size=22, value_size=26, name_color=GREY_B):
    """Horizontal bars from a common left edge x0, top row at y_top: rows of (name, value, text, colour). Each bar
    is value * unit long, with its name above its left end and `text` at its right end (tagged with the value for
    vlint's number checks). A list of VGroup(bar, value, name): grow a bar with GrowFromEdge(g[0], LEFT)."""
    out = []
    for i, (name, v, txt, c) in enumerate(rows):
        y = y_top - i * step
        b = Rectangle(width=max(v * unit, 0.04), height=h, stroke_color=c, fill_color=c, fill_opacity=0.55)
        b.move_to([x0 + b.width / 2, y, 0])
        val = lab(txt, value_size, c, shows=(v,)).next_to(b, RIGHT, buff=0.15)
        nm = lab(name, name_size, name_color).next_to(b, UP, buff=0.1, aligned_edge=LEFT)
        out.append(VGroup(b, val, nm))
    return out


def time_axis(w=10.0, name="time", size=24):
    """A clock without numbers: an arrow to the right with a tick at its start, named under its right end.
    move_to centres the arrow. g.line, g.name. g.t(f): the point a fraction f (0..1) of the way along."""
    ln = Arrow(LEFT * w / 2, RIGHT * w / 2, buff=0, color=WHITE, stroke_width=3, max_tip_length_to_length_ratio=0.02)
    t0 = Line(LEFT * w / 2 + UP * 0.12, LEFT * w / 2 + DOWN * 0.12, color=WHITE, stroke_width=3)
    nm = lab(name, size).next_to(ln.get_right(), DOWN, buff=0.18).shift(LEFT * 0.7)
    g = VGroup(ln, t0, nm)
    g.line, g.name = ln, nm
    g.t = lambda f: t0.get_center() + RIGHT * f * (ln.width - 0.35)
    return g


def tick_at(axis, f, color=YELLOW, h=0.3):
    """One event on a time_axis(): a short upright line at fraction f, standing on the axis."""
    p = axis.t(f)
    return Line(p, p + UP * h, color=color, stroke_width=3)


def gauge(n0=0.0, n_max=3.0, unit=1.5, h=0.34, name="", color=YELLOW, size=24):
    """A quantity that rises or runs down (a budget, a dose, a count): a frame n_max units long (`unit` scene
    units each), a tick and number at every whole unit, a name above its left end, and a fill whose length is the
    tracker g.n: animate it with g.n.animate.set_value(1.4). move_to centres the frame and its numbers.
    g.frame, g.fill (redrawn from g.n), g.ticks, g.name."""
    frame = Rectangle(width=n_max * unit, height=h, stroke_color=WHITE, stroke_width=2)
    ticks = VGroup(*[Line(frame.get_corner(DL) + RIGHT * k * unit, frame.get_corner(DL) + RIGHT * k * unit + DOWN * 0.1,
                          color=WHITE, stroke_width=2) for k in range(int(n_max) + 1)])
    nums = VGroup(*[lab(str(k), size).next_to(ticks[k], DOWN, buff=0.06) for k in range(int(n_max) + 1)])
    nm = lab(name, size).next_to(frame, UP, buff=0.12).align_to(frame, LEFT) if name else VGroup()
    n = ValueTracker(n0)

    def _fill():
        wd = max(n.get_value(), 1e-3) / n_max * frame.width
        return Rectangle(width=wd, height=frame.height * 0.8, stroke_width=0, fill_color=color, fill_opacity=0.85).move_to(
            frame.get_left() + RIGHT * wd / 2)
    fill = always_redraw(_fill)
    g = VGroup(frame, fill, ticks, nums, nm)
    g.frame, g.fill, g.ticks, g.name, g.n = frame, fill, VGroup(ticks, nums), nm, n
    return g


def live(build, op=1.0, **params):
    """A figure rebuilt every frame from its own numbers. `build(**values)` returns a VGroup with the same parts each
    time (no Tex/Text: it runs every frame; keep labels outside). Each parameter becomes a ValueTracker hung on the
    figure, so the cue that changes it names the figure: fig.hx.animate.set_value(12); pass a ValueTracker to share one
    value between figures. A rebuild resets opacity, so FadeIn, set_opacity and Indicate on it are lost: fade and dim
    it with its own tracker fig.op (0 to 1, multiplies every part): live(build, op=0, ...) then
    fig.op.animate.set_value(1) fades it in. Dim one part with a parameter build reads. Never move_to it."""
    tr = {k: (v if isinstance(v, ValueTracker) else ValueTracker(v)) for k, v in params.items()}
    opt = op if isinstance(op, ValueTracker) else ValueTracker(op)

    def _make():
        m = build(**{k: t.get_value() for k, t in tr.items()})
        o = opt.get_value()
        if o < 1.0:
            for s in m.family_members_with_points():
                s.set_stroke(opacity=s.get_stroke_opacity() * o)
                s.set_fill(opacity=s.get_fill_opacity() * o)
        return m
    fig = _make()
    for k, t in tr.items():
        setattr(fig, k, t)
    fig.op = opt
    fig.add_updater(lambda m: m.become(_make()))
    return fig


# ---- detectors and optics ---------------------------------------------------------------------------------------


def sipm_grid(n=8, size=2.4, color=WHITE, fill="#3a3f48"):
    """An n x n photodetector array seen face on. g[k] is the tile with index k, row by row from the top left
    (the usual channel order). Light one with g[k].set_fill(color, opacity=...). move_to centres the array."""
    c = size / n
    return VGroup(*[Square(side_length=c * 0.88, stroke_color=color, stroke_width=1.2, fill_color=fill, fill_opacity=1)
                    .move_to(RIGHT * (k % n - (n - 1) / 2) * c + UP * ((n - 1) / 2 - k // n) * c) for k in range(n * n)])


def slab_side(w=9.0, mm=(50.0, 10.0), n_tiles=8, crystal_color=BLUE_L, coupling_color="#c9b458",
              window_color="#9aa3ad", wrap_color="#d8d8d8", tile_fill="#3a3f48", wrap=True):
    """A scintillator slab seen from the side, schematic: the crystal (mm = width, thickness) with the entrance
    face on top, a wrap on the top and both sides, and under it the coupling layer, the window and a row of
    n_tiles photodetector tiles (layer thicknesses not to scale). move_to moves it all.
    g.crystal, g.coupling, g.window, g.tiles, g.wrap. g.pt(x_mm, z_mm): the point x mm from the centre line and
    z mm below the entrance face, read from the crystal as it is now."""
    h = w * mm[1] / mm[0]
    crystal = Rectangle(width=w, height=h, stroke_color=crystal_color, stroke_width=3, fill_color=crystal_color, fill_opacity=0.16)
    t_g, t_p, t_s = 0.07 * h + 0.03, 0.16 * h + 0.03, 0.2 * h + 0.03
    coupling = Rectangle(width=w, height=t_g, stroke_width=0, fill_color=coupling_color, fill_opacity=0.7).next_to(crystal, DOWN, buff=0)
    window = Rectangle(width=w, height=t_p, stroke_color=window_color, stroke_width=1.5, fill_color=window_color,
                       fill_opacity=0.22).next_to(coupling, DOWN, buff=0)
    tw = w / n_tiles
    tiles = VGroup(*[Rectangle(width=tw * 0.86, height=t_s, stroke_color=WHITE, stroke_width=1.5, fill_color=tile_fill,
                               fill_opacity=1).move_to(window.get_bottom() + DOWN * t_s / 2 + RIGHT * (k - (n_tiles - 1) / 2) * tw)
                     for k in range(n_tiles)])
    wr = VGroup()
    if wrap:
        off = 0.07
        ul, ur = crystal.get_corner(UL), crystal.get_corner(UR)
        dl, dr = crystal.get_corner(DL), crystal.get_corner(DR)
        wr = VGroup(Line(ul + UP * off + LEFT * off, ur + UP * off + RIGHT * off),
                    Line(ul + UP * off + LEFT * off, dl + LEFT * off),
                    Line(ur + UP * off + RIGHT * off, dr + RIGHT * off)).set_stroke(wrap_color, 4)
    g = VGroup(crystal, coupling, window, tiles, wr)
    g.crystal, g.coupling, g.window, g.tiles, g.wrap = crystal, coupling, window, tiles, wr
    g.pt = lambda x, z: crystal.get_corner(UL) + RIGHT * (x + mm[0] / 2) / mm[0] * crystal.width + DOWN * z / mm[1] * crystal.height
    return g


def snell(ratio=1.25, w=9.0, hh=2.4, R=2.0, theta=0.45, ray_color=PURPLE_L, top_color=BLUE_L, bot_color="#c9b458",
          normal_color=GREY_B):
    """A ray meeting a flat interface, driven by the tracker g.th (the angle of incidence from the normal, in
    radians): the medium it leaves on top, the one it enters below, the surface, the normal, the incoming ray, the
    refracted ray (Snell's law; hidden once sin(theta2) >= 1) and the reflected ray, whose brightness is the
    Fresnel reflection probability (unpolarised). `ratio` is n1 / n2; if the source gives no indices, the ratio is
    the drawing's assumption and the scene says schematic.
    g.top, g.bot, g.line, g.normal, g.inc, g.refl, g.refr, g.arc1, g.arc2, g.dot, g.th. g.O(): the crossing point.
    g.crit: the critical angle (None if ratio <= 1). g.T(): the transmission probability now. Nothing is added
    for you: bring the parts on as the voice names them."""
    top = Rectangle(width=w, height=hh, stroke_width=0, fill_color=top_color, fill_opacity=0.16).move_to(UP * hh / 2)
    bot = Rectangle(width=w, height=hh, stroke_width=0, fill_color=bot_color, fill_opacity=0.14).move_to(DOWN * hh / 2)
    line = Line(LEFT * w / 2, RIGHT * w / 2, color=WHITE, stroke_width=3)
    th = ValueTracker(theta)
    O = lambda: line.get_center()
    k = lambda: line.width / w * R

    def _s2():
        return ratio * np.sin(th.get_value())

    def _T():
        s2 = _s2()
        if s2 >= 1:
            return 0.0
        c1, c2 = np.cos(th.get_value()), np.sqrt(1 - s2 * s2)
        rs = (ratio * c1 - c2) / (ratio * c1 + c2)
        rp = (ratio * c2 - c1) / (ratio * c2 + c1)
        return 1 - (rs * rs + rp * rp) / 2

    def _inc():
        a = th.get_value()
        return Line(O() + k() * (LEFT * np.sin(a) + UP * np.cos(a)), O(), color=ray_color, stroke_width=4)

    def _refl():
        a = th.get_value()
        return Line(O(), O() + k() * (RIGHT * np.sin(a) + UP * np.cos(a)), color=ray_color, stroke_width=4).set_stroke(
            opacity=max(0.3, 1 - _T()))

    def _refr():
        s2 = min(_s2(), 0.9999)
        c2 = np.sqrt(1 - s2 * s2)
        return Line(O(), O() + k() * (RIGHT * s2 + DOWN * c2), color=ray_color, stroke_width=4).set_stroke(
            opacity=0.0 if _s2() >= 1 else max(0.3, _T()))

    def _arc1():
        return Arc(radius=0.3 * k(), start_angle=PI / 2, angle=max(th.get_value(), 0.02), arc_center=O(), color=WHITE,
                   stroke_width=2.5)

    def _arc2():
        s2 = min(_s2(), 0.9999)
        return Arc(radius=0.3 * k(), start_angle=-PI / 2, angle=max(np.arcsin(s2), 0.02), arc_center=O(), color=WHITE,
                   stroke_width=2.5).set_stroke(opacity=0.0 if _s2() >= 1 else 1.0)

    normal = DashedLine(UP * R * 0.95, DOWN * R * 0.95, color=normal_color, stroke_width=2.5)
    inc, refl, refr = always_redraw(_inc), always_redraw(_refl), always_redraw(_refr)
    arc1, arc2 = always_redraw(_arc1), always_redraw(_arc2)
    dot = Dot(radius=0.08, color=ray_color).set_z_index(5)
    g = VGroup(top, bot, line, normal, inc, refl, refr, arc1, arc2, dot)
    g.top, g.bot, g.line, g.normal, g.inc, g.refl, g.refr, g.arc1, g.arc2, g.dot = top, bot, line, normal, inc, refl, refr, arc1, arc2, dot
    g.th, g.O, g.T = th, O, _T
    g.crit = float(np.arcsin(1 / ratio)) if ratio > 1 else None
    return g
