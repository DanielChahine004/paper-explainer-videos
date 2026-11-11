# A 3D scene body for both engines (bench3d_ce.py / bench3d_gx.py exec it): a shaded surface, axes, solids and a
# moving camera, ~20 s at 1080p60. The kind of scene the explainers use for detector geometry.
class Bench3D(ThreeDScene):
    def construct(self):
        import numpy as np
        self.set_camera_orientation(phi=65 * DEGREES, theta=-50 * DEGREES)
        axes = ThreeDAxes(x_range=[-3, 3, 1], y_range=[-3, 3, 1], z_range=[0, 2, 1], x_length=6, y_length=6, z_length=2.4)
        surf = Surface(lambda u, v: axes.c2p(u, v, 1.6 * np.exp(-(u * u + v * v) / 1.5)), u_range=[-3, 3], v_range=[-3, 3],
                       resolution=(40, 40), fill_opacity=0.85, checkerboard_colors=[BLUE_D, BLUE_E], stroke_width=0.4)
        crystals = VGroup(*[Prism(dimensions=[0.5, 0.5, 1.4], fill_color=TEAL, fill_opacity=0.8).move_to(
            axes.c2p(2.4 * np.cos(a), 2.4 * np.sin(a), 0.7)) for a in np.linspace(0, 2 * PI, 12, endpoint=False)])
        ball = Sphere(radius=0.3, resolution=(24, 24)).set_color(ORANGE).move_to(axes.c2p(0, 0, 2.2))
        self.play(Create(axes), run_time=1.0)
        self.play(Create(surf), run_time=2.0)
        self.play(LaggedStart(*[FadeIn(c) for c in crystals], lag_ratio=0.1), run_time=2.0)
        self.play(FadeIn(ball), run_time=0.5)
        self.move_camera(phi=40 * DEGREES, theta=30 * DEGREES, run_time=5.0)
        self.begin_ambient_camera_rotation(rate=0.4)
        self.play(ball.animate.move_to(axes.c2p(1.5, 1.0, 0.8)), run_time=4.0)
        self.wait(3.0)
        self.stop_ambient_camera_rotation()
        self.play(FadeOut(surf), FadeOut(ball), run_time=1.0)
        self.wait(1.0)
