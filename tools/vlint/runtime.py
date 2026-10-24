"""Runtime checks: a Monitor rides along inside each scene as it renders and hands every play(), voiceover and cue
to the runtime rules (rules_runtime.py). Findings print as they happen ("[vlint] ...") and are saved next to the
scene's video as <Scene>.vlint.json together with the scene's fingerprint, which the output stage reads.

In a scene:  vlint_ok(mob, "text-overlap")         this mobject (and its children) may overlap text on purpose
             with self.vlint_off("frame-clip"): ... the rule is off inside the block
VLINT=0 turns the monitor off."""
import os
import sys
from contextlib import contextmanager
from pathlib import Path

from .core import RULES, Finding, dump, load_config, load_rules, write_json
from .fingerprint import fingerprint


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
        fw = getattr(self.scene.renderer, "file_writer", None)
        movie = getattr(fw, "movie_file_path", None)
        if not movie:
            return
        movie = Path(movie)
        rec = {"scene": self.name, "script": self.script.name, "fingerprint": fingerprint(self.script, self.name),
               "monitor": self.enabled, "findings": dump(self.findings)}
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
        super().play(*anims, **kw)
        self.vlint.event("play", anims=anims, trackers=trackers)

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
