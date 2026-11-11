

# ---- demonstrations: the calibration as it happens on the bench (DESIGN.md §3) ---------------------------------
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
        countl = VGroup(count, Tex(r"events", font_size=24, color=GREY_B)).arrange(RIGHT, buff=0.15).next_to(frame, DOWN, buff=0.2)
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
        dims = VGroup(Tex(r"\textbf{32 mm}", font_size=22).next_to(crys, DOWN, buff=0.35),
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

        def shot(depth, rt=0.3, keep=False):
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
            shot(4.0, 0.4)
            self.wait_until_bookmark("d")
            shot(11.0, 0.3)
            shot(18.0, 0.3)
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
