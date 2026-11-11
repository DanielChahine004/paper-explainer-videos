"""Times worth looking at in a rendered scene, one per line, from its <scene>.vlint.json review list: the settled
frame at the end of each narration block, and four frames across each tracker sweep (a moving curve). Used by
tools/review.sh to cut the frames for the scene's review sheet."""
import json
import sys

rec = json.load(open(sys.argv[1])) if sys.argv[1] != "-" else {}
dur = float(sys.argv[2])
ts = [0.5]
if not rec.get("review"):          # a record from before review lists (or none): eight even frames
    ts += [dur * k / 8 for k in range(1, 8)]
for r in rec.get("review", []):
    if r["kind"] == "block_end":
        ts.append(r["t"] - 0.15)
    elif r["kind"] == "sweep" and r["t1"] - r["t0"] > 0.2:
        ts += [r["t0"] + (r["t1"] - r["t0"]) * k / 3 for k in range(4)]
ts.append(dur - 1.2)                 # the last settled frame, before the closing fade
out = []
for t in sorted(min(max(t, 0.0), dur - 0.05) for t in ts):
    if not out or t - out[-1] > 0.25:
        out.append(t)
print("\n".join(f"{t:.2f}" for t in out))
