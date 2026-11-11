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
    told = set()                                  # Tex arguments already reported by the Tex check below
    for node in ast.walk(s.tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and _CTRL.search(node.value):
            yield node, f"control character in {node.value[:40]!r}"
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and re.search(r"\t(?:extbf|ext|imes|au|heta|ilde)", node.value) and id(node) not in told:
            # a tab where \textbf... was meant, in any string: a label helper (lab, credit) hides it from the Tex check
            yield node, f"tab where a LaTeX command was meant: {node.value[:40]!r}"
        if call_name(node) in TEX_CALLS | TEXT_CLASSES:
            for a in node.args:
                v = s.resolve_str(a)
                if v and re.search(r"\t[a-z]|\n(?:u|abla|eq|ot|i\b|ewline|ormalsize)", v):
                    yield a, f"tab or newline where a LaTeX command was meant: {v[:40]!r}"
                told.add(id(a))


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


@rule("narration-appendage", "static", "warn", "Narration tacks clauses on with a colon, semicolon or dash ('Then a "
      "live test: ECMWF's ...'), which reads as notes, not speech (user, subseasonal_pbc).", "Part II, Narration",
      "write full sentences: 'Then came a live test, ...', or split into two sentences")
def narration_appendage(s):
    for vo in s.voiceovers:
        if vo.text is None:
            continue
        t = MARK.sub("", vo.text)
        m = re.search(r"[:;—–]|\s-\s", t)
        if m:
            yield vo.node, f"{t[max(0, m.start() - 30):m.end() + 20]!r}"


def _sentences(text):
    t = MARK.sub("", text)
    return [x for x in re.split(r"(?<=[.!?])\s+", t.strip()) if len(x.split()) >= 3]


@rule("cue-gap", "static", "warn", "A long stretch of narration has no cue in it, so the picture holds still while "
      "the voice keeps talking. Cue density can be met on average and still leave a half-minute where nothing "
      "happens (user, lnp_comet: 'when something is said, it happens visually, synchronised').",
      "Part II, Sync: nothing is said for long over a still picture",
      "give every clause of the stretch its own bookmark and act on that word: draw the part being named, pulse it, "
      "move the dot along, put the number on the thing")
def cue_gap(s):
    """Spoken words between one cue and the next. Roughly 2.6 words a second, so 24 words is about nine seconds."""
    lim = int(opt(s, "max_words_per_cue", 24))
    for vo in s.voiceovers:
        if vo.text is None or vo.dynamic:
            continue
        cued = {m for m, _ in vo.cues}
        parts = MARK.split(vo.text)                              # text, mark, text, mark, ..., text
        runs, run, seg = [], parts[0], 0
        for k in range(1, len(parts), 2):
            if parts[k] in cued:
                runs.append(run)
                run = ""
                seg += 1
            run += parts[k + 1]
        runs.append(run)
        worst = max(runs, key=lambda r: len(r.split()))
        n = len(worst.split())
        if n > lim:
            where = "before the first cue" if runs.index(worst) == 0 and seg else \
                    ("after the last cue" if runs.index(worst) == len(runs) - 1 and seg else
                     ("uncued" if not seg else "between cues"))
            w = worst.split()
            yield vo.node, f"{n} words with no cue ({where}, want <= {lim}): " \
                           f"{' '.join(w[:6])} ... {' '.join(w[-6:])}"


PROPERTY_WORDS = ["width", "wide", "widen", "narrow", "edge", "sharp", "blur", "smear", "resolution", "fwhm",
                  "spread", "tail", "gap", "thick", "diameter", "radius", "distance", "contrast", "size", "depth",
                  "slope", "peak", "angle", "offset", "length", "ratio"]
_WORD = re.compile(r"<bookmark\s+mark\s*=\s*['\"][^'\"]+['\"]\s*/>|[A-Za-z][A-Za-z'-]*")


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


_CREDIT = re.compile(r"et al|arXiv:|\bCC BY\b|\bdoi\b|\bPMB\b|\bNat\.|\bPhys\.", re.I)


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
            if _CREDIT.search(" ".join(parts)):
                continue    # a citation is a credit however it is sized: all ten exemptions written for this
                            # rule were one, and a credit is long because a credit names its authors
            w = _words(" ".join(parts))
            if len(w) > mx:
                yield node, f"{len(w)} words on screen: {' '.join(w)[:50]!r}"


@rule("redraw-plot", "static", "warn", "An always_redraw rebuilds a smoothed function plot (ax.plot / plot_line_graph) "
      "every frame. A narrow peak or a sharp edge is sampled at a different height each frame and the Bezier smoothing "
      "overshoots, so the curve flickers while it moves.", "Part II, Motion",
      "build the curve as a polyline: VMobject().set_points_as_corners(points), with dense samples around the sharp part")
def redraw_plot(s):
    for node in ast.walk(s.tree):
        if call_name(node) == "always_redraw":
            for sub in ast.walk(node):
                if sub is not node and isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr in ("plot", "plot_line_graph"):
                    yield sub, f"always_redraw(... .{sub.func.attr}(...)) redraws a smoothed plot each frame"
                    break


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


@rule("gx-tex", "static", "error", "A Tex string ManimGX's Typst/mitex cannot set (common_gx maps the text macros "
      "it can): two maths runs touching ($a$$b$) crash the render, \\$ prints the word 'dollar', and a text "
      "starting with '+ ', '- ' or '1. ' is Typst list markup ('+ PBC' was set as '1. PBC', subseasonal_pbc) and "
      "one starting with '= ' is a heading, whose sign is dropped ('= channel' was set as 'channel', g4_tutorial).",
      "Part IV, ManimGX", "join the maths into one $...$; write 'USD' or a word; start a label with a word")
def gx_tex(s):
    # a script's own label helpers (def lab(t, ...): return Tex(t, ...)) pass their first argument straight to Tex
    wrappers = {"Tex"}
    for fn in ast.walk(s.tree):
        if isinstance(fn, ast.FunctionDef) and fn.args.args:
            p = fn.args.args[0].arg
            if any(call_name(n) == "Tex" and n.args and isinstance(n.args[0], ast.Name) and n.args[0].id == p
                   for n in ast.walk(fn)):
                wrappers.add(fn.name)
    for node in ast.walk(s.tree):
        name = call_name(node)
        if name in wrappers:
            for i, a in enumerate(node.args if name == "Tex" else node.args[:1]):
                v = s.resolve_str(a)
                if not v:
                    continue
                if re.search(r"(?<!\\)\$\$", v):
                    yield a, f"two maths runs touch: {v[:40]!r}"
                if re.search(r"(?<!\\)\\\$", v):
                    yield a, f"\\$ is set as the word 'dollar': {v[:40]!r}"
                if i == 0 and re.match(r"\s*([+\-]|\d+\.)\s", v):
                    yield a, f"set as a Typst list item: {v[:40]!r}"
                if i == 0 and re.match(r"\s*=+\s", v):
                    yield a, f"a leading '= ' is a Typst heading mark and is dropped (write $=$): {v[:40]!r}"


@rule("fixed-frame-early", "static", "error", "add_fixed_in_frame_mobjects(x) puts x on screen at once, so a later "
      "FadeIn/Write/Create of x plays over a frame where it is already shown (Neck3D's formula sat there before "
      "its cue).", "Part IV, 3D scenes", "self.remove(x) right after add_fixed_in_frame_mobjects(x), then introduce it")
def fixed_frame_early(s):
    for fn in ast.walk(s.tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        calls = sorted((n for n in ast.walk(fn) if isinstance(n, ast.Call)), key=lambda n: (n.lineno, n.col_offset))
        shown = {}                                  # fixed, not removed: key -> [the fixing call, time has passed]
        for c in calls:
            f = c.func
            meth = f.attr if isinstance(f, ast.Attribute) else None
            keys = [ast.dump(a.value if isinstance(a, ast.Starred) else a) for a in c.args]
            if meth == "add_fixed_in_frame_mobjects":
                for k in keys:
                    shown[k] = [c, False]
            elif meth == "remove":
                for k in keys:
                    shown.pop(k, None)
            elif meth in ("play", "wait", "at", "wait_until_bookmark", "move_camera"):
                # an intro in the very next play starts from nothing, so no frame shows it early
                for n in ast.walk(c):
                    if call_name(n) in INTRO and n.args and ast.dump(n.args[0]) in shown:
                        add, late = shown.pop(ast.dump(n.args[0]))
                        if late:
                            yield n, f"{call_name(n)}({ast.get_source_segment(s.text, n.args[0])}) after it was " \
                                     f"fixed in frame (line {add.lineno}) and shown during the wait in between"
                for v in shown.values():
                    v[1] = True


ALGEBRA = re.compile(r"\b(substitut\w*|plug(?:s|ging)? (?:it|this|that|them|in)|rearrang\w*|re-arrang\w*|"
                     r"factor(?:s|ing|ise|ize|ised|ized|ed)? (?:out|it|this|that)|factori[sz]\w*|pull(?:s|ing)? out|"
                     r"cancel(?:s|led|ling)? (?:out|each)|expand(?:s|ing|ed)? (?:it|this|that|the bracket|out)|"
                     r"simplif\w*|both sides|solve (?:it )?for|collect(?:ing)? (?:the )?terms|"
                     r"take the (?:log|logarithm) of)",
                     re.I)
MOVES = {"TransformMatchingTex", "TransformMatchingShapes", "TransformFromCopy", "ReplacementTransform", "Transform",
         "FadeTransform", "FadeTransformPieces"}


@rule("algebra-shown", "static", "warn", "The narration manipulates a formula (substitutes, rearranges, factors, "
      "cancels, expands...) but the block moves no term on screen, so the step is told, not shown.",
      "Part I §2, show the algebra move by move", "map the parts: TransformFromCopy the substituted term into its slot, "
      "TransformMatchingTex/Shapes for a rearrangement, light the common factor then pull it out, Cross what cancels")
def algebra_shown(s):
    for vo in s.voiceovers:
        if vo.text is None:
            continue
        said = sorted({m.group(0).lower() for m in ALGEBRA.finditer(vo.text)})
        if said and not any(call_name(n) in MOVES | {"Cross"} for n in ast.walk(vo.node)):
            yield vo.node, f"says {', '.join(repr(w) for w in said)} but no term moves (no Transform/Cross in the block)"


ORDER = re.compile(r"\b(?:previous|next|last|earlier|later|following|coming|upcoming|preceding)\s+(?:video|episode|part)s?\b|"
                   r"\bvideo (?:before|after) (?:this|that)\b", re.I)


@rule("watch-order", "static", "warn", "The narration points at the previous or next video, but the videos have no "
      "watch order (the catalogue, the reels feed and the playlists all shuffle or skip), so the pointer is wrong "
      "for most viewers.", "Narration, no watch order", "name the other paper instead, or say it 'has a video of "
      "its own' / 'is covered in another video'")
def watch_order(s):
    for vo in s.voiceovers:
        if vo.text is None:
            continue
        said = sorted({m.group(0).lower() for m in ORDER.finditer(vo.text)})
        if said:
            yield vo.node, f"says {', '.join(repr(w) for w in said)}"


ACRONYM = re.compile(r"(?<![\w'])[A-Z]{2,}(?![\w'])")
SAID_AS_WORD = {"PET", "MAP", "NASA", "LASER", "RADAR", "SONAR", "CERN", "SPECT", "LIGO", "COVID", "AIDS", "OK",   # said as words
                "GATE", "EXPLORER", "PRISM", "LYSO", "GAGG", "POPOP", "MAMMI", "FLUKA", "FLASH", "INSERT", "AUTOMAP",
                "ADAM", "BOLD", "STIR", "POET", "NEMA", "CAT", "DRAMA", "COMET", "LANCE", "DOPE"}


@rule("acronym-unspelled", "static", "warn", "An acronym is written in capitals in the narration, so the voice reads it as "
      "a word: 'EM' came out as 'em' and 'MR' as 'mister' (user, pet_fbsem).", "Narration, spell out what must be "
      "said", "write it letter by letter, 'E M', 'M R', 'O S E M'; leave as a word only the ones said as words "
      "(PET, MAP: SAID_AS_WORD)")
def acronym_unspelled(s):
    for vo in s.voiceovers:
        if vo.text is None:
            continue
        said = sorted({w for w in ACRONYM.findall(re.sub(r"<bookmark[^>]*/>", "", vo.text)) if w not in SAID_AS_WORD})
        if said:
            yield vo.node, f"says {', '.join(said)} as written"


SPACED = re.compile(r"(?<![\w\.])[A-Z](?: [A-Z]){1,}(?![\w-])")      # not "2.5D U-Net"


@rule("acronym-spaced-on-screen", "static", "warn", "On-screen text spells an acronym letter by letter ('M R I'). "
      "The spacing is only for the voice; the screen reads like the paper (user, pet_diffusion: 'the letters may "
      "need to be seperated for the pronounciation but not in the videos text').", "Narration, spell out what must "
      "be said", "write it closed up on screen, 'MRI', 'DDIM'; keep 'M R I' only inside the voiceover text")
def acronym_spaced_on_screen(s):
    for node in ast.walk(s.tree):
        if not isinstance(node, ast.Call) or call_name(node) == "voiceover":
            continue
        for a in list(node.args) + [k.value for k in node.keywords]:
            for c in ast.walk(a):                         # strings in lists of labels and f-strings too
                if isinstance(c, ast.Constant) and isinstance(c.value, str):
                    t = re.sub(r"\$[^$]*\$", " ", c.value)
                    hit = SPACED.search(t)
                    if hit and not set(hit.group(0)) <= set("ABCDEFG "):   # note names, "E A D G B E"
                        yield node, f"shows {hit.group(0)!r}"


@rule("pointer-white-on-page", "static", "warn", "A pointer box on a lifted figure is white. Paper figures sit on "
      "white, so the box vanishes (user, pet_dl_recon: 'white bounding box on white image - not a good idea').",
      "Reusing a figure", "give it a colour that shows on white and means something (the method's colour, BAD_C, "
      "TEAL_L)")
def pointer_white_on_page(s):
    for node in ast.walk(s.tree):
        if call_name(node) != "point" or len(node.args) < 2:
            continue
        on_fig = any(call_name(c) in ("spot", "sp") for c in ast.walk(node.args[1]))
        col = node.args[2] if len(node.args) > 2 else next((k.value for k in node.keywords if k.arg == "color"), None)
        if on_fig and isinstance(col, ast.Name) and col.id in ("WHITE", "GREY_A", "MARK_C", "YELLOW"):
            yield node, f"{col.id} box on a figure"


REMOVERS = {"FadeOut", "Uncreate", "Unwrite", "ShrinkToCenter", "Remove"}


def _base(n):
    """'lad' for lad[2][0].get_center()."""
    while isinstance(n, (ast.Subscript, ast.Attribute)):
        n = n.value
    return n.id if isinstance(n, ast.Name) else None


def _targets(expr, out):
    """Base names of the mobjects an animation expression acts on. A callee is not a target (the FadeIn in
    FadeIn(p) is not a picture), and neither is anything being removed: a group faded out at the end of its
    block was not carried into the next one."""
    if call_name(expr) in REMOVERS:
        return
    if isinstance(expr, ast.Call):
        for a in [*expr.args, *(k.value for k in expr.keywords)]:
            _targets(a, out)
        if isinstance(expr.func, ast.Attribute):            # p.animate.shift(...), pie.get_center()
            b = _base(expr.func)
            if b:
                out.add(b)
        return
    if isinstance(expr, (ast.Name, ast.Subscript, ast.Attribute)):
        b = _base(expr)
        if b:
            out.add(b)
        return
    for ch in ast.iter_child_nodes(expr):
        _targets(ch, out)


def _acted(block, helpers=()):
    """Pictures this narration block animates, by name. `helpers` names the script's own cue helpers (a page
    walk's self.hl / self.turn), which take animations to play alongside their own work: a figure handed to one
    of those is animated just as surely as one handed to self.at, and not counting them made a scene that does
    its work through the format's helpers look like a scene with no central figure."""
    out = set()

    def visit(n):
        for ch in ast.iter_child_nodes(n):
            if isinstance(ch, ast.With) and any(call_name(i.context_expr) == "voiceover" for i in ch.items):
                continue
            if call_name(ch) in ("at", "play") or call_name(ch) in helpers:
                for a in ch.args:
                    _targets(a, out)
            visit(ch)
    visit(block)
    return {n for n in out if n != "self" and not n.isupper()}


def _blocks(s, cls):
    return [vo.node for vo in s.voiceovers if cls.lineno <= vo.node.lineno <= cls.end_lineno]


# Verbs for something done to a thing that is already on screen. Verbs of coming into being (form, grow,
# appear, flow) are left out on purpose: there an introducing animation is the event. So are words that are
# usually nouns here (a stack of blocks, a drop of liquid, a split).
_ACTS_ON = re.compile(
    r"\b(?:reach(?:es|ed)?|enter(?:s|ed)?|unload(?:s|ed)?|releas(?:e|es|ed)|open(?:s|ed)|break(?:s)?|broke|"
    r"burst(?:s)?|fus(?:e|es|ed)|dissolv(?:e|es|ed)|travel(?:s|led)?|mov(?:e|es|ed)|slid(?:e|es)|"
    r"swap(?:s|ped)?|shuffl(?:e|es|ed)|scrambl(?:e|es|ed)|swing(?:s)?|swung|escap(?:e|es|ed)|"
    r"merg(?:e|es|ed)|collaps(?:e|es|ed)|widen(?:s|ed)|narrow(?:s|ed)|rotat(?:e|es|ed)|scatter(?:s|ed)?)\b",
    re.I)
# "reaches zero point seven eight" is a value being hit, not a thing crossing a room; "dissolved in alcohol"
# describes what something already is
_NOT_EVENT = re.compile(r"\s+(?:in\b|zero|one|two|three|four|five|six|seven|eight|nine|ten|\d|at most|at least|up to|"
                        r"about|nearly|roughly|almost|twice|half|further|farther|as far)", re.I)
# a cue that only brings things on: the clause names something new arriving ("a positron released at the centre",
# "the sensor and the clock enter"), which is what an introduction shows (pet_g4_configs: four such warnings)
_INTRO = {"FadeIn", "Create", "Write", "GrowFromCenter", "GrowFromPoint", "DrawBorderThenFill", "SpinInFromNothing",
          "FadeInFromPoint", "LaggedStart", "AnimationGroup", "Succession"}


def _fresh(s, node):
    """Whether every animation in the cue introduces, and nothing it introduces was animated earlier in its
    scene: then it is the arrival of a new thing, not a pulse on one already there."""
    calls = [n for n in ast.walk(node) if isinstance(n, ast.Call) and call_name(n)]
    if not calls or any(call_name(n)[:1].isupper() and call_name(n) not in _INTRO for n in calls) or \
            any(isinstance(n, ast.Attribute) and n.attr == "animate" for n in ast.walk(node)):
        return False
    names = {a.id for n in calls if call_name(n) in _INTRO for x in n.args for a in ast.walk(x) if isinstance(a, ast.Name)}
    cls = next((c for c in s.scenes if c.lineno <= node.lineno <= c.end_lineno), None)
    if cls is None or not names:
        return False
    for n in ast.walk(cls):
        if isinstance(n, ast.Call) and call_name(n) in ("play", "at") and n.lineno < node.lineno:
            if names & {a.id for a in ast.walk(n) if isinstance(a, ast.Name)}:
                return False
    return True

# animations that change something already on screen, as opposed to bringing it on or pulsing it
CHANGE = {"animate", "Transform", "ReplacementTransform", "TransformMatchingShapes", "TransformMatchingTex",
          "MoveAlongPath", "Rotate", "Rotating", "Restore", "MoveToTarget", "ApplyFunction", "ApplyMatrix",
          "ApplyMethod", "Swap", "CyclicReplace", "ScaleInPlace", "ShrinkToCenter", "ChangeSpeed"}


def _anim_calls(node):
    """The animation calls in a cue: 'FadeIn' for FadeIn(x), 'animate' for m.animate.shift(...).
    None (a cue helper the script does not define) has none."""
    out = []
    if node is None:
        return out
    for n in ast.walk(node):
        nm = call_name(n)
        if nm and nm[:1].isupper():
            out.append(nm)
        if isinstance(n, ast.Attribute) and n.attr == "animate":
            out.append("animate")
    return out


@rule("pulse-for-event", "static", "warn", "The narration says something is done to a thing that is already on "
      "screen, and the cue on that clause does not touch it: it pulses it, or raises a fresh arrow and a fresh "
      "box beside it. A pulse says 'this', never 'this happens' (user, lnp_comet Intro: 'instead of an arrow the "
      "lipid nanoparticle should've gone into the cell, dissolved or whatever it does, and the mRNA released as "
      "the narration says'). Only cue a thing when the narration gives the cue a purpose.",
      "Part I §1, animate the event, not a pulse on its picture",
      "animate what the clause describes, on the object the viewer is already holding: move it there, open it, "
      "let a part of it come away, change what it is made of. Keep Indicate for naming a thing again")
def pulse_for_event(s):
    for vo in s.voiceovers:
        if vo.text is None or vo.dynamic:
            continue
        parts = MARK.split(vo.text)                       # text, mark, text, mark, ..., text
        after = {}
        for k in range(1, len(parts), 2):
            after.setdefault(parts[k], parts[k + 1])
        for mark, node in vo.cues:
            clause = after.get(mark)
            if not clause:
                continue
            hit = _ACTS_ON.search(clause)
            if not hit or _NOT_EVENT.match(clause[hit.end():hit.end() + 12]):
                continue
            calls = _anim_calls(node)
            if calls and not any(c in CHANGE for c in calls) and not _fresh(s, node):
                words = " ".join(clause.split()[:9])
                yield node, f"the voice says {hit.group(0)!r} but nothing on screen is moved or changed: " \
                             f"{words!r} ({'/'.join(sorted(set(calls)))})"

@rule("scene-protagonist", "static", "warn", "The scene has no central figure. Its narration blocks each build a "
      "picture of their own and drop it, so nothing is on screen long enough to be transformed, and the viewer "
      "starts again at every block instead of watching one thing change (user, lnp_comet: 'have a central figure of "
      "interest which constitutes the focus of the scene's content, and focus on mutating, transforming, "
      "interacting with ... that central visualisation').",
      "Part I §1, one central figure, mutated",
      "pick the thing the scene is about and draw it once: the particle, the membrane, the input bundle, the "
      "detector. Every block then does something to that object (a piece taken out of it, a knob moved on it, a "
      "part lit, a number put on it) instead of introducing a fresh panel. Graphs and metrics may sit alongside it")
def scene_protagonist(s):
    """Calibrated over the 255 scenes in this repo: the median scene's busiest picture covers half its blocks,
    a scene built around one figure covers three quarters."""
    from .plan import load as load_plan

    want = float(opt(s, "protagonist_blocks", 0.6))
    least = int(opt(s, "protagonist_min_blocks", 3))
    plan = load_plan(s.path.parent)
    for cls in s.scenes:
        blocks = _blocks(s, cls)
        if len(blocks) < least:
            continue                                        # a two-block scene is allowed one picture per block
        acts = [_acted(b, s.cue_helpers) for b in blocks]
        seen = {}
        for a in acts:
            for nm in a:
                seen[nm] = seen.get(nm, 0) + 1
        if not seen:
            continue
        # With a staging plan there is no guessing: the scene declared its figure, so that is the one measured.
        st = plan.scenes.get(cls.name) if plan else None
        declared = st.entity if st and st.entity in seen else ""
        best = declared or max(seen, key=lambda nm: seen[nm])
        need = max(2, -(-int(want * len(blocks) * 100) // 100))      # ceil: 0.6 of four blocks is three
        if seen[best] >= need:
            continue
        once = sorted(nm for nm, c in seen.items() if c == 1)
        yield cls, ((f"the declared focus ({best}) is acted on in {seen[best]} of " if declared else
                     f"no central figure: the most used picture ({best}) is acted on in {seen[best]} of ")
                    + f"{len(blocks)} narration blocks (want {need}); "
                    f"{len(once)} pictures are used in one block only"
                    + (f": {', '.join(once[:8])}" if once else ""))


@rule("equation-talked-over", "static", "warn", "A multi-part equation is written whole inside a voiceover and none "
      "of its parts is cued in that block, so the voice reads its terms while the eye hunts for them.",
      "Part I §1, appear as it is named (equations)", "write it part by part on the words that name them, or keep "
      "the term marker on each term as it is read: point(self, eq[k])")
def equation_talked_over(s):
    for cls in s.scenes:
        eqs = {}                                    # name -> number of parts, for MathTex(a, b, c, ...) in this scene
        for n in ast.walk(cls):
            if (isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                    and call_name(n.value) == "MathTex" and not any(isinstance(a, ast.Starred) for a in n.value.args)
                    and len(n.value.args) >= 3):
                eqs[n.targets[0].id] = len(n.value.args)
        if not eqs:
            continue
        for vo in s.voiceovers:
            if not cls.lineno <= vo.node.lineno <= cls.end_lineno:
                continue
            nodes = list(ast.walk(vo.node))
            cued = {n.value.id for n in nodes if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name)}
            for n in nodes:
                if (call_name(n) in INTRO and n.args and isinstance(n.args[0], ast.Name) and n.args[0].id in eqs
                        and n.args[0].id not in cued):
                    yield n, (f"{n.args[0].id} ({eqs[n.args[0].id]} parts) is written whole and none of its parts is "
                              "cued while the voice reads it")


_AUTHORS = re.compile(r"\b(authors?|led by|colleagues|team|group)\b", re.I)
_PERSON = re.compile(r"\b[A-Z][a-z]+(?: [A-Z][a-z]+)* [A-Z][a-z]+\b")


@rule("authors-brief", "static", "warn", "The opening narration spends a long sentence on the authors (a list of names, "
      "their institutions) before the video says anything about the work (user, pet_recon_free: 'no need to speak "
      "about the authors for too long').", "Part I §1, opening",
      "one short clause: the first author or the group, and the journal; the front page shows the full list")
def authors_brief(s):
    first = next((c for c in s.tree.body if isinstance(c, ast.ClassDef)
                  and any(getattr(b, "id", None) == "Narrated" for b in c.bases)), None)
    if first is None:
        return
    most = int(opt(s, "author_sentence_words", 20))
    for vo in s.voiceovers:
        if vo.text is None or not first.lineno <= vo.node.lineno <= first.end_lineno:
            continue
        for sen in _sentences(vo.text):
            if not _AUTHORS.search(sen):
                continue
            n, names = len(sen.split()), len(_PERSON.findall(sen))
            if n > most or names >= 3:
                yield vo.node, f"{n} words and {names} names on the authors: {sen[:70]!r}"
                break


@rule("front-page", "static", "warn", "The video credits a paper (an 'et al.' citation) but never shows the paper's "
      "front page, so a viewer who knows the paper cannot recognise it (user, pet_explorer).", "Part I §1, opening",
      "tools/front_page.sh <video> writes assets/front.png; show front_page() in the first scene while the voice names "
      "the paper, its authors and its journal")
def front_page_shown(s):
    if any(call_name(n) == "front_page" for n in ast.walk(s.tree)):
        return
    # A front page needs a paper to be the front page of. Every one of the nine hand-written exemptions for
    # this rule said the same thing -- a topic or programme video over many papers, or no PDF in the folder to
    # draw a page from -- so ask the folder instead of asking the author.
    if len(list((s.path.parent / "src").glob("*.pdf"))) != 1:
        return
    for node in ast.walk(s.tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and re.search(r"\bet al\b", node.value):
            yield node, "cites a paper but never shows its front page (front_page())"
            return


# ManimGX's animations are not Manim CE's: the setters CE grew for fluent chaining are simply absent, so a call
# that renders under the checker (CE) raises AttributeError under the renderer (GX) partway through a scene.
GX_MISSING = {"set_run_time": "pass run_time= to the animation instead",
              "set_rate_func": "pass rate_func= to the animation instead",
              "set_name": "drop it; ManimGX animations have no name setter"}


@rule("gx-anim-setter", "static", "error", "An animation setter that exists in Manim CE but not in ManimGX "
      "(set_run_time, set_rate_func, set_name). The checks run under CE, so this passes every static and "
      "runtime check and then fails the GX render with AttributeError, after the other scenes have rendered "
      "(mc_recon Hardware: `turn(LC0).set_run_time(0.6)` inside a Succession).",
      "Part IV, ManimGX",
      "give the animation the value in its constructor (run_time=, rate_func=); for an .animate chain, wrap it "
      "in AnimationGroup(..., run_time=...)")
def gx_anim_setter(s):
    for node in ast.walk(s.tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in GX_MISSING:
            yield node, f"{node.func.attr}() does not exist in ManimGX: {GX_MISSING[node.func.attr]}"


# A morph is one object on screen becoming another. It is fine when the target is a rebuild of the same thing at
# new values (Transform(bar, sbar(10)), the bar that is now shorter) and confusing when it is a second object the
# scene built for itself, because the viewer was following both and one of them has just eaten the other.
MORPH = {"Transform", "ReplacementTransform", "TransformMatchingShapes", "TransformMatchingTex",
         "TransformFromCopy", "FadeTransform", "FadeTransformPieces"}


def _src(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "?"


def _makers(cls):
    """What built each of a scene's variables: `lors = VGroup(...)` -> 'VGroup', `grad = arm(...)` -> 'arm'.
    A name assigned by two different builders, or by anything that is not a call, is left out: the question
    these makers answer is only whether two objects are the same kind of thing, and a guess is worse than a
    shrug. `bars()` twice is one kind -- the second bars is the first one at new values, which is the whole
    point of a Transform -- so only a different maker is a different thing."""
    rhs = {}
    for n in ast.walk(cls):
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
            name = n.targets[0].id
            if name in rhs and _src(rhs[name]) != _src(n.value):
                rhs[name] = None                   # built two ways: no answer
            elif name not in rhs:
                rhs[name] = n.value
    out = {}

    def kind(expr, seen=()):
        """The builder at the bottom of an expression: `loop.copy().shift(x)` is whatever built `loop`, since
        moving a thing or copying it does not make it a different thing."""
        if isinstance(expr, ast.Call):
            return call_name(expr) if isinstance(expr.func, ast.Name) else kind(expr.func.value, seen)
        if isinstance(expr, ast.Name) and expr.id not in seen:
            return kind(rhs.get(expr.id), seen + (expr.id,))
        return None

    for name, expr in rhs.items():
        k = kind(expr, (name,))
        if k:
            out[name] = k
    return out


@rule("object-morph", "static", "warn", "One object the scene built turns into another object the scene built. The "
      "viewer has been tracking both, and a thing that becomes a different thing is a thing they stop tracking: the "
      "detector they were following is now an arrow, and nothing on screen is what it was a moment ago (user, "
      "mc_recon: 'some entities just straight up turn into different ones (e.g. a detector turns into an arrow) "
      "which is confusing to track, try to have some object permanence'). Transforming a thing into a fresh build "
      "of itself is not this: that is the same object at new values.",
      "Part I §1, one central figure, mutated",
      "keep the object and change it (move it, reshape it, recolour it, let a part come away), or fade the old one "
      "out and bring the new one on so it reads as a replacement rather than a metamorphosis. Where the "
      "metamorphosis is the point, stage the cue as `morph:` in plan.md and say in the why what it shows")
def object_morph(s):
    from .plan import load as load_plan
    plan = load_plan(s.path.parent)
    for cls in s.scenes:
        st = plan.scenes.get(cls.name) if plan else None
        makers = _makers(cls)
        staged = {mk for b in (st.blocks if st else []) for mk, (_l, a, _w) in b.actions.items()
                  if a.lower().startswith("morph:")}
        allowed = set()
        for vo in s.voiceovers:
            if cls.lineno <= vo.node.lineno <= cls.end_lineno:
                for mark, node in vo.cues:
                    if mark in staged:
                        allowed |= {id(n) for n in ast.walk(node)}
        for n in ast.walk(cls):
            if call_name(n) not in MORPH or len(getattr(n, "args", [])) < 2 or id(n) in allowed:
                continue
            src, dst = n.args[0], n.args[1]
            if not isinstance(src, ast.Name) or not isinstance(dst, ast.Name) or src.id == dst.id:
                continue                           # a part (sh[3]) or a fresh build: neither says what kind
            a, b = makers.get(src.id), makers.get(dst.id)
            if not a or not b or a == b:
                continue                           # one kind of thing becoming the same kind is a change of state
            yield n, f"`{src.id}` ({a}) turns into `{dst.id}` ({b}), a different kind of object"


# a clause about one of these is about a piece of the thing, not the whole of it. Kept to words that are a part
# of something in any sentence: "the far wall" and "the other side" are places, not parts, and a list that
# reaches for them flags a ball crossing a room (the beam `wall` in tests/static_bad).
PART_WORDS = ["kind", "type", "part", "piece", "component", "layer", "half", "corner", "term", "bin"]


@rule("property-scope", "static", "warn", "The narration names a property or a part of a thing, and the cue pulses "
      "the whole thing. The eye is sent to the object when the words were about its width, its tail, its fourth "
      "kind of lipid -- so the viewer is told 'this' at the moment they needed 'this bit of it' (user, mc_recon: "
      "'if mentioning a property of a thing try to only cue that property (or something indicative of that "
      "property) rather than the whole thing in question').",
      "Part I §1, steer the eye (a size)",
      "pulse the part (`sh[3]`, the edge, the one bar), or draw the property itself: a width arrow across it, a "
      "dimension line, a profile beside it. A pulse on the whole object is for naming the whole object")
def property_scope(s):
    words = [w.lower() for w in opt(s, "property_words", PROPERTY_WORDS)] + PART_WORDS
    for vo in s.voiceovers:
        if vo.text is None or vo.dynamic:
            continue
        parts = MARK.split(vo.text)
        after = {}
        for k in range(1, len(parts), 2):
            after.setdefault(parts[k], parts[k + 1])
        for mark, node in vo.cues:
            head = " ".join((after.get(mark) or "").split()[:8]).lower()
            hit = next((w for w in words if any(t.startswith(w) for t in head.split())), None)
            if not hit:
                continue
            calls = _anim_calls(node)
            if not calls or any(c not in EMPHASIS for c in calls):
                continue                                  # only a bare pulse is too wide; a change is the property
            if any(isinstance(n, ast.Subscript) for n in ast.walk(node)):
                continue                                  # the cue already picks a part out
            whole = sorted({n.id for n in ast.walk(node) if isinstance(n, ast.Name)
                            and n.id[:1].islower() and n.id != "self"})
            if any(w.startswith(hit[:5]) or hit.startswith(w) for w in whole):
                continue                                  # the object pulsed is the property (`tail`, `thick`)
            yield node, f"the voice says {hit!r} and the cue pulses the whole of {', '.join(whole) or 'it'}"
