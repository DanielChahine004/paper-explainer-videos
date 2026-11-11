"""Which of a video's helpers another video also needed: the candidates for kit.py (DESIGN Part III, step 8).

    python tools/kit_promote.py <video>          the video's helpers, each with the other videos that define it
    python tools/kit_promote.py --all [N]        helpers defined in N or more videos (default 3), across the corpus

A helper is a top-level function of a video's *_vo.py. Two are the same helper when they share a name, and the
same code when their bodies match once docstrings are dropped. A name kit.py already has is reported as such:
the video wrote its own instead of using kit's, which is either a gap in kit to close or a habit to break.
"""
import ast
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {"kit_gallery", "voice_ab"}
# first parameters that name the same thing
SAME = {"text": "t", "txt": "t", "s": "t", "label": "t", "string": "t", "fn": "path", "file": "path", "img": "path",
        "name_": "name", "title": "name"}
# names videos gave to what kit has under another name
ALIASES = {"kernel": "slots_box", "chip": "card", "dimline": "dim", "dim_line": "dim", "budget": "gauge",
           "interface": "snell", "grid8": "sipm_grid", "sipm_face": "sipm_grid", "path_line": "poly",
           "polyline": "poly", "hbar": "bars"}


def scripts():
    """Every video's *_vo.py: a video is a folder at the root here, under videos/ in the public repo."""
    return sorted(ROOT.glob("*/*_vo.py")) + sorted(ROOT.glob("videos/*/*_vo.py"))


def _body(fn):
    body = [b for b in fn.body if not (isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant)
                                       and isinstance(b.value.value, str))]
    return ast.dump(ast.Module(body=body, type_ignores=[]))


def helpers(py):
    try:
        tree = ast.parse(py.read_text(encoding="utf-8"))
    except SyntaxError:
        return {}
    return {n.name: _body(n) for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")}


def corpus():
    out = {}
    for py in scripts():
        if py.parent.name not in SKIP:
            out[py.parent.name] = helpers(py)
    return out


def kit_names():
    tree = ast.parse((ROOT / "kit.py").read_text(encoding="utf-8"))
    return {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}


def params(py):
    """name -> its parameter names, for each top-level function of a file."""
    try:
        tree = ast.parse(py.read_text(encoding="utf-8"))
    except SyntaxError:
        return {}
    return {n.name: [a.arg for a in n.args.args] for n in tree.body if isinstance(n, ast.FunctionDef)}


def clashes(name, video_params):
    """Videos whose `name` is not kit's `name`: the same word for another thing (pet_g4_configs: its figcard was
    the card(path, h) of four videos, which kit_promote reported as 'in kit' because kit's card is an object card).
    Told apart by their first parameter's name."""
    kp = params(ROOT / "kit.py").get(name)
    same = lambda a: SAME.get(a, a)
    return [v for v, ps in video_params.items() if name in ps and kp is not None and ps[name][:1] and kp[:1]
            and same(ps[name][0]) != same(kp[0])]


def one(video):
    pys = sorted((ROOT / video).glob("*_vo.py")) or sorted((ROOT / "videos" / video).glob("*_vo.py"))
    if not pys:
        sys.exit(f"kit_promote: no *_vo.py in {video}")
    mine, others, kit = helpers(pys[0]), corpus(), kit_names()
    others.pop(video, None)
    vp = {py.parent.name: params(py) for py in scripts() if py.parent.name not in SKIP | {video}}
    ref = {}                                      # kit's name a helper of mine matches by code elsewhere, under another name
    for name, body in mine.items():
        for v, h in others.items():
            for other, b in h.items():
                if b == body and other != name and other in kit and clashes(other, vp):
                    ref.setdefault(name, set()).add(f"{other} in {v}")
    print(f"== {video}: {len(mine)} helpers")
    for name, body in sorted(mine.items()):
        same_name = [v for v, h in others.items() if name in h]
        same_code = [v for v, h in others.items() if body in h.values()]
        note = []
        if name in kit or ALIASES.get(name) in kit:
            k = name if name in kit else ALIASES[name]
            note.append(f"kit has it{'' if k == name else ' as ' + k}: use it, or say why it did not fit")
        if same_code:
            note.append(f"same code in {len(same_code)}: {', '.join(same_code[:4])}{' ...' if len(same_code) > 4 else ''}")
        if same_name:
            note.append(f"same name in {len(same_name)}: {', '.join(same_name[:4])}{' ...' if len(same_name) > 4 else ''}")
        if name in ref:
            note.append("other videos call it " + ", ".join(sorted(ref[name])[:4]) + ", a name kit uses for something else")
        known = name in kit or ALIASES.get(name) in kit
        tag = "in kit" if known else ("PROMOTE?" if same_code or same_name or name in ref else "")
        print(f"  {name:<18} {tag:<9} {'; '.join(note) or 'this video only'}")


def every(n):
    by_name, kit = defaultdict(list), kit_names()
    vp = {py.parent.name: params(py) for py in scripts() if py.parent.name not in SKIP}
    for v, h in corpus().items():
        for name, body in h.items():
            by_name[name].append(body)
    rows = sorted(((len(b), len(set(b)), name) for name, b in by_name.items() if len(b) >= n), reverse=True)
    print(f"== helpers defined in {n} or more videos (videos, distinct versions, name)")
    for k, d, name in rows:
        k_ = name if name in kit else ALIASES.get(name) if ALIASES.get(name) in kit else None
        other = clashes(name, vp) if name in kit else []
        if other:
            print(f"  {k:>3} {d:>3}  {name}  (kit's {name} is another thing; {len(other)} videos mean: {', '.join(other[:4])})")
            continue
        print(f"  {k:>3} {d:>3}  {name}{'  (in kit' + ('' if k_ == name else ' as ' + str(k_)) + ')' if k_ else ''}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    if a[0] == "--all":
        every(int(a[1]) if len(a) > 1 else 3)
    else:
        one(a[0])
