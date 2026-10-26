# Planted bugs for `vlint selftest`: every line marked "expect: <rule>" must produce exactly that finding, and no
# other line may produce any warning or error. Each bug is one that reached a real render.
from common import *  # noqa


def card(path):                                   # a helper that returns an image, found by inference
    im = ImageMobject(path)
    return im.set_height(2)


def framed(path):
    return Group(card(path), Square())


def lab(t, fs=26):                                # a label helper: its first argument goes straight to Tex
    return Tex(t, font_size=fs)


class Flash(Narrated):  # expect: shadows-manim
    def construct(self):
        pic = card("x.png")
        a = Tex(r"\tau = 1")
        b = Tex("\tau = 2")  # expect: tex-not-raw, control-char
        c = MathTex("\\frac{1}{2}")                 # escaped backslash: fine
        d = MathTex("x" "\\beta")                   # fine
        e = MathTex("\frac{1}{2}")  # expect: tex-not-raw, control-char
        f = MathTex(f"\\alpha = {1}")               # fine
        g = lab(rf"	extbf{{{2}}} mm")  # expect: control-char
        row = VGroup(a, pic)  # expect: vgroup-non-vmobject
        row2 = VGroup(a, framed("y.png"))  # expect: vgroup-non-vmobject
        ok = Group(a, pic)
        box = VGroup()
        box.add(card("z.png"))  # expect: vgroup-non-vmobject
        words = Tex(r"this label is really a whole sentence that the narration should be saying instead")  # expect: long-text
        ax = Axes()
        k = ValueTracker(1.0)
        wob = always_redraw(lambda: ax.plot(lambda x: np.exp(-k.get_value() * x * x), color=RED))  # expect: redraw-plot
        small = Tex(r"source: a long credit line with many words is fine at footnote size", font_size=16)
        self.play(FadeIn(a), Indicate(a))  # expect: intro-and-pulse
        self.play(AnimationGroup(Create(b), Circumscribe(b)))  # expect: intro-and-pulse
        self.play(Succession(FadeIn(c), Indicate(c)))   # in turn: fine
        self.play(FadeIn(d))
        self.play(Indicate(d))                          # separate plays: fine
        with self.voiceover(text="One <bookmark mark='a'/>two. Three <bookmark mark='b'/>four, five <bookmark mark='a'/>six."):  # expect: bookmark-duplicate
            self.at("a", FadeIn(e))
            self.at("b", FadeIn(f))
        with self.voiceover(text="First <bookmark mark='x'/>thing here. Then <bookmark mark='y'/>the next thing."):
            self.at("y", FadeIn(ok))
            self.at("x", Indicate(ok))  # expect: bookmark-order
            self.at("q")  # expect: bookmark-missing
        with self.voiceover(text="A <bookmark mark='p'/>pulse here and a <bookmark mark='u'/>word nobody cues."):  # expect: bookmark-unused
            self.at("p", Indicate(a))
        with self.voiceover(text="Broken <bookmark mark=z/>tag. It is read aloud by the voice."):  # expect: narration-markup, cue-density
            pass
        with self.voiceover(text="Here is one sentence. Here is another sentence. And a third sentence with no cue."):  # expect: cue-density
            self.at("w")  # expect: bookmark-missing
        with self.voiceover(text="Loop <bookmark mark='m'/>one and <bookmark mark='n'/>two. Cues come from a loop here."):
            for m in "mn":
                self.at(m)                              # computed marks: order and unused checks stand down
        with self.voiceover(text="The beam <bookmark mark='s'/>arrives and after a long flight through the room its width has grown."):  # expect: property-cue
            self.at("s", FadeIn(ok))
        with self.voiceover(text="The beam arrives, and <bookmark mark='w'/>its width grows."):    # bookmarked: fine
            self.at("w", Indicate(ok))
        with self.voiceover(text="Then a <bookmark mark='lt'/>live test: the <bookmark mark='q'/>quest."):  # expect: narration-appendage
            self.at("lt", Indicate(ok))
            self.at("q", Indicate(ok))
        line = Tex("\tau")  # vlint: ignore[tex-not-raw, control-char] suppression on the line works
        sig = MathTex("\sigma")  # expect: syntax-warning, tex-not-raw
        # vlint: ignore-next[long-text] and on the line before
        long2 = Tex(r"another label that is far too long to be a label on the screen of a video")
        t1 = Tex(r"$a$$b$")  # expect: gx-tex
        t2 = Tex(r"costs \$5")  # expect: gx-tex
        t4 = lab(r"+ PBC")  # expect: gx-tex
        t5 = Tex(r"- 3 dB")  # expect: gx-tex
        t6 = lab(r"with PBC", 24)                       # a word first: fine
        t3 = Tex(r"one\\two")                           # a line break works in GX: fine
        self.add_fixed_in_frame_mobjects(t1, t2, t3)
        self.remove(t2)
        self.play(FadeIn(t2), Write(t3))                # removed first, or introduced at once: fine
        self.play(Write(t1))  # expect: fixed-frame-early
        with self.voiceover(text="Now we substitute the first result into the second."):  # expect: algebra-shown
            self.play(FadeOut(t1), FadeIn(t3))
        eq = MathTex(r"P", r"=", r"\tfrac12\sum", r"\min(p_A, p_B)")
        with self.voiceover(text="Its <bookmark mark='e'/>error is half the summed overlap of the two."):
            self.at("e", Write(eq))  # expect: equation-talked-over
        with self.voiceover(text="That <bookmark mark='m'/>minimum is awkward. So <bookmark mark='k'/>bound it."):
            self.at("m", Write(eq))                     # a part is cued in the block: fine
            self.at("k", Indicate(eq[3]))


class Circle(Narrated):  # expect: shadows-manim
    def construct(self):
        config.pixel_height = 2160  # expect: quality-cap
        self.wait()


class Orphan(Narrated):
    def construct(self):
        self.wait()
