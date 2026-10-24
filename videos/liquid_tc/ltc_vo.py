"""Explainer: 'Liquid Time-constant Networks' (Hasani, Lechner, Amini, Rus, Grosu; AAAI 2021, arXiv:2006.04439).

Numbers are from the paper's text, Eqs. 1-5, Tables 1-6 and the labels of Fig. 2(A). The paper is
"all rights reserved", so no figures are reused: every plot here is drawn from scratch. The single-neuron
traces are simulated with the paper's fused solver (Eq. 3) and are illustrative, as is the latent curve.
Visuals are cued to the narration with <bookmark/> tags and self.at() (see ../DESIGN.md).
Render with render.sh, or one scene: manim -ql ltc_vo.py Liquid
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import *  # noqa: E402,F401

LTC_C, CT_C, NODE_C, LSTM_C, GRU_C, IN_C = TEAL_L, ORANGE_L, PURPLE_L, BLUE_L, "#9aa4b2", "#e8c547"
NAMES = [("LSTM", LSTM_C), ("CT-RNN", CT_C), ("Neural ODE", NODE_C), ("CT-GRU", GRU_C), ("LTC", LTC_C)]
CITE = r"Hasani, Lechner, Amini, Rus, Grosu \textperiodcentered\ AAAI 2021"

# Table 3 (mean of n=5); higher is better except the two squared errors
TABLE3 = [
    ("Gesture", "acc. \\%", [64.57, 59.01, 46.97, 68.31, 69.55], 1),
    ("Occupancy", "acc. \\%", [93.18, 94.54, 90.15, 91.44, 94.63], 1),
    ("Activity", "acc. \\%", [95.85, 95.73, 97.26, 96.16, 95.67], 1),
    ("Seq.\\ MNIST", "acc. \\%", [98.41, 96.73, 97.61, 98.27, 97.57], 1),
    ("Traffic", "sq.\\ error", [0.169, 0.224, 1.512, 0.389, 0.099], -1),
    ("Power", "sq.\\ error", [0.628, 0.742, 1.254, 0.586, 0.642], -1),
    ("Ozone", "F1", [0.284, 0.236, 0.168, 0.260, 0.302], 1),
]
# Fig. 2(A): trajectory length per layer, Hard-tanh, width 100
TRAJ = {"Neural ODE": [108.245, 5407.3963, 255299.3159], "CT-RNN": [90.5486, 1210.7898, 15949.0123],
        "LTC": [12481.0242, 15332.7607, 17707.2484]}
CHEETAH = [("LSTM", 2.500), ("CT-RNN", 2.838), ("Neural ODE", 3.805), ("CT-GRU", 3.014), ("LTC", 2.308)]   # Table 6, MSE


def sig(z):
    return 1 / (1 + np.exp(-z))


def ltc_neuron(I, dt, tau=2.0, A=1.0, w=4.0):
    """One LTC neuron, f = w * sigmoid(3 I - 3), stepped with the paper's fused solver (Eq. 3)."""
    f = w * sig(3 * I - 3)
    x = np.zeros_like(I)
    for k in range(len(I) - 1):
        x[k + 1] = (x[k] + dt * f[k] * A) / (1 + dt * (1 / tau + f[k]))
    return f, x, tau / (1 + tau * f)


def trace(ax, t, y, color, upto=None, width=3):
    """A polyline of y(t) on ax, cut at time `upto`."""
    n = len(t) if upto is None else max(2, int(np.searchsorted(t, upto)))
    step = max(1, n // 400)
    pts = [ax.c2p(a, b) for a, b in zip(t[:n:step], y[:n:step])] + [ax.c2p(t[n - 1], y[n - 1])]
    return VMobject(stroke_color=color, stroke_width=width).set_points_as_corners(pts)


def neuron(pos, r=0.32, color=LTC_C):
    return Circle(radius=r, color=color, stroke_width=3, fill_color=color, fill_opacity=0.18).move_to(pos)


class Opening(Narrated):
    def construct(self):
        pos = [np.array(p) for p in [(-2.2, 0.2, 0), (-0.8, 1.2, 0), (-0.6, -0.9, 0), (0.9, 0.5, 0), (1.0, -1.2, 0), (2.3, 0.0, 0)]]
        cells = VGroup(*[neuron(p) for p in pos])
        links = [(0, 1), (0, 2), (1, 3), (2, 3), (2, 4), (3, 5), (4, 5), (1, 2), (3, 4)]
        syn = VGroup(*[Line(pos[a], pos[b], buff=0.34, color=GREY_B, stroke_width=2) for a, b in links])
        net = VGroup(syn, cells).shift(0.3 * DOWN)
        title = Tex("Liquid Time-constant Networks").scale(1.0).to_edge(UP, buff=0.5)
        foot = VGroup(Tex(r"R.\ Hasani, M.\ Lechner, A.\ Amini, D.\ Rus, R.\ Grosu", color=GREY_B).scale(0.5),
                      Tex(r"AAAI 2021 \textperiodcentered\ arXiv:2006.04439 \textperiodcentered\ MIT, IST Austria, TU Wien", color=TEAL_L).scale(0.5)
                      ).arrange(DOWN, buff=0.12).to_edge(DOWN, buff=0.35)
        with self.voiceover(text="Most neural networks react to their input at a fixed pace. What if each neuron could "
                                 "<bookmark mark='speed'/>change how fast it responds, depending on what it is seeing right now? "
                                 "That is the idea behind <bookmark mark='title'/>liquid time constant networks."):
            self.play(LaggedStart(*[GrowFromCenter(c) for c in cells], lag_ratio=0.12), run_time=1.2)
            self.play(LaggedStart(*[Create(s) for s in syn], lag_ratio=0.08), run_time=1.0)
            self.wait_until_bookmark("speed")
            for k, rt in [(0, 1.2), (3, 0.35), (5, 0.35), (2, 1.2)]:
                self.play(cells[k].animate.set_fill(opacity=0.85), run_time=rt / 2)
                self.play(cells[k].animate.set_fill(opacity=0.18), run_time=rt / 2)
            self.at("title", Write(title), FadeIn(foot, shift=0.1 * UP), run_time=1.2)
        with self.voiceover(text="In this video: where they come from, why their dynamics stay bounded, how they are solved and "
                                 "trained, and how they compare with other recurrent networks on time series."):
            self.play(*[Indicate(c, color=LTC_C, scale_factor=1.15) for c in cells], run_time=1.2)
        fade_all(self)


class Background(Narrated):
    def construct(self):
        title = Tex("From recurrent networks to neural ODEs").scale(0.72).to_edge(UP)
        tl = NumberLine(x_range=[0, 6, 1], length=5.2, include_tip=True, color=GREY_B).shift(3.3 * LEFT + 0.5 * UP)
        dots = VGroup(*[Dot(tl.n2p(k), color=LSTM_C, radius=0.08) for k in range(6)])
        rnn = MathTex(r"h_{k+1} = F(h_k, I_k)", font_size=40, color=LSTM_C).next_to(tl, UP, buff=0.35)
        ax = Axes(x_range=[0, 6, 1], y_range=[-1.2, 1.2, 1], x_length=5.2, y_length=2.0, tips=False,
                  axis_config={"color": GREY_B, "include_ticks": False}).shift(3.3 * RIGHT + 0.5 * UP)
        ts = np.linspace(0, 6, 300)
        flow = trace(ax, ts, np.sin(1.3 * ts) * np.exp(-0.15 * ts), NODE_C)
        node = MathTex(r"\frac{dx}{dt} = f(x, I, t, \theta)", font_size=40, color=NODE_C).next_to(ax, UP, buff=0.25)
        with self.voiceover(text="A <bookmark mark='rnn'/>classic recurrent network updates its hidden state in fixed "
                                 "<bookmark mark='steps'/>steps, one per input. A <bookmark mark='node'/>neural O D E instead lets "
                                 "a network f define the <bookmark mark='flow'/>rate of change of the state, so the state flows in "
                                 "continuous time and a numerical solver computes it."):
            self.play(Write(title), run_time=0.8)
            self.at("rnn", FadeIn(rnn), Create(tl))
            self.at("steps", LaggedStart(*[FadeIn(d, scale=0.5) for d in dots], lag_ratio=0.15), run_time=1.0)
            self.at("node", Write(node), Create(ax))
            self.at("flow", Create(flow, rate_func=linear), run_time=1.6)

        ct = MathTex(r"\frac{dx}{dt} = ", r"-\frac{x}{\tau}", r"+ f(x, I, t, \theta)", font_size=44, color=CT_C).shift(1.2 * DOWN + 2.6 * LEFT)
        ctl = Tex("continuous-time RNN (CT-RNN)", font_size=28, color=CT_C).next_to(ct, UP, buff=0.2)
        ax2 = Axes(x_range=[0, 5, 1], y_range=[0, 1.1, 1], x_length=4.2, y_length=2.0, tips=False,
                   axis_config={"color": GREY_B, "include_ticks": False}).shift(3.4 * RIGHT + 1.8 * DOWN)
        t2 = np.linspace(0, 5, 200)
        dec = trace(ax2, t2, np.exp(-t2), CT_C)
        tmark = DashedLine(ax2.c2p(1, 0), ax2.c2p(1, np.exp(-1)), color=GREY_B)
        tlab = MathTex(r"\tau", font_size=34).next_to(ax2.c2p(1, 0), DOWN, buff=0.12)
        fixed = Tex(r"$\tau$ is fixed after training", font_size=28, color=GREY_B).next_to(ax2, DOWN, buff=0.45)
        with self.voiceover(text="A more stable variant, the continuous time R N N, adds a <bookmark mark='leak'/>leak term, minus x "
                                 "over tau, which pulls the state back to rest with a <bookmark mark='tau'/>time constant tau. "
                                 "But tau is <bookmark mark='fixed'/>one fixed number per neuron, whatever the input."):
            self.play(FadeIn(ctl), Write(ct), run_time=1.0)
            self.at("leak", Indicate(ct[1], color=YELLOW), Create(ax2), Create(dec), run_time=1.0)
            self.at("tau", Create(tmark), FadeIn(tlab))
            self.at("fixed", FadeIn(fixed, shift=0.1 * UP))
        fade_all(self)


class Neuron(Narrated):
    def construct(self):
        title = Tex("The LTC neuron").scale(0.72).to_edge(UP)
        lin = MathTex(r"\frac{dx}{dt}", "=", r"-\frac{x}{\tau}", "+", "S(t)", font_size=44).shift(2.0 * UP)
        syn = MathTex(r"S(t)", "=", r"f(x, I, t, \theta)", r"\,(A - x)", font_size=44).next_to(lin, DOWN, buff=0.4)
        with self.voiceover(text="The authors start from a simple <bookmark mark='lin'/>linear neuron: a leak, plus an input "
                                 "<bookmark mark='S'/>S. Then they make S a <bookmark mark='f'/>neural network f times "
                                 "<bookmark mark='A'/>A minus x, where A is a learned bias."):
            self.play(Write(title), run_time=0.8)
            self.at("lin", Write(lin))
            self.at("S", Indicate(lin[4], color=YELLOW), FadeIn(syn[:2]))
            self.at("f", FadeIn(syn[2]))
            self.at("A", FadeIn(syn[3]))

        bio = VGroup(Tex(r"non-spiking neuron: membrane potential $v$, leak conductance $g_l$", font_size=28),
                     Tex(r"synapse current $\propto f(v, I)\,(A - v)$, $A$ = reversal potential", font_size=28)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.12).set_color(GREY_B).to_edge(DOWN, buff=0.5)
        with self.voiceover(text="This is borrowed from biology. In a <bookmark mark='bio'/>non spiking neuron, a synapse drives the "
                                 "membrane towards its <bookmark mark='rev'/>reversal potential, and the drive fades as it gets there."):
            self.at("bio", FadeIn(bio[0], shift=0.1 * UP))
            self.at("rev", FadeIn(bio[1], shift=0.1 * UP))

        eq1 = MathTex(r"\frac{dx}{dt}", "=", r"-\Big[\frac{1}{\tau}", "+", r"f(x, I, t, \theta)", r"\Big]\,x", "+", r"f(x, I, t, \theta)", r"\,A",
                      font_size=46).move_to(1.0 * UP)
        box = SurroundingRectangle(eq1[2:6], color=LTC_C, buff=0.12)
        tsys = MathTex(r"\tau_{\mathrm{sys}}", "=", r"\frac{\tau}{1 + \tau f(x, I, t, \theta)}", font_size=46, color=LTC_C).next_to(eq1, DOWN, buff=0.9)
        note = Tex(r"strong input $\Rightarrow$ large $f$ $\Rightarrow$ short time constant", font_size=30, color=GREY_B).next_to(tsys, DOWN, buff=0.45)
        with self.voiceover(text="Substitute S back in and you get <bookmark mark='eq'/>equation one. Look at what multiplies x: "
                                 "<bookmark mark='box'/>one over tau, plus f. The network f now sits inside the decay rate, so the "
                                 "neuron's effective time constant, <bookmark mark='tsys'/>tau system, equals tau over one plus tau f. "
                                 "It <bookmark mark='note'/>changes with the input at every moment: the time constant is liquid."):
            self.play(FadeOut(bio), FadeOut(lin), FadeOut(syn), run_time=0.5)
            self.at("eq", Write(eq1), run_time=1.2)
            self.at("box", Create(box))
            self.at("tsys", Write(tsys))
            self.at("note", FadeIn(note, shift=0.1 * UP))
        fade_all(self)


class Liquid(Narrated):
    def construct(self):
        title = Tex("One LTC neuron in action").scale(0.72).to_edge(UP)
        T, dt = 14.0, 0.002
        t = np.arange(0, T + dt, dt)
        I = np.where((t > 1) & (t < 5), 0.6, 0.0) + np.where((t > 7.5) & (t < 10.5), 2.0, 0.0)
        f, x, tsys = ltc_neuron(I, dt)
        cfg = {"color": GREY_B, "include_ticks": False}
        axI = Axes(x_range=[0, T, 1], y_range=[0, 2.2, 1], x_length=10, y_length=1.1, tips=False, axis_config=cfg)
        axX = Axes(x_range=[0, T, 1], y_range=[0, 1.0, 1], x_length=10, y_length=1.7, tips=False, axis_config=cfg)
        axT = Axes(x_range=[0, T, 1], y_range=[0, 2.0, 1], x_length=10, y_length=1.5, tips=False, axis_config=cfg)
        axes = VGroup(axI, axX, axT).arrange(DOWN, buff=0.45).shift(0.6 * RIGHT + 0.45 * DOWN)
        labs = VGroup(Tex(r"input $I$", font_size=28, color=IN_C), Tex(r"state $x$", font_size=28, color=LTC_C),
                      MathTex(r"\tau_{\mathrm{sys}}", font_size=34, color=ORANGE_L))
        for l, a in zip(labs, axes):
            l.next_to(a, LEFT, buff=0.3)
        now = ValueTracker(0.0)
        curves = VGroup(always_redraw(lambda: trace(axI, t, I, IN_C, now.get_value())),
                        always_redraw(lambda: trace(axX, t, x, LTC_C, now.get_value())),
                        always_redraw(lambda: trace(axT, t, tsys, ORANGE_L, now.get_value())))
        cursor = always_redraw(lambda: DashedLine(axI.c2p(now.get_value(), 2.2), axT.c2p(now.get_value(), 0), color=GREY_D, stroke_width=1.5))
        ceil = DashedLine(axT.c2p(0, 2.0), axT.c2p(T, 2.0), color=GREY_D, stroke_width=1.5)
        ceill = MathTex(r"\tau = 2", font_size=26, color=GREY_B).next_to(ceil, RIGHT, buff=0.1)
        ill = Tex(r"illustrative: $\tau=2$, $A=1$, $f = 4\,\sigma(3I-3)$, fused solver", font_size=22, color=GREY_D).to_corner(DR, buff=0.15)
        with self.voiceover(text="Here is one simulated neuron. The <bookmark mark='in'/>input at the top, the "
                                 "<bookmark mark='x'/>state in the middle, and its <bookmark mark='ts'/>effective time constant at "
                                 "the bottom, which can never exceed tau."):
            self.play(Write(title), run_time=0.8)
            self.at("in", Create(axI), FadeIn(labs[0]), FadeIn(ill))
            self.at("x", Create(axX), FadeIn(labs[1]))
            self.at("ts", Create(axT), FadeIn(labs[2]), Create(ceil), FadeIn(ceill))
        self.add(curves, cursor)
        with self.voiceover(text="A <bookmark mark='weak'/>weak input arrives. The time constant dips a little, and the state rises "
                                 "slowly to a <bookmark mark='low'/>modest level. When the input stops, it <bookmark mark='rel'/>relaxes "
                                 "back."):
            self.wait_until_bookmark("weak")
            self.play(now.animate.set_value(3.0), run_time=1.6, rate_func=linear)
            self.at("low", now.animate.set_value(5.0), run_time=1.0, rate_func=linear)
            self.at("rel", now.animate.set_value(7.4), run_time=1.6, rate_func=linear)
        with self.voiceover(text="Now a <bookmark mark='strong'/>strong input. The time constant collapses, so the neuron "
                                 "<bookmark mark='fast'/>snaps up almost at once, and settles close to A. Once the input is gone, the "
                                 "time constant <bookmark mark='back'/>returns to its slow value, and the neuron remembers a little "
                                 "longer."):
            self.wait_until_bookmark("strong")
            self.play(now.animate.set_value(8.2), run_time=1.0, rate_func=linear)
            self.at("fast", now.animate.set_value(10.5), run_time=1.6, rate_func=linear)
            self.at("back", now.animate.set_value(T), run_time=2.2, rate_func=linear)
        with self.voiceover(text="Same neuron, same weights: how quickly it reacts is decided by what it sees."):
            self.play(Indicate(labs[2], color=ORANGE_L), run_time=1.0)
        for m in (*curves, cursor):
            m.clear_updaters()
        fade_all(self)


class Bounded(Narrated):
    def construct(self):
        title = Tex("Stable by construction").scale(0.72).to_edge(UP)
        th1 = MathTex(r"\frac{\tau_i}{1 + \tau_i W_i}", r"\;\le\;", r"\tau_{\mathrm{sys},i}", r"\;\le\;", r"\tau_i", font_size=40, color=ORANGE_L)
        th2 = MathTex(r"\min(0, A_i^{\min})", r"\;\le\;", r"x_i(t)", r"\;\le\;", r"\max(0, A_i^{\max})", font_size=40, color=LTC_C)
        lab1, lab2 = Tex("Theorem 1", font_size=28, color=GREY_B), Tex("Theorem 2", font_size=28, color=GREY_B)
        rows = VGroup(VGroup(lab1, th1).arrange(RIGHT, buff=0.5), VGroup(lab2, th2).arrange(RIGHT, buff=0.5)).arrange(DOWN, aligned_edge=LEFT, buff=0.35)
        rows.next_to(title, DOWN, buff=0.35)
        with self.voiceover(text="A time constant that moves with the input could, in principle, run wild. The paper proves it "
                                 "can't. <bookmark mark='t1'/>Theorem one: each neuron's time constant stays between tau over one plus "
                                 "tau W, where W bounds the incoming weights, and tau itself. <bookmark mark='t2'/>Theorem two: the "
                                 "state stays between zero and the extreme values of A."):
            self.play(Write(title), run_time=0.8)
            self.at("t1", FadeIn(lab1), Write(th1))
            self.at("t2", FadeIn(lab2), Write(th2))

        T, dt = 8.0, 0.002
        t = np.arange(0, T + dt, dt)
        I = 0.35 * t ** 2
        f, x, tsys = ltc_neuron(I, dt)
        cfg = {"color": GREY_B, "include_ticks": False}
        axI = Axes(x_range=[0, T, 1], y_range=[0, 23, 10], x_length=3.8, y_length=3.2, tips=False, axis_config=cfg)
        axX = Axes(x_range=[0, T, 1], y_range=[0, 1.2, 1], x_length=3.8, y_length=3.2, tips=False, axis_config=cfg)
        axT = Axes(x_range=[0, T, 1], y_range=[0, 2.2, 1], x_length=3.8, y_length=3.2, tips=False, axis_config=cfg)
        axes = VGroup(axI, axX, axT).arrange(RIGHT, buff=0.7).to_edge(DOWN, buff=0.8)
        caps = VGroup(Tex(r"input grows without limit", font_size=26, color=IN_C), Tex(r"state $x$", font_size=26, color=LTC_C),
                      Tex(r"$\tau_{\mathrm{sys}}$", font_size=28, color=ORANGE_L))
        for c, a in zip(caps, axes):
            c.next_to(a, DOWN, buff=0.15)
        Aline = DashedLine(axX.c2p(0, 1), axX.c2p(T, 1), color=GREY_B, stroke_width=2)
        Alab = MathTex("A", font_size=28, color=GREY_B).next_to(Aline, UP, buff=0.05).align_to(Aline, RIGHT)
        floor = DashedLine(axT.c2p(0, 2 / 9), axT.c2p(T, 2 / 9), color=GREY_B, stroke_width=2)
        top = DashedLine(axT.c2p(0, 2), axT.c2p(T, 2), color=GREY_B, stroke_width=2)
        fl = MathTex(r"\frac{\tau}{1+\tau W}", font_size=28, color=GREY_B).next_to(floor, UP, buff=0.05).align_to(floor, RIGHT)
        tl = MathTex(r"\tau", font_size=26, color=GREY_B).next_to(top, DOWN, buff=0.05).align_to(top, RIGHT)
        with self.voiceover(text="Push an <bookmark mark='grow'/>ever growing input into our neuron. The <bookmark mark='state'/>state "
                                 "climbs towards A but never passes it, and the <bookmark mark='tau'/>time constant falls to its floor "
                                 "and stops. The outputs cannot explode, however large the input becomes."):
            self.at("grow", Create(axI), FadeIn(caps[0]), Create(trace(axI, t, I, IN_C)), run_time=1.2)
            self.at("state", Create(axX), FadeIn(caps[1]), Create(Aline), FadeIn(Alab), Create(trace(axX, t, x, LTC_C)), run_time=1.2)
            self.at("tau", Create(axT), FadeIn(caps[2]), Create(floor), Create(top), FadeIn(fl), FadeIn(tl),
                    Create(trace(axT, t, tsys, ORANGE_L)), run_time=1.2)
        fade_all(self)


class Solver(Narrated):
    def construct(self):
        title = Tex("Solving it: the fused solver").scale(0.72).to_edge(UP)
        tau, fv, A, h, n = 1.0, 30.0, 1.0, 0.07, 6
        xs_true = np.linspace(0, n * h, 200)
        xstar = fv * A / (1 / tau + fv)
        exact = xstar * (1 - np.exp(-(1 / tau + fv) * xs_true))
        ex, fu = [0.0], [0.0]
        for _ in range(n):
            ex.append(ex[-1] + h * (-(1 / tau + fv) * ex[-1] + fv * A))
            fu.append((fu[-1] + h * fv * A) / (1 + h * (1 / tau + fv)))
        ax = Axes(x_range=[0, n * h, h], y_range=[-2, 3.5, 1], x_length=6.0, y_length=4.6, tips=False,
                  axis_config={"color": GREY_B, "include_ticks": False}).to_edge(LEFT, buff=0.6).shift(0.5 * DOWN)
        ax.get_x_axis().move_to(ax.c2p(n * h / 2, 0))
        tru = trace(ax, xs_true, exact, GREY_B)
        exl = VMobject(stroke_color=RED, stroke_width=3).set_points_as_corners([ax.c2p(k * h, v) for k, v in enumerate(ex)])
        exd = VGroup(*[Dot(ax.c2p(k * h, v), color=RED, radius=0.06) for k, v in enumerate(ex)])
        ful = VMobject(stroke_color=LTC_C, stroke_width=3).set_points_as_corners([ax.c2p(k * h, v) for k, v in enumerate(fu)])
        fud = VGroup(*[Dot(ax.c2p(k * h, v), color=LTC_C, radius=0.06) for k, v in enumerate(fu)])
        leg = VGroup(Tex("exact", font_size=26, color=GREY_B), Tex("explicit Euler", font_size=26, color=RED),
                     Tex("fused step", font_size=26, color=LTC_C)).arrange(RIGHT, buff=0.4).next_to(ax, UP, buff=0.15)
        ill = Tex(r"illustrative: large $f$, step $\Delta t = 0.07$", font_size=22, color=GREY_D).next_to(ax, DOWN, buff=0.15)
        with self.voiceover(text="Equation one has no closed form solution, so a solver steps it forward in time. When f is large "
                                 "the equation is <bookmark mark='stiff'/>stiff: a plain <bookmark mark='euler'/>explicit Euler step "
                                 "overshoots, and the error <bookmark mark='grow'/>grows with every step."):
            self.play(Write(title), run_time=0.8)
            self.at("stiff", Create(ax), Create(tru), FadeIn(leg[0]), FadeIn(ill))
            seg = VMobject(stroke_color=RED, stroke_width=3).set_points_as_corners([ax.c2p(k * h, v) for k, v in enumerate(ex[:2])])
            self.at("euler", FadeIn(leg[1]), FadeIn(exd[:2]), Create(seg))
            self.at("grow", Create(exl), FadeIn(exd[2:]), run_time=1.4)
        plot = VGroup(ax, tru, seg, exl, exd, leg[0], leg[1], ill)
        self.play(FadeOut(plot), run_time=0.6)

        # where x appears: bare (linear) vs inside f (nonlinear)
        B, N = YELLOW, PURPLE_L
        rhs = MathTex(r"\frac{dx}{dt}", "=", r"-\Big(\frac{1}{\tau} + f(", "x", r", I)\Big)", r"\,", "x", r"\;+\; f(", "x", r", I)\,A",
                      font_size=46).next_to(title, DOWN, buff=0.45)
        bare = SurroundingRectangle(rhs[6], color=B, buff=0.08)
        bl = Tex(r"bare $x$: linear, like $3x$", font_size=28, color=B).next_to(bare, DOWN, buff=0.25)
        inner = VGroup(*[SurroundingRectangle(rhs[k], color=N, buff=0.06) for k in (3, 8)])
        il = Tex(r"inside $f = \sigma(Wx + UI + b)$: nonlinear", font_size=28, color=N).next_to(rhs, UP, buff=0.12).align_to(rhs, LEFT)
        VGroup(bl, il).arrange(DOWN, aligned_edge=LEFT, buff=0.12).next_to(rhs, DOWN, buff=0.25)
        with self.voiceover(text="Why does that happen, and how do they fix it? Look at where x appears in equation one. Once "
                                 "<bookmark mark='bare'/>on its own, multiplied by the decay rate. That is a linear appearance, like "
                                 "three x. And twice <bookmark mark='inner'/>inside f, wrapped in a sigmoid. That is a nonlinear one."):
            self.play(Write(rhs), run_time=1.2)
            self.at("bare", rhs[6].animate.set_color(B), Create(bare), FadeIn(bl))
            self.at("inner", rhs[3].animate.set_color(N), rhs[8].animate.set_color(N), Create(inner), FadeIn(il))

        step = MathTex(r"x_{\text{new}}", "=", r"x_{\text{old}}", r"+\,\Delta t\cdot", r"\big(\text{right-hand side}\big)", font_size=40)
        step.next_to(VGroup(il, bl), DOWN, buff=0.5)
        q = Tex(r"each $x$ on the right: old value or new value?", font_size=28, color=GREY_B).next_to(step, DOWN, buff=0.2)
        rowdat = [("explicit Euler", "every $x$ old", "cheap, but overshoots when stiff", RED),
                  ("implicit Euler", "every $x$ new", r"stable, but $x_{\text{new}}$ is inside a sigmoid: iterate every step", ORANGE_L)]
        rows = VGroup(*[VGroup(Tex(a, font_size=28, color=c), Tex(b, font_size=28), Tex(d, font_size=26, color=GREY_B)) for a, b, d, c in rowdat])
        for r in rows:
            r[0].move_to(6.2 * LEFT, aligned_edge=LEFT)
            r[1].move_to(3.6 * LEFT, aligned_edge=LEFT)
            r[2].move_to(1.4 * LEFT, aligned_edge=LEFT)
        rows[1].shift(0.5 * DOWN)
        rows.next_to(q, DOWN, buff=0.4).set_x(0)
        with self.voiceover(text="A solver step turns the derivative into an <bookmark mark='step'/>update: the new x is the old x, "
                                 "plus a time step times the right hand side. The only question is whether each x on the right uses "
                                 "the <bookmark mark='q'/>old value or the new one. <bookmark mark='exp'/>Explicit Euler uses old values "
                                 "everywhere. It is cheap, but with a large decay rate it overshoots. <bookmark mark='imp'/>Implicit "
                                 "Euler uses new values everywhere. It is stable, but then the new x sits inside a sigmoid, and every "
                                 "step needs an iterative solve."):
            self.at("step", Write(step))
            self.at("q", FadeIn(q))
            self.at("exp", FadeIn(rows[0], shift=0.1 * RIGHT))
            self.at("imp", FadeIn(rows[1], shift=0.1 * RIGHT))

        self.play(FadeOut(VGroup(step, q, rows)), run_time=0.5)
        d1 = MathTex(r"f = f(x_{\text{old}}, I)", r"\quad\text{(just a number this step)}", font_size=38, color=N)
        d2 = MathTex(r"x_{\text{new}} = x_{\text{old}} + \Delta t\,\Big[-\big(\tfrac{1}{\tau} + f\big)\,", r"x_{\text{new}}", r"+ f A\Big]", font_size=38)
        d2[1].set_color(B)
        d3 = MathTex(r"x_{\text{new}}\,\Big(1 + \Delta t\,\big(\tfrac{1}{\tau} + f\big)\Big) = x_{\text{old}} + \Delta t\, f A", font_size=38)
        eq3 = MathTex(r"x_{\text{new}} = \frac{x_{\text{old}} + \Delta t\, f\, A}{1 + \Delta t\,\big(1/\tau + f\big)}", font_size=42, color=LTC_C)
        der = VGroup(d1, d2, d3, eq3).arrange(DOWN, buff=0.38).next_to(VGroup(il, bl), DOWN, buff=0.45)
        fl = Tex("fused:", font_size=30, color=LTC_C).next_to(d1, LEFT, buff=0.5)
        with self.voiceover(text="The <bookmark mark='fused'/>fused step splits the difference. <bookmark mark='fo'/>Inside f it uses the "
                                 "old x, so f becomes just a number for this step. <bookmark mark='bx'/>The bare x uses the new value. "
                                 "That leaves a <bookmark mark='lin'/>linear equation in the new x, which "
                                 "<bookmark mark='solve'/>rearranges into a single division."):
            self.at("fused", FadeIn(fl))
            self.at("fo", FadeIn(d1), Indicate(inner, color=N))
            self.at("bx", FadeIn(d2), Indicate(bare, color=B))
            self.at("lin", FadeIn(d3, shift=0.1 * DOWN))
            self.at("solve", FadeIn(eq3, shift=0.1 * DOWN))

        self.play(FadeOut(VGroup(rhs, bare, bl, inner, il, d1, d2, d3, fl)), run_time=0.5)
        self.play(eq3.animate.scale(40 / 42).next_to(ax, RIGHT, buff=0.6).shift(1.6 * UP), FadeIn(plot), run_time=0.9)
        why = Tex(r"same rule every step:\\a blend of $x_{\text{old}}$ and $A$", font_size=28, color=GREY_B).next_to(eq3, DOWN, buff=0.3)
        with self.voiceover(text="It is the same rule on every step; nothing switches at run time. The new x is a "
                                 "<bookmark mark='avg'/>weighted blend of the old x and A, so it <bookmark mark='stable'/>cannot "
                                 "overshoot, whatever the step size, and it costs one evaluation of f, just like explicit Euler."):
            self.at("avg", FadeIn(why))
            self.at("stable", FadeIn(leg[2]), Create(ful), FadeIn(fud), run_time=1.2)

        tab = VGroup(
            VGroup(Tex("", font_size=26), Tex("BPTT", font_size=26, color=LTC_C), Tex("adjoint", font_size=26, color=NODE_C)),
            VGroup(Tex("memory", font_size=26), MathTex(r"O(L\times T)", font_size=28), MathTex(r"O(1)", font_size=28)),
            VGroup(Tex("backward accuracy", font_size=26), Tex("high", font_size=26), Tex("low", font_size=26)),
        )
        for row in tab:
            for k, c in enumerate(row):
                c.move_to(RIGHT * [0, 2.4, 4.0][k])
        for k, row in enumerate(tab):
            row.shift(DOWN * 0.5 * k)
        tab.next_to(why, DOWN, buff=0.5)
        with self.voiceover(text="To train, they unroll the solver and use plain <bookmark mark='bptt'/>backpropagation through time, "
                                 "rather than the adjoint method popular for neural O D Es. It costs <bookmark mark='mem'/>more memory, "
                                 "but the backward pass is <bookmark mark='acc'/>accurate, because nothing has to be re-integrated in "
                                 "reverse."):
            self.at("bptt", FadeIn(tab[0]))
            self.at("mem", FadeIn(tab[1]))
            self.at("acc", FadeIn(tab[2]))
        fade_all(self)


class Expressive(Narrated):
    def construct(self):
        title = Tex("How expressive are they?").scale(0.72).to_edge(UP)
        th = np.linspace(0, TAU, 400)
        circ = Circle(radius=0.9, color=IN_C, stroke_width=3).move_to(5.0 * LEFT + 1.2 * UP)
        cl = MathTex(r"I(t) = (\sin t, \cos t)", font_size=28, color=IN_C).next_to(circ, DOWN, buff=0.2)
        box = RoundedRectangle(corner_radius=0.15, width=2.6, height=1.4, color=GREY_B).move_to(1.6 * LEFT + 1.2 * UP)
        bl = Tex(r"random network\\(1 to 3 layers)", font_size=26).move_to(box)
        a1 = Arrow(circ.get_right(), box.get_left(), buff=0.15, color=GREY_B)
        r = 0.8 + 0.25 * np.sin(5 * th) + 0.12 * np.cos(11 * th)
        latent = VMobject(stroke_color=LTC_C, stroke_width=3).set_points_smoothly(
            [np.array([r[k] * np.cos(th[k] + 0.4 * np.sin(3 * th[k])), r[k] * np.sin(th[k]), 0]) for k in range(0, 400, 4)])
        latent.move_to(2.4 * RIGHT + 1.2 * UP)
        a2 = Arrow(box.get_right(), latent.get_left(), buff=0.2, color=GREY_B)
        ll = Tex(r"hidden states, first 2 PCs", font_size=26, color=LTC_C).next_to(latent, DOWN, buff=0.2)
        lenl = MathTex(r"\ell = \int \Big\|\frac{dz}{dt}\Big\|\,dt", font_size=34).next_to(latent, RIGHT, buff=0.4)
        ill = Tex("latent curve illustrative", font_size=22, color=GREY_D).to_corner(UR, buff=0.15).shift(0.6 * DOWN)
        with self.voiceover(text="To compare expressive power, the authors feed a <bookmark mark='circ'/>circle into "
                                 "<bookmark mark='net'/>randomly weighted networks, project the hidden states onto their "
                                 "<bookmark mark='pca'/>first two principal components, and measure the <bookmark mark='len'/>length "
                                 "of the curve that comes out. A longer, more tangled curve means the network can represent more "
                                 "complex functions."):
            self.play(Write(title), run_time=0.8)
            self.at("circ", Create(circ), FadeIn(cl))
            self.at("net", GrowArrow(a1), Create(box), FadeIn(bl))
            self.at("pca", GrowArrow(a2), Create(latent), FadeIn(ll), FadeIn(ill), run_time=1.2)
            self.at("len", Write(lenl))

        ax = Axes(x_range=[0, 3, 1], y_range=[0, 6, 1], x_length=6.4, y_length=2.6, tips=False,
                  axis_config={"color": GREY_B, "include_ticks": False}).shift(1.65 * DOWN + 0.6 * LEFT)
        yt = VGroup(*[MathTex(f"10^{k}", font_size=24).next_to(ax.c2p(0, k), LEFT, buff=0.12) for k in (1, 3, 5)])
        ytl = Tex(r"trajectory length", font_size=24).rotate(PI / 2).next_to(yt, LEFT, buff=0.15)
        bars, cols = {}, {"Neural ODE": NODE_C, "CT-RNN": CT_C, "LTC": LTC_C}
        for j, name in enumerate(["Neural ODE", "CT-RNN", "LTC"]):
            bars[name] = VGroup()
            for k, v in enumerate(TRAJ[name]):
                x0 = k + 0.22 + 0.2 * j
                bars[name].add(Rectangle(width=ax.x_length / 3 * 0.18, height=ax.c2p(0, np.log10(v))[1] - ax.c2p(0, 0)[1],
                                         fill_color=cols[name], fill_opacity=0.9, stroke_width=0).move_to(ax.c2p(x0 + 0.08, 0), aligned_edge=DOWN))
        layl = VGroup(*[Tex(f"layer {k + 1}", font_size=24).next_to(ax.c2p(k + 0.5, 0), DOWN, buff=0.12) for k in range(3)])
        key = VGroup(*[VGroup(Square(0.18, fill_color=cols[n], fill_opacity=1, stroke_width=0), Tex(n, font_size=24)).arrange(RIGHT, buff=0.1)
                       for n in cols]).arrange(DOWN, aligned_edge=LEFT, buff=0.12).next_to(ax, RIGHT, buff=0.4)
        src = Tex(r"Fig.\ 2A: Hard-tanh, width 100", font_size=22, color=GREY_D).next_to(key, DOWN, buff=0.3, aligned_edge=LEFT)
        with self.voiceover(text="Here are the measured lengths, on a log scale, with hard tanh activations. For "
                                 "<bookmark mark='node'/>neural O D Es and <bookmark mark='ct'/>C T R N Ns, the length grows "
                                 "exponentially with depth, from about a hundred to tens or hundreds of thousands. The "
                                 "<bookmark mark='ltc'/>L T C is already above twelve thousand with a single layer, and grows only "
                                 "gently after that."):
            self.play(Create(ax), FadeIn(yt), FadeIn(ytl), FadeIn(layl), FadeIn(src), run_time=0.8)
            self.at("node", FadeIn(key[0]), LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars["Neural ODE"]], lag_ratio=0.3), run_time=1.0)
            self.at("ct", FadeIn(key[1]), LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars["CT-RNN"]], lag_ratio=0.3), run_time=1.0)
            self.at("ltc", FadeIn(key[2]), LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars["LTC"]], lag_ratio=0.3), run_time=1.0)
        depth = Tex(r"solver steps per input: 0.61 (Neural ODE), 4.05 (CT-RNN), 81.0 (LTC)", font_size=26, color=GREY_B).to_edge(DOWN, buff=0.12)
        with self.voiceover(text="Their theorems give matching lower bounds on this growth. Part of the reason is "
                                 "<bookmark mark='depth'/>computational depth: the solver takes about eighty one steps per input for "
                                 "an L T C, against four for a C T R N N, so each layer is effectively much deeper."):
            self.at("depth", FadeIn(depth, shift=0.1 * UP))
        fade_all(self)


class Results(Narrated):
    def construct(self):
        title = Tex("Time-series benchmarks").scale(0.72).to_edge(UP)
        head = VGroup(Tex("task", font_size=26), Tex("metric", font_size=24, color=GREY_B),
                      *[Tex(n, font_size=26, color=c) for n, c in NAMES])
        xs = [-5.3, -3.4, -1.5, 0.3, 2.2, 4.0, 5.6]
        for m, xx in zip(head, xs):
            m.move_to(RIGHT * xx)
        rows, best = VGroup(), []
        for task, metric, vals, sgn in TABLE3:
            k = int(np.argmax(np.array(vals) * sgn))
            cells = [Tex(task, font_size=26), Tex(metric, font_size=22, color=GREY_B)] + \
                    [Tex(f"{v:.2f}" if "acc" in metric else f"{v:.3f}", font_size=26) for v in vals]
            row = VGroup(*cells)
            for m, xx in zip(row, xs):
                m.move_to(RIGHT * xx)
            rows.add(row)
            best.append(cells[2 + k])
        for k, row in enumerate(rows):
            row.shift(DOWN * (0.62 + 0.5 * k))
        grid = VGroup(head, rows)
        grid.next_to(title, DOWN, buff=0.35)
        hl = VGroup(*[SurroundingRectangle(b, color=YELLOW, buff=0.06, stroke_width=2) for b in best])
        ltcwins = VGroup(*[hl[i] for i in (0, 1, 4, 6)])
        others = VGroup(*[hl[i] for i in (2, 3, 5)])
        col = SurroundingRectangle(VGroup(head[6], *[r[6] for r in rows]), color=LTC_C, buff=0.1, stroke_width=2)
        note = Tex(r"Table 3, mean of 5 runs; squared errors: lower is better", font_size=22, color=GREY_D).to_edge(DOWN, buff=0.2)
        with self.voiceover(text="On seven real time series tasks, from <bookmark mark='g'/>hand gesture segmentation and room "
                                 "occupancy to traffic, power and ozone prediction, the L T C is compared with an L S T M, a C T R N N, "
                                 "a neural O D E and a continuous time G R U, all with thirty two hidden units."):
            self.play(Write(title), run_time=0.8)
            self.at("g", FadeIn(head), LaggedStart(*[FadeIn(r, shift=0.05 * DOWN) for r in rows], lag_ratio=0.12), FadeIn(note), run_time=1.6)
        with self.voiceover(text="The <bookmark mark='col'/>L T C is best on <bookmark mark='wins'/>four of the seven: gesture, "
                                 "occupancy, traffic, where it cuts the error from zero point one seven to about zero point one, and "
                                 "ozone. On the <bookmark mark='rest'/>other three it is close behind the winner."):
            self.at("col", Create(col))
            self.at("wins", LaggedStart(*[Create(b) for b in ltcwins], lag_ratio=0.2), run_time=1.0)
            self.at("rest", LaggedStart(*[Create(b) for b in others], lag_ratio=0.2), run_time=1.0)
        fade_all(self)

        title2 = Tex("Two more tests").scale(0.72).to_edge(UP)
        pa = VGroup(Tex("Person activity (Rubanova et al.\\ split)", font_size=28),
                    VGroup(Tex("best ODE baseline (Latent ODE)", font_size=26, color=NODE_C), Tex(r"84.6\%", font_size=30, color=NODE_C)).arrange(RIGHT, buff=0.4),
                    VGroup(Tex("LTC", font_size=26, color=LTC_C), Tex(r"88.2\%", font_size=30, color=LTC_C)).arrange(RIGHT, buff=0.4),
                    ).arrange(DOWN, aligned_edge=LEFT, buff=0.2).to_edge(LEFT, buff=0.7).shift(0.6 * UP)
        ax = Axes(x_range=[0, 4.2, 1], y_range=[0, 5, 1], x_length=4.2, y_length=3.4, tips=False,
                  axis_config={"color": GREY_B, "include_ticks": False}).to_edge(RIGHT, buff=1.4).shift(0.9 * DOWN)
        cmap = dict(NAMES)
        hb = VGroup()
        for k, (n, v) in enumerate(CHEETAH):
            y = 4.5 - k * 0.9
            bar = Rectangle(width=ax.c2p(v, 0)[0] - ax.c2p(0, 0)[0], height=0.45, fill_color=cmap[n], fill_opacity=0.9, stroke_width=0)
            bar.move_to(ax.c2p(0, y), aligned_edge=LEFT)
            hb.add(VGroup(bar, Tex(n, font_size=22).next_to(bar, LEFT, buff=0.1), Tex(f"{v:.3f}", font_size=22).next_to(bar, RIGHT, buff=0.1)))
        hc = Tex(r"Half-Cheetah dynamics\\test MSE, lower is better", font_size=28).next_to(ax, UP, buff=0.3)
        with self.voiceover(text="On <bookmark mark='pa'/>person activity recognition, with the same split as the latent O D E paper, the "
                                 "L T C reaches <bookmark mark='pal'/>eighty eight point two percent, against eighty four point six "
                                 "for the best O D E model."):
            self.play(Write(title2), run_time=0.8)
            self.at("pa", FadeIn(pa[0]), FadeIn(pa[1]))
            self.at("pal", FadeIn(pa[2], shift=0.1 * RIGHT), Circumscribe(pa[2], color=LTC_C))
        with self.voiceover(text="And on modelling the <bookmark mark='hc'/>physics of a simulated half cheetah robot, predicting its "
                                 "next observation, it has the <bookmark mark='low'/>lowest error of all five models."):
            self.at("hc", FadeIn(hc), LaggedStart(*[GrowFromEdge(b[0], LEFT) for b in hb], lag_ratio=0.15),
                    *[FadeIn(b[1:]) for b in hb], run_time=1.4)
            self.at("low", Indicate(hb[4], color=LTC_C))
        fade_all(self)


class Outro(Narrated):
    def construct(self):
        title = Tex("Limits and outlook").scale(0.72).to_edge(UP)
        lim = VGroup(Tex(r"$\bullet$ vanishing gradients: not the pick for long-term dependencies", font_size=30),
                     Tex(r"$\bullet$ needs a good solver; plain explicit Euler hurts accuracy", font_size=30),
                     Tex(r"$\bullet$ slower and more memory-hungry than neural ODEs", font_size=30)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.2).next_to(title, DOWN, buff=0.5)
        with self.voiceover(text="The authors are upfront about the limits. Like other continuous time models, L T Cs suffer from "
                                 "<bookmark mark='l1'/>vanishing gradients, so they are not the obvious choice for long term "
                                 "dependencies. They depend on a <bookmark mark='l2'/>good solver. And the extra expressivity "
                                 "<bookmark mark='l3'/>costs time and memory."):
            self.play(Write(title), run_time=0.8)
            for k in range(3):
                self.at(f"l{k + 1}", FadeIn(lim[k], shift=0.1 * RIGHT))
        fut = Tex(r"next: causal structure, and control of robots in continuous time", font_size=30, color=TEAL_L).next_to(lim, DOWN, buff=0.5)
        with self.voiceover(text="Their equations resemble dynamic causal models from neuroscience, so they point to "
                                 "<bookmark mark='fut'/>causality, and to controlling robots in continuous time, as natural next "
                                 "steps."):
            self.at("fut", FadeIn(fut, shift=0.1 * UP))
        self.play(FadeOut(lim), FadeOut(fut), FadeOut(title))
        eq = MathTex(r"\frac{dx}{dt} = -\Big[\frac{1}{\tau} + f(x, I, t, \theta)\Big]\,x + f(x, I, t, \theta)\,A", font_size=44, color=LTC_C).shift(0.6 * UP)
        cite = VGroup(Tex("Liquid Time-constant Networks", font_size=34), Tex(CITE, font_size=26, color=GREY_B),
                      Tex(r"code: github.com/raminmh/liquid\_time\_constant\_networks", font_size=24, color=GREY_B)
                      ).arrange(DOWN, buff=0.15).next_to(eq, DOWN, buff=0.7)
        with self.voiceover(text="In one line: a network whose neurons learn not just what to respond to, but <bookmark mark='eq'/>how "
                                 "fast. Thanks for watching."):
            self.play(FadeIn(cite), run_time=0.8)
            self.at("eq", Write(eq), run_time=1.2)
        self.wait(0.6)
        fade_all(self)
