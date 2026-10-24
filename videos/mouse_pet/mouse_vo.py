"""Explainer: the open-field mouse brain PET programme (Kyme, Meikle; Brain and Mind Centre, University of Sydney).

Source: the USYD literature-review note on the programme, with its numbers checked against
Enriquez-Mier-y-Teran et al. 2024 (PMB 69:115043, virtual cylinder), 2024 (PMB 69:165017, scatter network),
2025 (IEEE TRPMS 9:395, multiplexed detector) and 2026 (PMB 71:185006, uncollimated calibration). Every
drawing is new; the mouse, the light-sharing bars and the depth curves are illustrative.
Visuals are cued to the narration with <bookmark/> tags and self.at() (see ../DESIGN.md).
Render with render.sh, or one scene: manim -ql mouse_vo.py Detector
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import *  # noqa: E402,F401

XTAL_C, SIPM_C, LIGHT_C, GAM_C, PANEL_C, MOUSE_C = "#7fb3ff", "#4c8fe0", "#f5d76e", "#7ee081", "#b18cf0", "#d9c8b4"
CITE = r"Kyme \& Meikle \textperiodcentered\ Brain and Mind Centre, University of Sydney"


def mouse(scale=1.0):
    """A top-view cartoon mouse facing +x."""
    body = Ellipse(width=0.9, height=0.5, color=MOUSE_C, fill_color=MOUSE_C, fill_opacity=0.9, stroke_width=1)
    head = Ellipse(width=0.42, height=0.32, color=MOUSE_C, fill_color=MOUSE_C, fill_opacity=0.9, stroke_width=1).move_to(0.55 * RIGHT)
    ears = VGroup(*[Circle(radius=0.09, color=MOUSE_C, fill_color="#e8a0a0", fill_opacity=1, stroke_width=1).move_to(0.48 * RIGHT + s * 0.17 * UP)
                    for s in (1, -1)])
    tail = VMobject(stroke_color=MOUSE_C, stroke_width=2).set_points_smoothly([0.45 * LEFT, 0.75 * LEFT + 0.12 * UP, 1.0 * LEFT - 0.05 * UP])
    eye = Dot(0.66 * RIGHT + 0.06 * UP, radius=0.025, color=BLACK)
    return VGroup(tail, body, head, ears, eye).scale(scale)


def panels(c, s=2.4, t=0.3, color=PANEL_C):
    """Four overlapping detector panels around a square open field (top view)."""
    return VGroup(Rectangle(width=s + t, height=t).move_to(c + (s / 2 + t / 2) * UP + t / 2 * LEFT),
                  Rectangle(width=t, height=s + t).move_to(c + (s / 2 + t / 2) * RIGHT + t / 2 * UP),
                  Rectangle(width=s + t, height=t).move_to(c + (s / 2 + t / 2) * DOWN + t / 2 * RIGHT),
                  Rectangle(width=t, height=s + t).move_to(c + (s / 2 + t / 2) * LEFT + t / 2 * DOWN)
                  ).set_stroke(color, 2).set_fill(color, 0.3)


def ray(points, color=LIGHT_C, width=3):
    return VMobject(stroke_color=color, stroke_width=width).set_points_as_corners([np.array([x, y, 0]) for x, y in points])


class Opening(Narrated):
    def construct(self):
        title = Tex("Open-field mouse brain PET").scale(1.1).to_edge(UP, buff=0.5)
        foot = Tex(CITE, color=TEAL_L).scale(0.5).to_edge(DOWN, buff=0.35)
        c = 0.5 * DOWN
        box = panels(c)
        m = mouse(0.8).move_to(c + 0.5 * LEFT)
        path = VMobject().set_points_smoothly([c + 0.5 * LEFT, c + 0.4 * RIGHT + 0.5 * UP, c + 0.6 * RIGHT - 0.5 * DOWN * -1, c + 0.3 * DOWN, c + 0.5 * LEFT])
        with self.voiceover(text="Most PET scans of mice are done under anaesthesia, which changes how the brain works and rules out "
                                 "studying behaviour. This programme, led by Andre Kyme and Steven Meikle at the University of Sydney, "
                                 "is building a <bookmark mark='box'/>brain PET scanner for a mouse that is <bookmark mark='mouse'/>awake "
                                 "and free to move."):
            self.play(Write(title), FadeIn(foot), run_time=1.2)
            self.at("box", DrawBorderThenFill(box), run_time=1.0)
            self.at("mouse", FadeIn(m, scale=0.6))
            self.play(MoveAlongPath(m, path), run_time=3.0, rate_func=smooth)
        with self.voiceover(text="Here is what that takes, piece by piece: the detectors, how they are calibrated, how the images are "
                                 "reconstructed, and a hard limit the group found in the physics."):
            self.play(Rotate(m, PI / 3), m.animate.shift(0.3 * RIGHT), run_time=1.5)
        fade_all(self)


class Concept(Narrated):
    def construct(self):
        title = Tex("Imaging a moving brain").scale(0.72).to_edge(UP)
        c = 3.4 * LEFT + 0.4 * DOWN
        box = panels(c, s=3.0, t=0.35)
        m = mouse(0.9).move_to(c + 0.6 * LEFT + 0.3 * DOWN)
        pts = VGroup(Tex(r"four box-shaped panels around an open field", font_size=28),
                     Tex(r"motion tracking of the head", font_size=28),
                     Tex(r"motion-compensated reconstruction", font_size=28),
                     Tex(r"goal: brain PET and behaviour at the same time", font_size=28, color=YELLOW)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.16).to_edge(RIGHT, buff=0.5).shift(1.0 * UP)
        fit_frame(pts)
        src = m[2].get_center()
        lors = VGroup(*[Line(src + 2.0 * np.array([np.cos(a), np.sin(a), 0]), src - 2.0 * np.array([np.cos(a), np.sin(a), 0]),
                             color=GAM_C, stroke_width=1.5) for a in (0.3, 1.2, 2.2)])
        marker = SurroundingRectangle(m[2], color=RED, buff=0.06)
        with self.voiceover(text="The design surrounds an open field with <bookmark mark='p0'/>four box shaped detector panels. Because the "
                                 "mouse keeps moving, its head is <bookmark mark='p1'/>tracked, and every line of response is placed back "
                                 "into the brain's own frame of reference <bookmark mark='p2'/>during reconstruction. The aim is "
                                 "<bookmark mark='p3'/>brain PET and behaviour, recorded at the same time."):
            self.play(Write(title), run_time=0.8)
            self.at("p0", DrawBorderThenFill(box), FadeIn(m), FadeIn(pts[0]))
            self.at("p1", Create(marker), FadeIn(pts[1]))
            self.at("p2", LaggedStart(*[Create(l) for l in lors], lag_ratio=0.2), FadeIn(pts[2]), run_time=1.0)
            self.at("p3", FadeIn(pts[3]))
        need = VGroup(Tex(r"needs: fine crystals (sub-mm brain structures)", font_size=26),
                      Tex(r"depth of interaction (a box has big parallax)", font_size=26),
                      Tex(r"affordable electronics for thousands of channels", font_size=26)
                      ).arrange(DOWN, aligned_edge=LEFT, buff=0.12).next_to(pts, DOWN, buff=0.5, aligned_edge=LEFT)
        fit_frame(VGroup(pts, need))
        with self.voiceover(text="A mouse brain is tiny, so the detector needs <bookmark mark='n0'/>very fine crystals. Gammas hit the flat "
                                 "panels of a box at steep angles, so it also needs <bookmark mark='n1'/>depth of interaction. And all of "
                                 "this has to stay <bookmark mark='n2'/>affordable to read out."):
            for k in range(3):
                self.at(f"n{k}", FadeIn(need[k], shift=0.1 * RIGHT))
        fade_all(self)


class Motion(Narrated):
    def construct(self):
        title = Tex("How motion compensation works").scale(0.72).to_edge(UP)
        c = 3.3 * LEFT + 0.5 * DOWN
        box = panels(c, s=3.4, t=0.3)
        s_head = np.array([0.55, 0.0, 0])                       # a brain point, in the mouse's own frame (its head)
        poses = [(c + np.array([-0.6, -0.5, 0]), 0.0, 0.5), (c + np.array([0.5, 0.5, 0]), 2.1, 1.6)]   # (position, heading, LOR angle)

        def rot(v, a):
            return np.array([v[0] * np.cos(a) - v[1] * np.sin(a), v[0] * np.sin(a) + v[1] * np.cos(a), 0])

        mice, lors, srcs = VGroup(), VGroup(), VGroup()
        for (p, th, phi), col in zip(poses, (GAM_C, ORANGE_L)):
            m = mouse(0.75).rotate(th, about_point=ORIGIN).shift(p)
            w = p + rot(s_head * 0.75, th)
            u = np.array([np.cos(phi), np.sin(phi), 0])
            mice.add(m)
            lors.add(Line(w - 1.6 * u, w + 1.6 * u, color=col, stroke_width=3))
            srcs.add(Dot(w, color=RED, radius=0.05))
        sl = Tex("scanner frame", font_size=26).next_to(box, DOWN, buff=0.3)
        with self.voiceover(text="Each decay is recorded in the <bookmark mark='sc'/>scanner's frame. Here the same spot in the brain emits "
                                 "twice: once <bookmark mark='a'/>with the mouse here, and once <bookmark mark='b'/>after it has moved and "
                                 "turned. In the scanner's frame the two lines of response pass through different places, so an image "
                                 "made from them blurs."):
            self.play(Write(title), DrawBorderThenFill(box), FadeIn(sl), run_time=0.9)
            self.at("a", FadeIn(mice[0]), Create(lors[0]), FadeIn(srcs[0]))
            self.at("b", FadeIn(mice[1]), Create(lors[1]), FadeIn(srcs[1]))
        r = 3.4 * RIGHT + 0.5 * DOWN
        hm = mouse(1.4).shift(r)
        hs = Dot(r + s_head * 1.4, color=RED, radius=0.07)
        hl = VGroup()
        for (p, th, phi), col in zip(poses, (GAM_C, ORANGE_L)):
            u = np.array([np.cos(phi - th), np.sin(phi - th), 0])
            hl.add(Line(hs.get_center() - 1.8 * u, hs.get_center() + 1.8 * u, color=col, stroke_width=3))
        hlab = Tex("the mouse's own frame", font_size=26).next_to(hm, DOWN, buff=0.9)
        steps = VGroup(Tex(r"1.\ track the head's pose at each moment", font_size=26),
                       Tex(r"2.\ move each line by the inverse of that pose", font_size=26),
                       Tex(r"3.\ reconstruct in the head's frame", font_size=26)
                       ).arrange(DOWN, aligned_edge=LEFT, buff=0.1).next_to(hlab, DOWN, buff=0.25)
        fit_frame(steps)
        with self.voiceover(text="The fix: <bookmark mark='t'/>track the head's position and orientation at every moment, and "
                                 "<bookmark mark='inv'/>move each line of response by the inverse of that pose, into the mouse's own "
                                 "frame. There, both lines <bookmark mark='meet'/>cross at the same point in the brain, and the image "
                                 "is sharp again. The catch, which comes back later, is that the scanner's sensitivity also has to be "
                                 "recomputed for every pose."):
            self.at("t", FadeIn(steps[0]), Indicate(mice, color=RED))
            self.at("inv", FadeIn(steps[1]), FadeIn(hm), FadeIn(hlab), TransformFromCopy(lors[0], hl[0]), TransformFromCopy(lors[1], hl[1]),
                    run_time=1.4)
            self.at("meet", FadeIn(steps[2]), FadeIn(hs, scale=0.4), Flash(hs, color=YELLOW))
        fade_all(self)


class Detector(Narrated):
    def construct(self):
        title = Tex("Dual-ended readout").scale(0.72).to_edge(UP)
        h, w = 4.0, 0.7
        cx = -4.3
        crys = Rectangle(width=w, height=h, stroke_color=XTAL_C, fill_color=XTAL_C, fill_opacity=0.18).move_to([cx, -0.4, 0])
        top, base = -0.4 + h / 2, -0.4 - h / 2
        s_top = Rectangle(width=w + 0.3, height=0.22, stroke_width=0, fill_color=SIPM_C, fill_opacity=0.95).next_to(crys, UP, buff=0.04)
        s_bot = s_top.copy().next_to(crys, DOWN, buff=0.04)
        spec = VGroup(Tex(r"LYSO $0.785\times0.785\times20$ mm, 0.85 mm pitch", font_size=26),
                      Tex(r"23$\times$23 crystals per block", font_size=26),
                      Tex(r"$6\times6$ SiPMs (3.3 mm) on \emph{both} ends", font_size=26, color=SIPM_C)
                      ).arrange(DOWN, aligned_edge=LEFT, buff=0.12).to_edge(RIGHT, buff=0.5).shift(2.0 * UP)
        fit_frame(spec)
        with self.voiceover(text="The detector blocks are arrays of <bookmark mark='x'/>twenty three by twenty three L Y S O crystals, each less "
                                 "than eight tenths of a millimetre wide and twenty millimetres long. Each block is read at "
                                 "<bookmark mark='both'/>both ends, by silicon photomultipliers on the front and the back."):
            self.play(Write(title), run_time=0.8)
            self.at("x", FadeIn(crys), FadeIn(spec[0]), FadeIn(spec[1]))
            self.at("both", FadeIn(s_top), FadeIn(s_bot), FadeIn(spec[2]))

        def flash_at(y):
            f = Dot([cx, y, 0], color=LIGHT_C, radius=0.08)
            a = ray([(cx, y), (cx, top)], width=2 + 5 * (y - base) / h)
            b = ray([(cx, y), (cx, base)], width=2 + 5 * (top - y) / h)
            return VGroup(f, a, b)

        near_top = flash_at(top - 0.8)
        near_bot = flash_at(base + 0.8)
        ax = Axes(x_range=[0, 20, 5], y_range=[0, 1, 0.5], x_length=4.2, y_length=2.4, tips=False,
                  axis_config={"color": GREY_B, "font_size": 22}).move_to(0.6 * RIGHT + 0.9 * DOWN)
        ax.add_coordinates()
        xl = Tex(r"depth (mm)", font_size=24).next_to(ax, DOWN, buff=0.3)
        yl = MathTex(r"\frac{\text{front}}{\text{front} + \text{back}}", font_size=30).next_to(ax, UP, buff=0.2)
        curve = ax.plot(lambda z: 0.85 - 0.7 * z / 20, x_range=[0, 20], color=LIGHT_C)
        ill = Tex("illustrative", font_size=22, color=GREY_D).next_to(xl, DOWN, buff=0.08)
        with self.voiceover(text="The light from an interaction splits between the two ends. A hit <bookmark mark='t'/>near the front sends "
                                 "more light to the front, one <bookmark mark='b'/>near the back sends more to the back, so the "
                                 "<bookmark mark='r'/>fraction reaching each end measures depth."):
            self.at("t", FadeIn(near_top))
            self.at("b", ReplacementTransform(near_top, near_bot))
            self.at("r", Create(ax), FadeIn(xl), FadeIn(yl), Create(curve), FadeIn(ill), run_time=1.2)
        self.play(*[FadeOut(m) for m in (ax, xl, yl, curve, ill)], run_time=0.4)

        sig = VGroup(*[Line(np.array([-3.4, 0.4 - 0.13 * k, 0]), np.array([-2.0, -0.45 - 0.03 * k, 0]), color=SIPM_C, stroke_width=1.5)
                       for k in range(14)])
        board = RoundedRectangle(corner_radius=0.1, width=1.3, height=1.4, color=WHITE).move_to(1.3 * LEFT + 0.6 * DOWN)
        bl = Tex(r"custom\\multiplexing", font_size=22).move_to(board)
        outs = VGroup(*[Arrow(board.get_right() + (0.45 - 0.3 * k) * UP, board.get_right() + (0.45 - 0.3 * k) * UP + 1.0 * RIGHT, buff=0,
                              color=YELLOW, stroke_width=3, max_tip_length_to_length_ratio=0.2) for k in range(4)])
        asic = Tex(r"72 SiPM signals $\to$ 8 channels (9:1)\\into a PETsys TOFPET2 ASIC", font_size=26).next_to(board, DOWN, buff=0.4)
        res = VGroup(Tex(r"energy resolution $10.5 \pm 1.6\%$", font_size=28),
                     Tex(r"DOI resolution $2.3 \pm 0.3$ mm", font_size=28),
                     Tex(r"coincidence timing 1.3 ns", font_size=28, color=GREY_B)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.14).next_to(spec, DOWN, buff=0.6, aligned_edge=LEFT)
        fit_frame(VGroup(spec, res))
        with self.voiceover(text="Reading both ends would normally double the electronics. Instead, custom boards "
                                 "<bookmark mark='mux'/>combine the seventy two sensor signals of a block into just "
                                 "<bookmark mark='eight'/>eight channels, nine to one, feeding a low cost commercial chip. The 2025 paper "
                                 "reports <bookmark mark='r0'/>ten and a half percent energy resolution and <bookmark mark='r1'/>two point "
                                 "three millimetre depth resolution, at the price of <bookmark mark='r2'/>slower timing, one point three "
                                 "nanoseconds."):
            self.at("mux", LaggedStart(*[Create(s) for s in sig], lag_ratio=0.05), Create(board), FadeIn(bl), run_time=1.2)
            self.at("eight", LaggedStart(*[GrowArrow(o) for o in outs], lag_ratio=0.15), FadeIn(asic), run_time=1.0)
            for k in range(3):
                self.at(f"r{k}", FadeIn(res[k], shift=0.1 * RIGHT))
        fade_all(self)


class Calibration(Narrated):
    def construct(self):
        title = Tex("Calibrating depth without a collimator").scale(0.72).to_edge(UP)
        h, w = 3.6, 0.7
        def crystal(cx):
            r = Rectangle(width=w, height=h, stroke_color=XTAL_C, fill_color=XTAL_C, fill_opacity=0.18).move_to([cx, -0.3, 0])
            return VGroup(r, Rectangle(width=w + 0.3, height=0.2, stroke_width=0, fill_color=SIPM_C, fill_opacity=0.95).next_to(r, UP, buff=0.04),
                          Rectangle(width=w + 0.3, height=0.2, stroke_width=0, fill_color=SIPM_C, fill_opacity=0.95).next_to(r, DOWN, buff=0.04))
        old = crystal(-4.6)
        lead = VGroup(Rectangle(width=1.0, height=1.4, fill_color=GREY_D, fill_opacity=1, stroke_width=0).move_to([-2.9, 0.75, 0]),
                      Rectangle(width=1.0, height=1.4, fill_color=GREY_D, fill_opacity=1, stroke_width=0).move_to([-2.9, -1.35, 0]))
        beam = Arrow([-1.9, -0.3, 0], [-4.6, -0.3, 0], buff=0, color=GAM_C, stroke_width=4)
        step = VGroup(*[DashedLine([-5.2, y, 0], [-4.0, y, 0], color=GREY_B, stroke_width=1.5) for y in np.linspace(-1.8, 1.2, 5)])
        ol = Tex(r"usual: a collimated beam\\stepped along the depth", font_size=26).next_to(old, DOWN, buff=0.35).shift(0.9 * RIGHT)
        with self.voiceover(text="Every crystal needs its depth signal calibrated. The usual way is a <bookmark mark='col'/>collimated beam "
                                 "through a slit in lead, <bookmark mark='step'/>stepped to known depths one at a time, which is slow for "
                                 "thousands of crystals."):
            self.play(Write(title), FadeIn(old), run_time=0.8)
            self.at("col", FadeIn(lead), GrowArrow(beam), FadeIn(ol))
            self.at("step", Create(step), run_time=1.0)

        new = crystal(1.4)
        srcd = Dot([1.4, 2.1, 0], color=RED, radius=0.12)
        sl = Tex(r"$^{22}$Na on the front face", font_size=24, color=RED).next_to(srcd, RIGHT, buff=0.2)
        gams = VGroup(*[Arrow([1.4 + dx, 1.95, 0], [1.4 + dx, 1.95 - L, 0], buff=0, color=GAM_C, stroke_width=3, max_tip_length_to_length_ratio=0.15)
                        for dx, L in [(-0.2, 1.0), (0.0, 2.2), (0.2, 3.1)]])
        ax = Axes(x_range=[0, 20, 5], y_range=[0, 1, 0.5], x_length=3.0, y_length=2.4, tips=False,
                  axis_config={"color": GREY_B, "include_ticks": False}).move_to([4.6, -0.3, 0])
        exp = ax.plot(lambda z: np.exp(-z / 11.0), x_range=[0, 20], color=GAM_C)
        xl = Tex(r"depth (mm)", font_size=24).next_to(ax, DOWN, buff=0.12)
        el = Tex(r"interactions vs depth:\\known exponential", font_size=24).next_to(ax, UP, buff=0.15)
        with self.voiceover(text="Their 2026 paper skips that. Put an ordinary <bookmark mark='src'/>sodium twenty two source on the front "
                                 "face. Its gammas travel <bookmark mark='along'/>along the crystals, and how many stop at each depth "
                                 "follows a <bookmark mark='exp'/>known exponential, so one uncollimated exposure already contains every "
                                 "depth, in known proportions."):
            self.at("src", FadeIn(new), FadeIn(srcd, scale=0.5), FadeIn(sl))
            self.at("along", LaggedStart(*[GrowArrow(g) for g in gams], lag_ratio=0.2), run_time=1.0)
            self.at("exp", Create(ax), Create(exp), FadeIn(xl), FadeIn(el))
        res = VGroup(Tex(r"two calibrations (physics model, neural network): 0.36--0.61 mm RMSE vs collimated", font_size=26),
                     Tex(r"a 4$\times$4 panel from one flood: DOI 2.0 mm, energy 15.6\%", font_size=26, color=YELLOW)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.14).to_edge(DOWN, buff=0.35)
        fit_frame(res)
        with self.voiceover(text="Two calibrations built on this, one <bookmark mark='m'/>physics based and one a small neural network, "
                                 "matched the collimated gold standard to within about half a millimetre. A full <bookmark mark='pan'/>four "
                                 "by four panel was then calibrated from a single exposure, reaching two millimetre depth resolution."):
            self.at("m", FadeOut(ol), FadeIn(res[0], shift=0.1 * UP))
            self.at("pan", FadeIn(res[1], shift=0.1 * UP))
        fade_all(self)


class Virtual(Narrated):
    def construct(self):
        title = Tex("Too many lines of response").scale(0.72).to_edge(UP)
        c = 3.6 * LEFT + 0.4 * DOWN
        s = 3.0
        box = panels(c, s=s, t=0.35)
        rng = np.random.default_rng(4)
        sides = [(c + np.array([x, s / 2, 0])) for x in np.linspace(-1.3, 1.3, 7)] + [(c + np.array([s / 2, y, 0])) for y in np.linspace(-1.3, 1.3, 7)]
        others = [(c + np.array([x, -s / 2, 0])) for x in np.linspace(-1.3, 1.3, 7)] + [(c + np.array([-s / 2, y, 0])) for y in np.linspace(-1.3, 1.3, 7)]
        many = VGroup(*[Line(sides[i], others[j], color=GAM_C, stroke_width=0.8, stroke_opacity=0.5)
                        for i, j in zip(rng.integers(0, 14, 90), rng.integers(0, 14, 90))])
        facts = VGroup(Tex(r"fine crystals $\times$ DOI bins: LORs grow as $N_{\mathrm{DOI}}^2$", font_size=28),
                       Tex(r"$\approx$7.3 billion LORs, a $\sim$8 TB system matrix", font_size=28, color=RED),
                       Tex(r"motion compensation: recomputed for every pose", font_size=28)
                       ).arrange(DOWN, aligned_edge=LEFT, buff=0.16).to_edge(RIGHT, buff=0.5).shift(1.6 * UP)
        fit_frame(facts)
        with self.voiceover(text="Depth information has a cost in reconstruction. Every pair of crystals, at every pair of "
                                 "<bookmark mark='n'/>depth bins, is its own line of response. For this scanner that is "
                                 "<bookmark mark='b'/>about seven point three billion lines, and a system matrix of around eight "
                                 "terabytes. Motion compensation makes it worse, because the sensitivity has to be "
                                 "<bookmark mark='m'/>recomputed as the animal moves."):
            self.play(Write(title), DrawBorderThenFill(box), run_time=0.9)
            self.at("n", LaggedStart(*[Create(l) for l in many], lag_ratio=0.01), FadeIn(facts[0]), run_time=1.4)
            self.at("b", FadeIn(facts[1]))
            self.at("m", FadeIn(facts[2]))
        ring = Circle(radius=1.0, color=YELLOW, stroke_width=3).move_to(c)
        ticks = VGroup(*[Dot(c + 1.0 * np.array([np.cos(a), np.sin(a), 0]), radius=0.03, color=YELLOW) for a in np.linspace(0, TAU, 48, endpoint=False)])
        fix = VGroup(Tex(r"virtual cylinder of small detectors inside the field", font_size=28, color=YELLOW),
                     Tex(r"each real LOR rebinned to the virtual pair it crosses", font_size=28),
                     Tex(r"0.47 mm virtual detectors, 6 DOI bins: 86\% fewer LORs", font_size=28),
                     Tex(r"images nearly identical; sub-mm resolution", font_size=28)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.16).next_to(facts, DOWN, buff=0.5, aligned_edge=LEFT)
        fit_frame(VGroup(facts, fix))
        with self.voiceover(text="The 2024 fix is a <bookmark mark='v'/>virtual cylinder: a ring of small imaginary detectors inside the "
                                 "field of view. <bookmark mark='r'/>Each real line of response is assigned to the virtual pair it passes "
                                 "through, so many real lines collapse into one. With <bookmark mark='c'/>zero point four seven "
                                 "millimetre virtual detectors and six depth bins, that removes eighty six percent of the lines, with "
                                 "<bookmark mark='i'/>transaxial images almost identical to the full geometry and sub millimetre "
                                 "resolution across the field."):
            self.at("v", Create(ring), FadeIn(ticks), FadeIn(fix[0]))
            self.at("r", many.animate.set_stroke(opacity=0.15), FadeIn(fix[1]))
            self.at("c", FadeIn(fix[2]))
            self.at("i", FadeIn(fix[3]))
        fade_all(self)


class Scatter(Narrated):
    def construct(self):
        title = Tex("Which crystal was hit first?").scale(0.72).to_edge(UP)
        n, w, h = 5, 0.7, 2.6
        xs = [-4.6 + k * w for k in range(n)]
        cols = VGroup(*[Rectangle(width=w * 0.92, height=h, stroke_color=XTAL_C, fill_color=XTAL_C, fill_opacity=0.18).move_to([x, 0.6, 0]) for x in xs])
        g_in = Arrow([xs[2], 2.6, 0], [xs[2], 1.0, 0], buff=0, color=GAM_C, stroke_width=4)
        p1 = np.array([xs[2], 1.0, 0])
        fwd = Arrow(p1, [xs[4], 0.0, 0], buff=0, color=GAM_C, stroke_width=3, max_tip_length_to_length_ratio=0.15)
        bwd = Arrow(p1, [xs[0], 1.8, 0], buff=0, color=ORANGE_L, stroke_width=3, max_tip_length_to_length_ratio=0.15)
        fl = Tex("forward", font_size=24, color=GAM_C).next_to(cols, RIGHT, buff=0.2).set_y(fwd.get_end()[1])
        bl = Tex("backward", font_size=24, color=ORANGE_L).next_to(cols, LEFT, buff=0.2).set_y(bwd.get_end()[1])
        hit = Dot(p1, color=YELLOW, radius=0.08)
        with self.voiceover(text="With crystals this fine, a gamma often <bookmark mark='c'/>Compton scatters in one crystal and is absorbed "
                                 "in another. To draw the right line of response, the system must pick the crystal hit "
                                 "<bookmark mark='first'/>first. If scattering were mostly <bookmark mark='f'/>forward, the energies would "
                                 "usually give it away."):
            self.play(Write(title), FadeIn(cols), run_time=0.8)
            self.at("c", GrowArrow(g_in), FadeIn(hit, scale=0.4))
            self.at("first", Flash(hit, color=YELLOW))
            self.at("f", GrowArrow(fwd), FadeIn(fl))
        ax = Axes(x_range=[0, 2, 1], y_range=[0, 80, 20], x_length=3.4, y_length=2.6, tips=False,
                  axis_config={"color": GREY_B, "include_ticks": False}).to_edge(RIGHT, buff=1.0).shift(1.0 * UP)
        bars = VGroup()
        for k, (v, col) in enumerate([(54, GAM_C), (46, ORANGE_L)]):
            bars.add(Rectangle(width=0.8, height=ax.c2p(0, v)[1] - ax.c2p(0, 0)[1], stroke_width=0, fill_color=col, fill_opacity=0.9)
                     .move_to(ax.c2p(k + 0.5, 0), aligned_edge=DOWN))
        nums = VGroup(*[Tex(f"{v}\\%", font_size=26).next_to(b, UP, buff=0.08) for v, b in zip((54, 46), bars)])
        xl = VGroup(Tex("forward", font_size=24).next_to(ax.c2p(0.5, 0), DOWN, buff=0.12), Tex("backward", font_size=24).next_to(ax.c2p(1.5, 0), DOWN, buff=0.12))
        naive = DashedLine(ax.c2p(0.05, 70), ax.c2p(0.95, 70), color=RED, stroke_width=3)
        nl = Tex(r"naive Klein--Nishina: 70\%", font_size=24, color=RED).next_to(ax, UP, buff=0.2)
        with self.voiceover(text="But in their simulation of the real detector, scattering into a neighbouring crystal is <bookmark mark='b'/>"
                                 "almost evenly split: fifty four percent forward, forty six percent <bookmark mark='bk'/>backward, not the "
                                 "<bookmark mark='kn'/>seventy percent forward a naive Klein Nishina reading suggests."):
            self.at("b", Create(ax), FadeIn(xl), GrowFromEdge(bars[0], DOWN), FadeIn(nums[0]))
            self.at("bk", GrowArrow(bwd), FadeIn(bl), GrowFromEdge(bars[1], DOWN), FadeIn(nums[1]))
            self.at("kn", Create(naive), FadeIn(nl))
        res = VGroup(Tex(r"network: right crystal for 90\% of single-crystal events, 82\% of scattered", font_size=26),
                     Tex(r"positioning $\geq$34\% and $\geq$14\% better than Anger logic", font_size=26),
                     Tex(r"but with forward $\approx$ backward, the first crystal can't be picked with certainty", font_size=26, color=YELLOW),
                     Tex(r"from energies and light patterns alone", font_size=26, color=YELLOW)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.12).to_edge(DOWN, buff=0.35)
        fit_frame(res)
        with self.voiceover(text="A neural network still does well: it finds the right crystal for <bookmark mark='r0'/>ninety percent of "
                                 "single crystal events and eighty two percent of scattered ones, and <bookmark mark='r1'/>positions events "
                                 "better than classic Anger logic. But the authors name the ceiling: with forward and backward scatter "
                                 "<bookmark mark='r2'/>close to one to one, energies and light patterns alone can't pick the first crystal "
                                 "with certainty."):
            self.at("r0", FadeIn(res[0], shift=0.1 * UP))
            self.at("r1", FadeIn(res[1], shift=0.1 * UP))
            self.at("r2", FadeIn(res[2], shift=0.1 * UP), FadeIn(res[3], shift=0.1 * UP))
        fade_all(self)


class Outlook(Narrated):
    def construct(self):
        title = Tex("What the programme shows").scale(0.72).to_edge(UP)
        pts = VGroup(Tex(r"$\bullet$ dual-ended DOI without doubling the electronics (9:1 multiplexing)", font_size=28),
                     Tex(r"$\bullet$ depth calibration from one uncollimated flood", font_size=28),
                     Tex(r"$\bullet$ DOI reconstruction made tractable by a virtual cylinder", font_size=28),
                     Tex(r"$\bullet$ a physical limit on ordering interactions from energy alone", font_size=28)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.18).next_to(title, DOWN, buff=0.5)
        fit_frame(pts)
        with self.voiceover(text="Put together, the programme shows <bookmark mark='p0'/>dual ended depth encoding at a fraction of the usual "
                                 "channel count, a <bookmark mark='p1'/>calibration that needs no collimator, <bookmark mark='p2'/>"
                                 "reconstruction that stays tractable with depth bins and motion, and a <bookmark mark='p3'/>clear "
                                 "statement of what energies alone can't tell you about scatter."):
            self.play(Write(title), run_time=0.8)
            for k in range(4):
                self.at(f"p{k}", FadeIn(pts[k], shift=0.1 * RIGHT))
        nxt = VGroup(Tex(r"the open question for the scatter limit: timing", font_size=28, color=TEAL_L),
                     Tex(r"funded by the Australian Research Council; with UC Davis", font_size=26, color=GREY_B)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.16).next_to(pts, DOWN, buff=0.6, aligned_edge=LEFT)
        fit_frame(VGroup(pts, nxt))
        with self.voiceover(text="That last point leaves an <bookmark mark='q'/>open question: whether adding arrival times can do what "
                                 "energies can't, and put scattered interactions in the right order. The work is <bookmark mark='f'/>funded "
                                 "by the Australian Research Council, with collaborators at U C Davis."):
            self.at("q", FadeIn(nxt[0], shift=0.1 * UP))
            self.at("f", FadeIn(nxt[1], shift=0.1 * UP))
        self.play(FadeOut(pts), FadeOut(nxt), FadeOut(title))
        refs = VGroup(Tex("Open-field mouse brain PET", font_size=40),
                      Tex(r"Enr\'iquez-Mier-y-Ter\'an \emph{et al.}: PMB 2024 (two papers), TRPMS 2025, PMB 2026", font_size=24, color=GREY_B),
                      Tex(CITE, font_size=24, color=TEAL_L)).arrange(DOWN, buff=0.2)
        fit_frame(refs)
        with self.voiceover(text="Thanks for watching."):
            self.play(FadeIn(refs), run_time=1.0)
        self.wait(0.8)
        fade_all(self)
