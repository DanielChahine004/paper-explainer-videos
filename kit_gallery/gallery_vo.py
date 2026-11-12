"""kit_gallery: every primitive in kit.py, drawn and animated once, so a change to kit is seen under both engines
(check.sh runs it in CE skip mode, run_v.sh renders it with ManimGX) before a video depends on it. Not a paper
video: it is the test and the catalogue. A primitive promoted into kit gets a part in one of these scenes.
    MSYS_NO_PATHCONV=1 wsl bash /mnt/c/.../tools/check.sh kit_gallery
    MSYS_NO_PATHCONV=1 wsl bash -c 'QUALITY=-ql bash /mnt/c/.../tools/run_v.sh kit_gallery'
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kit import *  # noqa: E402,F401,F403

A = Path(__file__).resolve().parent / "assets"


class Snippet(Narrated):
    def construct(self):
        ttl = title("Code, as it is written")
        cd = code(["auto* rm = G4RunManagerFactory::CreateRunManager(type);",
                   "rm->SetUserInitialization(new Detector);",
                   "rm->Initialize();",
                   "rm->BeamOn(n);"], cw=0.16)
        lput(cd, -6.4, 1.4)
        cd.set_opacity(0.35)
        name = part(cd[1], "SetUserInitialization")
        tm = term(["event 0: 0 keV", "event 1: 511 keV"], w=5.2)
        tm.move_to(P(3.4, -2.0))
        one = mono("main.cc", 0.18, TEAL_L).move_to(P(-4.6, -2.0))
        with self.voiceover(text="<bookmark mark='a'/>A block of code comes on dimmed. <bookmark mark='b'/>The voice "
                                 "reads the first line, <bookmark mark='c'/>then the second, <bookmark mark='d'/>and one "
                                 "name inside it turns orange."):
            self.play(FadeIn(ttl), run_time=0.5)
            self.at("a", FadeIn(cd), FadeIn(one))
            self.at("b", *lit(cd, 0))
            self.at("c", *lit(cd, 1))
            self.at("d", name.animate.set_color(ORANGE_L))
        with self.voiceover(text="<bookmark mark='t'/>A terminal prints its output <bookmark mark='u'/>one line at a time."):
            self.at("t", FadeIn(tm[0]), FadeIn(tm[1]), FadeIn(tm.lines[0]))
            self.at("u", FadeIn(tm.lines[1], shift=UP * 0.1))


class Parts(Narrated):
    def construct(self):
        ttl = title("Objects, files and the framework they plug into")
        sb = slots_box(("Detector", "Physics", "Actions"), w=9.0, h=2.6, title="G4RunManager", color=GREY_B)
        sb.move_to(P(-1.6, 0.6))
        cards = VGroup(*[card(n, c, w=sb.slots[0].width, h=sb.slots[0].height)
                         for n, c in (("Detector", BLUE_L), ("Physics", PURPLE_L), ("Actions", ORANGE_L))])
        cards.arrange(RIGHT, buff=0.3).move_to(P(-1.6, -2.4))
        ft = ftree("app/", ["slab.cc", "Detector.cc", "Physics.hh"], [WHITE, BLUE_L, PURPLE_L])
        lput(ft, 4.4, 1.8)
        tl = tool("tri", "cmake", WHITE).move_to(P(5.2, -2.2))
        with self.voiceover(text="<bookmark mark='a'/>The framework has a slot for each object it needs. "
                                 "<bookmark mark='b'/>Your three objects <bookmark mark='c'/>go into the slots."):
            self.play(FadeIn(ttl), run_time=0.5)
            self.at("a", FadeIn(sb))
            self.at("b", FadeIn(cards))
            self.at("c", *[c.animate.move_to(sb.slots[i]) for i, c in enumerate(cards)], run_time=1.2)
        with self.voiceover(text="<bookmark mark='f'/>The files sit in a folder, <bookmark mark='g'/>and a tool "
                                 "<bookmark mark='h'/>reads one of them."):
            self.at("f", FadeIn(ft))
            self.at("g", FadeIn(tl))
            self.at("h", ft.cards[1].animate.set_color(YELLOW), tl.icon.animate.rotate(PI / 3))


class Flow(Narrated):
    def construct(self):
        ttl = title("What calls what")
        tr = tree([(0, "main", WHITE), (1, "Initialize()", GREY_B), (2, "Detector::Construct()", BLUE_L),
                   (1, "BeamOn(n)", GREY_B), (2, "Gun::GeneratePrimaries", ORANGE_L),
                   (2, "Stepping::UserSteppingAction", TEAL_L)], cw=0.15)
        lput(tr, -6.6, 1.6)
        rn = runner().move_to(rowpt(tr, 0))
        ns = nest(("Run", "Event", "Step"), w=6.0, h=4.2).move_to(P(3.5, -0.5))
        hk = mono("BeginOfEventAction", 0.12, ORANGE_L).next_to(ns.hook(1, LEFT), RIGHT, buff=0)
        ln = lane("worker 0", w=6.0).move_to(P(-3.2, -3.0))
        chip = token("event 7", ORANGE_L, w=1.3).move_to(P(ln.x(0.1), ln.strip.get_center()[1]))
        with self.voiceover(text="<bookmark mark='a'/>The call tree comes on, <bookmark mark='b'/>and a marker walks "
                                 "<bookmark mark='c'/>down to the call that runs now."):
            self.play(FadeIn(ttl), run_time=0.5)
            self.at("a", FadeIn(tr))
            self.at("b", FadeIn(rn))
            self.at("c", rn.animate.move_to(rowpt(tr, 4)))
        with self.voiceover(text="<bookmark mark='n'/>Loops sit one inside another, <bookmark mark='h'/>with a hook "
                                 "named on its own level. <bookmark mark='l'/>Each worker has a lane, <bookmark mark='m'/>and "
                                 "an event moves along it."):
            self.at("n", FadeIn(ns))
            self.at("h", FadeIn(hk))
            self.at("l", FadeIn(ln), FadeIn(chip))
            self.at("m", chip.animate.move_to(P(ln.x(0.9), ln.strip.get_center()[1])))


class Stack(Narrated):
    def construct(self):
        ttl = title("Stacks, records, clocks and budgets")
        st = stack_frame(4).move_to(P(-5.0, 0.0))
        toks = [token(r"$\gamma$", YELLOW), token(r"e$^-$", TEAL_L)]
        for t in toks:
            t.move_to(P(-5.0, 2.6))
        rec = cells(("x", "y", "z", "t", "e")).move_to(P(1.2, 1.4))
        ax = time_axis(6.0, "global time").move_to(P(1.2, -0.6))
        ga = gauge(0.0, 3.0, 1.2, name="mean free paths left").move_to(P(1.2, -2.6))
        with self.voiceover(text="<bookmark mark='a'/>Two tracks <bookmark mark='b'/>are pushed on the stack, "
                                 "<bookmark mark='c'/>the second on top of the first."):
            self.play(FadeIn(ttl), run_time=0.5)
            self.at("a", FadeIn(st), FadeIn(toks[0]))
            self.at("b", toks[0].animate.move_to(st.slot(0)), FadeIn(toks[1]))
            self.at("c", toks[1].animate.move_to(st.slot(1)))
        with self.voiceover(text="<bookmark mark='r'/>A record <bookmark mark='f'/>fills cell by cell. <bookmark mark='k'/>"
                                 "Arrivals land on one clock, <bookmark mark='g'/>and a budget <bookmark mark='s'/>runs down."):
            self.at("r", FadeIn(rec))
            self.at("f", *[b.animate.set_fill(ORANGE_L, opacity=0.6) for b in rec.boxes[:3]])
            self.at("k", FadeIn(ax), *[FadeIn(tick_at(ax, f)) for f in (0.2, 0.25, 0.4)])
            self.at("g", FadeIn(ga), ga.n.animate.set_value(2.6))
            self.at("s", ga.n.animate.set_value(0.8))
        pk = live(lambda w: gauss(4.9, 0.3, w, 1.3, TEAL_L), op=0, w=0.5)
        self.add(pk)
        with self.voiceover(text="<bookmark mark='p'/>A live curve fades in, <bookmark mark='w'/>widens, "
                                 "<bookmark mark='d'/>and dims."):
            self.at("p", pk.op.animate.set_value(1))
            self.at("w", pk.w.animate.set_value(1.3))
            self.at("d", pk.op.animate.set_value(0.3))


class Marks(Narrated):
    def construct(self):
        ttl = title("Tracks, dimensions and marks")
        w = wavy(P(-6.4, 1.6), P(-2.4, 1.6), YELLOW)
        b = burst(P(-2.2, 1.6))
        tk = poly([P(-2.2, 1.6), P(-1.4, 0.8), P(-0.6, 1.1)], TEAL_L)
        sg = step_seg(P(0.4, 1.0), P(2.2, 1.6), TEAL_L)
        fl = flag_at(P(2.2, 1.6), GREEN_L, h=0.3)
        x = xmark(P(3.4, 1.6))
        d1 = dim(P(-6.4, -0.4), P(-2.4, -0.4), "10 mm", side=DOWN)
        d2 = dim(P(-1.4, -1.6), P(1.0, 0.0), "3.1 mm", side=UP)
        a1 = arr(P(2.0, -0.6), P(4.0, -0.6), WHITE)
        a2 = carr(P(4.4, -0.6), P(6.2, -0.6), color=GREY_B)
        bx = dashed(Rectangle(width=1.6, height=0.8, stroke_color=GREY_B)).move_to(P(5.3, 1.6))
        gs = gauss(-4.4, -3.4, 1.4, 1.4, PURPLE_L)
        br = bars([("ours", 2.0, "2.0", ORANGE_L), ("theirs", 3.0, "3.0", GREY_B)], 0.0, -2.2, 1.6, step=0.9)
        with self.voiceover(text="<bookmark mark='a'/>A gamma flies in, <bookmark mark='b'/>flashes, <bookmark mark='c'/>"
                                 "and an electron takes a step <bookmark mark='d'/>that ends on a flagged point. "
                                 "<bookmark mark='e'/>A cross marks what is refused."):
            self.play(FadeIn(ttl), run_time=0.5)
            self.at("a", Create(w))
            self.at("b", FadeIn(b))
            self.at("c", Create(tk), FadeIn(sg))
            self.at("d", FadeIn(fl), FadeIn(bx))
            self.at("e", FadeIn(x))
        with self.voiceover(text="<bookmark mark='f'/>Dimensions read along their line, <bookmark mark='g'/>even a "
                                 "slanted one. <bookmark mark='h'/>Arrows point, <bookmark mark='i'/>a peak rises, "
                                 "<bookmark mark='j'/>and bars grow to their values."):
            self.at("f", FadeIn(d1))
            self.at("g", FadeIn(d2))
            self.at("h", GrowArrow(a1), Create(a2))
            self.at("i", Create(gs))
            self.at("j", *[GrowFromEdge(r[0], LEFT) for r in br], *[FadeIn(VGroup(r[1], r[2])) for r in br])


class Optics(Narrated):
    def construct(self):
        ttl = title("Detectors and light")
        sl = slab_side(6.0).move_to(P(-3.4, 0.6))
        ph = Dot(sl.pt(-10, 4), radius=0.08, color=YELLOW)
        rays = VGroup(*[wavy(sl.pt(-10, 4), t.get_top(), PURPLE_L, amp=0.03) for t in sl.tiles[1:4]])
        gr = sipm_grid(8, 2.0).move_to(P(-3.4, -2.4))
        sn = snell(1.25, w=5.6, hh=1.6, R=1.4).move_to(P(3.6, 0.4))
        with self.voiceover(text="<bookmark mark='a'/>A slab seen from the side. <bookmark mark='b'/>A flash inside it "
                                 "<bookmark mark='c'/>sends light to the tiles, <bookmark mark='d'/>and the array lights up."):
            self.play(FadeIn(ttl), run_time=0.5)
            self.at("a", FadeIn(sl))
            self.at("b", FadeIn(ph))
            self.at("c", *[Create(r) for r in rays])
            self.at("d", FadeIn(gr), *[gr[k].animate.set_fill(PURPLE_L, opacity=0.8) for k in (18, 19, 26, 27)])
        with self.voiceover(text="<bookmark mark='s'/>At an interface, a ray <bookmark mark='t'/>bends as it crosses, "
                                 "<bookmark mark='u'/>and past the critical angle it all reflects."):
            self.at("s", FadeIn(sn))
            self.at("t", sn.th.animate.set_value(0.6))
            self.at("u", sn.th.animate.set_value(1.1), run_time=1.5)


class Figures(Narrated):
    def construct(self):
        ttl = title("A figure from the paper")
        fg = figcard(A / "borghi_fig7.png", h=4.6).move_to(P(0, -0.3))
        bx = fig_box(fg, 0.595, 0.585, 0.815, 0.875, ORANGE_L)   # the heatmap only, clear of its title
        cr = credit(r"Fig. 7: Borghi et al., Phys.\ Med.\ Biol.\ 2016 (CC BY 3.0)")
        nt = note("frame added here")
        with self.voiceover(text="<bookmark mark='a'/>A figure cut from the paper sits on white, <bookmark mark='b'/>"
                                 "with its source in the corner. <bookmark mark='c'/>A frame picks out the deepest "
                                 "band, <bookmark mark='d'/>and a note says the frame is ours."):
            self.play(FadeIn(ttl), run_time=0.5)
            self.at("a", FadeIn(fg))
            self.at("b", FadeIn(cr))
            self.at("c", Create(bx))
            self.at("d", FadeIn(nt))
