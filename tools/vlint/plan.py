"""The staging plan: narration first, then one line per cue saying what the picture does.

Writing a scene in one pass puts the words and the pictures in the same head at the same time, and the
pictures lose: a clause gets whichever cue is cheap on whatever is already on screen -- a pulse, a fresh
arrow, another panel beside the last one. Writing the narration first and staging it afterwards forces one
question per clause, with the answer written down before any manim exists: what does this scene's own figure
*do* as this is said?

A video's `plan.md` holds, for each scene:

    ## Intro
    focus: `sh` -- one lipid nanoparticle: a shell of four lipid kinds around a coil of mRNA

    > A [p]lipid nanoparticle is the fatty bubble that carries [r]messenger R N A through the body.
    > [c]When it reaches a cell and unloads, [g]the cell reads the message.

    p  new: the shell flies together out of four kinds of lipid  -- the shell is a mixture, not one substance
    r  new: the coil of mRNA is laid inside it  -- the cargo sits inside the shell, it is not part of it
    c  the particle crosses to the cell and presses into the membrane  -- delivery is a journey, not a jump
    g  the shell opens out, the coil unwinds, protein appears  -- unloading is what "reads the message" means

One `focus:` naming the variable that will hold the scene's figure, the narration exactly as it will be
spoken with `[mark]` where each cue fires, and one action line per mark. Several blockquotes, separated by a
blank line, are the scene's narration blocks in order. An action line is `<mark>  what happens  -- why`:
the picture first, then what the viewer is meant to take from it. The why is what keeps a cue honest -- one
whose why only restates the words ("shows the particle") is a cue to delete, and writing the why down is how
the staging pass notices.

A plain action line means the focus itself changes -- the line worth having, so it needs no prefix; `side:`
is a change to something else on screen, `new:` something arriving, `mark:` a pulse on something already
there, and `morph:` one object on screen becoming another, which has to be asked for because a thing that
turns into a different thing is a thing the viewer stops tracking.

`rules_static_plan.py` then holds the code to it: the narration in the script must be the planned narration,
every mark must have a cue, and a mark whose action line describes an event must have an animation that
changes something rather than a pulse on it. The plan cannot rot into documentation, because editing either
side alone fails the check. A video with no `plan.md` is checked as before, by the heuristics that guess
(`scene-protagonist`, `pulse-for-event`).

    python tools/vlint plan <video> --draft > <video>/plan.md    # skeleton from an existing script
"""
import re
import textwrap
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .script import MARK

SECTION = re.compile(r"^##\s+(\w+)\s*$")
FOCUS = re.compile(r"^focus:\s*(.*\S)?\s*$", re.I)
ENTITY = re.compile(r"`([A-Za-z_]\w*)`")
PROSE = re.compile(r"^>\s?(.*)$")
ACTION = re.compile(r"^([A-Za-z0-9_]+)(?:(?:\s{2,}|\t)\s*(\S.*?))?\s*$")   # a bare mark is a line not filled in yet
WHY = re.compile(r"\s+--\s+")                                             # "what happens  -- why it is shown"
IN_PROSE = re.compile(r"\[([A-Za-z0-9_]+)\]")
COMMENT = re.compile(r"<!--.*?-->")                                       # an aside to a reader, not narration


@dataclass
class Block:
    """One narration block: the words, and what happens on each of its marks. A mark only has to be unique
    within its block, as in the script, so the action lines sit under the block they belong to."""
    line: int
    prose: str = ""
    actions: dict = field(default_factory=dict)       # mark -> (line, what happens, why it is shown)

    @property
    def marks(self):
        return IN_PROSE.findall(self.prose)


@dataclass
class Staging:
    """One scene's section of the plan."""
    name: str
    line: int
    focus: str = ""
    focus_line: int = 0
    entity: str = ""                                  # the variable named in `focus:`, if it names one
    blocks: list = field(default_factory=list)        # Block, in the order they are spoken
    bad: list = field(default_factory=list)           # (line, message): this section is not usable as written


@dataclass
class Plan:
    path: Path
    scenes: dict = field(default_factory=dict)
    bad: list = field(default_factory=list)


def _split_why(action):
    """An action line's two halves: what the picture does, and what that is meant to show. Only the first ` -- `
    separates them, so a why may contain dashes of its own."""
    parts = WHY.split(action, 1)
    return (parts[0].strip(), parts[1].strip() if len(parts) > 1 else "")


def spoken(text):
    """A narration string as the plan writes it: bookmarks as [mark], one space between words."""
    return " ".join(MARK.sub(lambda m: f"[{m.group(1)}]", text).split())


def load(video_dir):
    """The plan beside a script, or None. Cached: four rules read the same file."""
    p = Path(video_dir) / "plan.md"
    return _load(p, p.stat().st_mtime_ns) if p.exists() else None


@lru_cache(maxsize=16)
def _load(path, _mtime):
    plan, cur, para = Plan(path), None, None
    for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        ln = COMMENT.sub("", raw).rstrip()
        if raw.strip() and not ln.strip():
            continue                                   # a line that was only an <!-- html comment -->
        m = SECTION.match(ln)
        if m:
            cur, para = Staging(m.group(1), i), None
            if m.group(1) in plan.scenes:
                plan.bad.append((i, f"{m.group(1)} has two sections in the plan"))
            plan.scenes[m.group(1)] = cur
            continue
        if not ln.strip():
            para = None
            continue
        if cur is None:
            continue                                   # the file's own title and any prose before the first scene
        m = PROSE.match(ln)
        if m:
            if para is None:
                para = Block(i, m.group(1).strip())
                cur.blocks.append(para)
            else:
                para.prose = (para.prose + " " + m.group(1).strip()).strip()
            continue
        m = FOCUS.match(ln)
        if m:
            cur.focus, cur.focus_line = m.group(1) or "", i
            e = ENTITY.search(cur.focus)
            cur.entity = e.group(1) if e else ""
            continue
        m = ACTION.match(ln)
        if m:
            if not cur.blocks:
                cur.bad.append((i, f"an action line for {m.group(1)!r} before any narration in this section"))
                continue
            b = cur.blocks[-1]                             # the lines under a block stage that block
            if m.group(1) in b.actions:
                cur.bad.append((i, f"two action lines for mark {m.group(1)!r} in one block"))
            b.actions[m.group(1)] = (i, *_split_why(m.group(2) or ""))
            continue
        cur.bad.append((i, f"not a focus line, a quoted narration line or a '<mark>  what happens' line: {ln[:40]!r}"))
    for st in plan.scenes.values():
        for b in st.blocks:
            seen = set()
            for mk in b.marks:
                if mk in seen:
                    st.bad.append((b.line, f"mark {mk!r} appears twice in one narration block"))
                seen.add(mk)
    return plan


# ---- check ----------------------------------------------------------------------------------------------------
def check(path):
    """Read a plan on its own, before any manim exists. The plan-* rules compare a plan with a script, so until
    there is a script nothing holds the staging pass to anything: this is what it runs while it writes."""
    p = Path(path)
    p = p if p.is_file() else p / "plan.md"
    if not p.exists():
        print(f"no plan at {p}")
        return 2
    plan = _load(p, p.stat().st_mtime_ns)
    bad = [(line, msg) for line, msg in plan.bad]
    for st in plan.scenes.values():
        bad += st.bad
        if not st.focus:
            bad.append((st.line, f"{st.name} has no focus line"))
        elif not st.entity:
            bad.append((st.focus_line, f"{st.name}'s focus names no variable in `backticks`"))
        if not st.blocks:
            bad.append((st.line, f"{st.name} has no narration"))
        for b in st.blocks:
            for mk in b.marks:
                line, what, why = b.actions.get(mk, (b.line, "", ""))
                if not what:
                    bad.append((line, f"{st.name}: [{mk}] has no action line"))
                elif not why:
                    bad.append((line, f"{st.name}: [{mk}] says what happens and not why ({what[:40]})"))
                if _ARRIVES.match(what):
                    bad.append((line, f"{st.name}: [{mk}] is `side:` but brings something on ({what[:40]}): that is `new:`"))
            for mk, (line, _w, _y) in b.actions.items():
                if mk not in b.marks:
                    bad.append((line, f"{st.name}: an action line for [{mk}], which this block never says"))
    bad += _facts(p, plan)
    for line, msg in sorted(bad):
        print(f"{p.name}:{line}: {msg}")
    cues = sum(len(b.marks) for st in plan.scenes.values() for b in st.blocks)
    print(f"plan: {len(plan.scenes)} scene(s), {cues} cue(s), {len(bad)} problem(s)")
    return 1 if bad else 0


_FIGPAGE = re.compile(r"\b(Fig(?:ure|\.)?|Table)\s*(\d+)\b[^\n.;]{0,60}?\bpage\s+(\d+)", re.I)
# a `side:` line whose first verb is an arrival: writers re-prefixed 9 to 11 of these per video (pet_entangled to mono_review)
_ARRIVES = re.compile(r"side:\s*(?:\S+\s+){0,6}?(?:fades? in|appears?|arrives?|is drawn|draws? in|enters?|slides? in|grows? in|"
                      r"comes? in|pops? in|is written)\b", re.I)
_CAPTION = re.compile(r"(?:^ *|   +)(Figure|Fig\.|Table|TABLE) +(\d+)(?:[:.]| +[A-Z])")


def _captions(txt):
    """{("fig"|"table", n): {pages}} from pdftotext's form feeds, as tools/prep.sh lists them in the brief."""
    out, page = {}, 1
    for ln in txt.read_text(encoding="utf-8", errors="replace").split("\n"):  # not splitlines(), which splits on the form feeds too
        page += ln.count("\f")
        for m in _CAPTION.finditer(ln.replace("\f", "")):
            out.setdefault(("table" if m.group(1).lower() == "table" else "fig", int(m.group(2))), set()).add(page)
    return out


def _facts(p, plan):
    """What a plan can get wrong before any manim exists and a writer then works round (pico40l): a figure cited on
    the wrong page, and a focus that names a function (a shared helper or a kit primitive) instead of the variable
    that will hold what it draws."""
    bad = []
    txt = p.parent / "src" / "paper.txt"
    if txt.exists():
        caps = _captions(txt)
        for i, ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for m in _FIGPAGE.finditer(ln):
                key = ("table" if m.group(1).lower() == "table" else "fig", int(m.group(2)))
                pages = caps.get(key)
                if pages and int(m.group(3)) not in pages:
                    bad.append((i, f"{m.group(1)} {m.group(2)} is on page {'/'.join(map(str, sorted(pages)))} of "
                                   f"src/paper.txt, not page {m.group(3)}"))
    import ast
    fns = set()
    for f in [*p.parent.glob("*_vo.py"), Path(__file__).resolve().parents[2] / "kit.py"]:
        try:
            fns |= {n.name for n in ast.parse(f.read_text(encoding="utf-8")).body if isinstance(n, ast.FunctionDef)}
        except (OSError, SyntaxError):
            pass
    for st in plan.scenes.values():
        if st.entity and st.entity in fns:
            bad.append((st.focus_line, f"{st.name}'s focus `{st.entity}` is a function: name the variable the scene "
                                       f"assigns its result to (e.g. `vs = {st.entity}(...)` and focus: `vs`)"))
    return bad


# ---- draft ----------------------------------------------------------------------------------------------------
def draft(path):
    """Print a plan skeleton for a script that already exists: its scenes, its narration with the marks it
    already cues, and a blank line per mark. Filling those lines in is the staging pass; where what the code
    does now is not what the line ends up saying, the code is what changes."""
    from .core import load_config
    from .script import load_script

    for sp in ([Path(path)] if Path(path).is_file() else sorted(Path(path).glob("*_vo.py"))):
        s = load_script(sp, load_config(sp.parent))
        print(f"# {sp.parent.name}: staging plan\n")
        print("One focus per scene, the narration as it is spoken, and `<mark>  what happens  -- why` for every\n"
              "mark: the why is what the viewer is meant to take from it, and a cue with no why is a cue to drop.\n")
        for cls in s.scenes:
            print(f"## {cls.name}")
            print("focus: `?` -- ")
            for vo in [v for v in s.voiceovers if cls.lineno <= v.node.lineno <= cls.end_lineno]:
                if vo.text is None:
                    print("\n> (narration is built at run time; write it out here)")
                    continue
                said = spoken(vo.text)
                print()
                for w in textwrap.wrap(said, 112):
                    print(f"> {w}")
                print()
                for mk in IN_PROSE.findall(said):
                    print(f"{mk}  ")
            print()
    return 0
