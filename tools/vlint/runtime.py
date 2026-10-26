"""Runtime checks: a Monitor rides along inside each scene as it renders and hands every play(), voiceover and cue
to the runtime rules (rules_runtime.py). Findings print as they happen ("[vlint] ...") and are saved next to the
scene's video as <Scene>.vlint.json together with the scene's fingerprint, which the output stage reads.

In a scene:  vlint_ok(mob, "text-overlap")         this mobject (and its children) may overlap text on purpose
             with self.vlint_off("frame-clip"): ... the rule is off inside the block
VLINT=0 turns the monitor off. VLINT_OUT=<dir> saves the record there even when no video is written (skip mode,
`manim -s`: every play() jumps to its end state, so a whole scene checks in seconds). The record also lists the
review moments (the end of each narration block, each animated ValueTracker's time window) for tools/review.sh."""
import os
import sys
from contextlib import contextmanager
from pathlib import Path

from .core import RULES, Finding, dump, load_config, load_rules, write_json
from .fingerprint import fingerprint, rules_hash


def vlint_ok(mob, *rule_ids):
    """Mark a mobject (and everything inside it) as exempt from the given runtime rules ('*' for all)."""
    mob._vlint_ok = set(getattr(mob, "_vlint_ok", set())) | set(rule_ids or ("*",))
    return mob


class Monitor:
    def __init__(self, scene):
        self.scene = scene
        self.name = type(scene).__name__
        mod = sys.modules.get(type(scene).__module__)
        self.script = Path(getattr(mod, "__file__", "scene.py")).resolve()
        self.enabled = os.environ.get("VLINT", "1") != "0"
        load_rules(self.script.parent, stages=("runtime",))
        self.config = load_config(self.script.parent)
        self.rules = [r for r in RULES.values() if r.stage == "runtime" and self.config.level(r.id, self.name) != "off"]
        self.off = []                 # stack of rule-id sets switched off by vlint_off
        self.findings, self._seen, self.state = [], set(), {}
        self.review = []              # moments worth a look: narration block ends, tracker sweeps

    # ---- plumbing ------------------------------------------------------------------------------------------
    def time(self):
        return float(getattr(self.scene.renderer, "time", -1.0))

    def disabled(self, rule_id):
        return any(rule_id in s or "*" in s for s in self.off)

    def emit(self, rule_id, key, msg):
        if (rule_id, key) in self._seen or self.disabled(rule_id):
            return
        self._seen.add((rule_id, key))
        f = Finding(rule_id, msg, file=self.script.name, scene=self.name, time=self.time())
        f.severity = self.config.level(rule_id, self.name)
        print(f"[vlint] {f.severity}[{rule_id}] {self.name} t={f.time:.1f}s: {msg}", file=sys.stderr, flush=True)
        self.findings.append(f)

    def event(self, ev, **payload):
        if not self.enabled:
            return
        if ev == "vo_close":
            self.review.append({"kind": "block_end", "t": round(self.time(), 3)})
        if ev == "play" and payload.get("trackers"):
            self.review.append({"kind": "sweep", "t0": round(payload.get("t0", self.time()), 3), "t1": round(self.time(), 3)})
        for r in self.rules:
            if self.disabled(r.id):
                continue
            try:
                for key, msg in r.fn(self, ev, payload) or ():
                    self.emit(r.id, key, msg)
            except Exception as e:  # a broken rule must never break a render
                self.emit("vlint-internal", r.id, f"rule {r.id} crashed on {ev}: {e!r}")

    def finish(self):
        self.event("end")
        rec = {"scene": self.name, "script": self.script.name, "fingerprint": fingerprint(self.script, self.name),
               "rules": rules_hash(self.script), "monitor": self.enabled, "findings": dump(self.findings),
               "review": self.review}
        if os.environ.get("VLINT_RECHECK"):
            rec["rechecked"] = True       # findings refreshed in skip mode; the video beside it is older on purpose
        out = os.environ.get("VLINT_OUT")
        if out:
            write_json(Path(out) / f"{self.name}.vlint.json", rec)
            return
        fw = getattr(self.scene.renderer, "file_writer", None)
        movie = getattr(fw, "movie_file_path", None)
        if movie:
            movie = Path(movie)
            write_json(movie.with_name(movie.stem + ".vlint.json"), rec)

    @contextmanager
    def suspend(self, *rule_ids):
        self.off.append(set(rule_ids or ("*",)))
        try:
            yield
        finally:
            self.off.pop()


class Checked:
    """Mixin for any manim Scene: hands every play() to the monitor and saves its record at the end.
    common.Narrated builds on it and adds the narration events."""

    def setup(self):
        super().setup()
        self.vlint = Monitor(self)

    def play(self, *anims, **kw):
        from manim import ValueTracker
        trackers = [(a.mobject, a.mobject.get_value()) for a in anims if isinstance(getattr(a, "mobject", None), ValueTracker)]
        t0 = self.vlint.time()
        self.vlint.event("pre_play", anims=anims)
        super().play(*anims, **kw)
        self.vlint.event("play", anims=anims, trackers=trackers, t0=t0)

    def vlint_off(self, *rule_ids):
        """`with self.vlint_off("frame-clip"):` switches runtime rules off for a block (all if none named)."""
        return self.vlint.suspend(*rule_ids)

    def tear_down(self):
        self.vlint.finish()
        super().tear_down()


def walk(mobjects, ok=frozenset()):
    """(mobject, exempt rule ids) for every mobject in the tree, exemptions inherited from parents."""
    for m in mobjects:
        here = ok | getattr(m, "_vlint_ok", frozenset())
        yield m, here
        yield from walk(m.submobjects, here)
