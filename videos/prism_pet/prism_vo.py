"""Explainer: the Prism-PET programme (Goldan group, Stony Brook University and Weill Cornell Medicine).

Source: the Prism-PET literature-review note on the programme, with its numbers checked against
LaBella et al. 2020 (J Nucl Med) and 2021 (Med Phys), Zeng et al. 2023 and 2024 (Med Phys), and Petersen et al.
2020 (IEEE NSS/MIC) and 2024 (Phys Med Biol). The papers are publisher copyright, so every drawing is new; the
light-sharing bars, the w-versus-depth curve and the parallax sketch are illustrative.
Visuals are cued to the narration with <bookmark/> tags and self.at() (see ../DESIGN.md).
Render with render.sh, or one scene: manim -ql prism_vo.py Prism
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import *  # noqa: E402,F401

XTAL_C, SIPM_C, PRISM_C, GLASS_C, LIGHT_C, GAM_C = "#7fb3ff", "#4c8fe0", "#b18cf0", "#9aa4b2", "#f5d76e", "#7ee081"
CITE = r"Goldan group \textperiodcentered\ Stony Brook University \& Weill Cornell Medicine"


def column_module(n=6, w=0.62, h=3.2, origin=ORIGIN, guide="prism"):
    """Side view of a module: n crystal columns, SiPMs under pairs of columns, and either a prism array
    (offset by one column from the SiPM pairs) or a uniform glass guide on top."""
    xs = [origin[0] + (k - (n - 1) / 2) * w for k in range(n)]
    base = origin[1] - h / 2
    cols = VGroup(*[Rectangle(width=w * 0.92, height=h, stroke_color=XTAL_C, stroke_width=1.5, fill_color=XTAL_C, fill_opacity=0.18)
                    .move_to([x, origin[1], 0]) for x in xs])
    sipms = VGroup(*[Rectangle(width=2 * w * 0.96, height=0.22, stroke_width=0, fill_color=SIPM_C, fill_opacity=0.95)
                     .move_to([(xs[k] + xs[k + 1]) / 2, base - 0.14, 0]) for k in range(0, n, 2)])
    top = origin[1] + h / 2
    if guide == "prism":
        g = VGroup()
        for k in range(1, n - 1, 2):
            a, b = xs[k] - w / 2 * 0.92, xs[k + 1] + w / 2 * 0.92
            g.add(Polygon([a, top + 0.02, 0], [b, top + 0.02, 0], [(a + b) / 2, top + 0.02 + (b - a) / 2, 0],
                          stroke_color=PRISM_C, stroke_width=2, fill_color=PRISM_C, fill_opacity=0.25))
        for k in (0, n - 1):       # edge columns get their own small prism (the edge design)
            a, b = xs[k] - w / 2 * 0.92, xs[k] + w / 2 * 0.92
            g.add(Polygon([a, top + 0.02, 0], [b, top + 0.02, 0], [(a + b) / 2, top + 0.02 + (b - a) / 2, 0],
                          stroke_color=PRISM_C, stroke_width=2, fill_color=PRISM_C, fill_opacity=0.25))
    else:
        g = Rectangle(width=n * w, height=0.4, stroke_color=GLASS_C, stroke_width=2, fill_color=GLASS_C, fill_opacity=0.2).move_to([origin[0], top + 0.22, 0])
    return VGroup(cols, sipms, g), xs, base, top


def ray(points, color=LIGHT_C, width=3):
    return VMobject(stroke_color=color, stroke_width=width).set_points_as_corners([np.array([x, y, 0]) for x, y in points])


class Opening(Narrated):
    def construct(self):
        mod, xs, base, top = column_module(origin=np.array([0, -0.4, 0]))
        title = Tex("Prism-PET").scale(1.2).to_edge(UP, buff=0.5)
        sub = Tex(r"depth-encoding PET detectors with a prismatoid light guide", color=GREY_B).scale(0.6).next_to(title, DOWN, buff=0.15)
        foot = Tex(CITE, color=TEAL_L).scale(0.5).to_edge(DOWN, buff=0.3)
        y0 = -0.4 + 0.9
        path = ray([(xs[1], y0), (xs[1], top + 0.05), (xs[1] + 0.3, top + 0.35), (xs[2] - 0.0, top + 0.05), (xs[2], base)])
        with self.voiceover(text="This is the Prism-PET programme from Amir Goldan's group, first at Stony Brook University and now at "
                                 "Weill Cornell Medicine. Its idea fits in one picture: <bookmark mark='mod'/>long crystals, read from "
                                 "one end, with a row of <bookmark mark='pr'/>tiny glass prisms on the other end that "
                                 "<bookmark mark='ray'/>send each crystal's light into its neighbour."):
            self.play(Write(title), FadeIn(sub), FadeIn(foot), run_time=1.2)
            self.at("mod", FadeIn(mod[0]), FadeIn(mod[1]))
            self.at("pr", FadeIn(mod[2], shift=0.1 * DOWN))
            self.at("ray", Create(path), run_time=1.2)
        with self.voiceover(text="That small trick gives a single ended detector a sense of depth. Here is why that matters, how it "
                                 "works, and how far the group has taken it."):
            self.play(Indicate(mod[2], color=PRISM_C), run_time=1.0)
        fade_all(self)


class Parallax(Narrated):
    def construct(self):
        title = Tex("Why depth matters").scale(0.72).to_edge(UP)
        c = 3.2 * LEFT + 0.5 * DOWN
        R, L, n = 1.9, 1.0, 26
        xt = VGroup()
        for k in range(n):
            a = k * TAU / n
            u = np.array([np.cos(a), np.sin(a), 0])
            xt.add(Rectangle(width=0.36, height=L, stroke_color=XTAL_C, stroke_width=1.2, fill_color=XTAL_C, fill_opacity=0.25)
                   .rotate(a - PI / 2).move_to(c + (R + L / 2) * u))
        src = c + np.array([0.9, 1.0, 0])
        d = np.array([1.0, 0.12, 0]) / np.linalg.norm([1.0, 0.12])

        def end(sign):
            """Where the gamma travelling along sign*d stops (0.8 units past the ring's inner face), and the
            front-face centre of the crystal it stopped in: the point a detector without DOI assumes."""
            s = next(s for s in np.linspace(0, 6, 3000) if np.linalg.norm(src + sign * s * d - c) >= R)
            p = src + sign * (s + 0.8 * L) * d
            k = round(np.arctan2(*(p - c)[1::-1]) / (TAU / n)) % n
            return p, c + R * np.array([np.cos(k * TAU / n), np.sin(k * TAU / n), 0]), k

        (p1, f1, k1), (p2, f2, k2) = end(1), end(-1)
        gam = VGroup(Arrow(src, p1, buff=0, color=GAM_C, stroke_width=4, max_tip_length_to_length_ratio=0.06),
                     Arrow(src, p2, buff=0, color=GAM_C, stroke_width=4, max_tip_length_to_length_ratio=0.06))
        hit = VGroup(Dot(p1, color=YELLOW, radius=0.07), Dot(p2, color=YELLOW, radius=0.07), Dot(src, color=RED, radius=0.07))
        faces = VGroup(Dot(f1, color=RED, radius=0.07), Dot(f2, color=RED, radius=0.07))
        assumed = DashedLine(f1, f2, color=RED, stroke_width=3)
        pts = VGroup(Tex(r"crystals are long (20 mm) to stop 511 keV gammas", font_size=28),
                     Tex(r"an oblique gamma can stop deep inside", font_size=28),
                     Tex(r"without depth, the event is placed at the face", font_size=28, color=RED),
                     Tex(r"$\Rightarrow$ the line of response shifts: parallax", font_size=28, color=RED)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.16).to_edge(RIGHT, buff=0.5).shift(0.8 * UP)
        fit_frame(pts)
        with self.voiceover(text="PET crystals are <bookmark mark='long'/>long, around twenty millimetres, so they can stop five hundred "
                                 "and eleven kilo electron volt gammas. A gamma arriving <bookmark mark='obl'/>at an angle may travel "
                                 "into the crystal and stop deep inside. If the detector can't tell how deep, it "
                                 "<bookmark mark='face'/>places the event at the crystal's face, and the line of response "
                                 "<bookmark mark='par'/>shifts. This is parallax error, and it gets worse towards the edge of the "
                                 "field of view, and in compact scanners like brain PET."):
            self.play(Write(title), run_time=0.8)
            self.at("long", LaggedStart(*[FadeIn(x) for x in xt], lag_ratio=0.02), FadeIn(pts[0]), run_time=1.0)
            self.at("obl", GrowArrow(gam[0]), GrowArrow(gam[1]), FadeIn(hit, scale=0.4), FadeIn(pts[1]),
                    Indicate(xt[k1], color=YELLOW), Indicate(xt[k2], color=YELLOW))
            self.at("face", FadeIn(faces, scale=0.4), FadeIn(pts[2]))
            self.at("par", Create(assumed), FadeIn(pts[3]), Flash(hit[2], color=RED))
        doi = Tex(r"depth of interaction (DOI) fixes it", font_size=30, color=YELLOW).next_to(pts, DOWN, buff=0.5, aligned_edge=LEFT)
        with self.voiceover(text="Measuring the <bookmark mark='doi'/>depth of interaction, or D O I, removes the error. The usual way "
                                 "is a second photodetector on the far end of every crystal, which roughly doubles the electronics. "
                                 "Prism-PET gets depth from one end."):
            self.at("doi", FadeIn(doi, shift=0.1 * UP))
        fade_all(self)


class LightGuide(Narrated):
    def construct(self):
        title = Tex("Light sharing through a uniform glass guide").scale(0.72).to_edge(UP)
        mod, xs, base, top = column_module(origin=np.array([-3.4, -0.4, 0]), guide="glass")
        lab = VGroup(Tex("LYSO crystals", font_size=26, color=XTAL_C).next_to(mod[0], LEFT, buff=0.25),
                     Tex("SiPMs", font_size=26, color=SIPM_C).next_to(mod[1], DOWN, buff=0.15),
                     Tex("glass light guide", font_size=26, color=GLASS_C).next_to(mod[2], UP, buff=0.12))
        fit_frame(VGroup(mod, lab))
        xs = [x + mod[0][0].get_center()[0] - xs[0] for x in xs]
        k0 = 2
        y0 = -0.4 + 0.6
        flash = Dot([xs[k0], y0, 0], color=LIGHT_C, radius=0.08)
        rays = VGroup(*[ray([(xs[k0], y0), (xs[k0], top + 0.2), (xs[k], top + 0.42), (xs[k], base)], width=1.5) for k in range(6)])
        rays.set_stroke(opacity=0.7)
        sig = [0.10, 0.22, 0.42, 0.18, 0.10, 0.05]
        bars = VGroup(*[Rectangle(width=0.5, height=2.4 * v, stroke_width=0, fill_color=LIGHT_C, fill_opacity=0.9)
                        .move_to([1.6 + 0.8 * k, -2.2, 0], aligned_edge=DOWN) for k, v in enumerate(sig)])
        bl = Tex(r"signal per SiPM: spread thin", font_size=26).next_to(bars, DOWN, buff=0.2)
        ill = Tex("illustrative", font_size=22, color=GREY_D).to_corner(DR, buff=0.15)
        with self.voiceover(text="Start with the common single ended design. Thin <bookmark mark='x'/>crystals sit on an array of "
                                 "<bookmark mark='s'/>silicon photomultipliers, several crystals per sensor, and a "
                                 "<bookmark mark='g'/>flat glass light guide sits on top. Light from a crystal "
                                 "<bookmark mark='sh'/>enters the glass and spreads to many neighbours."):
            self.play(Write(title), run_time=0.8)
            self.at("x", FadeIn(mod[0]), FadeIn(lab[0]))
            self.at("s", FadeIn(mod[1]), FadeIn(lab[1]))
            self.at("g", FadeIn(mod[2]), FadeIn(lab[2]))
            self.at("sh", FadeIn(flash, scale=0.4), LaggedStart(*[Create(r) for r in rays], lag_ratio=0.08), run_time=1.2)
        pts = VGroup(Tex(r"depth: how much light is shared", font_size=28),
                     Tex(r"but the sharing is isotropic and random", font_size=28),
                     Tex(r"weak signals drown in dark counts", font_size=28),
                     Tex(r"edge and corner crystals lack neighbours", font_size=28)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.14).to_edge(RIGHT, buff=0.6).shift(1.4 * UP)
        fit_frame(pts)
        with self.voiceover(text="The amount of light that gets shared depends on depth, so it can encode D O I. But the sharing is "
                                 "<bookmark mark='iso'/>isotropic: the light ends up as <bookmark mark='bars'/>weak signals spread over "
                                 "many sensors, where <bookmark mark='dark'/>dark counts swamp them. And crystals at the "
                                 "<bookmark mark='edge'/>edges and corners have fewer neighbours to share with, so they come out "
                                 "worse."):
            self.at("iso", FadeIn(pts[0]), FadeIn(pts[1]))
            self.at("bars", LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars], lag_ratio=0.08), FadeIn(bl), FadeIn(ill), run_time=1.0)
            self.at("dark", FadeIn(pts[2]))
            self.at("edge", FadeIn(pts[3]), Indicate(mod[0][0], color=RED), Indicate(mod[0][-1], color=RED))
        fade_all(self)


class Prism(Narrated):
    def construct(self):
        title = Tex("The prismatoid light guide").scale(0.72).to_edge(UP)
        mod, xs, base, top = column_module(origin=np.array([-3.6, 0.1, 0]))
        w = xs[1] - xs[0]
        pl = Tex(r"right-triangle prisms,\\offset by one crystal", font_size=26, color=PRISM_C).next_to(mod[2], UP, buff=0.2)
        sl = Tex(r"each SiPM reads 2$\times$2 crystals", font_size=26, color=SIPM_C).next_to(mod[1], DOWN, buff=0.15)
        with self.voiceover(text="Prism-PET replaces the flat glass with an <bookmark mark='pr'/>array of small right triangle prisms. "
                                 "In this side view each prism covers two crystals, but the prisms are <bookmark mark='off'/>offset by one crystal from the "
                                 "sensors underneath, so the two crystals under a prism always sit on different sensors."):
            self.play(Write(title), FadeIn(mod[0]), FadeIn(mod[1]), FadeIn(sl), run_time=1.0)
            self.at("pr", FadeIn(mod[2], shift=0.1 * DOWN), FadeIn(pl))
            self.at("off", Indicate(mod[2][0], color=YELLOW), Indicate(VGroup(mod[1][0], mod[1][1]), color=YELLOW))

        k = 1
        apex = (xs[1] + xs[2]) / 2
        hh = (xs[2] - xs[1] + w * 0.92) / 2

        def light(y0, frac):
            f = Dot([xs[k], y0, 0], color=LIGHT_C, radius=0.08)
            down = ray([(xs[k], y0), (xs[k], base)], width=2 + 6 * (1 - frac))
            up = ray([(xs[k], y0), (xs[k], top + 0.02), (apex - 0.05, top + 0.02 + hh * 0.9), (xs[k + 1], top + 0.02), (xs[k + 1], base)],
                     width=2 + 6 * frac)
            return VGroup(f, down, up)

        deep = light(0.1 + 1.1, 0.55)
        shallow = light(0.1 - 1.1, 0.2)
        ax = Axes(x_range=[0, 20, 5], y_range=[0.4, 1.0, 0.2], x_length=4.2, y_length=2.6, tips=False,
                  axis_config={"color": GREY_B, "font_size": 22}).to_edge(RIGHT, buff=0.8).shift(0.4 * UP)
        ax.add_coordinates()
        xl = Tex(r"depth from the SiPMs (mm)", font_size=24).next_to(ax, DOWN, buff=0.3)
        yl = MathTex(r"w = \frac{\text{brightest SiPM}}{\text{all SiPMs}}", font_size=30).next_to(ax, UP, buff=0.25)
        curve = ax.plot(lambda z: 0.92 - 0.38 * (z / 20) ** 1.4, x_range=[0, 20], color=PRISM_C)
        ill = Tex(r"curve illustrative", font_size=22, color=GREY_D).next_to(xl, DOWN, buff=0.1)
        with self.voiceover(text="Follow the light. A gamma stops in a crystal and <bookmark mark='f'/>light goes both ways. Light heading "
                                 "down reaches this crystal's own sensor. Light heading up <bookmark mark='up'/>enters the prism, turns "
                                 "a hundred and eighty degrees, and comes down the neighbouring crystal onto a different sensor."):
            self.at("f", FadeIn(deep[0], scale=0.4), Create(deep[1]))
            self.at("up", Create(deep[2]), run_time=1.4)
        with self.voiceover(text="How the light splits depends on depth. An interaction <bookmark mark='near'/>near the sensors sends most "
                                 "light straight down. One <bookmark mark='far'/>near the prism shares much more with the neighbour. So the "
                                 "ratio of the <bookmark mark='w'/>brightest sensor to the total, called w, tracks depth."):
            self.wait_until_bookmark("near")
            self.play(ReplacementTransform(deep, shallow), run_time=0.8)
            self.wait_until_bookmark("far")
            self.play(ReplacementTransform(shallow, light(0.1 + 1.1, 0.55)), run_time=0.8)
            self.at("w", Create(ax), FadeIn(xl), FadeIn(yl), Create(curve), FadeIn(ill), run_time=1.2)
        keys = VGroup(Tex(r"deterministic: light goes only to the nearest neighbours", font_size=26),
                      Tex(r"centre, edge and corner prism designs", font_size=26),
                      Tex(r"up to 9 crystals per SiPM, each with its own pattern", font_size=26)
                      ).arrange(DOWN, aligned_edge=LEFT, buff=0.12).to_edge(DOWN, buff=0.35)
        fit_frame(keys)
        with self.voiceover(text="The key difference from glass is that the sharing is <bookmark mark='det'/>deterministic: each crystal "
                                 "lights a fixed pattern of its own sensor and its nearest neighbours, so the signals stay strong. Separate "
                                 "<bookmark mark='ec'/>centre, edge and corner prism designs keep the pattern working at the borders, and "
                                 "the fixed patterns let up to <bookmark mark='nine'/>nine crystals share one sensor and still be told "
                                 "apart."):
            self.at("det", FadeIn(keys[0]))
            self.at("ec", FadeIn(keys[1]), Indicate(VGroup(mod[2][-2], mod[2][-1]), color=YELLOW))
            self.at("nine", FadeIn(keys[2]))
        fade_all(self)


class Module(Narrated):
    def construct(self):
        title = Tex(r"The module: LaBella et al.\ 2020 and 2021").scale(0.72).to_edge(UP)
        spec = Tex(r"16$\times$16 LYSO, 1.4$\times$1.4$\times$20 mm, 4-to-1 on 3 mm SiPMs", font_size=28).next_to(title, DOWN, buff=0.3)
        ax = Axes(x_range=[0, 2, 1], y_range=[0, 14, 2], x_length=4.0, y_length=3.2, tips=False,
                  axis_config={"color": GREY_B, "include_ticks": False}).shift(3.6 * LEFT + 0.9 * DOWN)
        lab = VGroup(Tex("DOI (mm)", font_size=24).next_to(ax.c2p(0.5, 0), DOWN, buff=0.15),
                     Tex(r"energy res.\ (\%)", font_size=24).next_to(ax.c2p(1.5, 0), DOWN, buff=0.15))
        vals = [(0.5, 5.0, 2.5), (1.5, 13, 9)]
        bars, nums = VGroup(), VGroup()
        for x, g, p in vals:
            for dx, v, col in ((-0.17, g, GLASS_C), (0.17, p, PRISM_C)):
                b = Rectangle(width=0.55, height=ax.c2p(0, v)[1] - ax.c2p(0, 0)[1], stroke_width=0, fill_color=col, fill_opacity=0.9)
                b.move_to(ax.c2p(x + dx, 0), aligned_edge=DOWN)
                bars.add(b)
                nums.add(Tex(f"{v:g}", font_size=24).next_to(b, UP, buff=0.08))
        key = VGroup(VGroup(Square(0.18, fill_color=GLASS_C, fill_opacity=1, stroke_width=0), Tex("uniform glass", font_size=24)).arrange(RIGHT, buff=0.1),
                     VGroup(Square(0.18, fill_color=PRISM_C, fill_opacity=1, stroke_width=0), Tex("Prism-PET", font_size=24)).arrange(RIGHT, buff=0.1)
                     ).arrange(RIGHT, buff=0.5).next_to(ax, UP, buff=0.35)
        uni = Tex(r"and uniform crystal separation,\\even at edges and corners", font_size=26).next_to(key, UP, buff=0.25)
        with self.voiceover(text="The first module paper, in twenty twenty, used <bookmark mark='spec'/>sixteen by sixteen arrays of one "
                                 "point four millimetre L Y S O crystals, twenty millimetres long, four crystals to each sensor. Against "
                                 "the same module with a flat glass guide, the prisms <bookmark mark='doi'/>made depth resolution twice as sharp, "
                                 "from five millimetres to two and a half, improved <bookmark mark='en'/>energy resolution from thirteen "
                                 "to nine percent, and <bookmark mark='uni'/>kept crystals cleanly separated right out to the corners."):
            self.play(Write(title), run_time=0.8)
            self.at("spec", FadeIn(spec))
            self.at("doi", Create(ax), FadeIn(key), FadeIn(lab), *[GrowFromEdge(b, DOWN) for b in bars[:2]], FadeIn(nums[:2]))
            self.at("en", *[GrowFromEdge(b, DOWN) for b in bars[2:]], FadeIn(nums[2:]))
            self.at("uni", FadeIn(uni))

        ax2 = Axes(x_range=[0, 3, 1], y_range=[0, 5, 1], x_length=4.6, y_length=3.2, tips=False,
                   axis_config={"color": GREY_B, "include_ticks": False}).shift(3.2 * RIGHT + 0.9 * DOWN)
        cls = [2.59, 4.51, 4.38]
        cnn = [1.84, 2.14, 2.55]
        b2, n2 = VGroup(), VGroup()
        for kx, (a, b) in enumerate(zip(cls, cnn)):
            for dx, v, col in ((-0.17, a, GLASS_C), (0.17, b, TEAL_L)):
                r = Rectangle(width=0.32, height=ax2.c2p(0, v)[1] - ax2.c2p(0, 0)[1], stroke_width=0, fill_color=col, fill_opacity=0.9)
                r.move_to(ax2.c2p(kx + 0.5 + dx, 0), aligned_edge=DOWN)
                b2.add(r)
                n2.add(Tex(f"{v:.2f}", font_size=22).next_to(r, UP, buff=0.06))
        xl2 = VGroup(*[Tex(s, font_size=24).next_to(ax2.c2p(k + 0.5, 0), DOWN, buff=0.15) for k, s in enumerate(["centre", "edge", "corner"])])
        key2 = VGroup(VGroup(Square(0.18, fill_color=GLASS_C, fill_opacity=1, stroke_width=0), Tex("ratio estimator", font_size=24)).arrange(RIGHT, buff=0.1),
                      VGroup(Square(0.18, fill_color=TEAL_L, fill_opacity=1, stroke_width=0), Tex("CNN", font_size=24)).arrange(RIGHT, buff=0.1)
                      ).arrange(RIGHT, buff=0.5).next_to(ax2, UP, buff=0.35)
        t2 = Tex(r"2021: DOI (mm FWHM), 4 signals", font_size=26).next_to(key2, UP, buff=0.25)
        note = Tex(r"array average with all 64 signals: 1.84 mm (CNN) vs 3.04 mm (ratio)", font_size=24, color=GREY_B).to_edge(DOWN, buff=0.2)
        with self.voiceover(text="A year later, they replaced the simple ratio with a small <bookmark mark='cnn'/>convolutional neural "
                                 "network. Depth resolution dropped to <bookmark mark='c'/>one point eight four millimetres averaged "
                                 "over the array, with the biggest gains at the <bookmark mark='e'/>edges and corners, where the ratio "
                                 "struggles. That is the best single ended depth resolution reported at twenty millimetres. One "
                                 "caveat: inter crystal scatter events, about forty percent of the photopeak, were cut first."):
            self.at("cnn", Create(ax2), FadeIn(key2), FadeIn(t2), FadeIn(xl2))
            self.at("c", GrowFromEdge(b2[0], DOWN), GrowFromEdge(b2[1], DOWN), FadeIn(n2[:2]), FadeIn(note))
            self.at("e", *[GrowFromEdge(r, DOWN) for r in b2[2:]], FadeIn(n2[2:]))
        fade_all(self)


class Scanner(Narrated):
    def construct(self):
        title = Tex(r"A brain scanner: Zeng et al.\ 2023").scale(0.72).to_edge(UP)
        c = 3.4 * LEFT + 0.4 * DOWN
        a_, b_ = 2.5, 1.9                              # semi-axes in proportion to 38.5 x 29.1 cm
        verts = [c + np.array([a_ * np.cos(t), b_ * np.sin(t), 0]) for t in np.linspace(0, TAU, 10, endpoint=False) + PI / 10]
        dec = Polygon(*verts, color=GREY_B, stroke_width=1.5)
        mods = VGroup()
        for i in range(10):
            p, q = verts[i], verts[(i + 1) % 10]
            for j in range(4):
                s = p + (q - p) * (j + 0.5) / 4
                tvec = (q - p) / np.linalg.norm(q - p)
                mods.add(Rectangle(width=np.linalg.norm(q - p) / 4 * 0.9, height=0.28, stroke_color=PRISM_C, stroke_width=1.2,
                                   fill_color=XTAL_C, fill_opacity=0.4).rotate(np.arctan2(tvec[1], tvec[0])).move_to(s))
        dl = Tex(r"decagon, 40 modules\\38.5 $\times$ 29.1 cm, 25.5 mm axial", font_size=26).next_to(dec, DOWN, buff=0.35)
        res = VGroup(Tex(r"DOI 2.85 mm, energy 12.6\%, timing 271 ps", font_size=28),
                     Tex(r"intrinsic resolution 1.22 mm (0.89--1.40)", font_size=28),
                     Tex(r"reconstructed 1.53 mm (3D FBP)", font_size=28),
                     Tex(r"1.00 mm Derenzo rods resolved", font_size=28, color=YELLOW),
                     Tex(r"sensitivity 1.2\% (400--650 keV window)", font_size=28)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.16).to_edge(RIGHT, buff=0.5).shift(0.6 * UP)
        fit_frame(res)
        with self.voiceover(text="In twenty twenty three the group built a prototype brain scanner: <bookmark mark='dec'/>forty modules in "
                                 "a single ring, arranged as a decagon that hugs the head. It reached <bookmark mark='r0'/>two point eight "
                                 "five millimetre depth resolution and two hundred and seventy one picosecond timing, and "
                                 "<bookmark mark='r1'/>one point two millimetre intrinsic spatial resolution. Reconstructed images reached "
                                 "<bookmark mark='r2'/>one point five three millimetres, and in a Derenzo phantom, <bookmark mark='r3'/>one "
                                 "millimetre rods were resolved, which the authors claim is the highest resolution reported for a human "
                                 "brain PET scanner. The price is <bookmark mark='r4'/>sensitivity: one point two percent, from a ring "
                                 "only two and a half centimetres long."):
            self.play(Write(title), run_time=0.8)
            self.at("dec", Create(dec), LaggedStart(*[FadeIn(m) for m in mods], lag_ratio=0.02), FadeIn(dl), run_time=1.4)
            for k in range(5):
                self.at(f"r{k}", FadeIn(res[k], shift=0.1 * RIGHT))
        fade_all(self)


class Tapered(Narrated):
    def construct(self):
        title = Tex(r"Depth from light's travel time: Zeng et al.\ 2024").scale(0.72).to_edge(UP)
        h, w = 4.0, 0.9
        cx = -4.2
        crys = Rectangle(width=w, height=h, stroke_color=XTAL_C, fill_color=XTAL_C, fill_opacity=0.18).move_to([cx, -0.3, 0])
        top, base = -0.3 + h / 2, -0.3 - h / 2
        prism = Polygon([cx - w / 2, top, 0], [cx + w / 2 + 0.9, top, 0], [cx + 0.45 / 1 + 0.0, top + 0.7, 0], stroke_color=PRISM_C,
                        fill_color=PRISM_C, fill_opacity=0.25)
        nb = Rectangle(width=w, height=h, stroke_color=XTAL_C, fill_color=XTAL_C, fill_opacity=0.12).next_to(crys, RIGHT, buff=0.0)
        s1 = Rectangle(width=w, height=0.22, stroke_width=0, fill_color=SIPM_C, fill_opacity=0.95).next_to(crys, DOWN, buff=0.02)
        s2 = s1.copy().next_to(nb, DOWN, buff=0.02)
        y0 = 0.4
        f = Dot([cx, y0, 0], color=LIGHT_C, radius=0.08)
        down = ray([(cx, y0), (cx, base)])
        up = ray([(cx, y0), (cx, top), (cx + 0.5, top + 0.5), (cx + w, top), (cx + w, base)])
        t1 = Tex(r"$t_1$", font_size=30, color=LIGHT_C).next_to(s1, DOWN, buff=0.1)
        t2 = Tex(r"$t_2$", font_size=30, color=LIGHT_C).next_to(s2, DOWN, buff=0.1)
        dt = MathTex(r"t_2 - t_1 \;\propto\; \text{depth}", font_size=34, color=LIGHT_C).next_to(VGroup(crys, nb), RIGHT, buff=0.7).shift(1.4 * UP)
        with self.voiceover(text="Light sharing also gives a second clock. Light from an interaction <bookmark mark='dn'/>heading down "
                                 "reaches the crystal's own sensor first. Light going <bookmark mark='up'/>up through the prism arrives at "
                                 "the neighbour later. The <bookmark mark='dt'/>difference in arrival times depends on depth: an optical "
                                 "time of flight."):
            self.play(Write(title), FadeIn(crys), FadeIn(nb), FadeIn(prism), FadeIn(s1), FadeIn(s2), run_time=1.0)
            self.at("dn", FadeIn(f, scale=0.4), Create(down), FadeIn(t1))
            self.at("up", Create(up), FadeIn(t2), run_time=1.2)
            self.at("dt", Write(dt))
        leak = Tex(r"problem: light leaks where crystals\\overhang the SiPM's active area", font_size=26).next_to(dt, DOWN, buff=0.4, aligned_edge=LEFT)
        fix = Tex(r"fix: taper each crystal from 1.5 to 1.2 mm\\at the readout end", font_size=26, color=TEAL_L).next_to(leak, DOWN, buff=0.3, aligned_edge=LEFT)
        taper = Polygon([cx - w / 2, top, 0], [cx + w / 2, top, 0], [cx + w / 2 - 0.15, base, 0], [cx - w / 2 + 0.15, base, 0],
                        stroke_color=TEAL_L, stroke_width=3)
        with self.voiceover(text="The catch is light <bookmark mark='leak'/>leaking at the crystal to sensor interface, which scrambles these "
                                 "timestamps. The fix: <bookmark mark='tap'/>taper each crystal from one point five millimetres down to one "
                                 "point two at the readout end, so it sits entirely inside the sensor's active area."):
            self.at("leak", FadeIn(leak))
            self.at("tap", FadeIn(fix), Create(taper))
        self.play(*[FadeOut(m) for m in (crys, nb, prism, s1, s2, f, down, up, t1, t2, taper)], dt.animate.shift(0 * UP), run_time=0.5)
        rows = [("time-of-flight DOI", "13.87 mm", "5.42 mm"), ("energy-based DOI (centre)", "3.18 mm", "2.35 mm"),
                ("energy resolution", "11.18\\%", "8.88\\%"), ("coincidence timing", "286 ps", "243 ps"),
                ("10-ring sensitivity (sim.)", "30.9 kcps/MBq", "29.5 kcps/MBq")]
        hdr = VGroup(Tex("", font_size=26), Tex("straight", font_size=26, color=GLASS_C), Tex("tapered", font_size=26, color=TEAL_L))
        tab = VGroup(hdr, *[VGroup(Tex(a, font_size=26), Tex(b, font_size=26), Tex(c, font_size=26, color=TEAL_L)) for a, b, c in rows])
        for i, row in enumerate(tab):
            for j, m in enumerate(row):
                m.move_to(np.array([[-3.6, 0.6, 3.3][j], 0.9 - 0.55 * i, 0]))
        fit_frame(tab)
        with self.voiceover(text="Tapering cut the <bookmark mark='a'/>time of flight depth resolution from almost fourteen millimetres to five "
                                 "point four, the first experimental demonstration of this kind of depth encoding in a module. It also "
                                 "improved the <bookmark mark='b'/>energy based depth, the <bookmark mark='c'/>energy resolution and the "
                                 "<bookmark mark='d'/>timing, while costing <bookmark mark='e'/>almost nothing in sensitivity. Combining "
                                 "time and light reached two point two five millimetres for centre crystals."):
            self.play(FadeOut(leak), FadeOut(fix), FadeOut(dt), FadeIn(hdr), run_time=0.5)
            for k, m in enumerate("abcde"):
                self.at(m, FadeIn(tab[k + 1], shift=0.1 * RIGHT))
        fade_all(self)


class Scatter(Narrated):
    def construct(self):
        title = Tex(r"The scatter problem: Petersen et al.\ 2020 and 2024").scale(0.72).to_edge(UP)
        n, w, h = 5, 0.7, 2.6
        xs = [-4.4 + k * w for k in range(n)]
        cols = VGroup(*[Rectangle(width=w * 0.92, height=h, stroke_color=XTAL_C, fill_color=XTAL_C, fill_opacity=0.18).move_to([x, 0.2, 0]) for x in xs])
        g_in = Arrow([xs[1] - 1.2, 2.4, 0], [xs[1], 0.8, 0], buff=0, color=GAM_C, stroke_width=4)
        p1, p2 = np.array([xs[1], 0.8, 0]), np.array([xs[3], -0.4, 0])
        comp = Arrow(p1, p2, buff=0, color=GAM_C, stroke_width=3, max_tip_length_to_length_ratio=0.12)
        d1, d2 = Dot(p1, color=YELLOW, radius=0.08), Dot(p2, color=YELLOW, radius=0.08)
        l1 = Tex("1st", font_size=24, color=YELLOW).next_to(d1, LEFT, buff=0.1)
        l2 = Tex("2nd", font_size=24, color=YELLOW).next_to(d2, RIGHT, buff=0.1)
        facts = VGroup(Tex(r"at 1.4 mm pitch, only 37\% of photopeak\\events stay in one crystal", font_size=26),
                       Tex(r"the scanner rejects inter-crystal scatter", font_size=26, color=RED)
                       ).arrange(DOWN, aligned_edge=LEFT, buff=0.25).next_to(cols, DOWN, buff=0.4).align_to(cols, LEFT)
        with self.voiceover(text="Thin crystals have a cost. A gamma often <bookmark mark='c'/>Compton scatters in one crystal and finishes "
                                 "in another. At one point four millimetres, <bookmark mark='f'/>only thirty seven percent of photopeak "
                                 "events stay in a single crystal, and the scanner simply <bookmark mark='rej'/>throws the rest away."):
            self.play(Write(title), FadeIn(cols), run_time=0.8)
            self.at("c", GrowArrow(g_in), FadeIn(d1), FadeIn(l1), GrowArrow(comp), FadeIn(d2), FadeIn(l2), run_time=1.2)
            self.at("f", FadeIn(facts[0]))
            self.at("rej", FadeIn(facts[1]))
        pat = VGroup()
        for k, (a, b) in enumerate([(0.9, 0.3), (0.2, 0.7)]):
            grp = VGroup(*[Rectangle(width=0.32, height=1.2 * v, stroke_width=0, fill_color=LIGHT_C if j == k else PRISM_C, fill_opacity=0.9)
                           .move_to([1.0 + 0.4 * j + 2.0 * k, 1.0, 0], aligned_edge=DOWN) for j, v in enumerate([a, b, 0.15])])
            pat.add(grp)
        plus = MathTex("+", font_size=40).move_to([2.4, 1.5, 0])
        eq = MathTex("=", font_size=40).move_to([4.4, 1.5, 0])
        tot = VGroup(*[Rectangle(width=0.32, height=1.2 * v, stroke_width=0, fill_color=WHITE, fill_opacity=0.85)
                       .move_to([4.9 + 0.4 * j, 1.0, 0], aligned_edge=DOWN) for j, v in enumerate([1.1, 1.0, 0.3])])
        pl = Tex(r"each crystal: a fixed pattern $\Rightarrow$ the readout is their sum", font_size=26).next_to(VGroup(pat, tot), DOWN, buff=0.3)
        res = VGroup(Tex(r"first crystal found: 83.0\% of all events", font_size=26),
                     Tex(r"64.7\% of inter-crystal scatter events", font_size=26),
                     Tex(r"wrong-LOR spillover 63.8\% $\to$ 47.0\%", font_size=26),
                     Tex(r"simulation only (GATE + TracePro)", font_size=26, color=GREY_B)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.12).next_to(pl, DOWN, buff=0.4)
        fit_frame(VGroup(pat, plus, eq, tot, pl, res))
        with self.voiceover(text="But the prisms make recovery possible. Because each crystal lights a <bookmark mark='p'/>fixed pattern, the "
                                 "readout of a scattered event is just <bookmark mark='sum'/>the sum of known patterns, which can be "
                                 "decomposed. In simulation, a neural network trained on these patterns <bookmark mark='r0'/>found the "
                                 "first crystal in eighty three percent of photopeak events, and in <bookmark mark='r1'/>about two thirds of the "
                                 "scattered ones, cutting events assigned to the <bookmark mark='r2'/>wrong line of response from sixty four "
                                 "to forty seven percent. It is <bookmark mark='r3'/>not yet shown on real data."):
            self.at("p", FadeIn(pat[0]), FadeIn(plus), FadeIn(pat[1]))
            self.at("sum", FadeIn(eq), FadeIn(tot), FadeIn(pl))
            for k in range(4):
                self.at(f"r{k}", FadeIn(res[k], shift=0.1 * RIGHT))
        fade_all(self)


class Outlook(Narrated):
    def construct(self):
        title = Tex("Where it is going").scale(0.72).to_edge(UP)
        now = VGroup(Tex(r"main project at Weill Cornell: a compact, portable, upright brain PET", font_size=28),
                     Tex(r"motion compensation and CT-less attenuation correction", font_size=28),
                     Tex(r"\$6.2M NIA grant (Nov 2024), aimed at early Alzheimer's diagnosis", font_size=28, color=YELLOW),
                     Tex(r"others adopting it: KU Leuven reads it from both ends", font_size=28)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.16).next_to(title, DOWN, buff=0.45)
        fit_frame(now)
        with self.voiceover(text="The group is now at Weill Cornell, where Prism-PET is the main brain project: a <bookmark mark='n0'/>compact, "
                                 "portable, upright scanner, with <bookmark mark='n1'/>motion compensation and attenuation correction "
                                 "without C T. In late twenty twenty four it won a <bookmark mark='n2'/>six point two million dollar grant "
                                 "from the National Institute on Aging, aimed at early diagnosis of Alzheimer's disease. And "
                                 "<bookmark mark='n3'/>other groups are taking the design up."):
            self.play(Write(title), run_time=0.8)
            for k in range(4):
                self.at(f"n{k}", FadeIn(now[k], shift=0.1 * RIGHT))
        take = VGroup(Tex(r"depth from one readout face, by shaping where the light goes", font_size=28, color=TEAL_L),
                      Tex(r"Prism-PET: deterministic, set by geometry at the far face", font_size=28, color=PRISM_C),
                      Tex(r"a scattering bulk: statistical, set inside the crystal", font_size=28, color=LIGHT_C)
                      ).arrange(DOWN, aligned_edge=LEFT, buff=0.16).next_to(now, DOWN, buff=0.55).align_to(now, LEFT)
        fit_frame(VGroup(now, take))
        with self.voiceover(text="The lesson for detector design: <bookmark mark='t0'/>you can get depth from a single readout face by shaping "
                                 "where the light goes. Prism-PET does it <bookmark mark='t1'/>deterministically, with geometry at the far "
                                 "end. The alternative is to shape it <bookmark mark='t2'/>statistically, inside the crystal itself, by "
                                 "engineering how it scatters light."):
            for k in range(3):
                self.at(f"t{k}", FadeIn(take[k], shift=0.1 * RIGHT))
        self.play(FadeOut(now), FadeOut(take), FadeOut(title))
        refs = VGroup(Tex("Prism-PET", font_size=40),
                      Tex(r"LaBella 2020 (JNM), 2021 (Med Phys); Zeng 2023, 2024 (Med Phys);", font_size=24, color=GREY_B),
                      Tex(r"Petersen 2020 (NSS/MIC), 2024 (PMB)", font_size=24, color=GREY_B),
                      Tex(CITE, font_size=24, color=TEAL_L)).arrange(DOWN, buff=0.18)
        with self.voiceover(text="Thanks for watching."):
            self.play(FadeIn(refs), run_time=1.0)
        self.wait(0.8)
        fade_all(self)
