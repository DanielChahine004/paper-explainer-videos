"""vlint core: a registry of small rule functions, the config that sets each rule's severity, and the comments
that silence a single finding. The rules themselves live in rules_*.py beside this file, plus an optional
<video>/vlint_rules.py, so adding a check never means editing this file.

A rule is a function decorated with @rule(...). It has an id, a stage (static: reads the script; runtime: runs
inside the scene while it renders; output: reads the rendered files), a default severity (error, warn, info),
a one-line summary and the DESIGN.md section it enforces. Static rules take a Script and yield (line, message)
pairs; runtime and output rules get their own context objects (see rules_runtime.py, rules_output.py).

Severity is set per rule in vlint.toml (project root, then the video folder, later wins):
    [rules]
    text-overlap = "error"        # or "warn", "info", "off"
    [options]
    max_words = 14                # options a rule reads with opt(ctx, name, default)
    [scenes.Opening]
    ignore = ["frame-clip"]       # runtime and output rules, for one scene
In a script, `# vlint: ignore[rule-id]` silences that line, `# vlint: ignore-next[rule-id]` the next line and
`# vlint: ignore-file[rule-id]` the whole file; a reason after the bracket is encouraged. `ignore[*]` silences
every rule there. Errors fail the render; VLINT_ALLOW=1 reports them without failing.
"""
import importlib.util
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # python < 3.11
    tomllib = None

PKG = Path(__file__).resolve().parent
LEVELS = {"off": 0, "info": 1, "warn": 2, "error": 3}


@dataclass
class Rule:
    id: str
    stage: str
    severity: str
    summary: str
    design: str = ""
    fix: str = ""
    fn: object = None


RULES: dict[str, Rule] = {}


def rule(id, stage, severity, summary, design="", fix=""):
    """Register a rule. The decorated function is returned unchanged, so rules stay plain functions."""
    assert stage in ("static", "runtime", "output"), stage
    assert severity in LEVELS, severity

    def deco(fn):
        if id in RULES and RULES[id].fn is not fn:
            raise ValueError(f"vlint rule id {id!r} registered twice")
        RULES[id] = Rule(id, stage, severity, summary, design, fix, fn)
        return fn

    return deco


@dataclass
class Finding:
    rule: str
    msg: str
    file: str = ""
    line: int = 0
    scene: str = ""
    time: float = -1.0
    severity: str = ""

    def where(self):
        if self.line:
            return f"{self.file}:{self.line}"
        if self.scene:
            return f"{self.file or '?'} {self.scene}" + (f" t={self.time:.1f}s" if self.time >= 0 else "")
        return self.file

    def fmt(self):
        r = RULES.get(self.rule)
        hint = f"\n      fix: {r.fix}" if r and r.fix and self.severity == "error" else ""
        ref = f"  [DESIGN {r.design}]" if r and r.design else ""
        return f"{self.where()}: {self.severity}[{self.rule}] {self.msg}{ref}{hint}"


# ---- discovery and config -------------------------------------------------------------------------------------
def find_root(start):
    """The project root: the nearest folder at or above `start` holding common.py."""
    p = Path(start).resolve()
    for q in (p, *p.parents):
        if (q / "common.py").exists():
            return q
    return p


_loaded = set()


def load_rules(video_dir=None, stages=("static", "runtime", "output")):
    """Import rules_<stage>*.py for the stages asked for (runtime rules import manim, so the static linter, which
    must run anywhere, never loads them), then the video's own vlint_rules.py if it has one."""
    for st in stages:
        for f in sorted(PKG.glob(f"rules_{st}*.py")):
            _import(f)
    local = Path(video_dir) / "vlint_rules.py" if video_dir is not None else None
    if local is not None and local.exists():
        try:
            _import(local)
        except ImportError as e:
            print(f"vlint: skipped {local} here ({e}); import heavy modules inside the rule function", file=sys.stderr)
    return RULES


def _import(f):
    f = f.resolve()
    if f in _loaded:
        return
    _loaded.add(f)
    name = "vlint." + f.stem if f.parent == PKG else f"vlint_local_{abs(hash(f))}"
    if name in sys.modules:
        return
    spec = importlib.util.spec_from_file_location(name, f)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)


def _read_toml(p):
    if not p.exists():
        return {}
    if tomllib is None:
        raise RuntimeError(f"{p}: reading vlint.toml needs python >= 3.11")
    with open(p, "rb") as fh:
        return tomllib.load(fh)


@dataclass
class Config:
    severity: dict = field(default_factory=dict)
    options: dict = field(default_factory=dict)
    scenes: dict = field(default_factory=dict)

    def level(self, rule_id, scene=None):
        if scene and rule_id in self.scenes.get(scene, {}).get("ignore", []):
            return "off"
        if scene and "*" in self.scenes.get(scene, {}).get("ignore", []):
            return "off"
        sev = self.severity.get(rule_id) or (RULES[rule_id].severity if rule_id in RULES else "warn")
        if sev not in LEVELS:
            raise ValueError(f"vlint.toml: {rule_id} = {sev!r}, expected one of {list(LEVELS)}")
        return sev


def load_config(video_dir):
    video_dir = Path(video_dir).resolve()
    cfg = Config()
    for p in dict.fromkeys([find_root(video_dir) / "vlint.toml", video_dir / "vlint.toml"]):
        d = _read_toml(p)
        unknown = set(d) - {"rules", "options", "scenes"}
        if unknown:
            raise ValueError(f"{p}: unknown sections {sorted(unknown)}")
        cfg.severity.update(d.get("rules", {}))
        cfg.options.update(d.get("options", {}))
        for s, v in d.get("scenes", {}).items():
            cfg.scenes.setdefault(s, {}).update(v)
    return cfg


def opt(ctx, name, default):
    """Read an [options] value from vlint.toml (ctx is any context carrying .config)."""
    return ctx.config.options.get(name, default)


# ---- inline suppressions --------------------------------------------------------------------------------------
_SUP = re.compile(r"#\s*vlint:\s*(ignore|ignore-next|ignore-file)\[([^\]]*)\]")


class Suppressions:
    def __init__(self, lines):
        self.by_line, self.file = {}, set()
        for i, ln in enumerate(lines, 1):
            for kind, ids in _SUP.findall(ln):
                ids = {x.strip() for x in ids.split(",") if x.strip()}
                if kind == "ignore-file":
                    self.file |= ids
                else:
                    self.by_line.setdefault(i + (kind == "ignore-next"), set()).update(ids)

    def hides(self, rule_id, line, end=None):
        if rule_id in self.file or "*" in self.file:
            return True
        for ln in range(line, (end or line) + 1):
            ids = self.by_line.get(ln, ())
            if rule_id in ids or "*" in ids:
                return True
        return False


# ---- reporting ------------------------------------------------------------------------------------------------
def finalize(findings, cfg):
    """Apply severities from config, drop 'off', sort errors first."""
    out = []
    for f in findings:
        f.severity = cfg.level(f.rule, f.scene or None)
        if f.severity != "off":
            out.append(f)
    out.sort(key=lambda f: (-LEVELS[f.severity], f.file, f.line, f.scene, f.time))
    return out


def report(findings, quiet_info=False, stream=sys.stdout):
    n = {k: 0 for k in LEVELS}
    for f in findings:
        n[f.severity] += 1
        if not (quiet_info and f.severity == "info"):
            print(f.fmt(), file=stream)
    print(f"vlint: {n['error']} error(s), {n['warn']} warning(s), {n['info']} note(s)", file=stream)
    if n["error"] and os.environ.get("VLINT_ALLOW"):
        print("vlint: VLINT_ALLOW is set, not failing", file=stream)
        return 0
    return 1 if n["error"] else 0


def dump(findings):
    return [asdict(f) for f in findings]


def undump(rows):
    return [Finding(**{k: v for k, v in r.items() if k in Finding.__dataclass_fields__}) for r in rows]


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=1), encoding="utf-8")
