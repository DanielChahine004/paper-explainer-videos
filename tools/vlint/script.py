"""What static rules see: one parsed scene script plus its render.sh, with the narration blocks pre-extracted."""
import ast
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path

from .core import Suppressions

MARK = re.compile(r"<bookmark\s+mark\s*=\s*['\"]([^'\"]+)['\"]\s*/>")
EMPHASIS = {"Indicate", "Circumscribe", "Flash", "Wiggle", "ApplyWave", "FocusOn", "ShowPassingFlash", "Blink"}
INTRO = {"FadeIn", "Create", "Write", "DrawBorderThenFill", "GrowFromCenter", "GrowFromPoint", "GrowFromEdge",
         "GrowArrow", "SpinInFromNothing", "AddTextLetterByLetter", "AddTextWordByWord", "ShowIncreasingSubsets",
         "FadeInFromPoint", "FadeInFromLarge"}
TEXT_CLASSES = {"Text", "MarkupText", "Tex", "MathTex", "Paragraph", "Title", "BulletedList"}


def call_name(node):
    """'FadeIn' for FadeIn(x), 'at' for self.at(...), None for anything else."""
    if isinstance(node, ast.Call):
        f = node.func
        if isinstance(f, ast.Name):
            return f.id
        if isinstance(f, ast.Attribute):
            return f.attr
    return None


@dataclass
class Voiceover:
    node: ast.With
    text: str | None          # None when the text is not a literal we can resolve
    marks: list               # bookmark names in order of appearance
    cues: list = field(default_factory=list)   # (mark, call node) for self.at / wait_until_bookmark, in order
    dynamic: bool = False                       # some cue's mark is computed (a loop), so cue lists are partial


@dataclass
class Script:
    path: Path
    text: str
    lines: list
    tree: ast.Module
    config: object
    sup: Suppressions
    render_sh: str = ""
    scenes: list = field(default_factory=list)       # ClassDef nodes with a construct() method
    voiceovers: list = field(default_factory=list)
    constants: dict = field(default_factory=dict)    # module-level NAME = "literal"
    syntax_warnings: list = field(default_factory=list)

    def resolve_str(self, node):
        """Value of a string literal, an implicit/explicit concatenation of literals, or a module-level str
        constant; None if it depends on anything computed."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            a, b = self.resolve_str(node.left), self.resolve_str(node.right)
            return a + b if a is not None and b is not None else None
        if isinstance(node, ast.Name):
            return self.constants.get(node.id)
        return None


def load_script(path, config):
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        tree = ast.parse(text, filename=str(path))
        compile(tree, str(path), "exec")
    s = Script(path, text, text.splitlines(), tree, config, Suppressions(text.splitlines()))
    s.syntax_warnings = [(getattr(w, "lineno", 0) or 0, str(w.message)) for w in caught]
    rsh = path.parent / "render.sh"
    s.render_sh = rsh.read_text(encoding="utf-8") if rsh.exists() else ""
    for st in tree.body:
        if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
            v = s.resolve_str(st.value)
            if v is not None:
                s.constants[st.targets[0].id] = v
        if isinstance(st, ast.ClassDef) and any(isinstance(b, ast.FunctionDef) and b.name == "construct" for b in st.body):
            s.scenes.append(st)
    helpers = _cue_helpers(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.With):
            for item in node.items:
                c = item.context_expr
                if call_name(c) == "voiceover":
                    tnode = next((k.value for k in c.keywords if k.arg == "text"), c.args[0] if c.args else None)
                    t = s.resolve_str(tnode) if tnode is not None else None
                    vo = Voiceover(node, t, MARK.findall(t) if t else [])
                    _collect_cues(node, vo, helpers)
                    s.voiceovers.append(vo)
    return s


def _cue_helpers(tree):
    """Methods that pass one of their parameters on to self.at / wait_until_bookmark as the mark (a page walk's
    self.hl('x', ...) or self.turn(3, 'x')): name -> (position among the arguments after self, parameter name).
    A call to one of them with a literal there is a cue like self.at itself."""
    out = {}
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        params = [a.arg for a in fn.args.args]
        if params[:1] == ["self"]:
            params = params[1:]
        for n in ast.walk(fn):
            if call_name(n) in ("at", "wait_until_bookmark") and n.args and isinstance(n.args[0], ast.Name) \
                    and n.args[0].id in params:
                out[fn.name] = (params.index(n.args[0].id), n.args[0].id)
                break
    return out


def _collect_cues(with_node, vo, helpers=None):
    """Cue calls inside this voiceover block, not inside a nested voiceover, in source order."""
    helpers = helpers or {}

    def visit(n):
        for ch in ast.iter_child_nodes(n):
            if isinstance(ch, ast.With) and any(call_name(i.context_expr) == "voiceover" for i in ch.items):
                continue
            name, a = call_name(ch), None
            if name in ("at", "wait_until_bookmark") and ch.args:
                a = ch.args[0]
            elif name in helpers:
                i, kw = helpers[name]
                a = ch.args[i] if len(ch.args) > i else next((k.value for k in ch.keywords if k.arg == kw), None)
            if a is not None:
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    vo.cues.append((a.value, ch))
                else:
                    vo.dynamic = True
            visit(ch)
    for st in with_node.body:
        visit(ast.Module(body=[st], type_ignores=[]))


def render_scenes(render_sh):
    """Scene names from SCENES="..." in render.sh (may span lines with backslashes)."""
    m = re.search(r'^\s*(?:export\s+)?SCENES=["\']([^"\']*)["\']', render_sh, re.M)
    return m.group(1).replace("\\\n", " ").split() if m else None
