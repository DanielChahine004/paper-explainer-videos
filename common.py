"""Shared look and plumbing for the narrated paper videos: background, LaTeX template, encoder
quality, palette and the narrated scene base. Each video folder imports it (`from common import *`)."""
import sys
from contextlib import contextmanager
from pathlib import Path

from manim import *
from manim_voiceover import VoiceoverScene

sys.path.insert(0, str(Path(__file__).resolve().parent))
from voices import make_service

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))
from vlint.runtime import Checked, vlint_ok  # noqa: E402,F401  runtime design checks (tools/vlint)

config.background_color = "#0f1117"
_wide = TexTemplate()
_wide.add_to_preamble(r"\setlength{\textwidth}{40cm}\setlength{\linewidth}{40cm}\setlength{\hsize}{40cm}")
config.tex_template = _wide

# manim 0.19 hard-codes x264 at CRF 23 for its partial movies, and the scene file is a stream
# copy of them, so the final quality is set here: CRF 14 with the slow preset keeps text sharp.
import manim.scene.scene_file_writer as _sfw


class _HQContainer:
    def __init__(self, c):
        self._c = c

    def __getattr__(self, k):
        return getattr(self._c, k)

    def __enter__(self):
        self._c.__enter__()
        return self

    def __exit__(self, *a):
        return self._c.__exit__(*a)

    def add_stream(self, *a, options=None, **kw):
        if options and options.get("crf") == "23":
            options = {**options, "crf": "14", "preset": "slow", "tune": "animation"}
        return self._c.add_stream(*a, **({"options": options} if options is not None else {}), **kw)


class _HQAv:
    def __init__(self, av):
        self._av = av

    def __getattr__(self, k):
        return getattr(self._av, k)

    def open(self, *a, **kw):
        return _HQContainer(self._av.open(*a, **kw))


if not isinstance(_sfw.av, _HQAv):
    _sfw.av = _HQAv(_sfw.av)

BLUE_L, TEAL_L, GREEN_L, ORANGE_L, PURPLE_L = "#4c8fe0", "#2ec4b6", "#3fb27f", "#f08a4b", "#b18cf0"


class Narrated(Checked, VoiceoverScene):
    def setup(self):
        super().setup()
        self.set_speech_service(make_service())

    # Checked (tools/vlint/runtime.py) sends every play to the vlint monitor; narration and cues go too, so it
    # can check the frame as it really is: clipped or overlapping labels, vanished objects, bookmarks never reached.
    @contextmanager
    def voiceover(self, *a, **kw):
        self.vlint.event("vo_open", text=kw.get("text", a[0] if a else None))
        with super().voiceover(*a, **kw) as tracker:
            yield tracker
        self.vlint.event("vo_close")

    def wait_until_bookmark(self, mark):
        self.vlint.event("cue", mark=mark)
        super().wait_until_bookmark(mark)

    def at(self, mark, *anims, **kw):
        """Cue: wait for <bookmark mark='mark'/> in the current voiceover, then play (docs/DESIGN.md §1)."""
        self.wait_until_bookmark(mark)
        if anims:
            kw.setdefault("run_time", 0.7)
            self.play(*anims, **kw)


def fit_frame(m, margin=0.3):
    """Shrink and nudge m so it lies inside the frame with `margin` to spare (docs/DESIGN.md §2)."""
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
