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


def _accents(s):
    import unicodedata
    if not isinstance(s, str):
        return s
    s = s.replace("\\&", "&").replace("\\ ", " ")   # mitex sets these as "amp" and "thick"
    return _ACC_RE.sub(lambda m: unicodedata.normalize("NFC", m.group(2) + _ACC[m.group(1)]), s) if isinstance(s, str) else s


class Tex(_Tex):
    def __init__(self, *parts, **kw):
        super().__init__(*[_accents(p) for p in parts], **kw)


class MathTex(_MathTex):
    def __init__(self, *parts, **kw):
        super().__init__(*[_accents(p) for p in parts], **kw)

for _cls in (Mobject, ImageMobject):   # CE's old aliases
    _cls.set_height = lambda self, h, **kw: self.scale_to_fit_height(h, **kw)
    _cls.set_width = lambda self, w, **kw: self.scale_to_fit_width(w, **kw)

config.background_color = "#0f1117"
BLUE_L, TEAL_L, GREEN_L, ORANGE_L, PURPLE_L = "#4c8fe0", "#2ec4b6", "#3fb27f", "#f08a4b", "#b18cf0"
_BOOKMARK = re.compile(r"<bookmark\s+mark\s*=\s*['\"](\w*)['\"]\s*/>")


def vlint_ok(mob, *rule_ids):
    return mob


class _Tracker:
    def __init__(self, duration, marks):
        self.duration, self.marks = duration, marks


class Narrated(Scene):
    def _cache(self):
        base = os.environ.get("VOICE_ROOT") or Path(inspect.getfile(type(self))).parent
        root = Path(base) / f"m_{type(self).__name__}" / "voiceovers"
        return root, {e["input_data"]["input_text"]: e for e in json.loads((root / "cache.json").read_text())}

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
        yield _Tracker(duration, marks)
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
