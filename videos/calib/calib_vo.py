"""Explainer: how a PET detector is calibrated, pixelated versus monolithic and semi-monolithic, with the tricks
the literature uses to make monolithic calibration practical.

Sources: Casey & Nutt 1986 (block detector, LED gain equalisation, ratio thresholds);
Maas et al 2009 (k-NN on pencil-beam reference data); Borghi et al 2016 (fan-beam/flood calibration, quantile
pre-estimation, accelerated k-NN, per-voxel timing PDFs; CC BY 3.0, Figs 7 and 9 reused); Cucarella et al 2026
(one MLP for 28 modules, E/Imax DOI from a flood fit, three-step energy equalisation; CC BY 4.0); Freire et al
2026 (DeepBreast rotating fan beam, normalisation phantom; CC BY 4.0, Figs 4 and 5a reused).
The flood map, crystal lookup table, energy peaks, timing offsets, normalisation, k-NN and quantile-DOI panels are
computed here from simple stated models and are illustrative.
Visuals are cued to the narration with <bookmark/> tags and self.at() (see docs/DESIGN.md).
Render with render.sh, or one scene: manim -ql calib_vo.py Flood
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import *  # noqa: E402,F401

HERE = Path(__file__).resolve().parent
XTAL_C, PMT_C, SIPM_C, LIGHT_C, BAD_C, GOOD_C = "#9fd3ff", GREY_D, BLUE_L, "#f5d76e", "#ff5c5c", "#7ee081"
PIX_C, MONO_C, SEMI_C = ORANGE_L, TEAL_L, PURPLE_L
C_B16 = r"Borghi et al., Phys.\ Med.\ Biol.\ 2016 (CC BY 3.0)"
C_F26 = r"Freire et al., EJNMMI Phys.\ 2026 (CC BY 4.0)"

_CM = np.array([[0, 0, 4], [40, 11, 84], [101, 21, 110], [159, 42, 99], [212, 72, 66], [245, 125, 21], [250, 193, 39],
                [252, 255, 164]]) / 255.0


def cmap(v):
    v = np.clip(v, 0, 1) * (len(_CM) - 1)
    i = np.minimum(v.astype(int), len(_CM) - 2)
    f = (v - i)[..., None]
    return _CM[i] * (1 - f) + _CM[i + 1] * f


def heat(a, width, gamma=0.5):
    rgb = cmap((a / a.max()) ** gamma)
    rgba = np.concatenate([rgb, np.ones(rgb.shape[:-1] + (1,))], -1)
    im = ImageMobject((rgba * 255).astype(np.uint8))
    im.set_resampling_algorithm(RESAMPLING_ALGORITHMS["nearest"])
    return im.set_width(width)


def card(path, h):
    im = ImageMobject(str(HERE / "assets" / path)).set_height(h)
    bg = RoundedRectangle(corner_radius=0.08, width=im.width + 0.2, height=im.height + 0.2, fill_color=WHITE, fill_opacity=1,
                          stroke_width=0)
    return Group(bg.move_to(im), im)


def img_pt(im, fx, fy):
    return im.get_corner(UL) + np.array([fx * im.width, -fy * im.height, 0])


def img_box(im, fx0, fy0, fx1, fy1, color=YELLOW):
    a, b = img_pt(im, fx0, fy0), img_pt(im, fx1, fy1)
    return Rectangle(width=b[0] - a[0], height=a[1] - b[1], color=color, stroke_width=4).move_to((a + b) / 2)


def credit(text):
    return Tex(text, font_size=18, color=GREY_B).to_corner(DR, buff=0.15)


def icon_net(w=0.9, h=0.6, color=MONO_C):
    cols = [np.linspace(-h / 2, h / 2, k) for k in (3, 4, 2)]
    xs = np.linspace(-w / 2, w / 2, 3)
    nodes = [[np.array([x, y, 0]) for y in ys] for x, ys in zip(xs, cols)]
    edges = VGroup(*[Line(a, b, color=color, stroke_width=1, stroke_opacity=0.6) for L, R in zip(nodes[:-1], nodes[1:]) for a in L for b in R])
    return VGroup(edges, VGroup(*[Dot(p, radius=0.045, color=color) for col in nodes for p in col]))


def icon_flood(s=0.6):
    """An uncollimated source irradiating a crystal: a dot with rays spreading everywhere."""
    rays = VGroup(*[Line(ORIGIN, 0.5 * s * np.array([np.cos(a), np.sin(a), 0]), color=GOOD_C, stroke_width=2) for a in np.linspace(-2.6, -0.5, 6)])
    return VGroup(rays, Dot(ORIGIN, radius=0.06, color=YELLOW))


def icon_beam(s=0.6):
    """A collimated beam: a source between two blocks of tungsten, one narrow ray out."""
    blocks = VGroup(Rectangle(width=0.18 * s / 0.6, height=0.32 * s / 0.6, fill_color=GREY_C, fill_opacity=1, stroke_width=0).shift(LEFT * 0.13),
                    Rectangle(width=0.18 * s / 0.6, height=0.32 * s / 0.6, fill_color=GREY_C, fill_opacity=1, stroke_width=0).shift(RIGHT * 0.13))
    return VGroup(blocks, Line(ORIGIN, DOWN * 0.5 * s, color=GOOD_C, stroke_width=3), Dot(UP * 0.02, radius=0.05, color=YELLOW))


def tile(icon, text, w=2.6, fs=24):
    icon = icon.copy().scale_to_fit_height(min(icon.height, 0.55))
    g = VGroup(icon, Tex(text, font_size=fs)).arrange(RIGHT, buff=0.22)
    box = RoundedRectangle(corner_radius=0.1, width=max(w, g.width + 0.35), height=0.8, stroke_color=GREY_D, stroke_width=1.5)
    return VGroup(box, g.move_to(box))


# ---- computed models -----------------------------------------------------------------------------------------
def block_flood(n=8, events=60000, photons=500, k=1.7, seed=1, return_ij=False):
    """Anger positions of an n x n crystal block on four PMTs. The light guide is modelled as a compressive map
    tanh(k u)/tanh(k) of each crystal's centre (edge crystals bunch up), and Poisson light statistics blur each spot."""
    rng = np.random.default_rng(seed)
    c = (np.arange(n) + 0.5) / n * 2 - 1
    comp = np.tanh(k * c) / np.tanh(k)
    ij = rng.integers(0, n, size=(events, 2))
    u, v = comp[ij[:, 0]], comp[ij[:, 1]]
    w = np.stack([(1 - u) * (1 - v), (1 + u) * (1 - v), (1 - u) * (1 + v), (1 + u) * (1 + v)], 1) / 4
    q = rng.poisson(w * photons)
    tot = q.sum(1) + 1e-9
    x = (q[:, 1] + q[:, 3] - q[:, 0] - q[:, 2]) / tot
    y = (q[:, 2] + q[:, 3] - q[:, 0] - q[:, 1]) / tot
    return (x, y, comp, ij) if return_ij else (x, y, comp)


def hist2d(x, y, bins=128, lim=1.05):
    h, _, _ = np.histogram2d(y, x, bins=bins, range=[[-lim, lim], [-lim, lim]])
    return h[::-1]


def mono_light(px, py, h, pitch=4.0, n=8):
    """Light on an n x n pixel array (pitch mm) from a point at (px, py) a height h above it: solid-angle kernel."""
    c = (np.arange(n) - (n - 1) / 2) * pitch
    gx, gy = np.meshgrid(c, c)
    r2 = (gx - px) ** 2 + (gy - py) ** 2 + h * h
    return h / r2 ** 1.5


def knn_library(seed=2, pitch=2.0, per=8, photons=1500, h=8.0):
    rng = np.random.default_rng(seed)
    pos = np.arange(-15, 15.01, pitch)
    refs, lab = [], []
    for x in pos:
        for y in pos:
            m = mono_light(x, y, h).ravel()
            m = m / m.sum() * photons
            for _ in range(per):
                q = rng.poisson(m).astype(float)
                refs.append(q / q.sum())
                lab.append((x, y))
    return np.array(refs), np.array(lab)


class Opening(Narrated):
    def construct(self):
        title = Tex(r"\textbf{Calibrating a PET detector}", font_size=50).to_edge(UP, buff=0.4)
        sub = Tex(r"pixelated vs (semi-)monolithic", font_size=30, color=GREY_B).next_to(title, DOWN, buff=0.2)
        det = VGroup(*[Square(0.32, fill_color=XTAL_C, fill_opacity=0.3, stroke_color=XTAL_C, stroke_width=1) for _ in range(16)]).arrange_in_grid(4, 4, buff=0.04)
        sens = Rectangle(width=det.width, height=0.16, fill_color=SIPM_C, fill_opacity=1, stroke_width=0).next_to(det, DOWN, buff=0.03)
        raw = VGroup(*[Line(ORIGIN, DOWN * 0.5, color=LIGHT_C, stroke_width=3) for _ in range(6)]).arrange(RIGHT, buff=0.12).next_to(sens, DOWN, buff=0.1)
        rl = Tex(r"charges, timestamps", font_size=24, color=LIGHT_C).next_to(raw, DOWN, buff=0.12)
        left = VGroup(det, sens, raw, rl).move_to(LEFT * 4.2 + DOWN * 0.7)
        box = RoundedRectangle(corner_radius=0.15, width=2.4, height=1.0, color=YELLOW).move_to(LEFT * 0.6 + DOWN * 0.7)
        bl = Tex(r"calibration", font_size=30, color=YELLOW).move_to(box)
        a1 = Arrow(left.get_right(), box.get_left(), buff=0.2, color=GREY_B)
        outs = VGroup(MathTex(r"(x, y, z)", font_size=34, color=MONO_C), MathTex(r"E", font_size=34, color=PIX_C),
                      MathTex(r"t", font_size=34, color=SEMI_C), Tex(r"per-LOR\\efficiency", font_size=26, color=GREY_A)).arrange(DOWN, buff=0.35)
        outs.move_to(RIGHT * 3.6 + DOWN * 0.7)
        lab = VGroup(*[Tex(t, font_size=22, color=GREY_B).next_to(o, RIGHT, buff=0.3) for t, o in zip(("where", "how much", "when", "how often"), outs)])
        arrs = VGroup(*[Arrow(box.get_right(), o.get_left(), buff=0.15, color=GREY_B, stroke_width=2) for o in outs])
        with self.voiceover(text="A PET detector does not report where a gamma ray hit. <bookmark mark='r'/>It reports charges and "
                                 "timestamps from its photosensors. <bookmark mark='c'/>Calibration is everything that turns those "
                                 "numbers into physics: <bookmark mark='p'/>where the interaction was, <bookmark mark='e'/>how much "
                                 "energy it deposited, <bookmark mark='t'/>when it happened, <bookmark mark='n'/>and, across the whole "
                                 "scanner, how efficiently each line of response counts. <bookmark mark='d'/>The answers look very "
                                 "different for a pixelated block than for a monolithic crystal, and that difference is the subject "
                                 "of this video."):
            self.play(Write(title), FadeIn(sub), run_time=1.0)
            self.at("r", FadeIn(det), FadeIn(sens), LaggedStart(*[Create(r) for r in raw], lag_ratio=0.1), FadeIn(rl))
            self.at("c", GrowArrow(a1), Create(box), FadeIn(bl))
            self.at("p", GrowArrow(arrs[0]), FadeIn(outs[0]), FadeIn(lab[0]))
            self.at("e", GrowArrow(arrs[1]), FadeIn(outs[1]), FadeIn(lab[1]))
            self.at("t", GrowArrow(arrs[2]), FadeIn(outs[2]), FadeIn(lab[2]))
            self.at("n", GrowArrow(arrs[3]), FadeIn(outs[3]), FadeIn(lab[3]))
            self.at("d", Indicate(det, color=PIX_C))
        self.wait(0.5)
        fade_all(self)


class Block(Narrated):
    def construct(self):
        title = Tex(r"the block detector (Casey \& Nutt, 1986)", font_size=34).to_edge(UP, buff=0.35)
        n, s = 8, 0.42
        xt = VGroup(*[Rectangle(width=s * 0.92, height=1.6, fill_color=XTAL_C, fill_opacity=0.25, stroke_color=XTAL_C, stroke_width=1.5)
                      for _ in range(n)]).arrange(RIGHT, buff=s * 0.08).move_to(LEFT * 3.3 + UP * 0.9)
        guide = Rectangle(width=xt.width, height=0.5, fill_color=GREY_E, fill_opacity=0.8, stroke_color=GREY_B, stroke_width=1).next_to(xt, DOWN, buff=0.02)
        slots = VGroup(*[Line(guide.get_top() + RIGHT * (x * xt.width / 2), guide.get_top() + RIGHT * (x * xt.width / 2) + DOWN * d,
                              color=GREY_B, stroke_width=2) for x, d in ((-0.5, 0.35), (-0.25, 0.2), (0.25, 0.2), (0.5, 0.35))])
        pmts = VGroup(*[RoundedRectangle(corner_radius=0.1, width=xt.width / 2 - 0.06, height=0.7, fill_color=PMT_C, fill_opacity=1,
                                         stroke_width=0) for _ in range(2)]).arrange(RIGHT, buff=0.12).next_to(guide, DOWN, buff=0.03)
        pl = VGroup(MathTex("A", font_size=30).move_to(pmts[0]), MathTex("B", font_size=30).move_to(pmts[1]))
        dims = Tex(r"crystals \textbf{5.6 $\times$ 13.5 mm}, 4 rows $\times$ 8, \textbf{4} PMTs", font_size=24, color=GREY_B).to_edge(DOWN, buff=0.4)
        k = ValueTracker(1)

        def share(i):
            u = (i + 0.5) / n
            return 1 - u, u

        hit = always_redraw(lambda: Dot(xt[int(k.get_value())].get_center() + UP * 0.3, color=YELLOW, radius=0.08))
        bars = always_redraw(lambda: VGroup(*[Rectangle(width=0.35, height=0.05 + 1.6 * w, fill_color=LIGHT_C, fill_opacity=0.9, stroke_width=0)
                                              .move_to(pmts[j].get_bottom() + DOWN * 0.15, aligned_edge=UP) for j, w in enumerate(share(int(k.get_value())))]))
        ax = NumberLine(x_range=[0, 1, 0.25], length=5.0, color=GREY_B, include_numbers=True, font_size=20,
                        decimal_number_config={"num_decimal_places": 2}).move_to(RIGHT * 3.4 + DOWN * 0.4)
        axl = MathTex(r"\frac{B}{A+B}", font_size=34).next_to(ax, UP, buff=0.5)
        marks = VGroup(*[Dot(ax.n2p(share(i)[1]), color=XTAL_C, radius=0.07) for i in range(n)])
        thr = VGroup(*[DashedLine(ax.n2p(share(i)[1] + 0.5 / n) + UP * 0.35, ax.n2p(share(i)[1] + 0.5 / n) + DOWN * 0.35, color=YELLOW)
                       for i in range(n - 1)])
        tl = Tex(r"thresholds $\Rightarrow$ crystal", font_size=26, color=YELLOW).next_to(ax, DOWN, buff=0.55)
        led = VGroup(Circle(radius=0.16, color=LIGHT_C, fill_opacity=0.8), Tex(r"LED", font_size=22)).arrange(RIGHT, buff=0.1)
        led.next_to(pmts, RIGHT, buff=0.7)
        ledl = Tex(r"equal gains", font_size=24, color=LIGHT_C).next_to(led, DOWN, buff=0.15)
        with self.voiceover(text="The conventional detector is the block, introduced by Casey and Nutt in nineteen eighty six. "
                                 "<bookmark mark='x'/>A grid of small crystals, <bookmark mark='g'/>a slotted light guide, <bookmark mark='p'/>"
                                 "and only four photomultipliers. The slots are cut to different depths so that each crystal shares "
                                 "its light between the tubes in its own proportion. <bookmark mark='h'/>Light from a crystal on the "
                                 "left lands mostly in tube A; <bookmark mark='m'/>move right and it shifts toward B. <bookmark mark='r'/>"
                                 "So the ratio of B to the sum marks the crystal, <bookmark mark='t'/>and the decoder only needs "
                                 "thresholds between neighbouring values. <bookmark mark='l'/>That only works if all four tubes have "
                                 "equal gain, so the original system shone a common LED into them and adjusted each one."):
            self.play(Write(title), run_time=0.8)
            self.at("x", FadeIn(xt))
            self.at("g", FadeIn(guide), Create(slots))
            self.at("p", FadeIn(pmts), FadeIn(pl), FadeIn(dims))
            self.at("h", FadeIn(hit, scale=2), FadeIn(bars))
            self.at("m", k.animate.set_value(6), run_time=2.0, rate_func=linear)
            self.at("r", Create(ax), FadeIn(axl), LaggedStart(*[FadeIn(m, scale=2) for m in marks], lag_ratio=0.1), run_time=1.2)
            self.at("t", Create(thr), FadeIn(tl))
            self.at("l", FadeIn(led), FadeIn(ledl))
        self.wait(0.5)
        fade_all(self)


class Flood(Narrated):
    def construct(self):
        title = Tex(r"step 1: the flood map and the crystal lookup table", font_size=32).to_edge(UP, buff=0.35)
        x, y, comp = block_flood()
        h = hist2d(x, y)
        img = heat(h, 4.6).move_to(LEFT * 3.2 + DOWN * 0.35)
        frame = SurroundingRectangle(img, buff=0, color=GREY_D, stroke_width=1)
        src = VGroup(icon_flood(0.9), Tex(r"uncollimated source", font_size=22, color=GOOD_C)).arrange(RIGHT, buff=0.15).next_to(img, UP, buff=0.2)
        to_xy = lambda a, b: img.get_center() + np.array([a / 1.05 * img.width / 2, b / 1.05 * img.height / 2, 0])
        peaks = VGroup(*[Dot(to_xy(a, b), radius=0.05, color=GOOD_C) for a in comp for b in comp])
        mids = (comp[:-1] + comp[1:]) / 2
        grid = VGroup(*[Line(to_xy(m, -1.05), to_xy(m, 1.05), color=WHITE, stroke_width=1.5) for m in mids],
                      *[Line(to_xy(-1.05, m), to_xy(1.05, m), color=WHITE, stroke_width=1.5) for m in mids])
        lut = VGroup(*[Square(0.36, stroke_color=GREY_B, stroke_width=1, fill_color=XTAL_C, fill_opacity=0.15) for _ in range(64)]).arrange_in_grid(8, 8, buff=0.02)
        lut.move_to(RIGHT * 3.6 + DOWN * 0.35)
        lut_l = Tex(r"lookup table: \textbf{1 label} per region", font_size=24).next_to(lut, UP, buff=0.2)
        arrow = Arrow(img.get_right(), lut.get_left(), buff=0.25, color=GREY_B)
        edge = VGroup(*[SurroundingRectangle(Dot(to_xy(a, b)), buff=0.05, color=BAD_C) for a, b in ((comp[0], comp[0]), (comp[1], comp[0]))])
        el = Tex(r"edge crystals bunch together", font_size=24, color=BAD_C).next_to(img, DOWN, buff=0.2)
        note = Tex(r"computed here: Anger logic, 500 photons, a compressive light guide", font_size=20, color=GREY_B).to_edge(DOWN, buff=0.1)
        with self.voiceover(text="That accumulated picture is the flood map, and it drives the first calibration, crystal "
                                 "identification. <bookmark mark='s'/>The source was uncollimated, so no single event came with a "
                                 "known position. <bookmark mark='f'/>Yet the map shows one bright spot per crystal, blurred by "
                                 "light statistics. <bookmark mark='e'/>The spots "
                                 "are not evenly spaced; edge crystals are squeezed together by the light guide. <bookmark mark='p'/>"
                                 "Software finds the peaks, <bookmark mark='g'/>draws boundaries between them, <bookmark mark='l'/>and "
                                 "stores a lookup table that turns any position into a crystal number. The key point: the crystal "
                                 "pattern itself supplies the labels, so no collimator is needed."):
            self.play(Write(title), run_time=0.8)
            self.at("s", FadeIn(src))
            self.at("f", FadeIn(img), Create(frame), FadeIn(note), run_time=1.2)
            self.at("e", Create(edge), FadeIn(el))
            self.at("p", FadeOut(edge), FadeOut(el), LaggedStart(*[FadeIn(p, scale=2) for p in peaks], lag_ratio=0.01), run_time=1.2)
            self.at("g", Create(grid), run_time=1.0)
            self.at("l", GrowArrow(arrow), FadeIn(lut), FadeIn(lut_l))
        self.wait(0.5)
        fade_all(self)


class NoPeaks(Narrated):
    def construct(self):
        title = Tex(r"monolithic: the flood has \textbf{no peaks}", font_size=34).to_edge(UP, buff=0.35)
        x, y, comp = block_flood()
        left = heat(hist2d(x, y), 3.6).move_to(LEFT * 3.6 + DOWN * 0.2)
        rng = np.random.default_rng(3)
        u = rng.uniform(-1, 1, (60000, 2))
        comp_u = np.tanh(1.7 * u) / np.tanh(1.7)
        mx, my = comp_u[:, 0] + rng.normal(0, 0.05, 60000), comp_u[:, 1] + rng.normal(0, 0.05, 60000)
        right = heat(hist2d(mx, my), 3.6).move_to(RIGHT * 0.4 + DOWN * 0.2)
        ll = VGroup(Tex(r"pixelated", font_size=26, color=PIX_C).next_to(left, UP, buff=0.15),
                    Tex(r"monolithic", font_size=26, color=MONO_C).next_to(right, UP, buff=0.15))
        q = Tex(r"?", font_size=90, color=BAD_C).move_to(right)
        # the fix: events with known positions
        beam = VGroup(icon_beam(0.9), Tex(r"known position", font_size=24, color=GOOD_C)).arrange(DOWN, buff=0.15).move_to(RIGHT * 4.6 + UP * 1.0)
        pats = Group()
        for k, (px, py) in enumerate(((-8, 4), (0, 0), (9, -6))):
            m = mono_light(px, py, 8.0)
            pats.add(heat(m, 1.1, 1.0))
        pats.arrange(RIGHT, buff=0.15).move_to(RIGHT * 4.6 + DOWN * 1.0)
        pl = Tex(r"light pattern $\to$ $(x, y, z)$", font_size=24, color=MONO_C).next_to(pats, DOWN, buff=0.2)
        fit_frame(Group(pats, pl, beam))
        with self.voiceover(text="Now replace the pixels with one continuous crystal. <bookmark mark='l'/>A pixelated flood is a grid "
                                 "of spots. <bookmark mark='r'/>A monolithic flood is smooth: every position is possible, so there "
                                 "are no peaks to find <bookmark mark='q'/>and the flood alone cannot say where any event was. "
                                 "<bookmark mark='b'/>The labels have to be bought, with events of known position from a collimated "
                                 "beam, <bookmark mark='p'/>so that the detector can learn which light pattern belongs to which point "
                                 "in three dimensions."):
            self.play(Write(title), run_time=0.8)
            self.at("l", FadeIn(left), FadeIn(ll[0]))
            self.at("r", FadeIn(right), FadeIn(ll[1]))
            self.at("q", FadeIn(q, scale=1.5))
            self.at("b", FadeIn(beam))
            self.at("p", LaggedStart(*[FadeIn(p) for p in pats], lag_ratio=0.3), FadeIn(pl))
        self.wait(0.5)
        fade_all(self)


class KNN(Narrated):
    def construct(self):
        title = Tex(r"reference data and nearest neighbours", font_size=34).to_edge(UP, buff=0.35)
        refs, lab = knn_library()
        rng = np.random.default_rng(9)
        tx, ty = 3.3, -5.2
        m = mono_light(tx, ty, 8.0).ravel()
        q = rng.poisson(m / m.sum() * 1500).astype(float)
        q /= q.sum()
        d = ((refs - q) ** 2).sum(1)
        kk = 40
        nn = np.argsort(d)[:kk]
        estx, esty = lab[nn].mean(0)
        S = 0.15                                                   # units per mm on the crystal face
        face = Square(32 * S, fill_color=MONO_C, fill_opacity=0.12, stroke_color=MONO_C).move_to(LEFT * 3.4 + DOWN * 0.3)
        to = lambda x, y: face.get_center() + np.array([x * S, y * S, 0])
        pos = np.unique(lab, axis=0)
        grid = VGroup(*[Dot(to(*p), radius=0.03, color=GREY_B) for p in pos])
        gl = Tex(r"pencil beam at each point $\to$ library", font_size=24).next_to(face, UP, buff=0.2)
        ev = heat(q.reshape(8, 8), 1.8, 1.0).move_to(RIGHT * 2.0 + UP * 0.9)
        evl = Tex(r"unknown event", font_size=24).next_to(ev, UP, buff=0.15)
        hit_nn = VGroup(*[Dot(to(*lab[i]) + rng.normal(0, 0.03, 3) * np.array([1, 1, 0]), radius=0.05, color=YELLOW) for i in nn])
        est = VGroup(Cross(scale_factor=0.13, stroke_color=BAD_C, stroke_width=5).move_to(to(estx, esty)))
        true = Circle(radius=0.12, color=GOOD_C, stroke_width=4).move_to(to(tx, ty))
        res = VGroup(Tex(r"$k$ = \textbf{%d} closest patterns" % kk, font_size=26, color=YELLOW),
                     Tex(r"estimate: their position", font_size=26, color=BAD_C),
                     Tex(r"error \textbf{%.1f mm}" % np.hypot(estx - tx, esty - ty), font_size=26)).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        res.move_to(RIGHT * 3.6 + DOWN * 1.4)
        note = Tex(r"computed here: 32 mm face, 8$\times$8 pixels, 1500 photons, 8 refs per point", font_size=20, color=GREY_B).to_edge(DOWN, buff=0.1)
        cost = Tex(r"Maas 2009: a fine grid $\times$ \textbf{hundreds} of angles", font_size=26, color=BAD_C).to_edge(DOWN, buff=0.5)
        with self.voiceover(text="That scan gives a library. <bookmark mark='g'/>Every grid point holds many recorded light patterns "
                                 "with a known position. <bookmark mark='e'/>For a new event, compare "
                                 "its pattern with the whole library, <bookmark mark='n'/>pick the k closest, <bookmark mark='x'/>and "
                                 "take their position as the estimate. <bookmark mark='t'/>Here, with an idealised light model at one "
                                 "depth, the estimate lands under half a millimetre from the truth. <bookmark mark='c'/>The catch is the cost. The "
                                 "Delft group's first version needed a fine grid and hundreds of angles of incidence, because depth "
                                 "changes the pattern."):
            self.play(Write(title), FadeIn(face), run_time=0.8)
            self.at("g", LaggedStart(*[FadeIn(g_) for g_ in grid], lag_ratio=0.002), FadeIn(gl), FadeIn(note), run_time=1.5)
            self.at("e", FadeIn(ev), FadeIn(evl))
            self.at("n", LaggedStart(*[FadeIn(h_, scale=2) for h_ in hit_nn], lag_ratio=0.02), FadeIn(res[0]), run_time=1.2)
            self.at("x", FadeIn(est, scale=2), FadeIn(res[1]))
            self.at("t", Create(true), FadeIn(res[2]))
            self.at("c", FadeOut(note), FadeIn(cost))
        self.wait(0.5)
        fade_all(self)


class Cheaper(Narrated):
    def construct(self):
        title = Tex(r"buying fewer labels", font_size=34).to_edge(UP, buff=0.35)
        S = 0.075
        panels = VGroup()
        specs = [("pencil, many angles", 1), ("pencil, perpendicular", 2), ("fan beams, $x$ and $y$", 3)]
        for k, (lab, kind) in enumerate(specs):
            face = Square(32 * S, fill_color=MONO_C, fill_opacity=0.12, stroke_color=MONO_C)
            g = VGroup(face)
            pts = np.arange(-14, 14.01, 4)
            if kind < 3:
                for x in pts:
                    for y in pts:
                        g.add(Dot(face.get_center() + np.array([x * S, y * S, 0]), radius=0.035, color=YELLOW))
                        if kind == 1:
                            for a in (0.5, 2.1, 3.7):
                                g.add(Line(face.get_center() + np.array([x * S, y * S, 0]),
                                           face.get_center() + np.array([x * S, y * S, 0]) + 0.13 * np.array([np.cos(a), np.sin(a), 0]),
                                           color=YELLOW, stroke_width=1))
            else:
                for x in pts:
                    g.add(Line(face.get_center() + np.array([x * S, -15 * S, 0]), face.get_center() + np.array([x * S, 15 * S, 0]), color=YELLOW, stroke_width=2))
                    g.add(Line(face.get_center() + np.array([-15 * S, x * S, 0]), face.get_center() + np.array([15 * S, x * S, 0]), color=GOOD_C, stroke_width=2))
            g.add(Tex(lab, font_size=22).next_to(face, DOWN, buff=0.15))
            panels.add(g)
        panels.arrange(RIGHT, buff=1.7).shift(UP * 0.7)
        steps = VGroup(Tex(r"\textbf{$\geq$100$\times$}", font_size=28, color=GOOD_C), Tex(r"\textbf{$\geq$100$\times$}", font_size=28, color=GOOD_C))
        arrs = VGroup()
        for k in range(2):
            a = Arrow(panels[k][0].get_right(), panels[k + 1][0].get_left(), buff=0.1, color=GOOD_C)
            arrs.add(a)
            steps[k].next_to(a, UP, buff=0.05)
        cites = VGroup(Tex(r"van Dam 2011", font_size=20, color=GREY_B).next_to(arrs[0], DOWN, buff=0.08),
                       Tex(r"Borghi 2015", font_size=20, color=GREY_B).next_to(arrs[1], DOWN, buff=0.08))
        hours = Tex(r"$\to$ \textbf{2--3 h} per $\sim$2 cm detector", font_size=28).next_to(panels, DOWN, buff=0.5)
        acc = VGroup(Tex(r"k-NN only within a coarse pre-estimate: \textbf{$\sim$200$\times$} faster", font_size=26, color=MONO_C),
                     Tex(r"events missing \textbf{16 of 64} pixels still usable", font_size=26, color=MONO_C)).arrange(DOWN, buff=0.18).to_edge(DOWN, buff=0.45)
        with self.voiceover(text="Most of the progress since has been about buying fewer labels. <bookmark mark='a'/>The first "
                                 "libraries used a pencil beam at every point and many angles. <bookmark mark='b'/>Van Dam and "
                                 "colleagues needed reference data from perpendicular beams only, "
                                 "cutting calibration time at least a hundredfold. <bookmark mark='c'/>Borghi and colleagues then "
                                 "replaced the points with fan beams, one set along x and one along y, for at least another hundredfold. "
                                 "<bookmark mark='h'/>That brought a two centimetre crystal down to two or three hours. <bookmark mark='k'/>"
                                 "In twenty sixteen they also sped up the search itself, comparing each event only with library "
                                 "entries near a rough first guess, about two hundred times faster, <bookmark mark='m'/>and kept "
                                 "events with up to sixteen of sixty four pixels missing."):
            self.play(Write(title), run_time=0.8)
            self.at("a", FadeIn(panels[0]))
            self.at("b", GrowArrow(arrs[0]), FadeIn(steps[0]), FadeIn(cites[0]), FadeIn(panels[1]))
            self.at("c", GrowArrow(arrs[1]), FadeIn(steps[1]), FadeIn(cites[1]), FadeIn(panels[2]))
            self.at("h", FadeIn(hours))
            self.at("k", FadeIn(acc[0]))
            self.at("m", FadeIn(acc[1]))
        self.wait(0.5)
        fade_all(self)


class FloodDOI(Narrated):
    def construct(self):
        title = Tex(r"depth from a flood: match the quantiles", font_size=34).to_edge(UP, buff=0.35)
        T, nz = 22.0, 4                                        # crystal thickness (mm), depth bands (Borghi: 22 mm LYSO)
        mu = 1 / 11.0                                          # illustrative attenuation (1/mm)
        zs = np.linspace(0, T, 200)
        pz = mu * np.exp(-mu * zs) / (1 - np.exp(-mu * T))
        cdf = (1 - np.exp(-mu * zs)) / (1 - np.exp(-mu * T))
        zq = [zs[np.searchsorted(cdf, f)] for f in (0.25, 0.5, 0.75)]
        ax1 = Axes(x_range=[0, T, 5.5], y_range=[0, pz.max() * 1.15, 0.05], x_length=4.6, y_length=2.4, tips=False,
                   axis_config={"color": GREY_B, "include_ticks": False}).move_to(LEFT * 3.4 + UP * 0.4)
        c1 = ax1.plot(lambda z: np.interp(z, zs, pz), x_range=[0, T], color=GOOD_C, stroke_width=4)
        fill = ax1.get_area(c1, x_range=[0, T], color=GOOD_C, opacity=0.2)
        l1 = VGroup(Tex(r"depth $z$ (front $\to$ back)", font_size=22, color=GREY_B).next_to(ax1, DOWN, buff=0.15),
                    Tex(r"known: attenuation (simulated)", font_size=24, color=GOOD_C).next_to(ax1, UP, buff=0.15))
        q1 = VGroup(*[DashedLine(ax1.c2p(z, 0), ax1.c2p(z, pz.max() * 1.1), color=YELLOW) for z in zq])
        rng = np.random.default_rng(6)
        zev = -np.log(1 - rng.uniform(0, 1 - np.exp(-mu * T), 8000)) / mu
        sspi = 0.04 + 0.25 * np.exp(-(T - zev) / 6.0) + rng.normal(0, 0.012, zev.size)   # light concentration rises near the sensor
        hist, edges = np.histogram(sspi, bins=60)
        ax2 = Axes(x_range=[edges[0], edges[-1], 0.1], y_range=[0, hist.max() * 1.15, 100], x_length=4.6, y_length=2.4, tips=False,
                   axis_config={"color": GREY_B, "include_ticks": False}).move_to(RIGHT * 3.4 + UP * 0.4)
        bars = VGroup(*[Rectangle(width=ax2.c2p(edges[1], 0)[0] - ax2.c2p(edges[0], 0)[0], height=max(ax2.c2p(0, h)[1] - ax2.c2p(0, 0)[1], 0.001),
                                  fill_color=MONO_C, fill_opacity=0.8, stroke_width=0).move_to(ax2.c2p((a + b) / 2, 0), aligned_edge=DOWN)
                        for h, a, b in zip(hist, edges[:-1], edges[1:])])
        l2 = VGroup(Tex(r"light concentration $S = \sum n_i^2$", font_size=22, color=GREY_B).next_to(ax2, DOWN, buff=0.15),
                    Tex(r"measured: flood events", font_size=24, color=MONO_C).next_to(ax2, UP, buff=0.15))
        sq = np.quantile(sspi, [0.25, 0.5, 0.75])               # front (far from sensor) events have the lowest S
        q2 = VGroup(*[DashedLine(ax2.c2p(v, 0), ax2.c2p(v, hist.max() * 1.1), color=YELLOW) for v in sq])
        # the same colour marks the same quarter of events: a depth band on the left, an S band on the right
        band_c = [BLUE_L, TEAL_L, GOOD_C, YELLOW]
        zb = [0] + list(zq) + [T]
        sb = [edges[0]] + list(sq) + [edges[-1]]
        bands1 = VGroup(*[ax1.get_area(c1, x_range=[zb[k], zb[k + 1]], color=band_c[k], opacity=0.55) for k in range(4)])
        bands2 = VGroup(*[VGroup(*[b_.copy().set_fill(band_c[k], opacity=0.9) for b_, a, b in zip(bars, edges[:-1], edges[1:])
                                   if sb[k] <= (a + b) / 2 < sb[k + 1]]) for k in range(4)])
        links = VGroup(*[Tex(r"\textbf{25\%}", font_size=22, color=band_c[k]).move_to(ax1.c2p((zb[k] + zb[k + 1]) / 2, pz.max() * 0.08))
                         for k in range(4)])
        ends = VGroup(Tex(r"front", font_size=20, color=GREY_B).next_to(ax1.c2p(0, 0), DOWN, buff=0.05).shift(UP * 0.0),
                      Tex(r"sensor side", font_size=20, color=GREY_B).next_to(ax1.c2p(T, 0), DOWN, buff=0.05))
        eq = Tex(r"equal fractions $\Rightarrow$ same depth band", font_size=28, color=YELLOW).to_edge(DOWN, buff=1.3)
        cuc = VGroup(Tex(r"Cucarella 2026: fit the $E/I_{\max}$ histogram;", font_size=24),
                     Tex(r"its two edges $=$ front and back face $\to$ mm", font_size=24)).arrange(DOWN, buff=0.1).to_edge(DOWN, buff=0.35)
        note = Tex(r"computed here, illustrative", font_size=18, color=GREY_B).to_corner(DL, buff=0.12)
        with self.voiceover(text="Depth has its own trick, and it needs no collimator at all. <bookmark mark='a'/>In a flood, how "
                                 "deep the gamma rays interact is not unknown: it follows the exponential attenuation of the crystal, "
                                 "which a quick simulation gives. <bookmark mark='m'/>Meanwhile every event has a measurable light "
                                 "concentration, which is higher the closer it is to the sensor. <bookmark mark='q'/>Sort the events "
                                 "by that quantity, <bookmark mark='l'/>and cut the sorted list at the fractions the simulation "
                                 "expects in each depth band. <bookmark mark='e'/>The quarter with the most concentrated light is the "
                                 "quarter nearest the sensor, and so on. Borghi and colleagues build the depth lookup this way. "
                                 "<bookmark mark='c'/>The Valencia group does the same thing in one fit: the edges of the energy over "
                                 "maximum histogram mark the front and back faces of the crystal."):
            self.play(Write(title), run_time=0.8)
            self.at("a", Create(ax1), Create(c1), FadeIn(fill), FadeIn(l1), FadeIn(note))
            self.at("m", Create(ax2), LaggedStart(*[GrowFromEdge(b_, DOWN) for b_ in bars], lag_ratio=0.01), FadeIn(l2), run_time=1.2)
            self.at("q", Indicate(bars, color=YELLOW, scale_factor=1.0))
            self.at("l", Create(q2), Create(q1))
            self.play(LaggedStart(*[AnimationGroup(FadeIn(bands1[k]), FadeIn(bands2[k])) for k in range(4)], lag_ratio=0.35), run_time=1.6)
            self.at("e", FadeIn(links), FadeIn(eq), Indicate(bands2[3], color=YELLOW, scale_factor=1.0), Indicate(bands1[3], color=YELLOW, scale_factor=1.0))
            self.at("c", FadeOut(eq), FadeIn(cuc))
        self.wait(0.5)
        fade_all(self)


class MonoEnergyTime(Narrated):
    def construct(self):
        title = Tex(r"energy and timing become functions of position", font_size=32).to_edge(UP, buff=0.35)
        f7 = card("borghi_fig7.png", 3.4).to_edge(LEFT, buff=0.35).shift(DOWN * 0.2)
        f9 = card("borghi_fig9.png", 3.4).to_edge(RIGHT, buff=0.35).shift(DOWN * 0.2)
        cred = credit(r"Figs.~7 and 9: " + C_B16)
        l7 = Tex(r"photopeak vs $(x, y)$, 4 depth bands", font_size=24, color=PIX_C).next_to(f7, UP, buff=0.15)
        l9 = Tex(r"first-photon delay, 16 pixels, one voxel", font_size=24, color=SEMI_C).next_to(f9, UP, buff=0.15)
        b7 = img_box(f7[1], 0.15, 0.03, 0.43, 0.48, YELLOW)
        b9 = img_box(f9[1], 0.03, 0.42, 0.42, 0.82, YELLOW)
        lut = Tex(r"$E$: a map over $(x, y, z)$\quad $t$: one PDF per voxel and pixel", font_size=26).to_edge(DOWN, buff=0.45)
        laser = Tex(r"electronic skews first: a pulsed laser", font_size=24, color=GREY_A).next_to(lut, UP, buff=0.15)
        with self.voiceover(text="With position known, the other calibrations change character. <bookmark mark='e'/>Energy no longer "
                                 "has one gain per crystal; it has a map. In this Delft detector the photopeak shifts with position, "
                                 "<bookmark mark='z'/>and the map differs by depth, so the correction is a lookup over x, y and z. "
                                 "<bookmark mark='t'/>Timing too: the delay to the first detected photon depends on how far the "
                                 "interaction is from each pixel. <bookmark mark='p'/>Pixels right under the event fire early and "
                                 "sharply; distant ones late and spread out. They store these distributions per voxel and per pixel, "
                                 "and estimate the time by maximum likelihood, <bookmark mark='l'/>after first removing the "
                                 "electronic skews between dies with a pulsed laser."):
            self.play(Write(title), run_time=0.8)
            self.at("e", FadeIn(f7), FadeIn(l7), FadeIn(cred))
            self.at("z", Create(b7))
            self.at("t", FadeIn(f9), FadeIn(l9))
            self.at("p", Create(b9))
            self.at("l", FadeIn(lut), FadeIn(laser))
        self.wait(0.5)
        fade_all(self)


class Semi(Narrated):
    def construct(self):
        title = Tex(r"semi-monolithic and whole rings: the shortcuts", font_size=32).to_edge(UP, buff=0.35)
        slabs = VGroup(*[Rectangle(width=0.15, height=2.0, fill_color=XTAL_C, fill_opacity=0.3, stroke_color=WHITE, stroke_width=1)
                         for _ in range(16)]).arrange(RIGHT, buff=0.02).move_to(LEFT * 3.5 + UP * 1.0)
        across = VGroup(Arrow(slabs.get_corner(DL) + DOWN * 0.25, slabs.get_corner(DR) + DOWN * 0.25, buff=0, color=PIX_C, stroke_width=3),
                        Tex(r"slab: flood, like pixels", font_size=22, color=PIX_C))
        across[1].next_to(across[0], DOWN, buff=0.08)
        along = VGroup(DoubleArrow(slabs.get_corner(DL) + LEFT * 0.25, slabs.get_corner(UL) + LEFT * 0.25, buff=0, color=MONO_C, stroke_width=4, tip_length=0.15),
                       Tex(r"along: slit scan", font_size=22, color=MONO_C))
        along[1].next_to(along[0], LEFT, buff=0.1).rotate(PI / 2)
        mods = VGroup(*[Square(0.16, fill_color=XTAL_C, fill_opacity=0.5, stroke_width=0.5) for _ in range(28)]).arrange_in_grid(2, 14, buff=0.05)
        mods.next_to(across, DOWN, buff=0.5).align_to(slabs, LEFT)
        one = icon_net(0.8, 0.55).next_to(mods, RIGHT, buff=0.5)
        conv = VGroup(*[Line(one.get_left(), m.get_right(), color=MONO_C, stroke_width=0.8, stroke_opacity=0.5) for m in mods[::3]])
        trained = SurroundingRectangle(mods[0], buff=0.03, color=YELLOW)
        ml = Tex(r"train on \textbf{1}, use on \textbf{28}", font_size=24, color=MONO_C).next_to(VGroup(mods, one), DOWN, buff=0.2)
        eqz = VGroup(Tex(r"energy: channel gains $\to$ slab peaks $\to$ map", font_size=22, color=PIX_C),
                     Tex(r"depth: $E/I_{\max}$ from the flood", font_size=22, color=LIGHT_C)).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        eqz.next_to(ml, DOWN, buff=0.3).align_to(mods, LEFT)
        fan = card("db_fanbeam.png", 2.6).to_edge(RIGHT, buff=0.35).shift(UP * 0.8)
        cred = credit(r"Fig.~4: " + C_F26)
        fl = VGroup(Tex(r"DeepBreast: rotate a fan in the assembled ring", font_size=24),
                    Tex(r"\textbf{450} steps of \textbf{0.8}$^\circ$ + \textbf{99} of \textbf{0.5 mm}", font_size=24),
                    Tex(r"\textbf{11} $\to$ \textbf{3.6} days", font_size=30, color=GOOD_C)).arrange(DOWN, buff=0.15).next_to(fan, DOWN, buff=0.3)
        fit_frame(Group(fan, fl))
        with self.voiceover(text="Semi-monolithic detectors split the problem. <bookmark mark='s'/>Which slab was hit is a discrete "
                                 "label again, so a flood and a lookup table do it, as in a pixelated block. <bookmark mark='a'/>The "
                                 "position along the slab is continuous, so it needs collimated data: a slit stepped in half "
                                 "millimetre steps. <bookmark mark='o'/>Valencia's preclinical scanner trains one small network on a "
                                 "single module <bookmark mark='u'/>and uses it unchanged on all twenty eight. <bookmark mark='e'/>Energy "
                                 "is equalised in three passes, channel gains, then slab peaks, then a map, and depth comes from the "
                                 "flood fit we just saw. <bookmark mark='f'/>For a whole monolithic ring, DeepBreast puts a rotating "
                                 "fan beam inside the assembled scanner, <bookmark mark='n'/>four hundred and fifty steps of point "
                                 "eight degrees and ninety nine axial steps, <bookmark mark='d'/>cutting calibration from eleven days "
                                 "to three point six."):
            self.play(Write(title), FadeIn(slabs), run_time=0.8)
            self.at("s", GrowArrow(across[0]), FadeIn(across[1]))
            self.at("a", GrowFromCenter(along[0]), FadeIn(along[1]))
            self.at("o", FadeIn(mods), Create(trained), FadeIn(one))
            self.at("u", Create(conv), FadeIn(ml))
            self.at("e", FadeIn(eqz))
            self.at("f", FadeIn(fan), FadeIn(cred), FadeIn(fl[0]))
            self.at("n", FadeIn(fl[1]))
            self.at("d", FadeIn(fl[2]))
        self.wait(0.5)
        fade_all(self)


class Takeaway(Narrated):
    def construct(self):
        title = Tex(r"what each detector needs", font_size=34).to_edge(UP, buff=0.35)
        rows = ["position", "depth", "energy", "timing", "normalisation"]
        cols = [("pixelated", PIX_C), ("semi-mono", SEMI_C), ("monolithic", MONO_C)]
        F, B = "F", "B"
        table = [[F, None, F, F, F], [F + B, F, F, F, F], [B, F, F, F, F]]   # F = flood / uniform, B = collimated beam, None = n/a
        x0, y0, dx, dy = -2.2, 1.8, 2.6, 0.82
        heads = VGroup(*[Tex(n, font_size=28, color=c).move_to(np.array([x0 + k * dx, y0, 0])) for k, (n, c) in enumerate(cols)])
        rlab = VGroup(*[Tex(r, font_size=26, color=GREY_A).move_to(np.array([x0 - 2.6, y0 - (i + 1) * dy, 0]), aligned_edge=LEFT)
                        for i, r in enumerate(rows)])
        cells = VGroup()
        for k in range(3):
            for i in range(5):
                v = table[k][i]
                p = np.array([x0 + k * dx, y0 - (i + 1) * dy, 0])
                if v is None:
                    g = Tex(r"--", font_size=26, color=GREY_B).move_to(p)
                else:
                    icons = [icon_flood(0.7) if ch == F else icon_beam(0.7) for ch in v]
                    g = VGroup(*icons).arrange(RIGHT, buff=0.25).move_to(p)
                cells.add(g)
        legend = VGroup(VGroup(icon_flood(0.6), Tex(r"flood", font_size=22, color=GREY_B)).arrange(RIGHT, buff=0.1),
                        VGroup(icon_beam(0.6), Tex(r"collimated beam", font_size=22, color=GREY_B)).arrange(RIGHT, buff=0.1)).arrange(RIGHT, buff=0.6)
        legend.to_edge(DOWN, buff=0.75)
        moral = Tex(r"pixels give labels for free; monoliths \textbf{buy} them, and the art is buying fewer", font_size=28, color=YELLOW).to_edge(DOWN, buff=0.2)
        with self.voiceover(text="Putting it together. <bookmark mark='p'/>A pixelated scanner calibrates almost everything from "
                                 "floods and uniform sources, because each crystal is its own label. <bookmark mark='s'/>A "
                                 "semi-monolithic one needs a collimated scan only along the slab, and only once. <bookmark mark='m'/>A "
                                 "monolithic one must buy its position labels with collimated beams, <bookmark mark='d'/>while depth, "
                                 "energy and timing can again come from floods, once position is known. <bookmark mark='a'/>Pixels "
                                 "give labels for free; monoliths buy them, and the art is buying fewer."):
            self.play(Write(title), FadeIn(rlab), run_time=1.0)
            self.at("p", FadeIn(heads[0]), LaggedStart(*[FadeIn(c) for c in cells[0:5]], lag_ratio=0.15))
            self.at("s", FadeIn(heads[1]), LaggedStart(*[FadeIn(c) for c in cells[5:10]], lag_ratio=0.15))
            self.at("m", FadeIn(heads[2]), FadeIn(cells[10]), FadeIn(legend))
            self.at("d", LaggedStart(*[FadeIn(c) for c in cells[11:15]], lag_ratio=0.15))
            self.at("a", FadeIn(moral))
        self.wait(1.0)
        fade_all(self)


# ---- demonstrations: the calibration as it happens on the bench (docs/DESIGN.md §3) ---------------------------------
class FloodSetup(Narrated):
    def construct(self):
        title = Tex(r"a flood acquisition", font_size=34).to_edge(UP, buff=0.35)
        x, y, comp, ij = block_flood(return_ij=True)
        n, w = 8, 0.42
        xt = VGroup(*[Rectangle(width=w * 0.92, height=1.3, fill_color=XTAL_C, fill_opacity=0.25, stroke_color=XTAL_C, stroke_width=1.5)
                      for _ in range(n)]).arrange(RIGHT, buff=w * 0.08).move_to(LEFT * 3.6 + DOWN * 0.9)
        guide = Rectangle(width=xt.width, height=0.35, fill_color=GREY_E, fill_opacity=0.8, stroke_color=GREY_B, stroke_width=1).next_to(xt, DOWN, buff=0.02)
        pmts = VGroup(*[RoundedRectangle(corner_radius=0.08, width=xt.width / 2 - 0.06, height=0.5, fill_color=PMT_C, fill_opacity=1, stroke_width=0)
                        for _ in range(2)]).arrange(RIGHT, buff=0.12).next_to(guide, DOWN, buff=0.03)
        src = Dot(xt.get_center() + UP * 3.0, color=YELLOW, radius=0.1)
        srcl = Tex(r"point source, no collimator", font_size=24, color=GOOD_C).next_to(src, RIGHT, buff=0.25)
        cone = Polygon(src.get_center(), xt.get_corner(UL), xt.get_corner(UR), fill_color=GOOD_C, fill_opacity=0.08, stroke_width=0)
        side = Tex(r"side view", font_size=20, color=GREY_B).next_to(pmts, DOWN, buff=0.15)
        img_w = 4.3
        frame = Square(img_w, color=GREY_D, stroke_width=1).move_to(RIGHT * 3.3 + DOWN * 0.35)
        to_xy = lambda a, b: frame.get_center() + np.array([a / 1.05 * img_w / 2, b / 1.05 * img_w / 2, 0])
        maplab = Tex(r"Anger position, one dot per event", font_size=24).next_to(frame, UP, buff=0.15)
        count = Integer(0, font_size=30, color=GOOD_C)
        countl = VGroup(Tex(r"events:", font_size=24, color=GREY_B), count).arrange(RIGHT, buff=0.15).next_to(frame, DOWN, buff=0.2)
        rng = np.random.default_rng(11)

        def event(k, rt=0.35, show_pmt=True):
            col = int(ij[k, 0])
            p = xt[col].get_top() + DOWN * rng.uniform(0.15, 1.05) + RIGHT * rng.uniform(-0.1, 0.1)
            g = Dot(src.get_center(), radius=0.05, color=GOOD_C)
            self.add(g)
            self.play(g.animate.move_to(p), run_time=rt, rate_func=linear)
            flash = Circle(radius=0.12, color=LIGHT_C, fill_opacity=0.8, stroke_width=0).move_to(p)
            u = comp[col]
            bars = VGroup(*[Rectangle(width=0.3, height=0.05 + 1.0 * s_, fill_color=LIGHT_C, fill_opacity=0.9, stroke_width=0)
                            .move_to(pm.get_bottom() + DOWN * 0.42, aligned_edge=UP) for pm, s_ in zip(pmts, ((1 - u) / 2, (1 + u) / 2))])
            dot = Dot(to_xy(x[k], y[k]), radius=0.045, color=LIGHT_C)
            self.remove(g)
            anims = [FadeIn(flash), FadeIn(dot, scale=3)] + ([FadeIn(bars)] if show_pmt else [])
            self.play(*anims, count.animate.set_value(count.get_value() + 1), run_time=rt)
            self.play(FadeOut(flash), *([FadeOut(bars)] if show_pmt else []), run_time=rt * 0.6)
            return dot

        dots = VGroup()
        stages = [(300, "a"), (3000, "b"), (60000, "c")]
        imgs = [heat(hist2d(x[:N], y[:N]), img_w).move_to(frame) for N, _ in stages]
        with self.voiceover(text="Here is what that looks like on the bench. <bookmark mark='s'/>A point source sits in front of "
                                 "the block with no collimator, so it bathes the whole face. <bookmark mark='g'/>A gamma ray stops "
                                 "in one crystal, its light spreads through the guide, <bookmark mark='p'/>the tubes share it, "
                                 "<bookmark mark='m'/>and the event becomes one dot at its Anger position. <bookmark mark='f'/>One "
                                 "dot says little, so the source keeps firing. <bookmark mark='a'/>After a few hundred events, "
                                 "clusters appear; <bookmark mark='b'/>after a few thousand, a grid; <bookmark mark='c'/>after tens "
                                 "of thousands, one sharp spot per crystal."):
            self.play(Write(title), FadeIn(xt), FadeIn(guide), FadeIn(pmts), FadeIn(side), run_time=1.0)
            self.at("s", FadeIn(src, scale=2), FadeIn(srcl), FadeIn(cone))
            self.wait_until_bookmark("g")
            self.play(Create(frame), FadeIn(maplab), FadeIn(countl), run_time=0.5)
            dots.add(event(0, 0.5))
            self.wait_until_bookmark("f")
            for k in range(1, 13):
                dots.add(event(k, 0.16, show_pmt=False))
            self.wait_until_bookmark("a")
            self.play(FadeOut(dots), FadeIn(imgs[0]), count.animate.set_value(300), run_time=0.8)
            self.wait_until_bookmark("b")
            self.play(FadeIn(imgs[1]), count.animate.set_value(3000), run_time=0.8)
            self.wait_until_bookmark("c")
            self.play(FadeIn(imgs[2]), count.animate.set_value(60000), run_time=0.8)
        self.wait(0.5)
        fade_all(self)


class PencilScan(Narrated):
    def construct(self):
        title = Tex(r"a pencil-beam scan", font_size=34).to_edge(UP, buff=0.35)
        S, W, T = 0.12, 32.0, 22.0                                      # 32 x 32 x 22 mm LYSO (Borghi 2016)
        crys = Rectangle(width=W * S, height=T * S, fill_color=MONO_C, fill_opacity=0.15, stroke_color=MONO_C).move_to(LEFT * 3.2 + DOWN * 1.0)
        top_y, bot_y, xc = crys.get_top()[1], crys.get_bottom()[1], crys.get_center()[0]
        X = lambda mm: xc + mm * S
        pix = VGroup(*[Rectangle(width=4 * S * 0.9, height=0.12, fill_color=SIPM_C, fill_opacity=1, stroke_width=0)
                       .move_to(np.array([X(-14 + 4 * k), bot_y - 0.08, 0])) for k in range(8)])
        bx = ValueTracker(-12.0)
        coll = always_redraw(lambda: VGroup(
            Rectangle(width=1.0, height=0.5, fill_color=GREY_C, fill_opacity=1, stroke_width=0).move_to(np.array([X(bx.get_value()) - 0.55, top_y + 0.8, 0])),
            Rectangle(width=1.0, height=0.5, fill_color=GREY_C, fill_opacity=1, stroke_width=0).move_to(np.array([X(bx.get_value()) + 0.55, top_y + 0.8, 0])),
            Dot(np.array([X(bx.get_value()), top_y + 1.2, 0]), color=YELLOW, radius=0.08)))
        beam = always_redraw(lambda: DashedLine(np.array([X(bx.get_value()), top_y + 0.55, 0]), np.array([X(bx.get_value()), bot_y, 0]),
                                                color=GOOD_C, stroke_width=1.5, stroke_opacity=0.5))
        rail = Line(np.array([X(-16), top_y + 1.55, 0]), np.array([X(16), top_y + 1.55, 0]), color=GREY_B, stroke_width=3)
        rl = Tex(r"motorised stage", font_size=20, color=GREY_B).next_to(rail, UP, buff=0.08)
        cl = Tex(r"tungsten slit", font_size=20, color=GREY_B).next_to(crys, LEFT, buff=0.15).shift(UP * 1.45)
        dims = VGroup(Tex(r"\textbf{32 mm}", font_size=22).next_to(crys, RIGHT, buff=0.15).align_to(crys, DOWN),
                      Tex(r"\textbf{22}", font_size=22).next_to(crys, LEFT, buff=0.15))
        # face view: a 1 mm grid that fills as positions are recorded
        F = 0.11
        face = Square(W * F, color=MONO_C, fill_color=MONO_C, fill_opacity=0.08).move_to(RIGHT * 3.4 + DOWN * 0.4)
        pos = np.arange(-15.5, 16, 1.0)
        grid = VGroup(*[Dot(face.get_center() + np.array([px * F, py * F, 0]), radius=0.018, color=GREY_D) for py in pos[::-1] for px in pos])
        fl = Tex(r"face: \textbf{1 mm} grid", font_size=24).next_to(face, UP, buff=0.15)
        lib = Tex(r"$\sim$\textbf{60} events per point", font_size=24, color=YELLOW).next_to(face, DOWN, buff=0.2)
        total = Tex(r"$32 \times 32 =$ \textbf{1024} points (computed here)", font_size=24).next_to(lib, DOWN, buff=0.12)
        prof_base = bot_y - 0.32
        rng = np.random.default_rng(4)

        def shot(depth, rt=0.3, keep=False, hold=0.0):
            xm = bx.get_value()
            p = np.array([X(xm), top_y - depth * S, 0])
            g = Dot(np.array([X(xm), top_y + 1.2, 0]), radius=0.05, color=GOOD_C)
            self.add(g)
            self.play(g.animate.move_to(p), run_time=rt, rate_func=linear)
            self.remove(g)
            h = T - depth
            prof = mono_light(xm, 0.0, h)[4]
            prof = prof / prof.max()
            bars = VGroup(*[Rectangle(width=4 * S * 0.8, height=0.05 + 0.75 * v, fill_color=LIGHT_C, fill_opacity=0.9, stroke_width=0)
                            .move_to(np.array([pix[k].get_center()[0], prof_base, 0]), aligned_edge=UP) for k, v in enumerate(prof)])
            rays = VGroup(*[Line(p, pix[k].get_top(), color=LIGHT_C, stroke_width=1.2, stroke_opacity=0.6) for k in range(8)])
            spot = Dot(p, radius=0.07, color=YELLOW)
            self.play(FadeIn(spot, scale=2), FadeIn(rays), FadeIn(bars), run_time=rt)
            if hold:
                self.wait(hold)
            if not keep:
                self.play(FadeOut(spot), FadeOut(rays), FadeOut(bars), run_time=rt * 0.6)
            return VGroup(spot, rays, bars)

        def mark(xm, color=YELLOW):
            i = int(round(xm + 15.5))
            return grid[16 * 32 + i].animate.set_color(color).scale(1.6)

        with self.voiceover(text="Here is how the library is recorded. <bookmark mark='c'/>A small source sits behind a slit between "
                                 "two tungsten blocks, so only a narrow beam reaches the crystal. <bookmark mark='f'/>Fire, and a "
                                 "gamma ray stops somewhere along the beam. <bookmark mark='d'/>Same x, but a different depth each "
                                 "time, so the light pattern is narrower or wider. That is why every point needs many events, about "
                                 "sixty in the Delft measurements. <bookmark mark='s'/>Then the motorised stage steps the collimator "
                                 "by one millimetre and fires again. <bookmark mark='r'/>Step, fire, record, across the face, "
                                 "<bookmark mark='g'/>row after row, until every point on the grid has its own set of light patterns. "
                                 "<bookmark mark='n'/>For a thirty two millimetre crystal that is over a thousand positions, for one "
                                 "detector."):
            self.play(Write(title), FadeIn(crys), FadeIn(pix), FadeIn(dims), FadeIn(face), FadeIn(grid), FadeIn(fl), run_time=1.0)
            self.at("c", FadeIn(coll), Create(rail), FadeIn(rl), FadeIn(cl), FadeIn(beam))
            self.wait_until_bookmark("f")
            shot(4.0, 0.4, hold=0.8)
            self.wait_until_bookmark("d")
            shot(11.0, 0.3, hold=0.6)
            shot(18.0, 0.3, hold=0.6)
            self.play(mark(-12.0), FadeIn(lib))
            self.wait_until_bookmark("s")
            for _ in range(4):
                self.play(bx.animate.increment_value(1.0), run_time=0.35)
                shot(rng.uniform(2, 20), 0.18)
                self.play(mark(bx.get_value()), run_time=0.2)
            self.wait_until_bookmark("r")
            row = [grid[16 * 32 + int(round(v + 15.5))] for v in np.arange(bx.get_value() + 1, 15.6, 1.0)]
            self.play(bx.animate.set_value(15.0), LaggedStart(*[d_.animate.set_color(YELLOW).scale(1.6) for d_ in row], lag_ratio=0.1), run_time=2.0)
            self.wait_until_bookmark("g")
            rest = [grid[r * 32 + c] for r in range(32) for c in range(32) if r != 16]
            self.play(LaggedStart(*[d_.animate.set_color(YELLOW).scale(1.6) for d_ in rest], lag_ratio=0.002), run_time=2.5)
            self.at("n", FadeIn(total))
        self.wait(0.5)
        fade_all(self)


class FanScan(Narrated):
    def construct(self):
        title = Tex(r"a fan-beam scan", font_size=34).to_edge(UP, buff=0.35)
        F, W = 0.11, 32.0
        pos = np.arange(-15.5, 16, 1.0)

        def face_at(c):
            face = Square(W * F, color=MONO_C, fill_color=MONO_C, fill_opacity=0.08).move_to(c)
            grid = VGroup(*[Dot(c + np.array([px * F, py * F, 0]), radius=0.018, color=GREY_D) for py in pos[::-1] for px in pos])
            return face, grid

        fa, ga = face_at(LEFT * 3.6 + DOWN * 0.2)
        fb, gb = face_at(RIGHT * 1.3 + DOWN * 0.2)
        la = Tex(r"pencil: \textbf{1} point per step", font_size=24).next_to(fa, UP, buff=0.2)
        lb = Tex(r"fan: \textbf{1} line per step", font_size=24).next_to(fb, UP, buff=0.2)
        cb, ca = fb.get_center(), fa.get_center()
        sx = ValueTracker(-15.5)
        sy = ValueTracker(-15.5)
        mode = {"v": True}
        stripe = always_redraw(lambda: (Rectangle(width=0.06, height=W * F + 0.3, fill_color=YELLOW, fill_opacity=0.55, stroke_width=0)
                                        .move_to(cb + RIGHT * sx.get_value() * F)) if mode["v"] else
                               Rectangle(width=W * F + 0.3, height=0.06, fill_color=GOOD_C, fill_opacity=0.55, stroke_width=0)
                               .move_to(cb + UP * sy.get_value() * F))
        pen = always_redraw(lambda: Dot(ca + RIGHT * sx.get_value() * F + UP * 15.5 * F, radius=0.06, color=YELLOW))
        col_ = lambda i: [gb[r * 32 + i] for r in range(32)]
        row_ = lambda j: [gb[(31 - j) * 32 + c] for c in range(32)]
        cnt = VGroup(Tex(r"positions for a 1 mm grid:", font_size=24, color=GREY_B),
                     Tex(r"pencil \textbf{1024}", font_size=28, color=YELLOW), Tex(r"fan \textbf{64}", font_size=28, color=GOOD_C))
        cnt.arrange(DOWN, aligned_edge=LEFT, buff=0.18).next_to(fb, RIGHT, buff=0.5)
        note = Tex(r"computed here", font_size=18, color=GREY_B).next_to(cnt, DOWN, buff=0.12, aligned_edge=LEFT)
        with self.voiceover(text="A fan beam changes what one step buys. <bookmark mark='p'/>A pencil labels one point per step, so "
                                 "it crawls. <bookmark mark='f'/>Open the slit into a line, and each step labels a whole column of "
                                 "the face at once. <bookmark mark='x'/>Step it across in x, <bookmark mark='y'/>then turn it ninety "
                                 "degrees and step it in y. Each event now knows only one coordinate, which is all the one "
                                 "dimensional nearest neighbour method needs. <bookmark mark='c'/>On the same one millimetre grid, "
                                 "that is sixty four positions instead of one thousand and twenty four."):
            self.play(Write(title), FadeIn(fa), FadeIn(ga), FadeIn(fb), FadeIn(gb), FadeIn(la), FadeIn(lb), run_time=1.0)
            self.wait_until_bookmark("p")
            self.add(pen)
            first = [ga[i] for i in range(6)]
            for d_ in first:
                self.play(sx.animate.set_value(d_.get_center()[0] / F - ca[0] / F), d_.animate.set_color(YELLOW).scale(1.6), run_time=0.3)
            self.remove(pen)
            sx.set_value(-15.5)
            self.wait_until_bookmark("f")
            self.add(stripe)
            self.play(*[d_.animate.set_color(YELLOW).scale(1.6) for d_ in col_(0)], run_time=0.5)
            self.wait_until_bookmark("x")
            for i in range(1, 32):
                self.play(sx.animate.set_value(pos[i]), *[d_.animate.set_color(YELLOW).scale(1.6) for d_ in col_(i)], run_time=0.08)
            self.wait_until_bookmark("y")
            mode["v"] = False
            self.play(*[d_.animate.set_color(GOOD_C) for d_ in row_(0)], run_time=0.4)
            for j in range(1, 32):
                self.play(sy.animate.set_value(pos[j]), *[d_.animate.set_color(GOOD_C) for d_ in row_(j)], run_time=0.08)
            self.at("c", FadeIn(cnt), FadeIn(note))
        self.wait(0.5)
        fade_all(self)


# ---- steps 2-4 in depth: why, then how, then what it costs ------------------------------------------------------
# Extra sources: Kuang et al 2026a (176Lu background, 30 min); Krishnamoorthy et al 2018 (Peltier, +-0.5 C);
# Kang et al 2023 (SiPMs held at 26 +- 0.4 C); Spencer et al 2021 (uEXPLORER: >500 000 crystals, ~1e11 LORs,
# 505 ps global vs 412 ps mean per-LOR TOF, "incomplete TOF calibration"); Thull et al 2026 (fan-sum
# normalisation); Akamatsu et al 2022 (22Na dome, 1 MBq, 12 h for energy, timing and normalisation);
# Karlberg et al 2016 ("on a regular basis according to manufacturer's recommendations").
import math

WIN = (408.0, 613.0)                       # DeepBreast trues window (keV)


def phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def peak_kept(g, res=0.12):
    mu, sd = 511 * g, 0.12 * 511 * g / 2.3548
    return phi((WIN[1] - mu) / sd) - phi((WIN[0] - mu) / sd)


def scatter_in(g):
    mu, sd = 380 * g, 70 * g
    return phi((WIN[1] - mu) / sd) - phi((WIN[0] - mu) / sd)


def spec_curve(ax, g, color=WHITE, sw=4, parts=False):
    sd = 0.12 * 511 * g / 2.3548
    pk = lambda e: np.exp(-(e - 511 * g) ** 2 / (2 * sd ** 2))
    sc = lambda e: 0.55 * np.exp(-(e - 380 * g) ** 2 / (2 * (70 * g) ** 2))
    if parts:
        return (ax.plot(pk, x_range=[150, 800], color=GOOD_C, stroke_width=sw), ax.plot(sc, x_range=[150, 800], color=ORANGE_L, stroke_width=sw))
    return ax.plot(lambda e: pk(e) + sc(e), x_range=[150, 800], color=color, stroke_width=sw)


def window_band(ax, h=1.15):
    return Rectangle(width=ax.c2p(WIN[1], 0)[0] - ax.c2p(WIN[0], 0)[0], height=ax.c2p(0, h)[1] - ax.c2p(0, 0)[1], fill_color=WHITE,
                     fill_opacity=0.1, stroke_color=WHITE, stroke_width=1).move_to(ax.c2p(WIN[0], 0), aligned_edge=DL)


def live(label, fn, color, fs=28):
    t = Tex(label, font_size=fs - 4, color=GREY_B)
    v = DecimalNumber(fn() * 100, num_decimal_places=0, unit=r"\%", font_size=fs, color=color)
    v.add_updater(lambda m: m.set_value(fn() * 100))
    return VGroup(t, v).arrange(RIGHT, buff=0.15)


def ring_pts(c, R, nd, phase=0.0):
    return [c + R * np.array([np.cos(a), np.sin(a), 0]) for a in np.arange(nd) * TAU / nd + phase]


class EnergyWhy(Narrated):
    def construct(self):
        title = Tex(r"energy: why calibrate", font_size=34).to_edge(UP, buff=0.35)
        pat = Ellipse(width=2.2, height=1.4, fill_color=GREY_D, fill_opacity=0.5, stroke_color=GREY_B).move_to(LEFT * 4.6 + DOWN * 0.2)
        pl = Tex(r"patient", font_size=22, color=GREY_B).next_to(pat, DOWN, buff=0.1)
        det = VGroup(*[Rectangle(width=0.5, height=0.3, fill_color=XTAL_C, fill_opacity=0.35, stroke_color=XTAL_C, stroke_width=1.5)
                       for _ in range(6)]).arrange(DOWN, buff=0.03).move_to(LEFT * 1.6 + DOWN * 0.2)
        src = pat.get_center() + LEFT * 0.4
        straight = Arrow(src, det[2].get_left(), buff=0, color=GOOD_C, stroke_width=4, max_tip_length_to_length_ratio=0.08)
        kink = pat.get_center() + RIGHT * 0.5 + UP * 0.35
        sc1, sc2 = Line(src, kink, color=ORANGE_L, stroke_width=4), Arrow(kink, det[0].get_left(), buff=0, color=ORANGE_L, stroke_width=4,
                                                                           max_tip_length_to_length_ratio=0.15)
        lab = VGroup(Tex(r"\textbf{511 keV}", font_size=22, color=GOOD_C).next_to(straight, DOWN, buff=0.08),
                     Tex(r"$<$511, wrong line", font_size=22, color=ORANGE_L).next_to(sc2, UP, buff=0.1))
        ax = Axes(x_range=[150, 800, 100], y_range=[0, 1.2, 0.5], x_length=6.0, y_length=3.0, tips=False,
                  axis_config={"color": GREY_B, "font_size": 20}, x_axis_config={"numbers_to_include": [200, 400, 600, 800]},
                  y_axis_config={"include_ticks": False}).move_to(RIGHT * 3.4 + UP * 0.3)
        axl = Tex(r"energy (keV)", font_size=20, color=GREY_B).next_to(ax, DOWN, buff=0.12)
        pk0, sc0 = spec_curve(ax, 1.0, parts=True)
        g = ValueTracker(1.0)
        total = always_redraw(lambda: spec_curve(ax, g.get_value()))
        win = window_band(ax)
        wl = Tex(r"window \textbf{408--613}", font_size=22).next_to(win, UP, buff=0.05)
        nums = VGroup(live(r"photopeak kept", lambda: peak_kept(g.get_value()), GOOD_C),
                      live(r"scatter accepted", lambda: scatter_in(g.get_value()), ORANGE_L)).arrange(DOWN, aligned_edge=RIGHT, buff=0.15)
        nums.next_to(ax, DOWN, buff=0.55)
        gain = VGroup(Tex(r"this crystal's gain", font_size=24), DecimalNumber(1.0, num_decimal_places=2, font_size=30, color=YELLOW))
        gain[1].add_updater(lambda m: m.set_value(g.get_value()))
        gain.arrange(RIGHT, buff=0.2).next_to(det, DOWN, buff=0.6)
        note = Tex(r"spectrum shape illustrative; window from DeepBreast", font_size=18, color=GREY_B).to_corner(DL, buff=0.15)
        with self.voiceover(text="Why does energy need calibrating at all? <bookmark mark='u'/>A photon that leaves the patient "
                                 "untouched arrives with five hundred and eleven keV. <bookmark mark='s'/>One that scatters in the "
                                 "patient changes direction and loses energy, so the line it implies is wrong. <bookmark mark='p'/>In "
                                 "the spectrum, the clean photons form the photopeak, <bookmark mark='c'/>the scattered ones a broad "
                                 "hump below it. <bookmark mark='w'/>An energy window keeps the peak and rejects much of the hump; "
                                 "DeepBreast uses four hundred and eight to six hundred and thirteen keV. <bookmark mark='g'/>But the "
                                 "window is applied to a signal, and each crystal turns energy into signal with its own gain. "
                                 "<bookmark mark='d'/>If this crystal's gain is a quarter too low, its photopeak slides down "
                                 "<bookmark mark='k'/>and most of its good events fall outside the window. <bookmark mark='h'/>A "
                                 "quarter too high, and the peak overshoots while scatter slides in. So every crystal's signal has to "
                                 "be mapped to keV first."):
            self.play(Write(title), FadeIn(pat), FadeIn(pl), FadeIn(det), run_time=1.0)
            self.at("u", GrowArrow(straight), FadeIn(lab[0]))
            self.at("s", Create(sc1), GrowArrow(sc2), FadeIn(lab[1]), run_time=1.0)
            self.at("p", Create(ax), FadeIn(axl), Create(pk0), Indicate(straight, color=GOOD_C))
            self.at("c", Create(sc0), Indicate(VGroup(sc1, sc2), color=ORANGE_L))
            self.at("w", FadeIn(win), FadeIn(wl), FadeIn(note))
            self.wait_until_bookmark("g")
            self.play(FadeOut(pk0), FadeOut(sc0), FadeIn(total), FadeIn(gain), Indicate(det[2], color=YELLOW), FadeIn(nums))
            self.at("d", g.animate.set_value(0.75), run_time=2.0)
            self.at("k", Circumscribe(nums[0], color=GOOD_C))
            self.at("h", g.animate.set_value(1.25), run_time=2.5)
            self.play(Circumscribe(nums[1], color=ORANGE_L))
            self.play(g.animate.set_value(1.0), run_time=1.0)
        self.wait(0.5)
        fade_all(self)


class EnergyHow(Narrated):
    def construct(self):
        title = Tex(r"energy: how", font_size=34).to_edge(UP, buff=0.35)
        rng = np.random.default_rng(7)
        lut = VGroup(*[Square(0.34, stroke_color=GREY_B, stroke_width=1, fill_color=XTAL_C, fill_opacity=0.12) for _ in range(64)]).arrange_in_grid(8, 8, buff=0.02)
        lut.move_to(LEFT * 4.4 + DOWN * 0.2)
        ll = Tex(r"crystal lookup table", font_size=22).next_to(lut, UP, buff=0.15)
        picks, gains, cols = [9, 27, 36, 54], [0.8, 0.94, 1.07, 1.22], [ORANGE_L, YELLOW, GOOD_C, BLUE_L]
        rings = VGroup(*[SurroundingRectangle(lut[k], buff=0.0, color=c, stroke_width=4) for k, c in zip(picks, cols)])
        n_ev = 4000
        samples = []
        for gn in gains:
            pk = rng.normal(511 * gn, 0.12 * 511 * gn / 2.3548, int(n_ev * 0.65))
            co = rng.uniform(60, 340 * gn, n_ev - pk.size)
            samples.append(rng.permutation(np.concatenate([pk, co])))
        N = ValueTracker(10)
        a = ValueTracker(0.0)                                  # 0: raw signal, 1: after the per-crystal factor
        bins = np.linspace(100, 800, 36)
        panels = VGroup()
        axes = []
        for k in range(4):
            ax = Axes(x_range=[100, 800, 100], y_range=[0, 1.1, 0.5], x_length=3.0, y_length=1.3, tips=False,
                      axis_config={"color": GREY_B, "include_ticks": False})
            axes.append(ax)
            panels.add(ax)
        panels.arrange_in_grid(2, 2, buff=(0.6, 0.55)).move_to(RIGHT * 2.0 + DOWN * 0.3)
        hmax = [np.histogram(s, bins)[0].max() for s in samples]

        def hist(k):
            ax, s, gn = axes[k], samples[k], gains[k]
            f = 1 + (1 / gn - 1) * a.get_value()
            h, _ = np.histogram(s[:int(N.get_value())] * f, bins)
            w = ax.c2p(bins[1], 0)[0] - ax.c2p(bins[0], 0)[0]
            return VGroup(*[Rectangle(width=w * 0.9, height=max(ax.c2p(0, v / hmax[k])[1] - ax.c2p(0, 0)[1], 0.001), fill_color=cols[k],
                                      fill_opacity=0.85, stroke_width=0).move_to(ax.c2p((b0 + b1) / 2, 0), aligned_edge=DOWN)
                            for v, b0, b1 in zip(h, bins[:-1], bins[1:])])

        hists = VGroup(*[always_redraw(lambda k=k: hist(k)) for k in range(4)])
        found = [bins[np.argmax(np.histogram(s, bins)[0])] + (bins[1] - bins[0]) / 2 for s in samples]
        fac = [511 / p for p in found]
        marks = VGroup(*[DashedLine(axes[k].c2p(found[k], 0), axes[k].c2p(found[k], 1.1), color=WHITE) for k in range(4)])
        flabs = VGroup(*[Tex(r"$\times$\textbf{%.2f}" % fac[k], font_size=24, color=cols[k]).next_to(axes[k], UP, buff=0.05).align_to(axes[k], RIGHT)
                         for k in range(4)])
        l511 = VGroup(*[DashedLine(ax.c2p(511, 0), ax.c2p(511, 1.1), color=YELLOW, stroke_width=2) for ax in axes])
        table = VGroup(*[Tex(r"$\times$%.2f" % (511 / (511 * gn) * rng.uniform(0.98, 1.02) if k not in picks else fac[picks.index(k)]),
                             font_size=12, color=GREY_A).move_to(lut[k]) for k, gn in enumerate(rng.uniform(0.8, 1.2, 64))])
        tl = Tex(r"one factor per crystal, applied to every event", font_size=24).to_edge(DOWN, buff=0.35)
        src = VGroup(icon_flood(0.8), Tex(r"same uniform data", font_size=22, color=GOOD_C)).arrange(RIGHT, buff=0.15).next_to(ll, UP, buff=0.2)
        with self.voiceover(text="So how is it done? <bookmark mark='s'/>Reuse the same uniform acquisition that made the flood map. "
                                 "<bookmark mark='l'/>The crystal lookup table sends every event to its crystal, <bookmark mark='h'/>and "
                                 "each crystal fills its own spectrum. <bookmark mark='p'/>Software finds each photopeak, "
                                 "<bookmark mark='f'/>and computes one factor per crystal, five hundred and eleven over the peak "
                                 "position. <bookmark mark='a'/>Applied, the factors pull every peak onto five hundred and eleven. "
                                 "<bookmark mark='t'/>They are stored in a table, one entry per crystal, and used on every event from "
                                 "then on."):
            self.play(Write(title), run_time=0.8)
            self.at("s", FadeIn(src))
            self.at("l", FadeIn(lut), FadeIn(ll), Create(rings))
            self.wait_until_bookmark("h")
            self.add(hists)
            self.play(FadeIn(panels), N.animate.set_value(n_ev), run_time=3.0, rate_func=rate_functions.ease_in_quad)
            self.at("p", Create(marks))
            self.at("f", LaggedStart(*[FadeIn(f_) for f_ in flabs], lag_ratio=0.2), FadeIn(l511))
            self.at("a", a.animate.set_value(1.0), FadeOut(marks), run_time=2.0)
            self.at("t", FadeIn(table), FadeIn(tl), Indicate(lut, color=YELLOW, scale_factor=1.02))
        self.wait(0.5)
        fade_all(self)


class Drift(Narrated):
    def construct(self):
        title = Tex(r"why it is not done once: drift", font_size=34).to_edge(UP, buff=0.35)
        T = ValueTracker(0.0)                                  # temperature change (illustrative units)
        gfun = lambda: 1 - 0.05 * T.get_value()
        therm = VGroup(RoundedRectangle(corner_radius=0.12, width=0.3, height=2.4, stroke_color=GREY_B), Circle(radius=0.25, color=GREY_B))
        therm[1].next_to(therm[0], DOWN, buff=-0.1)
        therm.move_to(LEFT * 5.4 + DOWN * 0.1)
        fill = always_redraw(lambda: VGroup(Rectangle(width=0.18, height=0.6 + 0.35 * T.get_value(), fill_color=BAD_C, fill_opacity=1, stroke_width=0)
                                            .move_to(therm[1].get_center() + UP * 0.15, aligned_edge=DOWN),
                                            Circle(radius=0.18, fill_color=BAD_C, fill_opacity=1, stroke_width=0).move_to(therm[1])))
        sipm = VGroup(Rectangle(width=1.4, height=0.5, fill_color=SIPM_C, fill_opacity=0.8, stroke_width=0), Tex(r"SiPM", font_size=22))
        sipm.next_to(therm, RIGHT, buff=0.6).shift(UP * 0.3)
        gain = VGroup(Tex(r"gain", font_size=24), DecimalNumber(1.0, num_decimal_places=2, font_size=28, color=YELLOW)).arrange(RIGHT, buff=0.15)
        gain[1].add_updater(lambda m: m.set_value(gfun()))
        gain.next_to(sipm, DOWN, buff=0.25)
        ax = Axes(x_range=[150, 800, 100], y_range=[0, 1.2, 0.5], x_length=5.6, y_length=2.6, tips=False,
                  axis_config={"color": GREY_B, "font_size": 20}, x_axis_config={"numbers_to_include": [200, 400, 600, 800]},
                  y_axis_config={"include_ticks": False}).move_to(RIGHT * 2.8 + UP * 0.7)
        curve = always_redraw(lambda: spec_curve(ax, gfun()))
        win = window_band(ax)
        kept = live(r"photopeak kept", lambda: peak_kept(gfun()), GOOD_C).next_to(ax, DOWN, buff=0.3)
        illus = Tex(r"illustrative gain change", font_size=18, color=GREY_B).to_corner(DL, buff=0.15)
        led = VGroup(Circle(radius=0.16, color=LIGHT_C, fill_opacity=0.8), Tex(r"LED re-tunes PMT gains (1986)", font_size=22)).arrange(RIGHT, buff=0.15)
        fixes = VGroup(tile(VGroup(Square(0.4, color=BLUE_L, fill_opacity=0.3), Tex(r"$\ast$", font_size=40, color=BLUE_L)), r"Peltier: $\pm$\textbf{0.5}\,$^\circ$C", 3.4),
                       tile(VGroup(therm.copy().scale(0.25)), r"held at \textbf{26 $\pm$ 0.4}\,$^\circ$C", 3.4),
                       tile(VGroup(Circle(radius=0.25, color=GREY_A), Line(ORIGIN, UP * 0.18, color=GREY_A), Line(ORIGIN, RIGHT * 0.13, color=GREY_A)),
                            r"recalibrate regularly", 3.4)).arrange(RIGHT, buff=0.25).to_edge(DOWN, buff=1.25)
        cites = VGroup(*[Tex(t, font_size=16, color=GREY_B).next_to(f_, DOWN, buff=0.06) for t, f_ in
                         zip(("Krishnamoorthy 2018", "Kang 2023", "Karlberg 2016: per manufacturer"), fixes)])
        lu = VGroup(*[Square(0.18, fill_color=XTAL_C, fill_opacity=0.35, stroke_width=0.5) for _ in range(16)]).arrange_in_grid(4, 4, buff=0.02)
        sparks = VGroup(*[Dot(lu.get_center() + np.array([rng_x, rng_y, 0]), radius=0.04, color=YELLOW) for rng_x, rng_y in
                          np.random.default_rng(3).uniform(-0.35, 0.35, (10, 2))])
        lug = VGroup(lu, sparks)
        lut_ = VGroup(lug, Tex(r"$^{176}$Lu background: a built-in source,\\\textbf{30 min}, no external source (Kuang 2026)", font_size=22)).arrange(RIGHT, buff=0.3)
        lut_.to_edge(DOWN, buff=0.25)
        with self.voiceover(text="Why repeat it? <bookmark mark='g'/>Because gains do not stay put. <bookmark mark='p'/>The first block "
                                 "detector already had an LED to re-tune its four tubes as they drifted. <bookmark mark='t'/>Silicon "
                                 "photomultiplier gain depends on temperature, <bookmark mark='d'/>so as the detector warms, its "
                                 "photopeak walks <bookmark mark='o'/>and good events leave the window again. <bookmark mark='c'/>So "
                                 "scanners hold their sensors steady: one preclinical system keeps each detector within half a degree "
                                 "with Peltier coolers, <bookmark mark='k'/>another holds its sensors at twenty six plus or minus zero "
                                 "point four degrees. <bookmark mark='r'/>Whatever drift remains is caught by recalibrating on a "
                                 "regular basis, as the manufacturer recommends. <bookmark mark='l'/>Lutetium based crystals even carry "
                                 "their own source: the natural radioactivity of lutetium one seven six, which one group used for a "
                                 "thirty minute calibration with nothing placed in the scanner."):
            self.play(Write(title), Create(ax), FadeIn(win), FadeIn(curve), FadeIn(kept), run_time=1.0)
            self.at("g", FadeIn(sipm), FadeIn(gain))
            self.at("p", FadeIn(led.next_to(ax, UP, buff=0.15)))
            self.at("t", FadeOut(led), FadeIn(therm), FadeIn(fill), Indicate(sipm, color=SIPM_C), FadeIn(illus))
            self.at("d", T.animate.set_value(5.0), run_time=3.0)
            self.at("o", Circumscribe(kept, color=GOOD_C))
            self.at("c", T.animate.set_value(0.0), FadeIn(fixes[0]), FadeIn(cites[0]), run_time=1.2)
            self.at("k", FadeIn(fixes[1]), FadeIn(cites[1]))
            self.at("r", FadeIn(fixes[2]), FadeIn(cites[2]))
            self.at("l", FadeIn(lut_), LaggedStart(*[Flash(s_, color=YELLOW, line_length=0.08, flash_radius=0.08) for s_ in sparks], lag_ratio=0.1),
                    run_time=1.5)
        self.wait(0.5)
        fade_all(self)


class TimingWhy(Narrated):
    def construct(self):
        title = Tex(r"timing: why calibrate", font_size=34).to_edge(UP, buff=0.35)
        L = 10.0                                               # screen units for a 60 cm line of response
        cm = L / 60
        a_, b_ = LEFT * 5 + UP * 0.4, RIGHT * 5 + UP * 0.4
        dA = Rectangle(width=0.3, height=0.8, fill_color=XTAL_C, fill_opacity=0.5, stroke_color=XTAL_C).move_to(a_)
        dB = dA.copy().move_to(b_)
        lor = DashedLine(a_, b_, color=GREY_B)
        x0 = -9.0                                               # annihilation 9 cm left of centre
        s = Dot(ORIGIN + UP * 0.4 + RIGHT * x0 * cm, color=YELLOW)
        pA, pB = Dot(s.get_center(), radius=0.06, color=GOOD_C), Dot(s.get_center(), radius=0.06, color=GOOD_C)
        dt = Tex(r"$\Delta t \to \Delta x = c\,\Delta t/2$: \textbf{100 ps = 1.5 cm}", font_size=28).to_edge(DOWN, buff=1.6)
        off = ValueTracker(0.0)                                 # ps added to detector B
        fwhm_cm = 300 * 0.03 / 2                                # 300 ps kernel -> 4.5 cm FWHM
        sig = fwhm_cm / 2.3548

        def kern():
            mu = x0 + off.get_value() * 0.03 / 2
            pts = [np.array([x * cm, 0.4 + 1.6 * np.exp(-(x - mu) ** 2 / (2 * sig ** 2)), 0]) for x in np.linspace(mu - 4 * sig, mu + 4 * sig, 60)]
            return VMobject(color=SEMI_C, stroke_width=4).set_points_smoothly(pts)

        k = always_redraw(kern)
        kl = Tex(r"TOF kernel, 300 ps", font_size=22, color=SEMI_C).next_to(s, UP, buff=1.75)
        clockB = VGroup(Circle(radius=0.28, color=BAD_C, stroke_width=3), Line(ORIGIN, UP * 0.2, color=BAD_C, stroke_width=3))
        clockB.next_to(dB, DOWN, buff=0.3)
        cl = Tex(r"hidden delay", font_size=22, color=BAD_C).next_to(clockB, DOWN, buff=0.1)
        shift = VGroup(Tex(r"shift", font_size=24, color=GREY_B), DecimalNumber(0, num_decimal_places=1, font_size=28, color=BAD_C), Tex(r"cm", font_size=24))
        shift[1].add_updater(lambda m: m.set_value(off.get_value() * 0.03 / 2))
        shift.arrange(RIGHT, buff=0.12).next_to(cl, LEFT, buff=1.2)
        truth = DashedLine(s.get_center(), s.get_center() + UP * 1.8, color=YELLOW, stroke_width=2)
        bars = VGroup(*[VGroup(Rectangle(width=4.5 * v / 520, height=0.42, fill_color=c, fill_opacity=0.9, stroke_width=0), Tex(l_, font_size=22),
                               Tex(r"\textbf{%d ps}" % v, font_size=24)) for v, c, l_ in ((412, SEMI_C, "per line, averaged"), (505, BAD_C, "whole scanner"))])
        for i, b in enumerate(bars):
            b[0].move_to(np.array([0.5, -2.2 - 0.6 * i, 0]), aligned_edge=LEFT)
            b[1].next_to(b[0], LEFT, buff=0.15)
            b[2].next_to(b[0], RIGHT, buff=0.1)
        bl = Tex(r"uEXPLORER: $>$500\,000 crystals, $\sim$$10^{11}$ lines (Spencer 2021)", font_size=22, color=GREY_B).next_to(bars, UP, buff=0.15)
        with self.voiceover(text="Timing next, and again the why first. <bookmark mark='l'/>The two photons from one annihilation fly "
                                 "in opposite directions <bookmark mark='d'/>and reach their detectors at slightly different times. "
                                 "<bookmark mark='t'/>That difference places the annihilation along the line: every hundred "
                                 "picoseconds is one and a half centimetres. <bookmark mark='k'/>With finite timing resolution the "
                                 "position is a blur, the time of flight kernel. <bookmark mark='o'/>Now give one detector a hidden "
                                 "delay of two hundred picoseconds, from a longer cable or a slower channel. <bookmark mark='s'/>The "
                                 "kernel slides three centimetres, and every event on this line lands in the wrong place. "
                                 "<bookmark mark='m'/>Across a whole scanner, unequal offsets also blur the timing resolution itself. "
                                 "The first total body scanner, with over half a million crystals, measured five hundred and five "
                                 "picoseconds as a whole <bookmark mark='a'/>against four hundred and twelve averaged line by line, "
                                 "which its authors put down to incomplete timing calibration."):
            self.play(Write(title), FadeIn(dA), FadeIn(dB), Create(lor), run_time=1.0)
            self.at("l", FadeIn(s, scale=2), FadeIn(pA), FadeIn(pB))
            self.at("d", pA.animate.move_to(a_), pB.animate.move_to(b_), run_time=1.0, rate_func=linear)
            self.at("t", FadeIn(dt))
            self.at("k", Create(k), FadeIn(kl), Create(truth))
            self.at("o", FadeIn(clockB), FadeIn(cl), FadeIn(shift), Indicate(dB, color=BAD_C))
            self.at("s", off.animate.set_value(200.0), run_time=2.0)
            self.at("m", FadeOut(dt), FadeIn(bl), GrowFromEdge(bars[1][0], LEFT), FadeIn(bars[1][1:]))
            self.at("a", GrowFromEdge(bars[0][0], LEFT), FadeIn(bars[0][1:]))
        self.wait(0.5)
        fade_all(self)


class TimingHow(Narrated):
    def construct(self):
        title = Tex(r"timing: how", font_size=34).to_edge(UP, buff=0.35)
        rng = np.random.default_rng(4)
        c, R, nd = LEFT * 3.4 + DOWN * 0.2, 2.0, 12
        offs = rng.normal(0, 1, nd)
        offs -= offs.mean()
        P = ring_pts(c, R, nd)
        dets = VGroup(*[Square(0.34, fill_color=XTAL_C, fill_opacity=0.4, stroke_color=XTAL_C).move_to(p) for p in P])
        hands = VGroup(*[Line(p, p + 0.24 * np.array([np.sin(TAU * o / 6), np.cos(TAU * o / 6), 0]), color=SEMI_C, stroke_width=3) for p, o in zip(P, offs)])
        src = Dot(c, color=YELLOW)
        sl = Tex(r"known source position", font_size=22, color=YELLOW).next_to(src, DOWN, buff=0.15)
        sl.add_background_rectangle(color=config.background_color, opacity=0.85)
        sl.set_z_index(3)
        i, j = 1, 7
        lor = Line(P[i], P[j], color=GOOD_C, stroke_width=3)
        ax = Axes(x_range=[-3, 3, 1], y_range=[0, 1.1, 0.5], x_length=4.4, y_length=1.8, tips=False,
                  axis_config={"color": GREY_B, "include_ticks": False}).move_to(RIGHT * 3.4 + UP * 1.3)
        axl = Tex(r"measured $\Delta t$ for this pair", font_size=22, color=GREY_B).next_to(ax, DOWN, buff=0.12)
        zero = DashedLine(ax.c2p(0, 0), ax.c2p(0, 1.1), color=WHITE)
        zl = Tex(r"expected: 0", font_size=20).next_to(zero, UP, buff=0.05)
        d_ij = offs[i] - offs[j]
        samp = rng.normal(d_ij, 0.45, 3000)
        Nn = ValueTracker(5)
        bins = np.linspace(-3, 3, 41)
        hm = np.histogram(samp, bins)[0].max()

        def hist():
            h = np.histogram(samp[:int(Nn.get_value())], bins)[0]
            w = ax.c2p(bins[1], 0)[0] - ax.c2p(bins[0], 0)[0]
            return VGroup(*[Rectangle(width=w * 0.9, height=max(ax.c2p(0, v / hm)[1] - ax.c2p(0, 0)[1], 0.001), fill_color=GOOD_C, fill_opacity=0.85,
                                      stroke_width=0).move_to(ax.c2p((a + b) / 2, 0), aligned_edge=DOWN) for v, a, b in zip(h, bins[:-1], bins[1:])])

        hb = always_redraw(hist)
        peak = DashedLine(ax.c2p(d_ij, 0), ax.c2p(d_ij, 1.1), color=SEMI_C)
        eq = MathTex(r"\Delta t_{ij} = o_i - o_j", font_size=36, color=SEMI_C).next_to(axl, DOWN, buff=0.3)
        pairs = [(a, b) for a in range(nd) for b in range(nd) if a < b and (b - a) % nd in range(3, 10)]
        many = VGroup(*[Line(P[a], P[b], color=GOOD_C, stroke_width=1, stroke_opacity=0.5) for a, b in pairs])
        A = np.zeros((len(pairs) + 1, nd))
        bvec = np.zeros(len(pairs) + 1)
        for r_, (a, b) in enumerate(pairs):
            A[r_, a], A[r_, b], bvec[r_] = 1, -1, offs[a] - offs[b] + rng.normal(0, 0.05)
        A[-1] = 1
        est = np.linalg.lstsq(A, bvec, rcond=None)[0]
        cnt = Tex(r"\textbf{%d} pairs, \textbf{%d} unknowns $\to$ least squares" % (len(pairs), nd), font_size=24).next_to(eq, DOWN, buff=0.3)
        base_y, x_0 = -2.6, 0.8
        bars = VGroup()
        for k_ in range(nd):
            t_ = Rectangle(width=0.14, height=abs(offs[k_]) * 0.35 + 0.01, fill_color=SEMI_C, fill_opacity=0.9, stroke_width=0)
            e_ = Rectangle(width=0.14, height=abs(est[k_]) * 0.35 + 0.01, fill_color=WHITE, fill_opacity=0.9, stroke_width=0)
            t_.move_to(np.array([x_0 + k_ * 0.42, base_y, 0]), aligned_edge=DOWN if offs[k_] > 0 else UP)
            e_.move_to(np.array([x_0 + k_ * 0.42 + 0.16, base_y, 0]), aligned_edge=DOWN if est[k_] > 0 else UP)
            bars.add(VGroup(t_, e_))
        bl = VGroup(Tex(r"true", font_size=20, color=SEMI_C), Tex(r"solved", font_size=20)).arrange(DOWN, aligned_edge=LEFT, buff=0.08).next_to(bars, RIGHT, buff=0.2)
        laser = VGroup(Polygon(ORIGIN, RIGHT * 0.5 + UP * 0.12, RIGHT * 0.5 + DOWN * 0.12, color=BAD_C, fill_opacity=0.8),
                       Tex(r"first: electronic skews with a pulsed laser (Borghi 2016)", font_size=22)).arrange(RIGHT, buff=0.2).to_edge(DOWN, buff=0.25)
        with self.voiceover(text="How are the offsets found? <bookmark mark='s'/>Place a source whose position is known, here at the "
                                 "centre, <bookmark mark='z'/>so both photons of every pair travel the same distance and every true time "
                                 "difference is zero. <bookmark mark='h'/>For one pair of detectors, histogram the measured "
                                 "differences. <bookmark mark='o'/>The peak sits not at zero but at the difference of their two hidden "
                                 "offsets. <bookmark mark='m'/>Every pair gives one such equation, <bookmark mark='q'/>and with many "
                                 "more pairs than detectors, a least squares fit recovers every offset. <bookmark mark='a'/>Subtract "
                                 "them, and every clock agrees. <bookmark mark='c'/>The cost is counts: each pair needs enough "
                                 "coincidences to place its peak, and the number of pairs grows with the square of the number of "
                                 "crystals. <bookmark mark='l'/>Some groups first remove the purely electronic skews with a pulsed "
                                 "laser, before any gamma rays are involved."):
            self.play(Write(title), FadeIn(dets), Create(hands), run_time=1.0)
            self.at("s", FadeIn(src, scale=2), FadeIn(sl))
            self.at("z", Create(lor), Indicate(dets[i], color=GOOD_C), Indicate(dets[j], color=GOOD_C), Create(ax), Create(zero), FadeIn(zl))
            self.wait_until_bookmark("h")
            self.add(hb)
            self.play(FadeIn(axl), Nn.animate.set_value(3000), run_time=2.5, rate_func=rate_functions.ease_in_quad)
            self.at("o", Create(peak), Indicate(hands[i], color=SEMI_C), Indicate(hands[j], color=SEMI_C))
            self.at("m", Write(eq))
            self.at("q", Create(many), FadeIn(cnt), run_time=1.2)
            self.play(LaggedStart(*[FadeIn(b_, shift=0.05 * UP) for b_ in bars], lag_ratio=0.05), FadeIn(bl), run_time=1.0)
            self.at("a", *[h_.animate.put_start_and_end_on(p, p + UP * 0.24) for h_, p in zip(hands, P)], run_time=1.2)
            self.at("c", Indicate(many, color=YELLOW, scale_factor=1.0))
            self.at("l", FadeIn(laser))
        self.wait(0.5)
        fade_all(self)


def backproject(nd=48, n=64, seed=5, spread=0.15, norm=False):
    """Uniform disk in a ring of nd crystals with efficiencies eff: backproject measured/expected counts per LOR
    (noise-free), averaged over the lines through each pixel. Without normalisation the efficiency pattern shows."""
    rng = np.random.default_rng(seed)
    eff = np.clip(rng.normal(1, spread, nd), 0.6, 1.4)
    ang = np.arange(nd) * TAU / nd
    P = np.stack([np.cos(ang), np.sin(ang)], 1)
    img, w = np.zeros((n, n)), np.zeros((n, n))
    t = np.linspace(0, 1, 400)
    for i in range(nd):
        for j in range(i + 1, nd):
            pts = P[i][None] * (1 - t[:, None]) + P[j][None] * t[:, None]
            inside = (pts ** 2).sum(1) < 0.6 ** 2
            if inside.sum() < 3:
                continue
            r = 1.0 if norm else eff[i] * eff[j]
            ix = ((pts[inside] + 1) / 2 * (n - 1)).round().astype(int)
            u = np.unique((n - 1 - ix[:, 1]) * n + ix[:, 0])
            img.flat[u] += r
            w.flat[u] += 1
    yy, xx = np.mgrid[0:n, 0:n]
    disk = ((xx - (n - 1) / 2) ** 2 + (yy - (n - 1) / 2) ** 2) < (0.58 * (n - 1) / 2) ** 2
    return np.where(disk & (w > 0), img / np.maximum(w, 1), np.nan), eff


def fixed_heat(a, width, lo=0.8, hi=1.1):
    v = np.clip((np.nan_to_num(a, nan=lo) - lo) / (hi - lo), 0, 1)
    rgb = cmap(v)
    alpha = np.where(np.isnan(a), 0.0, 1.0)[..., None]
    im = ImageMobject((np.concatenate([rgb, alpha], -1) * 255).astype(np.uint8))
    im.set_resampling_algorithm(RESAMPLING_ALGORITHMS["nearest"])
    return im.set_width(width)


class NormWhy(Narrated):
    def construct(self):
        title = Tex(r"normalisation: why", font_size=34).to_edge(UP, buff=0.35)
        nd = 48
        raw, eff = backproject(nd=nd)
        flat, _ = backproject(nd=nd, norm=True)
        c, R = LEFT * 3.6 + DOWN * 0.3, 2.3
        P = ring_pts(c, R, nd)
        dets = VGroup(*[Square(0.2, fill_color=XTAL_C, fill_opacity=float(np.clip((e - 0.6) / 0.8, 0.1, 1)), stroke_width=0).move_to(p).rotate(a)
                        for p, e, a in zip(P, eff, np.arange(nd) * TAU / nd)])
        disk = Circle(radius=0.6 * R, fill_color=GOOD_C, fill_opacity=0.25, stroke_color=GOOD_C).move_to(c)
        dl = Tex(r"uniform cylinder", font_size=22, color=GOOD_C).move_to(c)
        ws = sorted(range(nd), key=lambda k: eff[k])
        weak = next((a, b) for a in ws[:8] for b in ws[:8] if 12 <= (b - a) % nd <= 36)
        strong = next((a, b) for a in ws[::-1][:8] for b in ws[::-1][:8] if 12 <= (b - a) % nd <= 36)
        lw, ls = Line(P[weak[0]], P[weak[1]], color=BAD_C, stroke_width=4), Line(P[strong[0]], P[strong[1]], color=GOOD_C, stroke_width=4)
        cw = Tex(r"weak pair: counts $\times$\textbf{%.2f}" % (eff[weak[0]] * eff[weak[1]]), font_size=24, color=BAD_C)
        cs = Tex(r"strong pair: counts $\times$\textbf{%.2f}" % (eff[strong[0]] * eff[strong[1]]), font_size=24, color=GOOD_C)
        VGroup(cw, cs).arrange(DOWN, aligned_edge=LEFT, buff=0.12).to_corner(UL, buff=0.3).shift(DOWN * 0.55)
        el = Tex(r"crystal efficiency: shade", font_size=22, color=GREY_B).next_to(VGroup(*dets), DOWN, buff=0.2)
        im_raw = fixed_heat(raw, 3.4).move_to(RIGHT * 1.6 + DOWN * 0.3)
        im_flat = fixed_heat(flat, 3.4).move_to(RIGHT * 5.0 + DOWN * 0.3)
        il = VGroup(Tex(r"lines treated as equal", font_size=22).next_to(im_raw, UP, buff=0.15),
                    Tex(r"each line $\div$ its efficiency", font_size=22).next_to(im_flat, UP, buff=0.15))
        cbar = VGroup(*[Rectangle(width=0.25, height=0.07, fill_color=ManimColor.from_rgb(cmap(np.array(v))), fill_opacity=1, stroke_width=0)
                        for v in np.linspace(0, 1, 30)]).arrange(UP, buff=0).next_to(im_flat, RIGHT, buff=0.15)
        cbl = VGroup(Tex(r"0.8", font_size=18).next_to(cbar, DOWN, buff=0.05), Tex(r"1.1", font_size=18).next_to(cbar, UP, buff=0.05))
        note = Tex(r"computed here: 48 crystals, efficiency $\pm$15\%, backprojection of measured/expected", font_size=18, color=GREY_B).to_corner(DL, buff=0.15)
        fit_frame(Group(im_flat, cbar, cbl))
        with self.voiceover(text="Last, normalisation, and again why. <bookmark mark='u'/>Image a perfectly uniform cylinder. "
                                 "<bookmark mark='e'/>Each crystal has its own efficiency, shown here by its shade, <bookmark mark='w'/>so "
                                 "a line between two weak crystals records fewer counts <bookmark mark='s'/>than a line between two "
                                 "strong ones, for exactly the same activity. <bookmark mark='r'/>Backproject the counts as if every line "
                                 "were equal, and the uniform cylinder comes out patterned: the efficiencies are printed into the image. "
                                 "<bookmark mark='n'/>Divide each line by its own efficiency, and it is flat again."):
            self.play(Write(title), run_time=0.8)
            self.at("u", FadeIn(disk), FadeIn(dl))
            self.at("e", LaggedStart(*[FadeIn(d_) for d_ in dets], lag_ratio=0.02), FadeIn(el), run_time=1.2)
            self.at("w", FadeOut(dl), Create(lw), FadeIn(cw), *[Indicate(dets[k], color=BAD_C, scale_factor=1.6) for k in weak])
            self.at("s", Create(ls), FadeIn(cs), *[Indicate(dets[k], color=GOOD_C, scale_factor=1.6) for k in strong])
            self.at("r", FadeIn(im_raw), FadeIn(il[0]), FadeIn(note), FadeIn(cbar), FadeIn(cbl), run_time=1.0)
            self.at("n", FadeIn(im_flat), FadeIn(il[1]))
        self.wait(0.5)
        fade_all(self)


class NormHow(Narrated):
    def construct(self):
        title = Tex(r"normalisation: how, and why it is slow", font_size=34).to_edge(UP, buff=0.35)
        nd = 24
        rng = np.random.default_rng(8)
        eff = np.clip(rng.normal(1, 0.15, nd), 0.6, 1.4)
        c, R = LEFT * 4.0 + DOWN * 0.4, 2.0
        P = ring_pts(c, R, nd)
        dets = VGroup(*[Square(0.26, fill_color=XTAL_C, fill_opacity=float(np.clip((e - 0.6) / 0.8, 0.1, 1)), stroke_width=1, stroke_color=XTAL_C)
                        .move_to(p) for p, e in zip(P, eff)])
        src = Circle(radius=0.6 * R, fill_color=GOOD_C, fill_opacity=0.2, stroke_color=GOOD_C).move_to(c)
        i = 3
        fan_idx = [j for j in range(nd) if 6 <= (j - i) % nd <= 18]
        fan = VGroup(*[Line(P[i], P[j], color=YELLOW, stroke_width=2, stroke_opacity=0.7) for j in fan_idx])
        eq = MathTex(r"\epsilon_i = \frac{C_i}{T_i}", font_size=40).move_to(RIGHT * 0.8 + UP * 1.6)
        eql = VGroup(Tex(r"$C_i$: counts summed over the fan", font_size=22), Tex(r"$T_i$: what the source predicts", font_size=22)).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        eql.next_to(eq, DOWN, buff=0.2)
        lor = MathTex(r"n_{ij} = \frac{1}{\epsilon_i\,\epsilon_j\,g_{ij}}", font_size=36).next_to(eql, DOWN, buff=0.35)
        ll = Tex(r"$g_{ij}$: geometry, shared by similar lines", font_size=20, color=GREY_B).next_to(lor, DOWN, buff=0.1)
        # unknowns and counts: crystals vs lines
        rows = [("here", 24, 276), ("total-body", 5e5, 1e11)]
        tab = VGroup()
        for k, (lab, nc, nl) in enumerate(rows):
            tab.add(VGroup(Tex(lab, font_size=24, color=GREY_A), Tex(r"\textbf{%s}" % (f"{nc:,.0f}" if nc < 1e4 else r"$5\times10^{5}$"), font_size=26, color=YELLOW),
                           Tex(r"\textbf{%s}" % (f"{nl:,.0f}" if nl < 1e4 else r"$\sim10^{11}$"), font_size=26, color=BAD_C)))
        head = VGroup(Tex(r"", font_size=22), Tex(r"crystals", font_size=22, color=YELLOW), Tex(r"lines", font_size=22, color=BAD_C))
        grid = VGroup(head, *tab)
        for r_, row in enumerate(grid):
            for c_, cell in enumerate(row):
                cell.move_to(np.array([3.3 + 1.6 * c_, 1.6 - 0.55 * r_, 0]))
        gl = Tex(r"unknowns", font_size=24).next_to(grid, UP, buff=0.2)
        counts = VGroup(Tex(r"1\% per factor $\Rightarrow$ $10^4$ counts each", font_size=24),
                        Tex(r"lines one by one: $\sim$\textbf{10$^{15}$} counts", font_size=24, color=BAD_C),
                        Tex(r"crystal fan sums: $\sim$\textbf{2.5$\times$10$^{9}$}", font_size=24, color=YELLOW),
                        Tex(r"computed here", font_size=18, color=GREY_B)).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        counts.next_to(grid, DOWN, buff=0.4).align_to(grid, LEFT)
        with self.voiceover(text="How are the efficiencies measured? <bookmark mark='a'/>Acquire a source that should give every line "
                                 "the same rate, <bookmark mark='i'/>pick one crystal, <bookmark mark='f'/>and add up the counts over its "
                                 "whole fan of lines to the far side. <bookmark mark='d'/>Divided by what the source geometry predicts, "
                                 "that sum is the crystal's efficiency. This is the fan sum method. <bookmark mark='p'/>A line's "
                                 "correction is then built from its two crystals' efficiencies and a geometric factor shared by similar "
                                 "lines. <bookmark mark='w'/>Why not measure every line directly? Count the unknowns. <bookmark mark='k'/>"
                                 "Here, twenty four crystals against two hundred and seventy six lines. <bookmark mark='x'/>In a total "
                                 "body scanner, half a million crystals against about a hundred billion lines. <bookmark mark='c'/>At "
                                 "one percent precision each factor needs ten thousand counts, <bookmark mark='l'/>so measuring lines "
                                 "one by one would take about ten to the fifteen counts, <bookmark mark='s'/>while crystal fan sums need "
                                 "a few billion."):
            self.play(Write(title), FadeIn(dets), run_time=0.8)
            self.at("a", FadeIn(src))
            self.at("i", Indicate(dets[i], color=YELLOW, scale_factor=1.8))
            self.at("f", LaggedStart(*[Create(l_) for l_ in fan], lag_ratio=0.08), run_time=1.2)
            self.at("d", Write(eq), FadeIn(eql))
            self.at("p", FadeIn(lor), FadeIn(ll))
            self.at("w", FadeOut(VGroup(eq, eql, lor, ll)), FadeIn(gl), FadeIn(head))
            self.at("k", FadeIn(tab[0]))
            self.at("x", FadeIn(tab[1]))
            self.at("c", FadeIn(counts[0]))
            self.at("l", FadeIn(counts[1]))
            self.at("s", FadeIn(counts[2]), FadeIn(counts[3]))
        self.wait(0.5)
        fade_all(self)


class Upkeep(Narrated):
    def construct(self):
        title = Tex(r"what it costs: reported acquisition times", font_size=32).to_edge(UP, buff=0.35)
        items = [(r"$^{176}$Lu background, position tables", 0.5, "Kuang 2026", SEMI_C),
                 (r"timing flood, per million events", 1.0, "Borghi 2016", SEMI_C),
                 (r"fan-beam position, per $\sim$2 cm detector", 2.5, "Borghi 2016", MONO_C),
                 (r"normalisation, ring phantom", 6.0, "Freire 2026", GOOD_C),
                 (r"energy + timing + normalisation, $^{22}$Na dome", 12.0, "Akamatsu 2022", ORANGE_L),
                 (r"whole-ring position, rotating fan", 86.4, "Freire 2026", MONO_C)]
        lo, hi = np.log10(0.3), np.log10(120)
        W = 6.0
        x0 = -0.6
        ax = NumberLine(x_range=[lo, hi, 1], length=W, include_ticks=False, color=GREY_B).move_to(np.array([x0 + W / 2, -2.75, 0]))
        ticks = VGroup()
        for v, lab in ((0.5, "30 min"), (1, "1 h"), (6, "6 h"), (24, "1 day"), (86.4, "3.6 days")):
            p = ax.n2p(np.log10(v))
            ticks.add(VGroup(Line(p + UP * 0.08, p + DOWN * 0.08, color=GREY_B), Tex(lab, font_size=18, color=GREY_B).next_to(p, DOWN, buff=0.12)))
        rows = VGroup()
        for k, (lab, h, cite, col) in enumerate(items):
            y = 1.9 - k * 0.72
            left = ax.n2p(lo)[0]
            b = Rectangle(width=ax.n2p(np.log10(h))[0] - left, height=0.42, fill_color=col, fill_opacity=0.85, stroke_width=0)
            b.move_to(np.array([left, y, 0]), aligned_edge=LEFT)
            t = Tex(lab, font_size=22).next_to(b.get_left(), LEFT, buff=0.15)
            c_ = Tex(cite, font_size=16, color=GREY_B).next_to(b, RIGHT, buff=0.1)
            rows.add(VGroup(b, t, c_))
        fit_frame(VGroup(rows, ax, ticks))
        reg = Tex(r"and repeated: ``on a regular basis according to manufacturer's recommendations'' (Karlberg 2016)", font_size=22, color=YELLOW).to_edge(DOWN, buff=0.2)
        with self.voiceover(text="So what does all this cost? Here are acquisition times reported in these papers, on a log scale. "
                                 "<bookmark mark='l'/>Thirty minutes of lutetium background built one scanner's position tables. "
                                 "<bookmark mark='t'/>About an hour per million events for the Delft timing flood. <bookmark mark='f'/>Two "
                                 "to three hours per detector for fan beam position calibration. <bookmark mark='n'/>Six hours for "
                                 "DeepBreast's normalisation phantom. <bookmark mark='a'/>Twelve hours for energy, timing and "
                                 "normalisation together, with one sodium source, on a hemispherical brain scanner. <bookmark mark='d'/>"
                                 "And three point six days for DeepBreast's position calibration. <bookmark mark='r'/>None of it is done "
                                 "once: clinical sites repeat detector calibration, timing alignment and normalisation on a regular basis "
                                 "as the manufacturer recommends, and again before any performance study."):
            self.play(Write(title), Create(ax), FadeIn(ticks), run_time=1.0)
            for k, m in enumerate("ltfnad"):
                self.at(m, GrowFromEdge(rows[k][0], LEFT), FadeIn(rows[k][1:]))
            self.at("r", FadeIn(reg))
        self.wait(0.5)
        fade_all(self)
