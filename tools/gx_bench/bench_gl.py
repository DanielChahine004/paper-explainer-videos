# ManimGL (3b1b) ports of body.py and body3d.py, kept as close as its API allows: Tex is math mode and TexText is
# text, Create is ShowCreation, Circumscribe is FlashAround, and the camera is self.frame.
from manimlib import *
import numpy as np


class Bench(Scene):
    def construct(self):
        ttl = TexText(r"\textbf{the light of a shared event}", font_size=36).to_edge(UP, buff=0.85)
        eq = Tex(r"f(t) = \frac{E_f\,LY_f}{\tau_{fd}-\tau_{fr}}\left(e^{-t/\tau_{fd}}-e^{-t/\tau_{fr}}\right)", font_size=34)
        eq.next_to(ttl, DOWN, buff=0.4)
        ax = Axes(x_range=[0, 200, 50], y_range=[0, 1400, 400], width=6.0, height=3.3,
                  axis_config={"color": GREY_B, "include_tip": False}).move_to(LEFT * 2.0 + DOWN * 1.1)
        ax.add_coordinate_labels(font_size=20)
        t = np.linspace(0, 200, 201)

        def rate(t, ef):
            f = ef / 1000 * 8400 / 1050 * (np.exp(-t / 1400) - np.exp(-t / 350))
            s = (511 - ef) / 1000 * 32000 / 39926 * (np.exp(-t / 40000) - np.exp(-t / 74))
            return 1000 * (f + s)
        ef = ValueTracker(0.0)
        cur = always_redraw(lambda: VMobject(stroke_color=ORANGE, stroke_width=5).set_points_as_corners(
            [ax.c2p(a, b) for a, b in zip(t, rate(t, ef.get_value()))]))
        num = always_redraw(lambda: VGroup(Tex(r"E_f =", font_size=32), DecimalNumber(ef.get_value(), num_decimal_places=0,
                                           font_size=34, color=ORANGE), TexText(r"keV", font_size=26)).arrange(RIGHT, buff=0.1)
                            .move_to(RIGHT * 4.4 + DOWN * 0.7))
        dots = VGroup(*[Dot(radius=0.06, color=BLUE) for _ in range(40)]).arrange_in_grid(5, 8, buff=0.2).move_to(RIGHT * 4.4 + DOWN * 2.4)
        box = RoundedRectangle(corner_radius=0.1, width=2.6, height=1.0, color=TEAL).move_to(RIGHT * 4.4 + UP * 0.6)
        lab = TexText(r"shared \textbf{40 ps}", font_size=28).move_to(box)
        self.play(Write(ttl), run_time=1.0)
        self.play(Write(eq), run_time=1.5)
        self.play(ShowCreation(ax), FadeIn(num), run_time=1.0)
        self.add(cur)
        self.play(ef.animate.set_value(80), run_time=3.0)
        self.play(ef.animate.set_value(511), run_time=5.0, rate_func=smooth)
        self.play(ShowCreation(box), FadeIn(lab), run_time=1.0)
        self.play(LaggedStart(*[FadeIn(d, scale=2) for d in dots], lag_ratio=0.05), run_time=3.0)
        self.play(Indicate(lab), FlashAround(eq), run_time=1.5)
        self.play(ef.animate.set_value(0), run_time=6.0)
        self.wait(2.0)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=1.0)


class Bench3D(ThreeDScene):
    def construct(self):
        frame = self.frame
        frame.reorient(-50 + 90, 65)   # ManimGL's theta is CE's theta + 90 degrees
        axes = ThreeDAxes(x_range=[-3, 3, 1], y_range=[-3, 3, 1], z_range=[0, 2, 1], width=6, height=6, depth=2.4)
        surf = ParametricSurface(lambda u, v: axes.c2p(u, v, 1.6 * np.exp(-(u * u + v * v) / 1.5)), u_range=[-3, 3],
                                 v_range=[-3, 3], resolution=(40, 40), color=BLUE_D, opacity=0.85)
        mesh = SurfaceMesh(surf, resolution=(41, 41), stroke_width=0.4)
        crystals = Group(*[Prism(0.5, 0.5, 1.4, color=TEAL, opacity=0.8).move_to(
            axes.c2p(2.4 * np.cos(a), 2.4 * np.sin(a), 0.7)) for a in np.linspace(0, 2 * PI, 12, endpoint=False)])
        ball = Sphere(radius=0.3, resolution=(24, 24), color=ORANGE).move_to(axes.c2p(0, 0, 2.2))
        self.play(ShowCreation(axes), run_time=1.0)
        self.play(ShowCreation(surf), ShowCreation(mesh), run_time=2.0)
        self.play(LaggedStart(*[FadeIn(c) for c in crystals], lag_ratio=0.1), run_time=2.0)
        self.play(FadeIn(ball), run_time=0.5)
        self.play(frame.animate.reorient(30 + 90, 40), run_time=5.0)
        spin = lambda m, dt: m.increment_theta(0.4 * dt)
        frame.add_updater(spin)
        self.play(ball.animate.move_to(axes.c2p(1.5, 1.0, 0.8)), run_time=4.0)
        self.wait(3.0)
        frame.remove_updater(spin)
        self.play(FadeOut(surf), FadeOut(mesh), FadeOut(ball), run_time=1.0)
        self.wait(1.0)
