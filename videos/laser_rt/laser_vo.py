"""Explainer: R. Alabd and D. R. Franklin, 'Laser-driven particle accelerators for cancer therapy: a review of
state-of-the-art techniques, challenges and opportunities', Phys. Med. Biol. (2026), accepted manuscript, CC BY 4.0.

Intent (survey): leave with a map of the field: three mechanisms, what each produces, how far each has got,
where each wins, and what blocks the clinic. A navigator chip strip keeps the map on screen; Compare and FieldMap
close the loop. Every number is from the review's text. Its four figures are schematics (depth-dose curves, LWFA, TNSA, RPA), so
they are redrawn as step-by-step animations (docs/DESIGN.md §4: mechanisms are remade, not reused). Computed here and
labelled: proton/carbon ranges from the Bragg-Kleeman rule (R = 0.0022 E^1.77 cm in water, carbon scaled by A/Z^2),
dipole radii from r = p/(qB), the spread-out Bragg peak weights, and all depth-dose shapes (illustrative).
Visuals are cued to the narration with <bookmark/> tags and self.at() (see docs/DESIGN.md).
Render with render.sh, or one scene: manim -ql laser_vo.py TNSA
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import *  # noqa: E402,F401

LASER_C, ELEC_C, ION_C, PROT_C, CARB_C, XRAY_C = "#ff4d6d", BLUE_L, ORANGE_L, "#ffb347", PURPLE_L, YELLOW
GOOD_C, BAD_C, FOIL_C, H_C = "#7ee081", "#ff5c5c", GREY_B, "#ff8fa3"
CITE = r"Alabd \& Franklin, Phys.\ Med.\ Biol.\ 2026 (review)"


# ---- computed models ---------------------------------------------------------------------------------------------
def bk_range(E, A=1, Z=1):
    """Range in water (cm) at E MeV per nucleon: Bragg-Kleeman for protons, scaled by A/Z^2 for heavier ions."""
    return 0.0022 * E ** 1.77 * A / Z ** 2


def bragg(z, R, sharp=1.0, tail=0.0):
    """Peak-normalised depth dose: Bortfeld-like (R - z)^(1/p - 1) core, Gaussian range straggling, optional
    fragment tail beyond the peak. Illustrative shape, correct peak position."""
    zz = np.linspace(0, R * 1.4 + 6, 1400)
    core = np.where(zz < R, np.maximum(R - zz, 2e-3) ** (1 / 1.77 - 1), 0.0)
    sig = max(0.012 * R / sharp, 0.05)
    dz = zz[1] - zz[0]
    n = int(4 * sig / dz) + 1
    ker = np.exp(-0.5 * ((np.arange(-n, n + 1) * dz) / sig) ** 2)
    d = np.convolve(core, ker / ker.sum(), mode="same")
    d /= d.max()
    if tail:
        d = d + tail * (zz > R) * np.exp(-(zz - R) / 4.0)
        d /= d.max()
    return np.interp(z, zz, d)


def photon_dd(z):
    d = (1 - np.exp(-np.asarray(z) / 1.2)) * np.exp(-0.045 * np.asarray(z))
    return d / 0.92


def vhee_dd(z):
    z = np.asarray(z)
    return np.clip((1 - np.exp(-z / 3.0)) * (0.82 + 0.18 * np.exp(-((z - 14) / 14) ** 2)), 0, 1) / 0.98


def momentum(T, m):
    return np.sqrt(T * T + 2 * T * m)               # MeV/c


def credit():
    return Tex(CITE, font_size=18, color=GREY_B).to_corner(DR, buff=0.15)


def log_axis(lo, hi, length, labels, y=0.0, fs=18):
    """A horizontal log10 axis from 10^lo to 10^hi with chosen tick labels {exponent: text}."""
    ax = NumberLine(x_range=[lo, hi, 1], length=length, include_ticks=True, color=GREY_B).shift(UP * y)
    labs = VGroup(*[Tex(t, font_size=fs, color=GREY_B).next_to(ax.n2p(e), DOWN, buff=0.12) for e, t in labels.items()])
    return ax, labs


def tile(icon, text, w=3.0, fs=24):
    icon = icon.copy().scale_to_fit_height(min(icon.height, 0.55))
    g = VGroup(icon, Tex(text, font_size=fs)).arrange(RIGHT, buff=0.22)
    box = RoundedRectangle(corner_radius=0.1, width=max(w, g.width + 0.35), height=0.85, stroke_color=GREY_D, stroke_width=1.5)
    return VGroup(box, g.move_to(box))


def pulse_curve(width=2.4, height=1.0, cycles=9, color=LASER_C):
    f = lambda x: height * np.exp(-(x / (width / 4)) ** 2) * np.cos(2 * PI * cycles * x / width)
    return ParametricFunction(lambda t: np.array([t, f(t), 0]), t_range=[-width / 2, width / 2], color=color, stroke_width=3)


BRANCHES = [("LWFA", r"e$^-$", ELEC_C), ("TNSA", r"p", PROT_C), ("RPA", r"p, C", CARB_C)]


def map_chips(active=None, scale=1.0):
    """The field map as three chips (mechanism -> particle). active: index of the branch in view, 'all' for
    a cross-cutting section, None for none highlighted."""
    chips = VGroup()
    for k, (n, p, c) in enumerate(BRANCHES):
        on = active == k
        fill = 0.85 if on else (0.25 if active == "all" else 0.0)
        box = RoundedRectangle(corner_radius=0.06, width=1.05, height=0.36, stroke_color=c, stroke_width=1.5, fill_color=c, fill_opacity=fill)
        t = Tex(n + r" $\to$ " + p, font_size=15, color=BLACK if on else c).move_to(box)
        chips.add(VGroup(box, t))
    return chips.arrange(RIGHT, buff=0.08).scale(scale)


def nav(active=None, section=None):
    """A small map in the top-left corner, so the viewer always knows which branch or section they are in."""
    g = VGroup(map_chips(active))
    if section:
        g.add(Tex(section, font_size=16, color=GREY_A).next_to(g[0], DOWN, buff=0.06, aligned_edge=LEFT))
    return g.to_corner(UL, buff=0.2)


def spotlight(scene, keep, run_time=0.5, fade=0.7):
    """Steer the eye (docs/DESIGN.md §1): dim everything on screen except `keep` (and the title/navigator strip at the
    top) to about 30%. Returns the animation that restores it. Mobjects with updaters are left alone."""
    keep_fam = set()
    for k in keep:
        keep_fam |= set(k.get_family())
    others = [m for m in scene.mobjects if isinstance(m, VMobject) and not m.updaters and not (set(m.get_family()) & keep_fam)
              and m.get_center()[1] < 3.0]                   # VMobject only: ValueTrackers live in scene.mobjects and cannot fade
    for m in others:
        m.save_state()
    if others:
        scene.play(*[m.animate.fade(fade) for m in others], run_time=run_time)
    return AnimationGroup(*[Restore(m) for m in others], run_time=run_time) if others else Wait(0.01)


def b_symbols(rect, into=True, nx=4, ny=4, color=BLUE_L):
    """A magnetic field into (x in a circle) or out of (dot in a circle) the page, tiled over a rectangle."""
    g = VGroup()
    for i in range(nx):
        for j in range(ny):
            p = rect.get_corner(DL) + np.array([(i + 0.5) * rect.width / nx, (j + 0.5) * rect.height / ny, 0])
            c = Circle(radius=0.1, color=color, stroke_width=2).move_to(p)
            mark = VGroup(Line(p + UL * 0.06, p + DR * 0.06), Line(p + UR * 0.06, p + DL * 0.06)).set_stroke(color, 2) if into \
                else Dot(p, radius=0.03, color=color)
            g.add(VGroup(c, mark))
    return g


def e_arrows(start, end, n=3, spread=0.5, color=YELLOW, sw=3):
    """A few parallel electric-field arrows from `start` to `end` (from + toward -), spread perpendicular to the line."""
    d = np.array(end) - np.array(start)
    perp = np.array([-d[1], d[0], 0]) / max(np.linalg.norm(d), 1e-6)
    offs = np.linspace(-spread, spread, n) if n > 1 else [0.0]
    return VGroup(*[Arrow(np.array(start) + o * perp, np.array(end) + o * perp, buff=0, color=color, stroke_width=sw,
                          max_tip_length_to_length_ratio=0.25) for o in offs])


def foil(w, h, color=FOIL_C):
    return Rectangle(width=w, height=h, fill_color=color, fill_opacity=0.5, stroke_color=color, stroke_width=1.5)


# ---- scenes ------------------------------------------------------------------------------------------------------
class Opening(Narrated):
    def construct(self):
        title = Tex(r"\textbf{Laser-driven particle accelerators}", font_size=46).to_edge(UP, buff=0.35)
        sub = Tex(r"for cancer therapy", font_size=34, color=GREY_B).next_to(title, DOWN, buff=0.15)
        who = Tex(r"Roumani Alabd \& Daniel Franklin, UTS --- Phys.\ Med.\ Biol.\ 2026", font_size=24, color=GREY_B).next_to(sub, DOWN, buff=0.15)
        # conventional: a synchrotron ring of magnets in a building
        ring = Circle(radius=1.5, color=GREY_B, stroke_width=6).move_to(LEFT * 3.6 + DOWN * 1.0)
        mags = VGroup(*[Rectangle(width=0.35, height=0.2, fill_color=BLUE_L, fill_opacity=0.9, stroke_width=0).move_to(
            ring.point_at_angle(a)).rotate(a + PI / 2) for a in np.linspace(0, TAU, 12, endpoint=False)])
        bld = DashedVMobject(Rectangle(width=4.2, height=3.6, color=GREY_C)).move_to(ring)
        p = Dot(ring.point_at_angle(0), color=PROT_C, radius=0.08)
        cl = Tex(r"tens of metres", font_size=26).next_to(bld, DOWN, buff=0.15)
        # laser: a pulse into a foil, a spray of ions
        f_ = foil(0.08, 1.4).move_to(RIGHT * 3.4 + DOWN * 1.0)
        pulse = pulse_curve(1.4, 0.45).next_to(f_, LEFT, buff=1.2)
        spray = VGroup(*[Arrow(f_.get_right(), f_.get_right() + 1.5 * np.array([np.cos(a), np.sin(a), 0]), buff=0.02, color=PROT_C,
                               stroke_width=3, max_tip_length_to_length_ratio=0.15) for a in np.linspace(-0.35, 0.35, 5)])
        ll = Tex(r"millimetres", font_size=26).next_to(f_, DOWN, buff=1.0).set_x(f_.get_x())
        q = map_chips(scale=1.6).move_to(UP * 1.05)
        ql = Tex(r"the map: \textbf{3} mechanisms $\to$ how far $\to$ what blocks", font_size=24, color=GREY_A).next_to(q, UP, buff=0.15)
        with self.voiceover(text="This video explains a review by Roumani Alabd and Daniel Franklin on laser driven particle "
                                 "accelerators for cancer therapy. <bookmark mark='c'/>Today, the proton and ion beams used in "
                                 "therapy come from accelerators the size of a building: linacs, cyclotrons and synchrotrons. "
                                 "<bookmark mark='l'/>A laser plasma accelerator does the accelerating over millimetres instead of tens "
                                 "of metres, <bookmark mark='p'/>by hitting a target with an extremely intense, extremely short laser "
                                 "pulse. <bookmark mark='q'/>By the end, you should have a map of the field: three ways to accelerate, "
                                 "what each one produces, how far each has got, and what still blocks the clinic."):
            self.play(Write(title), FadeIn(sub), FadeIn(who), run_time=1.2)
            self.at("c", Create(ring), FadeIn(mags), Create(bld), FadeIn(cl), FadeIn(p))
            self.play(MoveAlongPath(p, ring), run_time=1.5, rate_func=linear)
            self.at("l", FadeIn(f_), FadeIn(ll))
            self.at("p", Create(pulse), run_time=0.6)
            self.play(pulse.animate.next_to(f_, LEFT, buff=0.02), run_time=0.5, rate_func=linear)
            self.play(FadeOut(pulse), LaggedStart(*[GrowArrow(a) for a in spray], lag_ratio=0.1), run_time=0.8)
            self.at("q", LaggedStart(*[FadeIn(x, shift=0.1 * UP) for x in q], lag_ratio=0.3), FadeIn(ql), run_time=1.5)
        self.wait(0.5)
        fade_all(self)


class WhyParticles(Narrated):
    def construct(self):
        title = Tex(r"why charged particles", font_size=34).to_edge(UP, buff=0.35)
        ax = Axes(x_range=[0, 42, 10], y_range=[0, 1.1, 0.5], x_length=8.0, y_length=3.6, tips=False,
                  axis_config={"color": GREY_B, "font_size": 20}, x_axis_config={"numbers_to_include": [0, 10, 20, 30, 40]},
                  y_axis_config={"include_ticks": False}).move_to(LEFT * 1.6 + DOWN * 0.3)
        axl = VGroup(Tex(r"depth in water (cm)", font_size=20, color=GREY_B).next_to(ax, DOWN, buff=0.15),
                     Tex(r"dose", font_size=20, color=GREY_B).next_to(ax.y_axis, UP, buff=0.1))
        tum = Rectangle(width=ax.c2p(17.5, 0)[0] - ax.c2p(13.5, 0)[0], height=ax.c2p(0, 1.1)[1] - ax.c2p(0, 0)[1], fill_color=BAD_C,
                        fill_opacity=0.15, stroke_width=0).move_to(ax.c2p(13.5, 0), aligned_edge=DL)
        tl = Tex(r"tumour", font_size=22, color=BAD_C).next_to(tum, UP, buff=0.05)
        Rp, Rc = bk_range(150), bk_range(290, 12, 6)
        cx = ax.plot(photon_dd, x_range=[0, 42], color=XRAY_C, stroke_width=4)
        cp = ax.plot(lambda z: bragg(z, Rp), x_range=[0, 42, 0.05], color=PROT_C, stroke_width=4)
        cc = ax.plot(lambda z: bragg(z, Rc, sharp=1.8, tail=0.12), x_range=[0, 42, 0.05], color=CARB_C, stroke_width=4)
        ce = ax.plot(vhee_dd, x_range=[0, 42], color=ELEC_C, stroke_width=4)
        leg = VGroup(*[Tex(t, font_size=22, color=c) for t, c in (("X-ray photons", XRAY_C), ("protons, 150 MeV", PROT_C),
                                                                  ("carbon, 290 MeV/u", CARB_C), ("VHEE electrons", ELEC_C))])
        leg.arrange(DOWN, aligned_edge=LEFT, buff=0.15).next_to(ax, RIGHT, buff=0.3).shift(UP * 0.8)
        E = ValueTracker(150.0)
        slider = always_redraw(lambda: ax.plot(lambda z: bragg(z, bk_range(E.get_value())), x_range=[0, 42, 0.05], color=PROT_C, stroke_width=4))
        readout = VGroup(VGroup(DecimalNumber(150, num_decimal_places=0, font_size=30, color=PROT_C), Tex(r"MeV", font_size=24)).arrange(RIGHT, buff=0.1),
                         VGroup(Tex(r"range", font_size=22, color=GREY_B), DecimalNumber(Rp, num_decimal_places=1, font_size=30), Tex(r"cm", font_size=24)).arrange(RIGHT, buff=0.1))
        readout[0][0].add_updater(lambda m: m.set_value(E.get_value()))
        readout[1][1].add_updater(lambda m: m.set_value(bk_range(E.get_value())))
        readout.arrange(DOWN, aligned_edge=LEFT, buff=0.15).next_to(leg, DOWN, buff=0.5).align_to(leg, LEFT)
        note = Tex(r"computed here: Bragg--Kleeman ranges; curve shapes illustrative", font_size=18, color=GREY_B).to_corner(DL, buff=0.15)
        stats = VGroup(Tex(r"X-rays: $\sim$\textbf{90\%} of radiotherapy", font_size=24, color=XRAY_C),
                       Tex(r"hadron therapy since 1946: $\sim$\textbf{260\,000} patients", font_size=24, color=PROT_C)).arrange(RIGHT, buff=0.8)
        stats.to_edge(DOWN, buff=0.45)
        with self.voiceover(text="First, why charged particles at all. <bookmark mark='x'/>X-ray photons deposit most of their dose near "
                                 "the <bookmark mark='ns'/>surface and fade with depth, so the tissue in front of a deep "
                                 "<bookmark mark='dt'/>tumour gets more dose than the tumour. <bookmark mark='p'/>Protons are different. They lose energy slowly at first, then faster as "
                                 "they slow, and dump most of it in a sharp <bookmark mark='bp'/>Bragg peak, with no dose <bookmark mark='nb'/>beyond it. <bookmark mark='c'/>"
                                 "Carbon ions have an even sharper peak, with a small <bookmark mark='tf'/>tail from fragments. <bookmark mark='e'/>Very high "
                                 "energy electrons give a broad, <bookmark mark='fp'/>flat profile that tolerates changes in tissue density. <bookmark mark='d'/>"
                                 "The depth of the peak is set by the energy: <bookmark mark='s'/>sweep a proton beam from sixty to two "
                                 "hundred and fifty MeV, and its peak moves from about three to almost forty centimetres. "
                                 "<bookmark mark='n'/>Yet about ninety percent of radiotherapy still uses X-rays, and only about two "
                                 "hundred and sixty thousand patients have ever had hadron therapy, because the machines that make "
                                 "these beams are large, specialised and expensive."):
            self.play(Write(title), Create(ax), FadeIn(axl), FadeIn(tum), FadeIn(tl), FadeIn(note), run_time=1.0)
            self.at("x", Create(cx), FadeIn(leg[0]), run_time=1.2)
            self.at("ns", Flash(ax.c2p(4, photon_dd(4)), color=XRAY_C, flash_radius=0.35))
            self.at("dt", Indicate(tum, color=BAD_C, scale_factor=1.05), Indicate(tl, color=BAD_C))
            self.at("p", Create(cp), FadeIn(leg[1]), run_time=1.5)
            self.at("bp", Flash(ax.c2p(Rp, 1.0), color=PROT_C, flash_radius=0.35))
            beyond = Rectangle(width=ax.c2p(42, 0)[0] - ax.c2p(Rp + 0.4, 0)[0], height=ax.c2p(0, 1.1)[1] - ax.c2p(0, 0)[1], fill_color=PROT_C,
                               fill_opacity=0.18, stroke_width=0).move_to(ax.c2p(Rp + 0.4, 0), aligned_edge=DL)
            self.at("nb", FadeIn(beyond), run_time=0.4)
            self.play(FadeOut(beyond), run_time=0.6)
            self.at("c", Create(cc), FadeIn(leg[2]), run_time=1.2)
            tail = Rectangle(width=ax.c2p(30, 0)[0] - ax.c2p(Rc + 0.5, 0)[0], height=0.5).move_to(ax.c2p((Rc + 30) / 2, 0.08))
            self.at("tf", Circumscribe(tail, color=CARB_C))
            self.at("e", Create(ce), FadeIn(leg[3]), run_time=1.2)
            self.at("fp", Indicate(ce, color=ELEC_C, scale_factor=1.0), Indicate(leg[3], color=ELEC_C))
            self.at("d", FadeOut(cx), FadeOut(cc), FadeOut(ce), FadeOut(cp), FadeIn(slider), FadeIn(readout))
            self.at("s", E.animate.set_value(60), run_time=1.5)
            self.play(E.animate.set_value(250), run_time=3.0)
            self.play(E.animate.set_value(150), run_time=1.0)
            self.at("n", FadeIn(stats[0]))
            self.play(FadeIn(stats[1]))
        self.wait(0.5)
        fade_all(self)


class Accelerators(Narrated):
    def construct(self):
        title = Tex(r"conventional accelerators, and the laser alternative", font_size=32).to_edge(UP, buff=0.35)
        # linac
        cav = VGroup(*[RoundedRectangle(corner_radius=0.08, width=0.45, height=0.5, fill_color=BLUE_L, fill_opacity=0.35, stroke_color=BLUE_L)
                       for _ in range(6)]).arrange(RIGHT, buff=0.18).move_to(LEFT * 4.3 + UP * 1.5)
        lin_l = Tex(r"linac", font_size=24).next_to(cav, DOWN, buff=0.15)
        # cyclotron: two dees and a spiral
        cc = LEFT * 0.4 + UP * 1.4
        dees = VGroup(Sector(radius=1.0, angle=PI, start_angle=PI / 2 + 0.05, fill_color=BLUE_L, fill_opacity=0.25, stroke_color=BLUE_L),
                      Sector(radius=1.0, angle=PI, start_angle=-PI / 2 + 0.05, fill_color=BLUE_L, fill_opacity=0.25, stroke_color=BLUE_L)).move_to(cc)
        spiral = ParametricFunction(lambda t: cc + 0.12 * t * np.array([np.cos(t), np.sin(t), 0]), t_range=[0, 7.5], color=PROT_C, stroke_width=2)
        cyc_l = Tex(r"cyclotron: most therapy protons", font_size=22).next_to(dees, DOWN, buff=0.15)
        # synchrotron
        sc = RIGHT * 3.9 + UP * 1.4
        sring = Circle(radius=1.0, color=GREY_B, stroke_width=5).move_to(sc)
        smag = VGroup(*[Rectangle(width=0.28, height=0.16, fill_color=BLUE_L, fill_opacity=0.9, stroke_width=0).move_to(sring.point_at_angle(a)).rotate(a + PI / 2)
                        for a in np.linspace(0, TAU, 10, endpoint=False)])
        syn_l = Tex(r"synchrotron: heavier ions", font_size=22).next_to(sring, DOWN, buff=0.15)
        bld = DashedVMobject(Rectangle(width=12.6, height=3.2, color=GREY_C)).move_to(UP * 1.2)
        bl = Tex(r"dedicated building $\cdot$ power $\cdot$ shielding $\cdot$ slow ion switching", font_size=22, color=GREY_B).next_to(bld, DOWN, buff=0.1)
        # laser side
        f_ = foil(0.06, 1.0).move_to(LEFT * 1.0 + DOWN * 2.2)
        ruler = VGroup(Line(f_.get_right() + DOWN * 0.7, f_.get_right() + DOWN * 0.7 + RIGHT * 1.6, color=WHITE),
                       Tex(r"\textbf{10\,$\mu$m}", font_size=24).next_to(f_.get_right() + DOWN * 0.7 + RIGHT * 0.8, DOWN, buff=0.08))
        field = VGroup(*[Arrow(f_.get_right() + UP * y, f_.get_right() + UP * y + RIGHT * 1.5, buff=0.05, color=YELLOW, stroke_width=3,
                               max_tip_length_to_length_ratio=0.12) for y in (-0.3, 0, 0.3)])
        fl = Tex(r"plasma field $\sim$\textbf{1 TV/m}", font_size=24, color=YELLOW).next_to(field, UP, buff=0.12)
        gain = Tex(r"$\Rightarrow$ \textbf{10 MeV} over 10\,$\mu$m (computed)", font_size=26).next_to(field, RIGHT, buff=0.4)
        eff = tile(VGroup(Circle(radius=0.25, color=LASER_C), Tex(r"$\%$", font_size=26, color=LASER_C)), r"wall-plug \textbf{0.1--1\%} + cooling", 4.0)
        eff.to_edge(DOWN, buff=0.25).shift(RIGHT * 3.2)
        # fields: E across each linac gap, B through the cyclotron dees (out of the page for an anticlockwise proton)
        gaps = VGroup(*[Arrow(cav[k].get_right() + LEFT * 0.04, cav[k + 1].get_left() + RIGHT * 0.04, buff=0, color=YELLOW, stroke_width=3,
                              max_tip_length_to_length_ratio=0.5) for k in range(5)])
        cyc_b = b_symbols(Square(1.3).move_to(cc), into=False, nx=3, ny=3)
        cyc_bl = Tex(r"$\mathbf{B}$", font_size=22, color=BLUE_L).next_to(dees, LEFT, buff=0.1)
        sdot = Dot(sring.point_at_angle(0), color=PROT_C, radius=0.07)
        with self.voiceover(text="Conventional machines push particles through radio frequency <bookmark mark='rf'/>cavities again and "
                                 "again. <bookmark mark='l'/>A linac lines the cavities up in a row; <bookmark mark='c'/>a cyclotron bends "
                                 "the particles into a spiral so they cross the same <bookmark mark='cg'/>gap many times, and makes most of "
                                 "today's therapy protons; <bookmark mark='s'/>a synchrotron ramps its <bookmark mark='sm'/>magnets around a "
                                 "fixed ring, and makes the heavier ions. <bookmark mark='b'/>Each needs a dedicated building, power and "
                                 "shielding, and switching between ion species is slow. <bookmark mark='f'/>A laser plasma accelerator "
                                 "replaces the cavities with the <bookmark mark='ef'/>electric field inside a plasma, of order a "
                                 "<bookmark mark='tv'/>teravolt per metre. <bookmark mark='g'/>At that field, ten micrometres is enough for "
                                 "ten MeV. <bookmark mark='e'/>The catch is efficiency: the titanium sapphire lasers that drive them turn only "
                                 "zero point one to one percent of their electrical power into light, and need heavy cooling."):
            self.play(Write(title), run_time=0.8)
            dot = Dot(cav.get_left() + LEFT * 0.2, color=PROT_C)
            self.at("rf", FadeIn(cav), FadeIn(dot))
            self.at("l", FadeIn(lin_l), LaggedStart(*[GrowArrow(g_) for g_ in gaps], lag_ratio=0.15), run_time=0.8)
            self.play(dot.animate.move_to(cav.get_right() + RIGHT * 0.2), LaggedStart(*[Indicate(g_, color=YELLOW, scale_factor=1.4) for g_ in gaps],
                                                                                     lag_ratio=0.2), run_time=1.2, rate_func=rate_functions.ease_in_quad)
            self.at("c", FadeIn(dees), FadeIn(cyc_b), FadeIn(cyc_bl), Create(spiral), FadeIn(cyc_l), run_time=1.5)
            self.at("cg", ShowPassingFlash(spiral.copy().set_stroke(YELLOW, 5), time_width=0.3), Indicate(cyc_b, color=BLUE_L), run_time=1.2)
            self.at("s", Create(sring), FadeIn(smag), FadeIn(syn_l), FadeIn(sdot))
            self.at("sm", MoveAlongPath(sdot, sring), LaggedStart(*[Indicate(m, color=BLUE_L, scale_factor=1.5) for m in smag],
                                                                               lag_ratio=0.1), run_time=1.5)
            self.at("b", Create(bld), FadeIn(bl))
            self.wait_until_bookmark("f")
            restore = spotlight(self, [title])
            self.play(FadeIn(f_))
            self.at("ef", LaggedStart(*[GrowArrow(a) for a in field], lag_ratio=0.2), FadeIn(fl))
            self.at("tv", Indicate(fl, color=YELLOW), Indicate(field, color=YELLOW, scale_factor=1.1))
            self.at("g", Create(ruler), FadeIn(gain))
            self.play(Indicate(ruler, color=WHITE), run_time=0.6)
            self.at("e", restore, FadeIn(eff))
        self.wait(0.5)
        fade_all(self)


class Overview(Narrated):
    def construct(self):
        title = Tex(r"one laser, three mechanisms", font_size=34).to_edge(UP, buff=0.35)
        pulse = pulse_curve(3.6, 1.0).move_to(LEFT * 4.2 + UP * 0.9)
        env = ParametricFunction(lambda t: np.array([t, np.exp(-(t / 0.9) ** 2), 0]), t_range=[-1.8, 1.8], color=GREY_B, stroke_width=1.5).move_to(pulse.get_center() + UP * 0.5)
        pl = VGroup(Tex(r"tens of fs -- ps", font_size=24), Tex(r"$>$\textbf{10$^{18}$} W/cm$^2$", font_size=26, color=LASER_C),
                    Tex(r"Ti:sapphire", font_size=22, color=GREY_B)).arrange(DOWN, buff=0.12).next_to(pulse, DOWN, buff=0.3)
        train = VGroup(*[Line(UP * 0, UP * 0.45, color=LASER_C, stroke_width=3).move_to(LEFT * 5.6 + RIGHT * 0.55 * k + DOWN * 2.3) for k in range(6)])
        tl = Tex(r"\textbf{1--10} shots per second", font_size=22).next_to(train, DOWN, buff=0.12)
        rows = VGroup()
        specs = [("gas", r"wakefield (LWFA)", r"electrons $\to$ VHEE", ELEC_C, 0),
                 (r"foil, 5--50\,$\mu$m", r"sheath (TNSA)", r"protons", PROT_C, 1),
                 (r"foil, nm--1.5\,$\mu$m", r"radiation pressure (RPA)", r"protons, carbon; $10^{21}$--$10^{23}$", CARB_C, 2)]
        for name, mech, out, col, k in specs:
            if k == 0:
                tgt = VGroup(*[Dot(np.array([x, y, 0]), radius=0.025, color=GREY_B) for x in np.linspace(-0.4, 0.4, 6) for y in np.linspace(-0.3, 0.3, 4)])
            else:
                tgt = foil(0.25 if k == 1 else 0.05, 0.8)
            arr = Arrow(LEFT * 0.9, LEFT * 0.45, buff=0, color=LASER_C, stroke_width=4)
            outp = Arrow(RIGHT * 0.45, RIGHT * 1.0, buff=0, color=col, stroke_width=4)
            g = VGroup(arr, tgt, outp, VGroup(Tex(mech, font_size=26, color=col), Tex(name + r" $\to$ " + out, font_size=20, color=GREY_A)).arrange(DOWN, aligned_edge=LEFT, buff=0.06).next_to(outp, RIGHT, buff=0.25))
            rows.add(g)
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.6).move_to(RIGHT * 2.2 + DOWN * 0.3)
        fit_frame(rows)
        with self.voiceover(text="All three mechanisms start the same way. <bookmark mark='p'/>A titanium sapphire laser fires pulses "
                                 "tens of femtoseconds to picoseconds long, focused above ten to the eighteen watts per square "
                                 "centimetre, <bookmark mark='r'/>repeating one to ten times a second. <bookmark mark='g'/>Fired into a "
                                 "gas, it drives a wakefield that accelerates electrons. <bookmark mark='t'/>Into a foil a few "
                                 "micrometres thick, it drives target normal sheath acceleration, mostly of protons. <bookmark mark='a'/>"
                                 "Into a foil just nanometres thick, at a thousand times the intensity, radiation pressure acceleration, "
                                 "which can push protons and carbon."):
            self.play(Write(title), run_time=0.8)
            self.at("p", Create(pulse), Create(env), FadeIn(pl), run_time=1.2)
            self.at("r", LaggedStart(*[FadeIn(t_, scale=0.5) for t_ in train], lag_ratio=0.3), FadeIn(tl), run_time=1.5)
            for k, m in enumerate("gta"):
                self.at(m, GrowArrow(rows[k][0]), FadeIn(rows[k][1]), GrowArrow(rows[k][2]), FadeIn(rows[k][3]))
        self.wait(0.5)
        fade_all(self)


class LWFA(Narrated):
    def construct(self):
        self.add(nav(0, None))
        title = Tex(r"laser wakefield acceleration", font_size=34).to_edge(UP, buff=0.35)
        Rb, cy = 0.95, -0.2
        xs, ys = np.linspace(-6.8, 6.8, 46), np.linspace(-1.7, 1.7, 13)
        grid = np.array([(x, y) for x in xs for y in ys])
        jit = np.random.default_rng(1).uniform(-0.07, 0.07, grid.shape)
        grid = grid + jit
        xL = ValueTracker(-8.0)

        def epos(x, y, xl):
            c = xl - Rb
            dx, dy = x - c, y
            r = np.hypot(dx, dy)
            R2 = Rb * 1.12
            if r < R2 and x < xl + 0.15:
                s = R2 / max(r, 1e-3)
                return c + dx * s, dy * s
            return x, y

        ions = VGroup(*[Dot(np.array([x, y + cy, 0]), radius=0.022, color=ION_C, fill_opacity=0.6) for x, y in grid])
        elec = always_redraw(lambda: VGroup(*[Dot(np.array([*(lambda p: (p[0], p[1] + cy))(epos(x, y, xL.get_value())), 0]), radius=0.035, color=ELEC_C)
                                            for x, y in grid]))
        pulse = always_redraw(lambda: VGroup(Ellipse(width=0.35, height=1.2, fill_color=LASER_C, fill_opacity=0.55, stroke_width=0),
                                             pulse_curve(0.6, 0.35, 4).rotate(0)).move_to(np.array([xL.get_value(), cy, 0])))
        # E points from the positive ion bubble outward to the electron sheath (+ to -); the force on an electron is the reverse
        fields = always_redraw(lambda: VGroup(*[Arrow(np.array([xL.get_value() - Rb + Rb * 0.25 * np.cos(a), cy + Rb * 0.25 * np.sin(a), 0]),
                                                      np.array([xL.get_value() - Rb + Rb * 0.8 * np.cos(a), cy + Rb * 0.8 * np.sin(a), 0]),
                                                      buff=0, color=YELLOW, stroke_width=2.5, max_tip_length_to_length_ratio=0.3)
                                                for a in np.linspace(0, TAU, 8, endpoint=False)]))
        e_lab = always_redraw(lambda: MathTex(r"\mathbf{E}", font_size=30, color=YELLOW).move_to(np.array([xL.get_value() - Rb, cy + Rb * 1.55, 0])))
        push = always_redraw(lambda: VGroup(Arrow(np.array([xL.get_value(), cy + 0.45, 0]), np.array([xL.get_value(), cy + 1.15, 0]), buff=0, color=LASER_C,
                                                  stroke_width=3, max_tip_length_to_length_ratio=0.3),
                                            Arrow(np.array([xL.get_value(), cy - 0.45, 0]), np.array([xL.get_value(), cy - 1.15, 0]), buff=0, color=LASER_C,
                                                  stroke_width=3, max_tip_length_to_length_ratio=0.3)))
        gain = ValueTracker(0.0)
        bunch = always_redraw(lambda: VGroup(*[Dot(np.array([xL.get_value() - 2 * Rb + 0.25 + 0.6 * gain.get_value() + dx, cy + dy, 0]), radius=0.06,
                                                   color=WHITE) for dx, dy in ((0, 0), (0.08, 0.07), (0.08, -0.07), (0.16, 0))]))
        elab = VGroup(Tex(r"energy", font_size=22, color=GREY_B), Rectangle(width=0.3, height=0.05, fill_color=WHITE, fill_opacity=1, stroke_width=0))
        ebar = always_redraw(lambda: Rectangle(width=0.3, height=0.05 + 1.6 * gain.get_value(), fill_color=WHITE, fill_opacity=0.9, stroke_width=0)
                             .move_to(np.array([6.3, -2.6, 0]), aligned_edge=DOWN))
        elab[0].move_to(np.array([6.3, -2.85, 0]))
        lab = VGroup(Tex(r"electrons", font_size=22, color=ELEC_C), Tex(r"ions", font_size=22, color=ION_C)).arrange(RIGHT, buff=0.5).to_corner(UR, buff=0.3).shift(DOWN * 0.6)
        pond = Tex(r"ponderomotive push", font_size=22, color=LASER_C)
        bub = Tex(r"bubble: ions only", font_size=22, color=ION_C)
        facts = VGroup(Tex(r"\textbf{20--40 fs} $<$ plasma wavelength", font_size=24),
                       Tex(r"record \textbf{7.8 GeV}; therapy \textbf{50--250 MeV}; 400 MeV $\to$ $>$40 cm", font_size=24)).arrange(DOWN, buff=0.12).to_edge(DOWN, buff=0.25)
        force = always_redraw(lambda: VGroup(Arrow(bunch.get_right() + RIGHT * 0.02, bunch.get_right() + RIGHT * 0.75, buff=0, color=WHITE, stroke_width=4,
                                                   max_tip_length_to_length_ratio=0.3),
                                             MathTex(r"\mathbf{F}", font_size=26).next_to(bunch.get_right() + RIGHT * 0.4, UP, buff=0.05)))
        with self.voiceover(text="Wakefield acceleration first. <bookmark mark='p'/>The plasma is a sea of light <bookmark mark='pe'/>electrons "
                                 "and heavy positive <bookmark mark='pi'/>ions. <bookmark mark='l'/>As the laser pulse passes, its "
                                 "<bookmark mark='pf'/>ponderomotive force shoves the electrons sideways, out of its path. "
                                 "<bookmark mark='b'/>Behind the pulse they leave a <bookmark mark='bb'/>bubble that holds only ions. "
                                 "<bookmark mark='f'/>That charge separation makes an enormous <bookmark mark='ee'/>electric field inside "
                                 "the bubble. <bookmark mark='i'/>An electron caught at the back is <bookmark mark='pu'/>pulled forward and "
                                 "toward the axis, <bookmark mark='a'/>surfs the bubble, and gains energy all the way. <bookmark mark='s'/>The "
                                 "pulses last twenty to forty femtoseconds, shorter than the plasma wavelength, so the wake is driven "
                                 "resonantly. <bookmark mark='r'/>Wakefields have produced seven point eight GeV electrons. Therapy needs "
                                 "fifty to two hundred and fifty MeV, and four hundred MeV beams can reach beyond forty centimetres."):
            self.play(Write(title), run_time=0.8)
            self.at("p", FadeIn(ions), FadeIn(elec), FadeIn(lab))
            self.at("pe", Indicate(lab[0], color=ELEC_C, scale_factor=1.4))
            self.at("pi", Indicate(lab[1], color=ION_C, scale_factor=1.4))
            self.wait_until_bookmark("l")
            self.add(pulse)
            pond.next_to(np.array([-1.5, cy + 1.95, 0]), UP, buff=0.05)
            self.play(xL.animate.set_value(-3.5), run_time=1.0, rate_func=linear)
            self.wait_until_bookmark("pf")
            self.add(push)
            self.play(xL.animate.set_value(-1.5), FadeIn(pond), run_time=1.5, rate_func=linear)
            self.at("b", xL.animate.set_value(0.5), FadeOut(pond), FadeOut(push), run_time=1.5, rate_func=linear)
            bub.next_to(np.array([0.5 - Rb, cy - 1.9, 0]), DOWN, buff=0.0)
            ring_ = Circle(radius=Rb * 1.12, color=ION_C, stroke_width=4).move_to(np.array([0.5 - Rb, cy, 0]))
            self.at("bb", FadeIn(bub), Create(ring_), run_time=0.6)
            self.play(FadeOut(ring_), run_time=0.3)
            self.at("f", FadeOut(bub))
            self.at("ee", FadeIn(fields), FadeIn(e_lab))
            self.play(Indicate(e_lab, color=YELLOW, scale_factor=1.5))
            self.at("i", FadeIn(bunch, scale=2), FadeIn(elab[0]), FadeIn(ebar))
            self.at("pu", FadeIn(force), Flash(bunch.get_center(), color=WHITE, flash_radius=0.3))
            self.at("a", xL.animate.set_value(5.6), gain.animate.set_value(1.0), run_time=3.0, rate_func=linear)
            self.at("s", FadeIn(facts[0]))
            self.at("r", FadeIn(facts[1]))
        self.wait(0.5)
        fade_all(self)


class TNSA(Narrated):
    def construct(self):
        self.add(nav(1, None))
        title = Tex(r"target normal sheath acceleration", font_size=34).to_edge(UP, buff=0.35)
        cy = -0.1
        f_ = foil(0.5, 3.6).move_to(LEFT * 2.2 + UP * cy)
        fl = Tex(r"thin foil, \textbf{5--50\,$\mu$m}", font_size=22).next_to(f_, DOWN, buff=0.15)
        h_layer = Rectangle(width=0.07, height=3.6, fill_color=H_C, fill_opacity=0.9, stroke_width=0).next_to(f_, RIGHT, buff=0)
        hl = Tex(r"water, hydrocarbons", font_size=20, color=H_C).next_to(h_layer, UP, buff=0.1)
        laser = Arrow(LEFT * 6.5 + UP * cy, f_.get_left(), buff=0.02, color=LASER_C, stroke_width=8)
        pre = Ellipse(width=0.6, height=1.2, fill_color=LASER_C, fill_opacity=0.25, stroke_width=0).move_to(f_.get_left() + LEFT * 0.2)
        rng = np.random.default_rng(3)
        n_e = 36
        start = [f_.get_left() + RIGHT * 0.05 + UP * rng.uniform(-0.5, 0.5) for _ in range(n_e)]
        end = [h_layer.get_right() + RIGHT * rng.uniform(0.15, 0.6) + UP * rng.uniform(-1.6, 1.6) for _ in range(n_e)]
        hot = VGroup(*[Dot(p, radius=0.04, color=ELEC_C) for p in start])
        sheath_l = Tex(r"electron sheath", font_size=22, color=ELEC_C).next_to(h_layer, RIGHT, buff=1.5).shift(UP * 1.95)
        field = VGroup(*[Arrow(h_layer.get_right() + UP * y, h_layer.get_right() + UP * y + RIGHT * 0.65, buff=0.02, color=YELLOW, stroke_width=3,
                               max_tip_length_to_length_ratio=0.25) for y in np.linspace(-1.4, 1.4, 6)])
        fdl = Tex(r"$\sim$TV/m", font_size=24, color=YELLOW).next_to(field, RIGHT, buff=0.15)
        n_p = 70
        y0 = rng.uniform(-1.5, 1.5, n_p)
        v = rng.uniform(0.25, 1.0, n_p) ** 0.7                        # many slow, few fast
        th = rng.uniform(-1, 1, n_p) * (0.75 - 0.6 * v)               # fast protons in a narrow cone, slow ones wide
        t = ValueTracker(0.0)
        p0 = h_layer.get_right()

        def prot():
            return VGroup(*[Dot(np.array([p0[0] + 0.05 + 6.0 * vi * t.get_value() * np.cos(a), cy + yi * (1 - 0.6 * t.get_value()) + 6.0 * vi * t.get_value() * np.sin(a), 0]),
                                radius=0.04, color=PROT_C) for yi, vi, a in zip(y0, v, th)])
        protons = always_redraw(prot)
        cone_f = Polygon(p0 + RIGHT * 0.1, p0 + RIGHT * 5.2 + UP * 5 * np.tan(0.15), p0 + RIGHT * 5.2 + DOWN * 5 * np.tan(0.15), color=PROT_C, fill_opacity=0.12, stroke_width=1.5)
        cone_s = Polygon(p0 + RIGHT * 0.1, p0 + RIGHT * 3.2 + UP * 3.2 * np.tan(0.55), p0 + RIGHT * 3.2 + DOWN * 3.2 * np.tan(0.55), color=GREY_B, fill_opacity=0.06, stroke_width=1.5)
        cl = VGroup(Tex(r"fast: narrow", font_size=22, color=PROT_C).next_to(cone_f, RIGHT, buff=0.05),
                    Tex(r"slow: up to \textbf{200--300 mrad}", font_size=22, color=GREY_A).move_to(p0 + RIGHT * 2.6 + DOWN * 2.3))
        facts = VGroup(Tex(r"up to \textbf{6$\times$10$^{13}$} protons/pulse", font_size=24),
                       Tex(r"$E_{\max} \propto \sqrt{I}$", font_size=28, color=BAD_C)).arrange(RIGHT, buff=0.8).to_edge(DOWN, buff=0.25)
        # charges and the field: the foil's rear is left positive, the sheath beyond it negative; E points from + to -
        plus = VGroup(*[MathTex(r"+", font_size=26, color=BAD_C).move_to(f_.get_right() + LEFT * 0.12 + UP * y) for y in np.linspace(-1.4, 1.4, 6)])
        minus = VGroup(*[MathTex(r"-", font_size=30, color=ELEC_C).move_to(h_layer.get_right() + RIGHT * 0.95 + UP * y) for y in np.linspace(-1.2, 1.2, 4)])
        e_lab = MathTex(r"\mathbf{E}", font_size=32, color=YELLOW).next_to(field, UP, buff=0.12)
        launch = VGroup(Dot(p0 + RIGHT * 0.15, color=PROT_C, radius=0.07),
                        Arrow(p0 + RIGHT * 0.2, p0 + RIGHT * 0.95, buff=0, color=YELLOW, stroke_width=5, max_tip_length_to_length_ratio=0.3),
                        MathTex(r"\mathbf{F} = e\mathbf{E}", font_size=24, color=YELLOW).next_to(p0 + RIGHT * 0.6, DOWN, buff=0.12))
        with self.voiceover(text="For protons, the workhorse is target normal sheath acceleration. <bookmark mark='f'/>The <bookmark mark='lh'/>"
                                 "laser hits a thin <bookmark mark='tf'/>foil five to fifty micrometres thick. <bookmark mark='h'/>Its leading "
                                 "edge makes a hot <bookmark mark='hp'/>plasma on the front, and the main pulse drives those "
                                 "<bookmark mark='de'/>electrons to nearly the speed of light, <bookmark mark='t'/>straight through the foil "
                                 "<bookmark mark='s'/>and out of the back, where they hang as a thin negative <bookmark mark='ns'/>sheath. "
                                 "<bookmark mark='e'/>The <bookmark mark='fe'/>field between the sheath and the foil is of order "
                                 "<bookmark mark='tv'/>teravolts per metre. <bookmark mark='c'/>It does not pull ions out of the foil itself, "
                                 "but out of a thin layer of moisture and hydrocarbons on the back surface, which is why the beam is mostly "
                                 "protons, <bookmark mark='a'/>launched normal to the surface. <bookmark mark='d'/>The fastest protons leave in "
                                 "a narrow <bookmark mark='nc'/>cone; the slow ones <bookmark mark='sw'/>spread wide, up to two to three "
                                 "hundred milliradians. <bookmark mark='m'/>TNSA has given up to six times ten to the thirteen protons per "
                                 "pulse, <bookmark mark='q'/>but its maximum energy grows only with the square root of the laser intensity."):
            self.play(Write(title), run_time=0.8)
            self.at("f", FadeIn(f_), FadeIn(fl))
            self.at("lh", GrowArrow(laser))
            self.at("tf", Indicate(f_, color=WHITE, scale_factor=1.05), Indicate(fl))
            self.at("h", FadeIn(pre))
            self.at("hp", Flash(pre.get_center(), color=LASER_C, flash_radius=0.6))
            self.at("de", FadeIn(hot, scale=1.5))
            self.at("t", *[d.animate.move_to(h_layer.get_center() + UP * (p_[1] - h_layer.get_center()[1])) for d, p_ in zip(hot, start)], run_time=0.8)
            self.at("s", *[d.animate.move_to(e) for d, e in zip(hot, end)], FadeIn(sheath_l), run_time=1.0)
            self.at("ns", FadeIn(minus), FadeIn(plus), Circumscribe(VGroup(*hot), color=ELEC_C))
            self.wait_until_bookmark("fe")
            restore = spotlight(self, [title, f_, plus, minus, *hot])
            self.play(LaggedStart(*[GrowArrow(a) for a in field], lag_ratio=0.1), FadeIn(e_lab), run_time=1.0)
            self.at("tv", FadeIn(fdl), Indicate(field, color=YELLOW, scale_factor=1.15), Indicate(e_lab, color=YELLOW, scale_factor=1.5))
            self.at("c", restore, FadeIn(h_layer), FadeIn(hl))
            self.play(Indicate(h_layer, color=H_C, scale_factor=1.05), run_time=0.6)
            self.wait_until_bookmark("a")
            self.play(FadeIn(launch[0], scale=2), GrowArrow(launch[1]), FadeIn(launch[2]), run_time=0.6)
            self.add(protons)
            self.play(t.animate.set_value(1.0), FadeOut(field), FadeOut(fdl), FadeOut(e_lab), FadeOut(launch), run_time=3.0, rate_func=linear)
            self.at("d", FadeIn(cone_f), FadeIn(cone_s))
            self.at("nc", Indicate(cone_f, color=PROT_C, scale_factor=1.05), FadeIn(cl[0]))
            self.at("sw", Indicate(cone_s, color=WHITE, scale_factor=1.05), FadeIn(cl[1]))
            self.at("m", FadeIn(facts[0]))
            self.play(Indicate(facts[0]), run_time=0.6)
            self.at("q", FadeIn(facts[1]))
            self.play(Indicate(facts[1], color=BAD_C), run_time=0.6)
        self.wait(0.5)
        fade_all(self)


class RPA(Narrated):
    def construct(self):
        self.add(nav(2, None))
        title = Tex(r"radiation pressure acceleration", font_size=34).to_edge(UP, buff=0.35)
        req = Tex(r"$I \approx$ \textbf{10$^{21}$--10$^{23}$} W/cm$^2$", font_size=28, color=LASER_C).next_to(title, DOWN, buff=0.2)
        t = ValueTracker(0.0)
        # hole boring (left): a front moving in at constant speed, ions piled ahead of it
        hb_c = LEFT * 3.6 + UP * 0.4
        thick = foil(2.0, 2.2).move_to(hb_c)
        hb_l = Tex(r"hole boring: up to \textbf{1.5\,$\mu$m}", font_size=24).next_to(thick, DOWN, buff=0.2)
        # electrons are pushed ahead (-), ions lag behind (+): E points forward from the ion layer to the electron layer
        def layers(xi, h=2.2, gap=0.3):
            xe = xi + gap
            return VGroup(Rectangle(width=0.05, height=h, fill_color=ELEC_C, fill_opacity=1, stroke_width=0).move_to(np.array([xe, 0, 0])),
                          Rectangle(width=0.07, height=h, fill_color=ION_C, fill_opacity=1, stroke_width=0).move_to(np.array([xi, 0, 0])),
                          VGroup(*[Arrow(np.array([xi + 0.04, y, 0]), np.array([xe - 0.03, y, 0]), buff=0, color=YELLOW, stroke_width=3,
                                         max_tip_length_to_length_ratio=0.45) for y in (-0.6, 0.0, 0.6)]))

        front = always_redraw(lambda: VGroup(
            layers(thick.get_left()[0] + 0.12 + 1.5 * t.get_value()).shift(UP * hb_c[1]),
            Rectangle(width=0.1 + 1.5 * t.get_value(), height=2.2, fill_color=BLACK, fill_opacity=0.65, stroke_width=0).move_to(thick.get_left(), aligned_edge=LEFT)))
        las1 = always_redraw(lambda: Arrow(thick.get_left() + LEFT * 1.3, thick.get_left() + RIGHT * (0.05 + 1.6 * t.get_value()), buff=0, color=LASER_C, stroke_width=7))
        # light sail (right): the whole foil accelerates
        ls_c = RIGHT * 2.2 + UP * 0.4
        x0 = ls_c[0] - 0.6
        sail = always_redraw(lambda: layers(x0 + 3.2 * t.get_value() ** 2, gap=0.22).shift(UP * ls_c[1]))
        e_lab = MathTex(r"\mathbf{E}", font_size=28, color=YELLOW)
        rp_l = Tex(r"light pressure", font_size=22, color=LASER_C).next_to(thick.get_left() + LEFT * 0.7, UP, buff=0.25)
        las2 = always_redraw(lambda: Arrow(np.array([x0 - 1.4, ls_c[1], 0]), np.array([x0 + 3.2 * t.get_value() ** 2 - 0.05, ls_c[1], 0]), buff=0, color=LASER_C, stroke_width=7))
        ls_l = Tex(r"light sail: \textbf{5--50\,nm}, thinner than $\lambda$", font_size=24).move_to(np.array([ls_c[0] + 0.8, hb_l.get_y(), 0]))
        lab = VGroup(Tex(r"electrons", font_size=20, color=ELEC_C), Tex(r"ions", font_size=20, color=ION_C)).arrange(RIGHT, buff=0.4).to_corner(UR, buff=0.3).shift(DOWN * 1.0)
        trade = Tex(r"higher energy, lower flux", font_size=22, color=GREY_A).next_to(ls_l, DOWN, buff=0.1)
        circ = Tex(r"circular polarisation: motion, not heat", font_size=22, color=LASER_C).to_edge(DOWN, buff=1.35)
        # payoffs: a spectrum and the scaling law
        ax = Axes(x_range=[0, 4, 1], y_range=[0, 4, 1], x_length=3.0, y_length=1.9, tips=False, axis_config={"color": GREY_B, "include_ticks": False})
        ax.to_corner(DR, buff=0.45).shift(UP * 0.1)
        sq = ax.plot(lambda i: np.sqrt(i), x_range=[0, 4], color=PROT_C, stroke_width=4)
        li = ax.plot(lambda i: i, x_range=[0, 4], color=CARB_C, stroke_width=4)
        axl = VGroup(Tex(r"intensity", font_size=18, color=GREY_B).next_to(ax, DOWN, buff=0.08), Tex(r"$E_{\max}$", font_size=20, color=GREY_B).next_to(ax, LEFT, buff=0.08),
                     Tex(r"RPA $\propto I$", font_size=20, color=CARB_C).next_to(ax.c2p(4, 4), LEFT, buff=0.1),
                     Tex(r"TNSA $\propto \sqrt{I}$", font_size=20, color=PROT_C).next_to(ax.c2p(4, 2), DOWN, buff=0.1),
                     Tex(r"scaling only", font_size=16, color=GREY_B).next_to(ax, UP, buff=0.05))
        bunch = VGroup(Tex(r"ions leave as a \textbf{bunch}: far more monoenergetic", font_size=24)).to_edge(DOWN, buff=0.35).shift(LEFT * 2.0)
        with self.voiceover(text="Radiation pressure acceleration needs a thousand times more <bookmark mark='in'/>intensity, ten to the "
                                 "twenty one to ten to the twenty three watts per square centimetre. <bookmark mark='p'/>Now the "
                                 "<bookmark mark='pl'/>pressure of the light itself does the work. <bookmark mark='e'/>The pulse shoves the "
                                 "<bookmark mark='se'/>electrons forward, <bookmark mark='i'/>the charge separation drags the "
                                 "<bookmark mark='di'/>ions after them, and the two layers move <bookmark mark='mo'/>as one. <bookmark mark='h'/>"
                                 "In a target up to about one and a half micrometres thick, the laser bores a hole: a <bookmark mark='fm'/>front "
                                 "marches into the target and pushes ions ahead of it, like a piston. <bookmark mark='l'/>In a target thinner "
                                 "than the laser wavelength, five to fifty nanometres, the whole foil flies off as a <bookmark mark='ls'/>light "
                                 "sail, reaching higher energies at lower flux. <bookmark mark='c'/>Circularly polarised light helps, turning "
                                 "the pulse energy into motion rather than heat. <bookmark mark='s'/>Two payoffs: the ions leave as a "
                                 "<bookmark mark='bu'/>bunch, so they are far more monoenergetic, <bookmark mark='g'/>and their energy grows "
                                 "<bookmark mark='ln'/>linearly with intensity, against the <bookmark mark='sr'/>square root for TNSA."):
            self.play(Write(title), FadeIn(req), run_time=1.0)
            self.at("in", Indicate(req, color=LASER_C, scale_factor=1.15))
            self.at("p", FadeIn(thick), FadeIn(hb_l), FadeIn(lab))
            self.wait_until_bookmark("pl")
            self.add(front, las1)
            self.play(FadeIn(rp_l), Indicate(las1, color=LASER_C, scale_factor=1.1), run_time=0.6)
            self.at("se", Indicate(lab[0], color=ELEC_C, scale_factor=1.4), t.animate.set_value(0.08), run_time=0.8)
            e_lab.next_to(front[0][2], UP, buff=0.15)
            self.at("di", Indicate(lab[1], color=ION_C, scale_factor=1.4), FadeIn(e_lab))
            self.play(Indicate(e_lab, color=YELLOW, scale_factor=1.5), run_time=0.5)
            self.at("mo", t.animate.set_value(0.2), FadeOut(e_lab), run_time=0.8)
            self.at("h", t.animate.set_value(0.5), run_time=1.0, rate_func=linear)
            self.at("fm", t.animate.set_value(1.0), Indicate(hb_l), run_time=2.0, rate_func=linear)
            self.wait_until_bookmark("l")
            t.set_value(0.0)
            self.remove(front, las1)
            self.add(thick.copy().set_opacity(0.3), sail, las2)
            self.play(FadeOut(rp_l), FadeIn(ls_l), run_time=0.4)
            self.at("ls", t.animate.set_value(1.0), run_time=2.5, rate_func=rate_functions.ease_in_quad)
            self.play(FadeIn(trade))
            self.at("c", FadeIn(circ), Indicate(las2, color=LASER_C, scale_factor=1.1))
            self.at("s", FadeIn(bunch))
            self.at("bu", Indicate(bunch, color=YELLOW, scale_factor=1.05))
            self.at("g", Create(ax), FadeIn(axl[:2]), FadeIn(axl[4]), run_time=0.8)
            self.at("ln", Create(li), FadeIn(axl[2]), run_time=0.8)
            self.at("sr", Create(sq), FadeIn(axl[3]), run_time=0.8)
        self.wait(0.5)
        fade_all(self)


class BeamTime(Narrated):
    def construct(self):
        self.add(nav("all", "beams"))
        title = Tex(r"the beams: short, intense, divergent, mixed", font_size=32).to_edge(UP, buff=0.35)
        ax, labs = log_axis(-15, -8, 6.0, {-15: "1 fs", -12: "1 ps", -9: "1 ns"}, y=1.6)
        ax.shift(LEFT * 2.6)
        labs.shift(LEFT * 2.6)
        rng_bar = lambda a, b, y, col: Rectangle(width=ax.n2p(b)[0] - ax.n2p(a)[0], height=0.32, fill_color=col, fill_opacity=0.85, stroke_width=0).move_to(np.array([(ax.n2p(a)[0] + ax.n2p(b)[0]) / 2, y, 0]))
        b_las = rng_bar(-14, -12, 2.2, LASER_C)
        b_syn = rng_bar(-10, -8.5, 2.65, BLUE_L)
        bl = VGroup(Tex(r"laser-driven: tens of fs -- ps", font_size=20, color=LASER_C).next_to(b_las, RIGHT, buff=0.1),
                    Tex(r"synchrotron: 100s of ps -- ns", font_size=20, color=BLUE_L).next_to(b_syn, LEFT, buff=0.1))
        cur = VGroup(tile(VGroup(Tex(r"$\uparrow$", font_size=40, color=LASER_C)), r"peak current: \textbf{kA} vs mA", 3.6)).move_to(RIGHT * 4.3 + UP * 1.9)
        # divergence cones, full angle to scale
        o = LEFT * 5.6 + DOWN * 1.2
        L = 4.2
        cones = VGroup()
        specs = [(0.3, PROT_C, r"TNSA, slow: \textbf{200--300 mrad}"), (0.05, CARB_C, r"RPA: $\sim$\textbf{50 mrad}"),
                 (0.005, ELEC_C, r"LWFA: \textbf{1--5 mrad}"), (0.0, GREY_A, r"conventional: $\mu$rad")]
        for k, (ang, col, lab) in enumerate(specs):
            base = o + DOWN * 0.0 + UP * (0.0 - 0.0)
            yy = o + UP * (0.55 - 0.62 * k)
            if ang > 0:
                c_ = Polygon(yy, yy + RIGHT * L + UP * L * np.tan(ang / 2), yy + RIGHT * L + DOWN * L * np.tan(ang / 2), color=col, fill_opacity=0.35, stroke_width=1)
            else:
                c_ = Line(yy, yy + RIGHT * L, color=col, stroke_width=2)
            cones.add(VGroup(c_, Tex(lab, font_size=20, color=col).next_to(yy + RIGHT * L, RIGHT, buff=0.2)))
        cones[0][1].shift(UP * 0.25)
        cl = Tex(r"beam spread, full angle to scale", font_size=20, color=GREY_B).next_to(o + UP * 0.55, UP, buff=0.45).align_to(cones, LEFT)
        mix = VGroup(*[Dot(radius=0.07, color=c) for c in (PROT_C, PROT_C, CARB_C, PROT_C, ION_C, CARB_C, PROT_C)]).arrange(RIGHT, buff=0.12)
        mixl = VGroup(mix, Tex(r"several species per shot", font_size=22)).arrange(RIGHT, buff=0.25).to_corner(DR, buff=0.5)
        with self.voiceover(text="How do these beams compare with a synchrotron's? <bookmark mark='t'/>In time, a laser driven bunch "
                                 "lasts femtoseconds to picoseconds; <bookmark mark='y'/>synchrotron bunches last hundreds of "
                                 "picoseconds to nanoseconds. <bookmark mark='k'/>So the peak current reaches kiloamperes, against "
                                 "milliamperes. <bookmark mark='d'/>In angle, slow TNSA protons spread over two to three hundred "
                                 "milliradians, <bookmark mark='r'/>radiation pressure ions about fifty, <bookmark mark='w'/>wakefield "
                                 "electrons one to five, <bookmark mark='c'/>and a conventional beam only microradians. <bookmark mark='m'/>"
                                 "And every shot carries a broad spread of energies and several ion species at once, which a "
                                 "synchrotron never does."):
            self.play(Write(title), Create(ax), FadeIn(labs), run_time=1.0)
            self.at("t", GrowFromEdge(b_las, LEFT), FadeIn(bl[0]))
            self.at("y", GrowFromEdge(b_syn, LEFT), FadeIn(bl[1]))
            self.at("k", FadeIn(cur))
            self.at("d", FadeIn(cl), FadeIn(cones[0]))
            self.at("r", FadeIn(cones[1]))
            self.at("w", FadeIn(cones[2]))
            self.at("c", FadeIn(cones[3]))
            self.at("m", LaggedStart(*[FadeIn(d, scale=2) for d in mix], lag_ratio=0.1), FadeIn(mixl[1]))
        self.wait(0.5)
        fade_all(self)


class BeamYield(Narrated):
    def construct(self):
        self.add(nav("all", "beams"))
        title = Tex(r"a catch: what is actually usable", font_size=34).to_edge(UP, buff=0.35)
        ax, labs = log_axis(6, 14, 8.0, {6: "$10^6$", 9: "$10^9$", 12: "$10^{12}$", 14: "$10^{14}$"}, y=-1.7)
        ax.shift(RIGHT * 0.8)
        labs.shift(RIGHT * 0.8)
        left = ax.n2p(6)[0]
        shot = Rectangle(width=ax.n2p(13)[0] - left, height=0.55, fill_color=PROT_C, fill_opacity=0.85, stroke_width=0).move_to(np.array([left, 0.8, 0]), aligned_edge=LEFT)
        shot_r = Rectangle(width=ax.n2p(13)[0] - ax.n2p(12)[0], height=0.55, fill_color=PROT_C, fill_opacity=0.35, stroke_width=0).move_to(np.array([ax.n2p(12)[0], 0.8, 0]), aligned_edge=LEFT)
        win = Rectangle(width=ax.n2p(9)[0] - left, height=0.55, fill_color=GOOD_C, fill_opacity=0.85, stroke_width=0).move_to(np.array([left, 0.0, 0]), aligned_edge=LEFT)
        ll = VGroup(Tex(r"protons per shot, all energies", font_size=22).next_to(shot, UP, buff=0.08).align_to(shot, LEFT),
                    Tex(r"within 1 MeV of the 85 MeV cut-off", font_size=22, color=GOOD_C).next_to(win, RIGHT, buff=0.2))
        gap = BraceBetweenPoints(np.array([ax.n2p(9)[0], -0.35, 0]), np.array([ax.n2p(12)[0], -0.35, 0]), DOWN, color=BAD_C)
        gl = Tex(r"$\sim$\textbf{1000$\times$} fewer", font_size=24, color=BAD_C).next_to(gap, DOWN, buff=0.05)
        rate = VGroup(Tex(r"$\times$ \textbf{$\sim$1} shot/s (petawatt)", font_size=26), Tex(r"$\Rightarrow$ average current: \textbf{nA}", font_size=28),
                      Tex(r"comparable with clinical beams, not far above", font_size=24, color=GREY_A)).arrange(DOWN, buff=0.15).to_edge(DOWN, buff=0.35)
        with self.voiceover(text="Those numbers hide a catch. <bookmark mark='w'/>One shot may carry ten to the twelve to ten to the "
                                 "thirteen protons, <bookmark mark='n'/>but in one study only about ten to the nine landed within one MeV "
                                 "of the eighty five MeV cut-off, <bookmark mark='g'/>roughly a thousand times fewer. <bookmark mark='a'/>"
                                 "And a petawatt laser fires about once a second, so the average current is nanoamperes: comparable "
                                 "with the beams clinics already use, not orders of magnitude above them."):
            self.play(Write(title), Create(ax), FadeIn(labs), run_time=1.0)
            self.at("w", GrowFromEdge(shot, LEFT), FadeIn(shot_r), FadeIn(ll[0]))
            self.at("n", GrowFromEdge(win, LEFT), FadeIn(ll[1]))
            self.at("g", GrowFromCenter(gap), FadeIn(gl))
            self.at("a", LaggedStart(*[FadeIn(r) for r in rate], lag_ratio=0.4), run_time=1.5)
        self.wait(0.5)
        fade_all(self)


class UHDR(Narrated):
    def construct(self):
        self.add(nav("all", "dose rate"))
        title = Tex(r"ultra-high dose rate and FLASH", font_size=34).to_edge(UP, buff=0.35)
        # oxygen cartoon: a normal cell beside a vessel, a hypoxic tumour cell
        cn = Circle(radius=0.7, color=GOOD_C, fill_opacity=0.08).move_to(LEFT * 4.4 + UP * 1.75)
        ct = Circle(radius=0.7, color=BAD_C, fill_opacity=0.08).move_to(LEFT * 1.4 + UP * 1.75)
        vessel = Rectangle(width=0.25, height=2.0, fill_color=BAD_C, fill_opacity=0.6, stroke_width=0).next_to(cn, LEFT, buff=0.1)
        rng = np.random.default_rng(2)
        o2n = VGroup(*[Dot(cn.get_center() + 0.7 * np.array([*rng.uniform(-0.8, 0.8, 2), 0]), radius=0.05, color=BLUE_L) for _ in range(18)])
        o2t = VGroup(*[Dot(ct.get_center() + 0.7 * np.array([*rng.uniform(-0.8, 0.8, 2), 0]), radius=0.05, color=BLUE_L) for _ in range(3)])
        cl = VGroup(Tex(r"normal: O$_2$ resupplied", font_size=20, color=GOOD_C).next_to(cn, DOWN, buff=0.1),
                    Tex(r"tumour: hypoxic, resistant", font_size=20, color=BAD_C).next_to(ct, DOWN, buff=0.1))
        flash = Rectangle(width=4.6, height=2.2, fill_color=WHITE, fill_opacity=0.0, stroke_width=0).move_to(LEFT * 2.9 + UP * 1.75)
        res = Tex(r"normal tissue briefly hypoxic $\Rightarrow$ spared", font_size=22, color=GOOD_C).next_to(VGroup(cn, ct), RIGHT, buff=0.4)
        ax, labs = log_axis(-2, 14, 11.0, {-2: "0.01", 0: "1", 2: "100", 4: "$10^4$", 7: "$10^7$", 10: "$10^{10}$", 13: "$10^{13}$"}, y=-2.4)
        axl = Tex(r"dose rate (Gy/s)", font_size=20, color=GREY_B).next_to(ax, RIGHT, buff=0.1).shift(LEFT * 0.4 + DOWN * 0.4)
        fl = np.log10(40)
        fline = DashedLine(ax.n2p(fl) + UP * 1.6, ax.n2p(fl) + DOWN * 0.1, color=YELLOW)
        fll = Tex(r"FLASH $>$\textbf{40} Gy/s", font_size=20, color=YELLOW).next_to(fline, UP, buff=0.05)
        peaks = [(7, r"protons, 1st", PROT_C), (np.log10(1e9), r"protons", PROT_C), (np.log10(2e9), r"carbon, 400 ps", CARB_C),
                 (np.log10(1.6e10), r"e$^-$", ELEC_C), (13, r"e$^-$", ELEC_C)]
        avgs = [(np.log10(0.2), r"protons, 1st", PROT_C), (np.log10(1.1), r"e$^-$, kHz", ELEC_C), (np.log10(0.03), r"mouse, protons", PROT_C)]
        pk = VGroup(*[VGroup(Dot(ax.n2p(e) + UP * 1.05, color=c, radius=0.08), Tex(t, font_size=16, color=c).next_to(ax.n2p(e) + UP * 1.05, UP, buff=0.1 + 0.18 * (k % 2)))
                      for k, (e, t, c) in enumerate(peaks)])
        av = VGroup(*[VGroup(Square(0.14, color=c, fill_opacity=1).move_to(ax.n2p(e) + UP * 0.45), Tex(t, font_size=16, color=c).next_to(ax.n2p(e) + UP * 0.45, UP, buff=0.08 + 0.2 * k))
                      for k, (e, t, c) in enumerate(avgs)])
        key = VGroup(VGroup(Dot(radius=0.07, color=WHITE), Tex(r"peak", font_size=18)).arrange(RIGHT, buff=0.1),
                     VGroup(Square(0.12, color=WHITE, fill_opacity=1), Tex(r"average", font_size=18)).arrange(RIGHT, buff=0.1)).arrange(RIGHT, buff=0.4).next_to(ax, UP, buff=1.6).align_to(ax, RIGHT)
        with self.voiceover(text="Why care about such short pulses? Because of FLASH. <bookmark mark='f'/>Above about forty grays per "
                                 "second, irradiated normal tissue appears to be spared. <bookmark mark='o'/>The leading explanation: the "
                                 "dose arrives so fast that it uses up the <bookmark mark='ox'/>oxygen in normal cells before the <bookmark mark='bl'/>blood can resupply it, "
                                 "<bookmark mark='h'/>so for a moment they behave like hypoxic <bookmark mark='ht'/>tumour cells, which resist radiation. "
                                 "<bookmark mark='p'/>Laser sources reach extreme peak dose rates: <bookmark mark='p1'/>ten to the seven grays per second in "
                                 "an early proton study, <bookmark mark='p2'/>ten to the nine in others, <bookmark mark='p3'/>two times ten to the nine for a single four hundred "
                                 "picosecond carbon pulse, and up to <bookmark mark='p4'/>ten to the thirteen for electrons. <bookmark mark='a'/>Their "
                                 "average dose rates are another matter: <bookmark mark='a1'/>zero point two grays per second in that early proton study, "
                                 "<bookmark mark='a2'/>about one for a kilohertz electron source, and <bookmark mark='a3'/>one to two grays per minute in the first mouse study. "
                                 "<bookmark mark='q'/>The review stresses that relying on FLASH will need careful control of exactly "
                                 "this pulse structure."):
            self.play(Write(title), Create(ax), FadeIn(labs), FadeIn(axl), run_time=1.0)
            self.at("f", Create(fline), FadeIn(fll))
            self.at("o", FadeIn(cn), FadeIn(ct), FadeIn(vessel), FadeIn(o2n), FadeIn(o2t), FadeIn(cl))
            self.at("ox", Indicate(o2n, color=BLUE_L, scale_factor=1.3))
            self.play(flash.animate.set_fill(opacity=0.35), run_time=0.15)
            self.play(flash.animate.set_fill(opacity=0.0), *[FadeOut(d, scale=0.3) for d in o2n[:15]], run_time=0.8)
            self.at("bl", Indicate(vessel, color=BAD_C, scale_factor=1.15))
            self.at("h", FadeIn(res), Indicate(cn, color=GOOD_C))
            self.at("ht", Indicate(ct, color=BAD_C), Indicate(cl[1], color=BAD_C))
            self.at("p", FadeIn(key), Indicate(fline, color=YELLOW, scale_factor=1.0))
            for m, idx in (("p1", [0]), ("p2", [1]), ("p3", [2]), ("p4", [3, 4])):
                self.at(m, *[FadeIn(pk[i], scale=1.8) for i in idx], *[Flash(pk[i][0].get_center(), color=WHITE, flash_radius=0.25) for i in idx])
            for m, i in (("a1", 0), ("a2", 1), ("a3", 2)):
                self.at(m, FadeIn(av[i], scale=1.8), Flash(av[i][0].get_center(), color=WHITE, flash_radius=0.25))
            self.at("q", Indicate(fline, color=YELLOW, scale_factor=1.0))
        self.wait(0.5)
        fade_all(self)


class Transport(Narrated):
    def construct(self):
        self.add(nav("all", "delivery"))
        title = Tex(r"taming the beam: capture and selection", font_size=34).to_edge(UP, buff=0.35)
        src = Dot(LEFT * 6.0 + UP * 1.2, color=WHITE)
        spray = VGroup(*[Line(src.get_center(), src.get_center() + 1.6 * np.array([np.cos(a), np.sin(a), 0]), color=PROT_C, stroke_width=2) for a in np.linspace(-0.45, 0.45, 9)])
        lens = VGroup(Ellipse(width=0.35, height=1.8, color=BLUE_L, fill_opacity=0.2), *[Line(UP * y + LEFT * 0.17, UP * y + RIGHT * 0.17, color=BLUE_L) for y in np.linspace(-0.7, 0.7, 6)])
        lens.move_to(src.get_center() + RIGHT * 1.8)
        par = VGroup(*[Line(lens.get_center() + UP * (0.7 * np.sin(a) / 0.45 * 0.6) + RIGHT * 0.2, lens.get_center() + UP * (0.7 * np.sin(a) / 0.45 * 0.6) + RIGHT * 1.8,
                            color=PROT_C, stroke_width=2) for a in np.linspace(-0.45, 0.45, 9)])
        ll = VGroup(Tex(r"solenoid or permanent-magnet", font_size=20, color=BLUE_L), Tex(r"quadrupole lenses", font_size=20, color=BLUE_L)).arrange(DOWN, buff=0.04).next_to(lens, DOWN, buff=0.15)
        two = Tex(r"2 permanent magnets collimate \textbf{10 MeV} protons", font_size=22).next_to(VGroup(lens, par), UP, buff=0.25)
        # dipole separation, computed radii
        B, T = 0.9, 9.5
        r_p = momentum(T, 938.272) / 1000 / (0.29979 * 1 * B)
        r_c = momentum(12 * T, 11177.9) / 1000 / (0.29979 * 6 * B)
        o = RIGHT * 0.4 + UP * 0.1
        fld = Rectangle(width=3.2, height=3.0, fill_color=BLUE_L, fill_opacity=0.12, stroke_color=BLUE_L).move_to(o + RIGHT * 1.6 + DOWN * 0.6)
        fl = Tex(r"dipole \textbf{0.9 T}", font_size=22, color=BLUE_L).next_to(fld, UP, buff=0.08).align_to(fld, LEFT)
        S = 3.0 / r_c                                          # screen units per metre: carbon bends over the full field
        def track(r, col, length=3.2):
            R = r * S * 1.0
            pts = [o + np.array([R * np.sin(s), -(R - R * np.cos(s)), 0]) for s in np.linspace(0, min(length / R, 1.2), 50)]
            return VMobject(color=col, stroke_width=4).set_points_smoothly(pts)
        inbeam = Line(o + LEFT * 1.2, o, color=WHITE, stroke_width=4)
        tp, tc = track(r_p, PROT_C, 2.4), track(r_c, CARB_C)
        slit_x = tc.get_end()[0] + 0.3
        cy_ = tc.get_end()[1] + (tc.get_end()[1] - tc.points[-4][1]) / max(tc.get_end()[0] - tc.points[-4][0], 1e-3) * 0.3
        slit = VGroup(Rectangle(width=0.2, height=0.9, fill_color=GREY_C, fill_opacity=1, stroke_width=0).move_to(np.array([slit_x, cy_ + 0.57, 0])),
                      Rectangle(width=0.2, height=0.9, fill_color=GREY_C, fill_opacity=1, stroke_width=0).move_to(np.array([slit_x, cy_ - 0.57, 0])))
        sl = Tex(r"slit \textbf{500\,$\mu$m}", font_size=22).next_to(slit, UP, buff=0.1)
        rl = VGroup(Tex(r"proton: $r$ = \textbf{%.2f m}" % r_p, font_size=22, color=PROT_C), Tex(r"carbon: $r$ = \textbf{%.2f m}" % r_c, font_size=22, color=CARB_C),
                    Tex(r"$r = p/qB$, at 9.5 MeV/u (computed)", font_size=18, color=GREY_B)).arrange(DOWN, aligned_edge=LEFT, buff=0.1).to_corner(DL, buff=0.35)
        mq = Tex(r"$m/q$: carbon \textbf{2}, proton \textbf{1}", font_size=24).next_to(rl, UP, buff=0.25).align_to(rl, LEFT)
        gantry = Tex(r"capture + selection gantry: \textbf{2--3$\times$} smaller", font_size=24, color=GOOD_C).to_corner(UR, buff=0.3).shift(DOWN * 0.75)
        bsym = b_symbols(fld, into=False, nx=5, ny=4)                    # B out of the page bends positive ions downward
        bl = Tex(r"$\mathbf{B}$ out of page", font_size=18, color=BLUE_L).next_to(fld, UP, buff=0.08).align_to(fld, RIGHT)

        def force(r, col, s0):
            R = r * S
            p = o + np.array([R * np.sin(s0), -(R - R * np.cos(s0)), 0])
            v = np.array([np.cos(s0), -np.sin(s0), 0])
            f = (o + np.array([0, -R, 0]) - p) / R
            return VGroup(Arrow(p, p + 0.55 * v, buff=0, color=WHITE, stroke_width=3, max_tip_length_to_length_ratio=0.3),
                          Arrow(p, p + 0.55 * f, buff=0, color=YELLOW, stroke_width=4, max_tip_length_to_length_ratio=0.3))
        fp, fc = force(r_p, PROT_C, 0.35), force(r_c, CARB_C, 0.55)
        fll = VGroup(Tex(r"$\mathbf{v}$", font_size=22).next_to(fc[0].get_end(), RIGHT, buff=0.05),
                     Tex(r"$\mathbf{F} = q\,\mathbf{v}\times\mathbf{B}$", font_size=22, color=YELLOW).next_to(fld, DOWN, buff=0.08).align_to(fld, LEFT))
        with self.voiceover(text="A broad, <bookmark mark='br'/>divergent, mixed beam has to be tamed before it can reach a patient. "
                                 "<bookmark mark='c'/>First, capture it: pulsed solenoids or permanent magnet quadrupoles <bookmark mark='g1'/>"
                                 "grab the spreading particles and make them <bookmark mark='pa'/>parallel; <bookmark mark='t'/>one recent "
                                 "system collimated a ten MeV proton beam with just two permanent magnets. <bookmark mark='s'/>Then select. "
                                 "In a laser driven carbon experiment, a zero point nine tesla <bookmark mark='dp'/>dipole sat fifty "
                                 "millimetres from the target. <bookmark mark='b'/>A carbon ion has twice a proton's mass to charge ratio, "
                                 "so at the same energy per nucleon it <bookmark mark='bd'/>bends on twice the radius, about "
                                 "<bookmark mark='r1'/>one metre against <bookmark mark='r2'/>half a metre. <bookmark mark='l'/>A five "
                                 "hundred micrometre slit then passes only the carbon. <bookmark mark='g'/>Gantry designs built around "
                                 "capture and energy selection come out two to three times smaller than a conventional proton gantry."):
            self.play(Write(title), FadeIn(src), Create(spray), run_time=0.8)
            self.at("br", Indicate(spray, color=YELLOW, scale_factor=1.05))
            self.at("c", FadeIn(lens), FadeIn(ll))
            self.play(Circumscribe(lens, color=YELLOW), run_time=0.6)
            self.at("g1", Create(par), run_time=0.8)
            self.at("pa", Indicate(par, color=YELLOW, scale_factor=1.03))
            self.at("t", FadeIn(two), Indicate(lens, color=BLUE_L))
            self.wait_until_bookmark("s")
            restore = spotlight(self, [title])
            self.play(FadeIn(fld), FadeIn(fl), FadeIn(bsym), FadeIn(bl), Create(inbeam))
            self.at("dp", Indicate(bsym, color=BLUE_L, scale_factor=1.15), Circumscribe(fld, color=BLUE_L))
            self.at("b", Create(tp), Create(tc), FadeIn(mq), FadeIn(rl), run_time=1.5)
            self.play(GrowArrow(fp[0]), GrowArrow(fc[0]), GrowArrow(fp[1]), GrowArrow(fc[1]), FadeIn(fll), run_time=0.8)
            self.at("bd", Indicate(VGroup(fp[1], fc[1]), color=YELLOW, scale_factor=1.3))
            self.at("r1", Indicate(tc, color=CARB_C), Indicate(rl[1], color=CARB_C))
            self.at("r2", Indicate(tp, color=PROT_C), Indicate(rl[0], color=PROT_C))
            self.at("l", FadeIn(slit), FadeIn(sl), ShowPassingFlash(tc.copy().set_stroke(YELLOW, 8), time_width=0.4), run_time=1.0)
            self.at("g", restore, FadeIn(gantry))
        self.wait(0.5)
        fade_all(self)


class SOBP(Narrated):
    def construct(self):
        self.add(nav("all", "delivery"))
        title = Tex(r"from a broad spectrum to a flat dose", font_size=34).to_edge(UP, buff=0.35)
        ax = Axes(x_range=[0, 22, 5], y_range=[0, 1.25, 0.5], x_length=9.0, y_length=4.0, tips=False,
                  axis_config={"color": GREY_B, "font_size": 20}, x_axis_config={"numbers_to_include": [0, 5, 10, 15, 20]},
                  y_axis_config={"include_ticks": False}).move_to(DOWN * 0.3)
        axl = Tex(r"depth in water (cm)", font_size=20, color=GREY_B).next_to(ax, DOWN, buff=0.15)
        tum = Rectangle(width=ax.c2p(17, 0)[0] - ax.c2p(12, 0)[0], height=ax.c2p(0, 1.25)[1] - ax.c2p(0, 0)[1], fill_color=BAD_C, fill_opacity=0.12, stroke_width=0).move_to(ax.c2p(12, 0), aligned_edge=DL)
        Rs = np.linspace(12.2, 17.0, 11)
        z = np.linspace(12.0, 17.0, 120)
        A = np.stack([bragg(z, R) for R in Rs], 1)
        w = np.linalg.lstsq(A, np.ones_like(z), rcond=None)[0]
        for _ in range(30):
            w = np.clip(w, 0, None)
            act = w > 0
            w_a = np.linalg.lstsq(A[:, act], np.ones_like(z), rcond=None)[0]
            w = np.zeros_like(w)
            w[act] = w_a
        w = np.clip(w, 0, None)
        Es = [(R / 0.0022) ** (1 / 1.77) for R in Rs]
        cols = [interpolate_color(ManimColor(PROT_C), ManimColor(BAD_C), k / 10) for k in range(11)]
        one = ax.plot(lambda d: bragg(d, Rs[-1]), x_range=[0, 22, 0.05], color=PROT_C, stroke_width=4)
        parts = VGroup(*[ax.plot(lambda d, R=R, wk=wk: wk * bragg(d, R), x_range=[0, 22, 0.05], color=c, stroke_width=2) for R, wk, c in zip(Rs, w, cols)])
        tot = ax.plot(lambda d: float(sum(wk * bragg(d, R) for R, wk in zip(Rs, w))), x_range=[0, 22, 0.05], color=WHITE, stroke_width=5)
        el = Tex(r"%d energies, %d--%d MeV, weights solved here" % (len(Rs), round(Es[0]), round(Es[-1])), font_size=22, color=GREY_B).next_to(ax, UP, buff=0.1)
        bead = Tex(r"laser shot = all energies at once (BEAD dose model)", font_size=24, color=PROT_C).to_edge(DOWN, buff=0.75)
        chal = Tex(r"but the spectrum changes \textbf{shot to shot}", font_size=26, color=BAD_C).to_edge(DOWN, buff=0.3)
        with self.voiceover(text="A broad spectrum also changes how dose is planned. <bookmark mark='o'/>One energy gives one narrow Bragg "
                                 "peak, far too thin for a tumour. <bookmark mark='m'/>Several energies, each with its own weight, "
                                 "<bookmark mark='s'/>add up to a spread out Bragg peak, flat across the tumour. <bookmark mark='l'/>A "
                                 "laser shot produces many energies at once, and the broad energy assorted depth dose model is built on "
                                 "exactly this idea. <bookmark mark='c'/>The difficulty is that the spectrum changes from shot to shot, "
                                 "and shaping it reliably is one of the open problems the review highlights."):
            self.play(Write(title), Create(ax), FadeIn(axl), FadeIn(tum), run_time=1.0)
            self.at("o", Create(one), run_time=1.2)
            self.at("m", FadeOut(one), LaggedStart(*[Create(p) for p in parts], lag_ratio=0.15), FadeIn(el), run_time=2.0)
            self.at("s", Create(tot), run_time=1.5)
            self.at("l", FadeIn(bead))
            self.at("c", FadeIn(chal))
        self.wait(0.5)
        fade_all(self)


class Biology(Narrated):
    def construct(self):
        self.add(nav("all", "biology"))
        title = Tex(r"the biology so far", font_size=34).to_edge(UP, buff=0.35)
        ax = Axes(x_range=[0, 3, 1], y_range=[0.8, 1.8, 0.2], x_length=4.2, y_length=3.4, tips=False,
                  axis_config={"color": GREY_B, "font_size": 18}, y_axis_config={"numbers_to_include": [1.0, 1.2, 1.4, 1.6]},
                  x_axis_config={"include_ticks": False}).move_to(LEFT * 4.0 + DOWN * 0.3)
        axl = Tex(r"RBE$_{10}$", font_size=22, color=GREY_B).next_to(ax.y_axis, UP, buff=0.1)
        ref = DashedLine(ax.c2p(0, 1.1), ax.c2p(3, 1.1), color=GREY_A)
        refl = Tex(r"clinical 1.1", font_size=18, color=GREY_A).next_to(ax.c2p(3, 1.1), RIGHT, buff=0.05)
        pts = [(1, 1.20, 0.11, r"hamster, $10^7$ Gy/s"), (2, 1.4, 0.2, r"salivary, $10^9$ Gy/s")]
        dots = VGroup(*[VGroup(Line(ax.c2p(x, v - e), ax.c2p(x, v + e), color=PROT_C, stroke_width=3), Dot(ax.c2p(x, v), color=PROT_C),
                               Tex(l, font_size=16, color=PROT_C).next_to(ax.c2p(x, v - e), DOWN, buff=0.1)) for x, v, e, l in pts])
        same = Tex(r"direct comparisons: \textbf{no significant difference}", font_size=22, color=GOOD_C).next_to(ax, DOWN, buff=0.35)
        # in vivo: mouse ear with a tumour
        ear = Ellipse(width=1.6, height=1.0, fill_color="#d9a38b", fill_opacity=0.5, stroke_color="#d9a38b").move_to(RIGHT * 0.6 + UP * 1.1)
        tumour = Circle(radius=0.15, fill_color=BAD_C, fill_opacity=0.9, stroke_width=0).move_to(ear.get_center() + RIGHT * 0.2)
        e_iv = VGroup(Tex(r"\textbf{2015} laser electrons: 3, 6 Gy", font_size=22, color=ELEC_C), Tex(r"= clinical linac", font_size=20, color=GREY_A)).arrange(DOWN, aligned_edge=LEFT, buff=0.05)
        p_iv = VGroup(Tex(r"\textbf{2022} laser protons: \textbf{4.0 $\pm$ 0.4 Gy}, one shot", font_size=22, color=PROT_C),
                      Tex(r"$\sim$3 mm tumours; = cyclotron", font_size=20, color=GREY_A)).arrange(DOWN, aligned_edge=LEFT, buff=0.05)
        VGroup(e_iv, p_iv).arrange(DOWN, aligned_edge=LEFT, buff=0.3).next_to(ear, RIGHT, buff=0.4)
        beam = Arrow(ear.get_center() + UP * 1.2 + LEFT * 0.2, tumour.get_center(), buff=0.05, color=PROT_C)
        hints = VGroup(tile(VGroup(*[Dot(radius=0.06, color=BAD_C).shift(np.array([x, y, 0])) for x, y in ((0, 0), (0.15, 0.1), (-0.1, 0.12), (0.05, -0.12))]),
                            r"UHDR e$^-$: \textbf{1.7--2.9$\times$} unrepaired breaks at 24 h", 6.2),
                       tile(VGroup(Circle(radius=0.2, color=BAD_C), Circle(radius=0.2, color=GOOD_C).shift(RIGHT * 0.3)), r"VHEE: melanoma vs normal differ more than with X-rays", 6.2)
                       ).arrange(DOWN, buff=0.2).move_to(RIGHT * 2.9 + DOWN * 1.8)
        with self.voiceover(text="Do these beams act on cells like conventional ones? So far, mostly yes. <bookmark mark='r'/>The relative "
                                 "biological effectiveness at ten percent survival was one point two for hamster cells at ten to the seven "
                                 "grays per second, <bookmark mark='s'/>and one point four for salivary gland cells at ten to the nine. "
                                 "<bookmark mark='c'/>Studies that compared laser and conventional protons directly found no significant "
                                 "difference, consistent with the clinical value of one point one. <bookmark mark='m'/>In living animals, "
                                 "laser driven electrons treated tumours on mouse ears with three and six grays in twenty fifteen, "
                                 "matching a clinical linac. <bookmark mark='k'/>In twenty twenty two, the first in vivo laser proton "
                                 "study delivered four grays in a single shot to three millimetre tumours, matching a cyclotron. "
                                 "<bookmark mark='d'/>A few results hint at something new: ultra high dose rate electrons left one point "
                                 "seven to two point nine times more unrepaired DNA breaks a day later, <bookmark mark='v'/>and a VHEE "
                                 "study saw a larger difference between melanoma and normal cells than X-rays gave."):
            self.play(Write(title), Create(ax), FadeIn(axl), Create(ref), FadeIn(refl), run_time=1.0)
            self.at("r", FadeIn(dots[0]))
            self.at("s", FadeIn(dots[1]))
            self.at("c", FadeIn(same), Indicate(ref, color=GREY_A, scale_factor=1.0))
            self.at("m", FadeIn(ear), FadeIn(tumour), FadeIn(e_iv))
            self.at("k", GrowArrow(beam), FadeIn(p_iv), Flash(tumour, color=PROT_C))
            self.at("d", FadeIn(hints[0]))
            self.at("v", FadeIn(hints[1]))
        self.wait(0.5)
        fade_all(self)


class Challenges(Narrated):
    def construct(self):
        self.add(nav("all", "obstacles"))
        title = Tex(r"what stands in the way", font_size=34).to_edge(UP, buff=0.35)
        items = [("beam quality", r"spread, shot-to-shot", PROT_C), ("transport", r"compact, focused", BLUE_L), ("dose shaping", r"SOBP, FLASH control", BAD_C),
                 ("dosimetry", r"extreme dose rates", YELLOW), ("clinic + regulation", r"no UHDR standards yet", GREY_A)]
        tiles = VGroup(*[VGroup(RoundedRectangle(corner_radius=0.12, width=2.45, height=1.1, color=c), Tex(a, font_size=24, color=c), Tex(b, font_size=18, color=GREY_A))
                         for a, b, c in items])
        for t_ in tiles:
            t_[1].move_to(t_[0].get_center() + UP * 0.2)
            t_[2].move_to(t_[0].get_center() + DOWN * 0.22)
        tiles.arrange(RIGHT, buff=0.15).shift(UP * 1.6)
        # dosimetry: chamber reading vs dose per pulse (illustrative saturation), film, calorimeter
        ax = Axes(x_range=[0, 4, 1], y_range=[0, 4, 1], x_length=3.6, y_length=2.4, tips=False, axis_config={"color": GREY_B, "include_ticks": False}).move_to(LEFT * 3.8 + DOWN * 1.5)
        axl = VGroup(Tex(r"dose per pulse", font_size=18, color=GREY_B).next_to(ax, DOWN, buff=0.08), Tex(r"reading", font_size=18, color=GREY_B).next_to(ax, LEFT, buff=0.08))
        ideal = DashedLine(ax.c2p(0, 0), ax.c2p(4, 4), color=GREY_A)
        sat = ax.plot(lambda d: 1.8 * (1 - np.exp(-d / 1.8)), x_range=[0, 4], color=YELLOW, stroke_width=4)
        satl = VGroup(Tex(r"ion chamber: saturates", font_size=20, color=YELLOW), Tex(r"(recombination; illustrative)", font_size=16, color=GREY_B)).arrange(DOWN, buff=0.04).next_to(ax.c2p(4, 1.8), DOWN, buff=0.15)
        film = tile(VGroup(Rectangle(width=0.5, height=0.35, color=GREY_A, fill_opacity=0.3), Circle(radius=0.15, color=BAD_C).shift(RIGHT * 0.4)), r"film: rate-independent, not real-time", 4.6)
        calo = tile(VGroup(Rectangle(width=0.4, height=0.4, color=GREY_A, fill_opacity=0.4), Line(UP * 0.3, DOWN * 0.2, color=BAD_C, stroke_width=5).shift(RIGHT * 0.35)),
                    r"graphite calorimeter: \textbf{1--3 Gy}/pulse, 15--40 MeV", 4.6)
        VGroup(film, calo).arrange(DOWN, buff=0.25).move_to(RIGHT * 3.2 + DOWN * 1.4)
        with self.voiceover(text="The review groups the obstacles into five. <bookmark mark='q'/>Beam quality: broad spectra that change "
                                 "from shot to shot. <bookmark mark='t'/>Transport: beamlines that stay compact yet keep the beam "
                                 "focused. <bookmark mark='d'/>Dose shaping, and the biology of ultra short pulses. <bookmark mark='m'/>"
                                 "Dosimetry. <bookmark mark='r'/>And clinical engineering and regulation: lasers stable over many "
                                 "thousands of shots, targets that can be replaced, shielding, and standards that do not yet cover ultra "
                                 "high dose rates. <bookmark mark='i'/>Dosimetry deserves a closer look. An ionisation chamber collects "
                                 "the charge freed in its gas, but when a whole dose arrives in picoseconds, much of that charge "
                                 "recombines first, and the reading saturates. <bookmark mark='f'/>Film responds almost independently of "
                                 "dose rate, but it is read out afterwards, not in real time. <bookmark mark='c'/>One proposed answer "
                                 "measures heat instead of charge: a small graphite calorimeter recorded one to three grays per pulse "
                                 "from fifteen to forty MeV laser protons."):
            self.play(Write(title), run_time=0.8)
            for k, m in enumerate("qtdmr"):
                self.at(m, FadeIn(tiles[k], shift=0.1 * UP))
            self.at("i", Indicate(tiles[3], color=YELLOW), Create(ax), FadeIn(axl), Create(ideal))
            self.play(Create(sat), FadeIn(satl), run_time=1.2)
            self.at("f", FadeIn(film))
            self.at("c", FadeIn(calo))
        self.wait(0.5)
        fade_all(self)


class Future(Narrated):
    def construct(self):
        self.add(nav("all", "outlook"))
        title = Tex(r"what is changing", font_size=34).to_edge(UP, buff=0.35)
        c = LEFT * 3.7 + UP * 0.6
        nodes = [("laser", LASER_C), ("target", FOIL_C), ("measure", YELLOW), ("optimiser", GOOD_C)]
        pos = [c + 1.4 * np.array([np.cos(a), np.sin(a), 0]) for a in (PI / 2, 0, -PI / 2, PI)]
        loop = VGroup(*[VGroup(RoundedRectangle(corner_radius=0.12, width=1.6, height=0.6, color=col), Tex(n, font_size=22, color=col)).move_to(p) for (n, col), p in zip(nodes, pos)])
        arrows = VGroup(*[CurvedArrow(pos[k] + 0.35 * (pos[(k + 1) % 4] - pos[k]) / np.linalg.norm(pos[(k + 1) % 4] - pos[k]),
                                      pos[(k + 1) % 4] - 0.35 * (pos[(k + 1) % 4] - pos[k]) / np.linalg.norm(pos[(k + 1) % 4] - pos[k]), angle=-0.6, color=GREY_B)
                          for k in range(4)])
        knobs = Tex(r"wavefront, target position", font_size=18, color=GREY_A).next_to(loop[0], UP, buff=0.08)
        # trials converging (illustrative)
        ax = Axes(x_range=[0, 30, 10], y_range=[0, 1.1, 0.5], x_length=4.2, y_length=2.2, tips=False, axis_config={"color": GREY_B, "include_ticks": False}).move_to(RIGHT * 3.4 + UP * 0.9)
        rng = np.random.default_rng(6)
        ys = [min(1.0, 0.25 + 0.75 * (1 - np.exp(-k / 7)) + rng.normal(0, 0.12 * np.exp(-k / 12))) for k in range(30)]
        best = np.maximum.accumulate(ys)
        trials = VGroup(*[Dot(ax.c2p(k, y), radius=0.04, color=GREY_A) for k, y in enumerate(ys)])
        bline = VMobject(color=GOOD_C, stroke_width=3).set_points_as_corners([ax.c2p(k, b) for k, b in enumerate(best)])
        axl = VGroup(Tex(r"shot", font_size=18, color=GREY_B).next_to(ax, DOWN, buff=0.08), Tex(r"proton $E_{\max}$", font_size=18, color=GREY_B).next_to(ax, UP, buff=0.05),
                     Tex(r"schematic", font_size=16, color=GREY_B).next_to(ax, RIGHT, buff=0.05).shift(DOWN * 0.8))
        res = Tex(r"same energy as manual tuning with \textbf{60\%} of the laser energy", font_size=22, color=GOOD_C).next_to(ax, DOWN, buff=0.35)
        sig = Tex(r"signal: transmitted laser light", font_size=22, color=YELLOW).next_to(loop[2], DOWN, buff=0.25)
        tg = VGroup(tile(VGroup(*[Dot(UP * y, radius=0.05, color=BLUE_L) for y in np.linspace(-0.25, 0.25, 4)]), r"cryogenic H$_2$ jets", 2.9, 20),
                    tile(VGroup(Rectangle(width=0.1, height=0.5, color=BLUE_L, fill_opacity=0.5)), r"liquid sheets", 2.4, 20),
                    tile(VGroup(Circle(radius=0.2, color=FOIL_C), Circle(radius=0.2, color=FOIL_C).shift(RIGHT * 0.5), Line(UP * 0.2, UP * 0.2 + RIGHT * 0.5, color=FOIL_C)), r"tape drives", 2.4, 20))
        tg.arrange(RIGHT, buff=0.2).move_to(RIGHT * 2.1 + DOWN * 1.85)
        tgl = Tex(r"targets for sustained \textbf{multi-Hz}", font_size=22).next_to(tg, UP, buff=0.1)
        fac = VGroup(Tex(r"\textbf{LhARA} (UK): 10 Hz; p to \textbf{127 MeV}, C to \textbf{33.4 MeV/u}", font_size=22),
                     Tex(r"\textbf{Dr.~LASER} (ELI, Romania): C to \textbf{110 MeV/u}, $\sim$30 mm", font_size=22)).arrange(DOWN, buff=0.1).to_edge(DOWN, buff=0.2)
        with self.voiceover(text="What is changing? <bookmark mark='b'/>Tuning a laser plasma source is a nonlinear search in many dimensions, "
                                 "where adjusting one knob at a time is slow and misses the best settings. <bookmark mark='l'/>A closed "
                                 "loop Bayesian optimiser adjusts the <bookmark mark='lw'/>laser wavefront and target position, <bookmark mark='fi'/>fires, "
                                 "<bookmark mark='me'/>measures, and <bookmark mark='ch'/>chooses the next shot. <bookmark mark='r'/>The first such system matched the best manual proton energy using "
                                 "only sixty percent of the laser energy. <bookmark mark='f'/>It needs a fast signal from every shot, and "
                                 "transmitted laser light is one candidate. <bookmark mark='t'/>It also needs targets that survive: "
                                 "<bookmark mark='t1'/>cryogenic hydrogen jets, <bookmark mark='t2'/>liquid sheets and <bookmark mark='t3'/>tape drives now allow sustained multi hertz operation. "
                                 "<bookmark mark='p'/>Two dedicated research facilities are planned: LhARA in the UK, with protons up to "
                                 "one hundred and twenty seven MeV and carbon up to thirty three point four MeV per nucleon, "
                                 "<bookmark mark='d'/>and Dr LASER at ELI in Romania, aiming for carbon up to one hundred and ten MeV per "
                                 "nucleon, about three centimetres in tissue."):
            self.play(Write(title), run_time=0.8)
            self.at("b", Create(ax), FadeIn(axl), LaggedStart(*[FadeIn(d) for d in trials], lag_ratio=0.05), run_time=1.5)
            self.at("l", FadeIn(loop), LaggedStart(*[Create(a) for a in arrows], lag_ratio=0.25), Create(bline), run_time=1.5)
            self.at("lw", FadeIn(knobs), Indicate(loop[0], color=LASER_C, scale_factor=1.15))
            self.at("fi", Indicate(loop[1], color=WHITE, scale_factor=1.15))
            self.at("me", Indicate(loop[2], color=YELLOW, scale_factor=1.15))
            self.at("ch", Indicate(loop[3], color=GOOD_C, scale_factor=1.15))
            self.at("r", FadeIn(res), Indicate(bline, color=GOOD_C, scale_factor=1.0))
            self.at("f", FadeIn(sig), Indicate(loop[2], color=YELLOW))
            self.at("t", FadeIn(tgl))
            for m, i in (("t1", 0), ("t2", 1), ("t3", 2)):
                self.at(m, FadeIn(tg[i], scale=1.1))
            self.at("p", FadeIn(fac[0]))
            self.at("d", FadeIn(fac[1]))
        self.wait(0.5)
        fade_all(self)


class Takeaway(Narrated):
    def construct(self):
        self.add(nav("all", "energy"))
        title = Tex(r"where it stands: energy reached vs needed", font_size=32).to_edge(UP, buff=0.35)
        ax = NumberLine(x_range=[0, 450, 50], length=9.5, include_numbers=True, font_size=20, color=GREY_B).move_to(DOWN * 2.3 + RIGHT * 0.9)
        axl = Tex(r"MeV (per nucleon for carbon)", font_size=20, color=GREY_B).next_to(ax, DOWN, buff=0.45)
        rows = [("electrons", ELEC_C, (50, 250), 450, r"\textbf{7.8 GeV} $\rightarrow$", 1.2),
                ("protons", PROT_C, (60, 250), 150, r"\textbf{150 MeV}: $\sim$15 cm", 0.1),
                ("carbon", CARB_C, (120, 430), 48, r"\textbf{48 MeV/u}: $<$1 cm", -1.0)]
        groups = VGroup()
        for name, col, (a, b), rec, lab, y in rows:
            band = Rectangle(width=ax.n2p(b)[0] - ax.n2p(a)[0], height=0.5, fill_color=col, fill_opacity=0.25, stroke_color=col).move_to(np.array([(ax.n2p(a)[0] + ax.n2p(b)[0]) / 2, y, 0]))
            mark = Triangle(color=col, fill_opacity=1).scale(0.14).rotate(PI).move_to(np.array([ax.n2p(min(rec, 445))[0], y + 0.4, 0]))
            rl = Tex(lab, font_size=20, color=col).next_to(mark, UP, buff=0.05)
            nl = Tex(name, font_size=24, color=col).next_to(np.array([ax.n2p(0)[0], y, 0]), LEFT, buff=0.3)
            groups.add(VGroup(nl, band, mark, rl))
        key = VGroup(VGroup(Rectangle(width=0.4, height=0.2, fill_color=GREY_B, fill_opacity=0.3, stroke_color=GREY_B), Tex(r"needed for therapy", font_size=18)).arrange(RIGHT, buff=0.1),
                     VGroup(Triangle(color=GREY_A, fill_opacity=1).scale(0.1).rotate(PI), Tex(r"record", font_size=18)).arrange(RIGHT, buff=0.1)).arrange(RIGHT, buff=0.5).next_to(title, DOWN, buff=0.2)
        planned = VGroup(DashedLine(np.array([ax.n2p(110)[0], -1.35, 0]), np.array([ax.n2p(110)[0], -0.65, 0]), color=CARB_C),
                         Tex(r"ELI plan 110", font_size=16, color=CARB_C))
        planned[1].next_to(planned[0], LEFT, buff=0.06)
        note = Tex(r"depths: Bragg--Kleeman, computed here", font_size=16, color=GREY_B).to_corner(DR, buff=0.15)
        with self.voiceover(text="So where does each branch stand on energy? <bookmark mark='e'/>Electrons are there: therapy needs fifty to "
                                 "two hundred and fifty MeV, and wakefields have gone far beyond. <bookmark mark='p'/>Protons have reached "
                                 "one hundred and fifty MeV, inside the therapeutic range and enough for about fifteen centimetres of "
                                 "water. <bookmark mark='c'/>Carbon has reached forty eight MeV per nucleon, against the one hundred and "
                                 "twenty to four hundred and thirty needed, which is under a centimetre of range."):
            self.play(Write(title), Create(ax), FadeIn(axl), FadeIn(key), FadeIn(note), run_time=1.0)
            for k, m in enumerate("epc"):
                self.at(m, FadeIn(groups[k][0]), GrowFromCenter(groups[k][1]), FadeIn(groups[k][2], shift=0.2 * DOWN), FadeIn(groups[k][3]))
            self.play(FadeIn(planned))
        self.wait(1.0)
        fade_all(self)


# ---- survey structure: compare the branches, then the full map (docs/DESIGN.md Part I, "Start here") ---------------
def mini_spectrum(kind, w=1.3, h=0.55, color=WHITE):
    """Illustrative spectrum shapes: 'broad' (decaying, wide) or 'bunch' (a narrow peak)."""
    if kind == "bunch":
        f = lambda x: np.exp(-((x - 0.65) / 0.06) ** 2)
    else:
        f = lambda x: np.exp(-x / 0.35) * (x > 0.02) + 0.0
    pts = [np.array([x * w - w / 2, f(x) * h - h / 2, 0]) for x in np.linspace(0, 1, 60)]
    base = Line(np.array([-w / 2, -h / 2, 0]), np.array([w / 2, -h / 2, 0]), color=GREY_B, stroke_width=1.5)
    return VGroup(base, VMobject(color=color, stroke_width=3).set_points_smoothly(pts))


def mini_cone(full_angle, L=1.3, color=WHITE):
    o = np.array([-L / 2, 0, 0])
    if full_angle < 0.01:
        return VGroup(Polygon(o, o + RIGHT * L + UP * L * np.tan(full_angle / 2), o + RIGHT * L + DOWN * L * np.tan(full_angle / 2),
                              color=color, fill_opacity=0.5, stroke_width=1.5))
    return VGroup(Polygon(o, o + RIGHT * L + UP * L * np.tan(full_angle / 2), o + RIGHT * L + DOWN * L * np.tan(full_angle / 2),
                          color=color, fill_opacity=0.35, stroke_width=1))


def mini_need(lo, hi, rec, color, w=1.6, xmax=450.0, beyond=False):
    """Therapy range (band) against the best result (triangle) on a 0-450 MeV(/u) axis."""
    x = lambda v: -w / 2 + w * min(v, xmax) / xmax
    axis = Line(np.array([-w / 2, -0.18, 0]), np.array([w / 2, -0.18, 0]), color=GREY_B, stroke_width=1.5)
    band = Rectangle(width=x(hi) - x(lo), height=0.22, fill_color=color, fill_opacity=0.3, stroke_color=color, stroke_width=1).move_to(np.array([(x(lo) + x(hi)) / 2, 0, 0]))
    tri = Triangle(color=color, fill_opacity=1).scale(0.09).rotate(PI).move_to(np.array([x(rec), 0.25, 0]))
    g = VGroup(axis, band, tri)
    if beyond:
        g.add(Arrow(np.array([x(rec) - 0.15, 0.25, 0]), np.array([x(rec) + 0.2, 0.25, 0]), buff=0, color=color, stroke_width=2, max_tip_length_to_length_ratio=0.4))
    return g


class Compare(Narrated):
    def construct(self):
        self.add(nav("all", "compare"))
        title = Tex(r"the three branches side by side", font_size=34).to_edge(UP, buff=0.35)
        ys = [1.05, -0.35, -1.75]
        cols = [-3.75, -1.85, 0.05, 1.95, 3.9, 5.85]
        heads = [r"target", r"intensity, W/cm$^2$", r"spectrum", r"spread (to scale)", r"energy vs need", r"furthest biology"]
        hrow = VGroup(*[Tex(h, font_size=18, color=GREY_A).move_to(np.array([x, 2.15, 0])) for h, x in zip(heads, cols)])
        rows = VGroup(*[map_chips(k, 1.25)[k].copy().move_to(np.array([-5.85, y, 0])) for k, y in enumerate(ys)])
        grid = VGroup(*[Line(np.array([-6.8, y + 0.7, 0]), np.array([6.8, y + 0.7, 0]), color=GREY_E, stroke_width=1) for y in ys])
        # targets
        gas = VGroup(*[Dot(np.array([x, y, 0]), radius=0.03, color=GREY_B) for x in np.linspace(-0.3, 0.3, 5) for y in np.linspace(-0.22, 0.22, 4)])
        tg = [VGroup(gas, Tex(r"gas", font_size=16, color=GREY_B).next_to(gas, DOWN, buff=0.08)),
              VGroup(foil(0.14, 0.6), Tex(r"5--50\,$\mu$m", font_size=16, color=GREY_B)),
              VGroup(foil(0.03, 0.6), Tex(r"nm--1.5\,$\mu$m", font_size=16, color=GREY_B))]
        for t_ in tg[1:]:
            t_[1].next_to(t_[0], DOWN, buff=0.08)
        # intensity on a 10^18 .. 10^23 log scale
        def ibar(a, b, c):
            w = 1.5
            x = lambda e: -w / 2 + w * (e - 18) / 5
            ax_ = Line(np.array([-w / 2, -0.2, 0]), np.array([w / 2, -0.2, 0]), color=GREY_B, stroke_width=1.5)
            bar = Rectangle(width=x(b) - x(a), height=0.22, fill_color=c, fill_opacity=0.8, stroke_width=0).move_to(np.array([(x(a) + x(b)) / 2, 0.02, 0]))
            ticks = VGroup(Tex(r"18", font_size=14, color=GREY_B).move_to(np.array([x(18), -0.38, 0])), Tex(r"23", font_size=14, color=GREY_B).move_to(np.array([x(23), -0.38, 0])))
            return VGroup(ax_, bar, ticks)
        it = [ibar(18, 18.8, ELEC_C), ibar(18, 20.3, PROT_C), ibar(21, 23, CARB_C)]
        sp = [mini_spectrum("broad", color=ELEC_C), mini_spectrum("broad", color=PROT_C), mini_spectrum("bunch", color=CARB_C)]
        dv = [VGroup(mini_cone(0.005, color=ELEC_C), Tex(r"1--5 mrad", font_size=16, color=ELEC_C)),
              VGroup(mini_cone(0.3, color=PROT_C), Tex(r"200--300 mrad", font_size=16, color=PROT_C)),
              VGroup(mini_cone(0.05, color=CARB_C), Tex(r"$\sim$50 mrad", font_size=16, color=CARB_C))]
        for d in dv:
            d[1].next_to(d[0], DOWN, buff=0.12)
        en = [VGroup(mini_need(50, 250, 450, ELEC_C, beyond=True), Tex(r"7.8 GeV", font_size=16, color=ELEC_C)),
              VGroup(mini_need(60, 250, 150, PROT_C), Tex(r"150 MeV", font_size=16, color=PROT_C)),
              VGroup(mini_need(120, 430, 48, CARB_C), Tex(r"C: 48 MeV/u", font_size=16, color=CARB_C))]
        for e in en:
            e[1].next_to(e[0], DOWN, buff=0.08)
        bio = [VGroup(RoundedRectangle(corner_radius=0.08, width=1.45, height=0.42, color=GOOD_C, fill_opacity=0.2), Tex(r"e$^-$ in vivo, 2015", font_size=16)),
               VGroup(RoundedRectangle(corner_radius=0.08, width=1.45, height=0.42, color=GOOD_C, fill_opacity=0.2), Tex(r"p in vivo, 2022", font_size=16)),
               VGroup(RoundedRectangle(corner_radius=0.08, width=1.45, height=0.42, color=ORANGE_L, fill_opacity=0.2), Tex(r"C in vitro, 2023", font_size=16))]
        for b in bio:
            b[1].move_to(b[0])
        cells = [tg, it, sp, dv, en, bio]
        for c, x in zip(cells, cols):
            for k, m in enumerate(c):
                m.move_to(np.array([x, ys[k], 0]))
        note = Tex(r"spectrum shapes illustrative; biology by particle", font_size=16, color=GREY_B).to_corner(DR, buff=0.12)
        verdicts = [Tex(r"\textbf{LWFA} wins on energy and beam spread $\to$ VHEE", font_size=26, color=ELEC_C),
                    Tex(r"\textbf{TNSA} wins on maturity and particle numbers $\to$ protons today", font_size=26, color=PROT_C),
                    Tex(r"\textbf{RPA} wins on spectrum and scaling $\to$ the route to carbon, furthest from the clinic", font_size=26, color=CARB_C)]
        for v in verdicts:
            v.to_edge(DOWN, buff=0.3)
            fit_frame(v)
        wins = [[(4, 0), (3, 0)], [(5, 1), (0, 1)], [(2, 2), (1, 2)]]
        hl = [VGroup(*[SurroundingRectangle(cells[c][r], buff=0.08, color=YELLOW, stroke_width=3) for c, r in w]) for w in wins]
        with self.voiceover(text="Before looking at the beams in detail, here is how the three branches compare. <bookmark mark='t'/>"
                                 "Targets: a gas, a micrometre foil, a nanometre foil. <bookmark mark='i'/>Intensity: wakefields and sheath "
                                 "acceleration work from about ten to the eighteen watts per square centimetre; radiation pressure needs "
                                 "ten to the twenty one and up. <bookmark mark='s'/>Spectrum: wakefield electrons and sheath protons come "
                                 "out with broad energy spreads, while radiation pressure ions come out as a bunch. <bookmark mark='d'/>"
                                 "Spread: wakefield electrons a few milliradians, radiation pressure ions about fifty, slow sheath protons "
                                 "up to three hundred. <bookmark mark='e'/>Energy against what therapy needs: electrons are already far "
                                 "beyond it, protons have reached the therapeutic range, and carbon is well short. <bookmark mark='b'/>And "
                                 "biology: laser electrons and laser protons have both treated tumours in mice, while radiation pressure "
                                 "carbon has so far irradiated cells in a dish. <bookmark mark='w'/>So each branch wins somewhere. "
                                 "<bookmark mark='l'/>Wakefields win on energy and beam spread, for very high energy electrons. "
                                 "<bookmark mark='n'/>Sheath acceleration wins on maturity and particle numbers, for protons today. "
                                 "<bookmark mark='r'/>Radiation pressure wins on spectrum and scaling, the route to carbon, but it is the "
                                 "furthest from the clinic."):
            self.play(Write(title), FadeIn(rows), FadeIn(grid), run_time=1.0)
            for k, m in enumerate("tisdeb"):
                self.at(m, FadeIn(hrow[k]), LaggedStart(*[FadeIn(c_) for c_ in cells[k]], lag_ratio=0.25), FadeIn(note) if k == 2 else Wait(0), run_time=1.0)
            self.at("w", Indicate(rows, color=YELLOW, scale_factor=1.05))
            self.at("l", Create(hl[0]), FadeIn(verdicts[0]))
            self.at("n", ReplacementTransform(hl[0], hl[1]), ReplacementTransform(verdicts[0], verdicts[1]))
            self.at("r", ReplacementTransform(hl[1], hl[2]), ReplacementTransform(verdicts[1], verdicts[2]))
        self.wait(0.5)
        fade_all(self)


class FieldMap(Narrated):
    def construct(self):
        title = Tex(r"the map of the field", font_size=34).to_edge(UP, buff=0.35)
        root = VGroup(RoundedRectangle(corner_radius=0.12, width=3.4, height=0.55, color=LASER_C), Tex(r"laser-plasma acceleration", font_size=24, color=LASER_C))
        root[1].move_to(root[0])
        root.move_to(UP * 2.35)
        xs = [-4.3, 0.0, 4.3]
        mods = [r"VHEE electrons", r"proton therapy", r"carbon therapy"]
        status = [[(r"energy: reached", GOOD_C), (r"in vivo: yes", GOOD_C), (r"open: spread, dosimetry", BAD_C)],
                  [(r"energy: in range", GOOD_C), (r"in vivo: yes", GOOD_C), (r"open: spectrum, spread, SOBP", BAD_C)],
                  [(r"energy: $<$1 cm range", BAD_C), (r"cells only", ORANGE_L), (r"open: $10^{21+}$ W/cm$^2$, rep rate", BAD_C)]]
        branches = VGroup()
        for k, (x, m) in enumerate(zip(xs, mods)):
            chip = map_chips(k, 1.5)[k].copy().move_to(np.array([x, 1.2, 0]))
            edge = Line(root.get_bottom(), chip.get_top(), color=GREY_B, stroke_width=2)
            mod = Tex(m, font_size=24, color=BRANCHES[k][2]).next_to(chip, DOWN, buff=0.2)
            st = VGroup(*[Tex(t, font_size=20, color=c) for t, c in status[k]]).arrange(DOWN, buff=0.1).next_to(mod, DOWN, buff=0.25)
            branches.add(VGroup(edge, chip, mod, st))
        cross = VGroup(RoundedRectangle(corner_radius=0.1, width=12.4, height=0.55, color=BAD_C, fill_opacity=0.12),
                       Tex(r"across all three: shot-to-shot stability $\cdot$ compact transport $\cdot$ dosimetry $\cdot$ regulation for UHDR", font_size=22, color=BAD_C))
        cross[1].move_to(cross[0])
        cross.move_to(DOWN * 2.35)
        enab = VGroup(RoundedRectangle(corner_radius=0.1, width=12.4, height=0.55, color=GOOD_C, fill_opacity=0.12),
                      Tex(r"enablers: closed-loop optimisation $\cdot$ multi-Hz targets $\cdot$ LhARA, ELI", font_size=22, color=GOOD_C))
        enab[1].move_to(enab[0])
        enab.move_to(DOWN * 3.05)
        with self.voiceover(text="Putting the map together. <bookmark mark='m'/>Three mechanisms, each feeding one kind of therapy. "
                                 "<bookmark mark='e'/>Wakefield electrons, for very high energy electron therapy: the energy is reached "
                                 "and tumours have been treated in mice; what remains is the energy spread and dosimetry at extreme dose "
                                 "rates. <bookmark mark='p'/>Sheath protons: inside the therapeutic energy range and through a first in "
                                 "vivo study; what remains is the broad spectrum, the wide spread, and building a uniform spread out "
                                 "Bragg peak from it. <bookmark mark='c'/>Radiation pressure carbon: still under a centimetre of range, "
                                 "and cells only; it needs a thousand times the intensity and faster repetition. <bookmark mark='x'/>Across "
                                 "all three run the same open problems: shot to shot stability, compact transport, dosimetry, and "
                                 "regulation that does not yet cover ultra high dose rates. <bookmark mark='f'/>And the enablers the review "
                                 "points to: closed loop optimisation, targets that survive multi hertz operation, and dedicated "
                                 "facilities. Its conclusion is that translation will be driven as much by automation, control and target "
                                 "engineering as by peak energy."):
            self.play(Write(title), FadeIn(root), run_time=1.0)
            self.at("m", *[AnimationGroup(Create(b[0]), FadeIn(b[1]), FadeIn(b[2])) for b in branches], run_time=1.2)
            restore = None
            for k, m in enumerate("epc"):
                self.wait_until_bookmark(m)
                if restore is not None:
                    self.play(restore)
                restore = spotlight(self, [title, root, branches[k]], run_time=0.4)
                self.play(Indicate(branches[k][1], color=WHITE), LaggedStart(*[FadeIn(t_, shift=0.05 * DOWN) for t_ in branches[k][3]], lag_ratio=0.4), run_time=1.5)
            self.at("x", restore, FadeIn(cross, shift=0.1 * UP))
            self.at("f", FadeIn(enab, shift=0.1 * UP))
        self.wait(1.0)
        fade_all(self)
