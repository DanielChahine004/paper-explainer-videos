"""Static rules: read the scene script and render.sh before anything renders. Each one encodes a mistake that
already cost a render (see the DESIGN.md reference) and checks it deterministically."""
import ast
import io
import re
import tokenize
from pathlib import Path

from .core import opt, rule
from .script import EMPHASIS, INTRO, MARK, TEXT_CLASSES, call_name, render_scenes

TEX_CALLS = {"Tex", "MathTex", "SingleStringMathTex"}


def _str_tokens(seg):
    """(prefix, body) for every string literal in a source fragment, f-strings included."""
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(seg).readline))
    except (tokenize.TokenError, SyntaxError):
        return
    fstart = None
    for t in toks:
        name = tokenize.tok_name[t.type]
        if name == "STRING":
            m = re.match(r"([a-zA-Z]*)(['\"]{3}|['\"])", t.string)
            yield m.group(1).lower(), t.string[len(m.group(0)):-len(m.group(2))]
        elif name == "FSTRING_START":
            fstart, body = t.string.lower(), ""
        elif name == "FSTRING_MIDDLE" and fstart is not None:
            body += t.string
        elif name == "FSTRING_END" and fstart is not None:
            yield re.match(r"[a-z]*", fstart).group(0), body
            fstart = None


@rule("syntax-warning", "static", "error", "Python warns while compiling the script (usually an invalid escape "
      "such as '\\s' or '\\a' in a non-raw string).", "Part IV, Editing scripts", "make the string raw: r\"...\"")
def syntax_warning(s):
    for line, msg in s.syntax_warnings:
        yield line, msg


@rule("tex-not-raw", "static", "error", "A Tex/MathTex string with a single backslash is not raw, so '\\tau', "
      "'\\frac', '\\beta' silently become a tab, a form feed, a backspace.", "Part IV, Editing scripts",
      "prefix the literal with r")
def tex_not_raw(s):
    for node in ast.walk(s.tree):
        if call_name(node) in TEX_CALLS:
            for a in [*node.args, *(k.value for k in node.keywords if k.arg in ("tex_string", "arg_separator"))]:
                seg = ast.get_source_segment(s.text, a) or ""
                for prefix, body in _str_tokens(seg):
                    if "r" not in prefix and "\\" in body.replace("\\\\", ""):
                        yield a, f"non-raw string with a backslash: {body[:40]!r}"


_CTRL = re.compile(r"[\x07\x08\x0b\x0c]")


@rule("control-char", "static", "error", "A string holds a bell, backspace, vertical tab or form feed (or a tab "
      "inside Tex), the trace of a LaTeX command eaten by Python escaping.", "Part IV, Editing scripts",
      "restore the backslash and make the string raw")
def control_char(s):
    for node in ast.walk(s.tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and _CTRL.search(node.value):
            yield node, f"control character in {node.value[:40]!r}"
        if call_name(node) in TEX_CALLS | TEXT_CLASSES:
            for a in node.args:
                v = s.resolve_str(a)
                if v and re.search(r"\t[a-z]|\n(?:u|abla|eq|ot|i\b|ewline|ormalsize)", v):
                    yield a, f"tab or newline where a LaTeX command was meant: {v[:40]!r}"


def _anim_targets(args):
    """(kind, key, node) for each animation in a simultaneous group. Succession runs its parts in turn, so it
    is not descended into."""
    for a in args:
        if isinstance(a, ast.Starred):
            a = a.value
            if isinstance(a, (ast.ListComp, ast.GeneratorExp)):
                yield from _anim_targets([a.elt])
            elif isinstance(a, (ast.List, ast.Tuple)):
                yield from _anim_targets(a.elts)
            continue
        n = call_name(a)
        if n in ("AnimationGroup", "LaggedStart"):
            yield from _anim_targets(a.args)
        elif n in INTRO or n in EMPHASIS:
            if a.args:
                yield ("intro" if n in INTRO else "pulse"), ast.dump(a.args[0]), a


@rule("intro-and-pulse", "static", "error", "One play() both introduces a mobject (FadeIn, Create, Write...) and "
      "pulses it (Indicate, Circumscribe...): the pulse restores the faded start state and the object ends "
      "invisible.", "Part IV, Manim 0.19", "fade in first, pulse in a separate play")
def intro_and_pulse(s):
    for node in ast.walk(s.tree):
        n = call_name(node)
        if n in ("play", "at"):
            args = node.args[1:] if n == "at" else node.args
            seen = {}
            for kind, key, a in _anim_targets(args):
                seen.setdefault(key, set()).add(kind)
                if seen[key] == {"intro", "pulse"}:
                    yield node, f"{ast.unparse(a.args[0])[:40]} is introduced and pulsed in the same play"
                    seen[key].add("reported")


# ---- non-VMobjects (images, Groups) inside a VGroup ------------------------------------------------------------
_NONVM_CALLS = {"ImageMobject", "Group", "ImageMobjectFromCamera"}


def _is_nonvm(e, names, factories):
    if isinstance(e, ast.Call):
        if isinstance(e.func, ast.Name) and (e.func.id in _NONVM_CALLS or e.func.id in factories):
            return True
        if isinstance(e.func, ast.Attribute) and e.func.attr not in ("copy",) and _is_nonvm(e.func.value, names, factories):
            return True       # method chains (im.set_height(2).to_edge(UP)) return the image itself
        if isinstance(e.func, ast.Attribute) and e.func.attr == "copy":
            return _is_nonvm(e.func.value, names, factories)
        return False
    if isinstance(e, ast.Name):
        return e.id in names
    if isinstance(e, ast.Starred):
        return _is_nonvm(e.value, names, factories)
    if isinstance(e, (ast.ListComp, ast.GeneratorExp)):
        return _is_nonvm(e.elt, names, factories)
    if isinstance(e, (ast.List, ast.Tuple)):
        return any(_is_nonvm(x, names, factories) for x in e.elts)
    if isinstance(e, ast.IfExp):
        return _is_nonvm(e.body, names, factories) or _is_nonvm(e.orelse, names, factories)
    return False


def scope_walk(scope):
    """Nodes of one scope (a function, or the module's top level), not descending into nested defs."""
    todo = list(scope.body) if isinstance(scope, ast.Module) else list(ast.iter_child_nodes(scope))
    while todo:
        n = todo.pop()
        yield n
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            todo += list(ast.iter_child_nodes(n))


def _local_nonvm_names(fn, factories):
    """Names that hold a non-VMobject at every assignment in this scope (a name that is sometimes a VGroup is
    left alone, so the rule only fires when it is sure)."""
    assigns = {}
    for n in scope_walk(fn):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    assigns.setdefault(t.id, []).append(n.value)
        elif isinstance(n, (ast.For, ast.comprehension)) and isinstance(n.target, ast.Name):
            assigns.setdefault(n.target.id, []).append(None)
    names = set()
    for _ in range(3):                       # a few passes settle chains of assignments
        names = {k for k, vs in assigns.items() if all(v is not None and _is_nonvm(v, names, factories) for v in vs)}
    return names


@rule("vgroup-non-vmobject", "static", "error", "An ImageMobject or a Group (or a helper returning one) goes into "
      "a VGroup, which only holds VMobjects: TypeError at render.", "Part II, Reusing a figure",
      "use Group(...) for anything holding an image")
def vgroup_non_vmobject(s):
    funcs = [n for n in ast.walk(s.tree) if isinstance(n, (ast.FunctionDef, ast.Lambda))]
    factories = set(opt(s, "image_factories", []))
    for _ in range(4):                       # helpers that return images, to a fixed point
        for f in funcs:
            if isinstance(f, ast.FunctionDef) and f.name not in factories:
                names = _local_nonvm_names(f, factories)
                if any(isinstance(r, ast.Return) and r.value is not None and _is_nonvm(r.value, names, factories)
                       for r in scope_walk(f)):
                    factories.add(f.name)
    scopes = [n for n in ast.walk(s.tree) if isinstance(n, ast.FunctionDef)] + [s.tree]
    seen = set()
    for sc in scopes:
        names = _local_nonvm_names(sc, factories)
        vgroups = {t.id for n in scope_walk(sc) if isinstance(n, ast.Assign) and call_name(n.value) == "VGroup"
                   for t in n.targets if isinstance(t, ast.Name)}
        for n in scope_walk(sc):
            if id(n) in seen:
                continue
            if call_name(n) == "VGroup" and isinstance(n.func, ast.Name):
                bad = [a for a in n.args if _is_nonvm(a, names, factories)]
                if bad:
                    seen.add(id(n))
                    yield n, f"VGroup gets a non-VMobject: {ast.unparse(bad[0])[:40]}"
            if (call_name(n) == "add" and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
                    and n.func.value.id in vgroups and any(_is_nonvm(a, names, factories) for a in n.args)):
                seen.add(id(n))
                yield n, f"{n.func.value.id} is a VGroup and gets a non-VMobject"


# ---- names ------------------------------------------------------------------------------------------------------
def _manim_names():
    p = Path(__file__).with_name("manim_names.txt")
    return set(p.read_text().split()) if p.exists() else set()


@rule("shadows-manim", "static", "error", "A scene class, function or global is named after a manim export "
      "(Flash, Circle, Line...), so later uses get the wrong object.", "Part IV, Naming",
      "rename it (Flash -> UHDR)")
def shadows_manim(s):
    names = _manim_names() - set(opt(s, "allow_shadow", []))
    for st in s.tree.body:
        targets = []
        if isinstance(st, (ast.ClassDef, ast.FunctionDef)):
            targets = [st.name]
        elif isinstance(st, ast.Assign):
            targets = [t.id for t in st.targets if isinstance(t, ast.Name)]
        for t in targets:
            if t in names:
                yield st, f"'{t}' shadows manim.{t}"


# ---- narration and cues ----------------------------------------------------------------------------------------
@rule("bookmark-missing", "static", "error", "self.at('x') waits for a bookmark that is not in its voiceover text: "
      "manim-voiceover fails or the cue fires at the wrong time.", "Part II, Sync",
      "add <bookmark mark='x'/> to the narration or fix the name")
def bookmark_missing(s):
    for vo in s.voiceovers:
        if vo.text is None:
            continue
        for mark, node in vo.cues:
            if mark not in vo.marks:
                yield node, f"no <bookmark mark='{mark}'/> in this voiceover (has: {', '.join(vo.marks) or 'none'})"


@rule("bookmark-duplicate", "static", "error", "The same bookmark name appears twice in one narration.",
      "Part II, Sync", "rename one")
def bookmark_duplicate(s):
    for vo in s.voiceovers:
        dup = sorted({m for m in vo.marks if vo.marks.count(m) > 1})
        if dup:
            yield vo.node, f"duplicate bookmark(s): {', '.join(dup)}"


@rule("bookmark-order", "static", "error", "Cues run out of narration order, or one bookmark is waited for twice: "
      "the later wait returns at once, so its animation plays on the wrong words.", "Part II, Sync",
      "reorder the self.at calls to follow the text")
def bookmark_order(s):
    for vo in s.voiceovers:
        if vo.dynamic:
            continue
        last, lastm = -1, None
        for mark, node in vo.cues:
            if mark not in vo.marks:
                continue
            i = vo.marks.index(mark)
            if i < last:
                yield node, f"cue '{mark}' comes after '{lastm}' in code but before it in the narration"
            elif i == last:
                yield node, f"cue '{mark}' is waited for twice"
            last, lastm = max(last, i), mark


@rule("bookmark-unused", "static", "warn", "A bookmark in the narration has no cue, so nothing happens on that word.",
      "Part I §1, steer the eye", "add self.at('x', ...) or delete the bookmark")
def bookmark_unused(s):
    for vo in s.voiceovers:
        if vo.text is None or vo.dynamic:
            continue
        cued = {m for m, _ in vo.cues}
        unused = [m for m in vo.marks if m not in cued]
        if unused:
            yield vo.node, f"bookmark(s) never cued: {', '.join(unused)}"


@rule("narration-markup", "static", "error", "Narration holds markup that is not a well-formed bookmark, so the voice "
      "reads it aloud ('less than bookmark mark equals...').", "Part II, Sync",
      "write it as <bookmark mark='x'/>")
def narration_markup(s):
    for vo in s.voiceovers:
        if vo.text is None:
            continue
        rest = MARK.sub(" ", vo.text)
        m = re.search(r"[<>]|bookmark|mark\s*=", rest)
        if m:
            yield vo.node, f"stray markup near {rest[max(0, m.start() - 20):m.end() + 20]!r}"


def _sentences(text):
    t = MARK.sub("", text)
    return [x for x in re.split(r"(?<=[.!?])\s+", t.strip()) if len(x.split()) >= 3]


@rule("cue-density", "static", "warn", "A voiceover has fewer cues than the design asks for, so the eye is left "
      "alone while the voice talks.", "Part I §1, steer the eye",
      "add a bookmark + Indicate/Circumscribe on each noun the sentence names")
def cue_density(s):
    need = float(opt(s, "min_cues_per_sentence", 0.75))
    for vo in s.voiceovers:
        if vo.text is None or vo.dynamic:
            continue
        n = len(_sentences(vo.text))
        if n >= 2 and len(vo.cues) < need * n:
            yield vo.node, f"{len(vo.cues)} cue(s) for {n} sentences (want >= {need:g} per sentence)"


@rule("unresolved-narration", "static", "info", "A voiceover's text is computed, so the bookmark rules cannot read it.",
      "", "use a literal string (implicit concatenation is fine)")
def unresolved_narration(s):
    for vo in s.voiceovers:
        if vo.text is None:
            yield vo.node, "narration text is not a literal; bookmark checks skipped here"


# ---- on-screen text ----------------------------------------------------------------------------------------------
UNITS = {"mm", "cm", "nm", "um", "ns", "ps", "fs", "ms", "keV", "MeV", "GeV", "TeV", "eV", "Hz", "kHz", "MHz", "GHz",
         "Gy", "Bq", "kBq", "MBq", "min", "h", "s", "kg", "g", "MV", "kV", "W", "TW", "PW", "J", "mJ", "T", "u"}


def _words(tex):
    """Prose words: letters only, not maths, numbers or units (numbers on screen are encouraged)."""
    t = re.sub(r"\$[^$]*\$", " ", tex)
    t = re.sub(r"\\\\", " ", t)
    t = re.sub(r"\\[a-zA-Z]+\*?", " ", t)                      # commands
    t = re.sub(r"[{}~&]", " ", t)
    return [w for w in re.findall(r"[A-Za-z][A-Za-z'-]*", t) if w not in UNITS]


@rule("long-text", "static", "warn", "An on-screen Text/Tex holds a sentence. Text is a label or a bold number; "
      "the narration carries the argument.", "Part I §1, draw, don't write",
      "cut it to a label, or draw it as shapes")
def long_text(s):
    mx = int(opt(s, "max_words", 8))
    small = float(opt(s, "small_font", 18))
    for node in ast.walk(s.tree):
        if call_name(node) in ("Tex", "Text", "MarkupText", "Paragraph"):
            fs = next((k.value for k in node.keywords if k.arg == "font_size"), None)
            if isinstance(fs, ast.Constant) and isinstance(fs.value, (int, float)) and fs.value <= small:
                continue                                        # footnotes and credits
            parts = [s.resolve_str(a) for a in node.args]
            if any(p is None for p in parts) or not parts:
                continue
            w = _words(" ".join(parts))
            if len(w) > mx:
                yield node, f"{len(w)} words on screen: {' '.join(w)[:50]!r}"


# ---- render.sh -------------------------------------------------------------------------------------------------
@rule("scene-list", "static", "error", "render.sh SCENES and the scene classes in the script disagree: a missing "
      "scene is never rendered, an unknown one crashes the render.", "Part III, step 2",
      "make SCENES list every scene class once, in order")
def scene_list(s):
    listed = render_scenes(s.render_sh)
    if listed is None:
        return
    defined = [c.name for c in s.scenes]
    line = next((i for i, l in enumerate(s.render_sh.splitlines(), 1) if "SCENES=" in l), 1)
    for x in sorted(set(listed) - set(defined)):
        yield ("render.sh", line), f"render.sh lists '{x}' but the script defines no such scene"
    for x in [d for d in defined if d not in listed]:
        yield ("render.sh", line), f"scene '{x}' is defined but not in render.sh SCENES"
    dup = sorted({x for x in listed if listed.count(x) > 1})
    if dup:
        yield ("render.sh", line), f"listed twice: {', '.join(dup)}"


@rule("quality-cap", "static", "error", "Something asks for more than 1080p (-qp, -qk, production/fourk quality, "
      "pixel_height > 1080). The user wants 1080p at most.", "Part III, step 6", "use -qh (1080p60) or lower")
def quality_cap(s):
    for i, l in enumerate(s.render_sh.splitlines(), 1):
        if re.search(r"QUALITY\S*?[=:]-?[\"']?-q[pk]\b", l) or re.search(r"--resolution[ =]\S*?[,x](\d{4,})", l):
            yield ("render.sh", i), l.strip()
    for node in ast.walk(s.tree):
        if isinstance(node, ast.Constant) and node.value in ("production_quality", "fourk_quality"):
            yield node, f"quality {node.value}"
        if (isinstance(node, ast.Assign) and any(isinstance(t, ast.Attribute) and t.attr == "pixel_height" for t in node.targets)
                and isinstance(node.value, ast.Constant) and isinstance(node.value.value, int) and node.value.value > 1080):
            yield node, f"pixel_height = {node.value.value}"
