"""Runtime rules: called by the Monitor inside a rendering scene. Each gets (monitor, event, payload) and yields
(key, message); a key is reported once per scene. Events: "play" (after each play, payload anims), "vo_open"
(text), "cue" (mark), "vo_close", "end". They read the real mobjects, so they catch what the script can't show:
where things ended up and whether they can be seen."""
import re

from .core import opt, rule
from .runtime import walk
from .script import MARK


class _M:
    """manim, imported on first use, so the rule list loads (vlint rules, selftest) where manim is not installed."""
    def __getattr__(self, k):
        import manim
        if k == "AbstractImageMobject":
            from manim.mobject.types.image_mobject import AbstractImageMobject
            return AbstractImageMobject
        return getattr(manim, k)


M = _M()


def TEXTS():
    return (M.Text, M.MarkupText, M.SingleStringMathTex, M.MathTex, M.Paragraph)


def visibility(m):
    """Highest opacity anywhere in m's family (images: their alpha channel)."""
    best = 0.0
    for sm in m.get_family():
        if isinstance(sm, M.AbstractImageMobject):
            pa = getattr(sm, "pixel_array", None)
            if pa is not None and pa.ndim == 3 and pa.shape[2] == 4:
                best = max(best, pa[..., 3].max() / 255.0)
            else:
                best = max(best, 1.0)
        elif isinstance(sm, M.VMobject) and sm.has_points():
            best = max(best, float(max(sm.get_fill_opacities(), default=0)))
            if sm.get_stroke_width() > 0:
                best = max(best, float(max(sm.get_stroke_opacities(), default=0)))
    return best


def label(m):
    t = getattr(m, "tex_string", None) or getattr(m, "original_text", None) or getattr(m, "text", None)
    return repr(str(t)[:30]) if t else type(m).__name__


def leaves(scene, rule_id):
    """Visible text blocks and images on screen, not descending into a text block, skipping exempt ones."""
    out = []
    stack = [(m, frozenset(getattr(m, "_vlint_ok", ()))) for m in scene.mobjects]
    while stack:
        m, ok = stack.pop()
        if rule_id in ok or "*" in ok:
            continue
        if isinstance(m, TEXTS()) or isinstance(m, M.AbstractImageMobject):
            if m.family_members_with_points() if isinstance(m, M.VMobject) else True:
                out.append(m)
            continue
        stack += [(c, ok | frozenset(getattr(c, "_vlint_ok", ()))) for c in m.submobjects]
    return out


def bbox(m):
    import numpy as np
    pts = np.asarray(m.get_all_points(), dtype=float).reshape(-1, 3)    # one pass over the points, not four critical-point searches
    if len(pts) == 0:
        c = m.get_center()
        return c[0], c[1], c[0], c[1]
    lo, hi = pts.min(0), pts.max(0)
    return lo[0], lo[1], hi[0], hi[1]


def frame_box(scene):
    fr = getattr(scene.camera, "frame", None)
    if fr is not None:
        return bbox(fr)
    cam = scene.camera
    w, h = cam.frame_width, cam.frame_height
    c = getattr(cam, "frame_center", (0.0, 0.0, 0.0))
    return c[0] - w / 2, c[1] - h / 2, c[0] + w / 2, c[1] + h / 2


@rule("frame-clip", "runtime", "error", "A label or image ends a play partly outside the frame, so it is cut off.",
      "Part II, Layout (fit_frame)", "fit_frame(panel) after building it, or move the label in")
def frame_clip(mon, ev, p):
    if ev != "play" or isinstance(mon.scene, M.ThreeDScene):
        return
    tol = float(opt(mon, "clip_tolerance", 0.03))
    X0, Y0, X1, Y1 = frame_box(mon.scene)
    for m in leaves(mon.scene, "frame-clip"):
        if visibility(m) < 0.05:
            continue
        x0, y0, x1, y1 = bbox(m)
        inside = x1 > X0 and x0 < X1 and y1 > Y0 and y0 < Y1
        out = x0 < X0 - tol or x1 > X1 + tol or y0 < Y0 - tol or y1 > Y1 + tol
        if inside and out:
            yield id(m), f"{label(m)} is cut off by the frame edge (box x {x0:.2f}..{x1:.2f}, y {y0:.2f}..{y1:.2f})"


@rule("frame-margin", "runtime", "warn", "An equation or large label ends a play within a hair of the bottom or side "
      "edge. It fits here, but ManimGX's Typst sets maths a little larger than CE's LaTeX, so in the real render it "
      "can be cut off (liquid_tc Solver).", "Part II, Layout (fit_frame)",
      "keep ~0.3 from the edge: tighten the stack's buff, shrink it, or move it up")
def frame_margin(mon, ev, p):
    if ev != "play" or isinstance(mon.scene, M.ThreeDScene):
        return
    margin = float(opt(mon, "edge_margin", 0.2))
    tall = float(opt(mon, "edge_min_height", 0.35))          # footnotes and credits may sit near the edge
    X0, Y0, X1, Y1 = frame_box(mon.scene)
    for m in leaves(mon.scene, "frame-margin"):
        if not isinstance(m, TEXTS()) or visibility(m) < 0.05:
            continue
        x0, y0, x1, y1 = bbox(m)
        if y1 - y0 < tall or x1 < X0 or x0 > X1 or y1 < Y0 or y0 > Y1:
            continue
        gaps = {"bottom": y0 - Y0, "left": x0 - X0, "right": X1 - x1}
        side, g = min(gaps.items(), key=lambda kv: kv[1])
        if -0.03 <= g < margin:
            yield id(m), f"{label(m)} is {g:.2f} from the {side} edge (< {margin})"


@rule("text-overlap", "runtime", "warn", "Two visible labels overlap at the end of a play.",
      "Part II, Layout; Part IV (two labels on one edge)", "move one, align them to opposite ends, or remove the old one")
def text_overlap(mon, ev, p):
    if ev != "play" or isinstance(mon.scene, M.ThreeDScene):
        return
    frac = float(opt(mon, "overlap_fraction", 0.15))
    ts = [m for m in leaves(mon.scene, "text-overlap") if isinstance(m, TEXTS()) and visibility(m) >= 0.05]
    boxes = [bbox(m) for m in ts]
    for i in range(len(ts)):
        a = boxes[i]
        aa = (a[2] - a[0]) * (a[3] - a[1])
        for j in range(i + 1, len(ts)):
            b = boxes[j]
            iw, ih = min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])
            if iw <= 0 or ih <= 0:
                continue
            small = min(aa, (b[2] - b[0]) * (b[3] - b[1]))
            big = max(aa, (b[2] - b[0]) * (b[3] - b[1]))
            if label(ts[i]) == label(ts[j]) and iw * ih > 0.9 * big:
                continue                     # an exact duplicate stacked on itself reads as one label
            if small > 1e-4 and iw * ih > frac * small:
                key = tuple(sorted((id(ts[i]), id(ts[j]))))
                yield key, f"{label(ts[i])} overlaps {label(ts[j])} ({100 * iw * ih / small:.0f}% of the smaller)"


def _flatten(anims):
    for a in anims:
        # TransformMatchingShapes/Tex fade their unmatched pieces in, then swap in the target: one animation, not intros
        if type(a).__name__.startswith("TransformMatching"):
            yield a
        elif isinstance(a, M.AnimationGroup):
            yield from _flatten(a.animations)
        else:
            yield a


@rule("vanished-after-intro", "runtime", "error", "An animation that introduces a mobject (FadeIn, Create, Write...) "
      "finished and the mobject is invisible: usually another animation in the same play reset it.",
      "Part IV, Manim 0.19", "split the intro and the pulse into separate plays")
def vanished_after_intro(mon, ev, p):
    if ev != "play":
        return
    for a in _flatten(p.get("anims", ())):
        m = getattr(a, "mobject", None)
        intro = getattr(a, "is_introducer", lambda: False)()
        if m is None or not intro or getattr(a, "remover", False):
            continue
        if any("vanished-after-intro" in ok or "*" in ok for mm, ok in walk([m]) if mm is m):
            continue
        if m.get_family() and visibility(m) < 0.02:
            yield id(m), f"{type(a).__name__}({label(m)}) ended with the object invisible"


@rule("indicate-image", "runtime", "warn", "Indicate pulses an image: it recolours the whole picture (a flat yellow or "
      "white wash) instead of drawing the eye to it.", "Part IV, Manim 0.19",
      "pulse the image's frame (framed(...)[1]) or use Circumscribe")
def indicate_image(mon, ev, p):
    if ev != "play":
        return
    for a in _flatten(p.get("anims", ())):
        m = getattr(a, "mobject", None)
        if m is None or not isinstance(a, M.Indicate):
            continue
        if any(isinstance(sm, M.AbstractImageMobject) and not ("indicate-image" in ok or "*" in ok) for sm, ok in walk([m])):
            yield id(m), f"Indicate({label(m)}) pulses an image"


@rule("arrow-over-label", "runtime", "warn", "An arrow's shaft runs through a label or an image it doesn't point at, "
      "so the label is struck through.", "Part II, Layout", "end the arrow at the label's side, or route it around")
def arrow_over_label(mon, ev, p):
    if ev != "play" or isinstance(mon.scene, M.ThreeDScene):
        return
    import numpy as np
    skip = float(opt(mon, "arrow_end_clearance", 0.2))
    arrows = [m for m, ok in walk(mon.scene.mobjects) if isinstance(m, (M.Arrow, M.CurvedArrow, M.CurvedDoubleArrow))
              and not ("arrow-over-label" in ok or "*" in ok) and visibility(m) >= 0.05]
    if not arrows:
        return
    targets = [m for m in leaves(mon.scene, "arrow-over-label") if visibility(m) >= 0.05]
    for a in arrows:
        if len(a.get_points()) < 2:
            continue
        s, e = a.get_start(), a.get_end()
        shaft = [a.point_from_proportion(u) for u in np.linspace(0, 1, 60)]      # the tip is a submobject, not sampled
        samp = [q for q in shaft if np.linalg.norm(q - s) > skip and np.linalg.norm(q - e) > skip]
        for m in targets:
            x0, y0, x1, y1 = bbox(m)
            x0, y0, x1, y1 = x0 + 0.03, y0 + 0.03, x1 - 0.03, y1 - 0.03
            if isinstance(m, M.AbstractImageMobject) and any(x0 < q[0] < x1 and y0 < q[1] < y1 for q in (s, e)):
                continue                     # it points into this one (an arrow landing on an image)
            if any(x0 < q[0] < x1 and y0 < q[1] < y1 for q in (s, e)):
                yield (id(a), id(m)), f"an arrow ends inside {label(m)}"
                continue
            if any(x0 < q[0] < x1 and y0 < q[1] < y1 for q in samp):
                yield (id(a), id(m)), f"an arrow runs through {label(m)}"


def _strokes(scene, rule_id):
    """Visible drawn strokes (curves, lines, outlines) outside text and arrows, as leaf VMobjects."""
    out, stack = [], [(m, frozenset(getattr(m, "_vlint_ok", ()))) for m in scene.mobjects]
    while stack:
        m, ok = stack.pop()
        if rule_id in ok or "*" in ok or isinstance(m, TEXTS()) or isinstance(m, (M.Arrow, M.CurvedArrow, M.CurvedDoubleArrow, M.ArrowTip)):
            continue
        if isinstance(m, M.VMobject) and len(m.points) >= 4 and m.get_stroke_width() > 0 and max(m.get_stroke_opacities(), default=0) >= 0.05:
            out.append(m)
        stack += [(c, ok | frozenset(getattr(c, "_vlint_ok", ()))) for c in m.submobjects]
    return out


def _sample_curve(points, step=0.03):
    """Points along a VMobject's cubic pieces, about `step` apart (a long straight edge gets as many as it needs)."""
    import numpy as np
    pts = points[: len(points) // 4 * 4].reshape(-1, 4, 3)
    out = []
    for q in pts:
        n = max(4, int(np.ceil(np.linalg.norm(q[3] - q[0]) / step)) + 1)
        t = np.linspace(0, 1, n)[:, None]
        out.append(((1 - t) ** 3) * q[0] + 3 * ((1 - t) ** 2) * t * q[1] + 3 * (1 - t) * (t ** 2) * q[2] + (t ** 3) * q[3])
    return np.vstack(out) if out else np.zeros((0, 3))


def _inside(poly, P):
    """Even-odd point-in-polygon for many points P (k, 2) against a closed outline poly (n, 2)."""
    import numpy as np
    x, y = P[:, 0][:, None], P[:, 1][:, None]
    x0, y0 = poly[:, 0][None, :], poly[:, 1][None, :]
    x1, y1 = np.roll(poly[:, 0], -1)[None, :], np.roll(poly[:, 1], -1)[None, :]
    cross = ((y0 > y) != (y1 > y)) & (x < (x1 - x0) * (y - y0) / np.where(y1 == y0, 1e-12, y1 - y0) + x0)
    return cross.sum(axis=1) % 2 == 1


@rule("shape-overlap", "runtime", "warn", "Two filled shapes partly overlap: one runs into the other by accident "
      "(rows spaced closer than the shapes are tall). A shape mostly inside another is a layer and is left alone.",
      "Part II, Layout", "space the rows by the shapes' real extent, or shrink the shape")
def shape_overlap(mon, ev, p):
    if ev != "vo_close" or isinstance(mon.scene, M.ThreeDScene):
        return
    import numpy as np
    lo, hi = float(opt(mon, "overlap_min", 0.03)), float(opt(mon, "overlap_max", 0.6))
    shapes = []
    for m, ok in walk(mon.scene.mobjects):
        if "shape-overlap" in ok or "*" in ok or isinstance(m, TEXTS()) or not isinstance(m, M.VMobject) or len(m.points) < 4:
            continue
        if m.get_fill_opacity() < 0.05 or visibility(m) < 0.05:
            continue
        b = bbox(m)
        if (b[2] - b[0]) * (b[3] - b[1]) < 0.15:
            continue
        outline = _sample_curve(m.points, 0.05)[:, :2]
        shapes.append((m, b, outline))
    text_fam = {id(y) for t in mon.scene.mobjects for x in t.get_family() if isinstance(x, TEXTS()) for y in x.get_family()}
    shapes = [s_ for s_ in shapes if id(s_[0]) not in text_fam]
    for i in range(len(shapes)):
        for j in range(i + 1, len(shapes)):
            (a, ba, pa), (b, bb, pb) = shapes[i], shapes[j]
            x0, y0, x1, y1 = max(ba[0], bb[0]), max(ba[1], bb[1]), min(ba[2], bb[2]), min(ba[3], bb[3])
            if x1 <= x0 or y1 <= y0:
                continue
            if a in b.get_family() or b in a.get_family():
                continue
            g = np.stack(np.meshgrid(np.linspace(x0, x1, 40), np.linspace(y0, y1, 40)), -1).reshape(-1, 2)
            both = (_inside(pa, g) & _inside(pb, g)).sum() * (x1 - x0) * (y1 - y0) / len(g)
            area = lambda bx, pts: _inside(pts, np.stack(np.meshgrid(np.linspace(bx[0], bx[2], 40), np.linspace(bx[1], bx[3], 40)), -1).reshape(-1, 2)).mean() * (bx[2] - bx[0]) * (bx[3] - bx[1])
            small = min(area(ba, pa), area(bb, pb))
            if small > 1e-6 and lo < both / small < hi:
                yield (id(a), id(b)), (f"{type(a).__name__} at ({(ba[0] + ba[2]) / 2:+.1f}, {(ba[1] + ba[3]) / 2:+.1f}) and {type(b).__name__} at "
                                       f"({(bb[0] + bb[2]) / 2:+.1f}, {(bb[1] + bb[3]) / 2:+.1f}) overlap by {both / small:.0%} of the smaller")


@rule("line-over-label", "runtime", "warn", "A plotted curve, line or outline runs through a label: the text is struck "
      "through (a curve label set on top of its own curve).", "Part II, Layout",
      "set the label beside the line in empty space, e.g. next_to a data point on the open side")
def line_over_label(mon, ev, p):
    if ev != "play" or isinstance(mon.scene, M.ThreeDScene):
        return
    import numpy as np
    texts = [(m, bbox(m)) for m in leaves(mon.scene, "line-over-label") if isinstance(m, TEXTS()) and visibility(m) >= 0.05]
    if not texts:
        return
    for c in _strokes(mon.scene, "line-over-label"):
        cx0, cy0, cx1, cy1 = bbox(c)
        near = [(m, b) for m, b in texts if not (b[2] < cx0 or b[0] > cx1 or b[3] < cy0 or b[1] > cy1)]
        if not near:
            continue
        samp = _sample_curve(c.points)
        for m, (x0, y0, x1, y1) in near:
            x0, y0, x1, y1 = x0 + 0.04, y0 + 0.04, x1 - 0.04, y1 - 0.04
            hit = (samp[:, 0] > x0) & (samp[:, 0] < x1) & (samp[:, 1] > y0) & (samp[:, 1] < y1)
            if hit.sum() >= 2:
                yield (id(c), id(m)), f"a {type(c).__name__} runs through {label(m)}"


@rule("arrow-skew", "runtime", "warn", "A straight arrow is a few degrees off horizontal or vertical: it reads as a "
      "mistake, not a direction. Usually its ends sit on centres of groups whose labels shift them.",
      "Part II, Layout (align)", "line the ends up on the icons' centres (icon[0], not the labelled group)")
def arrow_skew(mon, ev, p):
    if ev != "play" or isinstance(mon.scene, M.ThreeDScene):
        return
    import math
    lo, hi = float(opt(mon, "skew_min_deg", 0.6)), float(opt(mon, "skew_max_deg", 12))
    for m, ok in walk(mon.scene.mobjects):
        if not isinstance(m, M.Arrow) or "arrow-skew" in ok or "*" in ok or visibility(m) < 0.05:
            continue
        s, e = m.get_start(), m.get_end()
        dx, dy = e[0] - s[0], e[1] - s[1]
        if math.hypot(dx, dy) < 0.3:
            continue
        a = math.degrees(math.atan2(abs(dy), abs(dx)))           # 0 = horizontal, 90 = vertical
        dev = min(a, 90 - a)
        if lo < dev < hi:
            yield id(m), f"arrow from ({s[0]:+.1f}, {s[1]:+.1f}) to ({e[0]:+.1f}, {e[1]:+.1f}) is {dev:.1f}° off " + ("horizontal" if a < 45 else "vertical")


@rule("title-margin", "runtime", "warn", "A title sits too close to the top edge: it crowds the nav chips and looks "
      "pushed off the screen.", "Part II, Layout (title)", "to_edge(UP, buff=0.8) or more")
def title_margin(mon, ev, p):
    if ev != "play" or isinstance(mon.scene, M.ThreeDScene):
        return
    gap = float(opt(mon, "title_gap", 0.75))
    Y1 = frame_box(mon.scene)[3]
    for m in mon.scene.mobjects:
        if not isinstance(m, TEXTS()) or "title-margin" in getattr(m, "_vlint_ok", ()) or visibility(m) < 0.05:
            continue
        b = bbox(m)
        if b[3] - b[1] >= 0.2 and b[2] - b[0] >= 2.0 and Y1 - b[3] < gap - 0.01:
            yield id(m), f"title {label(m)!r} top is {Y1 - b[3]:.2f} below the frame edge (< {gap})"


@rule("redraw-jitter", "runtime", "warn", "A curve redrawn from a ValueTracker wobbles up and down while the tracker "
      "moves steadily: it flickers. Usually the function is sampled on a grid that moves with the parameter (a peak "
      "crossing grid points, a renormalisation by a sampled maximum).", "Part II, Motion",
      "make the function smooth in the parameter: integrate singular parts over grid cells, sample on a fixed grid")
def redraw_jitter(mon, ev, p):
    if ev != "play" or not p.get("trackers"):
        return
    import numpy as np
    n, frac = int(opt(mon, "jitter_steps", 40)), float(opt(mon, "jitter_share", 0.25))
    curves = [m for m, ok in walk(mon.scene.mobjects) if m.updaters and isinstance(m, M.VMobject) and len(m.points) >= 16
              and not ("redraw-jitter" in ok or "*" in ok) and visibility(m) >= 0.05]
    if not curves:
        return
    for vt, v0 in p["trackers"]:
        v1 = vt.get_value()
        if abs(v1 - v0) < 1e-9:
            continue
        P = {id(c): [] for c in curves}
        try:
            for t in np.linspace(0, 1, n):
                vt.set_value(v0 + (v1 - v0) * t)
                for c in curves:
                    c.update(0)
                    P[id(c)].append(c.points[:, :2].copy())
        finally:
            vt.set_value(v1)
            for c in curves:
                c.update(0)
        for c in curves:
            fr = P[id(c)]
            if any(len(f) < 16 or np.any(np.diff(f[:, 0]) < -1e-9) for f in fr):
                continue                     # only curves that are functions of x
            lo, hi = max(f[0, 0] for f in fr), min(f[-1, 0] for f in fr)
            if hi - lo < 0.5:
                continue
            xs = np.linspace(lo, hi, 60)
            Y = np.array([np.interp(xs, f[:, 0], f[:, 1]) for f in fr])          # (steps, 60): height at fixed x over time
            d = np.diff(Y, axis=0)
            span = max(np.ptp(Y), 1e-6)
            sig = np.where(np.abs(d) > 2e-3 * span, np.sign(d), 0)
            rev = []
            for k in range(sig.shape[1]):
                s_ = sig[:, k][sig[:, k] != 0]
                rev.append(int(np.sum(s_[1:] != s_[:-1])))
            share = np.mean(np.array(rev) >= 4)
            if share > frac:
                yield id(c), (f"a redrawn curve wobbles while a ValueTracker goes {v0:.3g} -> {v1:.3g}: at {share:.0%} of x "
                              f"positions its height reverses direction 4+ times")


@rule("title-gap", "runtime", "warn", "A shape, image or diagram comes up to the title's baseline: the title has "
      "no air below it (often after the title was lowered and the content was not).", "Part II, Layout (title)",
      "move the content down, or start it lower; keep ~0.2 below the title")
def title_gap(mon, ev, p):
    if ev != "play" or isinstance(mon.scene, M.ThreeDScene):
        return
    gap_min = float(opt(mon, "title_gap_below", 0.18))
    Y1 = frame_box(mon.scene)[3]
    tops = [m for m in mon.scene.mobjects if isinstance(m, TEXTS()) and visibility(m) >= 0.05]
    titles = [(m, bbox(m)) for m in tops if bbox(m)[2] - bbox(m)[0] >= 2.0 and bbox(m)[3] - bbox(m)[1] >= 0.2 and Y1 - bbox(m)[3] < 1.3]
    if not titles:
        return
    for t, tb in titles:
        tcy = (tb[1] + tb[3]) / 2
        for m in mon.scene.mobjects:
            if m is t or isinstance(m, TEXTS()) or "title-gap" in getattr(m, "_vlint_ok", ()) or visibility(m) < 0.05:
                continue
            fam = m.family_members_with_points() if isinstance(m, M.VMobject) else [m]
            inside = {id(y) for x in m.get_family() if isinstance(x, TEXTS()) for y in x.get_family()}
            shapes = [x for x in fam if id(x) not in inside]
            if not shapes:
                continue                     # a text-only group (a subtitle) may sit close
            for x in shapes:
                b = bbox(x)
                if (b[1] + b[3]) / 2 >= tcy or b[2] < tb[0] - 0.3 or b[0] > tb[2] + 0.3:
                    continue                 # above the title's middle (the nav), or beside it
                if tb[1] - b[3] < gap_min:
                    yield (id(t), id(m)), f"{type(x).__name__} top at {b[3]:+.2f} is {tb[1] - b[3]:.2f} below the title {label(t)} (< {gap_min})"
                    break


def _holds(outer, inner, tol=0.15):
    """Whether bbox outer contains the centre of bbox inner, with most of it inside (tol: slack at the edges)."""
    cx, cy = (inner[0] + inner[2]) / 2, (inner[1] + inner[3]) / 2
    return outer[0] - tol <= cx <= outer[2] + tol and outer[1] - tol <= cy <= outer[3] + tol and outer != inner


def _content(mon, rule_id):
    """Visible top-level items below the title band, as (mobject, bbox); arrows, lines and tiny labels left out."""
    top = float(opt(mon, "title_band", 2.75))
    out = []
    for m in mon.scene.mobjects:
        if rule_id in getattr(m, "_vlint_ok", ()) or not m.get_family() or visibility(m) < 0.05:
            continue
        if isinstance(m, (M.Line, M.Arrow, M.CurvedArrow, M.DashedLine, M.DashedVMobject)) and not isinstance(m, M.NumberLine):
            continue                         # a number line is a chart axis, it is content
        fam = m.family_members_with_points()
        if all(isinstance(x, (M.Line, M.ArrowTip)) for x in fam) and any(isinstance(x, (M.Arrow, M.ArrowTip)) for x in fam):
            continue                         # an arrow routed as several segments
        b = bbox(m)
        if b[2] - b[0] < 1e-3 and b[3] - b[1] < 1e-3:
            continue
        if (b[1] + b[3]) / 2 > top:
            continue
        if isinstance(m, TEXTS()) and b[3] - b[1] < 0.22:
            continue                         # footnotes and captions in a corner don't make a layout
        out.append((m, b))
    return out


def _usable(mon):
    X0, Y0, X1, Y1 = frame_box(mon.scene)
    return X0, Y0, X1, min(Y1, float(opt(mon, "title_band", 2.75)))


@rule("layout-crowded", "runtime", "warn", "Two panels (images, plots, diagrams) sit almost touching while a large "
      "part of the screen stays empty: the content is cramped instead of spread out.", "Part II, Layout (use the space)",
      "spread the panels over the free space; keep at least ~0.3 units between panels")
def layout_crowded(mon, ev, p):
    if ev != "vo_close" or isinstance(mon.scene, M.ThreeDScene):
        return
    gap_min, area_min = float(opt(mon, "panel_gap", 0.25)), float(opt(mon, "panel_area", 0.6))
    items = _content(mon, "layout-crowded")
    if not items:
        return
    X0, Y0, X1, Y1 = _usable(mon)
    u = [min(b[0] for _, b in items), min(b[1] for _, b in items), max(b[2] for _, b in items), max(b[3] for _, b in items)]
    free_w, free_h = 1 - (u[2] - u[0]) / (X1 - X0), 1 - (u[3] - u[1]) / (Y1 - Y0)
    if max(free_w, free_h) < float(opt(mon, "free_fraction", 0.2)):
        return
    def wordy(m):                            # a text, or a group of nothing but texts (captions under a row of panels)
        fam = m.family_members_with_points()
        if isinstance(m, TEXTS()):
            return True
        inside = {id(y) for t in m.get_family() if isinstance(t, TEXTS()) for y in t.get_family()}
        return bool(fam) and all(id(x) in inside for x in fam)
    big = [(m, b) for m, b in items if (b[2] - b[0]) * (b[3] - b[1]) >= area_min and not wordy(m)]
    for i in range(len(big)):
        for j in range(i + 1, len(big)):
            a, b = big[i][1], big[j][1]
            dx = max(a[0] - b[2], b[0] - a[2])
            dy = max(a[1] - b[3], b[1] - a[3])
            if dx < 0 and dy < 0:
                continue                     # overlapping or nested: a layer on purpose, or text-overlap's business
            if any(c is not big[i][0] and c is not big[j][0] and _holds(cb, a) and _holds(cb, b) for c, cb in items):
                continue                     # two marks inside one chart or frame: parts of it, not panels
            gap = max(dx, dy)
            if gap < gap_min:
                where = lambda b_: f"({(b_[0] + b_[2]) / 2:+.1f}, {(b_[1] + b_[3]) / 2:+.1f})"
                yield (id(big[i][0]), id(big[j][0])), (f"{label(big[i][0])} at {where(a)} and {label(big[j][0])} at {where(b)} are {gap:.2f} apart while "
                                                       f"{100 * max(free_w, free_h):.0f}% of the {'width' if free_w >= free_h else 'height'} is empty")


@rule("layout-balance", "runtime", "warn", "At the end of a narration block the content sits well off the centre of "
      "the screen, leaving one side empty.", "Part II, Layout (use the space)", "re-centre the layout or fill the empty side")
def layout_balance(mon, ev, p):
    if ev != "vo_close" or isinstance(mon.scene, M.ThreeDScene):
        return
    items = _content(mon, "layout-balance")
    if not items:
        return
    X0, Y0, X1, Y1 = _usable(mon)
    u = [min(b[0] for _, b in items), min(b[1] for _, b in items), max(b[2] for _, b in items), max(b[3] for _, b in items)]
    cx, cy = (u[0] + u[2]) / 2 - (X0 + X1) / 2, (u[1] + u[3]) / 2 - (Y0 + Y1) / 2
    tx, ty = float(opt(mon, "balance_x", 1.0)), float(opt(mon, "balance_y", 0.8))
    if abs(cx) > tx or abs(cy) > ty:
        side = ("left" if cx > 0 else "right") if abs(cx) > tx else ("bottom" if cy > 0 else "top")
        yield ("balance", mon.time()), f"content centre is off by ({cx:+.1f}, {cy:+.1f}); the {side} is empty"


def _chain_nodes(scene):
    """Visible arrows, and the boxes/labels at their ends: (arrows, nodes) where a node is (bbox, text_only)."""
    arrows, texts, rects, other = [], [], [], []
    text_ids = set()
    for m, ok in walk(scene.mobjects):
        if "text-chain" in ok or "*" in ok:
            continue
        if isinstance(m, TEXTS()):
            text_ids |= {id(x) for x in m.get_family()}
            raw = str(getattr(m, "tex_string", None) or getattr(m, "original_text", None) or getattr(m, "text", "") or "")
            word = re.sub(r"\\[a-zA-Z]+|[^a-zA-Z0-9]", "", raw)
            if m.family_members_with_points() and visibility(m) >= 0.05 and len(word) >= 2:
                texts.append(m)              # a lone symbol (+, -, E) is part of a drawing, not a word
        elif isinstance(m, (M.Arrow, M.CurvedArrow, M.CurvedDoubleArrow)):
            if visibility(m) >= 0.05:
                arrows.append(m)
    arrow_ids = {id(x) for a in arrows for x in a.get_family()}
    for m, ok in walk(scene.mobjects):
        if id(m) in text_ids or id(m) in arrow_ids or "text-chain" in ok or "*" in ok:
            continue
        if isinstance(m, M.AbstractImageMobject):
            other.append(m)
        elif isinstance(m, M.VMobject) and m.has_points() and visibility(m) >= 0.05:
            (rects if isinstance(m, M.Rectangle) else other).append(m)
    return arrows, texts, rects, other


@rule("text-chain", "runtime", "warn", "Three or more text-only boxes joined by arrows: words pointing at words. "
      "Each node should carry a picture of the thing (an image, a network, a detector), with the word as its label.",
      "Part I §1, draw, don't write", "replace each box with an icon or image plus a one-word label")
def text_chain(mon, ev, p):
    if ev != "play" or isinstance(mon.scene, M.ThreeDScene):
        return
    need = int(opt(mon, "min_text_chain", 3))
    arrows, texts, rects, other = _chain_nodes(mon.scene)
    if len(arrows) < need - 1:
        return
    tol = 0.25

    def near(b, q):
        return b[0] - tol <= q[0] <= b[2] + tol and b[1] - tol <= q[1] <= b[3] + tol

    def inside(b, m):
        c = m.get_center()
        return b[0] <= c[0] <= b[2] and b[1] <= c[1] <= b[3]

    def node(q):
        """The smallest box (or bare label) at point q, and whether it holds only words."""
        cands = [bbox(r) for r in rects if near(bbox(r), q)]
        cands = [b for b in cands if (b[2] - b[0]) * (b[3] - b[1]) < 6]
        if cands:
            b = min(cands, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
        else:
            ts = [bbox(t) for t in texts if near(bbox(t), q)]
            if not ts:
                return None
            b = ts[0]
        has_text = any(inside(b, t) for t in texts)
        drawn = any(inside(b, o) for o in other) or sum(inside(b, r) and bbox(r) != b for r in rects) > 0
        return (tuple(round(x, 2) for x in b), has_text and not drawn)

    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            x = parent[x]
        return x
    for a in arrows:
        n0, n1 = node(a.get_start()), node(a.get_end())
        if n0 and n1 and n0[1] and n1[1] and n0[0] != n1[0]:
            parent[find(n0[0])] = find(n1[0])
    groups = {}
    for x in list(parent):
        groups.setdefault(find(x), set()).add(x)
    big = max((len(g) for g in groups.values()), default=0)
    if big >= need:
        yield "chain", f"{big} text-only boxes joined by arrows (words pointing at words)"


@rule("bookmark-unfired", "runtime", "error", "A bookmark was never waited for, or a cue named a bookmark the "
      "narration lacks; the picture and the words drift apart.", "Part II, Sync",
      "cue every bookmark once with self.at, in narration order")
def bookmark_unfired(mon, ev, p):
    st = mon.state
    if ev == "vo_open":
        st["marks"], st["hit"] = MARK.findall(p.get("text") or ""), []
    elif ev == "cue" and "marks" in st:
        if p["mark"] not in st["marks"]:
            yield ("unknown", p["mark"], mon.time()), f"cue '{p['mark']}' is not a bookmark of the current narration"
        st["hit"].append(p["mark"])
    elif ev == "vo_close" and "marks" in st:
        missed = [m for m in st["marks"] if m not in st["hit"]]
        if missed:
            yield ("missed", tuple(missed), mon.time()), f"bookmark(s) never waited for: {', '.join(missed)}"
        st.pop("marks")


def _lum(rgb):
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


@rule("faint-mark", "runtime", "warn", "A small filled mark (a dot, a marker) with no outline is so close to the "
      "background once its opacity is applied that it can hardly be seen (guitar's faint scale dots).",
      "Part II, Colour", "raise its fill_opacity, brighten its colour, or give it an outline")
def faint_mark(mon, ev, p):
    if ev != "play":
        return
    import numpy as np
    size = float(opt(mon, "mark_size", 0.5))
    need = float(opt(mon, "mark_contrast", 1.5))
    bg = np.asarray(M.ManimColor(getattr(mon.scene.camera, "background_color", None) or M.config.background_color).to_rgb())
    def rgb(m):
        return np.asarray(M.ManimColor(m.get_fill_color()).to_rgb())

    T, VM = TEXTS(), M.VMobject
    seen = mon.state.setdefault("faint-mark", {})     # id -> (colour, opacity) last judged: unchanged marks are skipped
    drawn = []                                  # (mobject, exempt) in drawing order, text left out
    def collect(ms, ok):
        for m in ms:
            here = ok | frozenset(getattr(m, "_vlint_ok", ()))
            if isinstance(m, T):
                continue
            if isinstance(m, VM) and m.has_points():
                drawn.append((m, here))
            collect(m.submobjects, here)
    collect(mon.scene.mobjects, frozenset())
    # possible backdrops, boxed once per play (a box per mark per shape cost calib's FanScan 14 min)
    backs = []
    for i, (b, _) in enumerate(drawn):
        ba = float(b.get_fill_opacity())
        if ba >= 0.3 and not isinstance(b, M.ArrowTip):          # a dot on an arrow's own tip is not hidden
            bx = bbox(b)
            backs.append((i, bx, (bx[2] - bx[0]) * (bx[3] - bx[1]), ba, b))
    for i, (m, ok) in enumerate(drawn):
        # round marks only: colour-bar and heatmap cells fade into the background on purpose
        if "faint-mark" in ok or "*" in ok or not isinstance(m, M.Circle):
            continue
        fr = getattr(m, "fill_rgbas", None)
        state = fr.tobytes() if fr is not None else None
        if state is not None and seen.get(id(m)) == state:
            continue
        seen[id(m)] = state
        a = float(m.get_fill_opacity())
        # below half opacity a mark is a ghost, dimmed so it recedes
        if a < 0.5 or (m.get_stroke_width() > 0 and float(m.get_stroke_opacity()) >= 0.05):
            continue
        x0, y0, x1, y1 = bbox(m)
        if max(x1 - x0, y1 - y0) > size:
            continue
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        under, what = bg, "the background"
        for j, (bx0, by0, bx1, by1), area, ba, b in reversed(backs):   # the topmost filled shape drawn under the mark
            if j >= i:
                continue
            if bx0 <= cx <= bx1 and by0 <= cy <= by1 and area > 4 * (x1 - x0) * (y1 - y0):
                under, what = ba * rgb(b) + (1 - ba) * bg, f"the {type(b).__name__} under it"
                break
        r = _contrast(a * rgb(m) + (1 - a) * under, under)
        if r < need:
            yield id(m), f"{type(m).__name__} at ({cx:.2f}, {cy:.2f}) has contrast {r:.2f} against {what}"
