"""What every static rule finds across the whole corpus, remembered in baseline.json.

A rule that stops matching is invisible: zero findings reads exactly like a clean repo. That is how a rule
whose `\\b` word boundaries had become literal backspace bytes shipped, reported all 50-odd videos clean, and
was believed. It is also the only cheap guard over the runtime stage's real material, since the planted-bug
fixture proves a rule fires once in a toy scene, not that it still fires on the videos people actually make.

    python tools/vlint baseline            compare the corpus with baseline.json
    python tools/vlint baseline --write    record what it finds now as the new baseline

Static only, so it reads scripts and never renders: the whole corpus takes seconds and needs no manim, no GPU
and no narration cache. Counts are taken after suppressions, so they are what a person would actually see.

The runtime and output stages cannot be measured that way -- they need a render -- so what they find is
recorded from the records a check has just written, per video:

    bash tools/check.sh <video>                     report, with that video's recorded findings held back
    RECORD=1 bash tools/check.sh <video>            accept what it finds now as that video's known debt

That ledger is what keeps a finished video quiet. A video nobody is going to revisit has its layout warnings
counted once instead of reprinted on every corpus check, and anything above the recorded count still prints:
the difference between a rule that is being ignored and a rule nobody has read is whether it is on the record.
Debt is only ever accepted deliberately, by someone passing RECORD=1.
"""
import json
from collections import Counter
from pathlib import Path

from .core import RULES, load_rules

HERE = Path(__file__).resolve().parent
FILE = HERE / "baseline.json"


def videos(root):
    """Every video folder: the ones with a render.sh beside their scene script."""
    return sorted(d for d in root.iterdir() if d.is_dir() and (d / "render.sh").is_file())


def measure(root):
    """{video: {rule: count}}. Per video, not just per rule: a corpus total hides a rule losing one branch,
    and it cannot tell "someone edited this video" from "the rule broke everywhere"."""
    from .__main__ import check_static

    out = {}
    for d in videos(root):
        n = Counter()
        for f in check_static(d):
            n[f.rule] += 1
        out[d.name] = dict(sorted(n.items()))
    return out


def totals(per_video):
    n = Counter()
    for counts in per_video.values():
        n.update(counts)
    return n


def load():
    return json.loads(FILE.read_text(encoding="utf-8")) if FILE.is_file() else {}


def known(video):
    """What this video's runtime and output stages are already known to find: {rule: count}."""
    return load().get("runtime", {}).get(video, {})


def record(video, recdir):
    """Accept what a check just found for one video as its known debt. Reads the scene records rather than
    re-rendering, so this costs nothing beyond the check that has already run."""
    n = Counter()
    for f in sorted(Path(recdir).rglob("*.vlint.json")):
        for x in json.loads(f.read_text(encoding="utf-8")).get("findings", []):
            if x.get("severity", "warn") != "error":        # an error is never debt
                n[x["rule"]] += 1
    data = load()
    data.setdefault("runtime", {})[video] = dict(sorted(n.items()))
    FILE.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print(f"  recorded as known: {sum(n.values())} finding(s) over {len(n)} rule(s) in {video}")
    return 0


def run(root=None, write=False):
    root = Path(root or HERE.parent.parent).resolve()
    load_rules()
    now = measure(root)
    now_t = totals(now)
    static_ids = {r.id for r in RULES.values() if r.stage == "static"}
    if write:
        data = load()                                       # the runtime ledger is written elsewhere: keep it
        data["videos"] = now
        FILE.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
        print(f"baseline: wrote {len(now_t)} rules over {len(now)} videos -> {FILE.name}")
        return 0
    if not FILE.is_file():
        print("baseline: no baseline.json yet; run `vlint baseline --write`")
        return 1
    was = json.loads(FILE.read_text(encoding="utf-8"))["videos"]
    was_t = totals(was)
    # A rule that found things and now finds none anywhere is broken, not satisfied: nobody fixes 44 videos at
    # once. A rule that keeps firing but drops a tenth of its findings has usually lost one branch.
    lost = sorted(r for r in was_t if was_t[r] and not now_t.get(r))
    shrunk = sorted(r for r in was_t if r not in lost and was_t[r] - now_t.get(r, 0) > max(2, was_t[r] // 10))
    for r in lost + shrunk:
        where = sorted((v for v in set(was) | set(now)
                        if was.get(v, {}).get(r, 0) != now.get(v, {}).get(r, 0)))[:6]
        tag = "LOST   " if r in lost else "SHRANK "
        print(f"  {tag} {r}: {was_t[r]} -> {now_t.get(r, 0)}  ({', '.join(where)})")
    for r in sorted(r for r in now_t if not was_t.get(r)):
        print(f"  new     {r}: {now_t[r]}")
    for v in sorted(set(was) | set(now)):
        a, b = was.get(v), now.get(v)
        if a is None or b is None:
            print(f"  {'added' if a is None else 'gone '}   video {v}")
        elif a != b and not (set(a) | set(b)) & set(lost + shrunk):
            print(f"  video   {v}: {a} -> {b}")
    quiet = sorted(static_ids - set(now_t))
    if quiet:
        print(f"  never fires anywhere ({len(quiet)}): {', '.join(quiet)}")
    debt = load().get("runtime", {})
    if debt:
        held = sum(sum(c.values()) for c in debt.values())
        print(f"  runtime ledger: {held} finding(s) held as known debt over {len(debt)} video(s)")
    bad = lost + shrunk
    print(f"baseline: {'FAILED' if bad else 'ok'} ({sum(now_t.values())} findings over {len(now)} videos)")
    return 1 if bad else 0
