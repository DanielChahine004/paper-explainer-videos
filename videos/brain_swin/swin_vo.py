"""Explainer: 'Voxel-Level Brain States Prediction Using Swin Transformer' (Sun, Chahine, Wen, Liu, Li, Yuan,
Calamante, Lv; IEEE JBHI 29(12), 2025; CC BY 4.0).

Numbers are from the paper's text, Fig. 2(a) and Table I. Figures in assets/ are crops of the paper's
Figs. 2(b), 3 and 4(a), shown with attribution; the small coloured brain slices are illustrative.
Visuals are cued to the narration with <bookmark/> tags and self.at() (see ../DESIGN.md).
Render with render.sh, or one scene: manim -ql swin_vo.py Model
"""
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import *  # noqa: E402,F401

HERE = Path(__file__).resolve().parent
ENC_C, DEC_C, IN_C, OUT_C = "#4c8fe0", "#3fb27f", "#9aa4b2", "#f08a4b"
CITE = r"Sun \emph{et al.}, IEEE JBHI 2025 (CC BY 4.0)"

STEP_MSE = [0.007, 0.003, 0.003, 0.005, 0.008, 0.015, 0.028, 0.051, 0.089, 0.144]  # Fig. 2(a)
BEST = [("L", "SPL\\_1", "DorsAttn A", 0.0280), ("R", "IPL\\_1", "Cont B", 0.0282), ("R", "SPL\\_1", "DorsAttn A", 0.0286)]   # Table I
WORST = [("R", "OFC\\_1", "Limbic B", 0.0401), ("L", "OFC\\_1", "Limbic B", 0.0399), ("L", "TempPole\\_1", "Limbic A", 0.0398)]


def brain_slice(seed, size=40, smooth=2.2):
    """An illustrative BOLD-like slice: smoothed noise in a brain-shaped mask, blue-white-red."""
    rng = np.random.default_rng(seed)
    f = gaussian_filter(rng.standard_normal((size, size)), smooth)
    f /= np.abs(f).max() + 1e-9
    y, x = np.mgrid[-1:1:size * 1j, -1:1:size * 1j]
    mask = (x / 0.82) ** 2 + (y / 0.95) ** 2 < 1
    r = np.where(f > 0, 1.0, 1 + f)
    g = 1 - np.abs(f)
    b = np.where(f < 0, 1.0, 1 - f)
    img = np.stack([r, g, b], -1) * 255
    img[~mask] = [15, 17, 23]
    im = ImageMobject(img.astype(np.uint8))
    im.set_resampling_algorithm(RESAMPLING_ALGORITHMS["nearest"])
    return im


def volume(seed, h=0.9, color=IN_C):
    """A brain state: one slice in a thin frame."""
    s = brain_slice(seed).set_height(h)
    return Group(s, SurroundingRectangle(s, buff=0.02, color=color, stroke_width=2))


def card(path, h):
    """A paper figure on a white card."""
    im = ImageMobject(str(HERE / "assets" / path)).set_height(h)
    bg = RoundedRectangle(corner_radius=0.08, width=im.width + 0.2, height=im.height + 0.2, fill_color=WHITE, fill_opacity=1, stroke_width=0)
    return Group(bg.move_to(im), im)


BRAIN_BASE = np.array([0.80, 0.72, 0.68])   # neutral cortex tone
BOLD_POS, BOLD_NEG = np.array([0.86, 0.16, 0.16]), np.array([0.16, 0.36, 0.88])


def hemisphere(side):
    """A stylised hemisphere: ellipsoid with gyral folds, a temporal lobe bulging down at the side,
    a flattened underside and a flat medial wall with a fissure between the hemispheres."""
    def f(u, v):
        fold = 1 + 0.05 * np.sin(14 * u + 3 * np.sin(5 * v)) * np.sin(11 * v + 2 * np.sin(7 * u))
        x = 0.8 * np.sin(u) * np.cos(v) * fold
        y = 1.6 * np.cos(u) * fold
        z = 1.0 * np.sin(u) * np.sin(v) * fold
        temporal = 0.38 * np.exp(-((np.cos(u) - 0.1) / 0.32) ** 2) * max(0.0, -np.sin(v)) * abs(np.cos(v))
        z -= temporal
        x = side * (0.09 + np.abs(x) + 0.12 * temporal)
        if z < -0.5 and temporal < 0.05:
            z = -0.5 + 0.35 * (z + 0.5)        # flatter underside away from the temporal lobes
        return np.array([x, y, z])
    return Surface(f, u_range=[0.04, PI - 0.04], v_range=[0, TAU], resolution=(26, 38),
                   stroke_width=0.35, stroke_color="#6b5650", fill_opacity=1, checkerboard_colors=False)


def cerebellum():
    def f(u, v):
        fold = 1 + 0.06 * np.sin(22 * u)
        return np.array([0.78 * np.sin(u) * np.cos(v), -1.15 + 0.42 * np.cos(u), -0.62 + 0.36 * np.sin(u) * np.sin(v) * fold])
    return Surface(f, u_range=[0.05, PI - 0.05], v_range=[0, TAU], resolution=(10, 18),
                   stroke_width=0.35, stroke_color="#6b5650", fill_opacity=1, checkerboard_colors=False)


def bold_field(p, t):
    """Illustrative BOLD activity: a few blobs drifting over the cortex, in [-1, 1]."""
    v = 0.0
    for k, (a, w) in enumerate([(1.0, 0.7), (-1.0, 0.9), (0.8, 1.3), (-0.8, 0.5), (0.9, 1.1)]):
        c = np.array([0.9 * np.sin(w * t + 1.7 * k), 1.3 * np.cos(0.7 * w * t + k), 0.7 * np.sin(0.5 * w * t + 2.3 * k)])
        v += a * np.exp(-np.sum((p - c) ** 2) / 0.28)
    return np.tanh(1.6 * v)


class Opening(Narrated, ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=62 * DEGREES, theta=-55 * DEGREES, zoom=1.55)
        brain = VGroup(hemisphere(1), hemisphere(-1), cerebellum()).shift(0.15 * IN)
        faces = [f for h in brain for f in h]
        t = ValueTracker(0.0)

        def paint(m):
            for face in faces:
                v = bold_field(face.get_center(), t.get_value())
                col = BRAIN_BASE + (BOLD_POS - BRAIN_BASE if v > 0 else BOLD_NEG - BRAIN_BASE) * min(abs(v) * 1.15, 1)
                face.set_fill(rgb_to_color(col), opacity=1)

        paint(brain)
        title = Tex(r"Voxel-level brain state prediction\\with a Swin Transformer").scale(0.9).to_edge(UP, buff=0.3)
        auth = Tex(r"Y.\ Sun, D.\ Chahine, Q.\ Wen, T.\ Liu, X.\ Li, Y.\ Yuan, F.\ Calamante, J.\ Lv", color=GREY_B).scale(0.5)
        venue = Tex(r"IEEE Journal of Biomedical and Health Informatics, 2025", color=TEAL_L).scale(0.55)
        foot = VGroup(auth, venue).arrange(DOWN, buff=0.12).to_edge(DOWN, buff=0.35)
        ill = Tex("illustrative brain and activity", font_size=20, color=GREY_D).to_corner(DR, buff=0.15)
        self.add_fixed_in_frame_mobjects(title, foot, ill)
        self.remove(title, foot, ill)
        with self.voiceover(text="Can a neural network watch the resting brain for twenty three seconds, and predict what it does "
                                 "<bookmark mark='next'/>next, voxel by voxel? That's the question of this paper.") as tr:
            self.play(FadeIn(brain), Write(title), FadeIn(ill), run_time=1.5)
            brain.add_updater(paint)
            self.begin_ambient_camera_rotation(rate=0.22)
            self.play(t.animate.set_value(1.5), run_time=1.2, rate_func=linear)
            self.wait_until_bookmark("next")
            self.play(FadeIn(foot, shift=0.1 * UP), t.animate.set_value(2.2), run_time=0.8, rate_func=linear)
            self.play(t.animate.set_value(2.2 + 0.6 * tr.get_remaining_duration()), run_time=max(tr.get_remaining_duration(), 0.1), rate_func=linear)
        self.play(t.animate.set_value(t.get_value() + 1.5), run_time=1.5, rate_func=linear)
        brain.clear_updaters()
        self.stop_ambient_camera_rotation()
        self.play(FadeOut(brain), FadeOut(title), FadeOut(foot), FadeOut(ill))


class Intro(Narrated):
    def construct(self):
        head = Tex("A brain state = one fMRI volume").scale(0.75).to_edge(UP)
        tl = Arrow(6.3 * LEFT + 1.6 * DOWN, 6.3 * RIGHT + 1.6 * DOWN, buff=0, color=GREY_B, stroke_width=3, tip_length=0.2)
        tlab = Tex("time", font_size=28, color=GREY_B).next_to(tl, DOWN, buff=0.1).align_to(tl, RIGHT)
        vols = Group(*[volume(i, h=0.85) for i in range(12)]).arrange(RIGHT, buff=0.12).move_to(0.2 * UP)
        for k in range(9, 12):
            vols[k][1].set_color(OUT_C)
        tr = Tex(r"one every 0.72 s", font_size=28).next_to(VGroup(vols[0][1], vols[1][1]), DOWN, buff=0.25)
        inb = Brace(Group(*vols[:9]), UP, color=IN_C)
        inl = Tex(r"past: 32 states = 23.04 s", color=IN_C, font_size=30).next_to(inb, UP, buff=0.1)
        outb = Brace(Group(*vols[9:]), UP, color=OUT_C)
        outl = Tex(r"predict: next 10 = 7.2 s", color=OUT_C, font_size=30).next_to(outb, UP, buff=0.1)
        ill = Tex("slices illustrative", font_size=22, color=GREY_D).to_corner(DR, buff=0.2)
        with self.voiceover(text="Functional M R I measures the <bookmark mark='bold'/>BOLD signal, a blood oxygen proxy for neural "
                                 "activity, as a <bookmark mark='vol'/>three D volume of voxels, here <bookmark mark='tr'/>every zero "
                                 "point seven two seconds. The paper calls each volume a brain state."):
            self.play(Write(head), run_time=0.8)
            self.at("bold", Create(tl), FadeIn(tlab))
            self.at("vol", FadeIn(vols[0], scale=0.8), FadeIn(ill))
            self.at("tr", LaggedStart(*[FadeIn(v, shift=0.1 * RIGHT) for v in vols[1:9]], lag_ratio=0.15), FadeIn(tr), run_time=1.4)
        with self.voiceover(text="The model sees the last <bookmark mark='in'/>thirty two states, about twenty three seconds, and "
                                 "predicts the <bookmark mark='out'/>next ten, seven point two seconds into the future, at full voxel "
                                 "detail."):
            self.at("in", GrowFromCenter(inb), FadeIn(inl))
            self.at("out", LaggedStart(*[FadeIn(v, shift=0.1 * RIGHT) for v in vols[9:]], lag_ratio=0.2), GrowFromCenter(outb), FadeIn(outl), run_time=1.2)
        why = VGroup(Tex(r"$\bullet$ understand how brain states arise and evolve", font_size=28),
                     Tex(r"$\bullet$ shorter scans for patients who can't lie still", font_size=28),
                     Tex(r"$\bullet$ brain--computer interfaces", font_size=28)).arrange(DOWN, aligned_edge=LEFT, buff=0.12).to_edge(DOWN, buff=0.35)
        with self.voiceover(text="Why bother? To <bookmark mark='w1'/>understand how brain states unfold, to <bookmark mark='w2'/>shorten "
                                 "scans for patients who can't stay in the scanner, and one day for <bookmark mark='w3'/>brain computer "
                                 "interfaces."):
            self.play(FadeOut(tr), FadeOut(tlab), run_time=0.3)
            for k in range(3):
                self.at(f"w{k + 1}", FadeIn(why[k], shift=0.1 * RIGHT))
        fade_all(self)


class Data(Narrated):
    def construct(self):
        title = Tex(r"Data: the Human Connectome Project").scale(0.72).to_edge(UP)
        facts = VGroup(
            Tex(r"100 unrelated adults, aged 22--36 (54 F, 46 M)", font_size=30),
            Tex(r"2 resting scans each, 1200 time points, 2 mm voxels, TR 0.72 s", font_size=30),
            Tex(r"6 mm smoothing, 0.01--0.1 Hz band-pass, z-score per voxel", font_size=30),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.18).next_to(title, DOWN, buff=0.45)
        with self.voiceover(text="The data are resting state scans of <bookmark mark='sub'/>one hundred unrelated young adults from the "
                                 "Human Connectome Project, <bookmark mark='scan'/>two scans each, twelve hundred time points, two "
                                 "millimetre voxels. They are <bookmark mark='pre'/>smoothed, band pass filtered and z scored."):
            self.play(Write(title), run_time=0.8)
            for k, m in enumerate(["sub", "scan", "pre"]):
                self.at(m, FadeIn(facts[k], shift=0.1 * RIGHT))

        dims = VGroup(MathTex(r"91\times109\times91", font_size=40), MathTex(r"46\times54\times46", font_size=40),
                      MathTex(r"48\times48\times48", font_size=40, color=YELLOW))
        dims.arrange(RIGHT, buff=1.1).shift(0.5 * DOWN)
        arr = VGroup(*[Arrow(dims[i].get_right(), dims[i + 1].get_left(), buff=0.15, stroke_width=3, tip_length=0.15, color=GREY_B) for i in range(2)])
        al = VGroup(Tex(r"halve\\(cubic)", font_size=22, color=GREY_B).next_to(arr[0], UP, buff=0.08),
                    Tex(r"crop / pad", font_size=22, color=GREY_B).next_to(arr[1], UP, buff=0.08))
        mask = Tex(r"loss and metrics only inside each subject's brain mask", font_size=26, color=GREY_B).next_to(dims, DOWN, buff=0.35)
        with self.voiceover(text="Each volume, <bookmark mark='d0'/>ninety one by one oh nine by ninety one voxels, is "
                                 "<bookmark mark='d1'/>halved in each dimension, then <bookmark mark='d2'/>cropped or padded to a "
                                 "forty eight voxel cube. Only voxels <bookmark mark='mask'/>inside the brain count."):
            self.at("d0", FadeIn(dims[0]))
            self.at("d1", GrowArrow(arr[0]), FadeIn(al[0]), FadeIn(dims[1]))
            self.at("d2", GrowArrow(arr[1]), FadeIn(al[1]), FadeIn(dims[2]))
            self.at("mask", FadeIn(mask))

        win = VGroup(*[Rectangle(width=0.11, height=0.5, stroke_width=0, fill_opacity=0.9, fill_color=IN_C if i < 32 else OUT_C) for i in range(42)])
        win.arrange(RIGHT, buff=0.02)
        strip = VGroup(*[Rectangle(width=0.11, height=0.5, stroke_width=0, fill_opacity=0.25, fill_color=GREY_B) for _ in range(90)]).arrange(RIGHT, buff=0.02)
        strip.to_edge(DOWN, buff=0.85)
        win.move_to(strip[:42])
        wl = VGroup(Tex("32 in", color=IN_C, font_size=24).next_to(win[:32], UP, buff=0.08),
                    Tex("10 out", color=OUT_C, font_size=24).next_to(win[32:], UP, buff=0.08))
        split = Tex(r"80 subjects train (182\,560 windows), 20 unseen subjects test (45\,640)", font_size=28).to_edge(DOWN, buff=0.25)
        with self.voiceover(text="A <bookmark mark='slide'/>sliding window cuts each scan into samples of thirty two inputs and ten "
                                 "targets. <bookmark mark='split'/>Eighty subjects train the model, and twenty unseen subjects test it."):
            self.at("slide", FadeIn(strip), FadeIn(win), FadeIn(wl), run_time=0.6)
            self.play(VGroup(win, wl).animate.shift(48 * 0.13 * RIGHT), run_time=1.6, rate_func=linear)
            self.at("split", FadeIn(split))
        fade_all(self)


class Model(Narrated):
    def construct(self):
        title = Tex(r"Why a Swin Transformer?").scale(0.72).to_edge(UP)
        n = 8
        cell = 0.42
        grid = VGroup(*[Square(cell, stroke_color=GREY_D, stroke_width=1.5, fill_color=ENC_C, fill_opacity=0.15) for _ in range(n * n)])
        grid.arrange_in_grid(n, n, buff=0).shift(3.2 * LEFT + 0.4 * DOWN)
        gl = Tex(r"tokens (2D here; 4D in the model)", font_size=24, color=GREY_B).next_to(grid, DOWN, buff=0.2)

        def win_rects(off):
            g = VGroup()
            for i in range(-1, 2):
                for j in range(-1, 2):
                    x0, y0 = i * 4 + off, j * 4 + off
                    xa, xb, ya, yb = max(x0, 0), min(x0 + 4, n), max(y0, 0), min(y0 + 4, n)
                    if xa >= xb or ya >= yb:
                        continue
                    tl = grid[ya * n + xa].get_corner(UL)
                    br = grid[(yb - 1) * n + (xb - 1)].get_corner(DR)
                    g.add(Rectangle(width=br[0] - tl[0], height=tl[1] - br[1], stroke_color=YELLOW, stroke_width=4).move_to((tl + br) / 2))
            return g

        w0, w1 = win_rects(0), win_rects(2)
        pts = VGroup(
            Tex(r"full attention over every voxel token is far too expensive", font_size=28),
            Tex(r"Swin: attention only inside local windows", font_size=28, color=YELLOW),
            Tex(r"next layer: windows shifted, so information crosses borders", font_size=28, color=YELLOW),
            Tex(r"patch merging: coarser tokens, wider view", font_size=28, color=TEAL_L),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.3).next_to(grid, RIGHT, buff=0.7).shift(0.4 * UP)
        with self.voiceover(text="A voxel-level brain is huge. Ordinary <bookmark mark='full'/>self attention compares every token with "
                                 "every other, which is far too expensive here. The authors' earlier model worked on three hundred and "
                                 "seventy nine brain regions instead."):
            self.play(Write(title), run_time=0.8)
            self.at("full", FadeIn(grid), FadeIn(gl), FadeIn(pts[0]))
        with self.voiceover(text="The Swin Transformer only attends <bookmark mark='win'/>within small local windows. In the next layer the "
                                 "windows are <bookmark mark='shift'/>shifted, so information flows across window borders. And "
                                 "<bookmark mark='merge'/>patch merging builds a hierarchy, from fine detail to the whole brain."):
            self.at("win", Create(w0), FadeIn(pts[1]))
            self.at("shift", ReplacementTransform(w0, w1), FadeIn(pts[2]))
            merged = VGroup(*[Square(cell * 2, stroke_color=TEAL_L, stroke_width=3, fill_color=TEAL_L, fill_opacity=0.15) for _ in range(16)])
            merged.arrange_in_grid(4, 4, buff=0).move_to(grid)
            self.at("merge", FadeOut(w1), ReplacementTransform(grid, merged), FadeIn(pts[3]))
        self.play(*[FadeOut(m) for m in self.mobjects if m is not title])

        t2 = Tex(r"The model: SwiFT encoder, convolutional decoder").scale(0.72).to_edge(UP)

        def blk(text, color, w=2.25, h=0.95):
            r = RoundedRectangle(corner_radius=0.1, width=w, height=h, stroke_color=color, fill_color=color, fill_opacity=0.15)
            return VGroup(r, Tex(text, font_size=22).move_to(r))

        enc = VGroup(blk(r"patch embed\\$3{\times}3{\times}3{\times}4$, $E{=}36$", ENC_C), blk(r"stage 1\\2 layers, 3 heads", ENC_C),
                     blk(r"merge + stage 2\\6 layers, 6 heads", ENC_C), blk(r"merge + stage 3\\2 layers, 12 heads", ENC_C)).arrange(RIGHT, buff=0.55)
        dec = VGroup(blk(r"conv, then $1{\times}1{\times}1$\\$\to$ 10 states", DEC_C), blk(r"concat + conv\\$\to$ transposed conv", DEC_C),
                     blk(r"concat + conv\\$\to$ transposed conv", DEC_C), blk(r"time $\to$ channels\\$\to$ transposed conv", DEC_C)).arrange(RIGHT, buff=0.55)
        VGroup(enc, dec).arrange(DOWN, buff=1.35).shift(0.35 * RIGHT + 0.15 * DOWN)
        inp = MathTex(r"48^3\!\times\!32", font_size=30, color=IN_C).next_to(enc, LEFT, buff=0.35)
        out = MathTex(r"48^3\!\times\!10", font_size=30, color=OUT_C).next_to(dec, LEFT, buff=0.35)
        ea = VGroup(*[Arrow(a.get_right(), b.get_left(), buff=0.05, stroke_width=3, tip_length=0.13, color=GREY_B) for a, b in zip(enc[:-1], enc[1:])])
        da = VGroup(*[Arrow(b.get_left(), a.get_right(), buff=0.05, stroke_width=3, tip_length=0.13, color=GREY_B) for a, b in zip(dec[:-1], dec[1:])])
        down = Arrow(enc[3].get_bottom(), dec[3].get_top(), buff=0.05, stroke_width=3, tip_length=0.13, color=GREY_B)
        skips = VGroup(*[DashedLine(enc[k].get_bottom(), dec[k].get_top(), color=YELLOW, stroke_width=2.5, dash_length=0.08) for k in (1, 2)])
        shp = VGroup(*[MathTex(s, font_size=24, color=GREY_B).next_to(enc[k], UP, buff=0.1) for k, s in
                       [(1, r"16^3\!\times\!8\!\times\!36"), (2, r"8^3\!\times\!8\!\times\!72"), (3, r"4^3\!\times\!8\!\times\!144")]])
        ia = Arrow(inp.get_right(), enc[0].get_left(), buff=0.08, stroke_width=3, tip_length=0.13, color=IN_C)
        oa = Arrow(dec[0].get_left(), out.get_right(), buff=0.08, stroke_width=3, tip_length=0.13, color=OUT_C)
        el = Tex("encoder (SwiFT)", color=ENC_C, font_size=26).next_to(enc, UP, buff=0.5).align_to(enc, LEFT)
        dl = Tex("decoder", color=DEC_C, font_size=26).next_to(dec, DOWN, buff=0.2).align_to(dec, LEFT)
        sl = Tex("skip connections", color=YELLOW, font_size=24).next_to(skips, RIGHT, buff=0.15).shift(0.0 * UP)
        with self.voiceover(text="The <bookmark mark='enc'/>encoder is SwiFT, a four D Swin Transformer for f M R I. It cuts the "
                                 "<bookmark mark='in'/>input into patches of three by three by three voxels by four time points, "
                                 "embeds them, and runs <bookmark mark='st'/>three stages of window attention, shrinking space down to a "
                                 "<bookmark mark='bott'/>four voxel cube with a hundred and forty four channels."):
            self.play(ReplacementTransform(title, t2), run_time=0.7)
            self.at("enc", FadeIn(el))
            self.at("in", FadeIn(inp), GrowArrow(ia), FadeIn(enc[0]))
            self.at("st", LaggedStart(*[AnimationGroup(GrowArrow(a), FadeIn(b), FadeIn(s)) for a, b, s in zip(ea, enc[1:], shp)], lag_ratio=0.5), run_time=1.8)
            self.at("bott", Indicate(shp[2], color=YELLOW))
        with self.voiceover(text="The <bookmark mark='dec'/>decoder folds time into channels, so one pass outputs all ten future states, "
                                 "and climbs back up with <bookmark mark='tc'/>three transposed convolutions. "
                                 "<bookmark mark='skip'/>Skip connections, as in a U net, pass fine detail across. The "
                                 "<bookmark mark='out'/>output is ten full brain volumes."):
            self.at("dec", GrowArrow(down), FadeIn(dec[3]), FadeIn(dl))
            self.at("tc", LaggedStart(*[AnimationGroup(GrowArrow(a), FadeIn(b)) for a, b in zip(reversed(da[1:]), [dec[2], dec[1]])], lag_ratio=0.5), run_time=1.0)
            self.at("skip", Create(skips), FadeIn(sl))
            self.at("out", GrowArrow(da[0]), FadeIn(dec[0]), GrowArrow(oa), FadeIn(out))
        leak = Tex(r"only past states go in, so nothing leaks from the future", font_size=26, color=GREY_B).to_edge(DOWN, buff=0.3)
        with self.voiceover(text="Because only <bookmark mark='past'/>past states go in, there's no information leak from the future."):
            self.at("past", FadeIn(leak), Indicate(inp, color=IN_C))
        fade_all(self)


class Loss(Narrated):
    def construct(self):
        title = Tex(r"Training: accurate \emph{and} structured").scale(0.72).to_edge(UP)
        mse = MathTex(r"\text{masked MSE} = \frac{1}{n}\sum_{i=1}^{n}\big(Y_i-\hat Y_i\big)^2", font_size=40)
        ml = Tex(r"$n$ = voxels inside the brain", font_size=26, color=GREY_B)
        trap = Tex(r"but a blurry, mean-like prediction can also score a low MSE", font_size=28, color=RED_C)
        ssim = MathTex(r"\text{SSIM}(x,y)=\frac{(2\mu_x\mu_y+c_1)(2\sigma_{xy}+c_2)}{(\mu_x^2+\mu_y^2+c_1)(\sigma_x^2+\sigma_y^2+c_2)}", font_size=36)
        sl = Tex(r"local means, variances, covariance in a $7{\times}7{\times}7$ Gaussian window (3D)", font_size=26, color=GREY_B)
        loss = MathTex(r"\mathcal{L}", r"=", r"\text{masked MSE}", r"+", r"\alpha", r"\,(1-\text{SSIM})", r",\quad \alpha=2", font_size=44, color=YELLOW)
        train = Tex(r"Adam, learning rate $10^{-4}$, NVIDIA A100; converged after 24 epochs", font_size=26, color=GREY_B)
        VGroup(mse, ml, trap, ssim, sl, loss, train).arrange(DOWN, buff=0.3).next_to(title, DOWN, buff=0.55)
        with self.voiceover(text="Training compares the prediction with the real future using <bookmark mark='mse'/>mean squared error, "
                                 "counted only <bookmark mark='mask'/>inside the brain."):
            self.play(Write(title), run_time=0.8)
            self.at("mse", Write(mse))
            self.at("mask", FadeIn(ml))
        with self.voiceover(text="But a <bookmark mark='blur'/>blurry prediction that hugs the average can also score a low error. So "
                                 "the loss adds <bookmark mark='ssim'/>structural similarity, S S I M, extended to three D, which compares "
                                 "<bookmark mark='loc'/>local means, contrasts and correlations."):
            self.at("blur", FadeIn(trap))
            self.at("ssim", Write(ssim), run_time=1.2)
            self.at("loc", FadeIn(sl))
        with self.voiceover(text="The <bookmark mark='tot'/>final loss is the masked M S E plus <bookmark mark='alpha'/>two times one minus "
                                 "S S I M. The model trained with <bookmark mark='adam'/>Adam on an A one hundred, and converged in twenty "
                                 "four epochs."):
            self.at("tot", Write(loss[:4]), run_time=0.9)
            self.at("alpha", Write(loss[4:]))
            self.at("adam", FadeIn(train))
        fade_all(self)


class Results(Narrated):
    def construct(self):
        title = Tex(r"Results on 20 unseen subjects").scale(0.72).to_edge(UP)
        big = VGroup(VGroup(MathTex(r"0.035", font_size=64, color=TEAL_L), Tex("masked MSE", font_size=28)).arrange(DOWN, buff=0.1),
                     VGroup(MathTex(r"0.954", font_size=64, color=TEAL_L), Tex("SSIM", font_size=28)).arrange(DOWN, buff=0.1)
                     ).arrange(RIGHT, buff=1.6).next_to(title, DOWN, buff=0.5)
        with self.voiceover(text="On twenty unseen subjects, the average masked error is <bookmark mark='mse'/>zero point zero three five, "
                                 "and the structural similarity is <bookmark mark='ssim'/>zero point nine five four, close to a perfect "
                                 "one."):
            self.play(Write(title), run_time=0.8)
            self.at("mse", FadeIn(big[0], scale=0.8))
            self.at("ssim", FadeIn(big[1], scale=0.8))

        ax = Axes(x_range=[0, 3.6, 1], y_range=[0, 0.1, 0.02], x_length=6.0, y_length=3.0,
                  axis_config={"color": GREY_B, "include_tip": False, "include_ticks": False}).next_to(big, DOWN, buff=0.6)
        bars = VGroup()
        labs = VGroup()
        for i, (v, name, col) in enumerate([(0.035, "prediction", TEAL_L), (0.076, r"shifted:\\vs previous state", ORANGE_L),
                                            (0.1, r"input order\\shuffled", RED_C)]):
            b = Rectangle(width=0.8, height=ax.c2p(0, v)[1] - ax.c2p(0, 0)[1], fill_color=col, fill_opacity=0.85, stroke_width=0)
            b.move_to(ax.c2p(0.7 + 1.1 * i, 0), aligned_edge=DOWN)
            bars.add(b)
            labs.add(VGroup(Tex(name, font_size=22).next_to(ax.c2p(0.7 + 1.1 * i, 0), DOWN, buff=0.12),
                            MathTex([r"0.035", r"0.076", r"4890\ \Uparrow"][i], font_size=30, color=col).next_to(b, UP, buff=0.08)))
        bk = Tex(r"(off the scale)", font_size=20, color=RED_C).next_to(labs[2][1], RIGHT, buff=0.1)
        with self.voiceover(text="Two controls. <bookmark mark='shuf'/>Shuffle the order of the input states, and the error explodes to "
                                 "four thousand eight hundred and ninety: the model really uses the temporal sequence."):
            self.play(FadeOut(big[1]), big[0].animate.scale(0.6).to_corner(UL).shift(0.8 * DOWN), run_time=0.6)
            self.play(Create(ax), GrowFromEdge(bars[0], DOWN), FadeIn(labs[0]), run_time=0.8)
            self.at("shuf", GrowFromEdge(bars[2], DOWN), FadeIn(labs[2]), FadeIn(bk))
        with self.voiceover(text="And compare each prediction with the <bookmark mark='prev'/>previous real state instead: the error doubles, "
                                 "to zero point zero seven six. So the model isn't just copying the last frame forward."):
            self.at("prev", GrowFromEdge(bars[1], DOWN), FadeIn(labs[1]))
        self.play(*[FadeOut(m) for m in self.mobjects if m is not title])

        ax2 = Axes(x_range=[0.3, 10.7, 1], y_range=[0, 0.16, 0.04], x_length=6.0, y_length=2.9,
                   axis_config={"color": GREY_B, "include_tip": False},
                   y_axis_config={"include_numbers": True, "font_size": 22, "decimal_number_config": {"num_decimal_places": 2}},
                   x_axis_config={"include_ticks": False}).to_edge(LEFT, buff=1.5).shift(0.75 * UP)
        xl = VGroup(*[MathTex(f"{k}", font_size=22).next_to(ax2.c2p(k, 0), DOWN, buff=0.12) for k in range(1, 11)])
        xt = Tex(r"predicted step (0.72 s each)", font_size=24).next_to(xl, DOWN, buff=0.15)
        yt = Tex(r"masked MSE", font_size=24).rotate(PI / 2).next_to(ax2.y_axis, LEFT, buff=0.75)
        pts = [ax2.c2p(k + 1, v) for k, v in enumerate(STEP_MSE)]
        dots = VGroup(*[Dot(p, radius=0.06, color=TEAL_L if k < 5 else ORANGE_L) for k, p in enumerate(pts)])
        line = VMobject(stroke_color=TEAL_L, stroke_width=3).set_points_as_corners(pts)
        vals = VGroup(*[MathTex(f"{v:.3f}", font_size=20, color=GREY_B).next_to(p, UP if k > 4 else UP, buff=0.12) for k, (v, p) in enumerate(zip(STEP_MSE, pts))])
        first5 = Tex(r"first 5 steps $<$ 0.01", color=TEAL_L, font_size=26).move_to(ax2.c2p(3.2, 0.05))
        maps = card("fig2b_error_maps.png", 1.25).next_to(xt, DOWN, buff=0.25).align_to(ax2, LEFT).shift(0.6 * LEFT)
        maps.scale_to_fit_width(min(maps.width, 7.2))
        with self.voiceover(text="How does accuracy hold up further into the future? The error stays below zero point zero one for the "
                                 "<bookmark mark='f5'/>first five steps, about three and a half seconds, then <bookmark mark='grow'/>"
                                 "climbs, to zero point one four four at the tenth."):
            self.play(Create(ax2), FadeIn(xl), FadeIn(xt), FadeIn(yt), run_time=0.8)
            self.at("f5", LaggedStart(*[FadeIn(d) for d in dots[:5]], lag_ratio=0.15), Create(VMobject().set_points_as_corners(pts[:5]).set_stroke(TEAL_L, 3)),
                    FadeIn(vals[:5]), FadeIn(first5), run_time=1.0)
            self.at("grow", Create(line), LaggedStart(*[FadeIn(d) for d in dots[5:]], lag_ratio=0.15), FadeIn(vals[5:]), run_time=1.6)
        fig3 = card("fig3_pred_vs_truth.png", 6.3).to_edge(RIGHT, buff=0.35).shift(0.15 * DOWN)
        cite = Tex(r"Figs.\ 2(b), 3: " + CITE, font_size=20, color=GREY_B).to_corner(DR, buff=0.08)
        with self.voiceover(text="The <bookmark mark='err'/>error maps show no spatial bias, the error just grows evenly with time. And "
                                 "side by side with the <bookmark mark='fig3'/>real brain states, the predictions keep the same contrast "
                                 "patterns, step after step."):
            self.at("err", FadeIn(maps), FadeIn(cite))
            self.at("fig3", FadeIn(fig3, shift=0.2 * LEFT), run_time=0.9)
        fade_all(self)


class Regions(Narrated):
    def construct(self):
        title = Tex(r"Which brain regions are easiest to predict?").scale(0.72).to_edge(UP)
        fig = card("fig4a_regional_mse.png", 2.75).next_to(title, DOWN, buff=0.3)
        im = fig[1]   # hide the stray ')' of the panel label cropped at the image's top-left
        fig.add(Rectangle(width=0.2, height=0.62, fill_color=WHITE, fill_opacity=1, stroke_width=0).move_to(im.get_corner(UL), aligned_edge=UL))
        fl = Tex(r"regional MSE, Yeo17 atlas, 100 regions: darker red = more accurate", font_size=24, color=GREY_B).next_to(fig, DOWN, buff=0.12)
        cite = Tex(r"Fig.\ 4(a): " + CITE, font_size=20, color=GREY_B).to_corner(DR, buff=0.08)

        def rows(data, col):
            return VGroup(*[Tex(f"{h} {r}, {net}: {v:.4f}", font_size=26, color=col) for h, r, net, v in data]).arrange(DOWN, aligned_edge=LEFT, buff=0.1)

        best_h = Tex(r"lowest error", font_size=30, color=TEAL_L)
        worst_h = Tex(r"highest error", font_size=30, color=ORANGE_L)
        best = VGroup(best_h, rows(BEST, WHITE)).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        worst = VGroup(worst_h, rows(WORST, WHITE)).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
        VGroup(best, worst).arrange(RIGHT, buff=1.4, aligned_edge=UP).next_to(fl, DOWN, buff=0.3)
        with self.voiceover(text="Breaking the error down over <bookmark mark='atlas'/>one hundred cortical regions of the Yeo atlas, the "
                                 "spread is narrow, with no outliers."):
            self.play(Write(title), run_time=0.8)
            self.at("atlas", FadeIn(fig), FadeIn(fl), FadeIn(cite))
        why_b = Tex(r"attention and control hubs:\\stable connectivity, high SNR", font_size=24, color=GREY_B, tex_environment="flushleft").next_to(best, DOWN, buff=0.25).align_to(best, LEFT)
        why_w = Tex(r"limbic: signal dropout and artefacts,\\variable at rest", font_size=24, color=GREY_B, tex_environment="flushleft").next_to(worst, DOWN, buff=0.25).align_to(worst, LEFT)
        with self.voiceover(text="The <bookmark mark='best'/>best predicted are the superior and inferior parietal lobules, of the dorsal "
                                 "attention and control networks: <bookmark mark='whyb'/>well connected hubs with strong, stable signals."):
            self.at("best", FadeIn(best_h), LaggedStart(*[FadeIn(r) for r in best[1]], lag_ratio=0.3), run_time=1.0)
            self.at("whyb", FadeIn(why_b))
        with self.voiceover(text="The <bookmark mark='worst'/>worst are limbic: orbitofrontal cortex and the temporal pole. These areas "
                                 "<bookmark mark='whyw'/>suffer signal loss and artefacts in f M R I, and vary more at rest. Even so, the "
                                 "worst region's error is <bookmark mark='ratio'/>only about forty percent above the best."):
            self.at("worst", FadeIn(worst_h), LaggedStart(*[FadeIn(r) for r in worst[1]], lag_ratio=0.3), run_time=1.0)
            self.at("whyw", FadeIn(why_w))
            self.at("ratio", Indicate(best[1][0], color=TEAL_L), Indicate(worst[1][0], color=ORANGE_L))
        fade_all(self)


class Outro(Narrated):
    def construct(self):
        title = Tex("In context").scale(0.72).to_edge(UP)
        ctx = VGroup(
            Tex(r"BrainLM: MSE $\approx$ 0.5 over its first 10 states (different preprocessing)", font_size=28),
            Tex(r"regional transformer (379 regions): better first step (0.0013),\\but above 0.15 after 5.04 s", font_size=28, tex_environment="flushleft"),
            Tex(r"this voxel model: accurate short-term, at full spatial detail", font_size=28, color=TEAL_L),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.25).next_to(title, DOWN, buff=0.45)
        with self.voiceover(text="In context: <bookmark mark='blm'/>BrainLM reported errors around zero point five, though with different "
                                 "preprocessing. The authors' <bookmark mark='reg'/>regional model was better on the very first step, but "
                                 "its error passed zero point one five after five seconds, while <bookmark mark='this'/>this voxel model "
                                 "stays accurate in the short term."):
            self.play(Write(title), run_time=0.7)
            for k, m in enumerate(["blm", "reg", "this"]):
                self.at(m, FadeIn(ctx[k], shift=0.1 * RIGHT))
        nxt = VGroup(Tex(r"Next:", font_size=30, color=YELLOW),
                     Tex(r"longer inputs and loss weighted towards far steps", font_size=26),
                     Tex(r"full-resolution data", font_size=26),
                     Tex(r"task fMRI, not just rest", font_size=26)).arrange(DOWN, aligned_edge=LEFT, buff=0.12).next_to(ctx, DOWN, buff=0.55).align_to(ctx, LEFT)
        with self.voiceover(text="Next steps are <bookmark mark='n1'/>longer input windows with a loss that weights the far future, "
                                 "<bookmark mark='n2'/>full resolution data, and <bookmark mark='n3'/>task f M R I, not just rest."):
            self.play(FadeIn(nxt[0]), run_time=0.4)
            for k in range(3):
                self.at(f"n{k + 1}", FadeIn(nxt[k + 1], shift=0.1 * RIGHT))
        end = Tex(r"A Swin Transformer can learn the brain's spatiotemporal dynamics, voxel by voxel.", color=TEAL_L).scale(0.62).to_edge(DOWN, buff=0.5)
        with self.voiceover(text="The takeaway: a <bookmark mark='end'/>Swin Transformer can learn how the resting brain evolves, voxel by "
                                 "voxel, well enough to predict its next seven seconds."):
            self.at("end", Write(end), run_time=1.5)
        self.wait(1)
        fade_all(self)
