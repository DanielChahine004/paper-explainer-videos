# One scene body for both engines (bench_ce.py / bench_gx.py exec it after their own `import *`): the features the
# explainers lean on, ~30 s at 1080p60. No narration, so it times drawing and encoding only.
class Bench(Scene):
    def construct(self):
        import numpy as np
        ttl = Tex(r"\textbf{the light of a shared event}", font_size=36).to_edge(UP, buff=0.85)
        eq = MathTex(r"f(t) = \frac{E_f\,LY_f}{\tau_{fd}-\tau_{fr}}\left(e^{-t/\tau_{fd}}-e^{-t/\tau_{fr}}\right)", font_size=34)
        eq.next_to(ttl, DOWN, buff=0.4)
        ax = Axes(x_range=[0, 200, 50], y_range=[0, 1400, 400], x_length=6.0, y_length=3.3, tips=False,
                  axis_config={"color": GREY_B, "include_numbers": True, "font_size": 20}).move_to(LEFT * 2.0 + DOWN * 1.1)
        t = np.linspace(0, 200, 201)

        def rate(t, ef):
            f = ef / 1000 * 8400 / 1050 * (np.exp(-t / 1400) - np.exp(-t / 350))
            s = (511 - ef) / 1000 * 32000 / 39926 * (np.exp(-t / 40000) - np.exp(-t / 74))
            return 1000 * (f + s)
        ef = ValueTracker(0.0)
        cur = always_redraw(lambda: VMobject(color=ORANGE, stroke_width=5).set_points_as_corners(
            [ax.c2p(a, b) for a, b in zip(t, rate(t, ef.get_value()))]))
        num = always_redraw(lambda: VGroup(MathTex(r"E_f =", font_size=32), DecimalNumber(ef.get_value(), num_decimal_places=0,
                                           font_size=34, color=ORANGE), Tex(r"keV", font_size=26)).arrange(RIGHT, buff=0.1)
                            .move_to(RIGHT * 4.4 + DOWN * 0.7))
        dots = VGroup(*[Dot(radius=0.06, color=BLUE) for _ in range(40)]).arrange_in_grid(5, 8, buff=0.2).move_to(RIGHT * 4.4 + DOWN * 2.4)
        box = RoundedRectangle(corner_radius=0.1, width=2.6, height=1.0, color=TEAL).move_to(RIGHT * 4.4 + UP * 0.6)
        lab = Tex(r"shared \textbf{40 ps}", font_size=28).move_to(box)
        self.play(Write(ttl), run_time=1.0)
        self.play(Write(eq), run_time=1.5)
        self.play(Create(ax), FadeIn(num), run_time=1.0)
        self.add(cur)
        self.play(ef.animate.set_value(80), run_time=3.0)
        self.play(ef.animate.set_value(511), run_time=5.0, rate_func=smooth)
        self.play(Create(box), FadeIn(lab), run_time=1.0)
        self.play(LaggedStart(*[FadeIn(d, scale=2) for d in dots], lag_ratio=0.05), run_time=3.0)
        self.play(Indicate(lab), Circumscribe(eq), run_time=1.5)
        self.play(ef.animate.set_value(0), run_time=6.0)
        self.wait(2.0)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=1.0)
