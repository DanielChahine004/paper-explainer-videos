"""vlint: deterministic checks for the narrated videos, so the design rules don't depend on anyone remembering them.

  python tools/vlint check <video dir | x_vo.py>...    static rules (no manim needed; run before every render)
  python tools/vlint stale <dir> --script S --res R SCENES...   print the scenes that must be (re)rendered
  python tools/vlint adopt <dir> --script S --res R SCENES...   trust videos rendered before vlint (writes records)
  python tools/vlint parts <dir> --script S --res R SCENES...   before the join: missing/stale scenes, runtime findings
  python tools/vlint final <out.mp4> --script S --res R SCENES... after the join: resolution, A/V sync, length
  python tools/vlint rules [--md]                       list every rule (--md: the table for docs/CHECKS.md)
  python tools/vlint selftest                           every rule against its planted-bug fixture
Exit status 1 when any finding is an error (VLINT_ALLOW=1 reports without failing). Rules and config: core.py.
"""
import argparse
import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vlint import core  # noqa: E402
from vlint.core import RULES, Finding, finalize, load_config, load_rules, report  # noqa: E402


def scripts_in(path):
    p = Path(path)
    return [p] if p.is_file() else sorted(p.glob("*_vo.py"))


def check_static(path):
    """All static findings for one video folder or script, config and suppressions applied."""
    from vlint.script import load_script

    out = []
    for sp in scripts_in(path):
        load_rules(sp.parent, stages=("static",))
        cfg = load_config(sp.parent)
        try:
            s = load_script(sp, cfg)
        except SyntaxError as e:
            out += finalize([Finding("syntax-error", str(e.msg), sp.name, e.lineno or 0)], cfg)
            continue
        found = []
        for r in RULES.values():
            if r.stage != "static" or cfg.level(r.id) == "off":
                continue
            try:
                for where, msg in r.fn(s) or ():
                    found.append(_finding(r.id, where, msg, sp, s))
            except Exception as e:  # a broken rule is reported, never fatal
                found.append(Finding("vlint-internal", f"rule {r.id} crashed: {e!r}", sp.name, 0))
        out += finalize([f for f in found if f is not None], cfg)
    return out


def _finding(rid, where, msg, sp, s):
    if isinstance(where, tuple):                       # ("render.sh", line)
        return Finding(rid, msg, where[0], where[1])
    if isinstance(where, int):
        line, end = where, where
    else:
        line = getattr(where, "lineno", 0)
        end = line if isinstance(where, ast.With) else getattr(where, "end_lineno", line)
    if s.sup.hides(rid, line, end):
        return None
    return Finding(rid, msg, sp.name, line)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vlint", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("check")
    c.add_argument("paths", nargs="+")
    c.add_argument("-q", "--quiet", action="store_true", help="hide info notes")
    for name in ("stale", "recheck", "adopt", "parts", "final"):
        p = sub.add_parser(name)
        p.add_argument("target")
        p.add_argument("--script", required=True)
        p.add_argument("--res", required=True)
        p.add_argument("--pattern")
        p.add_argument("scenes", nargs="+")
    r = sub.add_parser("rules")
    r.add_argument("--md", action="store_true")
    sub.add_parser("selftest")
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in sub.choices and not argv[0].startswith("-"):
        argv.insert(0, "check")                          # `vlint <dir>` means check
    a = ap.parse_args(argv)

    if a.cmd == "check":
        return report([f for p in a.paths for f in check_static(p)], quiet_info=a.quiet)
    if a.cmd == "rules":
        load_rules()
        return list_rules(a.md)
    if a.cmd == "selftest":
        from vlint.selftest import run
        return run()
    if a.cmd in ("stale", "recheck", "adopt", "parts", "final"):
        from vlint.rules_output import OutputCtx, runtime_findings

        load_rules(stages=("output",))
        target = Path(a.target).resolve()
        vdir = target if a.cmd != "final" else target.parent
        script = (vdir / a.script).resolve()
        cfg = load_config(vdir)
        ctx = OutputCtx(vdir, script, a.res, a.scenes, cfg, "parts" if a.cmd != "final" else "final",
                        final=target if a.cmd == "final" else None, pattern=a.pattern)
        if a.cmd == "stale":
            for s in a.scenes:
                why = ctx.stale(s)
                if why:
                    print(s)
                    print(f"vlint: {s}: {why}", file=sys.stderr)
            return 0
        if a.cmd == "recheck":
            from vlint.rules_output import needs_recheck
            for s in a.scenes:
                if needs_recheck(ctx, s):
                    print(s)
            return 0
        if a.cmd == "adopt":
            from vlint.core import write_json
            for s, p in ctx.parts.items():
                rec = p.with_name(p.stem + ".vlint.json")
                if p.exists() and not rec.exists():
                    write_json(rec, {"scene": s, "script": script.name, "fingerprint": ctx.fp(s), "monitor": False,
                                     "adopted": True, "findings": []})
                    print(f"vlint: adopted {s} as rendered from the current code")
            return 0
        found = []
        for rr in RULES.values():
            if rr.stage == "output":
                for where, msg in rr.fn(ctx) or ():
                    found.append(Finding(rr.id, msg, script.name, scene=where if where in a.scenes else "",
                                         ) if where in a.scenes else Finding(rr.id, msg, where))
        if a.cmd == "parts":
            load_rules(vdir, stages=())                  # pick up local runtime rule docs, if importable
            found += runtime_findings(ctx)
        return report(finalize(found, cfg))
    ap.print_help()
    return 2


def list_rules(md=False):
    rows = sorted(RULES.values(), key=lambda r: (["static", "runtime", "output"].index(r.stage), r.id))
    if md:
        print("| rule | stage | default | checks | DESIGN.md |\n|---|---|---|---|---|")
        for r in rows:
            print(f"| `{r.id}` | {r.stage} | {r.severity} | {r.summary} | {r.design} |")
    else:
        for r in rows:
            print(f"{r.id:22s} {r.stage:8s} {r.severity:6s} {r.summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
