"""Runtime fixture for `vlint selftest`: a silent scene with planted layout bugs. EXPECT counts the findings each
runtime rule must report; the exempted and switched-off cases must report nothing."""
import sys
from pathlib import Path

from manim import *

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from vlint.runtime import Checked, vlint_ok  # noqa: E402

EXPECT = {"frame-clip": 1, "text-overlap": 1, "vanished-after-intro": 1, "bookmark-unfired": 2, "indicate-image": 1, "text-chain": 1, "arrow-over-label": 1}


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
        with self.vlint_off("frame-clip"):
            self.play(FadeIn(Text("edge on purpose", font_size=30).move_to(LEFT * 7.2 + DOWN * 3)), run_time=0.2)
        self.vlint.event("vo_open", text="One <bookmark mark='a'/>two <bookmark mark='b'/>three.")
        self.vlint.event("cue", mark="a")
        self.vlint.event("cue", mark="zz")                                          # not in the text
        self.vlint.event("vo_close")                                                # 'b' never reached
