# Planted bugs for the plan-* rules (vlint selftest). A video with a plan.md is held to it: the words must be
# the planned words, the focus must be a thing the scene builds, and every mark must do what its line says.
from common import *  # noqa


class One(Narrated):
    def construct(self):
        ttl = title(r"one")
        sh = Circle()
        box = Square().shift(RIGHT * 2)
        self.add(ttl)
        with self.voiceover(text="The <bookmark mark='a'/>shell opens out, and the <bookmark mark='b'/>box is "
                                 "named again."):
            self.at("a", Indicate(sh))                       # expect: plan-action, pulse-for-event
            self.at("b", Indicate(box))


class Two(Narrated):
    def construct(self):
        ttl = title(r"two")
        bar = Rectangle(height=1, width=0.4)
        self.add(ttl)
        with self.voiceover(text="The <bookmark mark='c'/>bar grows."):   # expect: plan-narration
            self.at("c", bar.animate.stretch(2.0, 1))


class Three(Narrated):                                       # expect: plan-missing
    def construct(self):
        ttl = title(r"three")
        dot = Dot()
        self.add(ttl)
        with self.voiceover(text="A <bookmark mark='d'/>dot arrives."):
            self.at("d", FadeIn(dot))


class Four(Narrated):
    def construct(self):
        ttl = title(r"four")
        det = Square()
        arr = Arrow(LEFT, RIGHT)
        self.add(ttl, det)
        with self.voiceover(text="The <bookmark mark='f'/>detector is replaced, and its "
                                 "<bookmark mark='g'/>width grows."):
            self.at("f", ReplacementTransform(det, arr))      # expect: object-morph
            self.at("g", Indicate(det))                       # expect: property-scope
