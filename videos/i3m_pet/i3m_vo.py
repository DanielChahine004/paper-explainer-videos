"""Explainer: the i3M Valencia Detectors for Molecular Imaging Lab (A. J. Gonzalez, J. M. Benlloch) and its
monolithic PET programme, from a literature-review note on the group.

Numbers are checked against the papers: Moliner 2012 (MAMMI), Pajak 2016 (Albira),
Gsell 2020 (Bruker 7 T insert), Gonzalez 2018 (tube feasibility), Freire 2022 (tube prototype), Cucarella 2026
(semi-monolithic scanner), Freire 2026 (DeepBreast), Ilisie 2018 and Valladares 2024 (Compton / TOF layers).
Reused figures (DESIGN.md §7): photos and one measured light profile from the CC BY papers only (Gonzalez 2018,
Freire 2026, Cucarella 2026). Everything else is redrawn from the papers' numbers. The light-sharing curves
are computed here from a point-source solid-angle model and are illustrative.
Visuals are cued to the narration with <bookmark/> tags and self.at() (see ../DESIGN.md).
Render with render.sh, or one scene: manim -ql i3m_vo.py Light
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import *  # noqa: E402,F401

HERE = Path(__file__).resolve().parent
LYSO_C, SIPM_C, GAM_C, LIGHT_C, BAD_C = "#9fd3ff", BLUE_L, "#7ee081", "#f5d76e", "#ff5c5c"
OLD_C, NEW_C = GREY_B, TEAL_L
C_TUBE = r"Fig.~3B: Gonz\'alez et al., Front.\ Med.\ 2018 (CC BY)"
C_DB = r"Freire et al., EJNMMI Phys.\ 2026 (CC BY 4.0)"
C_SM = r"Fig.~1: Cucarella et al., IEEE TRPMS 2026 (CC BY 4.0)"


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


def hbars(rows, xmax, width=4.6, bar_h=0.42, pitch=0.7, fs=26, fmt="{:g}"):
    g = VGroup()
    for k, (lab, v, col) in enumerate(rows):
        b = Rectangle(width=max(width * v / xmax, 0.02), height=bar_h, fill_color=col, fill_opacity=0.9, stroke_width=0)
        b.move_to(np.array([0, -k * pitch, 0]), aligned_edge=LEFT)
        t = Tex(lab, font_size=fs).next_to(b.get_left(), LEFT, buff=0.15)
        n = Tex(r"\textbf{" + fmt.format(v) + "}", font_size=fs + 2).next_to(b, RIGHT, buff=0.1)
        g.add(VGroup(b, t, n))
    return g


def grow(rows, lag=0.25):
    return LaggedStart(*[AnimationGroup(GrowFromEdge(r[0], LEFT), FadeIn(r[1:])) for r in rows], lag_ratio=lag)


# ---- light sharing in a 50 mm wide, 10 mm thick monolithic block read out on its exit face -------------------
BW, BT, NPIX = 50.0, 10.0, 16
_XS = np.linspace(-BW / 2, BW / 2, 801)


def light_profile(x0, h, reflective=False):
    """Light per unit length on the exit face (row projection of a point source at height h above it): the
    solid-angle kernel h / ((x - x0)^2 + h^2). Black walls absorb; reflective walls add mirror sources."""
    srcs = [x0] + ([BW - x0, -BW - x0] if reflective else [])
    return sum(h / ((_XS - s) ** 2 + h ** 2) for s in srcs)


def pixel_sums(x0, h, reflective=False):
    prof = light_profile(x0, h, reflective)
    edges = np.linspace(-BW / 2, BW / 2, NPIX + 1)
    return np.array([prof[(_XS >= a) & (_XS < b)].sum() for a, b in zip(edges[:-1], edges[1:])])


def centroid(x0, h, reflective=False):
    p = pixel_sums(x0, h, reflective)
    c = np.linspace(-BW / 2, BW / 2, NPIX + 1)
    c = (c[:-1] + c[1:]) / 2
    return (p * c).sum() / p.sum()


def ring_block(a, r0, r1, w0, w1, s, center, **kw):
    """A trapezoidal block of a polygon ring: inner face width w0 at apothem r0, outer face w1 at r1 (mm)."""
    t, n = np.array([-np.sin(a), np.cos(a), 0]), np.array([np.cos(a), np.sin(a), 0])
    pts = [center + s * (r0 * n - w0 / 2 * t), center + s * (r0 * n + w0 / 2 * t),
           center + s * (r1 * n + w1 / 2 * t), center + s * (r1 * n - w1 / 2 * t)]
    return Polygon(*pts, **kw)


# ---- pictograms: draw the fact instead of listing it (DESIGN.md §1c) -----------------------------------------
def icon_blocks(r=0.5, n=12, color=OLD_C):
    """A ring of n separate blocks with gaps."""
    return VGroup(*[ring_block(k * TAU / n, 0.78 * r, r, 2 * 0.78 * r * np.tan(PI / n) * 0.75, 2 * r * np.tan(PI / n) * 0.8, 1,
                               ORIGIN, fill_color=color, fill_opacity=0.5, stroke_color=color, stroke_width=1.5) for k in range(n)])


def icon_tube(r=0.5, n=10, color=NEW_C):
    outer = RegularPolygon(n, color=color).scale(r / np.cos(PI / n))
    return Difference(outer, Circle(radius=0.72 * r), fill_color=color, fill_opacity=0.5, stroke_color=color, stroke_width=1.5)


def icon_glued(r=0.5, n=14, color=NEW_C):
    segs = VGroup(*[AnnularSector(inner_radius=0.85 * r, outer_radius=r, angle=TAU / n, start_angle=k * TAU / n, fill_color=color,
                                  fill_opacity=0.5, stroke_width=0) for k in range(n)])
    joints = VGroup(*[Line(0.85 * r * np.array([np.cos(a), np.sin(a), 0]), r * np.array([np.cos(a), np.sin(a), 0]), color=YELLOW,
                           stroke_width=2) for a in np.arange(n) * TAU / n])
    return VGroup(segs, joints)


def icon_layers(r=0.5):
    """A scatter square inside a ring of blocks: the two-layer Compton/TOF design."""
    return VGroup(icon_blocks(r, 14, LYSO_C), Square(0.6 * r, color=ORANGE_L, stroke_width=3))


def icon_net(w=0.9, h=0.6, color=NEW_C):
    cols = [np.linspace(-h / 2, h / 2, k) for k in (3, 4, 2)]
    xs = np.linspace(-w / 2, w / 2, 3)
    nodes = [[np.array([x, y, 0]) for y in ys] for x, ys in zip(xs, cols)]
    edges = VGroup(*[Line(a, b, color=color, stroke_width=1, stroke_opacity=0.6) for L, R in zip(nodes[:-1], nodes[1:]) for a in L for b in R])
    dots = VGroup(*[Dot(p, radius=0.045, color=color) for col in nodes for p in col])
    return VGroup(edges, dots)


def icon_fwhm(w=0.7, color=NEW_C):
    ax = lambda x: np.array([x * w / 2, 0.45 * np.exp(-x * x * 4) - 0.2, 0])
    curve = VMobject(color=color, stroke_width=3).set_points_smoothly([ax(x) for x in np.linspace(-1, 1, 25)])
    half = np.sqrt(np.log(2) / 4)
    arr = DoubleArrow(ax(-half) + LEFT * 0.08, ax(half) + RIGHT * 0.08, buff=0, color=WHITE, stroke_width=2, tip_length=0.08)
    return VGroup(curve, arr)


def icon_sens(r=0.32, color=NEW_C):
    ring = Circle(radius=r, color=color, stroke_width=4)
    rays = VGroup(*[Line(ORIGIN, (r - 0.04) * np.array([np.cos(a), np.sin(a), 0]), color=GAM_C, stroke_width=2) for a in (0.4, 0.4 + PI)])
    return VGroup(ring, rays, Dot(ORIGIN, radius=0.05, color=YELLOW))


def icon_doi(color=LIGHT_C):
    blk = Rectangle(width=0.3, height=0.6, color=LYSO_C, fill_opacity=0.2, stroke_width=2)
    return VGroup(blk, DoubleArrow(blk.get_bottom(), blk.get_top(), buff=0.05, color=color, stroke_width=3, tip_length=0.1))


def icon_energy(color=ORANGE_L):
    pts = [np.array([x * 0.35, 0.5 * np.exp(-(x - 0.6) ** 2 * 6) + 0.12 * np.exp(-(x + 0.4) ** 2) - 0.25, 0]) for x in np.linspace(-1, 1.3, 30)]
    return VGroup(Line(LEFT * 0.38 + DOWN * 0.27, RIGHT * 0.48 + DOWN * 0.27, color=GREY_B, stroke_width=2),
                  VMobject(color=color, stroke_width=3).set_points_smoothly(pts))


def icon_rate(color=TEAL_L):
    pts = [np.array([x * 0.7 - 0.35, 0.5 * x * np.exp(1 - 2.2 * x) - 0.25, 0]) for x in np.linspace(0, 1, 25)]
    return VGroup(Line(LEFT * 0.38 + DOWN * 0.27, RIGHT * 0.4 + DOWN * 0.27, color=GREY_B, stroke_width=2),
                  VMobject(color=color, stroke_width=3).set_points_smoothly(pts))


def icon_clock(crossed=False, color=GREY_A):
    g = VGroup(Circle(radius=0.28, color=color, stroke_width=3), Line(ORIGIN, UP * 0.2, color=color, stroke_width=3),
               Line(ORIGIN, RIGHT * 0.14, color=color, stroke_width=3))
    if crossed:
        g.add(Line(UL * 0.3, DR * 0.3, color=BAD_C, stroke_width=4))
    return g


def icon_grid(n=5, s=0.12):
    val = np.exp(-((np.arange(n)[None] - 1.6) ** 2 + (np.arange(n)[:, None] - 2.4) ** 2) / 1.5)
    cells = VGroup(*[Square(s, stroke_width=0.5, stroke_color=GREY_D, fill_color=LIGHT_C, fill_opacity=0.1 + 0.85 * val[r, c])
                     .move_to(np.array([c * s, -r * s, 0])) for r in range(n) for c in range(n)])
    rows = VGroup(*[Rectangle(width=0.05 + 0.3 * val[r].sum() / val.sum(1).max(), height=s * 0.8, fill_color=ORANGE_L, fill_opacity=0.9,
                              stroke_width=0).move_to(np.array([n * s - s / 2 + 0.06, -r * s, 0]), aligned_edge=LEFT) for r in range(n)])
    cols = VGroup(*[Rectangle(width=s * 0.8, height=0.05 + 0.3 * val[:, c].sum() / val.sum(0).max(), fill_color=TEAL_L, fill_opacity=0.9,
                              stroke_width=0).move_to(np.array([c * s, s / 2 + 0.06, 0]), aligned_edge=DOWN) for c in range(n)])
    return VGroup(cells, rows, cols)


def icon_painted(color=LYSO_C):
    blk = Rectangle(width=0.8, height=0.45, fill_color=color, fill_opacity=0.2, stroke_width=0)
    walls = VGroup(Line(blk.get_corner(UL), blk.get_corner(UR)), Line(blk.get_corner(UL), blk.get_corner(DL)),
                   Line(blk.get_corner(UR), blk.get_corner(DR))).set_stroke(GREY_E, 6)
    sens = Rectangle(width=0.8, height=0.06, fill_color=SIPM_C, fill_opacity=1, stroke_width=0).next_to(blk, DOWN, buff=0)
    cone = VGroup(*[Line(blk.get_center() + UP * 0.05, blk.get_bottom() + RIGHT * dx, color=LIGHT_C, stroke_width=1.5) for dx in (-0.25, 0, 0.25)])
    return VGroup(blk, walls, sens, cone)


def tile(icon, text, w=2.9):
    icon = icon.copy().scale_to_fit_height(min(icon.height, 0.6))
    t = Tex(text, font_size=26)
    g = VGroup(icon, t).arrange(RIGHT, buff=0.25)
    box = RoundedRectangle(corner_radius=0.1, width=max(w, g.width + 0.35), height=0.85, stroke_color=GREY_D, stroke_width=1.5)
    return VGroup(box, g.move_to(box))


def fwhm_inset(tracker, fwhm, color, mm=8.0, width=3.4, height=1.2):
    """A point source's blur on a fixed mm scale: a unit-peak Gaussian whose FWHM (mm) is fwhm(tracker),
    with the half-maximum arrow and a live value, so the eye sees the spot widen as the source moves."""
    ax = Axes(x_range=[-mm, mm, 4], y_range=[0, 1.15, 0.5], x_length=width, y_length=height, tips=False,
              axis_config={"color": GREY_B, "include_ticks": False})
    sig = lambda: fwhm(tracker.get_value()) / 2.3548
    curve = always_redraw(lambda: ax.plot(lambda x: np.exp(-x * x / (2 * sig() ** 2)), x_range=[-mm, mm], color=color, stroke_width=4))
    fill = always_redraw(lambda: ax.get_area(ax.plot(lambda x: np.exp(-x * x / (2 * sig() ** 2)), x_range=[-mm, mm]), color=color, opacity=0.2))
    half = always_redraw(lambda: DoubleArrow(ax.c2p(-fwhm(tracker.get_value()) / 2, 0.5), ax.c2p(fwhm(tracker.get_value()) / 2, 0.5),
                                             buff=0, color=WHITE, stroke_width=3, tip_length=0.12))
    val = always_redraw(lambda: VGroup(DecimalNumber(fwhm(tracker.get_value()), num_decimal_places=1, font_size=30),
                                       Tex(r"mm", font_size=24)).arrange(RIGHT, buff=0.08).next_to(ax.c2p(mm, 1.0), LEFT, buff=0.0))
    scale = VGroup(Line(ax.c2p(-mm, -0.08), ax.c2p(-mm + 4, -0.08), color=GREY_B, stroke_width=3),
                   Tex(r"4 mm", font_size=18, color=GREY_B))
    scale[1].next_to(scale[0], DOWN, buff=0.05)
    return VGroup(ax, fill, curve, half, val, scale)


def dim_arrow(a, b, text, side=UP, color=GREY_A, fs=24, buff=0.1):
    arr = DoubleArrow(a, b, buff=0, color=color, stroke_width=2, tip_length=0.12)
    return VGroup(arr, Tex(text, font_size=fs, color=color).next_to(arr, side, buff=buff))


class Opening(Narrated):
    def construct(self):
        title = Tex(r"\textbf{i3M Valencia}", font_size=58)
        sub = Tex(r"Detectors for Molecular Imaging Lab", font_size=32, color=GREY_B)
        who = Tex(r"A.\,J.\ Gonz\'alez (lead) \quad J.\,M.\ Benlloch (director)", font_size=26, color=GREY_B)
        VGroup(title, sub, who).arrange(DOWN, buff=0.2).to_edge(UP, buff=0.4)
        line = NumberLine(x_range=[2010, 2027, 2], length=12, color=GREY_B, include_numbers=True, font_size=22,
                          decimal_number_config={"group_with_commas": False, "num_decimal_places": 0}).shift(DOWN * 0.9)
        events = [(2012, icon_blocks(0.42, 12), "MAMMI", 1), (2016, icon_blocks(0.32, 8), "Albira", -1), (2018, icon_tube(0.36), "idea", 1),
                  (2020, icon_blocks(0.32, 8, SIPM_C), r"7\,T", -1), (2022, icon_tube(0.42), "tube", 1), (2024, icon_layers(0.4), "TOF", -1),
                  (2026, icon_glued(0.45), "DeepBreast", 1)]
        marks = VGroup()
        for yr, ic, lab, side in events:
            d = Dot(line.n2p(yr), color=GREY_A, radius=0.07)
            ic.move_to(line.n2p(yr) + (UP * 1.05 if side > 0 else DOWN * 1.25))
            t = Tex(lab, font_size=22, color=GREY_B).next_to(ic, UP if side > 0 else DOWN, buff=0.1)
            marks.add(VGroup(d, ic, t))
        foot = VGroup(Tex(r"\textbf{$>$10 years} monolithic", font_size=30),
                      Tex(r"Oncovision $\cdot$ Bruker", font_size=26, color=GREY_B)).arrange(RIGHT, buff=1.2).to_edge(DOWN, buff=0.3)
        with self.voiceover(text="This video is about one lab: <bookmark mark='t'/>the Detectors for Molecular Imaging Lab at i3M in "
                                 "Valencia, <bookmark mark='w'/>led by Antonio González, with José Benlloch as institute director. "
                                 "<bookmark mark='y'/>For more than a decade it has built PET from monolithic crystals, single "
                                 "blocks of scintillator instead of arrays of tiny pixels. <bookmark mark='l'/>The thread runs from "
                                 "a breast ring of separate blocks in twenty twelve, <bookmark mark='m'/>through a rodent scanner made "
                                 "of one crystal tube, <bookmark mark='n'/>to a breast ring of curved crystals glued into one. "
                                 "<bookmark mark='c'/>Along the way came a spin-off, Oncovision, and a preclinical line now sold by "
                                 "Bruker."):
            self.wait_until_bookmark("t")
            self.play(Write(title), FadeIn(sub), run_time=1.0)
            self.at("w", FadeIn(who))
            self.at("y", Create(line), FadeIn(foot[0]), run_time=1.0)
            self.at("l", FadeIn(marks[0], scale=0.8), FadeIn(marks[1], scale=0.8))
            self.at("m", FadeIn(marks[2], scale=0.8), FadeIn(marks[3], scale=0.8), FadeIn(marks[4], scale=0.8))
            self.at("n", FadeIn(marks[5], scale=0.8), FadeIn(marks[6], scale=0.8))
            self.at("c", FadeIn(foot[1]))
        self.wait(0.5)
        fade_all(self)


class Light(Narrated):
    def construct(self):
        sx, ht = 0.11, 1.6
        blk = Rectangle(width=BW * sx, height=ht, fill_color=LYSO_C, fill_opacity=0.15, stroke_color=LYSO_C).move_to(LEFT * 3.4 + UP * 1.2)
        x_of = lambda mm: blk.get_center()[0] + mm * sx
        y_of = lambda h: blk.get_bottom()[1] + ht * h / BT
        pix = VGroup(*[Rectangle(width=BW * sx / NPIX * 0.9, height=0.12, fill_color=SIPM_C, fill_opacity=1, stroke_width=0)
                       .move_to(np.array([x_of(-BW / 2 + (k + 0.5) * BW / NPIX), blk.get_bottom()[1] - 0.08, 0])) for k in range(NPIX)])
        walls = VGroup(Line(blk.get_corner(UL), blk.get_corner(DL), color=GREY_E, stroke_width=8),
                       Line(blk.get_corner(UR), blk.get_corner(DR), color=GREY_E, stroke_width=8),
                       Line(blk.get_corner(UL), blk.get_corner(UR), color=GREY_E, stroke_width=8))
        wl = Tex(r"black paint", font_size=24, color=GREY_B).next_to(blk, UP, buff=0.15)
        x0, h, refl = ValueTracker(0.0), ValueTracker(5.0), ValueTracker(0.0)
        base_y = blk.get_bottom()[1] - 0.3
        norm = pixel_sums(0.0, 5.0).max()

        def bars():
            p = pixel_sums(x0.get_value(), h.get_value(), refl.get_value() > 0.5) / norm
            return VGroup(*[Rectangle(width=BW * sx / NPIX * 0.8, height=max(1.6 * v, 0.01), fill_color=LIGHT_C, fill_opacity=0.85,
                                      stroke_width=0).move_to(np.array([pix[k].get_center()[0], base_y, 0]), aligned_edge=UP)
                            for k, v in enumerate(p)])

        hist = always_redraw(bars)
        src = always_redraw(lambda: Dot(np.array([x_of(x0.get_value()), y_of(h.get_value()), 0]), color=YELLOW, radius=0.08))
        est = always_redraw(lambda: Triangle(color=BAD_C, fill_opacity=1).scale(0.1).rotate(PI)
                            .move_to(np.array([x_of(centroid(x0.get_value(), h.get_value(), refl.get_value() > 0.5)), base_y + 0.2, 0])))
        dims = VGroup(Tex(r"\textbf{50 mm}", font_size=24).next_to(walls[2], UP, buff=0.5),
                      Tex(r"\textbf{10}", font_size=24).next_to(blk, LEFT, buff=0.15))
        ax = Axes(x_range=[-25, 25, 25], y_range=[-25, 25, 25], x_length=4.4, y_length=4.4, tips=False,
                  axis_config={"color": GREY_B, "font_size": 20, "include_numbers": True}).move_to(RIGHT * 3.6 + DOWN * 0.1)
        axl = VGroup(Tex(r"true $x$ (mm)", font_size=22, color=GREY_B).next_to(ax, DOWN, buff=0.15),
                     Tex(r"centroid", font_size=22, color=BAD_C).next_to(ax, UP, buff=0.15))
        diag = DashedLine(ax.c2p(-25, -25), ax.c2p(25, 25), color=GREY_C)
        xs = np.linspace(-24.5, 24.5, 50)
        c_black = VMobject(color=NEW_C, stroke_width=4).set_points_smoothly([ax.c2p(x, centroid(x, 5.0)) for x in xs])
        cl = Tex(r"compressed at both edges", font_size=24, color=NEW_C).next_to(ax.c2p(-25, 25), DR, buff=0.2)
        note = Tex(r"model: $h/((x-x_0)^2+h^2)$ per face, \textbf{16} pixels", font_size=20, color=GREY_B).to_edge(DOWN, buff=0.2)
        depth_l = Tex(r"near the sensor $\Rightarrow$ narrow", font_size=26, color=LIGHT_C).move_to(LEFT * 3.4 + DOWN * 2.4)
        with self.voiceover(text="Start with why monolithic crystals are hard. <bookmark mark='b'/>Here is a block fifty "
                                 "millimetres wide and ten thick, with photodetectors on its bottom face. <bookmark mark='g'/>A "
                                 "gamma ray interacts inside it, and the light spreads into a peak across the pixels. "
                                 "<bookmark mark='x'/>Move the interaction, and the peak moves with it, so the centroid gives "
                                 "position. <bookmark mark='h'/>Move it toward the sensor and the peak narrows, so the width gives "
                                 "depth. <bookmark mark='p'/>i3M paints the other faces black, so light that hits them is lost "
                                 "rather than bounced back, which keeps that shape intact."):
            self.play(FadeIn(blk), FadeIn(pix), run_time=0.8)
            self.at("b", FadeIn(dims))
            self.at("g", FadeIn(src, scale=2), FadeIn(hist), FadeIn(est))
            self.at("x", x0.animate.set_value(-12.0), run_time=1.5)
            self.play(x0.animate.set_value(6.0), run_time=1.5)
            self.at("h", h.animate.set_value(1.5), run_time=1.5)
            self.play(h.animate.set_value(8.5), run_time=1.5)
            self.play(h.animate.set_value(5.0), x0.animate.set_value(0.0), run_time=1.0)
            self.at("p", Create(walls), FadeIn(wl), FadeIn(note))
        with self.voiceover(text="The trouble is the edges. <bookmark mark='e'/>Near a side face, half the light is missing, so the "
                                 "centroid is dragged toward the middle. <bookmark mark='a'/>Plotting the centroid against the true "
                                 "position, <bookmark mark='c'/>positions bunch inward near both edges. <bookmark mark='r'/>This is the "
                                 "edge effect, and every design in this story is, in part, an answer to it."):
            self.at("e", x0.animate.set_value(22.0), run_time=2.0)
            self.at("a", Create(ax), FadeIn(axl), Create(diag))
            self.at("c", Create(c_black), FadeIn(cl), run_time=1.5)
            self.at("r", Indicate(c_black, color=YELLOW, scale_factor=1.0))
        self.wait(0.5)
        fade_all(self)


class Mammi(Narrated):
    def construct(self):
        c, s = LEFT * 3.6 + DOWN * 0.3, 0.026
        blocks = VGroup(*[ring_block(k * TAU / 12, 93, 103, 40, 50, s, c, fill_color=LYSO_C, fill_opacity=0.35, stroke_color=LYSO_C,
                                     stroke_width=2) for k in range(12)])
        pmts = VGroup(*[ring_block(k * TAU / 12, 103.5, 112, 50, 50, s, c, fill_color=GREY_D, fill_opacity=1, stroke_width=0)
                        for k in range(12)])
        title = Tex(r"\textbf{MAMMI} (2012): breast PET", font_size=34).to_edge(UP, buff=0.35)
        bore = dim_arrow(c + LEFT * 93 * s, c + RIGHT * 93 * s, r"\textbf{186 mm}")
        # one block, enlarged: a truncated pyramid side-on, with its photomultiplier
        k = 0.045
        o = RIGHT * 3.2 + UP * 1.5
        pyr = Polygon(o + k * np.array([-20, 5, 0]), o + k * np.array([20, 5, 0]), o + k * np.array([25, -5, 0]), o + k * np.array([-25, -5, 0]),
                      fill_color=LYSO_C, fill_opacity=0.35, stroke_color=LYSO_C)
        dims = VGroup(dim_arrow(o + k * np.array([-20, 8, 0]), o + k * np.array([20, 8, 0]), r"\textbf{40}"),
                      dim_arrow(o + k * np.array([-25, -14, 0]), o + k * np.array([25, -14, 0]), r"\textbf{50}", side=DOWN),
                      dim_arrow(o + k * np.array([-30, -5, 0]), o + k * np.array([-30, 5, 0]), r"\textbf{10}", side=LEFT))
        pmt = Rectangle(width=50 * k, height=0.55, fill_color=GREY_D, fill_opacity=1, stroke_width=0).next_to(pyr, DOWN, buff=0.02)
        anodes = VGroup(*[Square(0.04, fill_color=GREY_B, fill_opacity=1, stroke_width=0) for _ in range(64)]).arrange_in_grid(8, 8, buff=0.025)
        anodes.move_to(pmt)
        dims[1].next_to(pmt, DOWN, buff=0.08)
        outs = VGroup(*[Arrow(pmt.get_right() + UP * y, pmt.get_right() + UP * y + RIGHT * 0.6, buff=0.05, color=LIGHT_C,
                              stroke_width=3, max_tip_length_to_length_ratio=0.3) for y in (0.24, 0.14, 0.04, -0.06, -0.24)])
        # five Anger-network outputs: four corner signals give E and the centroid, the fifth the second moment
        b4 = Brace(outs[:4], RIGHT, buff=0.05, color=GREY_B)
        outl = VGroup(Tex(r"\textbf{64} $\to$ \textbf{5}", font_size=26, color=LIGHT_C),
                      VGroup(b4, MathTex(r"X^\pm, Y^\pm \to E,\ \bar{x},\ \bar{y}", font_size=26).next_to(b4, RIGHT, buff=0.08)),
                      MathTex(r"\sigma \to \text{depth}", font_size=26).next_to(outs[4], RIGHT, buff=0.12))
        outl[2].next_to(b4, DOWN, buff=0.04, aligned_edge=LEFT).match_y(outs[4]).shift(DOWN * 0.08)
        outl[0].next_to(outl[1], UP, buff=0.15, aligned_edge=LEFT)
        fit_frame(VGroup(pyr, dims, pmt, anodes, outs, outl))
        ax = Axes(x_range=[0, 80, 20], y_range=[0, 7, 1], x_length=5.0, y_length=2.6, tips=False,
                  axis_config={"color": GREY_B, "font_size": 20},
                  x_axis_config={"numbers_to_include": [0, 20, 40, 60, 80]}, y_axis_config={"numbers_to_include": [0, 3, 6]})
        ax.move_to(RIGHT * 3.4 + DOWN * 1.9)
        axl = VGroup(Tex(r"radial position (mm)", font_size=20, color=GREY_B).next_to(ax, DOWN, buff=0.15),
                     Tex(r"FWHM (mm)", font_size=20, color=GREY_B).next_to(ax, UP, buff=0.1).align_to(ax, LEFT))
        pts = [(0, 1.8), (60, 3.0), (75, 6.0)]
        rad = VGroup(*[Dot(ax.c2p(*p), color=BAD_C) for p in pts],
                     *[DashedLine(ax.c2p(*a), ax.c2p(*b), color=BAD_C) for a, b in zip(pts[:-1], pts[1:])])
        rl = Tex(r"radial", font_size=22, color=BAD_C).next_to(ax.c2p(75, 6.0), LEFT, buff=0.15)
        band = Rectangle(width=ax.c2p(75, 0)[0] - ax.c2p(0, 0)[0], height=ax.c2p(0, 3)[1] - ax.c2p(0, 0)[1], fill_color=NEW_C,
                         fill_opacity=0.15, stroke_width=0).move_to(ax.c2p(0, 0), aligned_edge=DL)
        bandl = Tex(r"tangential, axial", font_size=22, color=WHITE).move_to(ax.c2p(32, 0.8))
        nodoi = VGroup(icon_doi(), Tex(r"measured, \textbf{not used}", font_size=26, color=BAD_C)).arrange(RIGHT, buff=0.2)
        nodoi.next_to(ax, UP, buff=0.45)
        with self.voiceover(text="The lab's first big monolithic system was MAMMI, a breast scanner built with Oncovision. "
                                 "<bookmark mark='r'/>Twelve LYSO blocks form a ring <bookmark mark='a'/>with a hundred and eighty six "
                                 "millimetre opening. <bookmark mark='p'/>Each block is ten millimetres thick and cut as a truncated "
                                 "pyramid, forty millimetres at the front and fifty at the back, so the blocks tile the ring with "
                                 "less dead space. <bookmark mark='s'/>Each sits on a position sensitive photomultiplier whose sixty "
                                 "four anodes are reduced to five signals: <bookmark mark='m'/>energy, the centroid in two directions, "
                                 "and the spread of the light, which gives depth."):
            self.play(Write(title), run_time=0.8)
            self.at("r", LaggedStart(*[FadeIn(b) for b in blocks], lag_ratio=0.08), run_time=1.2)
            self.at("a", GrowFromCenter(bore[0]), FadeIn(bore[1]))
            self.at("p", TransformFromCopy(blocks[3], pyr), run_time=1.0)
            self.play(LaggedStart(*[FadeIn(d) for d in dims], lag_ratio=0.3))
            self.at("s", FadeIn(pmts), FadeIn(pmt), FadeIn(anodes))
            self.at("m", LaggedStart(*[GrowArrow(a) for a in outs], lag_ratio=0.15), FadeIn(outl))
        self.play(FadeOut(VGroup(pyr, dims, pmt, anodes, outs, outl)))
        # a point source moved from the centre to the edge, its radial blur drawn as a bell curve (DESIGN.md §1c)
        r = ValueTracker(0.0)
        fw = lambda rr: np.interp(rr, [0, 60, 75], [1.8, 3.0, 6.0])     # reported points only
        src = always_redraw(lambda: Dot(c + RIGHT * r.get_value() * s, color=YELLOW, radius=0.08))
        rpath = DashedLine(c, c + RIGHT * 75 * s, color=GREY_C, stroke_width=1.5)
        bell, ride = fwhm_inset(r, fw, BAD_C), always_redraw(lambda: Dot(ax.c2p(r.get_value(), fw(r.get_value())), color=YELLOW, radius=0.07))
        bell.move_to(RIGHT * 3.4 + UP * 1.55)
        with self.voiceover(text="At the centre it resolved one point eight millimetres radially. <bookmark mark='o'/>Moving outward, "
                                 "the radial number passes three millimetres beyond sixty, and reaches six at the edge of the field, "
                                 "<bookmark mark='t'/>while tangential and axial stay under three. <bookmark mark='d'/>That is "
                                 "parallax, and the depth that could fix it was measured but not used in these images, because of "
                                 "computing limits at the time."):
            self.play(Create(ax), FadeIn(axl), FadeIn(rad[0]), FadeIn(src, scale=2), FadeIn(bell), FadeIn(rpath))
            self.add(ride)
            self.at("o", FadeIn(rad[1:3]), Create(rad[3:]), FadeIn(rl), r.animate.set_value(60), run_time=2.5)
            self.play(r.animate.set_value(75), run_time=1.5)
            self.at("t", FadeIn(band), FadeIn(bandl))
            self.at("d", FadeIn(nodoi))
        self.wait(0.5)
        fade_all(self)


class Preclinical(Narrated):
    def construct(self):
        title = Tex(r"the preclinical line", font_size=34).to_edge(UP, buff=0.35)
        heads = VGroup(Tex(r"\textbf{Albira} (NEMA 2016)", font_size=28, color=OLD_C),
                       Tex(r"\textbf{Bruker 7 T insert} (2020)", font_size=28, color=NEW_C)).arrange(RIGHT, buff=2.0).shift(UP * 2.1)
        desc = VGroup(Tex(r"pyramids on PMTs, 2 rings of 8", font_size=22, color=GREY_B).next_to(heads[0], DOWN, buff=0.15),
                      Tex(r"50$\times$50$\times$10 mm on 12$\times$12 SiPMs", font_size=22, color=GREY_B).next_to(heads[1], DOWN, buff=0.15))
        res = hbars([("Albira", 1.72, OLD_C), ("insert", 0.68, NEW_C)], 2.0, width=3.4, fs=24)
        sen = hbars([("Albira", 5.3, OLD_C), ("insert", 11.0, NEW_C)], 12.0, width=3.4, fs=24)
        res.move_to(LEFT * 3.0 + DOWN * 0.6)
        sen.move_to(RIGHT * 3.6 + DOWN * 0.6)
        rl = Tex(r"radial FWHM at centre (mm)", font_size=22, color=GREY_B).next_to(res, UP, buff=0.3)
        sl = Tex(r"peak sensitivity (\%)", font_size=22, color=GREY_B).next_to(sen, UP, buff=0.3)
        flat = Tex(r"$\approx$\textbf{0.92 mm} out to \textbf{35 mm}: depth used", font_size=28, color=NEW_C).to_edge(DOWN, buff=0.6)
        with self.voiceover(text="The same blocks went into small animal scanners. <bookmark mark='a'/>Albira, the first commercial PET "
                                 "built on monolithic crystals, used two rings of eight pyramid blocks on photomultipliers. "
                                 "<bookmark mark='r'/>An independent test measured one point seven two millimetres at the centre "
                                 "<bookmark mark='s'/>and five point three percent sensitivity. <bookmark mark='b'/>Its successor, "
                                 "Bruker's insert for a seven tesla MRI, moved to silicon photomultipliers <bookmark mark='c'/>and "
                                 "reached zero point six eight millimetres and eleven percent. <bookmark mark='f'/>Because depth was "
                                 "now used, the resolution stays near zero point nine millimetres all the way to thirty five "
                                 "millimetres off centre."):
            self.play(Write(title), run_time=0.8)
            self.at("a", FadeIn(heads[0]), FadeIn(desc[0]))
            self.at("r", FadeIn(rl), grow(res[:1]))
            self.at("s", FadeIn(sl), grow(sen[:1]))
            self.at("b", FadeIn(heads[1]), FadeIn(desc[1]))
            self.at("c", grow(res[1:]), grow(sen[1:]))
            self.at("f", FadeIn(flat))
        self.wait(0.5)
        fade_all(self)


class TubeIdea(Narrated):
    def construct(self):
        title = Tex(r"2018: why not \textbf{one} crystal?", font_size=34).to_edge(UP, buff=0.35)
        c, s = LEFT * 3.5 + DOWN * 0.3, 0.05
        mods = VGroup(*[ring_block(k * TAU / 10 + PI / 10, 31, 41, 18, 22, s, c, fill_color=LYSO_C, fill_opacity=0.35,
                                   stroke_color=LYSO_C, stroke_width=2) for k in range(10)])
        outer = RegularPolygon(10, color=LYSO_C, stroke_width=2).scale(41 * s / np.cos(PI / 10)).move_to(c)
        tube = Difference(outer, Circle(radius=31 * s).move_to(c), fill_color=LYSO_C, fill_opacity=0.35, stroke_color=LYSO_C, stroke_width=2)
        gaps = VGroup(*[Line(c + 30 * s * np.array([np.cos(a), np.sin(a), 0]), c + 43 * s * np.array([np.cos(a), np.sin(a), 0]),
                             color=BAD_C, stroke_width=3) for a in np.arange(10) * TAU / 10])
        ml = Tex(r"10 blocks: gaps + 20 edges", font_size=24, color=BAD_C).next_to(mods, DOWN, buff=0.3)
        tl = Tex(r"1 tube: no gaps, no side edges", font_size=24, color=NEW_C).next_to(mods, DOWN, buff=0.3)
        blk = Rectangle(width=4.4, height=1.0, fill_color=LYSO_C, fill_opacity=0.15, stroke_color=LYSO_C).move_to(RIGHT * 3.4 + UP * 1.3)
        inner = DashedVMobject(Rectangle(width=4.4 * 0.6, height=1.0, color=YELLOW).move_to(blk))
        il = Tex(r"inner \textbf{60\%}", font_size=24, color=YELLOW).next_to(blk, UP, buff=0.15)
        test = Tex(r"1 mm rods: \textbf{1.45} $\to$ \textbf{1.19 mm}", font_size=28).next_to(blk, DOWN, buff=0.35)
        tl2 = Tex(r"measured on Bruker's insert", font_size=22, color=GREY_B).next_to(test, DOWN, buff=0.12)
        sens = hbars([("10 blocks", 3.7, OLD_C), ("one tube", 5.3, NEW_C)], 6.0, width=2.6, fs=24, fmt="{:g}\\%")
        sens.move_to(RIGHT * 3.9 + DOWN * 1.7)
        sl = Tex(r"GATE sensitivity, point source", font_size=22, color=GREY_B).next_to(sens, UP, buff=0.2)
        with self.voiceover(text="In twenty eighteen the lab, with Stan Majewski and colleagues, asked a radical question. "
                                 "<bookmark mark='m'/>A ring of separate blocks has gaps, and every block has two side edges where "
                                 "positions bunch up. <bookmark mark='t'/>What if the whole ring were one crystal, a tube with flat "
                                 "outer facets for the sensors? <bookmark mark='e'/>Their evidence was indirect. On Bruker's insert, "
                                 "keeping only events in the inner sixty percent of each block, away from the edges, "
                                 "<bookmark mark='r'/>sharpened the fitted rod width from one point four five to one point one nine "
                                 "millimetres. <bookmark mark='s'/>And a simulation gave the tube about thirty percent more "
                                 "sensitivity: five point three against three point seven percent."):
            self.play(Write(title), run_time=0.8)
            self.at("m", FadeIn(mods), Create(gaps), FadeIn(ml))
            self.at("t", FadeOut(gaps), ReplacementTransform(mods, tube), ReplacementTransform(ml, tl), run_time=1.5)
            self.at("e", FadeIn(blk), Create(inner), FadeIn(il))
            self.at("r", FadeIn(test), FadeIn(tl2))
            self.at("s", FadeIn(sl), grow(sens))
        self.wait(0.5)
        fade_all(self)


class Tube(Narrated):
    def construct(self):
        photo = card("tube_fig3b.png", 4.0).to_edge(LEFT, buff=0.5).shift(UP * 0.6)
        cred = credit(C_TUBE)
        c, s = RIGHT * 3.4 + UP * 0.9, 0.034          # cross-section, units per mm
        r_in, apo = 31.0, 40.0                         # 62 mm bore; 26 mm facets => apothem 13/tan(18 deg)
        outer = RegularPolygon(10, color=LYSO_C).scale(apo * s / np.cos(PI / 10)).move_to(c).rotate(PI / 10)
        tube = Difference(outer, Circle(radius=r_in * s).move_to(c), fill_color=LYSO_C, fill_opacity=0.3, stroke_color=LYSO_C, stroke_width=2)
        bore = dim_arrow(c + LEFT * r_in * s, c + RIGHT * r_in * s, r"\textbf{62}", fs=24)
        sipms = VGroup()
        for k in range(10):
            a = k * TAU / 10
            n, t = np.array([np.cos(a), np.sin(a), 0]), np.array([-np.sin(a), np.cos(a), 0])
            for j in range(8):
                sipms.add(Line(c + (apo + 0.8) * s * n + (-11.4 + j * 3.25) * s * t, c + (apo + 0.8) * s * n + (-9.6 + j * 3.25) * s * t,
                               color=SIPM_C, stroke_width=5))
        a0 = 0.0
        n0, t0 = np.array([1, 0, 0]), np.array([0, 1, 0])
        facet = dim_arrow(c + (apo + 4) * s * n0 - 13 * s * t0, c + (apo + 4) * s * n0 + 13 * s * t0, r"\textbf{26}", side=RIGHT, fs=22)
        count = Tex(r"$\times$\textbf{10}", font_size=26, color=LYSO_C).next_to(outer, DOWN, buff=0.15)
        tiles = VGroup(tile(icon_fwhm(), r"\textbf{1.4} / \textbf{1.3} mm"), tile(icon_sens(), r"\textbf{3.8\%}")).arrange(RIGHT, buff=0.3)
        tiles.to_edge(DOWN, buff=0.75)
        caveat = Tex(r"sinogram profiles", font_size=20, color=GREY_B).next_to(tiles, DOWN, buff=0.1)
        # row / column readout, drawn large
        n = 8
        yy, xx = np.mgrid[0:n, 0:n]
        val = np.exp(-((xx - 2.6) ** 2 + (yy - 4.2) ** 2) / 3.0)
        cells = VGroup(*[Square(0.34, stroke_color=GREY_D, stroke_width=1, fill_color=LIGHT_C, fill_opacity=0.08 + 0.9 * val[r, q])
                         .move_to(np.array([q * 0.34, -r * 0.34, 0])) for r in range(n) for q in range(n)])
        cells.move_to(RIGHT * 2.6 + DOWN * 0.6)
        rows = VGroup(*[Rectangle(width=0.05 + 1.0 * val[r].sum() / val.sum(axis=1).max(), height=0.26, fill_color=ORANGE_L,
                                  fill_opacity=0.9, stroke_width=0).move_to(np.array([cells.get_right()[0] + 0.15, cells[r * n].get_center()[1], 0]),
                                                                           aligned_edge=LEFT) for r in range(n)])
        cols = VGroup(*[Rectangle(width=0.26, height=0.05 + 1.0 * val[:, q].sum() / val.sum(axis=0).max(), fill_color=TEAL_L,
                                  fill_opacity=0.9, stroke_width=0).move_to(np.array([cells[q].get_center()[0], cells[0].get_top()[1] + 0.12, 0]),
                                                                           aligned_edge=DOWN) for q in range(n)])
        rc = Tex(r"\textbf{64} $\to$ \textbf{16}", font_size=30).next_to(cells, DOWN, buff=0.25)
        with self.voiceover(text="By twenty twenty two the tube existed. <bookmark mark='p'/>This is the crystal: one piece of LYSO "
                                 "<bookmark mark='b'/>with a sixty two millimetre bore, <bookmark mark='f'/>ten flat outer facets, "
                                 "<bookmark mark='s'/>each carrying an eight by eight silicon photomultiplier array. It reached "
                                 "<bookmark mark='r'/>about one point four millimetres radially and one point three axially, with "
                                 "three point eight percent peak sensitivity, <bookmark mark='c'/>measured from sinogram profiles "
                                 "rather than reconstructed images."):
            self.wait_until_bookmark("p")
            self.play(FadeIn(photo), FadeIn(cred), FadeIn(tube), run_time=1.0)
            self.at("b", GrowFromCenter(bore[0]), FadeIn(bore[1]))
            self.at("f", FadeIn(facet), FadeIn(count))
            self.at("s", LaggedStart(*[Create(l) for l in sipms], lag_ratio=0.01), run_time=1.2)
            self.at("r", FadeIn(tiles[0], shift=0.1 * UP))
            self.play(FadeIn(tiles[1], shift=0.1 * UP))
            self.at("c", FadeIn(caveat))
        self.play(FadeOut(Group(tube, bore, facet, count, sipms, tiles, caveat)))
        with self.voiceover(text="The readout keeps channel counts low. <bookmark mark='g'/>Instead of sixty four signals per facet, "
                                 "<bookmark mark='r'/>the rows are summed <bookmark mark='c'/>and the columns are summed, sixteen "
                                 "signals that still describe the light's shape, including the spread that encodes depth. "
                                 "<bookmark mark='v'/>Positions come from the centre of gravity, corrected with a calibration map "
                                 "that also absorbs the depth dependence."):
            self.at("g", FadeIn(cells))
            self.at("r", LaggedStart(*[GrowFromEdge(b, LEFT) for b in rows], lag_ratio=0.1))
            self.at("c", LaggedStart(*[GrowFromEdge(b, DOWN) for b in cols], lag_ratio=0.1), FadeIn(rc))
            self.at("v", Indicate(cells, color=YELLOW, scale_factor=1.03))
        self.wait(0.5)
        fade_all(self)


class SemiMono(Narrated):
    def construct(self):
        title = Tex(r"a second line: \textbf{semi-monolithic}", font_size=34).to_edge(UP, buff=0.35)
        slabs = VGroup(*[Rectangle(width=0.16, height=2.4, fill_color=LYSO_C, fill_opacity=0.35, stroke_color=WHITE, stroke_width=1)
                         for _ in range(22)]).arrange(RIGHT, buff=0.02).move_to(LEFT * 3.6 + UP * 0.5)
        hit = Dot(slabs[8].get_center() + UP * 0.5, color=YELLOW)
        hl = SurroundingRectangle(slabs[8], buff=0.03, color=YELLOW)
        count = Brace(slabs, UP, color=GREY_B)
        count_l = Tex(r"\textbf{22} $\times$ \textbf{0.97 mm}", font_size=24).next_to(count, UP, buff=0.08)
        across = VGroup(Arrow(slabs.get_corner(DL) + DOWN * 0.3, slabs.get_corner(DR) + DOWN * 0.3, buff=0, color=GREY_A, stroke_width=3),
                        MathTex(r"\bar{x}", font_size=34, color=GREY_A))
        across[1].next_to(across[0], DOWN, buff=0.1)
        along = DoubleArrow(slabs.get_corner(DL) + LEFT * 0.3, slabs.get_corner(UL) + LEFT * 0.3, buff=0, color=NEW_C, stroke_width=4, tip_length=0.15)
        net = icon_net().next_to(along, LEFT, buff=0.15)
        depth = VGroup(icon_doi(), MathTex(r"E/I_{\max}", font_size=28, color=LIGHT_C), Tex(r"\textbf{3.08 mm}", font_size=24, color=LIGHT_C))
        depth.arrange(RIGHT, buff=0.15).next_to(across, DOWN, buff=0.3)
        photo = card("semimono_fig1.png", 2.9).to_edge(RIGHT, buff=0.4).shift(UP * 1.1)
        cred = credit(C_SM)
        # 28 modules -> one network
        mods = VGroup(*[Square(0.16, fill_color=LYSO_C, fill_opacity=0.5, stroke_width=0.5) for _ in range(28)]).arrange_in_grid(2, 14, buff=0.05)
        mods.next_to(photo, DOWN, buff=0.45).shift(LEFT * 0.9)
        one = icon_net(0.8, 0.55).next_to(mods, RIGHT, buff=0.7)
        conv = VGroup(*[Line(m.get_right(), one.get_left(), color=NEW_C, stroke_width=0.8, stroke_opacity=0.5) for m in mods[::3]])
        ml = VGroup(Tex(r"\textbf{28}", font_size=24).next_to(mods, DOWN, buff=0.1), Tex(r"\textbf{1}", font_size=24, color=NEW_C).next_to(one, DOWN, buff=0.1))
        chan = Tex(r"\textbf{1792} ch, TOFPET2", font_size=22, color=GREY_B).next_to(ml, DOWN, buff=0.15).align_to(mods, LEFT)
        tiles = VGroup(tile(icon_fwhm(), r"\textbf{1.61 mm}", 2.6), tile(icon_sens(), r"\textbf{3.5\%}", 2.0),
                       tile(icon_clock(), r"\textbf{252 ps}", 2.4)).arrange(RIGHT, buff=0.25).to_edge(DOWN, buff=0.35)
        with self.voiceover(text="In parallel the lab developed a hybrid. <bookmark mark='s'/>The block is cut into twenty two thin "
                                 "slabs, under a millimetre each. <bookmark mark='w'/>Which slab was hit comes from a simple centroid, "
                                 "<bookmark mark='n'/>the position along the slab from a small neural network, <bookmark mark='d'/>and "
                                 "depth from the ratio of total energy to the brightest signal. <bookmark mark='p'/>In twenty "
                                 "twenty six this became a preclinical scanner: two rings of fourteen blocks around a hundred and six "
                                 "millimetre bore, <bookmark mark='c'/>every one of its seventeen hundred and ninety two channels read "
                                 "out. <bookmark mark='o'/>One network, trained once on one module, serves all twenty eight. "
                                 "<bookmark mark='r'/>It reached one point six one millimetres at the centre and three point five "
                                 "percent sensitivity."):
            self.play(Write(title), run_time=0.8)
            self.at("s", LaggedStart(*[FadeIn(sb) for sb in slabs], lag_ratio=0.03), GrowFromCenter(count), FadeIn(count_l), run_time=1.0)
            self.at("w", FadeIn(hit, scale=2), Create(hl), GrowArrow(across[0]), FadeIn(across[1]))
            self.at("n", GrowFromCenter(along), FadeIn(net))
            self.at("d", FadeIn(depth))
            self.at("p", FadeIn(photo), FadeIn(cred))
            self.at("c", FadeIn(mods), FadeIn(ml[0]), FadeIn(chan))
            self.at("o", Create(conv), FadeIn(one), FadeIn(ml[1]))
            self.at("r", LaggedStart(*[FadeIn(t, shift=0.1 * UP) for t in tiles], lag_ratio=0.3), run_time=1.2)
        self.wait(0.5)
        fade_all(self)


class DeepBreast(Narrated):
    def construct(self):
        title = Tex(r"2026: \textbf{DeepBreast}", font_size=34).to_edge(UP, buff=0.35)
        photo = card("deepbreast_fig1.png", 4.2).to_edge(LEFT, buff=0.4).shift(DOWN * 0.1)
        cred = credit(r"Fig.~1: " + C_DB)
        c = RIGHT * 3.7 + DOWN * 0.2
        s = 0.0165                                      # units per mm: 200 mm bore -> 3.3 units
        r_in, r_out = 100 * s, 112.5 * s
        big_tube = icon_tube(r_out, 10, OLD_C).move_to(c)
        no = VGroup(Line(c + UL * 1.4, c + DR * 1.4, color=BAD_C, stroke_width=8), Line(c + UR * 1.4, c + DL * 1.4, color=BAD_C, stroke_width=8))
        no_l = Tex(r"one LYSO tube, 200 mm: \textbf{cannot grow}", font_size=24, color=BAD_C).next_to(big_tube, DOWN, buff=0.35)
        segs = VGroup(*[AnnularSector(inner_radius=r_in, outer_radius=r_out, angle=TAU / 14, start_angle=k * TAU / 14 + 0.1, arc_center=c,
                                      fill_color=LYSO_C, fill_opacity=0.35, stroke_color=LYSO_C, stroke_width=1.5) for k in range(14)])
        joints = VGroup(*[Line(c + r_in * np.array([np.cos(a), np.sin(a), 0]), c + r_out * np.array([np.cos(a), np.sin(a), 0]),
                               color=YELLOW, stroke_width=4) for a in np.arange(14) * TAU / 14 + 0.1])
        n14 = Tex(r"\textbf{14}", font_size=30, color=LYSO_C).move_to(c)
        bore = dim_arrow(c + LEFT * r_in + DOWN * 0.45, c + RIGHT * r_in + DOWN * 0.45, r"\textbf{200 mm}", side=DOWN, fs=22)
        a = PI / 2 + 0.1 + TAU / 28
        u = np.array([np.cos(a), np.sin(a), 0])
        thick = VGroup(Line(c + r_in * u, c + r_out * u, color=WHITE, stroke_width=3),
                       Tex(r"\textbf{12.5}", font_size=24).move_to(c + (r_out + 0.35) * u))
        nl = VGroup(MathTex(r"n_\text{glue}\,\mathbf{1.7}", font_size=28, color=YELLOW), MathTex(r"n_\text{LYSO}\,\mathbf{1.8}", font_size=28, color=LYSO_C))
        nl.arrange(DOWN, aligned_edge=LEFT, buff=0.15).next_to(c + r_out * RIGHT, RIGHT, buff=0.35)
        sipm = VGroup(*[Line(c + (r_out + 0.06) * np.array([np.cos(b), np.sin(b), 0]), c + (r_out + 0.18) * np.array([np.cos(b), np.sin(b), 0]),
                             color=SIPM_C, stroke_width=3) for b in np.linspace(0, TAU, 14 * 12, endpoint=False)])
        geo_top = VGroup(segs, joints, n14, bore, thick, nl, sipm)
        fit_frame(VGroup(geo_top, big_tube, no_l))
        with self.voiceover(text="The newest system scales the idea to a breast. <bookmark mark='p'/>DeepBreast is a ring two hundred "
                                 "millimetres across. <bookmark mark='w'/>The single tube could not simply be scaled up: the authors "
                                 "say LYSO cannot be grown to that size. <bookmark mark='f'/>So the ring is fourteen curved crystals, "
                                 "<bookmark mark='t'/>twelve and a half millimetres thick, <bookmark mark='g'/>glued edge to edge "
                                 "with Meltmount, whose refractive index of one point seven is close to LYSO's one point eight. "
                                 "<bookmark mark='s'/>Bent circuit boards carry twelve by twelve silicon photomultipliers around the "
                                 "outside."):
            self.play(Write(title), run_time=0.8)
            self.at("p", FadeIn(photo), FadeIn(cred), run_time=1.0)
            self.at("w", FadeIn(big_tube), Create(no), FadeIn(no_l))
            self.at("f", FadeOut(no), FadeOut(no_l), ReplacementTransform(big_tube, segs), FadeIn(n14), GrowFromCenter(bore[0]), FadeIn(bore[1]),
                    run_time=1.2)
            self.at("t", Create(thick[0]), FadeIn(thick[1]))
            self.at("g", LaggedStart(*[Create(j) for j in joints], lag_ratio=0.05), FadeIn(nl), run_time=1.0)
            self.at("s", LaggedStart(*[Create(l) for l in sipm], lag_ratio=0.003), run_time=1.2)
        self.play(FadeOut(photo), FadeOut(cred), FadeOut(geo_top))
        # light crossing a glued joint vs an air gap
        c, rad = DOWN * 6.0, 7.6

        def seg(a0, a1):
            return AnnularSector(inner_radius=rad, outer_radius=rad + 1.2, angle=a1 - a0, start_angle=a0, arc_center=c,
                                 fill_color=LYSO_C, fill_opacity=0.25, stroke_color=LYSO_C, stroke_width=2)
        segs2 = VGroup(seg(PI / 2 - 0.36, PI / 2 - 0.12), seg(PI / 2 - 0.12, PI / 2 + 0.12), seg(PI / 2 + 0.12, PI / 2 + 0.36))
        pt = c + (rad + 0.6) * np.array([np.cos(PI / 2 - 0.105), np.sin(PI / 2 - 0.105), 0])
        rng = np.random.default_rng(3)
        aj = PI / 2 - 0.12

        def ray_set(gap):
            """Straight light rays from pt, stopped at the crystal's inner/outer faces and, with an air gap, at the joint."""
            g = VGroup()
            for ang0 in rng.uniform(0, TAU, 40):
                uu, end = np.array([np.cos(ang0), np.sin(ang0), 0]), pt
                for step in np.arange(0.02, 2.4, 0.02):
                    q = pt + step * uu
                    r, ang = np.linalg.norm(q - c), np.arctan2(*(q - c)[[1, 0]])
                    if not rad <= r <= rad + 1.2 or abs(ang - PI / 2) > 0.36 or (gap and ang < aj):
                        break
                    end = q
                g.add(Line(pt, end, color=LIGHT_C, stroke_width=1.5, stroke_opacity=0.75))
            return g

        state = rng.bit_generator.state
        rays_gap = ray_set(True)
        rng.bit_generator.state = state
        rays = ray_set(False)
        jfrom, jto = c + rad * np.array([np.cos(aj), np.sin(aj), 0]), c + (rad + 1.2) * np.array([np.cos(aj), np.sin(aj), 0])
        gap_line, joint = Line(jfrom, jto, color=BAD_C, stroke_width=4), Line(jfrom, jto, color=YELLOW, stroke_width=4)
        geo = VGroup(segs2, joint, gap_line, rays, rays_gap)
        shift = DOWN * 0.2 - segs2.get_center()
        geo.shift(shift)
        src = Dot(pt + shift, color=YELLOW, radius=0.07)
        gl = Tex(r"air gap", font_size=28, color=BAD_C).next_to(segs2, DOWN, buff=0.35)
        jl = Tex(r"glue", font_size=28, color=YELLOW).next_to(segs2, DOWN, buff=0.35)
        with self.voiceover(text="The glue is the point. <bookmark mark='r'/>Take an interaction near a joint. <bookmark mark='l'/>With "
                                 "an air gap, the light would stop at the boundary and the position would bunch up there. "
                                 "<bookmark mark='j'/>With index-matched glue, the light carries on into the neighbouring crystal, "
                                 "so optically the ring behaves as one piece, and the side edges disappear."):
            self.at("r", FadeIn(segs2), FadeIn(src, scale=2))
            self.at("l", Create(gap_line), Create(rays_gap), FadeIn(gl), run_time=1.2)
            self.at("j", ReplacementTransform(gap_line, joint), ReplacementTransform(rays_gap, rays), ReplacementTransform(gl, jl),
                    run_time=1.2)
        self.wait(0.5)
        fade_all(self)


class Positioning(Narrated):
    def construct(self):
        fig = card("deepbreast_fig2b.png", 4.3).to_edge(UP, buff=0.3)
        im = fig[1]
        cred = credit(r"Fig.~2b: " + C_DB)
        box = img_box(im, 0.25, 0.45, 0.33, 0.66, YELLOW)
        bl = Tex(r"M4 $|$ M5", font_size=26, color=YELLOW).next_to(fig, RIGHT, buff=0.15).shift(UP * 0.4)
        fit_frame(Group(fig, bl, box))
        # pipeline drawn as shapes: 14 module profiles -> network -> point on the ring
        rng = np.random.default_rng(1)
        prof = np.exp(-((np.arange(14) - 4.5) ** 2) / 0.8)
        mods = VGroup(*[Rectangle(width=0.16, height=0.05 + 1.1 * p, fill_color=TEAL_L, fill_opacity=0.9, stroke_width=0)
                        for p in prof]).arrange(RIGHT, buff=0.04, aligned_edge=DOWN)
        cols = VGroup(*[Rectangle(width=0.16, height=0.12, fill_color=ORANGE_L, fill_opacity=0.9, stroke_width=0) for _ in range(3)])
        cols.arrange(RIGHT, buff=0.04).next_to(mods[3:6], DOWN, buff=0.08)
        sig = VGroup(mods, cols)
        nets = VGroup(icon_net(0.8, 0.5), icon_net(0.8, 0.5)).arrange(DOWN, buff=0.15)
        ring = VGroup(Circle(radius=0.45, color=LYSO_C, stroke_width=4), Dot(0.45 * np.array([np.cos(1.0), np.sin(1.0), 0]), color=YELLOW))
        depth = VGroup(icon_doi(), MathTex(r"E/I_{\max}", font_size=26, color=LIGHT_C)).arrange(RIGHT, buff=0.1)
        row = VGroup(sig, nets, ring, depth).arrange(RIGHT, buff=0.9).to_edge(DOWN, buff=0.9)
        arr = VGroup(*[Arrow(row[k].get_right(), row[k + 1].get_left(), buff=0.12, color=GREY_B, stroke_width=3) for k in range(2)])
        lab = VGroup(Tex(r"\textbf{168} + 3$\times$12", font_size=22, color=GREY_B).next_to(sig, DOWN, buff=0.12),
                     Tex(r"\textbf{2} MLPs", font_size=22, color=NEW_C).next_to(nets, DOWN, buff=0.12),
                     MathTex(r"(x, z)", font_size=26).next_to(ring, DOWN, buff=0.12))
        fan = VGroup(Circle(radius=0.25, color=LYSO_C, stroke_width=3),
                     Polygon(ORIGIN, 0.25 * np.array([np.cos(1.2), np.sin(1.2), 0]), 0.25 * np.array([np.cos(1.6), np.sin(1.6), 0]),
                             fill_color=GREY_A, fill_opacity=0.8, stroke_width=0))
        cal = VGroup(fan, Tex(r"\textbf{11} $\to$ \textbf{3.6} days", font_size=26)).arrange(RIGHT, buff=0.2).to_corner(DL, buff=0.3)
        with self.voiceover(text="Here is a real coincidence, measured on the ring. <bookmark mark='a'/>Each module's sensors are "
                                 "summed into rows and columns, and the light of one gamma ray <bookmark mark='m'/>spreads across the "
                                 "boundary between modules four and five. <bookmark mark='n'/>So an event is positioned from the rows "
                                 "of all fourteen modules, a hundred and sixty eight signals, plus the columns of the three nearest, "
                                 "<bookmark mark='p'/>fed to two small neural networks, one per coordinate, <bookmark mark='d'/>with "
                                 "depth again from energy over the brightest signal. <bookmark mark='c'/>Training on the assembled "
                                 "ring with a rotating collimated fan beam cut calibration from eleven days to three point six."):
            self.wait_until_bookmark("a")
            self.play(FadeIn(fig), FadeIn(cred), run_time=1.0)
            self.at("m", Create(box), FadeIn(bl))
            self.at("n", LaggedStart(*[GrowFromEdge(m, DOWN) for m in mods], lag_ratio=0.05), FadeIn(cols), FadeIn(lab[0]))
            self.at("p", GrowArrow(arr[0]), FadeIn(nets), FadeIn(lab[1]), GrowArrow(arr[1]), FadeIn(ring), FadeIn(lab[2]))
            self.at("d", FadeIn(depth))
            self.at("c", FadeIn(fan[0]), FadeIn(cal[1]), Rotate(fan[1], angle=TAU, about_point=fan[0].get_center(), run_time=2.0))
        self.wait(0.5)
        fade_all(self)


class BreastResults(Narrated):
    def construct(self):
        title = Tex(r"MAMMI (2012) vs DeepBreast (2026)", font_size=34).to_edge(UP, buff=0.35)
        ax = Axes(x_range=[0, 80, 20], y_range=[0, 7, 1], x_length=5.6, y_length=3.4, tips=False,
                  axis_config={"color": GREY_B, "font_size": 20},
                  x_axis_config={"numbers_to_include": [0, 20, 40, 60, 80]}, y_axis_config={"numbers_to_include": [0, 3, 6]})
        ax.move_to(LEFT * 3.2 + DOWN * 0.3)
        axl = VGroup(Tex(r"radial position (mm)", font_size=20, color=GREY_B).next_to(ax, DOWN, buff=0.15),
                     Tex(r"radial FWHM (mm)", font_size=20, color=GREY_B).next_to(ax, UP, buff=0.1).align_to(ax, LEFT))
        pts = [(0, 1.8), (60, 3.0), (75, 6.0)]
        mam = VGroup(*[Dot(ax.c2p(*p), color=OLD_C) for p in pts], *[DashedLine(ax.c2p(*a), ax.c2p(*b), color=OLD_C) for a, b in zip(pts[:-1], pts[1:])])
        db = VGroup(Dot(ax.c2p(0, 1.7), color=NEW_C),
                    Rectangle(width=ax.c2p(80, 0)[0] - ax.c2p(0, 0)[0], height=ax.c2p(0, 0.2)[1] - ax.c2p(0, 0)[1], fill_color=NEW_C,
                              fill_opacity=0.5, stroke_width=0).move_to(ax.c2p(40, 1.9)))
        mi = icon_blocks(0.28).next_to(ax.c2p(75, 6.0), LEFT, buff=0.25)
        di = icon_glued(0.28).move_to(ax.c2p(40, 0.9))
        lab = VGroup(VGroup(mi, Tex(r"no DOI", font_size=20, color=OLD_C).next_to(mi, DOWN, buff=0.08)),
                     VGroup(di, Tex(r"\textbf{1.9 $\pm$ 0.1}", font_size=22, color=NEW_C).next_to(di, RIGHT, buff=0.15)))
        sens = VGroup()
        for k, (ic, v, col) in enumerate(((icon_blocks(0.22), 1.6, OLD_C), (icon_glued(0.22), 2.0, NEW_C), (icon_blocks(0.22, 16, GREY_D), 11.2, GREY_D))):
            b = Rectangle(width=3.0 * v / 12, height=0.4, fill_color=col, fill_opacity=0.9, stroke_width=0).move_to(np.array([0, -k * 0.62, 0]), aligned_edge=LEFT)
            sens.add(VGroup(b, ic.next_to(b.get_left(), LEFT, buff=0.2), Tex(r"\textbf{" + f"{v:g}" + r"\%}", font_size=24).next_to(b, RIGHT, buff=0.1)))
        sens.move_to(RIGHT * 4.2 + UP * 1.2)
        sl = VGroup(icon_sens(0.2), Tex(r"sensitivity", font_size=22, color=GREY_B)).arrange(RIGHT, buff=0.12).next_to(sens, UP, buff=0.25)
        pix = Tex(r"pixels", font_size=18, color=GREY_B).next_to(sens[2][1], DOWN, buff=0.05)
        tiles = VGroup(tile(icon_doi(), r"\textbf{3.6 mm}", 2.5), tile(icon_energy(), r"\textbf{19\%}", 2.5),
                       tile(icon_rate(), r"\textbf{15 kcps}", 2.5), tile(icon_clock(True), r"$\sim$\textbf{100 ps}?", 2.5)).arrange_in_grid(2, 2, buff=0.2)
        tiles.move_to(RIGHT * 3.7 + DOWN * 1.9)
        fit_frame(VGroup(sens, sl, pix, tiles))
        with self.voiceover(text="Against MAMMI, the gain is flatness. <bookmark mark='m'/>MAMMI's radial resolution climbed from one "
                                 "point eight to six millimetres toward the edge. <bookmark mark='d'/>DeepBreast starts at one point "
                                 "seven and averages one point nine out to eighty millimetres, within ten percent everywhere. "
                                 "<bookmark mark='c'/>That is not only the glue: MAMMI's figures ignored depth, and DeepBreast uses it. "
                                 "<bookmark mark='s'/>Sensitivity is two percent, above MAMMI's one point six, <bookmark mark='e'/>but "
                                 "far below a pixelated breast ring at eleven. <bookmark mark='o'/>Depth is resolved to three point six "
                                 "millimetres, energy to nineteen percent, the count rate peaks at fifteen kilocounts per second, "
                                 "<bookmark mark='t'/>and there is no time of flight yet; the authors estimate about a hundred "
                                 "picoseconds would be needed to matter."):
            self.play(Write(title), Create(ax), FadeIn(axl), run_time=1.0)
            self.at("m", FadeIn(mam[:3]), Create(mam[3:]), FadeIn(lab[0]))
            self.at("d", FadeIn(db), FadeIn(lab[1]))
            self.at("c", Indicate(lab[0], color=BAD_C))
            self.at("s", FadeIn(sl), grow(sens[:2]))
            self.at("e", grow(sens[2:]), FadeIn(pix))
            self.at("o", LaggedStart(*[FadeIn(t, shift=0.1 * UP) for t in tiles[:3]], lag_ratio=0.3), run_time=1.2)
            self.at("t", FadeIn(tiles[3], shift=0.1 * UP))
        self.wait(0.5)
        fade_all(self)


class Compton(Narrated):
    def construct(self):
        title = Tex(r"the other bet: layers ordered by \textbf{time}", font_size=34).to_edge(UP, buff=0.35)
        probs = hbars([("Compton", 48.8, ORANGE_L), ("photoelectric", 45.5, NEW_C), ("Rayleigh", 5.7, GREY_B)], 50, width=3.2, fs=24,
                      fmt="{:g}\\%").move_to(LEFT * 2.6 + UP * 1.6)
        pl = Tex(r"LYSO at 511 keV", font_size=22, color=GREY_B).next_to(probs, UP, buff=0.2)
        a, b = LEFT * 4.6 + DOWN * 1.2, LEFT * 2.2 + DOWN * 0.6
        hits = VGroup(Dot(a, color=YELLOW, radius=0.1), Dot(b, color=YELLOW, radius=0.07))
        g = Arrow(a + DOWN * 1.2 + LEFT * 0.3, a, buff=0.05, color=GAM_C)
        sc = Arrow(a, b, buff=0.1, color=GAM_C, stroke_width=3)
        cen = Cross(scale_factor=0.12, stroke_color=BAD_C, stroke_width=5).move_to(a * 0.45 + b * 0.55)
        cl = Tex(r"centroid: between them", font_size=24, color=BAD_C).next_to(cen, DOWN, buff=0.6).shift(RIGHT * 0.5)
        lay1 = Rectangle(width=0.3, height=3.0, fill_color=ORANGE_L, fill_opacity=0.5, stroke_width=1).move_to(RIGHT * 2.2 + DOWN * 0.6)
        lay2 = Rectangle(width=1.2, height=3.0, fill_color=LYSO_C, fill_opacity=0.35, stroke_width=1).move_to(RIGHT * 4.6 + DOWN * 0.6)
        ll = VGroup(Tex(r"thin scatterer", font_size=22, color=ORANGE_L).next_to(lay1, UP, buff=0.15),
                    Tex(r"absorber", font_size=22, color=LYSO_C).next_to(lay2, UP, buff=0.15))
        gap = VGroup(DoubleArrow(lay1.get_right(), lay2.get_left(), buff=0, color=GREY_B, tip_length=0.15))
        need = hbars([("needed at 192 ps", 58.2, BAD_C), ("built", 38.5, GREY_B)], 60, width=3.0, fs=22, fmt="{:g} mm")
        need.move_to(RIGHT * 3.6 + DOWN * 2.9)
        fit_frame(need)
        with self.voiceover(text="Monolithic crystals still reduce each gamma ray to one point. <bookmark mark='p'/>In LYSO, a five "
                                 "hundred and eleven keV photon is about as likely to Compton scatter as to be absorbed outright. "
                                 "<bookmark mark='h'/>When it scatters and is then absorbed, <bookmark mark='c'/>the light of both "
                                 "deposits merges, and the estimate lands between them. <bookmark mark='l'/>i3M's plan for this, "
                                 "from twenty eighteen, is two separate layers: a thin scatterer and a thick absorber, "
                                 "<bookmark mark='g'/>far enough apart for time of flight to say which was hit first. "
                                 "<bookmark mark='t'/>In twenty twenty four they built the scatter ring and measured one hundred and "
                                 "ninety two picoseconds. That needs the layers about fifty eight millimetres apart; <bookmark mark='b'/>"
                                 "they are thirty eight and a half. So the timing cannot order the hits, and the ring was repurposed."):
            self.play(Write(title), run_time=0.8)
            self.at("p", FadeIn(pl), grow(probs), run_time=1.2)
            self.at("h", GrowArrow(g), FadeIn(hits[0], scale=2), GrowArrow(sc), FadeIn(hits[1], scale=2))
            self.at("c", FadeIn(cen, scale=2), FadeIn(cl))
            self.at("l", FadeIn(lay1), FadeIn(lay2), FadeIn(ll))
            self.at("g", GrowFromCenter(gap))
            self.at("t", grow(need[:1]))
            self.at("b", grow(need[1:]))
        self.wait(0.5)
        fade_all(self)


class Takeaway(Narrated):
    def construct(self):
        steps = VGroup(*[VGroup(ic, Tex(yr, font_size=28, color=col)).arrange(DOWN, buff=0.2)
                         for ic, yr, col in ((icon_blocks(0.6), r"\textbf{2012}", OLD_C), (icon_tube(0.6), r"\textbf{2022}", NEW_C),
                                             (icon_glued(0.62), r"\textbf{2026}", NEW_C))]).arrange(RIGHT, buff=1.6).shift(UP * 1.7)
        arr = VGroup(*[Arrow(steps[k][0].get_right(), steps[k + 1][0].get_left(), buff=0.25, color=GREY_B) for k in range(2)])
        habits = VGroup(*[VGroup(ic.scale_to_fit_height(1.05), Tex(t, font_size=26, color=GREY_A)).arrange(DOWN, buff=0.18)
                          for ic, t in ((icon_painted(), "black paint"), (icon_grid(), "rows + cols"), (icon_net(1.0, 0.7), "one net"))])
        habits.arrange(RIGHT, buff=1.6).shift(DOWN * 0.5)
        # the open problem, drawn: two deposits in one crystal, reduced to one point between them
        blk = Rectangle(width=2.6, height=0.9, fill_color=LYSO_C, fill_opacity=0.2, stroke_color=LYSO_C).to_edge(DOWN, buff=0.55).shift(LEFT * 1.2)
        p1, p2 = blk.get_center() + LEFT * 0.8 + DOWN * 0.15, blk.get_center() + RIGHT * 0.7 + UP * 0.2
        gap = VGroup(blk, Dot(p1, color=YELLOW), Dot(p2, color=YELLOW), DashedLine(p1, p2, color=GAM_C, stroke_width=2),
                     Cross(scale_factor=0.12, stroke_color=BAD_C, stroke_width=5).move_to((p1 + p2) / 2))
        gl = Tex(r"open: \textbf{2+ hits} in one crystal", font_size=28, color=BAD_C).next_to(blk, RIGHT, buff=0.4)
        with self.voiceover(text="So the arc of this lab: <bookmark mark='a'/>separate blocks with edges and gaps, <bookmark mark='b'/>"
                                 "then a single crystal tube, <bookmark mark='c'/>then, when crystals could not grow large enough, a "
                                 "ring glued into optical continuity. <bookmark mark='h'/>The habits carry through: black paint to "
                                 "keep the light's shape, row and column sums to keep channels low, and lately one trained network "
                                 "for every module. <bookmark mark='g'/>What none of these systems does yet is separate several "
                                 "interactions inside one thick crystal; each event is still a single point."):
            self.wait_until_bookmark("a")
            self.play(FadeIn(steps[0], scale=0.8))
            self.at("b", GrowArrow(arr[0]), FadeIn(steps[1], scale=0.8))
            self.at("c", GrowArrow(arr[1]), FadeIn(steps[2], scale=0.8))
            self.at("h", LaggedStart(*[FadeIn(h, shift=0.1 * UP) for h in habits], lag_ratio=0.4), run_time=1.5)
            self.at("g", FadeIn(gap[:4]), FadeIn(gap[4], scale=2), FadeIn(gl))
        self.wait(1.0)
        fade_all(self)
