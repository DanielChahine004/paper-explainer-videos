"""Where each narrated claim comes from, timed to the video, for the site's Sources panel.

The plan cites each narration block's facts (`cite:` lines, checked by `vlint plan --check` against the paper with
paperstore). The captions (tools/captions.py) carry the same words with their times. A block is found in the
captions by its letters alone, so "E J N M M I" in the plan meets "EJNMMI" in the subtitles, and starts where its
first words are said; it lasts until the next block starts.

    python tools/sources.py <video> <captions.vtt>     prints the timed sources as JSON
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vlint import plan as vplan  # noqa: E402
import videofolders as vf  # noqa: E402  (a video is at the root or under private/)

_TS = re.compile(r"(\d+):(\d\d):(\d\d)\.(\d+)\s+-->")
_QUOTE = re.compile(r'^p(\d+)\s+["“](.+)["”]$')
_FIG = re.compile(r"^figure\s+p(\d+)\s*(.*)$", re.I)
_COMP = re.compile(r"^computed\s*(.*)$", re.I)


def _letters(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _cues(vtt):
    """[(start seconds, text)] in order."""
    out, t = [], None
    for ln in Path(vtt).read_text(encoding="utf-8").splitlines():
        m = _TS.match(ln)
        if m:
            h, mi, s, f = m.groups()
            t = int(h) * 3600 + int(mi) * 60 + int(s) + float("0." + f)
        elif ln.strip() and t is not None:
            out.append((t, ln.strip()))
            t = None
    return out


def _cite(c):
    """[page or None, text, kind] for one cite line."""
    m = _QUOTE.match(c)
    if m:
        return [int(m.group(1)), m.group(2), "quote"]
    m = _FIG.match(c)
    if m:
        return [int(m.group(1)), m.group(2), "figure"]
    m = _COMP.match(c)
    return [None, m.group(1) if m else c, "computed"]


def timed(vid, vtt):
    """[{t, scene, cites}] for every cited narration block found in the captions, in time order. [] when the
    video's plan cites nothing."""
    p = vf.folder(vid, ROOT) / "plan.md"
    if not p.exists() or not vtt:
        return []
    pl = vplan._load(p, p.stat().st_mtime_ns)
    cues = _cues(vtt)
    stream, owner = "", []
    for i, (_, text) in enumerate(cues):
        n = _letters(text)
        stream += n
        owner += [i] * len(n)
    found = []                                         # every block, cited or not: each one ends the block before it
    for st in pl.scenes.values():
        for b in st.blocks:
            head = _letters(vplan.IN_PROSE.sub("", b.prose))[:60]
            at = stream.find(head) if len(head) >= 12 else -1
            if at >= 0:                                # else a block the render no longer says
                found.append((cues[owner[at]][0], st.name, b))
    found.sort(key=lambda x: x[0])
    end = cues[-1][0] + 8 if cues else 0
    return [{"t": round(t, 2), "e": round(found[i + 1][0] if i + 1 < len(found) else end, 2), "scene": sc,
             "cites": [_cite(c) for _, c in b.cites]} for i, (t, sc, b) in enumerate(found) if b.cites]


if __name__ == "__main__":
    print(json.dumps(timed(sys.argv[1], sys.argv[2]), ensure_ascii=False, indent=1))
