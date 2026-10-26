"""Runtime fixture for `vlint selftest`: a silent scene with planted layout bugs. EXPECT counts the findings each
runtime rule must report; the exempted and switched-off cases must report nothing."""
import sys
from pathlib import Path

from manim import *

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from vlint.runtime import Checked, vlint_ok  # noqa: E402

EXPECT = {"frame-clip": 1, "text-overlap": 1, "vanished-after-intro": 1, "bookmark-unfired": 2, "indicate-image": 1, "text-chain": 1, "arrow-over-label": 1, "layout-crowded": 1, "layout-balance": 1, "arrow-skew": 1, "title-margin": 1, "line-over-label": 1, "redraw-jitter": 1, "shape-overlap": 1, "title-gap": 1, "faint-mark": 2, "frame-margin": 1, "icon-idle": 1, "intro-of-visible": 1, "number-undrawn": 1}


class Fixture(Checked, Scene):
    def construct(self):
        clipped = Text("cut off", font_size=40).move_to(RIGHT * 7.0)                 # frame-clip
        gone = Text("offscreen", font_size=40).move_to(RIGHT * 12)                  # wholly outside: fine
        a = Text("label one", font_size=36).move_to(UP * 2)
        b = Text("label two", font_size=36).move_to(UP * 2 + RIGHT * 0.3)          # text-overlap
        c = Text("pulsed", font_size=36).move_to(DOWN * 2)
        self.play(FadeIn(clipped), FadeIn(gone), FadeIn(a), FadeIn(b), run_time=0.2)
        self.play(FadeIn(c), Indicate(c), run_time=0.2)                             # vanished-after-intro
        d = vlint_ok(Text("allowed", font_size=36).move_to(DOWN * 0.5), "text-overlap")
        e = Text("allowed too", font_size=36).move_to(DOWN * 0.5 + RIGHT * 0.2)
        self.play(FadeIn(d), FadeIn(e), run_time=0.2)                               # exempt: fine
        pic = Group(ImageMobject(np.full((8, 8, 4), 200, dtype=np.uint8)).set_height(1).move_to(LEFT * 4), Square(1).move_to(LEFT * 4))
        self.add(pic)
        self.play(Indicate(pic), run_time=0.2)                                      # indicate-image
        self.play(Indicate(pic[1]), run_time=0.2)                                   # the frame: fine
        def chain(icon):
            bx = VGroup(*[VGroup(RoundedRectangle(width=1.4, height=0.6), Text(w, font_size=20)) for w in ("in", "net", "out")])
            bx.arrange(RIGHT, buff=0.6).move_to(UP * 3.1)
            if icon:
                bx[1][1].scale(0.6).shift(DOWN * 0.15)
                bx[1].add(Circle(radius=0.1).move_to(bx[1][0].get_center() + UP * 0.12))
            return VGroup(bx, *[Arrow(bx[k].get_right(), bx[k + 1].get_left(), buff=0.05) for k in range(2)])
        good = chain(True)
        self.play(FadeIn(good), run_time=0.2)                                       # a drawn node breaks it: fine
        self.play(FadeOut(good), run_time=0.2)
        bad = chain(False)
        self.play(FadeIn(bad), run_time=0.2)                                        # text-chain
        self.play(FadeOut(bad), run_time=0.2)
        mid = Text("struck", font_size=30).move_to(DOWN * 3.2)
        thru = Arrow(LEFT * 3 + DOWN * 3.2, RIGHT * 3 + DOWN * 3.2, buff=0)
        self.play(FadeIn(mid), GrowArrow(thru), run_time=0.2)                       # arrow-over-label
        self.play(FadeOut(mid), FadeOut(thru), run_time=0.2)
        sk = Arrow(LEFT * 2 + DOWN * 1.0, RIGHT * 2 + DOWN * 1.35, buff=0)          # arrow-skew
        ok1 = Arrow(LEFT * 2 + DOWN * 2.0, RIGHT * 2 + DOWN * 2.0, buff=0)           # level: fine
        ok2 = Arrow(LEFT * 2 + UP * 0.5, RIGHT * 0 + UP * 1.6, buff=0)               # a real diagonal: fine
        self.play(GrowArrow(sk), GrowArrow(ok1), GrowArrow(ok2), run_time=0.2)
        self.play(FadeOut(sk), FadeOut(ok1), FadeOut(ok2), run_time=0.2)
        hi = Text("a title set too high", font_size=32).to_edge(UP, buff=0.3)        # title-margin
        lo = Text("a title set right", font_size=32).to_edge(UP, buff=0.8).shift(RIGHT * 3)
        bar = Rectangle(width=1.5, height=0.3).next_to(lo, DOWN, buff=0.05)                  # title-gap
        sub = Text("a subtitle", font_size=24).next_to(lo, DOWN, buff=0.08)                     # text may sit close: fine
        sub.shift(LEFT * 2.5)
        self.play(FadeIn(hi), FadeIn(lo), FadeIn(bar), FadeIn(sub), run_time=0.2)
        self.remove(bar, sub)
        self.play(FadeOut(hi), FadeOut(lo), run_time=0.2)
        crv = Line(LEFT * 3 + DOWN * 2.6, RIGHT * 3 + DOWN * 2.6)
        on = Text("on the line", font_size=30).move_to(LEFT * 1.8 + DOWN * 2.6)                 # line-over-label
        off = Text("beside the line", font_size=30).next_to(crv, UP, buff=0.15).shift(RIGHT * 1.8)   # fine
        box = SurroundingRectangle(off, buff=0.1)                                   # an outline around a label: fine
        self.play(Create(crv), FadeIn(on), FadeIn(off), Create(box), run_time=0.2)
        self.play(FadeOut(crv), FadeOut(on), FadeOut(off), FadeOut(box), run_time=0.2)
        k = ValueTracker(0.0)
        saw = always_redraw(lambda: VMobject().set_points_as_corners([[x, -1 + 0.4 * ((k.get_value() * 9) % 1), 0] for x in np.linspace(-3, 3, 30)]))
        glide = always_redraw(lambda: VMobject().set_points_as_corners([[x, 1 + 0.3 * np.sin(x + k.get_value()), 0] for x in np.linspace(-3, 3, 30)]))
        self.add(saw, glide)
        self.play(k.animate.set_value(1.0), run_time=0.2)                          # redraw-jitter (saw only)
        self.remove(saw, glide)
        with self.vlint_off("frame-clip"):
            self.play(FadeIn(Text("edge on purpose", font_size=30).move_to(LEFT * 7.2 + DOWN * 3)), run_time=0.2)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.2)
        faint = Dot(RIGHT * 5 + DOWN * 3, color="#1a1d26")                               # faint-mark
        dim = Dot(RIGHT * 5.6 + DOWN * 3, fill_opacity=0.25)                            # dim but visible: fine
        pad = Square(1, fill_color=WHITE, fill_opacity=1, stroke_width=0).move_to(RIGHT * 3 + DOWN * 3)
        pale = Dot(pad.get_center() + LEFT * 0.25, color="#eeeeee")                     # faint-mark (on the pad)
        eye = Dot(pad.get_center() + RIGHT * 0.25, color=BLACK)                         # black on white: fine
        low = MathTex(r"\frac{a}{b}", font_size=48).to_edge(DOWN, buff=0.08).shift(LEFT * 3)    # frame-margin
        cred = Text("credit line", font_size=16).to_edge(DOWN, buff=0.08)                      # a footnote: fine
        self.play(FadeIn(faint), FadeIn(dim), FadeIn(pad), FadeIn(pale), FadeIn(eye), FadeIn(low), FadeIn(cred), run_time=0.2)
        self.remove(faint, dim, pad, pale, eye, low, cred)
        e1, e2 = MathTex("a", "+", "b"), MathTex("b", "+", "a", "+", "c")
        self.add(e1)
        self.play(TransformMatchingShapes(e1, e2), run_time=0.2)                     # pieces fade in inside it: fine
        self.remove(e2)
        t1 = Triangle(fill_opacity=0.5).scale(0.8).move_to(LEFT * 5.6 + UP * 1.7)
        t2 = Triangle(fill_opacity=0.5).scale(0.8).move_to(LEFT * 5.1 + UP * 1.2)                 # shape-overlap
        lay = Square(0.7, fill_opacity=0.3).move_to(LEFT * 3.4 + UP * 1.6)
        dot_in = Circle(0.2, fill_opacity=1).move_to(lay)                                         # a layer inside: fine
        self.add(t1, t2, lay, dot_in)
        idle = VGroup(*[Square(0.3).shift(RIGHT * 0.4 * k) for k in range(3)]).move_to(RIGHT * 4 + UP * 1.5)
        idle_l = Text("idea", font_size=24).next_to(idle, DOWN, buff=0.15)                         # icon-idle
        used = VGroup(*[Circle(0.15).shift(RIGHT * 0.4 * k) for k in range(3)]).move_to(RIGHT * 4 + DOWN * 1.5)
        used_l = Text("used", font_size=24).next_to(used, DOWN, buff=0.15)
        self.play(FadeIn(idle), FadeIn(idle_l), FadeIn(used), FadeIn(used_l), run_time=0.2)
        self.play(Indicate(used[1]), run_time=0.2)                                  # a part pulsed: fine
        self.play(FadeOut(idle), FadeOut(idle_l), FadeOut(used), FadeOut(used_l), run_time=0.2)
        early = Square(0.5).move_to(LEFT * 5 + DOWN * 2.6)
        self.add(early)                                                             # on screen before its cue
        self.wait(0.1)
        self.play(FadeIn(early), run_time=0.2)                                      # intro-of-visible
        late = Square(0.5).move_to(LEFT * 3.5 + DOWN * 2.6)
        self.play(FadeIn(late), run_time=0.2)                                       # introduced when added: fine
        quick = Square(0.5).move_to(LEFT * 2 + DOWN * 2.6)
        self.add(quick)
        self.play(FadeIn(quick), run_time=0.2)                                      # no frame between: fine
        self.play(FadeOut(early), FadeOut(late), FadeOut(quick), run_time=0.2)
        self.vlint.event("vo_open", text="It is twenty two centimetres wide and tilts fifty seven degrees.")
        spec = Text("22 cm", font_size=30).move_to(RIGHT * 4 + DOWN * 2.6)
        self.play(FadeIn(spec), run_time=0.2)                                       # 22 drawn: fine
        self.vlint.event("vo_close")                                                # number-undrawn (57)
        self.play(FadeOut(spec), run_time=0.2)
        grow = ValueTracker(10.0)
        readout = always_redraw(lambda: DecimalNumber(grow.get_value(), num_decimal_places=0).move_to(DOWN * 2.6))
        self.add(readout)
        with self.vlint_off("layout-balance"):
            self.vlint.event("vo_open", text="It climbs to forty percent.")
            self.play(grow.animate.set_value(39.8), run_time=0.2)                  # a live readout showing 40: fine
            self.vlint.event("vo_close")
        self.remove(readout)
        p1 = Square(1.5).move_to(LEFT * 5 + DOWN * 0.5)
        p2 = Square(1.5).next_to(p1, RIGHT, buff=0.1)                               # layout-crowded, layout-balance
        self.play(FadeIn(p1), FadeIn(p2), run_time=0.2)
        self.vlint.event("vo_open", text="One <bookmark mark='a'/>two <bookmark mark='b'/>three.")
        self.vlint.event("cue", mark="a")
        self.vlint.event("cue", mark="zz")                                          # not in the text
        self.vlint.event("vo_close")                                                # 'b' never reached
