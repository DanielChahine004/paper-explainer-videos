"""Template: copy this folder to videos/<name>/, rename this file, and set SCRIPT, OUT and SCENES in
render.sh. Read docs/DESIGN.md first. Each scene is a Narrated class: write the narration with
<bookmark mark='x'/> tags placed right before the word a visual belongs to, and cue the visual with
self.at("x", animation).

Source: <full citation of the paper, its DOI and its licence>. State here which numbers come from
where, which figures are reused (licence permitting) and what is computed in the scenes.
Render with render.sh, or one scene: pixi run manim -ql template_vo.py Opening
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import *  # noqa: E402,F401

ACCENT = TEAL_L


class Opening(Narrated):
    def construct(self):
        title = Tex(r"\textbf{Paper title}", font_size=46).to_edge(UP, buff=0.4)
        who = Tex(r"Authors, Journal Year", font_size=26, color=GREY_B).next_to(title, DOWN, buff=0.2)
        box = Square(1.6, color=ACCENT, fill_opacity=0.2).shift(LEFT * 2.5 + DOWN * 0.5)
        num = Tex(r"\textbf{42\%}", font_size=48, color=ACCENT).shift(RIGHT * 2.5 + DOWN * 0.5)
        with self.voiceover(text="This video explains <bookmark mark='t'/>a paper about something. "
                                 "<bookmark mark='b'/>Here is the object it studies, <bookmark mark='n'/>and the number "
                                 "that matters most."):
            self.at("t", Write(title), FadeIn(who), run_time=1.0)
            self.at("b", FadeIn(box))
            self.at("n", FadeIn(num, shift=0.1 * UP))
        self.wait(0.5)
        fade_all(self)


class Mechanism(Narrated):
    def construct(self):
        title = Tex(r"how it works", font_size=34).to_edge(UP, buff=0.35)
        ax = Axes(x_range=[0, 10, 2], y_range=[0, 1.1, 0.5], x_length=7, y_length=3.2, tips=False,
                  axis_config={"color": GREY_B}).shift(DOWN * 0.4)
        k = ValueTracker(1.0)
        curve = always_redraw(lambda: ax.plot(lambda x: np.exp(-((x - 5) / k.get_value()) ** 2), x_range=[0, 10], color=ACCENT))
        width = VGroup(Tex(r"width", font_size=24, color=GREY_B), DecimalNumber(1.0, num_decimal_places=1, font_size=30))
        width[1].add_updater(lambda m: m.set_value(k.get_value()))
        width.arrange(RIGHT, buff=0.15).next_to(ax, UP, buff=0.2)
        fit_frame(VGroup(ax, width))
        with self.voiceover(text="Show the cause, then vary it. <bookmark mark='c'/>Here is the effect as a shape, "
                                 "<bookmark mark='v'/>and as the cause grows, the shape widens in step."):
            self.play(Write(title), Create(ax), run_time=0.8)
            self.at("c", Create(curve), FadeIn(width))
            self.at("v", k.animate.set_value(2.5), run_time=2.0)
        self.wait(0.5)
        fade_all(self)
