

# ---- survey structure: compare the branches, then the full map (DESIGN.md Part I, "Start here") ---------------
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
            for k, m in enumerate("epc"):
                self.at(m, Indicate(branches[k][1], color=WHITE), LaggedStart(*[FadeIn(t_, shift=0.05 * DOWN) for t_ in branches[k][3]], lag_ratio=0.4), run_time=1.5)
            self.at("x", FadeIn(cross, shift=0.1 * UP))
            self.at("f", FadeIn(enab, shift=0.1 * UP))
        self.wait(1.0)
        fade_all(self)
