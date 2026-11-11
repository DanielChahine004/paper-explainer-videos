"""`vlint cues <video>` -- what every cue actually does, beside the clause it fires on.

A cue can bring something on (intro), do something to what is already on screen (change), or merely point at it
(emphasis). The third kind says "this", never "this happens", and a scene built mostly of the first kind is a
slideshow: each clause raises a new thing instead of the scene's own figure doing something.

This is a report, not a gate. There is no good threshold -- a thing named for the first time *should* appear,
and a thing named again *should* be pulsed -- so it prints the shape of a scene and leaves the judgement where
it belongs. Read it while writing: if "change" is a thin slice, the narration is being illustrated rather than
performed.

    python tools/vlint cues lnp_comet
"""
import ast
import re
from collections import Counter
from pathlib import Path

from .script import EMPHASIS, INTRO, MARK, call_name

CHANGE = {"animate", "Transform", "ReplacementTransform", "TransformMatchingShapes", "TransformMatchingTex",
          "MoveAlongPath", "Rotate", "Rotating", "Restore", "MoveToTarget", "ApplyFunction", "ApplyMatrix",
          "ShrinkToCenter", "CyclicReplace", "ScaleInPlace"}


def _kinds(node):
    out = set()
    for n in ast.walk(node):
        nm = call_name(n)
        if nm in EMPHASIS:
            out.add("emphasis")
        elif nm in CHANGE:
            out.add("change")
        elif nm in INTRO:
            out.add("intro")
        if isinstance(n, ast.Attribute) and n.attr == "animate":
            out.add("change")
    return out


def _text_of(call, s):
    kw = next((k.value for k in call.keywords if k.arg == "text"), call.args[0] if call.args else None)
    return (s.resolve_str(kw) or "") if kw is not None else ""


def report(path):
    from .core import load_config
    from .script import load_script

    out = []
    for sp in ([Path(path)] if Path(path).is_file() else sorted(Path(path).glob("*_vo.py"))):
        s = load_script(sp, load_config(sp.parent))
        tally, quiet = Counter(), []
        for cls in s.scenes:
            for vo in [v for v in s.voiceovers if cls.lineno <= v.node.lineno <= cls.end_lineno]:
                parts = MARK.split(_text_of(vo.node.items[0].context_expr, s))
                after = {parts[k]: parts[k + 1] for k in range(1, len(parts), 2)}
                for mark, node in vo.cues:
                    k = _kinds(node)
                    tag = ("emphasis only" if k == {"emphasis"} else "intro only" if k == {"intro"} else
                           "change" if "change" in k else "intro + pulse" if k else "nothing")
                    tally[tag] += 1
                    if tag in ("emphasis only", "nothing"):
                        quiet.append((cls.name, node.lineno, mark, " ".join(after.get(mark, "").split()[:11])))
        total = sum(tally.values()) or 1
        print(f"{sp.name}: {total} cues")
        for tag in ("change", "intro only", "intro + pulse", "emphasis only", "nothing"):
            if tally[tag]:
                print(f"  {tally[tag]:4d}  {100 * tally[tag] / total:3.0f}%  {tag}")
        if quiet:
            print("  cues that only point at something:")
            for scene, line, mark, clause in quiet:
                print(f"    {scene:11s} :{line:<5d} {mark!r:5s} {clause}")
        out.append(tally)
    return 0
