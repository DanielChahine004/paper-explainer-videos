

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
            self.at("d", T.animate.set_value(4.0), run_time=3.0)
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
        cw = Tex(r"$\times$\textbf{%.2f}" % (eff[weak[0]] * eff[weak[1]]), font_size=26, color=BAD_C).next_to(lw.get_center(), DOWN, buff=0.2)
        cs = Tex(r"$\times$\textbf{%.2f}" % (eff[strong[0]] * eff[strong[1]]), font_size=26, color=GOOD_C).next_to(ls.get_center(), UP, buff=0.2)
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
            self.at("w", Create(lw), FadeIn(cw), *[Indicate(dets[k], color=BAD_C, scale_factor=1.6) for k in weak])
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
