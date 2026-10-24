"""Runtime fixture for `vlint selftest`: a silent scene with planted layout bugs. EXPECT counts the findings each
runtime rule must report; the exempted and switched-off cases must report nothing."""
import sys
from pathlib import Path

from manim import *

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from vlint.runtime import Checked, vlint_ok  # noqa: E402

EXPECT = {"frame-clip": 1, "text-overlap": 1, "vanished-after-intro": 1, "bookmark-unfired": 2}


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
        with self.vlint_off("frame-clip"):
            self.play(FadeIn(Text("edge on purpose", font_size=30).move_to(LEFT * 7.2 + DOWN * 3)), run_time=0.2)
        self.vlint.event("vo_open", text="One <bookmark mark='a'/>two <bookmark mark='b'/>three.")
        self.vlint.event("cue", mark="a")
        self.vlint.event("cue", mark="zz")                                          # not in the text
        self.vlint.event("vo_close")                                                # 'b' never reached
