"""Explainer (technical version): Walk-Through PET (WT-PET), Ghent University MEDISIP (Vandenberghe).

Source: the WT-PET literature-review note on the programme, with numbers and methods checked against
Vandenberghe et al. 2020 (EJNMMI Phys) and 2023 (EJNMMI), Dadgar et al. 2023, Abi-Akl et al. 2023 and 2025
(EJNMMI Phys) and Dhaenens, Vervenne et al. 2026 (Front Phys).
The cost figures are recomputed from the 2023 paper's own cost model (Table 3). The sinogram coverage maps are
computed here with the 2026 paper's method (which transverse lines of response can hit both panels) for its stated
panel sizes and motion ranges. Every drawing is new; the patient, the Gaussian clouds and the voxel weights are
schematic. Visuals are cued to the narration with <bookmark/> tags and self.at() (see ../DESIGN.md).
Render with render.sh, or one scene: manim -ql wt_vo.py Coverage
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import *  # noqa: E402,F401

PANEL_C, CYL_C, GAM_C, PERSON_C, BLOCK_C, SIPM_C = "#4c8fe0", "#9aa4b2", "#7ee081", "#d9c8b4", "#7fb3ff", "#3b6fd1"
CITE = r"Vandenberghe group \textperiodcentered\ MEDISIP, Ghent University \textperiodcentered\ wt-pet.org"
U = 0.05            # scene units per cm in the 3D scenes


def flat(*mobs):
    """Keep 2D overlays (lines, dots) out of the 3D depth sort so they draw on top (DESIGN.md, 3D draw order)."""
    for m in mobs:
        for s in m.get_family():
            s.shade_in_3d = False
    return mobs[0] if len(mobs) == 1 else mobs


def panel3d(width_cm, height_cm, y0=0.0, x=1.3, color=PANEL_C, grid=None, opacity=0.45):
    """A vertical flat panel (x = thickness, y = width, z = height), optional block grid lines on its inner face."""
    p = Prism(dimensions=[0.22, width_cm * U, height_cm * U], fill_color=color, fill_opacity=opacity,
              stroke_color=BLOCK_C, stroke_width=0.6).move_to([x, y0, 0])
    if grid:
        nc, nr = grid
        xf = x - np.sign(x) * 0.115
        w, h = width_cm * U, height_cm * U
        lines = VGroup(*[Line([xf, y0 - w / 2 + k * w / nc, -h / 2], [xf, y0 - w / 2 + k * w / nc, h / 2], stroke_width=0.6, color=BLOCK_C)
                         for k in range(nc + 1)],
                       *[Line([xf, y0 - w / 2, -h / 2 + k * h / nr], [xf, y0 + w / 2, -h / 2 + k * h / nr], stroke_width=0.6, color=BLOCK_C)
                         for k in range(nr + 1)])
        return VGroup(p, lines)
    return p


def patient3d(h=3.4):
    body = Cylinder(radius=0.42, height=h * 0.72, direction=OUT, resolution=(4, 16), fill_color=PERSON_C, fill_opacity=0.7,
                    stroke_width=0, checkerboard_colors=False).move_to([0, 0, -h * 0.5 + h * 0.36])
    head = Sphere(radius=0.26, resolution=(8, 12), fill_color=PERSON_C, fill_opacity=0.8, stroke_width=0,
                  checkerboard_colors=False).move_to([0, 0, -h * 0.5 + h * 0.72 + 0.3])
    return VGroup(body, head)


def person(h=2.4, color=PERSON_C):
    head = Circle(radius=0.11 * h, color=color, stroke_width=3).move_to(np.array([0, 0.89 * h, 0]))
    body = Line(np.array([0, 0.78 * h, 0]), np.array([0, 0.42 * h, 0]), color=color, stroke_width=3)
    arms = VGroup(Line(np.array([0, 0.7 * h, 0]), np.array([-0.18 * h, 0.48 * h, 0]), color=color, stroke_width=3),
                  Line(np.array([0, 0.7 * h, 0]), np.array([0.18 * h, 0.48 * h, 0]), color=color, stroke_width=3))
    legs = VGroup(Line(np.array([0, 0.42 * h, 0]), np.array([-0.12 * h, 0, 0]), color=color, stroke_width=3),
                  Line(np.array([0, 0.42 * h, 0]), np.array([0.12 * h, 0, 0]), color=color, stroke_width=3))
    return VGroup(head, body, arms, legs)


def coverage(panels, R=45.0, nr=150, nt=180, gap=50.0):
    """Which transverse lines of response (r, theta) hit both panels (Dhaenens 2026, Sec. 2.2.1).
    panels: list of ((c1, w1), (c2, w2)) panel-pair positions (centre, width in cm) over the motion; the union is returned.
    Panels sit at x = +gap/2 and -gap/2 and extend along y."""
    r = np.linspace(-R, R, nr)[:, None]
    th = np.linspace(0.5, 179.5, nt)[None, :] * DEGREES
    s, c = np.sin(th), np.cos(th)
    y1 = (r - gap / 2 * c) / s
    y2 = (r + gap / 2 * c) / s
    m = np.zeros((nr, nt), bool)
    for (c1, w1), (c2, w2) in panels:
        m |= (np.abs(y1 - c1) <= w1 / 2) & (np.abs(y2 - c2) <= w2 / 2)
    return m


def mask_image(m, h=2.0, w=2.4):
    img = np.zeros((*m.shape, 3), np.uint8)
    img[...] = (28, 32, 44)
    img[m] = (46, 196, 182)
    im = ImageMobject(img[::-1])
    im.set_resampling_algorithm(RESAMPLING_ALGORITHMS["nearest"])
    im.stretch_to_fit_height(h).stretch_to_fit_width(w)
    return Group(im, SurroundingRectangle(im, buff=0, color=GREY_B, stroke_width=1))


class Opening(Narrated, ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=72 * DEGREES, theta=-35 * DEGREES, zoom=0.72)
        p1 = panel3d(70, 106, x=-1.36, grid=(14, 20))
        p2 = panel3d(70, 106, x=1.36, grid=(14, 20))
        pat = patient3d()
        rng = np.random.default_rng(2)
        lors = VGroup()
        for _ in range(9):
            src = np.array([rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), rng.uniform(-1.2, 1.4)])
            d = rng.normal(size=3)
            d[0] = np.sign(d[0] or 1) * (abs(d[0]) + 1.2)
            d /= np.linalg.norm(d)
            t = 1.25 / abs(d[0])
            lors.add(Line(src - t * d, src + t * d, color=GAM_C, stroke_width=2))
        flat(lors)
        title = Tex("Walk-Through PET").scale(1.1).to_edge(UP, buff=0.35)
        foot = Tex(CITE, color=TEAL_L).scale(0.5).to_edge(DOWN, buff=0.3)
        self.add_fixed_in_frame_mobjects(title, foot)
        self.remove(title, foot)
        with self.voiceover(text="Ghent University's walk through PET puts a <bookmark mark='pat'/>standing patient between "
                                 "<bookmark mark='pan'/>two flat panels of monolithic detectors, seventy by a hundred and six centimetres, "
                                 "fifty centimetres apart. Every <bookmark mark='lor'/>line of response runs from one panel to the "
                                 "other."):
            self.play(Write(title), FadeIn(foot), run_time=1.0)
            self.at("pat", FadeIn(pat))
            self.at("pan", FadeIn(p1), FadeIn(p2), run_time=1.0)
            self.begin_ambient_camera_rotation(rate=0.12)
            self.at("lor", LaggedStart(*[Create(l) for l in lors], lag_ratio=0.15), run_time=1.5)
        with self.voiceover(text="This video goes through the six papers behind it, with the methods: how the system was sized and "
                                 "costed, how the detectors were modelled, how the images were reconstructed, and what the geometry "
                                 "costs in angular sampling."):
            self.wait(max(0.1, 1.0))
        self.stop_ambient_camera_rotation()
        self.play(*[FadeOut(m) for m in (p1, p2, pat, lors, title, foot)])


class Sizing(Narrated):
    def construct(self):
        title = Tex("Sizing and costing the system (2023)").scale(0.72).to_edge(UP)
        sz = VGroup(Tex(r"sized from \textbf{40} PET-CT patients", font_size=26),
                    Tex(r"\textbf{70 $\times$ 106 cm} panels, \textbf{50 cm} gap", font_size=26, color=YELLOW),
                    Tex(r"\textbf{14 $\times$ 20} blocks per panel", font_size=26)
                    ).arrange(DOWN, aligned_edge=LEFT, buff=0.12).next_to(title, DOWN, buff=0.35).to_edge(LEFT, buff=0.6)
        model = VGroup(MathTex(r"C_{\text{scint}} = V \times p_V", r"\quad p_V = 30\ \text{EUR/cm}^3\ (\text{LSO}),\ 10\ (\text{BGO})", font_size=32),
                       MathTex(r"C_{\text{SiPM}} = \frac{A}{25\ \text{cm}^2} \times 1000\ \text{EUR}", r"\quad (8\times8\ \text{SiPMs of}\ 6\ \text{mm})", font_size=32)
                       ).arrange(DOWN, aligned_edge=LEFT, buff=0.25).next_to(sz, DOWN, buff=0.45).align_to(sz, LEFT)
        fit_frame(VGroup(sz, model))
        with self.voiceover(text="The 2023 design paper starts from patients. <bookmark mark='ct'/>Forty random P E T C T scans gave the "
                                 "height from head to thigh, the shoulder width and the body depth, which set the <bookmark mark='dim'/>"
                                 "panel size and the fifty centimetre gap, filled with <bookmark mark='blk'/>fourteen by twenty monolithic "
                                 "blocks per panel. Cost is then estimated from the two dominant components: "
                                 "<bookmark mark='sc'/>scintillator volume times a price per cubic centimetre, thirty euros for L S O and "
                                 "ten for B G O, and <bookmark mark='si'/>SiPM area at a thousand euros per five by five centimetre "
                                 "module. Electronics are left out."):
            self.play(Write(title), run_time=0.8)
            self.at("ct", FadeIn(sz[0]))
            self.at("dim", FadeIn(sz[1]))
            self.at("blk", FadeIn(sz[2]))
            self.at("sc", Write(model[0]))
            self.at("si", Write(model[1]))
        ax = Axes(x_range=[0, 3000, 1000], y_range=[0, 4, 1], x_length=5.6, y_length=2.4, tips=False,
                  axis_config={"color": GREY_B, "include_ticks": False}).to_edge(RIGHT, buff=0.9).to_edge(DOWN, buff=0.75)
        rows = [("26 cm cylinder (LSO)", 417, 278), ("106 cm cylinder (LSO)", 1666, 1112), ("walk-through, BGO", 237, 593), ("walk-through, LYSO", 711, 593)]
        bars = VGroup()
        for k, (lab, s, p) in enumerate(rows):
            y = 3.5 - k
            b1 = Rectangle(width=ax.c2p(s, 0)[0] - ax.c2p(0, 0)[0], height=0.45, fill_color=BLOCK_C, fill_opacity=0.9, stroke_width=0)
            b1.move_to(ax.c2p(0, y), aligned_edge=LEFT)
            b2 = Rectangle(width=ax.c2p(p, 0)[0] - ax.c2p(0, 0)[0], height=0.45, fill_color=YELLOW, fill_opacity=0.8, stroke_width=0)
            b2.next_to(b1, RIGHT, buff=0)
            bars.add(VGroup(b1, b2, Tex(lab, font_size=22).next_to(b1, LEFT, buff=0.12).set_x(ax.c2p(0, 0)[0] - 0.12, direction=RIGHT),
                            Tex(f"{s + p:,} kEUR".replace(",", "{,}"), font_size=22).next_to(b2, RIGHT, buff=0.08)))
        key = VGroup(VGroup(Square(0.16, fill_color=BLOCK_C, fill_opacity=1, stroke_width=0), Tex("scintillator", font_size=22)).arrange(RIGHT, buff=0.08),
                     VGroup(Square(0.16, fill_color=YELLOW, fill_opacity=1, stroke_width=0), Tex("SiPMs", font_size=22)).arrange(RIGHT, buff=0.08)
                     ).arrange(RIGHT, buff=0.35).next_to(ax, UP, buff=0.12)
        fit_frame(VGroup(ax, bars, key))
        res = Tex(r"BGO panels: \textbf{3.3$\times$} below 106 cm, \textbf{1.2$\times$} a 26 cm scanner", font_size=24, color=YELLOW).to_edge(DOWN, buff=0.2)
        with self.voiceover(text="Applied to each system, that gives about <bookmark mark='b0'/>seven hundred thousand euros for a twenty "
                                 "six centimetre scanner, <bookmark mark='b1'/>two point eight million for a hundred and six centimetre "
                                 "cylinder, and <bookmark mark='b2'/>about eight hundred and thirty thousand for walk through panels in B G O: "
                                 "<bookmark mark='r'/>three point three times less than the long cylinder, and only twenty percent more "
                                 "than the short one. In <bookmark mark='b3'/>L Y S O it is about one point three million."):
            self.at("b0", Create(ax), FadeIn(key), *[FadeIn(m) for m in bars[0]])
            self.at("b1", *[FadeIn(m) for m in bars[1]])
            self.at("b2", *[FadeIn(m) for m in bars[2]])
            self.at("r", FadeIn(res))
            self.at("b3", *[FadeIn(m) for m in bars[3]])
        fade_all(self)


class Throughput(Narrated):
    def construct(self):
        title = Tex("Throughput: where the time goes").scale(0.72).to_edge(UP)
        method = VGroup(Tex(r"handling timed: \textbf{1 day}, Vision 600", font_size=26),
                        Tex(r"CT, positioning, transfer", font_size=24, color=GREY_B),
                        Tex(r"scan time scaled by sensitivity, TOF", font_size=26),
                        Tex(r"all lines kept: \textbf{152} kcps/MBq", font_size=26)
                        ).arrange(DOWN, aligned_edge=LEFT, buff=0.12).next_to(title, DOWN, buff=0.4).to_edge(LEFT, buff=0.6)
        fit_frame(method)
        with self.voiceover(text="Throughput was estimated, not assumed. The group <bookmark mark='m0'/>timed a full day of patient handling "
                                 "on a conventional scanner, from C T and scout scan to positioning on the bed. Acquisition times were "
                                 "then <bookmark mark='m2'/>scaled by each design's sensitivity and time of flight resolution. For the "
                                 "panels, the simulated sensitivity of a hundred and fifty two kilo counts per second per megabecquerel "
                                 "uses <bookmark mark='m3'/>every line of response, because depth of interaction removes the blur of "
                                 "oblique lines."):
            self.play(Write(title), run_time=0.8)
            self.at("m0", FadeIn(method[0]), FadeIn(method[1]))
            self.at("m2", FadeIn(method[2]))
            self.at("m3", FadeIn(method[3]))
        ax = Axes(x_range=[0, 100, 20], y_range=[0, 3, 1], x_length=5.0, y_length=2.1, tips=False,
                  axis_config={"color": GREY_B, "include_ticks": False}).to_edge(RIGHT, buff=0.9).to_edge(DOWN, buff=0.8)
        rows = [("26 cm cylinder", 28, CYL_C), ("106 cm cylinder", 60, CYL_C), ("walk-through", 87, PANEL_C)]
        bars = VGroup()
        for k, (lab, v, col) in enumerate(rows):
            b = Rectangle(width=ax.c2p(v, 0)[0] - ax.c2p(0, 0)[0], height=0.45, fill_color=col, fill_opacity=0.9, stroke_width=0)
            b.move_to(ax.c2p(0, 2.5 - k), aligned_edge=LEFT)
            bars.add(VGroup(b, Tex(lab, font_size=24).next_to(b, LEFT, buff=0.12).set_x(ax.c2p(0, 0)[0] - 0.12, direction=RIGHT),
                            Tex(("53--60" if v == 60 else str(v)), font_size=24).next_to(b, RIGHT, buff=0.08)))
        pl = Tex(r"patients per 8-hour day", font_size=24).next_to(ax, UP, buff=0.12)
        fit_frame(VGroup(ax, bars, pl))
        dose = Tex(r"or \textbf{66\%} less tracer per patient", font_size=24, color=YELLOW).to_edge(DOWN, buff=0.2)
        with self.voiceover(text="The estimate: <bookmark mark='b0'/>twenty eight patients a day on a short scanner, "
                                 "<bookmark mark='b1'/>fifty three to sixty on a long cylinder, and <bookmark mark='b2'/>eighty seven walking "
                                 "through the panels. Or, keeping the patient count, <bookmark mark='d'/>two thirds less tracer ordered per "
                                 "patient."):
            self.at("b0", Create(ax), FadeIn(pl), *[FadeIn(m) for m in bars[0]])
            self.at("b1", *[FadeIn(m) for m in bars[1]])
            self.at("b2", *[FadeIn(m) for m in bars[2]])
            self.at("d", FadeIn(dose))
        fade_all(self)


class Block(Narrated, ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=64 * DEGREES, theta=-50 * DEGREES, zoom=1.35)
        s = 2.6
        hz = s * 16 / 50
        crys = Prism(dimensions=[s, s, hz], fill_color=BLOCK_C, fill_opacity=0.18, stroke_width=0).move_to([0, 0, 0.3])
        zb = 0.3 - s * 8 / 50
        cx = [np.array([sx * s / 2, sy * s / 2, z]) for z in (zb, zb + hz) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        edges = VGroup(*[Line(cx[a], cx[b], color=BLOCK_C, stroke_width=2)
                         for a, b in [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]])
        sipms = VGroup(*[Square(s / 8 * 0.9, fill_color=SIPM_C, fill_opacity=0.95, stroke_width=0).move_to([(-3.5 + i) * s / 8, (-3.5 + j) * s / 8, zb - 0.02])
                         for i in range(8) for j in range(8)])
        layers = VGroup(*[Rectangle(width=s, height=s, stroke_color=YELLOW, stroke_width=1.3).move_to([0, 0, zb + (k + 1) * hz / 6])
                          for k in range(5)])
        p = np.array([0.35, -0.2, 0.42])
        rng = np.random.default_rng(5)
        sig = np.array([0.55, 0.55, 0.85]) * 0.35           # sigma in mm, drawn 0.35 units per mm (exaggerated)
        lo, hi = np.array([-s / 2, -s / 2, zb]), np.array([s / 2, s / 2, zb + hz])
        cloud = VGroup(*[Dot(np.clip(p + rng.normal(size=3) * sig, lo, hi), radius=0.03, color=YELLOW) for _ in range(70)])   # clamped, as in the papers
        ell = Sphere(radius=1, resolution=(10, 16), fill_color=YELLOW, fill_opacity=0.18, stroke_width=0, checkerboard_colors=False)
        ell.stretch(2 * sig[0], 0).stretch(2 * sig[1], 1).stretch(2 * sig[2], 2).move_to(p)
        truth = Dot(p, radius=0.07, color=RED)
        # The camera always looks down on the block, so draw in physical order instead of the 3D depth sort
        # (which put the flat SiPM squares over the cloud): SiPMs under the crystal, then the translucent
        # crystal, the depth layers, the cloud, and the crystal's outline last (re-raised after each step).
        flat(crys, edges, sipms, layers, ell, cloud, truth)
        info = VGroup(Tex(r"monolithic, \textbf{50 $\times$ 50 $\times$ 16 mm}", font_size=26),
                      Tex(r"\textbf{8 $\times$ 8} SiPMs, 6 mm", font_size=26, color=SIPM_C),
                      Tex(r"\textbf{6} DOI layers", font_size=26, color=YELLOW)).arrange(DOWN, aligned_edge=LEFT, buff=0.1).to_corner(UR, buff=0.4)
        meth = VGroup(Tex(r"GATE: true interaction point", font_size=26),
                      Tex(r"3D Gaussian: $\sigma_{xy}$ \textbf{0.55}, $\sigma_z$ \textbf{0.85} mm", font_size=26, color=YELLOW),
                      Tex(r"LYSO: \textbf{1.14} / \textbf{2.67} mm FWHM", font_size=24, color=GREY_B),
                      Tex(r"clamped to the crystal", font_size=24, color=GREY_B)
                      ).arrange(DOWN, aligned_edge=LEFT, buff=0.1).to_corner(DL, buff=0.35)
        ex = Tex("cloud exaggerated", font_size=22, color=GREY_D).to_edge(RIGHT, buff=0.3).shift(0.6 * UP)
        fit_frame(info)
        fit_frame(meth)
        self.add_fixed_in_frame_mobjects(info, meth, ex)
        self.remove(info, meth, ex)
        with self.voiceover(text="Each block is a <bookmark mark='c'/>single crystal, five by five centimetres and sixteen millimetres thick, "
                                 "read by an <bookmark mark='s'/>eight by eight array of six millimetre SiPMs. The group's measured block "
                                 "resolves depth in <bookmark mark='l'/>six layers."):
            self.at("c", FadeIn(crys), FadeIn(edges), FadeIn(info[0]))
            self.wait_until_bookmark("s")
            self.add(sipms)
            self.bring_to_front(crys, edges)                  # SiPMs sit under the crystal
            sipms.set_opacity(0)
            self.play(sipms.animate.set_opacity(0.95), FadeIn(info[1]), run_time=0.7)
            self.at("l", Create(layers), FadeIn(info[2]))
            self.bring_to_front(edges)
            self.begin_ambient_camera_rotation(rate=0.1)
        with self.voiceover(text="In the system simulations, the detector is not simulated photon by photon. GATE reports the "
                                 "<bookmark mark='t'/>exact interaction point, energy weighted when a gamma scatters inside the block, and "
                                 "it is then <bookmark mark='g'/>smeared with a three dimensional Gaussian: sigma of zero point five five "
                                 "millimetres across the face and zero point eight five in depth for B G O, the block's measured average. "
                                 "The L Y S O papers use one point one four and two point six seven millimetres full width. Points pushed "
                                 "<bookmark mark='e'/>outside the crystal are clamped to its edge."):
            self.at("t", FadeIn(truth), FadeIn(meth[0]))
            self.at("g", FadeIn(ell), LaggedStart(*[FadeIn(d) for d in cloud], lag_ratio=0.01), FadeIn(meth[1]), FadeIn(meth[2]), FadeIn(ex), run_time=1.4)
            self.bring_to_front(truth, edges)
            self.at("e", FadeIn(meth[3]))
        vary = Tex(r"edge model (2025): \textbf{1.02 $\to$ 1.35 mm}; DOI \textbf{2.4 / 3.7 mm}", font_size=26, color=TEAL_L)
        vary.scale_to_fit_width(min(vary.width, 13.0)).to_edge(DOWN, buff=0.12)
        self.add_fixed_in_frame_mobjects(vary)
        self.remove(vary)
        self.stop_ambient_camera_rotation()
        with self.voiceover(text="A uniform Gaussian ignores edges. So the 2025 paper also tried a <bookmark mark='v'/>spatially varying "
                                 "model: one point zero two millimetres in the centre, worsening to one point three five at the edges, and "
                                 "poorer depth resolution in the two layers nearest the SiPMs."):
            self.at("v", FadeOut(meth[3]), FadeIn(vary))
        self.play(*[FadeOut(m) for m in (crys, edges, sipms, layers, cloud, ell, truth, info, meth, ex, vary)])


class Recon(Narrated):
    def construct(self):
        title = Tex("Reconstruction: list-mode (TOF-)MLEM").scale(0.72).to_edge(UP)
        n, sz = 9, 0.42
        grid = VGroup(*[Square(sz, stroke_width=0.8, stroke_color=GREY_D) for _ in range(n * n)]).arrange_in_grid(n, n, buff=0)
        grid.move_to(4.0 * LEFT + 0.6 * DOWN)
        a = grid.get_corner(DL) + np.array([-0.4, 0.5, 0])
        b = grid.get_corner(UR) + np.array([0.4, -0.9, 0])
        lor = Line(a, b, color=GAM_C, stroke_width=3)
        u = (b - a) / np.linalg.norm(b - a)
        mid = a + 0.55 * (b - a)
        weights = VGroup()
        for sq in grid:
            q = sq.get_center()
            dist = np.linalg.norm(np.cross(np.append((q - a)[:2], 0), np.append(u[:2], 0)))
            along = np.dot(q - mid, u)
            wv = np.exp(-dist ** 2 / (2 * 0.12 ** 2)) * np.exp(-along ** 2 / (2 * 0.6 ** 2))
            if wv > 0.03:
                weights.add(sq.copy().set_fill(YELLOW, opacity=0.85 * wv).set_stroke(width=0))
        eq = MathTex(r"\lambda_j^{(k+1)}", r"=", r"\frac{\lambda_j^{(k)}}{s_j}", r"\sum_{i\,\in\,\text{events}}",
                     r"\frac{a_{ij}^{\text{TOF}}}{\sum_l a_{il}^{\text{TOF}}\,\lambda_l^{(k)}}", font_size=40).to_edge(RIGHT, buff=0.5).shift(1.6 * UP)
        terms = VGroup(Tex(r"$a_{ij}^{\text{TOF}}$: line $\times$ TOF kernel", font_size=24),
                       Tex(r"$s_j$: sensitivity image", font_size=24),
                       Tex(r"list mode: sum over events", font_size=24)
                       ).arrange(DOWN, aligned_edge=LEFT, buff=0.12).next_to(eq, DOWN, buff=0.35)
        fit_frame(VGroup(eq, terms))
        with self.voiceover(text="The simulation studies reconstruct with list mode maximum likelihood expectation maximisation, M L E M, "
                                 "with time of flight for the image studies. Each <bookmark mark='ev'/>recorded event defines a line. Its "
                                 "<bookmark mark='a'/>system weights are the voxels along that line, multiplied by the time of flight "
                                 "kernel, so the voxels near the timing estimate count most. The update <bookmark mark='eq'/>compares the "
                                 "events with the current image projected along each line, and divides by the <bookmark mark='s'/>"
                                 "sensitivity image, which is how the limited panel geometry enters the reconstruction."):
            self.play(Write(title), FadeIn(grid), run_time=0.8)
            self.at("ev", Create(lor))
            self.at("a", FadeIn(weights), FadeIn(terms[0]))
            self.at("eq", Write(eq), FadeIn(terms[2]))
            self.at("s", FadeIn(terms[1]), Indicate(eq[2], color=YELLOW))
        impl = VGroup(Tex(r"QETIR (C++): \textbf{10} iterations, 0.5 mm voxels", font_size=24),
                      Tex(r"PETRecon (Julia, GPU)", font_size=24),
                      Tex(r"no regularisation, no PSF model", font_size=24, color=YELLOW)
                      ).arrange(DOWN, aligned_edge=LEFT, buff=0.12).to_edge(DOWN, buff=0.35)
        fit_frame(impl)
        with self.voiceover(text="The codes are in house: <bookmark mark='q'/>Q E T I R, in C plus plus, run with no subsets and ten "
                                 "iterations, and later <bookmark mark='p'/>PET Recon, written in Julia for the GPU. With <bookmark mark='n'/>"
                                 "no regularisation and no resolution model, whatever the geometry does shows up directly in the "
                                 "images."):
            self.at("q", FadeIn(impl[0]))
            self.at("p", FadeIn(impl[1]))
            self.at("n", FadeIn(impl[2]))
        fade_all(self)


class Coverage(Narrated):
    def construct(self):
        title = Tex("Which angles can two panels measure?").scale(0.72).to_edge(UP)
        c = 4.1 * LEFT + 0.5 * DOWN
        sc = 0.045
        top = VGroup(Line(c + np.array([-25 * sc, -35 * sc, 0]), c + np.array([-25 * sc, 35 * sc, 0]), color=PANEL_C, stroke_width=8),
                     Line(c + np.array([25 * sc, -35 * sc, 0]), c + np.array([25 * sc, 35 * sc, 0]), color=PANEL_C, stroke_width=8))
        tl = Tex(r"top view: panels 50 cm apart", font_size=24).next_to(top, DOWN, buff=0.3)
        th = 35 * DEGREES
        ex_lor = Line(c - 1.6 * np.array([np.cos(th), np.sin(th), 0]), c + 1.6 * np.array([np.cos(th), np.sin(th), 0]), color=GAM_C, stroke_width=3)
        par = DashedLine(c + np.array([0, -1.8, 0]), c + np.array([0, 1.8, 0]), color=RED, stroke_width=3)
        m_wt = coverage([((0, 70), (0, 70))])
        img = mask_image(m_wt, h=2.6, w=3.4).move_to(1.5 * RIGHT + 0.3 * DOWN)
        xl = Tex(r"angle $\theta$ (0--180$^\circ$)", font_size=22).next_to(img, DOWN, buff=0.12)
        yl = Tex(r"offset $r$ ($\pm$45 cm)", font_size=22).rotate(PI / 2).next_to(img, LEFT, buff=0.12)
        il = Tex(r"recordable lines, static panels", font_size=24, color=TEAL_L).next_to(img, UP, buff=0.15)
        expl = VGroup(Tex(r"line $\to$ point $(r, \theta)$", font_size=24),
                      Tex(r"dark: parallel to the panels", font_size=24, color=RED),
                      Tex(r"$\Rightarrow$ elongation $\perp$ panels", font_size=24, color=RED)
                      ).arrange(DOWN, aligned_edge=LEFT, buff=0.1).to_edge(DOWN, buff=0.3).shift(1.6 * RIGHT)
        fit_frame(expl)
        with self.voiceover(text="The key analysis comes from the 2026 paper. In the transverse plane, every line of response is a point "
                                 "in the <bookmark mark='sino'/>sinogram: its angle and its offset from the centre. A line counts only if "
                                 "it <bookmark mark='hit'/>hits both panels. Computing that for every line gives this map. The "
                                 "<bookmark mark='band'/>dark bands are the lines running nearly parallel to the panels, which are "
                                 "<bookmark mark='par'/>never recorded, and that missing range of angles is what stretches images "
                                 "<bookmark mark='el'/>perpendicular to the panels."):
            self.play(Write(title), Create(top), FadeIn(tl), run_time=0.9)
            self.at("sino", FadeIn(img), FadeIn(xl), FadeIn(yl), FadeIn(expl[0]))
            self.at("hit", Create(ex_lor), FadeIn(il))
            self.at("band", FadeIn(expl[1]))
            self.at("par", Create(par))
            self.at("el", FadeIn(expl[2]))
        res = Tex(r"NEMA: \textbf{$<$2 mm} $\parallel$, \textbf{3.36 mm} $\perp$", font_size=24, color=YELLOW).next_to(il, UP, buff=0.2)
        fit_frame(res)
        with self.voiceover(text="The 2023 B G O simulation measured exactly this with N E M A point sources in a warm background: "
                                 "<bookmark mark='r'/>under two millimetres parallel to the panels, but up to three point three six "
                                 "perpendicular, worst near a panel."):
            self.at("r", FadeIn(res))
        fade_all(self)


class Timing(Narrated):
    def construct(self):
        title = Tex("How time of flight helps").scale(0.72).to_edge(UP)
        c = 3.4 * LEFT + 0.4 * DOWN
        p1 = Rectangle(width=0.3, height=4.6, fill_color=PANEL_C, fill_opacity=0.6, stroke_color=PANEL_C).move_to(c + 1.8 * LEFT)
        p2 = p1.copy().move_to(c + 1.8 * RIGHT)
        src = c + 0.6 * LEFT + 0.2 * UP
        a, b = np.array([p1.get_right()[0], src[1] - 0.15, 0]), np.array([p2.get_left()[0], src[1] + 0.15, 0])
        lor = Line(a, b, color=GAM_C, stroke_width=3)
        sd = Dot(src, color=RED, radius=0.07)
        ta = Tex(r"$t_1$", font_size=30, color=YELLOW).next_to(a, LEFT, buff=0.35)
        tb = Tex(r"$t_2$", font_size=30, color=YELLOW).next_to(b, RIGHT, buff=0.35)
        u = (b - a) / np.linalg.norm(b - a)
        nrm = np.array([-u[1], u[0], 0])
        kern = VMobject(stroke_color=YELLOW, stroke_width=3).set_points_smoothly(
            [src + s * u + 0.9 * np.exp(-s ** 2 / (2 * 0.32 ** 2)) * nrm for s in np.linspace(-1.2, 1.2, 40)])
        eq = MathTex(r"\Delta x = \frac{c\,(t_2 - t_1)}{2}", font_size=40).to_edge(RIGHT, buff=1.2).shift(1.8 * UP)
        pts = VGroup(Tex(r"300 ps $\to$ \textbf{4.5 cm}", font_size=26),
                     Tex(r"BGO: \textbf{600 ps} assumed (bench \textbf{327})", font_size=24, color=GREY_B),
                     Tex(r"kernel lies across the gap", font_size=26),
                     Tex(r"$\Rightarrow$ constrains the stretched axis", font_size=26, color=TEAL_L),
                     Tex(r"every paper: want $<$\textbf{300 ps}", font_size=26, color=YELLOW)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.14).next_to(eq, DOWN, buff=0.45)
        fit_frame(VGroup(eq, pts))
        with self.voiceover(text="Time of flight is the main lever against those missing angles. The arrival time difference "
                                 "<bookmark mark='t'/>between the two panels, <bookmark mark='eq'/>times the speed of light and halved, "
                                 "places the event along its line. At <bookmark mark='k'/>three hundred picoseconds for L Y S O, that is "
                                 "about four and a half centimetres. For B G O the papers assume a more conservative "
                                 "<bookmark mark='bgo'/>six hundred picoseconds, using Cherenkov light, though the bench block reached "
                                 "three hundred and twenty seven."):
            self.play(Write(title), FadeIn(p1), FadeIn(p2), Create(lor), FadeIn(sd), run_time=1.0)
            self.at("t", FadeIn(ta), FadeIn(tb))
            self.at("eq", Write(eq))
            self.at("k", Create(kern), FadeIn(pts[0]))
            self.at("bgo", FadeIn(pts[1]))
        with self.voiceover(text="Because lines between two panels run <bookmark mark='x'/>across the gap, the timing kernel lies along "
                                 "<bookmark mark='str'/>exactly the direction the missing angles blur. Four and a half centimetres is "
                                 "still coarse next to millimetre voxels, so <bookmark mark='b'/>every paper ends asking for faster "
                                 "timing."):
            self.at("x", FadeIn(pts[2]), Indicate(lor, color=YELLOW))
            self.at("str", FadeIn(pts[3]))
            self.at("b", FadeIn(pts[4]), kern.animate.stretch(0.5, 0, about_point=src).stretch(1.5, 1, about_point=src), run_time=1.0)
        fade_all(self)


class Ring(Narrated, ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=66 * DEGREES, theta=-60 * DEGREES, zoom=0.9)
        R, n, nr = 1.75, 40, 7
        dz = 0.26
        blocks = VGroup()
        for k in range(nr):
            for i in range(n):
                a = i * TAU / n
                blocks.add(Prism(dimensions=[0.3, 2 * PI * R / n * 0.92, dz * 0.92], fill_color=PANEL_C, fill_opacity=0.5, stroke_width=0.3,
                                 stroke_color=BLOCK_C).rotate(a, axis=OUT).move_to([(R + 0.15) * np.cos(a), (R + 0.15) * np.sin(a), (k - 3) * dz]))
        info = VGroup(Tex(r"\textbf{40} blocks per ring, 70 cm bore", font_size=26),
                      Tex(r"\textbf{7} or \textbf{14} rings", font_size=26),
                      Tex(r"NEMA NU 2-2018 in GATE", font_size=24, color=GREY_B),
                      Tex(r"11.5\%, 440--650 keV, 3 ns", font_size=24, color=GREY_B),
                      Tex(r"TOF-MLEM, \textbf{200 ps}", font_size=24, color=GREY_B)
                      ).arrange(DOWN, aligned_edge=LEFT, buff=0.1).to_corner(UL, buff=0.35)
        res = VGroup(Tex(r"\textbf{$<$2 mm} every direction", font_size=26, color=YELLOW),
                     Tex(r"\textbf{29.2 / 106.8} kcps/MBq", font_size=26),
                     Tex(r"NECR \textbf{716 / 1235} kcps", font_size=26)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.1).to_corner(DR, buff=0.35)
        fit_frame(info)
        fit_frame(res)
        self.add_fixed_in_frame_mobjects(info, res)
        self.remove(info, res)
        with self.voiceover(text="As a reference, Maya Abi Akl and colleagues put the <bookmark mark='r'/>same L Y S O block into a "
                                 "conventional ring: forty blocks around a seventy centimetre bore, <bookmark mark='len'/>seven or fourteen "
                                 "rings long. They ran the <bookmark mark='nema'/>N E M A NU two twenty eighteen tests in GATE, with the "
                                 "detector's energy resolution, energy window, coincidence window and a paralysable dead time model."):
            self.at("r", LaggedStart(*[FadeIn(b) for b in blocks], lag_ratio=0.002), FadeIn(info[0]), run_time=1.6)
            self.begin_ambient_camera_rotation(rate=0.1)
            self.at("len", FadeIn(info[1]))
            self.at("nema", FadeIn(info[2]), FadeIn(info[3]), FadeIn(info[4]))
        self.stop_ambient_camera_rotation()
        with self.voiceover(text="With every angle covered, resolution stays <bookmark mark='a'/>under two millimetres in every direction. "
                                 "<bookmark mark='b'/>Sensitivity is twenty nine and a hundred and seven kilo counts per second per "
                                 "megabecquerel, and the <bookmark mark='c'/>count rate peaks at seven hundred and sixteen and twelve "
                                 "hundred and thirty five kilo counts per second. This is what the panels are measured against."):
            for k, m in enumerate("abc"):
                self.at(m, FadeIn(res[k]))
        self.play(*[FadeOut(m) for m in (blocks, info, res)])


class Sparse(Narrated, ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=72 * DEGREES, theta=-35 * DEGREES, zoom=0.85)
        rows, mod, gap = 8, 0.55, 0.55 * 28 / 50     # 50 mm blocks, 28 mm gaps (to scale with each other)
        def panel(x):
            g = VGroup()
            for k in range(rows):
                z = (k - (rows - 1) / 2) * (mod + gap)
                g.add(Prism(dimensions=[0.18, 3.2, mod], fill_color=PANEL_C, fill_opacity=0.5, stroke_width=0.5, stroke_color=BLOCK_C).move_to([x, 0, z]))
            return g
        p1, p2 = panel(-1.4), panel(1.4)
        ghost = VGroup(*[m.copy().set_fill(YELLOW, opacity=0.25).shift((mod + gap) / 2 * OUT) for m in [*p1, *p2]])
        info = VGroup(Tex(r"\textbf{60 cm}, 8 rows, \textbf{28 mm} gaps", font_size=26),
                      Tex(r"step: \textbf{half a module}", font_size=26, color=YELLOW),
                      Tex(r"blocks land on the gaps", font_size=26, color=YELLOW)).arrange(DOWN, aligned_edge=LEFT, buff=0.1).to_corner(UL, buff=0.35)
        res = VGroup(Tex(r"\textbf{26} kcps/MBq ($\div$\textbf{4.6})", font_size=24),
                     Tex(r"\textbf{2--3 min} $\approx$ \textbf{30 s} long panels", font_size=24),
                     Tex(r"\textbf{3--3.5 mm} $\perp$", font_size=24, color=RED)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.1).to_corner(DR, buff=0.3)
        fit_frame(info)
        fit_frame(res)
        self.add_fixed_in_frame_mobjects(info, res)
        self.remove(info, res)
        with self.voiceover(text="Then the cost cutting. The 2025 design makes the panels <bookmark mark='s'/>sparse: sixty centimetres tall, "
                                 "eight rows of blocks with twenty eight millimetre gaps, about half a block. The gaps are not wasted: "
                                 "the panels <bookmark mark='m'/>step vertically by half a module, so the new block positions sit exactly "
                                 "over the old gaps and the axial sensitivity profile <bookmark mark='f'/>smooths out."):
            self.at("s", FadeIn(p1), FadeIn(p2), FadeIn(info[0]))
            self.wait_until_bookmark("m")
            self.play(FadeIn(ghost), FadeIn(info[1]), run_time=0.8)
            self.at("f", FadeIn(info[2]), Indicate(ghost, color=YELLOW))
        with self.voiceover(text="Evaluated with N E M A sensitivity, the image quality phantom and an X CAT anthropomorphic phantom, the "
                                 "sparse build is <bookmark mark='a'/>four point six times less sensitive, needs <bookmark mark='b'/>two to "
                                 "three minutes to match thirty seconds on the long panels, and keeps <bookmark mark='c'/>three to three and "
                                 "a half millimetres perpendicular to the panels."):
            for k, m in enumerate("abc"):
                self.at(m, FadeIn(res[k]))
        self.play(*[FadeOut(m) for m in (p1, p2, ghost, info, res)])


class SlideThrough(Narrated, ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=70 * DEGREES, theta=-55 * DEGREES, zoom=0.9)
        u2 = 0.034                                   # this scene only: 190.5 cm has to fit the frame
        T = 190.5 * u2
        H_top, H_bot = 0.55 * T, 0.45 * T
        def strip(x, y0):
            return VGroup(Prism(dimensions=[0.2, 20.9 * u2, H_top], fill_color=PANEL_C, fill_opacity=0.55, stroke_width=0.5, stroke_color=BLOCK_C)
                          .move_to([x, y0, -T / 2 + H_bot + H_top / 2]),
                          Prism(dimensions=[0.2, 10.3 * u2, H_bot], fill_color=PANEL_C, fill_opacity=0.55, stroke_width=0.5, stroke_color=BLOCK_C)
                          .move_to([x, y0 - (20.9 - 10.3) * u2 / 2, -T / 2 + H_bot / 2]))
        sweep = (73.9 - 20.9) / 2 * u2
        s1, s2 = strip(-50 * u2 / 2, 0), strip(50 * u2 / 2, 0)
        pat = patient3d(h=T * 0.95)
        info = VGroup(Tex(r"\textbf{190.5 cm} strips, 50 cm apart", font_size=26),
                      Tex(r"\textbf{20.9 / 10.3 cm} wide, \textbf{224} modules", font_size=26),
                      Tex(r"slide over \textbf{73.9 cm}", font_size=26, color=YELLOW)).arrange(DOWN, aligned_edge=LEFT, buff=0.1).to_corner(UL, buff=0.35)
        fit_frame(info)
        self.add_fixed_in_frame_mobjects(info)
        self.remove(info)
        with self.voiceover(text="The 2026 design goes further: <bookmark mark='p'/>narrow strips almost two metres tall, wider at the torso "
                                 "and narrower at the legs, two hundred and twenty four modules in all, about as many as a standard "
                                 "cylinder. To cover the body, the strips <bookmark mark='sl'/>slide sideways together across a seventy four "
                                 "centimetre field."):
            self.play(FadeIn(pat), run_time=0.6)
            self.at("p", FadeIn(s1), FadeIn(s2), FadeIn(info[0]), FadeIn(info[1]))
            self.wait_until_bookmark("sl")
            self.play(FadeIn(info[2]), VGroup(s1, s2).animate.shift(sweep * DOWN), run_time=1.2)
            self.play(VGroup(s1, s2).animate.shift(2 * sweep * UP), run_time=2.0)
            self.play(VGroup(s1, s2).animate.shift(sweep * DOWN), run_time=1.0)
        self.play(*[FadeOut(m) for m in (s1, s2, pat, info)])


class Motions(Narrated):
    def construct(self):
        title = Tex("Choosing the motion: sinogram coverage (2026)").scale(0.72).to_edge(UP)
        w = 20.9
        cs = np.linspace(-(73.9 - w) / 2, (73.9 - w) / 2, 25)
        maps = [("static narrow panels", [((0, w), (0, w))]),
                ("parallel motion", [((c, w), (c, w)) for c in cs]),
                ("opposite motion", [((c, w), (-c, w)) for c in cs]),
                ("one panel moving", [((c, w), (0, w)) for c in cs])]
        imgs = Group()
        for k, (lab, pan) in enumerate(maps):
            im = mask_image(coverage(pan), h=1.75, w=2.6)
            g = Group(im, Tex(lab, font_size=24).next_to(im, UP, buff=0.1))
            body = VGroup(*[DashedLine(im.get_left() + (im.height / 2) * (rr / 45) * UP, im.get_right() + (im.height / 2) * (rr / 45) * UP,
                                       color=YELLOW, stroke_width=1.5, dash_length=0.06) for rr in (-15, 15)])
            g.add(body)
            imgs.add(g)
        imgs.arrange_in_grid(2, 2, buff=(0.6, 0.5)).shift(2.2 * LEFT + 0.4 * DOWN)
        note = VGroup(Tex(r"angle across, offset up", font_size=22, color=GREY_B),
                      Tex(r"yellow: $\pm$15 cm torso", font_size=22, color=YELLOW),
                      Tex(r"computed here", font_size=22, color=GREY_D)).arrange(DOWN, aligned_edge=LEFT, buff=0.06)
        txt = VGroup(Tex(r"opposite: centre only", font_size=24),
                     Tex(r"$|r| <$ \textbf{10 cm}", font_size=24),
                     Tex(r"single: small field", font_size=24),
                     Tex(r"parallel: same angles at all $r$", font_size=24, color=TEAL_L),
                     Tex(r"$\Rightarrow$ parallel motion chosen", font_size=24, color=YELLOW)).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        side = VGroup(note, txt).arrange(DOWN, aligned_edge=LEFT, buff=0.4).to_edge(RIGHT, buff=0.4).shift(0.2 * DOWN)
        fit_frame(side)
        with self.voiceover(text="Which way should the strips move? The paper answers with the same sinogram analysis. A "
                                 "<bookmark mark='st'/>static pair of narrow strips records only a sliver of lines. Moving them "
                                 "<bookmark mark='op'/>in opposite directions covers many angles, but only near the centre: nothing beyond "
                                 "about ten centimetres, half the strip width, so most of a patient is lost. "
                                 "<bookmark mark='si'/>Moving just one strip covers more angles but a smaller field. "
                                 "<bookmark mark='pa'/>Parallel motion gives the same, truncated range of angles at every offset, so it was "
                                 "chosen."):
            self.play(Write(title), FadeIn(note), run_time=0.8)
            self.at("st", FadeIn(imgs[0]))
            self.at("op", FadeIn(imgs[2]), FadeIn(txt[0]), FadeIn(txt[1]))
            self.at("si", FadeIn(imgs[3]), FadeIn(txt[2]))
            self.at("pa", FadeIn(imgs[1]), FadeIn(txt[3]), FadeIn(txt[4]))
        fade_all(self)
        title2 = Tex("Slide-Through PET: the numbers").scale(0.72).to_edge(UP)
        meth = Tex(r"GATE 9.4 \textperiodcentered\ same detectors \textperiodcentered\ NEMA IQ + 2 XCATs", font_size=26, color=GREY_B).next_to(title2, DOWN, buff=0.3)

        def hbars(rows, xmax, origin, unit):
            ax = Axes(x_range=[0, xmax, xmax / 4], y_range=[0, len(rows), 1], x_length=4.2, y_length=0.75 * len(rows), tips=False,
                      axis_config={"color": GREY_B, "include_ticks": False}).move_to(origin)
            g = VGroup()
            for k, (lab, v, col) in enumerate(rows):
                b = Rectangle(width=ax.c2p(v, 0)[0] - ax.c2p(0, 0)[0], height=0.42, fill_color=col, fill_opacity=0.9, stroke_width=0)
                b.move_to(ax.c2p(0, len(rows) - 0.5 - k), aligned_edge=LEFT)
                g.add(VGroup(b, Tex(lab, font_size=24).next_to(b, LEFT, buff=0.12).set_x(ax.c2p(0, 0)[0] - 0.12, direction=RIGHT),
                             Tex(r"\textbf{" + f"{v:g}" + "}", font_size=26).next_to(b, RIGHT, buff=0.1)))
            return ax, g, Tex(unit, font_size=24, color=GREY_B).next_to(ax, UP, buff=0.12)

        ax1, sens, u1 = hbars([("torso", 1.66, PANEL_C), ("legs", 0.52, PANEL_C), ("cylinder", 1.05, CYL_C)], 2.0, 3.1 * LEFT + 0.6 * DOWN,
                              "sensitivity (cps/kBq)")
        ax2, times, u2 = hbars([("Slide-Through", 4, PANEL_C), ("cylinder", 9.15, CYL_C)], 10, 3.4 * RIGHT + 0.3 * DOWN,
                               "scan time, equal torso noise (min)")
        fit_frame(VGroup(ax1, sens, u1))
        fit_frame(VGroup(ax2, times, u2))
        warn = VGroup(Tex(r"elongation remains", font_size=28, color=RED),
                      Tex(r"needs $<$\textbf{300 ps}", font_size=28, color=YELLOW)).arrange(RIGHT, buff=0.8).to_edge(DOWN, buff=0.45)
        with self.voiceover(text="The paper compares it in <bookmark mark='g'/>GATE against two references built from the same detectors: "
                                 "the wide static panels and a cylinder. <bookmark mark='m'/>Sensitivity comes from a uniform box source the "
                                 "size of the field, image quality from the <bookmark mark='x'/>N E M A phantom and two X CAT patients. The "
                                 "torso gets <bookmark mark='r0'/>more sensitivity than the cylinder, the legs half as much, and "
                                 "<bookmark mark='r1'/>four minutes matches nine on the cylinder for torso noise. But "
                                 "<bookmark mark='r2'/>elongation remains, and the conclusion <bookmark mark='r3'/>asks for timing better "
                                 "than three hundred picoseconds."):
            self.play(Write(title2), run_time=0.8)
            self.at("g", FadeIn(meth))
            self.at("m", Create(ax1), FadeIn(u1))
            self.at("x", Indicate(meth, color=WHITE))
            self.at("r0", LaggedStart(*[AnimationGroup(GrowFromEdge(r[0], LEFT), FadeIn(r[1:])) for r in sens], lag_ratio=0.25), run_time=1.2)
            self.at("r1", Create(ax2), FadeIn(u2), LaggedStart(*[AnimationGroup(GrowFromEdge(r[0], LEFT), FadeIn(r[1:])) for r in times], lag_ratio=0.3),
                    run_time=1.2)
            self.at("r2", FadeIn(warn[0], shift=0.1 * UP))
            self.at("r3", FadeIn(warn[1], shift=0.1 * UP))
        fade_all(self)


class Takeaway(Narrated):
    def construct(self):
        title = Tex("The pattern across six papers").scale(0.72).to_edge(UP)
        steps = VGroup(Tex(r"2023: panels, \textbf{3.3$\times$} cheaper", font_size=28),
                       Tex(r"2023: BGO $\to$ \textbf{3.36 mm} $\perp$", font_size=28),
                       Tex(r"2025: sparse $\to$ \textbf{3--3.5 mm} $\perp$", font_size=28),
                       Tex(r"2026: strips $\to$ want $<$\textbf{300 ps}", font_size=28)
                       ).arrange(DOWN, aligned_edge=LEFT, buff=0.18).next_to(title, DOWN, buff=0.5)
        fit_frame(steps)
        with self.voiceover(text="Read in order, the papers make one argument. Each step <bookmark mark='s0'/>saves detector and money, and "
                                 "each pays in <bookmark mark='s1'/>angular sampling, visible in the sinogram and in the "
                                 "<bookmark mark='s2'/>perpendicular blur, which the <bookmark mark='s3'/>latest paper hopes faster timing "
                                 "will hide."):
            self.play(Write(title), run_time=0.8)
            for k in range(4):
                self.at(f"s{k}", FadeIn(steps[k], shift=0.1 * RIGHT))
        lesson = VGroup(Tex(r"panels: cheaper, faster, fewer angles", font_size=30, color=YELLOW),
                        Tex(r"ring: every angle, nothing moves", font_size=30, color=TEAL_L)
                        ).arrange(DOWN, aligned_edge=LEFT, buff=0.18).next_to(steps, DOWN, buff=0.6).align_to(steps, LEFT)
        fit_frame(VGroup(steps, lesson))
        with self.voiceover(text="It is a strong <bookmark mark='l0'/>cost and throughput case, with its weakness measured honestly by the "
                                 "group itself. And it shows what a <bookmark mark='l1'/>closed ring gets for free: every angle, and "
                                 "nothing that has to move."):
            self.at("l0", FadeIn(lesson[0], shift=0.1 * UP))
            self.at("l1", FadeIn(lesson[1], shift=0.1 * UP))
        self.play(FadeOut(steps), FadeOut(lesson), FadeOut(title))
        refs = VGroup(Tex("Walk-Through PET", font_size=40),
                      Tex(r"Vandenberghe 2020, 2023; Dadgar 2023; Abi-Akl 2023, 2025; Dhaenens \& Vervenne 2026", font_size=24, color=GREY_B),
                      Tex(CITE, font_size=24, color=TEAL_L)).arrange(DOWN, buff=0.2)
        fit_frame(refs)
        with self.voiceover(text="Thanks for watching."):
            self.play(FadeIn(refs), run_time=1.0)
        self.wait(0.8)
        fade_all(self)
