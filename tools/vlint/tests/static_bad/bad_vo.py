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


def num(t):                                       # a label helper that wraps its argument: still a label
    return Tex(r"\textbf{" + t + "}")


class Flash(Narrated):  # expect: shadows-manim, scene-protagonist
    def construct(self):
        pic = card("x.png")
        a = Tex(r"\tau = 1")
        b = Tex("\tau = 2")  # expect: tex-not-raw, control-char
        c = MathTex("\\frac{1}{2}")                 # escaped backslash: fine
        d = MathTex("x" "\\beta")                   # fine
        e = MathTex("\frac{1}{2}")  # expect: tex-not-raw, control-char
        f = MathTex(f"\\alpha = {1}")               # fine
        cite = Tex(r"Fig.\ 1: Smith et al., 2020", font_size=18)  # expect: front-page
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
        with self.voiceover(text="<bookmark mark='au'/>Its authors, led by Ann Lee, Bo Chen, Cy Diaz and Di Evans, work at three universities in two countries."):  # expect: authors-brief
            self.at("au", Indicate(ok))
        with self.voiceover(text="One <bookmark mark='a'/>two. Three <bookmark mark='b'/>four, five <bookmark mark='a'/>six."):  # expect: bookmark-duplicate
            self.at("a", FadeIn(e))
            self.at("b", FadeIn(f))
        with self.voiceover(text="First <bookmark mark='x'/>thing here. Then <bookmark mark='y'/>the next thing."):
            self.at("y", FadeIn(ok))
            self.at("x", Indicate(ok))  # expect: bookmark-order
            self.at("q")  # expect: bookmark-missing
        with self.voiceover(text="A <bookmark mark='p'/>pulse here and a <bookmark mark='u'/>word nobody cues."):  # expect: bookmark-unused
            self.at("p", Indicate(a))
        with self.voiceover(text="Broken <bookmark mark=z/>tag. It is read aloud by the voice."):  # expect: narration-markup
            pass
        with self.voiceover(text="Here is one sentence. Here is another sentence. And a third sentence with no cue."):
            self.at("w")  # expect: bookmark-missing
        with self.voiceover(text="Loop <bookmark mark='m'/>one and <bookmark mark='n'/>two. Cues come from a loop here."):
            for m in "mn":
                self.at(m)                              # computed marks: order and unused checks stand down
        with self.voiceover(text="The <bookmark mark='g'/>run begins. Then the voice keeps going and going, naming a part and then another part and then a third one, and nothing at all happens on the screen while all of that is said aloud."):  # expect: cue-gap
            self.at("g", FadeIn(ok))
        with self.voiceover(text="The beam <bookmark mark='s'/>arrives and after a long flight through the room its width has grown."):
            self.at("s", FadeIn(ok))
        with self.voiceover(text="The beam arrives, and <bookmark mark='w'/>its width grows."):    # bookmarked: fine
            self.at("w", Indicate(ok))  # expect: property-scope
        with self.voiceover(text="The ball <bookmark mark='v'/>travels to the far wall and rests against it."):
            self.at("v", Indicate(ok))  # expect: pulse-for-event
        with self.voiceover(text="The ball <bookmark mark='vv'/>travels to the far wall and rests against it."):
            self.at("vv", ok.animate.shift(RIGHT))      # the ball actually goes there: fine
        with self.voiceover(text="Then a <bookmark mark='lt'/>live test: the <bookmark mark='q'/>quest."):  # expect: narration-appendage
            self.at("lt", Indicate(ok))
            self.at("q", Indicate(ok))
        with self.voiceover(text="It is not a wrong <bookmark mark='nr'/>answer. It is a non-answer."):  # expect: narration-tic
            self.at("nr", Indicate(ok))
        line = Tex("\tau")  # vlint: ignore[tex-not-raw, control-char] suppression on the line works
        sig = MathTex("\sigma")  # expect: syntax-warning, tex-not-raw
        # vlint: ignore-next[long-text] and on the line before
        long2 = Tex(r"another label that is far too long to be a label on the screen of a video")
        t1 = Tex(r"$a$$b$")  # expect: gx-tex
        t2 = Tex(r"costs \$5")  # expect: gx-tex
        t4 = lab(r"+ PBC")  # expect: gx-tex
        t5 = Tex(r"- 3 dB")  # expect: gx-tex
        t6 = lab(r"= channel")  # expect: gx-tex
        t6 = lab(r"with PBC", 24)                       # a word first: fine
        t3 = Tex(r"one\\two")                           # a line break works in GX: fine
        self.add_fixed_in_frame_mobjects(t1, t2, t3)
        self.remove(t2)
        self.play(FadeIn(t2), Write(t3))                # removed first, or introduced at once: fine
        self.play(Write(t1))  # expect: fixed-frame-early
        with self.voiceover(text="Now we substitute the first result into the second."):  # expect: algebra-shown
            self.play(FadeOut(t1), FadeIn(t3))
        with self.voiceover(text="The EM step runs on the PET data."):  # expect: acronym-unspelled
            self.play(FadeOut(t1), FadeIn(t3))
        with self.voiceover(text="The E M step runs on the PET data."):  # spelled out, PET said as a word: fine
            self.play(FadeOut(t1), FadeIn(t3))
        t4 = Tex(r"the E M step")  # expect: acronym-spaced-on-screen
        t5 = Tex(r"the EM step, $A B$")  # closed up on screen, maths ignored: fine
        point(self, spot(f1, (0, 0, 10, 10)), WHITE)  # expect: pointer-white-on-page
        point(self, spot(f1, (0, 0, 10, 10)), TEAL_L)  # shows on white: fine
        point(self, spot(f1, (0, 0, 10, 10)), color=WHITE)  # expect: pointer-white-on-page
        vbars(0, 0, [1, 2], [r"W L S", r"OSEM"])  # expect: acronym-spaced-on-screen
        with self.voiceover(text="Reference four is the paper of the previous video."):  # expect: watch-order
            self.play(FadeOut(t1), FadeIn(t3))
        n1 = Tex(r"gain 3.66")  # expect: number-unsourced
        n2 = Tex(r"gain 3.59, or 3.6")                  # the source's number, and a rounding of it: fine
        n4 = Tex(r"1{,}600 counts, 2 million decays, 45\%")  # written differently, the same numbers: fine
        n5 = num("17 000")  # expect: number-unsourced
        n6 = Tex(r"since 1997")  # expect: number-unsourced
        n3 = Tex(r"ours: 0.4 mm")  # vlint: ignore[number-unsourced] computed: the scene's own k-NN demo
        with self.voiceover(text="The gain is three point six six, over sixteen hundred counts."):  # expect: number-unsourced
            self.play(FadeOut(t1), FadeIn(t3))
        with self.voiceover(text="Page forty shows a gain of three point five nine in twelve steps."):  # a place, the source's number, a small count: fine
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


def _gx_setter_bug(m):
    return FadeIn(m).set_run_time(0.5)              # expect: gx-anim-setter
