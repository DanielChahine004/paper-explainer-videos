"""One-off patch: eye-guiding cues for WhyParticles, UHDR and Future (narration words unchanged; bookmarks added)."""
import sys

p = sys.argv[1]
s = open(p, encoding="utf-8").read()


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:80])
    s = s.replace(a, b)


Q = "\"\n                                 \""   # the string break used inside voiceover texts

# WhyParticles ---------------------------------------------------------------------------------------------------
rep("X-ray photons deposit most of their dose near " + Q + "the surface and fade with depth, so the tissue in front of a deep tumour gets more dose than the " + Q + "tumour.",
    "X-ray photons deposit most of their dose near " + Q + "the <bookmark mark='ns'/>surface and fade with depth, so the tissue in front of a deep " + Q + "<bookmark mark='dt'/>tumour gets more dose than the tumour.")
rep("and dump most of it in a sharp Bragg peak, with no dose beyond it.",
    "and dump most of it in a sharp <bookmark mark='bp'/>Bragg peak, with no dose <bookmark mark='nb'/>beyond it.")
rep("with a small tail from fragments.", "with a small <bookmark mark='tf'/>tail from fragments.")
rep("energy electrons give a broad, flat profile", "energy electrons give a broad, <bookmark mark='fp'/>flat profile")
rep('            self.at("p", Create(cp), FadeIn(leg[1]), Indicate(tum, color=BAD_C), run_time=1.5)\n'
    '            self.at("c", Create(cc), FadeIn(leg[2]), run_time=1.2)\n'
    '            self.at("e", Create(ce), FadeIn(leg[3]), run_time=1.2)\n',
    '            self.at("ns", Flash(ax.c2p(4, photon_dd(4)), color=XRAY_C, flash_radius=0.35))\n'
    '            self.at("dt", Indicate(tum, color=BAD_C, scale_factor=1.05), Indicate(tl, color=BAD_C))\n'
    '            self.at("p", Create(cp), FadeIn(leg[1]), run_time=1.5)\n'
    '            self.at("bp", Flash(ax.c2p(Rp, 1.0), color=PROT_C, flash_radius=0.35))\n'
    '            beyond = Rectangle(width=ax.c2p(42, 0)[0] - ax.c2p(Rp + 0.4, 0)[0], height=ax.c2p(0, 1.1)[1] - ax.c2p(0, 0)[1], fill_color=PROT_C,\n'
    '                               fill_opacity=0.18, stroke_width=0).move_to(ax.c2p(Rp + 0.4, 0), aligned_edge=DL)\n'
    '            self.at("nb", FadeIn(beyond), run_time=0.4)\n'
    '            self.play(FadeOut(beyond), run_time=0.6)\n'
    '            self.at("c", Create(cc), FadeIn(leg[2]), run_time=1.2)\n'
    '            tail = Rectangle(width=ax.c2p(30, 0)[0] - ax.c2p(Rc + 0.5, 0)[0], height=0.5).move_to(ax.c2p((Rc + 30) / 2, 0.08))\n'
    '            self.at("tf", Circumscribe(tail, color=CARB_C))\n'
    '            self.at("e", Create(ce), FadeIn(leg[3]), run_time=1.2)\n'
    '            self.at("fp", Indicate(ce, color=ELEC_C, scale_factor=1.0), Indicate(leg[3], color=ELEC_C))\n')

# UHDR -----------------------------------------------------------------------------------------------------------
rep("it uses up the oxygen in normal cells before the blood can resupply it, ",
    "it uses up the <bookmark mark='ox'/>oxygen in normal cells before the <bookmark mark='bl'/>blood can resupply it, ")
rep("behave like hypoxic tumour cells,", "behave like hypoxic <bookmark mark='ht'/>tumour cells,")
rep("peak dose rates: ten to the seven grays per second in " + Q + "an early proton study, ten to the nine in others, two times ten to the nine for a single four hundred " + Q
    + "picosecond carbon pulse, and up to ten to the thirteen for electrons.",
    "peak dose rates: <bookmark mark='p1'/>ten to the seven grays per second in " + Q + "an early proton study, <bookmark mark='p2'/>ten to the nine in others, "
    "<bookmark mark='p3'/>two times ten to the nine for a single four hundred " + Q + "picosecond carbon pulse, and up to <bookmark mark='p4'/>ten to the thirteen for electrons.")
rep("another matter: zero point two grays per second in that early proton study, " + Q + "about one for a kilohertz electron source, and one to two grays per minute",
    "another matter: <bookmark mark='a1'/>zero point two grays per second in that early proton study, " + Q
    + "<bookmark mark='a2'/>about one for a kilohertz electron source, and <bookmark mark='a3'/>one to two grays per minute")
rep('            self.play(flash.animate.set_fill(opacity=0.35), run_time=0.15)\n',
    '            self.at("ox", Indicate(o2n, color=BLUE_L, scale_factor=1.3))\n'
    '            self.play(flash.animate.set_fill(opacity=0.35), run_time=0.15)\n')
rep('            self.at("h", FadeIn(res), Indicate(cn, color=GOOD_C))\n'
    '            self.at("p", FadeIn(key), LaggedStart(*[FadeIn(p, scale=1.5) for p in pk], lag_ratio=0.4), run_time=2.5)\n'
    '            self.at("a", LaggedStart(*[FadeIn(a, scale=1.5) for a in av], lag_ratio=0.4), run_time=2.0)\n',
    '            self.at("bl", Indicate(vessel, color=BAD_C, scale_factor=1.15))\n'
    '            self.at("h", FadeIn(res), Indicate(cn, color=GOOD_C))\n'
    '            self.at("ht", Indicate(ct, color=BAD_C), Indicate(cl[1], color=BAD_C))\n'
    '            self.at("p", FadeIn(key), Indicate(fline, color=YELLOW, scale_factor=1.0))\n'
    '            for m, idx in (("p1", [0]), ("p2", [1]), ("p3", [2]), ("p4", [3, 4])):\n'
    '                self.at(m, *[FadeIn(pk[i], scale=1.8) for i in idx], *[Flash(pk[i][0].get_center(), color=WHITE, flash_radius=0.25) for i in idx])\n'
    '            for m, i in (("a1", 0), ("a2", 1), ("a3", 2)):\n'
    '                self.at(m, FadeIn(av[i], scale=1.8), Flash(av[i][0].get_center(), color=WHITE, flash_radius=0.25))\n')

# Future ---------------------------------------------------------------------------------------------------------
rep("adjusts the laser wavefront and target position, fires, measures, and chooses " + Q + "the next shot.",
    "adjusts the <bookmark mark='lw'/>laser wavefront and target position, <bookmark mark='fi'/>fires, " + Q
    + "<bookmark mark='me'/>measures, and <bookmark mark='ch'/>chooses the next shot.")
rep("targets that survive: " + Q + "cryogenic hydrogen jets, liquid sheets and tape drives now allow",
    "targets that survive: " + Q + "<bookmark mark='t1'/>cryogenic hydrogen jets, <bookmark mark='t2'/>liquid sheets and <bookmark mark='t3'/>tape drives now allow")
rep('            self.at("l", FadeIn(loop), FadeIn(knobs), LaggedStart(*[Create(a) for a in arrows], lag_ratio=0.25), Create(bline), run_time=2.0)\n',
    '            self.at("l", FadeIn(loop), LaggedStart(*[Create(a) for a in arrows], lag_ratio=0.25), Create(bline), run_time=1.5)\n'
    '            self.at("lw", FadeIn(knobs), Indicate(loop[0], color=LASER_C, scale_factor=1.15))\n'
    '            self.at("fi", Indicate(loop[1], color=WHITE, scale_factor=1.15))\n'
    '            self.at("me", Indicate(loop[2], color=YELLOW, scale_factor=1.15))\n'
    '            self.at("ch", Indicate(loop[3], color=GOOD_C, scale_factor=1.15))\n')
rep('            self.at("t", FadeIn(tgl), LaggedStart(*[FadeIn(t_) for t_ in tg], lag_ratio=0.3))\n',
    '            self.at("t", FadeIn(tgl))\n'
    '            for m, i in (("t1", 0), ("t2", 1), ("t3", 2)):\n'
    '                self.at(m, FadeIn(tg[i], scale=1.1))\n')

open(p, "w", encoding="utf-8").write(s)
print("patched")
