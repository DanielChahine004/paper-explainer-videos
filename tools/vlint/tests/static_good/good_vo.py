# A clean script for `vlint selftest`: no rule may report a warning or error here.
from common import *  # noqa


def card(path):
    return Group(ImageMobject(path).set_height(2), Square())


class Intro(Narrated):
    def construct(self):
        pic = card("x.png")
        eq = MathTex(r"\tau = \frac{1}{2}")
        lab = Tex(r"\textbf{1.8} mm, $a$ and $b$, ``quoted''", font_size=28)
        self.add_fixed_in_frame_mobjects(lab)
        self.remove(lab)
        row = Group(pic, VGroup(eq, lab).arrange(DOWN))
        with self.voiceover(text="The <bookmark mark='p'/>picture comes first. Then the <bookmark mark='e'/>equation, "
                                 "and the <bookmark mark='n'/>number."):
            self.at("p", FadeIn(pic))
            self.at("e", Write(eq))
            self.at("n", FadeIn(lab))
        with self.voiceover(text="Now we <bookmark mark='i'/>point at it again."):
            self.at("i", Indicate(lab))
