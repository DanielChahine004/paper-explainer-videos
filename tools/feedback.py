"""Read and triage the timestamped notes left in the catalog player (tools/catalog.py writes <video>/feedback.json).

    python tools/feedback.py                     # every open note, by video and time, with its scene and frame grab
    python tools/feedback.py pet_explorer --all  # one video, resolved notes too
    python tools/feedback.py resolve pet_explorer <nid> design "DESIGN §1: ..."   # close a note, saying how

Triage each note as one of:
  incidental  this video only (a nudge, a typo, a wrong number): fix the scene
  design      a class of mistake a reader must judge: fix the scene and add or sharpen a DESIGN.md rule
  vlint       a class a program can catch: fix the scene and add a vlint rule with a planted bug in its tests
  wontfix     considered and left, with the reason
A note made on an older render (its 'render' stamp differs from the current file) may point at a moved moment; the frame
grab in <video>/review/feedback/<nid>.jpg shows what was on screen when it was written.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KINDS = ("incidental", "design", "vlint", "wontfix")


def fmt(t):
    t = int(round(t))
    return f"{t // 60}:{t % 60:02d}"


def notes(vid):
    try:
        return json.loads((ROOT / vid / "feedback.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def show(vids, every):
    shown = 0
    for vid in vids:
        ns = [n for n in notes(vid) if every or n.get("status") == "open"]
        if not ns:
            continue
        full = next(iter((ROOT / vid).glob("*_narrated.mp4")), None)
        now = int(full.stat().st_mtime) if full else None
        print(f"== {vid}: {len(ns)} note(s)")
        for n in sorted(ns, key=lambda n: n["t"]):
            where = f"{n['scene']} @ {n['scene_t']} s" if n.get("scene") else "scene unknown"
            stale = "" if n.get("render") == now else "  [older render]"
            grab = ROOT / vid / "review" / "feedback" / f"{n['nid']}.jpg"
            print(f"  {n['nid']}  {fmt(n['t']):>6}  {where}{stale}  ({n['status']})")
            print("      " + n["text"].replace("\n", "\n      "))
            if grab.exists():
                print(f"      frame: {grab}")
            if n.get("resolution"):
                print(f"      -> {n['kind']}: {n['resolution']}")
            shown += 1
    if not shown:
        print("no open notes" if not every else "no notes")


def resolve(vid, nid, kind, what):
    if kind not in KINDS:
        sys.exit(f"kind must be one of {', '.join(KINDS)}")
    ns = notes(vid)
    hit = [n for n in ns if n["nid"] == nid]
    if not hit:
        sys.exit(f"no note {nid} in {vid}")
    hit[0].update(status="done", kind=kind, resolution=what, resolved=time.strftime("%Y-%m-%d %H:%M"))
    (ROOT / vid / "feedback.json").write_text(json.dumps(ns, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{vid} {nid}: {kind}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["resolve"]:
        if len(a) != 5:
            sys.exit(__doc__)
        resolve(*a[1:])
    else:
        every = "--all" in a
        a = [x for x in a if x != "--all"]
        vids = a or sorted(p.parent.name for p in ROOT.glob("*/feedback.json"))
        show(vids, every)
