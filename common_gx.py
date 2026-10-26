"""ManimGX side of common.py (ENGINE=gx, the default): the same helpers, and a Narrated that replays the narration
tools/voice_prepass.py cached for the scene (m_<Scene>/voiceovers beside the scene file, or under VOICE_ROOT) with
add_sound, timing self.at() cues from its word timings as manim-voiceover does. vlint's runtime checks run in CE
(skip mode), so vlint_ok is a no-op here. Patches the few CE habits ManimGX lacks (see the comments)."""
import inspect
import json
import os
import re
from contextlib import contextmanager
import numpy as np
from manimgx import *
from manimgx import Tex as _Tex, MathTex as _MathTex
from pathlib import Path   # after the star import: manimgx exports a Path mobject

# mitex has no text accents (\'a); give it the characters instead
_ACC = {"'": "́", "`": "̀", '"': "̈", "^": "̂", "~": "̃"}
_ACC_RE = re.compile(r"""\\(['`"^~])\{?([A-Za-z])\}?""")


def _accents(s, math=False):
    import unicodedata
    if not isinstance(s, str):
        return s
    # mitex sets \& as "amp" and "\ " as "thick" (in maths it drops the gap, which \; keeps); keep \\ breaks
    s = re.sub(r"(?<!\\)\\ ", r"\\; " if math else " ", s.replace("\\&", "&"))
    return _ACC_RE.sub(lambda m: unicodedata.normalize("NFC", m.group(2) + _ACC[m.group(1)]), s)


# text-mode macros mitex prints as words ("quad", "dots") or crashes on; outside $...$ they become the characters
_TEXT_MACROS = [(re.compile(p), r) for p, r in (
    (r"\\textperiodcentered\b\s*", "·"), (r"\\checkmark\b\s*", "✓"), (r"\\l?dots\b\s*", "…"),
    (r"\\qquad\b\s*", "\u2003\u2003"), (r"\\quad\b\s*", "\u2003"), (r"\\,", "\u2009"), (r"(?<!\\)~", "\u00a0"),
    (r"\\_", "_"), (r"``", "“"), (r"''", "”"), (r"(?<![\w\\])`", "‘"))]


def _text_mode(parts):
    out, math = [], False
    for p in parts:
        if not isinstance(p, str):
            out.append(p)
            continue
        segs = re.split(r"((?<!\\)\$)", p)
        for i, seg in enumerate(segs):
            if seg == "$":
                math = not math
            elif not math:
                for rx, r in _TEXT_MACROS:
                    seg = rx.sub(r, seg)
            segs[i] = seg
        out.append("".join(segs))
    return out


class Tex(_Tex):
    def __init__(self, *parts, **kw):
        super().__init__(*[_accents(p) for p in _text_mode(parts)], **kw)


class MathTex(_MathTex):
    def __init__(self, *parts, **kw):
        super().__init__(*[_accents(p, math=True) for p in parts], **kw)

for _cls in (Mobject, ImageMobject):   # CE's old aliases
    _cls.set_height = lambda self, h, **kw: self.scale_to_fit_height(h, **kw)
    _cls.set_width = lambda self, w, **kw: self.scale_to_fit_width(w, **kw)

config.background_color = "#0f1117"
BLUE_L, TEAL_L, GREEN_L, ORANGE_L, PURPLE_L = "#4c8fe0", "#2ec4b6", "#3fb27f", "#f08a4b", "#b18cf0"
_BOOKMARK = re.compile(r"<bookmark\s+mark\s*=\s*['\"](\w*)['\"]\s*/>")


def vlint_ok(mob, *rule_ids):
    return mob


import types
rate_functions = types.SimpleNamespace(**{n: globals()[n] for n in (
    "smooth", "linear", "there_and_back", "rush_into", "rush_from", "double_smooth", "ease_in_out_sine",
    "ease_out_cubic", "wiggle", "there_and_back_with_pause", "exponential_decay") if n in globals()})   # CE's module


class _Tracker:
    """manim-voiceover's tracker: the block's length, its bookmarks, and how much of it is left."""
    def __init__(self, scene, t0, duration, marks):
        self.scene, self.t0, self.duration, self.marks = scene, t0, duration, marks

    def get_remaining_duration(self, buff=0.0):
        return max(self.duration - (self.scene.time - self.t0) + buff, 0)

    def time_until_bookmark(self, mark, buff=0, limit=None):
        left = max(self.marks[mark] - (self.scene.time - self.t0) + buff, 0)
        return min(left, limit) if limit is not None else left


class Narrated(Scene):
    def wait(self, duration=1.0, *a, **kw):
        # end every wait on a whole frame: a wait ending between frames is held as a frame sampled just inside the
        # next animation, so the first stroke of a Write/Create sat on screen for the whole pause
        fps = config.frame_rate
        d = round((self.time + duration) * fps) / fps - self.time
        if d > 0.5 / fps:
            super().wait(d, *a, **kw)

    def _cache(self):
        base = os.environ.get("VOICE_ROOT") or Path(inspect.getfile(type(self))).parent
        root = Path(base) / f"m_{type(self).__name__}" / "voiceovers"
        for k in range(20):   # the voice pre-pass may be rewriting cache.json for another line right now
            try:
                return root, {e["input_data"]["input_text"]: e for e in json.loads((root / "cache.json").read_text())}
            except json.JSONDecodeError:
                if k == 19:
                    raise
                import time
                time.sleep(0.25)

    @contextmanager
    def voiceover(self, text):
        root, cache = self._cache()
        spoken = " ".join(_BOOKMARK.sub("", text).split())
        entry = cache[spoken]
        words = entry["word_boundaries"]
        marks = {}
        parts = _BOOKMARK.split(text)                                   # text, mark, text, mark, ..., text
        before = ""
        for k in range(1, len(parts), 2):
            before += parts[k - 1]
            off = len(" ".join(before.split()))
            w = next((w for w in words if w["text_offset"] >= off), words[-1])
            marks[parts[k]] = w["audio_offset"] / 10_000_000
        duration = words[-1]["audio_offset"] / 10_000_000
        self._vo = (self.time, marks)
        self.add_sound(str(root / entry["original_audio"]))
        yield _Tracker(self, self.time, duration, marks)
        left = duration - (self.time - self._vo[0])
        if left > 1 / 60:
            self.wait(left)

    def wait_until_bookmark(self, mark):
        t0, marks = self._vo
        left = marks[mark] - (self.time - t0)
        if left > 1 / 60:
            self.wait(left)

    def at(self, mark, *anims, **kw):
        self.wait_until_bookmark(mark)
        if anims:
            kw.setdefault("run_time", 0.7)
            self.play(*anims, **kw)


TITLE_BUFF = 0.85
CONTENT_TOP = 2.45


def title(text, size=32, **kw):
    return Tex(text, font_size=size, **kw).to_edge(UP, buff=TITLE_BUFF)


def top_at(m, y=CONTENT_TOP):
    return m.shift((y - m.get_top()[1]) * UP)


def place(g, p):
    return g.shift(np.array(p) - g[0].get_center())


def grid(items, cols, dx, dy, center=ORIGIN, by_icon=True):
    rows = (len(items) + cols - 1) // cols
    for i, m in enumerate(items):
        r, c = divmod(i, cols)
        n = min(cols, len(items) - r * cols)
        p = np.array(center) + RIGHT * (c - (n - 1) / 2) * dx + UP * ((rows - 1) / 2 - r) * dy
        place(m, p) if by_icon and len(m.submobjects) else m.move_to(p)
    return items


def fit_frame(m, margin=0.3):
    hw, hh = config.frame_width / 2 - margin, config.frame_height / 2 - margin
    if m.width > 2 * hw:
        m.scale_to_fit_width(2 * hw)
    if m.height > 2 * hh:
        m.scale_to_fit_height(2 * hh)
    dx = min(0, hw - m.get_right()[0]) + max(0, -hw - m.get_left()[0])
    dy = min(0, hh - m.get_top()[1]) + max(0, -hh - m.get_bottom()[1])
    return m.shift(dx * RIGHT + dy * UP)


def fade_all(scene):
    scene.play(*[FadeOut(m) for m in scene.mobjects])


def front_page(h=6.4, name="front.png"):
    """Page 1 of the paper the video explains (tools/front_page.sh writes <video>/assets/front.png), framed, for the
    opening seconds: the viewer recognises the paper before the explaining starts (docs/DESIGN.md §1, vlint: front-page)."""
    import inspect
    here = Path(inspect.stack()[1].filename).resolve().parent
    im = ImageMobject(str(here / "assets" / name)).set_height(h)
    return Group(im, Rectangle(width=im.width, height=im.height, stroke_color=GREY_B, stroke_width=1.5).move_to(im))

def point(scene, m, color=WHITE):
    """The term marker: a box that moves onto whichever part of an equation the voice is naming, so the eye
    always knows which symbol is being read (docs/DESIGN.md §1). Returns the animation; the first call draws the box.
    Point at a part that is on screen: under ManimGX a Transform reshapes its target, so transform into
    target.copy() when you will point at the target's parts later."""
    box = SurroundingRectangle(m, buff=0.08, color=color, stroke_width=2.5)
    old = getattr(scene, "_ptr", None)
    scene._ptr = box
    return ReplacementTransform(old, box) if old is not None else Create(box)


def unpoint(scene):
    """Fade the term marker; call it at the next block's first cue, not right after the last `at`."""
    old, scene._ptr = scene._ptr, None
    return FadeOut(old)

