"""Runtime rules: called by the Monitor inside a rendering scene. Each gets (monitor, event, payload) and yields
(key, message); a key is reported once per scene. Events: "play" (after each play, payload anims), "vo_open"
(text), "cue" (mark), "vo_close", "end". They read the real mobjects, so they catch what the script can't show:
where things ended up and whether they can be seen."""
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
    return m.get_left()[0], m.get_bottom()[1], m.get_right()[0], m.get_top()[1]


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
        if isinstance(a, M.AnimationGroup):
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
            if any(x0 < q[0] < x1 and y0 < q[1] < y1 for q in samp):
                yield (id(a), id(m)), f"an arrow runs through {label(m)}"


def _chain_nodes(scene):
    """Visible arrows, and the boxes/labels at their ends: (arrows, nodes) where a node is (bbox, text_only)."""
    arrows, texts, rects, other = [], [], [], []
    text_ids = set()
    for m, ok in walk(scene.mobjects):
        if "text-chain" in ok or "*" in ok:
            continue
        if isinstance(m, TEXTS()):
            text_ids |= {id(x) for x in m.get_family()}
            if m.family_members_with_points() and visibility(m) >= 0.05:
                texts.append(m)
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
