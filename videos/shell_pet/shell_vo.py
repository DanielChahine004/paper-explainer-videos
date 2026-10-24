"""Explainer: K. Wilson, 'High-Sensitivity PET using Optimised Continuous Cylindrical Shell Nanocomposite and
Transparent Ceramic Scintillators', PhD thesis, University of Technology Sydney, 2020.

Numbers are from the thesis text and Tables 3.2, 4.1-4.5, 5.1 and 6.2-6.4. The thesis is (c) its author, so no
figures are reused: every drawing here is new. Light maps are computed from the thesis's own photon model
(Eqs. 3.1-3.2), pulse trains are deconvolved for real with an exponential kernel; both are illustrative.
Visuals are cued to the narration with <bookmark/> tags and self.at() (see ../DESIGN.md).
Render with render.sh, or one scene: manim -ql shell_vo.py Locate
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import *  # noqa: E402,F401

CER_C, NANO_C, GAM_C, LIGHT_C, SIPM_C = TEAL_L, PURPLE_L, "#7ee081", "#f5d76e", "#4c8fe0"
CITE = r"K.\ Wilson, PhD thesis, University of Technology Sydney, 2020"

# Table 3.2: optimum thickness (mm) and % of gammas localised within 5 mm
MATERIALS = [("Gd$_2$O$_3$ / PVT", 62.61, 37.21, 0), ("LaBr$_3$:Ce / PS", 53.78, 36.70, 0), ("LaF$_3$:Ce / OA", 32.66, 25.73, 0),
             ("LaF$_3$:Ce / PS", 42.60, 48.83, 0), ("YAG:Ce / PS", 46.79, 45.63, 0), ("GAGG:Ce", 13.98, 47.95, 1),
             ("GLuGAG:Ce", 27.54, 67.82, 1), ("GYGAG:Ce", 42.63, 66.75, 1), ("LuAG:Pr", 18.96, 59.95, 1)]
# Table 6.2-6.4, OSEM, corrected: FWHM (mm) along x, y, z for sources at centre, 50% and 75% of the inner radius
OSEM = [(3.36, 3.31, 2.36), (3.95, 3.99, 3.16), (3.84, 4.41, 3.16)]


def photon_map(xs, z, lam=60.0, xd=None):
    """Thesis Eq. 3.1 along one row of pixels: photons reaching a face at distance z from the emission point."""
    xd = np.linspace(-10, 10, 21) if xd is None else xd
    r = np.sqrt((xs - xd) ** 2 + z ** 2)
    return z * np.exp(-r / lam) / (4 * PI * r ** 3)


def blob(sx, sy, size=60):
    """An illustrative reconstructed point source: a Gaussian spot, black-to-yellow."""
    y, x = np.mgrid[-1:1:size * 1j, -1:1:size * 1j]
    v = np.exp(-(x ** 2 / (2 * sx ** 2) + y ** 2 / (2 * sy ** 2)))
    img = np.stack([np.clip(1.6 * v, 0, 1), np.clip(1.6 * v - 0.4, 0, 1), np.clip(2 * v - 1.4, 0, 1), np.clip(2 * v, 0, 1)], -1) * 255
    im = ImageMobject(img.astype(np.uint8))
    im.set_resampling_algorithm(RESAMPLING_ALGORITHMS["linear"])
    return im


def ring(r_in, r_out, color=CER_C, opacity=0.35):
    return Annulus(inner_radius=r_in, outer_radius=r_out, fill_color=color, fill_opacity=opacity, stroke_color=color, stroke_width=2)


def sipm_ticks(r, n, out=True, color=SIPM_C, length=0.12):
    """Short radial bars standing for the photodetector tiles on one surface of the ring."""
    d = 1 if out else -1
    return VGroup(*[Line(r * np.array([np.cos(a), np.sin(a), 0]), (r + d * length) * np.array([np.cos(a), np.sin(a), 0]),
                         color=color, stroke_width=3) for a in np.linspace(0, TAU, n, endpoint=False)])


def gamma_pair(c, ang, r, color=GAM_C):
    u = np.array([np.cos(ang), np.sin(ang), 0])
    return VGroup(Arrow(c, c + r * u, buff=0, color=color, stroke_width=4, max_tip_length_to_length_ratio=0.08),
                  Arrow(c, c - r * u, buff=0, color=color, stroke_width=4, max_tip_length_to_length_ratio=0.08))


class Opening(Narrated, ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=68 * DEGREES, theta=-50 * DEGREES, zoom=1.0)
        outer = Cylinder(radius=2.0, height=2.6, resolution=(6, 48), fill_color=CER_C, fill_opacity=0.28,
                         stroke_width=0.4, stroke_color=CER_C, show_ends=False, checkerboard_colors=False)
        inner = Cylinder(radius=1.55, height=2.6, resolution=(6, 48), fill_color=CER_C, fill_opacity=0.18,
                         stroke_width=0.4, stroke_color=CER_C, show_ends=False, checkerboard_colors=False)
        shell = VGroup(outer, inner).rotate(PI / 2, axis=RIGHT)
        title = Tex(r"High-sensitivity PET with a\\continuous cylindrical shell scintillator").scale(0.85).to_edge(UP, buff=0.3)
        foot = VGroup(Tex(r"Keenan Wilson \textperiodcentered\ PhD thesis, 2020", color=GREY_B).scale(0.55),
                      Tex(r"University of Technology Sydney \textperiodcentered\ supervisor Daniel Franklin", color=TEAL_L).scale(0.5)
                      ).arrange(DOWN, buff=0.12).to_edge(DOWN, buff=0.35)
        self.add_fixed_in_frame_mobjects(title, foot)
        self.remove(title, foot)
        with self.voiceover(text="This thesis proposes a P E T scanner unlike the ones in hospitals today. Instead of tens of "
                                 "thousands of separate crystals, a <bookmark mark='shell'/>single continuous shell of scintillator, "
                                 "read out by light sensors on both its inner and outer surfaces."):
            self.play(Write(title), run_time=1.5)
            self.wait_until_bookmark("shell")
            self.play(FadeIn(shell), run_time=1.2)
            self.begin_ambient_camera_rotation(rate=0.25)
        with self.voiceover(text="Let's see why you would build it, what it takes to make it work, and how well it does in "
                                 "simulation."):
            self.play(FadeIn(foot, shift=0.1 * UP))
        self.stop_ambient_camera_rotation()
        self.play(FadeOut(shell), FadeOut(title), FadeOut(foot))


class PETBasics(Narrated):
    def construct(self):
        title = Tex("How PET sees").scale(0.72).to_edge(UP)
        R = 2.6
        det = Circle(radius=R, color=GREY_B, stroke_width=6).shift(2.6 * LEFT + 0.4 * DOWN)
        c0 = det.get_center()
        src = c0 + np.array([0.6, 0.4, 0])
        dot = Dot(src, color=RED, radius=0.09)
        lab = Tex("tracer", font_size=26, color=RED).next_to(dot, DOWN, buff=0.12)
        lab.add_background_rectangle(color=config.background_color, opacity=0.85, buff=0.04).set_z_index(3)
        dot.set_z_index(3)

        def hit(ang):
            u = np.array([np.cos(ang), np.sin(ang), 0])
            b = np.dot(src - c0, u)
            s = -b + np.sqrt(b ** 2 - np.dot(src - c0, src - c0) + R ** 2)
            s2 = -b - np.sqrt(b ** 2 - np.dot(src - c0, src - c0) + R ** 2)
            return src + s * u, src + s2 * u

        a, b = hit(0.5)
        pair = VGroup(Arrow(src, a, buff=0, color=GAM_C, stroke_width=4), Arrow(src, b, buff=0, color=GAM_C, stroke_width=4))
        glab = Tex(r"two 511 keV gammas,\\back to back", font_size=26, color=GAM_C).next_to(det, RIGHT, buff=0.4).shift(1.2 * UP)
        lors = VGroup(*[Line(*hit(t), color=YELLOW, stroke_width=2) for t in (0.5, 1.4, 2.2, 2.9, -0.6)])
        hits = VGroup(*[Dot(p, color=GAM_C, radius=0.07) for t in (0.5,) for p in hit(t)])
        lorl = Tex(r"line of response", font_size=26, color=YELLOW).next_to(glab, DOWN, buff=0.5, aligned_edge=LEFT)
        keys = VGroup(Tex(r"\textbf{sensitivity}: fraction of decays recorded", font_size=28),
                      Tex(r"\textbf{resolution}: how sharply each source is placed", font_size=28)
                      ).arrange(DOWN, aligned_edge=LEFT, buff=0.18).next_to(lorl, DOWN, buff=0.6, aligned_edge=LEFT)
        with self.voiceover(text="A <bookmark mark='tr'/>radioactive tracer in the body emits positrons. Each one annihilates with an "
                                 "electron and produces <bookmark mark='pair'/>two gamma photons of five hundred and eleven kilo "
                                 "electron volts, flying in opposite directions."):
            self.play(Write(title), Create(det), run_time=0.9)
            self.at("tr", FadeIn(dot, scale=0.5), FadeIn(lab))
            self.at("pair", GrowArrow(pair[0]), GrowArrow(pair[1]), FadeIn(glab))
        with self.voiceover(text="When a <bookmark mark='hit'/>ring of detectors catches both, the source lies somewhere on the "
                                 "<bookmark mark='lor'/>line between the two hits, the line of response. "
                                 "<bookmark mark='many'/>Millions of such lines are combined into an image."):
            self.at("hit", FadeIn(hits, scale=0.5))
            self.at("lor", Create(lors[0]), FadeIn(lorl), FadeOut(pair))
            self.at("many", LaggedStart(*[Create(l) for l in lors[1:]], lag_ratio=0.25), run_time=1.4)
        with self.voiceover(text="Two numbers matter most. <bookmark mark='sens'/>Sensitivity: what fraction of decays the scanner "
                                 "actually records. And <bookmark mark='res'/>spatial resolution: how sharply it places each source."):
            self.at("sens", FadeIn(keys[0], shift=0.1 * RIGHT))
            self.at("res", FadeIn(keys[1], shift=0.1 * RIGHT))
        fade_all(self)


class Conventional(Narrated):
    def construct(self):
        title = Tex("Today's detectors").scale(0.72).to_edge(UP)
        R, n = 2.2, 24
        c1 = 3.4 * LEFT + 0.5 * DOWN
        blocks = VGroup()
        for k in range(n):
            a = k * TAU / n
            blk = VGroup(*[Rectangle(width=0.1, height=0.5, stroke_width=1, stroke_color=BLUE_B, fill_color="#7fb3ff", fill_opacity=0.5)
                           .shift((i - 1.5) * 0.11 * RIGHT) for i in range(4)])
            blk.rotate(a - PI / 2).move_to(c1 + R * np.array([np.cos(a), np.sin(a), 0]))
            blocks.add(blk)
        dlab = Tex(r"discrete crystals", font_size=28).next_to(blocks, DOWN, buff=0.3)
        gap_a = 0.5 * TAU / n
        leak = Arrow(c1, c1 + 3.3 * np.array([np.cos(gap_a), np.sin(gap_a), 0]), buff=0, color=GAM_C, stroke_width=4)
        cons = VGroup(Tex(r"tens of thousands of small crystals", font_size=28),
                      Tex(r"each wrapped and optically isolated", font_size=28),
                      Tex(r"gaps between blocks lose gammas", font_size=28),
                      Tex(r"finer resolution $\Rightarrow$ more, smaller crystals", font_size=28)
                      ).arrange(DOWN, aligned_edge=LEFT, buff=0.15).to_edge(RIGHT, buff=0.6).shift(0.9 * UP)
        with self.voiceover(text="Most scanners use <bookmark mark='blk'/>blocks of small, separate crystals. A large scanner needs "
                                 "<bookmark mark='c1'/>tens of thousands of them, each <bookmark mark='c2'/>wrapped so its light stays "
                                 "inside. The wrapping and the <bookmark mark='c3'/>gaps between blocks are dead space, where gammas "
                                 "escape. And <bookmark mark='c4'/>sharper images need more, smaller crystals, so cost climbs fast."):
            self.play(Write(title), run_time=0.8)
            self.at("blk", LaggedStart(*[FadeIn(b) for b in blocks], lag_ratio=0.03), FadeIn(dlab), run_time=1.2)
            self.at("c1", FadeIn(cons[0], shift=0.1 * RIGHT))
            self.at("c2", FadeIn(cons[1], shift=0.1 * RIGHT))
            self.at("c3", FadeIn(cons[2], shift=0.1 * RIGHT), GrowArrow(leak))
            self.at("c4", FadeIn(cons[3], shift=0.1 * RIGHT))

        slabs = VGroup()
        for k in range(8):
            a = k * TAU / 8
            slabs.add(Rectangle(width=1.7, height=0.4, stroke_color=BLUE_B, stroke_width=1.5, fill_color="#7fb3ff", fill_opacity=0.5)
                      .rotate(a - PI / 2).move_to(c1 + R * np.array([np.cos(a), np.sin(a), 0])))
        edges = VGroup(*[Dot(s.get_corner(UR), color=RED, radius=0.06) for s in slabs[:3]])
        mlab = Tex(r"monolithic slabs", font_size=28).next_to(slabs, DOWN, buff=0.3).match_y(dlab)
        mcons = VGroup(Tex(r"position from the light pattern", font_size=28),
                       Tex(r"large, flawless crystals are expensive", font_size=28),
                       Tex(r"accuracy drops near the edges", font_size=28)
                       ).arrange(DOWN, aligned_edge=LEFT, buff=0.15).next_to(cons, DOWN, buff=0.55, aligned_edge=LEFT)
        with self.voiceover(text="The alternative is <bookmark mark='mono'/>monolithic slabs: big single crystals that work out "
                                 "<bookmark mark='m1'/>where the gamma hit from the pattern of light. But <bookmark mark='m2'/>large, "
                                 "high quality crystals are expensive to grow, and <bookmark mark='m3'/>near the edges of a slab the "
                                 "position estimate gets worse."):
            self.at("mono", FadeOut(leak), ReplacementTransform(blocks, slabs), ReplacementTransform(dlab, mlab))
            self.at("m1", FadeIn(mcons[0], shift=0.1 * RIGHT))
            self.at("m2", FadeIn(mcons[1], shift=0.1 * RIGHT))
            self.at("m3", FadeIn(mcons[2], shift=0.1 * RIGHT), LaggedStart(*[Flash(e, color=RED) for e in edges], lag_ratio=0.2))
        fade_all(self)


class Idea(Narrated):
    def construct(self):
        title = Tex("The idea: one continuous shell").scale(0.72).to_edge(UP)
        c = 3.3 * LEFT + 0.4 * DOWN
        shell = ring(1.7, 2.35).move_to(c)
        tin = sipm_ticks(1.7, 52, out=False).move_to(c)
        tout = sipm_ticks(2.35, 60, out=True).move_to(c)
        pts = VGroup(Tex(r"no internal boundaries, no dead space", font_size=28),
                     Tex(r"no slab edges anywhere around the ring", font_size=28),
                     Tex(r"SiPMs on the inner \emph{and} outer surface", font_size=28, color=SIPM_C)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.15).to_edge(RIGHT, buff=0.5).shift(1.6 * UP)
        with self.voiceover(text="Wilson takes the monolithic idea to its limit: <bookmark mark='ring'/>one continuous cylindrical "
                                 "shell. It has <bookmark mark='p1'/>no internal boundaries, so no dead space, and <bookmark mark='p2'/>no "
                                 "edges anywhere around the ring. Small silicon photomultipliers cover <bookmark mark='p3'/>both the "
                                 "inner and the outer surface."):
            self.play(Write(title), run_time=0.8)
            self.at("ring", DrawBorderThenFill(shell), run_time=1.0)
            self.at("p1", FadeIn(pts[0], shift=0.1 * RIGHT))
            self.at("p2", FadeIn(pts[1], shift=0.1 * RIGHT), Indicate(shell, color=CER_C, scale_factor=1.03))
            self.at("p3", FadeIn(pts[2], shift=0.1 * RIGHT), Create(tin), Create(tout), run_time=1.0)

        rng = np.random.default_rng(3)
        nbox = Square(1.3, color=NANO_C, stroke_width=2, fill_color=NANO_C, fill_opacity=0.12)
        ndots = VGroup(*[Dot(nbox.get_center() + np.array([*(rng.uniform(-0.55, 0.55, 2)), 0]), radius=0.035, color=NANO_C)
                         for _ in range(70)])
        nano = VGroup(nbox, ndots)
        cbox = Square(1.3, color=CER_C, stroke_width=2, fill_color=CER_C, fill_opacity=0.12)
        grains = VGroup(*[RegularPolygon(6, radius=0.21, color=CER_C, stroke_width=1.5).move_to(cbox.get_center() + np.array([x, y, 0]))
                          for x in (-0.38, 0, 0.38) for y in (-0.36, 0.0, 0.36)])
        cer = VGroup(cbox, grains)
        mats = VGroup(nano, cer).arrange(RIGHT, buff=2.1).next_to(pts, DOWN, buff=0.6)
        nl = Tex(r"nanocomposite\\nanoparticles in a polymer", font_size=26, color=NANO_C).next_to(nano, DOWN, buff=0.15)
        cl = Tex(r"transparent ceramic\\sintered grains", font_size=26, color=CER_C).next_to(cer, DOWN, buff=0.15)
        trade = Tex(r"cheap, easy to shape \textemdash\ but they scatter light", font_size=28, color=YELLOW).next_to(VGroup(nl, cl), DOWN, buff=0.35)
        with self.voiceover(text="A shell like this can't be cut from a single crystal. Instead it uses two newer materials: "
                                 "<bookmark mark='n'/>nanocomposites, scintillating nanoparticles held in a polymer, and "
                                 "<bookmark mark='c'/>transparent ceramics, made of sintered grains. Both are <bookmark mark='t'/>cheaper "
                                 "and far easier to form into shapes. The catch: they scatter the scintillation light, and the "
                                 "nanocomposites are less dense."):
            self.at("n", FadeIn(nano), FadeIn(nl))
            self.at("c", FadeIn(cer), FadeIn(cl))
            self.at("t", FadeIn(trade, shift=0.1 * UP))
        fade_all(self)


class Locate(Narrated):
    def construct(self):
        title = Tex("Where did the gamma hit?").scale(0.72).to_edge(UP)
        W, T = 5.0, 2.0
        slab = Rectangle(width=W, height=T, color=CER_C, fill_color=CER_C, fill_opacity=0.15).shift(3.3 * LEFT + 0.2 * DOWN)
        top = Line(slab.get_corner(UL), slab.get_corner(UR), color=SIPM_C, stroke_width=8)
        bot = Line(slab.get_corner(DL), slab.get_corner(DR), color=SIPM_C, stroke_width=8)
        tl = Tex("front SiPMs", font_size=24, color=SIPM_C).next_to(top, UP, buff=0.1).align_to(top, LEFT)
        bl = Tex("back SiPMs", font_size=24, color=SIPM_C).next_to(bot, DOWN, buff=0.1)
        xs_u, zs_frac = 0.8, 0.28          # emission point: 0.8 units right of centre, 28% of the way down from the front
        pt = slab.get_top() + xs_u * RIGHT + zs_frac * T * DOWN
        gam = Arrow(slab.get_top() + xs_u * RIGHT + 1.0 * UP, pt, buff=0, color=GAM_C, stroke_width=4)
        flash = Dot(pt, color=LIGHT_C, radius=0.08)
        rays = VGroup(*[Line(pt, pt + 0.9 * np.array([np.cos(a), np.sin(a), 0]), color=LIGHT_C, stroke_width=1.5, stroke_opacity=0.7)
                        for a in np.linspace(0, TAU, 18, endpoint=False)])
        with self.voiceover(text="First, how does a monolithic detector locate a hit? A <bookmark mark='g'/>gamma stops at some point "
                                 "inside the slab and <bookmark mark='flash'/>releases a flash of thousands of light photons, spreading "
                                 "in every direction. Light sensors on the <bookmark mark='faces'/>front and the back count how many "
                                 "land on each pixel."):
            self.play(Write(title), Create(slab), run_time=0.8)
            self.at("g", GrowArrow(gam))
            self.at("flash", FadeIn(flash, scale=0.3), LaggedStart(*[Create(r) for r in rays], lag_ratio=0.03), run_time=0.9)
            self.at("faces", Create(top), Create(bot), FadeIn(tl), FadeIn(bl))

        # pixel counts on each face from the thesis model (Eq. 3.1/3.2), pixels 1 mm, slab 20 mm wide
        xd = np.linspace(-9.5, 9.5, 20)
        xs_mm, z_front, z_back = xs_u / W * 20, zs_frac * 8, (1 - zs_frac) * 8
        cf, cb = photon_map(xs_mm, z_front, xd=xd), photon_map(xs_mm, z_back, xd=xd)
        mx = max(cf.max(), cb.max())
        bw = W / 20

        def bars(counts, base, up):
            return VGroup(*[Rectangle(width=bw * 0.85, height=max(1.3 * v / mx, 0.01), stroke_width=0, fill_color=LIGHT_C, fill_opacity=0.9)
                            .move_to(base + (xd[k] / 20 * W) * RIGHT, aligned_edge=DOWN if up else UP) for k, v in enumerate(counts)])
        hf = bars(cf, top.get_center() + 0.42 * UP, True)
        hb = bars(cb, bot.get_center() + 0.42 * DOWN, False)
        with self.voiceover(text="Here is what they see. The face <bookmark mark='near'/>nearer the flash gets a tall, narrow spot. The "
                                 "<bookmark mark='far'/>far face gets a low, wide one. So the centre of the spots says where across the "
                                 "slab the hit was, and their widths say how deep."):
            self.play(FadeOut(rays), FadeOut(gam), FadeOut(tl), FadeOut(bl), run_time=0.4)
            self.at("near", LaggedStart(*[GrowFromEdge(b, DOWN) for b in hf], lag_ratio=0.03), run_time=1.0)
            self.at("far", LaggedStart(*[GrowFromEdge(b, UP) for b in hb], lag_ratio=0.03), run_time=1.0)

        model = MathTex(r"J(x_d)", "=", r"\frac{J_0\, z\, \Delta x\,\Delta y\; e^{-r/\lambda}}{4\pi r^3}", font_size=40).to_edge(RIGHT, buff=0.7).shift(1.7 * UP)
        rdef = MathTex(r"r = \sqrt{(x_s - x_d)^2 + (y_s - y_d)^2 + z^2}", font_size=30, color=GREY_B).next_to(model, DOWN, buff=0.2)
        steps = VGroup(Tex(r"1.\ light from a point spreads over distance $r$", font_size=26),
                       Tex(r"2.\ $e^{-r/\lambda}$: light lost on the way", font_size=26),
                       Tex(r"3.\ fit to front and back maps at once", font_size=26),
                       Tex(r"4.\ unknowns: $x_s, y_s$, depth, photons $J_0$", font_size=26)
                       ).arrange(DOWN, aligned_edge=LEFT, buff=0.14).next_to(rdef, DOWN, buff=0.4).align_to(rdef, LEFT)
        fit_frame(VGroup(model, rdef, steps))
        with self.voiceover(text="To turn that into numbers, the thesis uses a simple <bookmark mark='m'/>model of the light. From a "
                                 "point source, the photons reaching a pixel <bookmark mark='r'/>fall off with distance r, like light "
                                 "from a bulb, and an <bookmark mark='att'/>exponential term accounts for light lost on the way. The "
                                 "model is <bookmark mark='fit'/>fitted to the front and back maps together, by least squares, and the "
                                 "best fit gives the <bookmark mark='unk'/>position, the depth, and the number of photons."):
            self.at("m", Write(model))
            self.at("r", FadeIn(rdef), FadeIn(steps[0]))
            self.at("att", FadeIn(steps[1]), Indicate(model[2], color=YELLOW))
            self.at("fit", FadeIn(steps[2]), Indicate(hf, color=WHITE), Indicate(hb, color=WHITE))
            self.at("unk", FadeIn(steps[3]), Flash(flash, color=YELLOW))
        fade_all(self)


class Thickness(Narrated):
    def construct(self):
        title = Tex("How thick should the shell be?").scale(0.72).to_edge(UP)
        thin = VGroup(Rectangle(width=0.45, height=2.4, color=CER_C, fill_color=CER_C, fill_opacity=0.2),
                      Arrow(1.1 * LEFT, 1.1 * RIGHT, buff=0, color=GAM_C, stroke_width=4)).shift(5.3 * LEFT + 1.2 * UP)
        tl = Tex(r"too thin:\\most gammas\\pass through", font_size=26).next_to(thin, DOWN, buff=0.25)
        thick = Rectangle(width=2.2, height=2.4, color=CER_C, fill_color=CER_C, fill_opacity=0.2).shift(1.9 * LEFT + 1.2 * UP)
        rng = np.random.default_rng(1)
        p = thick.get_center() + 0.3 * LEFT
        walk = [p]
        for _ in range(14):
            walk.append(walk[-1] + 0.25 * np.array([*rng.normal(0, 1, 2), 0]))
        scat = VMobject(stroke_color=LIGHT_C, stroke_width=2).set_points_as_corners([np.clip(w, thick.get_corner(DL) + 0.05, thick.get_corner(UR) - 0.05) for w in walk])
        thl = Tex(r"too thick:\\light scatters,\\more Compton hits", font_size=26).next_to(thick, DOWN, buff=0.25)
        with self.voiceover(text="These materials force a design choice: the shell's thickness. <bookmark mark='thin'/>Too thin, and most "
                                 "gammas pass straight through. <bookmark mark='thick'/>Too thick, and the light <bookmark mark='scat'/>"
                                 "scatters and fades before it reaches the sensors, and more gammas bounce around by Compton scattering, "
                                 "so the position estimate falls apart."):
            self.play(Write(title), run_time=0.8)
            self.at("thin", FadeIn(thin[0]), GrowArrow(thin[1]), FadeIn(tl))
            self.at("thick", FadeIn(thick), FadeIn(thl))
            self.at("scat", Create(scat), run_time=1.2)

        metric = Tex(r"score $=$ fraction of gammas located within 5 mm", font_size=30, color=YELLOW).next_to(VGroup(tl, thl), DOWN, buff=0.45).set_x(-2.6)
        ax = Axes(x_range=[0, 40, 10], y_range=[0, 80, 20], x_length=4.6, y_length=3.0, tips=False,
                  axis_config={"color": GREY_B, "font_size": 24}).to_edge(RIGHT, buff=0.7).shift(0.6 * UP)
        ax.add_coordinates()
        xl = Tex("thickness (mm)", font_size=24).next_to(ax, DOWN, buff=0.35)
        yl = Tex(r"\% within 5 mm", font_size=24).rotate(PI / 2).next_to(ax, LEFT, buff=0.55)
        topt, popt = 27.54, 67.82
        f = lambda t: popt * (1 - np.exp(-t / 9.0)) * np.exp(-max(t - topt, 0) ** 2 / 900) / (1 - np.exp(-topt / 9.0))
        curve = ax.plot(f, x_range=[1, 40], color=CER_C)
        sims = VGroup(*[Dot(ax.c2p(t, f(t)), color=WHITE, radius=0.06) for t in (5, 10, 15, 20, 25, 30, 35)])
        opt = VGroup(DashedLine(ax.c2p(topt, 0), ax.c2p(topt, popt), color=YELLOW), Dot(ax.c2p(topt, popt), color=YELLOW, radius=0.08))
        ol = Tex(r"GLuGAG:Ce: 27.5 mm $\to$ 67.8\%", font_size=26, color=YELLOW).next_to(ax, DOWN, buff=0.75)
        note = Tex(r"curve shape illustrative; optimum from Table 3.2", font_size=22, color=GREY_D).to_edge(DOWN, buff=0.15)
        with self.voiceover(text="So the thesis defines a <bookmark mark='met'/>score that captures both effects: the fraction of "
                                 "incoming gammas whose hit point can be located within, say, five millimetres. To find the best "
                                 "thickness, <bookmark mark='sim'/>simulate a handful of thicknesses, <bookmark mark='fit'/>fit a smooth "
                                 "curve through the scores, and <bookmark mark='max'/>take its maximum. For the ceramic glue gag, that "
                                 "is about twenty seven and a half millimetres, where sixty eight percent of gammas are located within "
                                 "five millimetres."):
            self.at("met", FadeIn(metric, shift=0.1 * UP))
            self.at("sim", Create(ax), FadeIn(xl), FadeIn(yl), LaggedStart(*[FadeIn(d, scale=0.5) for d in sims], lag_ratio=0.1), FadeIn(note), run_time=1.2)
            self.at("fit", Create(curve), run_time=1.0)
            self.at("max", Create(opt), FadeIn(ol))
        fade_all(self)


class Materials(Narrated):
    def construct(self):
        title = Tex("Nine candidate materials").scale(0.72).to_edge(UP)
        ax = Axes(x_range=[0, 80, 20], y_range=[0, 9, 1], x_length=6.4, y_length=5.2, tips=False,
                  axis_config={"color": GREY_B, "include_ticks": False}).shift(1.0 * RIGHT + 0.4 * DOWN)
        xt = VGroup(*[Tex(f"{v}\\%", font_size=22, color=GREY_B).next_to(ax.c2p(v, 0), DOWN, buff=0.12) for v in (0, 20, 40, 60, 80)])
        xl = Tex(r"gammas located within 5 mm, at each material's best thickness", font_size=24).next_to(xt, DOWN, buff=0.12)
        rows = VGroup()
        for k, (name, t, p, cer) in enumerate(MATERIALS):
            y = 8.5 - k
            col = CER_C if cer else NANO_C
            bar = Rectangle(width=ax.c2p(p, 0)[0] - ax.c2p(0, 0)[0], height=0.38, fill_color=col, fill_opacity=0.85, stroke_width=0)
            bar.move_to(ax.c2p(0, y), aligned_edge=LEFT)
            rows.add(VGroup(bar, Tex(name, font_size=24).next_to(bar, LEFT, buff=0.15).set_x(ax.c2p(0, 0)[0] - 0.15, direction=RIGHT),
                            Tex(f"{p:.1f}\\% at {t:.1f} mm", font_size=22, color=GREY_B).next_to(bar, RIGHT, buff=0.12)))
        key = VGroup(VGroup(Square(0.2, fill_color=NANO_C, fill_opacity=1, stroke_width=0), Tex("nanocomposite", font_size=24)).arrange(RIGHT, buff=0.1),
                     VGroup(Square(0.2, fill_color=CER_C, fill_opacity=1, stroke_width=0), Tex("ceramic", font_size=24)).arrange(RIGHT, buff=0.1)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.1).to_corner(UR, buff=0.4).shift(0.5 * DOWN)
        src = Tex("Table 3.2", font_size=22, color=GREY_D).to_corner(DR, buff=0.15)
        with self.voiceover(text="Wilson ran this optimisation for <bookmark mark='nano'/>five nanocomposites and "
                                 "<bookmark mark='cer'/>four transparent ceramics, each simulated in GATE with full tracking of every "
                                 "light photon."):
            self.play(Write(title), FadeIn(xt), FadeIn(xl), FadeIn(src), run_time=0.8)
            self.at("nano", FadeIn(key[0]), LaggedStart(*[AnimationGroup(GrowFromEdge(r[0], LEFT), FadeIn(r[1:])) for r in rows[:5]], lag_ratio=0.15), run_time=1.4)
            self.at("cer", FadeIn(key[1]), LaggedStart(*[AnimationGroup(GrowFromEdge(r[0], LEFT), FadeIn(r[1:])) for r in rows[5:]], lag_ratio=0.15), run_time=1.2)
        with self.voiceover(text="The ceramics win overall, because they are much denser and stop gammas in less material. The best was "
                                 "the garnet <bookmark mark='glu'/>glue gag, cerium doped. The best nanocomposite was <bookmark mark='laf'/>"
                                 "lanthanum fluoride in polystyrene, helped by a high nanoparticle loading and a good refractive index "
                                 "match. These two go forward into a full scanner."):
            self.at("glu", Circumscribe(rows[6], color=CER_C))
            self.at("laf", Circumscribe(rows[3], color=NANO_C))
        fade_all(self)


class Scanner(Narrated):
    def construct(self):
        title = Tex("Finding both ends of the line").scale(0.72).to_edge(UP)
        c = 3.6 * LEFT + 0.3 * DOWN
        r_in, r_out = 1.75, 2.35
        shell = ring(r_in, r_out).move_to(c)
        ticks = VGroup(sipm_ticks(r_in, 52, out=False), sipm_ticks(r_out, 58)).move_to(c)
        specs = VGroup(Tex(r"inner radius 233 mm, length 296 mm", font_size=26),
                       Tex(r"GLuGAG:Ce shell $\approx$ 25 mm thick", font_size=26),
                       Tex(r"104 inner + 116 outer faces, 21 SiPMs each", font_size=26),
                       Tex(r"$14\times14$ pixels of 1 mm per SiPM", font_size=26)
                       ).arrange(DOWN, aligned_edge=LEFT, buff=0.12).to_edge(RIGHT, buff=0.5).shift(2.0 * UP)
        ang = 0.55
        e1 = c + 2.05 * np.array([np.cos(ang), np.sin(ang), 0])
        e2 = c - 2.05 * np.array([np.cos(ang), np.sin(ang), 0])
        spots = VGroup(*[Dot(e, color=LIGHT_C, radius=0.16).set_opacity(0.85) for e in (e1, e2)])
        pair = gamma_pair(c + 0.2 * UP, ang, 2.0)
        with self.voiceover(text="The scanner is sized for the <bookmark mark='head'/>head or for small animals: an inner radius of two "
                                 "hundred and thirty three millimetres, and with glue gag a shell about <bookmark mark='th'/>twenty five "
                                 "millimetres thick. Its surfaces carry <bookmark mark='tiles'/>more than four thousand silicon photomultipliers, "
                                 "every one a grid of one millimetre pixels."):
            self.play(Write(title), DrawBorderThenFill(shell), run_time=1.0)
            self.at("head", FadeIn(specs[0]))
            self.at("th", FadeIn(specs[1]))
            self.at("tiles", FadeIn(specs[2]), FadeIn(specs[3]), Create(ticks))
        with self.voiceover(text="A decay sends two gammas into the shell, and each makes its own <bookmark mark='spots'/>splash of light "
                                 "on the inner and outer sensors."):
            self.at("spots", GrowArrow(pair[0]), GrowArrow(pair[1]), FadeIn(spots, scale=0.4))

        cut = VGroup(*[DashedLine(c + r_in * 0.95 * np.array([np.cos(a), np.sin(a), 0]), c + r_out * 1.05 * np.array([np.cos(a), np.sin(a), 0]),
                                  color=RED, stroke_width=4) for a in (ang + PI / 2, ang - PI / 2)])
        half1 = AnnularSector(inner_radius=r_in, outer_radius=r_out, angle=PI, start_angle=ang - PI / 2, fill_color=CER_C,
                              fill_opacity=0.35, stroke_color=CER_C, stroke_width=2).move_arc_center_to(c)
        half2 = AnnularSector(inner_radius=r_in, outer_radius=r_out, angle=PI, start_angle=ang + PI / 2, fill_color=CER_C,
                              fill_opacity=0.35, stroke_color=CER_C, stroke_width=2).move_arc_center_to(c)
        flat1 = Rectangle(width=4.2, height=0.6, fill_color=CER_C, fill_opacity=0.35, stroke_color=CER_C).move_to(2.6 * RIGHT + 0.4 * DOWN)
        flat2 = flat1.copy().move_to(2.6 * RIGHT + 1.9 * DOWN)
        fs1 = Dot(flat1.get_center() + 0.0 * RIGHT, color=LIGHT_C, radius=0.16).set_opacity(0.85)
        fs2 = Dot(flat2.get_center(), color=LIGHT_C, radius=0.16).set_opacity(0.85)
        ul = Tex(r"each half unrolled into a flat slab, then the same fit", font_size=26).next_to(flat2, DOWN, buff=0.3)
        with self.voiceover(text="To reuse the flat slab method, the algorithm <bookmark mark='cut'/>cuts the ring into two halves, "
                                 "midway between the two splashes. It then <bookmark mark='unroll'/>unrolls each half into a flat slab, "
                                 "mapping angle to distance, so both surfaces line up, and <bookmark mark='fit'/>fits the same light "
                                 "model to the inner and outer maps."):
            self.at("cut", Create(cut), FadeOut(pair))
            self.add(half1, half2)
            self.remove(shell)
            self.wait_until_bookmark("unroll")
            self.play(FadeOut(specs), FadeOut(cut), FadeOut(ticks), ReplacementTransform(half1, flat1), ReplacementTransform(half2, flat2),
                      ReplacementTransform(spots[0], fs1), ReplacementTransform(spots[1], fs2), run_time=1.4)
            self.at("fit", FadeIn(ul), Flash(fs1, color=YELLOW), Flash(fs2, color=YELLOW))
        fade_all(self)

        title2 = Tex("How accurate are the lines?").scale(0.72).to_edge(UP)
        hdr = VGroup(Tex("source position", font_size=26), Tex("centre", font_size=26), Tex(r"50\% radius", font_size=26), Tex(r"75\% radius", font_size=26))
        r1 = VGroup(Tex(r"GLuGAG:Ce, median LOR error", font_size=26, color=CER_C), *[Tex(f"{v} mm", font_size=26) for v in ("1.27", "1.48", "1.62")])
        r2 = VGroup(Tex(r"LaF$_3$:Ce / PS, median LOR error", font_size=26, color=NANO_C), *[Tex(f"{v} mm", font_size=26) for v in ("3.12", "3.59", "4.13")])
        r3 = VGroup(Tex(r"GLuGAG:Ce, ends within 5 mm", font_size=26, color=CER_C), *[Tex(f"{v}\\%", font_size=26) for v in ("81.6", "80.4", "78.8")])
        r4 = VGroup(Tex(r"LaF$_3$:Ce / PS, ends within 5 mm", font_size=26, color=NANO_C), *[Tex(f"{v}\\%", font_size=26) for v in ("62.1", "60.9", "60.1")])
        tab = VGroup(hdr, r1, r2, r3, r4)
        for k, row in enumerate(tab):
            for j, m in enumerate(row):
                m.move_to(np.array([[-3.6, 0.6, 2.6, 4.6][j], 1.6 - 0.65 * k, 0]))
        src = Tex(r"Tables 4.3--4.5 and Ch.\ 7", font_size=22, color=GREY_D).to_edge(DOWN, buff=0.15)
        with self.voiceover(text="It works. With glue gag, the median distance between the estimated line of response and the true "
                                 "source is <bookmark mark='g'/>about one point three to one point six millimetres, getting only slightly "
                                 "worse as the source moves off centre. Lanthanum fluoride, less dense and less bright, gives "
                                 "<bookmark mark='l'/>three to four millimetres. And around <bookmark mark='w'/>eighty percent of glue "
                                 "gag's endpoints land within five millimetres of the truth."):
            self.play(Write(title2), FadeIn(hdr), FadeIn(src), run_time=0.8)
            self.at("g", FadeIn(r1, shift=0.1 * RIGHT))
            self.at("l", FadeIn(r2, shift=0.1 * RIGHT))
            self.at("w", FadeIn(r3, shift=0.1 * RIGHT), FadeIn(r4, shift=0.1 * RIGHT))
        fade_all(self)


class Coincidence(Narrated):
    def construct(self):
        title = Tex("Which flashes belong together?").scale(0.72).to_edge(UP)
        dt, tau = 10.0, 84.0                                   # 10 ns readout, GLuGAG:Ce decay time
        n = 60
        t = np.arange(n) * dt
        onsets = {5: 1.0, 9: 0.7, 13: 0.9, 31: 1.0, 34: 0.6}
        x = np.zeros(n)
        for k, a in onsets.items():
            x[k:] += a * np.exp(-(t[k:] - t[k]) / tau)
        a = np.exp(-dt / tau)
        y = x - a * np.concatenate([[0], x[:-1]])              # exact inverse of the exponential impulse response
        ax1 = Axes(x_range=[0, n * dt, 100], y_range=[0, 2.4, 1], x_length=6.2, y_length=1.9, tips=False,
                   axis_config={"color": GREY_B, "include_ticks": False}).shift(3.0 * RIGHT + 1.35 * UP)
        ax2 = Axes(x_range=[0, n * dt, 100], y_range=[0, 1.1, 1], x_length=6.2, y_length=1.5, tips=False,
                   axis_config={"color": GREY_B, "include_ticks": False}).next_to(ax1, DOWN, buff=0.6)
        wave = VMobject(stroke_color=LIGHT_C, stroke_width=3).set_points_as_corners([ax1.c2p(tt, v) for tt, v in zip(t, x)])
        stems = VGroup(*[Line(ax2.c2p(tt, 0), ax2.c2p(tt, v), color=GAM_C, stroke_width=4) for tt, v in zip(t, y) if v > 0.05])
        thr = DashedLine(ax2.c2p(0, 0.05), ax2.c2p(n * dt, 0.05), color=RED, stroke_width=2)
        l1 = Tex(r"light in one sector, summed every 10 ns", font_size=24, color=LIGHT_C).next_to(ax1, UP, buff=0.12)
        l2 = Tex(r"after deconvolution: one spike per event", font_size=24, color=GAM_C).next_to(ax2, UP, buff=0.12)
        ill = Tex(r"illustrative pulses, $\tau = 84$ ns", font_size=22, color=GREY_D).to_edge(DOWN, buff=0.15)

        c = 3.6 * LEFT + 0.4 * DOWN
        shell = ring(1.7, 2.3).move_to(c)
        secs = VGroup(*[Line(c + 1.6 * np.array([np.cos(q), np.sin(q), 0]), c + 2.4 * np.array([np.cos(q), np.sin(q), 0]), color=WHITE, stroke_width=2)
                        for q in np.linspace(0, TAU, 16, endpoint=False)])
        offs = VGroup(*[DashedLine(c + 1.6 * np.array([np.cos(q), np.sin(q), 0]), c + 2.4 * np.array([np.cos(q), np.sin(q), 0]), color=GREY_B, stroke_width=1.5)
                        for q in np.linspace(0, TAU, 16, endpoint=False) + TAU / 32])
        sl = Tex(r"16 sectors of 22.5$^\circ$\\+ 16 offset by half", font_size=24).next_to(shell, DOWN, buff=0.25)
        with self.voiceover(text="In a real scan, decays arrive constantly, and this scintillator glows for about eighty four nanoseconds "
                                 "after each hit. In one giant detector, <bookmark mark='pile'/>flashes overlap in time, so which "
                                 "flashes belong together? Conventional coincidence logic, built for separate crystals, doesn't apply."):
            self.play(Write(title), DrawBorderThenFill(shell), run_time=0.9)
            self.at("pile", Create(ax1), Create(wave), FadeIn(l1), FadeIn(ill), run_time=1.4)
        with self.voiceover(text="Wilson's method goes in steps. First, split the inner and outer surfaces into "
                                 "<bookmark mark='sec'/>sixteen sectors, plus a <bookmark mark='off'/>second set shifted by half a "
                                 "sector, so a splash on a boundary in one set sits in the middle of a sector in the other. Every ten "
                                 "nanoseconds, the light in each sector is summed, giving thirty two signals."):
            self.at("sec", Create(secs), FadeIn(sl))
            self.at("off", Create(offs))
        with self.voiceover(text="Second, <bookmark mark='dec'/>deconvolve each signal by the scintillator's measured pulse shape. That "
                                 "undoes the slow glow and leaves <bookmark mark='sp'/>one sharp spike at the start of each event, even "
                                 "when the pulses overlapped."):
            self.at("dec", Create(ax2), FadeIn(l2))
            self.at("sp", LaggedStart(*[Create(s) for s in stems], lag_ratio=0.2), run_time=1.2)
        rules = VGroup(Tex(r"1 sector above threshold: single", font_size=26),
                       Tex(r"2 sectors: coincidence $\to$ line of response", font_size=26, color=GAM_C),
                       Tex(r"more than 2: multiple, discarded", font_size=26)
                       ).arrange(DOWN, aligned_edge=LEFT, buff=0.1).next_to(ax2, DOWN, buff=0.25).align_to(ax2, LEFT)
        with self.voiceover(text="Third, apply a <bookmark mark='thr'/>small threshold in each time step and count the sectors above it. "
                                 "<bookmark mark='one'/>One sector means a single gamma. <bookmark mark='two'/>Exactly two means a "
                                 "coincidence, which goes on to the localisation step. <bookmark mark='more'/>More than two is ambiguous, "
                                 "and is set aside."):
            self.at("thr", Create(thr))
            self.at("one", FadeIn(rules[0]))
            self.at("two", FadeIn(rules[1]))
            self.at("more", FadeIn(rules[2]))
        fade_all(self)

        title2 = Tex("How many decays become usable lines?").scale(0.72).to_edge(UP)
        ax = Axes(x_range=[0, 35, 5], y_range=[0, 4, 1], x_length=8.0, y_length=3.6, tips=False,
                  axis_config={"color": GREY_B, "include_ticks": False}).shift(0.8 * RIGHT + 0.5 * DOWN)
        data = [("both gammas interact", 32.79, CER_C), ("detected, true", 17.42, GAM_C), ("missed", 15.37, GREY_B), ("random (false)", 2.08, RED)]
        bars = VGroup()
        for k, (name, v, col) in enumerate(data):
            b = Rectangle(width=ax.c2p(v, 0)[0] - ax.c2p(0, 0)[0], height=0.55, fill_color=col, fill_opacity=0.85, stroke_width=0)
            b.move_to(ax.c2p(0, 3.5 - k), aligned_edge=LEFT)
            bars.add(VGroup(b, Tex(name, font_size=26).next_to(b, LEFT, buff=0.15).set_x(ax.c2p(0, 0)[0] - 0.15, direction=RIGHT),
                            Tex(f"{v:.2f}\\%", font_size=26).next_to(b, RIGHT, buff=0.12)))
        ref = Tex(r"typical whole-body scanner: $\sim$2\% coincidence sensitivity", font_size=26, color=YELLOW).next_to(ax, DOWN, buff=0.35)
        src = Tex(r"Table 5.1: \% of all decays, GLuGAG:Ce, mean of 5 runs", font_size=22, color=GREY_D).to_edge(DOWN, buff=0.15)
        with self.voiceover(text="In simulation, both gammas reach the shell in <bookmark mark='b0'/>about a third of all decays. The "
                                 "algorithm correctly finds <bookmark mark='b1'/>seventeen point four percent of all decays as true "
                                 "coincidences, <bookmark mark='b2'/>misses fifteen percent, mostly gammas that left too little light, "
                                 "and adds <bookmark mark='b3'/>two percent of false, random pairs. For comparison, a typical whole body "
                                 "scanner records <bookmark mark='ref'/>around two percent."):
            self.play(Write(title2), FadeIn(src), run_time=0.8)
            for k, m in enumerate(["b0", "b1", "b2", "b3"]):
                self.at(m, GrowFromEdge(bars[k][0], LEFT), FadeIn(bars[k][1:]))
            self.at("ref", FadeIn(ref, shift=0.1 * UP))
        fade_all(self)


class Images(Narrated):
    def construct(self):
        title = Tex("Does it make images?").scale(0.72).to_edge(UP)
        c = 4.0 * LEFT + 0.4 * DOWN
        fov = Circle(radius=2.2, color=GREY_B, stroke_width=3).move_to(c)
        srcs = [c, c + 0.5 * 2.2 * RIGHT, c + 0.75 * 2.2 * UP]
        dots = VGroup(*[Dot(p, color=RED, radius=0.07) for p in srcs])
        sl = VGroup(Tex("centre", font_size=24), Tex(r"50\% radius", font_size=24), Tex(r"75\% radius", font_size=24))
        sl[0].next_to(dots[0], DOWN, buff=0.42)
        sl[1].next_to(dots[1], DOWN, buff=0.42)
        sl[2].next_to(dots[2], RIGHT, buff=0.42)
        setup = VGroup(Tex(r"three 2 mm $^{18}$F sources, 3 MBq each", font_size=26),
                       Tex(r"3 s of scan $\approx$ 27 million decays", font_size=26),
                       Tex(r"full optical-photon simulation (GATE)", font_size=26),
                       Tex(r"reconstruction in STIR: 2D FBP, 3D FBP, OSEM", font_size=26)
                       ).arrange(DOWN, aligned_edge=LEFT, buff=0.12).to_edge(RIGHT, buff=0.5).shift(1.7 * UP)
        with self.voiceover(text="The final test puts it all together. <bookmark mark='src'/>Three tiny sources sit in the field of "
                                 "view: at the centre, and at half and three quarters of the radius. <bookmark mark='scan'/>Three seconds "
                                 "of scanning, about twenty seven million decays, are simulated photon by photon. The lines of response "
                                 "go into the open source <bookmark mark='stir'/>STIR toolkit, after corrections, and are reconstructed "
                                 "with filtered back projection and with the iterative O S E M algorithm."):
            self.play(Write(title), Create(fov), run_time=0.8)
            self.at("src", LaggedStart(*[FadeIn(d, scale=0.5) for d in dots], lag_ratio=0.3), FadeIn(sl), FadeIn(setup[0]))
            self.at("scan", FadeIn(setup[1]), FadeIn(setup[2]))
            self.at("stir", FadeIn(setup[3]))

        blobs = Group(*[blob(sx, sy).set_height(0.7).move_to(p) for (sx, sy), p in zip([(0.17, 0.17), (0.2, 0.2), (0.2, 0.22)], srcs)])
        ill = Tex("blobs illustrative", font_size=22, color=GREY_D).next_to(fov, DOWN, buff=0.2)
        ax = Axes(x_range=[0, 3, 1], y_range=[0, 5, 1], x_length=5.0, y_length=2.4, tips=False,
                  axis_config={"color": GREY_B, "include_ticks": False}).to_edge(RIGHT, buff=0.9).shift(1.6 * DOWN)
        yt = VGroup(*[Tex(f"{v} mm", font_size=22).next_to(ax.c2p(0, v), LEFT, buff=0.1) for v in (2, 4)])
        grid = VGroup(*[DashedLine(ax.c2p(0, v), ax.c2p(3, v), color=GREY_D, stroke_width=1) for v in (2, 4)])
        cols = [RED_B, YELLOW, BLUE_B]
        bars = VGroup()
        for k, vals in enumerate(OSEM):
            for j, v in enumerate(vals):
                bars.add(Rectangle(width=0.32, height=ax.c2p(0, v)[1] - ax.c2p(0, 0)[1], fill_color=cols[j], fill_opacity=0.85, stroke_width=0)
                         .move_to(ax.c2p(k + 0.5 + (j - 1) * 0.22, 0), aligned_edge=DOWN))
        xl = VGroup(*[Tex(s, font_size=22).next_to(ax.c2p(k + 0.5, 0), DOWN, buff=0.1) for k, s in enumerate(["centre", r"50\%", r"75\%"])])
        key = VGroup(*[VGroup(Square(0.16, fill_color=cc, fill_opacity=1, stroke_width=0), Tex(s, font_size=22)).arrange(RIGHT, buff=0.08)
                       for cc, s in zip(cols, "xyz")]).arrange(RIGHT, buff=0.3).next_to(ax, UP, buff=0.15)
        bl = Tex(r"OSEM resolution (FWHM)", font_size=26).next_to(key, UP, buff=0.12)
        src = Tex(r"Tables 6.2--6.4, corrected", font_size=22, color=GREY_D).to_corner(DR, buff=0.15)
        with self.voiceover(text="All three <bookmark mark='img'/>sources come out as clean, compact spots. Measured as full width at half "
                                 "maximum, the O S E M images resolve them to <bookmark mark='fw'/>under four millimetres in almost "
                                 "every direction: from about two point four millimetres along the scanner axis at the centre, to "
                                 "four point four at three quarters of the radius. Filtered back projection smears a little more in "
                                 "one direction."):
            self.at("img", FadeOut(dots), FadeIn(blobs), FadeIn(ill), run_time=1.0)
            self.at("fw", FadeOut(setup), Create(ax), FadeIn(yt), FadeIn(grid), FadeIn(bl), FadeIn(key), FadeIn(xl), FadeIn(src),
                    LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars], lag_ratio=0.08), run_time=1.6)
        fade_all(self)


class Outro(Narrated):
    def construct(self):
        title = Tex("What the thesis shows").scale(0.72).to_edge(UP)
        res = VGroup(Tex(r"$\bullet$ a continuous shell PET scanner is feasible, in simulation", font_size=30),
                     Tex(r"$\bullet$ thickness tuned per material by a localisation score", font_size=30),
                     Tex(r"$\bullet$ $\sim$1.3--1.6 mm line errors with a ceramic garnet", font_size=30),
                     Tex(r"$\bullet$ 17\% of decays become true lines, vs $\sim$2\% whole-body", font_size=30),
                     Tex(r"$\bullet$ point sources resolved to about 4 mm or better (OSEM)", font_size=30)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.16).next_to(title, DOWN, buff=0.45)
        with self.voiceover(text="In short: a <bookmark mark='r0'/>continuous shell scanner works, at least in simulation. The thickness "
                                 "can be <bookmark mark='r1'/>tuned to each material, the lines of response are <bookmark mark='r2'/>placed "
                                 "to within about a millimetre and a half, <bookmark mark='r3'/>sensitivity is high, and "
                                 "<bookmark mark='r4'/>point sources are resolved to about four millimetres or better."):
            self.play(Write(title), run_time=0.8)
            for k in range(5):
                self.at(f"r{k}", FadeIn(res[k], shift=0.1 * RIGHT))
        nxt = VGroup(Tex(r"next: full NEMA performance tests", font_size=28, color=TEAL_L),
                     Tex(r"correct for positron range to sharpen images", font_size=28, color=TEAL_L),
                     Tex(r"optical simulation is costly: only 3 s of scan here", font_size=28, color=TEAL_L)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.12).next_to(res, DOWN, buff=0.45).align_to(res, LEFT)
        with self.voiceover(text="The next steps are <bookmark mark='n0'/>standard NEMA performance tests, <bookmark mark='n1'/>correcting "
                                 "for positron range to sharpen the images, and working around the <bookmark mark='n2'/>huge computing cost "
                                 "of simulating every light photon. But the case is made: cheaper, shapeable scintillators open a very "
                                 "different path to high sensitivity PET."):
            for k in range(3):
                self.at(f"n{k}", FadeIn(nxt[k], shift=0.1 * RIGHT))
        self.play(FadeOut(res), FadeOut(nxt), FadeOut(title))
        cite = VGroup(Tex(r"High-Sensitivity PET using Optimised Continuous Cylindrical Shell\\Nanocomposite and Transparent Ceramic Scintillators", font_size=32),
                      Tex(CITE, font_size=26, color=GREY_B)).arrange(DOWN, buff=0.3)
        with self.voiceover(text="Thanks for watching."):
            self.play(FadeIn(cite), run_time=1.0)
        self.wait(0.8)
        fade_all(self)
