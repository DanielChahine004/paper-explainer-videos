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


_MISS = object()                        # "not fetched yet", so a real None (no frame) is cached too


def vlint_ok(mob, *rule_ids):
    """Mark a mobject (and everything inside it) as exempt from the given runtime rules ('*' for all).

    The mark is written onto every member of the family, not just the root. Scene.add and Scene.remove dissolve
    a parent group -- removing or introducing one child splices that group's remaining children into
    scene.mobjects in its place (manim's Scene.get_restructured_mobject_list) -- so a mark that only lived on
    the root would quietly stop applying partway through a scene, and a rule that had been exempt for ten plays
    would start firing on the eleventh for no reason the author could see."""
    ids = set(rule_ids or ("*",))
    for m in mob.get_family() if hasattr(mob, "get_family") else [mob]:
        m._vlint_ok = set(getattr(m, "_vlint_ok", set())) | ids
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
        self._frame = _MISS                 # the rendered frame, fetched at most once per play
        self.review = []              # moments worth a look: narration block ends, tracker sweeps

    # ---- plumbing ------------------------------------------------------------------------------------------
    def time(self):
        return float(getattr(self.scene.renderer, "time", -1.0))

    def disabled(self, rule_id):
        return any(rule_id in s or "*" in s for s in self.off)

    def frame(self):
        """The rendered frame at this moment as an (H, W, 4) array, or None.

        The pixels are the only honest answer to "does this look wrong": a bounding box is not a shape, and the
        mobject tree is reshaped underneath a rule whenever Scene.add dissolves a group. Available even in skip
        mode (manim -ql -s still rasterises), so a pixel rule costs a check, not a render. Cached per play."""
        if self._frame is _MISS:
            try:
                import numpy as np
                self._frame = np.asarray(self.scene.renderer.get_frame())
            except Exception:
                self._frame = None
        return self._frame

    def to_px(self, x, y):
        """A point in scene units -> (column, row) in frame(). Manim's camera maps the frame width across the
        full pixel width, origin at the centre, y upwards."""
        f = self.frame()
        if f is None:
            return None
        import manim as M
        h, w = f.shape[0], f.shape[1]
        fw, fh = float(M.config.frame_width), float(M.config.frame_height)
        return (w / 2 + x / fw * w, h / 2 - y / fh * h)

    def emit(self, rule_id, key, msg, sev=None):
        if (rule_id, key) in self._seen or self.disabled(rule_id):
            return
        self._seen.add((rule_id, key))
        f = Finding(rule_id, msg, file=self.script.name, scene=self.name, time=self.time())
        f.severity = sev or self.config.level(rule_id, self.name)
        print(f"[vlint] {f.severity}[{rule_id}] {self.name} t={f.time:.1f}s: {msg}", file=sys.stderr, flush=True)
        self.findings.append(f)

    def event(self, ev, **payload):
        if not self.enabled:
            return
        self._frame = _MISS                 # a new moment: whatever was cached is last moment's picture
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
                # a crash means that rule checked nothing, so it is exactly as serious as the rule was: a
                # broken error rule still fails the render, a broken layout warning does not hold a video
                self.emit("vlint-internal", r.id, f"rule {r.id} crashed on {ev}: {e!r}",
                          sev=self.config.level(r.id, self.name))

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
