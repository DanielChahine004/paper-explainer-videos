"""How long each video takes to make, phase by phase: <video>/timelog.json.

A phase runs from its mark to the next mark; "sent" closes the first version, "done" closes feedback rounds.
Phases in order: received (the paper is in src/), figures (page renders, crops), script, check (vlint until clean),
render (1080p and frame review), sent, feedback (a round of notes), done. Renders log themselves (render_lib.sh
writes render_start / render_end events), so the report also shows how many renders a video took and their time.

  python tools/timelog.py mark <video> <phase> [--at "2026-10-26 18:11"] [--note text]
  python tools/timelog.py report [<video> ...]       (no video: every video with a timelog)
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FMT = "%Y-%m-%d %H:%M:%S"


def _load(video):
    f = ROOT / video / "timelog.json"
    return f, (json.loads(f.read_text()) if f.exists() else {"marks": [], "events": []})


def _save(f, log):
    f.write_text(json.dumps(log, indent=1) + "\n")


def _now():
    return datetime.now().strftime(FMT)


def mark(video, phase, at=None, note=None):
    f, log = _load(video)
    t = datetime.strptime(at, FMT if at.count(":") == 2 else "%Y-%m-%d %H:%M").strftime(FMT) if at else _now()
    log["marks"].append({"phase": phase, "t": t, **({"note": note} if note else {})})
    log["marks"].sort(key=lambda m: m["t"])
    _save(f, log)


def event(video_dir, name):
    """Called from render_lib.sh with the video's folder (the render's working directory)."""
    d = Path(video_dir).resolve()
    f = d / "timelog.json"
    log = json.loads(f.read_text()) if f.exists() else {"marks": [], "events": []}
    log["events"].append({"event": name, "t": _now()})
    _save(f, log)


def _mins(a, b):
    return (datetime.strptime(b, FMT) - datetime.strptime(a, FMT)).total_seconds() / 60


def report(videos):
    if not videos:
        videos = sorted(p.parent.name for p in ROOT.glob("*/timelog.json"))
    for v in videos:
        _, log = _load(v)
        ms = log["marks"]
        if not ms:
            continue
        print(f"== {v}")
        for a, b in zip(ms, ms[1:]):
            print(f"  {a['phase']:<10} {_mins(a['t'], b['t']):6.1f} min   {a['t'][11:16]}{'  ' + a['note'] if 'note' in a else ''}")
        sent = next((m["t"] for m in ms if m["phase"] == "sent"), None)
        if sent:
            print(f"  {'to first send':<10} {_mins(ms[0]['t'], sent):6.1f} min")
        if ms[-1]["phase"] == "done":
            print(f"  {'total':<10} {_mins(ms[0]['t'], ms[-1]['t']):6.1f} min")
        ev = log["events"]
        starts = [e["t"] for e in ev if e["event"].startswith("render_start")]
        ends = [e["t"] for e in ev if e["event"] == "render_end"]
        if starts:
            spent = sum(_mins(a, b) for a, b in zip(starts, ends))
            print(f"  renders    {len(starts)} run(s), {spent:.1f} min rendering")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("mark")
    m.add_argument("video"), m.add_argument("phase"), m.add_argument("--at"), m.add_argument("--note")
    e = sub.add_parser("event")
    e.add_argument("video_dir"), e.add_argument("name")
    r = sub.add_parser("report")
    r.add_argument("videos", nargs="*")
    a = ap.parse_args()
    if a.cmd == "mark":
        mark(a.video, a.phase, a.at, a.note)
    elif a.cmd == "event":
        event(a.video_dir, a.name)
    else:
        report(a.videos)


if __name__ == "__main__":
    sys.exit(main())
