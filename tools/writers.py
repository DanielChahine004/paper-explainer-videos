"""Scene writers' copies of a video: cut them, and splice what comes back (DESIGN Part III, step 2).

    python tools/writers.py split <video> a=Cited,Spread,Toolkit b=Fortran,Blind ...
    python tools/writers.py split <video> --per 3          every scene render.sh lists and the script lacks, 3 each
    python tools/writers.py merge <video>

`split` makes one folder per writer, <work>/<video>_<name> (work: $WRITERS_WORK, default ../slab_work beside the
repository; the name is unique because tools/sync.sh keys the render root on it). Each holds:
  - the script with every scene class taken out: the shared helpers, then one marker line. The writer adds
    scenes below the marker and touches nothing above it;
  - examples.py, the scenes the lead has already written, to read for the house style. It is not a *_vo.py,
    so nothing lints or renders it;
  - render.sh listing only that writer's scenes, and plan.md holding only their sections;
  - assets/, heard_ok.txt and vlint.toml as the video has them, and WRITER.md, which is the writer's brief;
  - helpers.png, every shared helper drawn once. split refuses without it when the script has helpers.
So the writer's first check passes the scene-list gate. On geant4 the base carried two finished scenes as
examples and a render.sh that did not list them; `scene-list` is an error, and all five writers got past it
with VLINT_ALLOW=1 -- five writers independently switching a gate off is the gate teaching them to.

`merge` takes each copy in turn and refuses it, saying why, unless: the script still starts with the base it was
given, byte for byte; what follows defines exactly that writer's scenes and otherwise only `_private` names that
collide with nothing; and no spoken word of its plan sections changed (a re-prefixed action line is fine).
A copy that passes has its scenes appended to the video's script and its plan sections put back. Nothing is
merged from a copy that fails, and the others still are. When every copy is merged, the copies and every
other <work>/<video>_* folder are deleted (--keep leaves them).
"""
import argparse
import ast
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(os.environ.get("WRITERS_WORK", ROOT.parent / "slab_work"))
MARK = "# ==== writer's scenes below this line; nothing above it is yours to edit " + "=" * 40 + "\n"


def _video(v):
    d = ROOT / v
    rsh = (d / "render.sh").read_text(encoding="utf-8")
    script = d / re.search(r'^SCRIPT=["\']?([\w.]+)', rsh, re.M).group(1)
    scenes = re.search(r'^SCENES=["\']([^"\']*)["\']', rsh, re.M).group(1).split()
    return d, rsh, script, scenes


def _tops(text):
    """{name: (first line, last line, is a scene)} for every top-level def, class and assignment."""
    out = {}
    for st in ast.parse(text).body:
        names = []
        if isinstance(st, (ast.FunctionDef, ast.ClassDef)):
            names = [st.name]
        elif isinstance(st, ast.Assign):
            names = [t.id for t in st.targets if isinstance(t, ast.Name)]
        scene = isinstance(st, ast.ClassDef) and any(isinstance(b, ast.FunctionDef) and b.name == "construct" for b in st.body)
        first = min([st.lineno] + [d.lineno for d in getattr(st, "decorator_list", [])])
        for n in names:
            out[n] = (first, st.end_lineno, scene)
    return out


def _sections(plan):
    """(what comes before the first scene, {scene: its section's text}) of a plan.md."""
    parts = re.split(r"(?m)^(?=## )", plan)
    return parts[0], {re.match(r"## +(\S+)", p).group(1): p for p in parts[1:]}


def _spoken(section):
    return " ".join(" ".join(l.lstrip("> ").strip() for l in section.splitlines() if l.startswith(">")).split())


def _helpers_sheet(d, text, sheet):
    """The picture of every shared helper drawn once, which a split needs when the script has helpers: a helper
    is frozen once it is split, so what is wrong with it must be seen first (pet_entangled: dphi_plot put its axis
    name on the 180 degree tick, and four writers each worked round it). None when the script has no helpers."""
    helpers = [n.name for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)]
    if not helpers:
        return None
    p = Path(sheet) if sheet else d / "src" / "helpers.png"
    if not p.exists():
        sys.exit(f"writers: {len(helpers)} shared helpers ({', '.join(helpers[:6])}{' ...' if len(helpers) > 6 else ''}) "
                 f"and no picture of them. Render a throwaway scene that draws each once with a marked target, "
                 f"fix what is wrong, and save one frame or sheet as {d.name}/src/helpers.png (or pass --helpers <png>). "
                 f"DESIGN Part III, step 2.")
    return p


def split(v, assign, per, sheet=None):
    d, rsh, script, scenes = _video(v)
    text = script.read_text(encoding="utf-8")
    hp = _helpers_sheet(d, text, sheet)
    tops = _tops(text)
    written = [n for n, (_, _, sc) in tops.items() if sc]
    if not assign:
        todo = [s for s in scenes if s not in written]
        assign = {chr(97 + i // per): todo[i:i + per] for i in range(0, len(todo), per)}
    taken = [s for ss in assign.values() for s in ss]
    for s in taken:
        if s not in scenes:
            sys.exit(f"writers: {s} is not in {v}/render.sh SCENES")
        if s in written:
            sys.exit(f"writers: {s} is already written in {script.name}; a writer's scene starts empty")
    if len(set(taken)) != len(taken):
        sys.exit("writers: a scene is given to two writers")
    lines = text.splitlines(keepends=True)
    drop = sorted((a, b) for a, b, sc in tops.values() if sc)
    base, examples, at = [], [], 1
    for a, b in drop:
        base += lines[at - 1:a - 1]
        examples += lines[a - 1:b] + ["\n\n"]
        at = b + 1
    base += lines[at - 1:]
    base = re.sub(r"\n{4,}", "\n\n\n", "".join(base)).rstrip("\n") + "\n\n\n" + MARK
    plan = (d / "plan.md").read_text(encoding="utf-8")
    head, secs = _sections(plan)
    state = {"video": v, "script": script.name, "writers": {}}
    WORK.mkdir(parents=True, exist_ok=True)
    for name, mine in assign.items():
        missing = [s for s in mine if s not in secs]
        if missing:
            sys.exit(f"writers: plan.md has no section for {', '.join(missing)}")
        c = WORK / f"{v}_{name}"
        if c.exists():
            shutil.rmtree(c)
        c.mkdir()
        (c / script.name).write_text(base, encoding="utf-8", newline="\n")
        (c / ".base").write_text(base, encoding="utf-8", newline="\n")
        if examples:
            (c / "examples.py").write_text(
                '"""Scenes of this video that are already written: read them for the house style. Not rendered,\n'
                'not checked, and not yours to change."""\nfrom kit import *  # noqa\n\n\n' + "".join(examples),
                encoding="utf-8", newline="\n")
        (c / "render.sh").write_text(re.sub(r'(?m)^SCENES=.*$', f'SCENES="{" ".join(mine)}"', rsh), encoding="utf-8", newline="\n")
        (c / "plan.md").write_text(head + "".join(secs[s] for s in mine), encoding="utf-8", newline="\n")
        for extra in ("heard_ok.txt", "vlint.toml"):
            if (d / extra).exists():
                shutil.copy2(d / extra, c / extra)
        txts = sorted((d / "src").glob("*.txt"))        # number-unsourced reads them; without them it stands down
        if txts:
            (c / "src").mkdir()
            for t in txts:
                shutil.copy2(t, c / "src" / t.name)
        if (d / "assets").is_dir():
            shutil.copytree(d / "assets", c / "assets")
        if hp:
            shutil.copy2(hp, c / "helpers.png")
        wsl = "/mnt/" + c.drive[0].lower() + c.as_posix()[2:] if c.drive else c.as_posix()
        wroot = "/mnt/" + ROOT.drive[0].lower() + ROOT.as_posix()[2:] if ROOT.drive else ROOT.as_posix()
        (c / "WRITER.md").write_text(_BRIEF.format(v=v, scenes=", ".join(mine), script=script.name, c=c.as_posix(), wsl=wsl,
                                                   root=ROOT.as_posix(), wroot=wroot, ex="examples.py holds the scenes already written: "
                                                   "read it for the house style.\n" if examples else ""),
                                     encoding="utf-8", newline="\n")
        state["writers"][name] = {"dir": str(c), "scenes": mine}
        print(f"  {name}: {', '.join(mine)}  ->  {c}")
    (WORK / f"{v}_writers.json").write_text(json.dumps(state, indent=1), encoding="utf-8")
    print(f"== {len(assign)} writer cop{'y' if len(assign) == 1 else 'ies'}; each one's brief is its WRITER.md")


_BRIEF = """# Scene writer: {scenes} ({v})

You write these scenes of one video, and nothing else: {scenes}.

Your folder is {c}. Work only in it.
- plan.md is your whole brief: every spoken word, every cue and what it is for. You do not need the paper.
- helpers.png shows every shared helper drawn once (if the script has helpers): look at it before calling one.
- {script} holds the video's shared helpers and palette, then a marker line. Add your scenes below the marker.
  Change nothing above it. A helper of your own is named `_<scene>_<what>` and goes below the marker too.
- Before you write a helper, read {root}/KIT.md: the shared primitives (code, call trees, files, stacks,
  dimension lines, tracks, detector drawings), tested under both engines. If the script imports kit, use them.
  If one is wrong for your scene, say so in your report rather than working round it silently.
- {ex}- You may change the prefix of an action line in plan.md (new:, side:, mark:, morph:) when the check asks
  for it. You may not change a spoken word, in the plan or in the script.
- Read DESIGN.md Part II and Part IV in {root} before you write.
- Write code with the Write and Edit tools, never a shell heredoc: an apostrophe in a label breaks the quoting.

Check after every edit, and render once, at the end:
    wsl bash {wroot}/tools/check.sh {wsl}
    wsl bash -c 'QUALITY=-ql bash {wroot}/tools/run_v.sh {wsl}'
(from Git Bash, prefix both with MSYS_NO_PATHCONV=1, or it rewrites the /mnt/c paths. QUALITY is set inside the
wsl command because a variable set in front of `wsl` does not cross into it, and the render then runs at 1080p)
The first is static checks and every scene in skip mode, about 25 s, nothing rendered: loop on it until it is
clean. Only then run the second, which renders your scenes at 480p (minutes) and leaves a sheet per scene in
review/: read them, fix what they show, check again, and render again only if a fix changed the picture.
Rendering between checks was most of a writer's time on pet_mrpc. Never set VLINT_ALLOW: an error from the
check is yours to fix, and if you believe it is wrong, say so in your report instead.

render.sh lists all of your scenes, and the check holds you to that list: a scene it names and you have not
written yet is an error. While you work, shorten SCENES in render.sh to the scenes you have written so far,
and put it back before you hand back. That one line is the only thing in render.sh that is yours.

Hand back when both are clean with every scene listed. Report what you were unsure of. Do not commit.
"""


def merge(v, keep=False):
    d, rsh, script, scenes = _video(v)
    state = json.loads((WORK / f"{v}_writers.json").read_text(encoding="utf-8"))
    text = script.read_text(encoding="utf-8")
    plan_path = d / "plan.md"
    head, secs = _sections(plan_path.read_text(encoding="utf-8"))
    ok = True
    for name, w in state["writers"].items():
        c, mine = Path(w["dir"]), w["scenes"]
        if w.get("merged"):
            print(f"  {name}: already merged ({', '.join(mine)})")
            continue
        why = []
        base = (c / ".base").read_text(encoding="utf-8")
        got = (c / state["script"]).read_text(encoding="utf-8").replace("\r\n", "\n")
        rest = got[len(base):]
        if not got.startswith(base):
            k = next((i for i, (x, y) in enumerate(zip(got, base)) if x != y), min(len(got), len(base)))
            why.append(f"edited above the marker, at line {base.count(chr(10), 0, k) + 1} of the base")
        else:
            try:
                new = _tops(base + rest)
            except SyntaxError as e:
                new, why = {}, [f"does not parse: {e.msg} (line {e.lineno})"]
            old, have = _tops(base), _tops(text)
            added = {n: t for n, t in new.items() if n not in old}
            for s in mine:
                if s not in added or not added[s][2]:
                    why.append(f"{s} is not written")
            for n, (_, _, scene) in added.items():
                if scene and n not in mine:
                    why.append(f"wrote a scene that is not its own: {n}")
                elif not scene and not n.startswith("_"):
                    why.append(f"added a shared name: {n} (a writer's helper is _private)")
                if n in have:
                    why.append(f"{n} is already in {script.name}")
        _, theirs = _sections((c / "plan.md").read_text(encoding="utf-8").replace("\r\n", "\n"))
        for s in mine:
            if s not in theirs:
                why.append(f"plan.md lost the section for {s}")
            elif _spoken(theirs[s]) != _spoken(secs[s]):
                why.append(f"plan.md: the spoken words of {s} changed")
        if why:
            ok = False
            print(f"  {name}: NOT merged ({', '.join(mine)})")
            for x in why:
                print(f"      {x}")
            continue
        text = text.rstrip("\n") + "\n\n\n" + rest.strip("\n") + "\n"
        for s in mine:
            secs[s] = theirs[s]
        w["merged"] = True
        print(f"  {name}: merged {', '.join(mine)}")
    script.write_text(text, encoding="utf-8", newline="\n")
    plan_path.write_text(head + "".join(secs.values()), encoding="utf-8", newline="\n")
    (WORK / f"{v}_writers.json").write_text(json.dumps(state, indent=1), encoding="utf-8")
    if ok and not keep:
        _clean(v)
    print(f"== {v}: now run  wsl bash tools/check.sh {v}" + ("" if ok else "   (after the copies above are put right and merged)"))
    return 0 if ok else 1


def _clean(v):
    """Every copy merged: the copies, the state file and the lead's throwaway folders (<video>_words, _helpers...)
    go. slab_work held 70-odd of them by pet_mrpc. A name that starts with another video's name and an underscore is
    that video's (g4_inside_a is not g4's), so it stays."""
    others = [p.name for p in ROOT.iterdir() if p.is_dir() and p.name != v]
    gone = []
    for p in WORK.glob(f"{v}_*"):
        if any(p.name.startswith(o + "_") and len(o) > len(v) for o in others):
            continue
        shutil.rmtree(p) if p.is_dir() else p.unlink()
        gone.append(p.name)
    if gone:
        print(f"  removed from {WORK}: {', '.join(sorted(gone))}  (--keep to leave them)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("split")
    s.add_argument("video"), s.add_argument("assign", nargs="*"), s.add_argument("--per", type=int, default=3)
    s.add_argument("--helpers", help="the picture of every shared helper (default <video>/src/helpers.png)")
    m = sub.add_parser("merge")
    m.add_argument("video"), m.add_argument("--keep", action="store_true", help="leave the copies in the work folder")
    a = ap.parse_args()
    if a.cmd == "split":
        split(a.video, {x.split("=")[0]: x.split("=")[1].split(",") for x in a.assign}, a.per, a.helpers)
        return 0
    return merge(a.video, a.keep)


if __name__ == "__main__":
    sys.exit(main())
