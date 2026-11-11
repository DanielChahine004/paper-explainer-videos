"""A scene's fingerprint: a hash of everything that can change its video. That is its own class (and any scene class
it inherits from), the script's shared code (helpers, constants, other non-scene classes), common.py, voices.py and
the video's assets/ folder. Comments, blank lines and the module docstring do not count, so editing one scene leaves
the others' fingerprints alone and only the edited scene is re-rendered."""
import ast
import hashlib
from pathlib import Path

from .core import find_root


def _is_scene(st):
    return isinstance(st, ast.ClassDef) and any(isinstance(b, ast.FunctionDef) and b.name == "construct" for b in st.body)


def imports_kit(tree):
    """Whether a script draws with the shared primitives (from kit import ...)."""
    return any(isinstance(n, ast.ImportFrom) and n.module == "kit" or
               isinstance(n, ast.Import) and any(a.name == "kit" for a in n.names) for n in ast.walk(tree))


def kit_used(tree, kit):
    """The part of kit.py a script can reach: its statements that are not functions or classes (imports,
    constants), and the functions and classes the script names, followed through kit's own calls. Promoting a
    primitive, or changing one, then stales only the videos that draw with it (pet_g4_configs: a promotion at
    the end of a build would have staled that build and every other video importing kit)."""
    body = _strip_doc(ast.parse(kit.read_text(encoding="utf-8")).body)
    defs = {st.name: st for st in body if isinstance(st, (ast.FunctionDef, ast.ClassDef))}
    names = lambda t: {n.id for n in ast.walk(t) if isinstance(n, ast.Name)} | \
        {n.attr for n in ast.walk(t) if isinstance(n, ast.Attribute)}
    todo, used = list(names(tree) & defs.keys()), set()
    while todo:
        k = todo.pop()
        if k not in used:
            used.add(k)
            todo += [m for m in names(defs[k]) & defs.keys() if m not in used]
    keep = [st for st in body if not isinstance(st, (ast.FunctionDef, ast.ClassDef)) or st.name in used]
    return ast.dump(ast.Module(body=keep, type_ignores=[]))


def _strip_doc(body):
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        return body[1:]
    return body


def fingerprint(script, scene):
    script = Path(script).resolve()
    tree = ast.parse(script.read_text(encoding="utf-8"))
    classes = {st.name: st for st in tree.body if _is_scene(st)}
    if scene not in classes:
        return None
    h = hashlib.sha256()
    h.update(ast.dump(ast.Module(body=[st for st in _strip_doc(tree.body) if not _is_scene(st)], type_ignores=[])).encode())
    todo, done = [scene], set()
    while todo:                                  # the scene and the scene classes it inherits from
        c = todo.pop()
        if c in done or c not in classes:
            continue
        done.add(c)
        h.update(ast.dump(classes[c]).encode())
        todo += [b.id for b in classes[c].bases if isinstance(b, ast.Name)]
    root = find_root(script.parent)
    for name in ("common.py", "common_ce.py", "common_gx.py", "voices.py"):
        p = root / name
        if p.exists():
            h.update(ast.dump(ast.Module(body=_strip_doc(ast.parse(p.read_text(encoding="utf-8")).body), type_ignores=[])).encode())
    if imports_kit(tree) and (root / "kit.py").exists():
        h.update(kit_used(tree, root / "kit.py").encode())
    assets = script.parent / "assets"
    if assets.is_dir():
        for f in sorted(assets.rglob("*")):
            if f.is_file():
                h.update(f.relative_to(assets).as_posix().encode())
                h.update(hashlib.sha256(f.read_bytes()).digest())
    return h.hexdigest()[:16]


def rules_hash(script):
    """A hash of the checks themselves (the rule modules and every vlint.toml that applies), saved in each scene's
    record. When it changes, the scene's video is still current but its findings are not: render.sh re-checks it
    in skip mode (seconds) instead of re-rendering it."""
    script = Path(script).resolve()
    h = hashlib.sha256()
    here = Path(__file__).resolve().parent
    # script.py and core.py count too: the static rules read the narration through script._collect_cues and
    # MARK, and core carries the severities. Leaving them out meant an edit to the cue parsing left every
    # scene's cached findings looking current, so `vlint recheck` re-checked nothing.
    for f in sorted(here.glob("rules_*.py")) + [here / "runtime.py", here / "script.py", here / "core.py"]:
        h.update(f.name.encode())
        h.update(f.read_bytes())
    root = find_root(script.parent)
    for d in sorted({root, script.parent}):
        for f in sorted(d.glob("vlint*.py")) + [d / "vlint.toml"]:
            if f.is_file():
                h.update(f.read_bytes())
    return h.hexdigest()[:16]
