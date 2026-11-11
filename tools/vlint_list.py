"""List the findings in every <scene>.vlint.json under a folder, most severe first: severity, rule, scene, time,
message. Only 1080p records unless --all (tools/check.sh writes its records to chk/ and passes --all).

With `--known <video>`, findings a rule is already recorded as making in that video are held back and counted
on one line instead (vlint/baseline.py: the runtime ledger). A rule finding MORE than its record prints in
full, because a count cannot say which of them is the new one. Errors are never held back.
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vlint.baseline import known as known_debt  # noqa: E402

ORDER = {"error": 0, "warn": 1, "info": 2}
args = sys.argv[1:]
video = args[args.index("--known") + 1] if "--known" in args else None
debt = known_debt(video) if video else {}

rows = []
for f in sorted(Path(args[0]).rglob("*.vlint.json")):
    if "1080p60" not in str(f) and "--all" not in args:
        continue
    for x in json.loads(f.read_text())["findings"]:
        sev = x.get("severity", "warn")
        rows.append((ORDER.get(sev, 1), sev, x["rule"], x["scene"], x.get("time", 0), x["msg"]))

# a rule at or under its recorded count is debt someone has already looked at and accepted
seen = Counter(r[2] for r in rows if r[1] != "error")
held = {r: n for r, n in debt.items() if 0 < seen.get(r, 0) <= n}
for _, sev, rule, scene, t, msg in sorted(rows, key=lambda r: (r[0], r[3], r[4])):
    if sev != "error" and rule in held:
        continue
    over = f"  [{seen[rule]} of a recorded {debt[rule]}]" if rule in debt and sev != "error" else ""
    print(f"{sev:5s} {rule:18s} {scene:13s} {t:6.1f}  {msg[:130]}{over}")
if held:
    s = ", ".join(f"{r} {n}" for r, n in sorted(held.items()))
    print(f"      {sum(held.values())} known, held back: {s}   (RECORD=1 to re-record)")
