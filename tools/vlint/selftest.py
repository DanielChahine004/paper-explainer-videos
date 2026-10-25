"""`vlint selftest`: proves each rule fires on its planted bug and stays quiet on clean code.

static   tests/static_bad: every "# expect: rule" comment must match a finding on that line (and vice versa);
         tests/static_good: no warnings or errors; every static rule that can warn must have a planted bug.
output   a throwaway render folder: a missing video, a stale one and a fresh one.
runtime  tests/runtime/rt_vo.py rendered at 480p (only where manim is installed): counts per rule match EXPECT.
A new rule is not finished until it has a planted bug here."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from .core import RULES, load_config, load_rules

T = Path(__file__).resolve().parent / "tests"
EXPECT = re.compile(r"#\s*expect:\s*([\w\-, ]+)")


def _expected(folder):
    exp = Counter()
    for f in sorted(folder.iterdir()):
        if f.suffix in (".py", ".sh"):
            for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                m = EXPECT.search(ln)
                if m:
                    for r in m.group(1).split(","):
                        exp[(f.name, i, r.strip())] += 1
    return exp


def static():
    from .__main__ import check_static

    ok = True
    got = Counter((f.file, f.line, f.rule) for f in check_static(T / "static_bad") if f.severity != "info")
    exp = _expected(T / "static_bad")
    for k in sorted(set(exp) | set(got)):
        if exp[k] != got[k]:
            ok = False
            print(f"  static_bad {k[0]}:{k[1]} {k[2]}: expected {exp[k]}, got {got[k]}")
    planted = {r for _, _, r in exp}
    for r in RULES.values():
        if r.stage == "static" and r.severity != "info" and r.id not in planted and not r.fn.__module__.startswith("vlint_local"):
            ok = False
            print(f"  rule {r.id} has no planted bug in tests/static_bad")
    bad = [f for f in check_static(T / "static_good") if f.severity in ("warn", "error")]
    for f in bad:
        ok = False
        print("  static_good false positive:", f.fmt())
    print(f"static : {'ok' if ok else 'FAILED'} ({sum(got.values())} planted findings)")
    return ok


def output():
    from .fingerprint import fingerprint
    from .rules_output import OutputCtx

    ok = True
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        shutil.copy(T / "static_good" / "good_vo.py", d / "good_vo.py")
        part = d / "m_Intro/videos/good_vo/480p15/Intro.mp4"
        cfg = load_config(d)

        def run():
            ctx = OutputCtx(d, d / "good_vo.py", "480p15", ["Intro"], cfg, "parts")
            return sorted({rid for rid, r in RULES.items() if r.stage == "output" for _ in (r.fn(ctx) or ())})

        r1 = run()
        part.parent.mkdir(parents=True)
        part.write_bytes(b"")
        rec = part.with_name("Intro.vlint.json")
        rec.write_text(json.dumps({"fingerprint": "0" * 16, "findings": []}))
        r2 = run()
        rec.write_text(json.dumps({"fingerprint": fingerprint(d / "good_vo.py", "Intro"), "findings": []}))
        r3 = run()
        log = d / "m_Intro.log"
        log.write_text("layout: 1 problem\n  [1] t=2.5-3.0s (x.py:9)  a (MathTex 'x'): box runs through the text\n")
        r3b = run()
        log.write_text("layout: 1 problem\n  [1] t=67.7–6.2s (common_gx.py:148)  eq3 (MathTex 'x'): 0.03 past the bottom edge\n",
                       encoding="utf-8")
        r3c = run()
        log.unlink()
        (d / "good_vo.py").write_text((d / "good_vo.py").read_text().replace("1.8", "1.9"))
        r4 = run()
        for name, got, want in [("missing", r1, ["missing-scene"]), ("stale", r2, ["stale-scene"]),
                                ("fresh", r3, []), ("gx note", r3b, []), ("gx edge", r3c, ["gx-frame-edge"]),
                                ("edited", r4, ["stale-scene"])]:
            if got != want:
                ok = False
                print(f"  output case {name}: expected {want}, got {got}")
        if shutil.which("ffmpeg") and shutil.which("ffprobe"):
            ok &= _final_cases(d, cfg)
        else:
            print("  final checks skipped (no ffmpeg here)")
    print(f"output : {'ok' if ok else 'FAILED'}")
    return ok


def _final_cases(d, cfg):
    """Two synthetic scenes (2 s of video, 1.2 s of narration each) joined the right way and the old way."""
    from .rules_output import OutputCtx

    ff = ["ffmpeg", "-loglevel", "error", "-y"]
    scenes = ["A", "B"]
    for s in scenes:
        p = d / f"m_{s}/videos/good_vo/480p15/{s}.mp4"
        p.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(ff + ["-f", "lavfi", "-i", "color=c=black:s=854x480:r=15:d=2", "-f", "lavfi", "-i",
                             "sine=f=440:d=1.2", "-c:v", "libx264", "-c:a", "aac", str(p)], check=True)
    lst = d / "list.txt"
    lst.write_text("".join(f"file '{d}/m_{s}/videos/good_vo/480p15/{s}.mp4'\n" for s in scenes))
    good, bad = d / "good.mp4", d / "bad.mp4"
    subprocess.run(ff + ["-f", "concat", "-safe", "0", "-i", str(lst), "-c:v", "copy", "-af",
                         "aresample=async=1:first_pts=0", "-c:a", "aac", str(good)], check=True)
    subprocess.run(ff + ["-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(bad)], check=True)
    ok = True
    for f, want in ((good, []), (bad, ["av-sync"])):
        ctx = OutputCtx(d, d / "good_vo.py", "480p15", scenes, cfg, "final", final=f)
        got = sorted({rid for rid, r in RULES.items() if r.stage == "output" for _ in (r.fn(ctx) or ())})
        if got != want:
            ok = False
            print(f"  final case {f.name}: expected {want}, got {got}")
    return ok


def runtime():
    try:
        import manim  # noqa: F401
    except ImportError:
        print("runtime: skipped (manim not installed here; run selftest in the render environment)")
        return True
    ok = True
    src = T / "runtime" / "rt_vo.py"
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run([sys.executable, "-m", "manim", "-ql", "--disable_caching", "--progress_bar", "none",
                            "--media_dir", d, str(src), "Fixture"], capture_output=True, text=True)
        recs = list(Path(d).rglob("Fixture.vlint.json"))
        if r.returncode or not recs:
            print(r.stdout[-2000:], r.stderr[-2000:])
            print("runtime: FAILED (fixture did not render)")
            return False
        found = json.loads(recs[0].read_text())["findings"]
        got = Counter(f["rule"] for f in found)
    ns = {}
    exec(compile(re.search(r"EXPECT = \{[^}]*\}", src.read_text()).group(0), "EXPECT", "exec"), ns)
    for k in sorted(set(ns["EXPECT"]) | set(got)):
        if ns["EXPECT"].get(k, 0) != got.get(k, 0):
            ok = False
            print(f"  runtime {k}: expected {ns['EXPECT'].get(k, 0)}, got {got.get(k, 0)}")
            for f in found:
                if f["rule"] == k:
                    print(f"    {f.get('msg', f)}")
    planted = set(ns["EXPECT"])
    for rr in RULES.values():
        if rr.stage == "runtime" and rr.id not in planted and not rr.fn.__module__.startswith("vlint_local"):
            ok = False
            print(f"  rule {rr.id} has no planted bug in tests/runtime")
    print(f"runtime: {'ok' if ok else 'FAILED'} ({sum(got.values())} planted findings)")
    return ok


def run():
    load_rules()
    results = [static(), output(), runtime()]
    return 0 if all(results) else 1
