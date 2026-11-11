"""Which moments of a video are worth looking at: the frames that differ from the one before them.

ffmpeg's scene score says how much each frame changed from the last. A narrated explainer is still for
most of its length -- on capstone, 3423 of 5252 frames sampled at 8 fps were byte-identical to their
predecessor -- so sampling at a fixed interval spends most of its frames on pictures that are not moving
and still skips the transitions, which last under a second. Those transitions are where the defects are:
the head that faded in over the front page did so entirely between two narration blocks, so no settled
frame ever showed it.

So keep a frame once the picture has changed enough since the last one kept. A moving stretch is then
sampled densely, a still one barely at all, and nothing is looked at twice.

    python tools/watch_times.py <scene-score log> [threshold] [min gap] [max gap]

Reads the log ffmpeg writes with `metadata=print`, prints one timestamp per line. The threshold is summed
scene score, not a per-frame cut threshold: 0.02 gives roughly 150 frames for a ten-minute video.
"""
import re
import sys

PTS = re.compile(r"pts_time:([0-9.]+)")
SCORE = re.compile(r"lavfi\.scene_score=([0-9.]+)")


def load(path):
    """[(time, change since the previous sampled frame)] from an ffmpeg metadata log."""
    out, t = [], None
    for line in open(path, encoding="utf-8", errors="replace"):
        m = PTS.search(line)
        if m:
            t = float(m.group(1))
            continue
        m = SCORE.search(line)
        if m and t is not None:
            out.append((t, float(m.group(1))))
            t = None
    return out


def pick(rows, thresh=0.02, min_gap=0.3, max_gap=15.0):
    """Timestamps to look at. min_gap keeps one fast move from filling the sheet with near-copies of
    itself; max_gap keeps a scene that sits still for a long time from going unlooked-at entirely."""
    if not rows:
        return []
    kept, last, acc = [rows[0][0]], rows[0][0], 0.0
    for t, s in rows[1:]:
        acc += s
        if t - last < min_gap:
            continue
        if acc >= thresh or t - last >= max_gap:
            kept.append(t)
            last, acc = t, 0.0
    return kept


def main(argv):
    rows = load(argv[0])
    args = [float(a) for a in argv[1:]]
    times = pick(rows, *args)
    print("\n".join(f"{t:.2f}" for t in times))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
