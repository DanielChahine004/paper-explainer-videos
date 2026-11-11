"""Rules that hold a scene to its staging plan (plan.md, see plan.py).

The plan is written before the manim: the narration first, then one line per cue saying what the scene's
figure does as that clause is spoken. These rules make the two sides inseparable. The narration in the code
must be the planned narration, word for word, so neither side can be edited alone. Every mark in the planned
narration must be cued. And every action line declares what kind of cue it is -- the picture does something
(the default), `new:` something arrives, `mark:` something already on screen is named again -- which the code
must match, so "the shell opens out" cannot ship as an Indicate on the shell. The four kinds of line:

    c  the particle crosses to the cell and presses in     the focus changes (the default)
    n  side: the tally beside it ticks up to four          something else on screen changes
    p  new: a well plate is set down on the right          something arrives
    t  mark: the abstract's promise is named again         a pulse on what is already there
    m  morph: the counts become the picture of the tracer  one object on screen turns into another

Every line also says why, after ` -- `: what the viewer is meant to take from the cue, which is the question a
cue that illustrates nothing cannot answer. `morph:` has to be declared because a thing that turns into a
different thing is a thing the viewer stops tracking (user, mc_recon: 'some entities just straight up turn
into different ones (e.g. a detector turns into an arrow) which is confusing to track').


Where the heuristics (scene-protagonist, pulse-for-event) guess the intent from the narration's verbs, these
read it off a declaration, so they are errors rather than warnings. A video with no plan.md is silent here.
"""
import ast
import re

from .core import rule
from .plan import IN_PROSE, load, spoken
from .rules_static import CHANGE, MORPH, _anim_calls
from .script import EMPHASIS, INTRO, call_name

# What an action line declares, and what the cue must then contain. The unprefixed line -- the scene's figure
# does something -- is the one worth having, so it is the default; the other four have to be asked for.
KINDS = {
    "": ("change to the focus", CHANGE, "an animation that changes the scene's focus"),
    "side:": ("change", CHANGE, "an animation that changes something already on screen"),
    "new:": ("introduction", INTRO, "an animation that brings something on"),
    "mark:": ("pulse", EMPHASIS, "a pulse (Indicate, Circumscribe, Flash)"),
    "morph:": ("metamorphosis", MORPH, "a Transform of one object into another"),
}


def kind_of(action):
    for pre in ("new:", "mark:", "side:", "morph:"):
        if action.lower().startswith(pre):
            return pre
    return ""


def _changed(node):
    """Names mentioned by the parts of a cue that change something, as opposed to bringing it on or pulsing it.
    Every name in such a part counts, not just the animation's target: `VGroup(sh, cg).animate.move_to(dock)`
    does move the shell, and a method chain hides the name from _base (it bottoms out on a Call, not a Name).
    The question here is only whether the cue touches the figure the plan named, so being generous is right."""
    out = set()
    for a in getattr(node, "args", [])[1:]:
        if any(c in CHANGE for c in _anim_calls(a)):
            out |= {n.id for n in ast.walk(a) if isinstance(n, ast.Name)}
    return {n for n in out if n != "self" and not n.isupper()}


def _vos(s, cls):
    return [vo for vo in s.voiceovers if cls.lineno <= vo.node.lineno <= cls.end_lineno]


@rule("plan-missing", "static", "warn", "The video has a staging plan and this scene is not in it (or the plan has "
      "a section for a scene the script does not have), so this scene's cues were staged by hand with nothing to "
      "check them against.",
      "Part III, write the narration first and stage it second",
      "add a `## Scene` section with a focus and one action line per mark (`vlint plan <video> --draft` prints the "
      "skeleton), or delete the stale section")
def plan_missing(s):
    plan = load(s.path.parent)
    if plan is None:
        return
    names = {c.name for c in s.scenes}
    for cls in s.scenes:
        if cls.name not in plan.scenes:
            yield cls, f"{cls.name} has no section in plan.md"
    for name, st in plan.scenes.items():
        if name not in names:
            yield ("plan.md", st.line), f"the plan stages {name}, which is not a scene in {s.path.name}"


@rule("plan-narration", "static", "error", "The narration in the script is not the narration in the plan. The plan "
      "is what the staging was written against, so a block edited on one side only leaves every action line below "
      "it describing a sentence that is no longer spoken.",
      "Part III, write the narration first and stage it second",
      "make the two the same: the plan's quoted lines are the spoken words with [mark] where each cue fires")
def plan_narration(s):
    plan = load(s.path.parent)
    if plan is None:
        return
    for line, msg in plan.bad:
        yield ("plan.md", line), msg
    for cls in s.scenes:
        st = plan.scenes.get(cls.name)
        if st is None:
            continue
        for line, msg in st.bad:
            yield ("plan.md", line), msg
        blocks = _vos(s, cls)
        if not st.blocks:
            yield ("plan.md", st.line), f"{cls.name} has no narration in the plan"
            continue
        if len(blocks) != len(st.blocks):
            yield ("plan.md", st.line), (f"{cls.name} has {len(st.blocks)} narration block(s) in the plan and "
                                         f"{len(blocks)} in {s.path.name}")
            continue
        for vo, b in zip(blocks, st.blocks):
            if vo.text is None:
                continue                            # built at run time: nothing to compare, cues still checked
            got, want = spoken(vo.text), b.prose
            if got != want:
                yield vo.node, f"the narration here is not the planned narration: {_diff(want, got)}"


def _diff(want, got):
    w, g = want.split(), got.split()
    k = next((i for i in range(min(len(w), len(g))) if w[i] != g[i]), min(len(w), len(g)))
    return f"plan says ...{' '.join(w[k:k + 7])!r}, script says ...{' '.join(g[k:k + 7])!r}"


@rule("plan-focus", "static", "error", "A scene's plan does not name the one figure the scene is about, or names a "
      "variable the scene never builds. The focus is the whole point of staging the narration separately: it is "
      "the thing every action line then does something to.",
      "Part I §1, one central figure, mutated",
      "focus: `name` -- what it is, where `name` is the variable that will hold it in the scene")
def plan_focus(s):
    plan = load(s.path.parent)
    if plan is None:
        return
    for cls in s.scenes:
        st = plan.scenes.get(cls.name)
        if st is None:
            continue
        if not st.focus:
            yield ("plan.md", st.line), f"{cls.name} has no focus line"
            continue
        if not st.entity:
            yield ("plan.md", st.focus_line), (f"{cls.name}'s focus names no variable: write the name of the object in "
                                         f"backticks, as in focus: `sh` -- {st.focus[:40]}")
            continue
        built = {t.id for n in ast.walk(cls) if isinstance(n, ast.Assign)
                 for t in n.targets if isinstance(t, ast.Name)}
        built |= {n.target.id for n in ast.walk(cls)
                  if isinstance(n, (ast.AnnAssign, ast.AugAssign)) and isinstance(n.target, ast.Name)}
        built |= {el.id for n in ast.walk(cls) if isinstance(n, ast.Assign)
                  for t in n.targets if isinstance(t, (ast.Tuple, ast.List))
                  for el in t.elts if isinstance(el, ast.Name)}
        if st.entity not in built:
            yield ("plan.md", st.focus_line), f"{cls.name}'s focus is `{st.entity}`, which the scene never builds"


@rule("plan-action", "static", "error", "A cue does not do what the plan says happens on that word: the plan has no "
      "line for it, the script has no cue for it, or the line says the picture does something and the cue only "
      "brings a fresh object on or pulses one (user, lnp_comet: 'the lipid nanoparticle should've gone into the "
      "cell, dissolved or whatever it does, and the mRNA released as the narration says').",
      "Part I §1, animate the event, not a pulse on its picture",
      "animate what the line describes on the scene's focus, or -- if the line was wrong -- say what the cue really "
      "is: `new:` for something arriving, `mark:` for something named again")
def plan_action(s):
    plan = load(s.path.parent)
    if plan is None:
        return
    # A cue fired through one of the script's own cue helpers (a page walk's self.hl / self.turn / self.lift)
    # animates nothing at the call site: what it does is in the helper's body, so read that as well. Both, not
    # one or the other: these helpers take extra animations to play alongside their own (`self.turn(10, "c",
    # FadeOut(ring))`), and reading only those would say a page turn brings nothing on. Without this the format's
    # helpers cannot be used at all and every scene re-implements the page turn by hand.
    bodies = {fn.name: fn for fn in ast.walk(s.tree) if isinstance(fn, ast.FunctionDef)}
    for cls in s.scenes:
        st = plan.scenes.get(cls.name)
        if st is None:
            continue
        vos = _vos(s, cls)
        if len(vos) != len(st.blocks):
            continue                       # plan-narration has said so already; pairing them up would be a guess
        for vo, b in zip(vos, st.blocks):
            cues = {}
            for mark, node in vo.cues:
                cues.setdefault(mark, node)
            for mk, (line, action, _why) in b.actions.items():
                if mk not in b.marks:
                    yield ("plan.md", line), f"{cls.name}: an action line for [{mk}], which this block never says"
            for mk in b.marks:
                line, action, _why = b.actions.get(mk, (b.line, "", ""))
                if not action:
                    yield ("plan.md", line), \
                        f"{cls.name}: [{mk}] has no action line, so nothing says what happens on that word"
                    continue
                node = cues.get(mk)
                if node is None:
                    if not vo.dynamic:
                        yield ("plan.md", line), f"{cls.name}: nothing is cued on [{mk}] ({action[:48]})"
                    continue
                pre = kind_of(action)
                name, want, what = KINDS[pre]
                calls = _anim_calls(node) + _anim_calls(bodies.get(call_name(node)))
                if not calls:
                    yield node, f"[{mk}] is a {name} in the plan ({action[:48]}) and this cue animates nothing"
                elif not any(c in want for c in calls):
                    yield node, (f"[{mk}] in the plan is {action[len(pre):].strip()[:56]!r}, which needs {what}; "
                                 f"this cue has {'/'.join(sorted(set(calls)))}")
                elif pre == "" and st.entity and st.entity not in _changed(node):
                    yield node, (f"[{mk}] is staged on the scene's focus `{st.entity}` ({action[:44]}), and this "
                                 f"cue changes {', '.join(sorted(_changed(node))) or 'nothing'} instead "
                                 f"(write `side:` if the change really belongs elsewhere)")


@rule("plan-why", "static", "warn", "An action line says what happens and not why: nothing records what the viewer "
      "is meant to take from the cue. That question is the one an unnecessary animation cannot answer, so leaving "
      "it out is how a scene fills up with cues that illustrate nothing (user, mc_recon: 'there seems to be too "
      "many unnecessary [or un]explainable animations in the video now').",
      "Part III, write the narration first and stage it second",
      "finish the line as `<mark>  what happens  -- why`, where the why says what the picture shows that the words "
      "do not. If the only honest why restates the words, drop the cue")
def plan_why(s):
    plan = load(s.path.parent)
    if plan is None:
        return
    for cls in s.scenes:
        st = plan.scenes.get(cls.name)
        if st is None:
            continue
        for b in st.blocks:
            for mk, (line, action, why) in b.actions.items():
                if not action:
                    continue                            # plan-action has said the line is empty
                if not why:
                    yield ("plan.md", line), \
                        f"{cls.name}: [{mk}] says what happens ({action[:44]}) and not what it illustrates"
                elif len(why.split()) < 4 or set(_words(why)) <= set(_words(action)):
                    yield ("plan.md", line), \
                        f"{cls.name}: [{mk}]'s why repeats what happens rather than saying what it shows: {why[:48]!r}"


def _words(t):
    return [w for w in re.findall(r"[a-z]+", t.lower()) if w not in STOP and len(w) > 2]


STOP = {"the", "and", "its", "it", "a", "an", "of", "to", "is", "are", "that", "this", "then", "as", "on", "in",
        "with", "for", "from", "into", "out", "up", "down", "so", "not", "but", "one", "two", "what", "which"}


def declared_focus(s, cls):
    """The focus a scene's plan names, for the heuristics to prefer over their own guess."""
    plan = load(s.path.parent)
    st = plan.scenes.get(cls.name) if plan else None
    return st.entity if st else ""
