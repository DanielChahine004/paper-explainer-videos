"""Subtitles (WebVTT) for a finished video, from its own narration: the words come from the script and their timings
from the voice cache's word timings (voices.py), so nothing is transcribed and nothing is misheard.

What the cache does not hold is where each voice clip starts in its scene. A clip is mixed into the scene's audio
as it is, so it is found there by cross-correlation: every clip cached for the scene is tried, and those that are
not in it (lines since rewritten) score low and are left out. That works the same for both engines.

    python tools/captions.py <video>        on Windows: prints the path of the cached .vtt (made in WSL if needed)

Inside WSL (numpy and ffmpeg live in the render env) it is run as `captions.py --align <render root> <video>` and
prints the VTT.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = "/home/h/slab_render/.pixi/envs/default/bin/python"   # the render env, inside WSL
BIN = Path(PY).parent
SR = 8000          # Hz: plenty to find a clip, cheap to correlate
MIN_SCORE = 0.6    # normalised correlation an exact copy of a clip reaches easily (~0.9+); a different line, ~0.1


# ---- inside WSL ---------------------------------------------------------------------------------------------------

def _pcm(path):
    import numpy as np
    out = subprocess.run([str(BIN / "ffmpeg"), "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR),
                          "-f", "s16le", "-"], capture_output=True).stdout
    return np.frombuffer(out, dtype=np.int16).astype(np.float32)


def _duration(path):
    r = subprocess.run([str(BIN / "ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                        str(path)], capture_output=True, text=True).stdout.strip()
    return float(r or 0)


def _find(scene, ends, clip):
    """(offset in samples, score) of the best place for clip in scene."""
    import numpy as np
    n, L = len(scene), len(clip)
    if L == 0 or L > n + SR // 2:
        return 0, 0.0
    size = 1 << (n + L).bit_length()
    c = np.fft.irfft(np.fft.rfft(scene, size) * np.conj(np.fft.rfft(clip, size)), size)[:max(n - L // 2, 1)]
    win = ends[np.minimum(np.arange(len(c)) + L, n)] - ends[np.arange(len(c))]   # scene energy under each placing
    ec = float(np.dot(clip, clip))
    # a near-silent window would turn FFT rounding into a perfect score: count it as at least a quarter of the clip
    score = c / np.sqrt(np.maximum(win, 0.25 * ec) * ec + 1e-9)
    k = int(np.argmax(score))
    return k, float(score[k])


def _words(entry, offset, end):
    """[(time, word with its punctuation)] for one clip placed at offset seconds."""
    spoken = entry["input_data"]["input_text"]
    wb = [w for w in entry["word_boundaries"] if w.get("boundary_type", "Word") == "Word"]
    out = []
    for i, w in enumerate(wb):
        stop = wb[i + 1]["text_offset"] if i + 1 < len(wb) else len(spoken)
        word = spoken[w["text_offset"]:stop].strip()
        if word:
            out.append((offset + w["audio_offset"] / 1e7, word))
    return out, end


def align(render_root, vid):
    import numpy as np
    render_root = Path(render_root)
    words, t0 = [], 0.0   # words: [(time, text, end of its clip)]
    for line in (render_root / vid / "list.txt").read_text().splitlines():
        m = re.match(r"file '/home/h/slab_render/(.+)'", line.strip())
        if not m:
            continue
        mp4 = render_root / m.group(1)
        dur = _duration(mp4)
        cache = render_root / vid / f"m_{mp4.stem}" / "voiceovers"   # each scene renders in <video>/m_<Scene>
        try:
            entries = {e["original_audio"]: e for e in json.loads((cache / "cache.json").read_text())}
        except (OSError, ValueError):
            entries = {}
        if entries:
            scene = _pcm(mp4)
            ends = np.concatenate([[0.0], np.cumsum(scene.astype(np.float64) ** 2)])
            found = []
            for name, e in entries.items():
                clip = _pcm(cache / name)
                k, s = _find(scene, ends, clip)
                if s >= MIN_SCORE:
                    found.append((k / SR, (k + len(clip)) / SR, s, e))
            found.sort(key=lambda f: -f[2])
            kept = []
            for f in found:   # one clip per stretch of audio: the best fit wins
                if all(f[1] <= g[0] + 0.2 or f[0] >= g[1] - 0.2 for g in kept):
                    kept.append(f)
            for a, b, _, e in sorted(kept, key=lambda f: f[0]):
                ws, end = _words(e, t0 + a, t0 + b)
                words += [(t, w, end) for t, w in ws]
        t0 += dur
    return vtt(words)


def _tidy(s):
    # letters spelt out for the voice: "G P U" -> "GPU", "S i PM" -> "SiPM"
    s = re.sub(r"\b[A-Z](?: [A-Za-z]\b)+(?: [A-Z]{2,}\b)?", lambda m: m.group(0).replace(" ", ""), s)
    return " ".join(s.split())


def vtt(words, most=84):
    """Cues of up to two short lines, broken at sentence ends, pauses, and commas once a cue is long."""
    cues, cur = [], []
    for i, (t, w, end) in enumerate(words):
        cur.append((t, w, end))
        text = " ".join(x[1] for x in cur)
        nxt = words[i + 1] if i + 1 < len(words) else None
        gap = (nxt[0] - t) if nxt else 99
        nxt_len = len(nxt[1]) + 1 if nxt else 0
        rest = 0   # what is left of the sentence: a short tail stays on this cue rather than standing alone
        for _, x, _ in words[i + 1:i + 4]:
            rest += len(x) + 1
            if x.endswith((".", "?", "!", ":")):
                break
        else:
            rest = 99
        if (not nxt or gap > 1.2 or w.endswith((".", "?", "!", ":")) or (len(text) + nxt_len > most and len(text) + rest > most + 16)
                or (w.endswith((",", ";")) and len(text) > most * 0.55)):
            stop = min(nxt[0] if nxt else end, end, t + 2.0)
            cues.append((cur[0][0], max(stop, t + 0.4), _tidy(text)))
            cur = []
    out = ["WEBVTT", ""]
    for k, (a, b, text) in enumerate(cues):
        if k + 1 < len(cues):
            b = min(b, cues[k + 1][0] - 0.01)
        out += [f"{_ts(a)} --> {_ts(b)}", text, ""]
    return "\n".join(out)


def _ts(s):
    s = max(s, 0)
    return f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{s % 60:06.3f}"


# ---- on Windows ---------------------------------------------------------------------------------------------------

def _wsl(p):
    p = str(Path(p).resolve()).replace("\\", "/")
    return f"/mnt/{p[0].lower()}{p[2:]}"


def make(vid, key, cache_dir, render_root="/home/h/slab_render"):
    """The video's .vtt in cache_dir, named by key (the render it belongs to), aligned in WSL the first time.
    None when it could not be made (no WSL, no render mirror, no narration found)."""
    out = Path(cache_dir) / f"{vid}-{key}.vtt"
    if out.exists():
        return out if out.stat().st_size > 20 else None
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = subprocess.run((["wsl"] if os.name == "nt" else []) + [PY, _wsl(__file__) if os.name == "nt" else __file__,
                           "--align", render_root, vid], capture_output=True, text=True, encoding="utf-8", timeout=1200)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0 or not r.stdout.startswith("WEBVTT"):
        sys.stderr.write(f"captions: {vid}: {r.stderr.strip()[-300:]}\n")
        return None
    for old in out.parent.glob(f"{vid}-*.vtt"):
        old.unlink()
    out.write_text(r.stdout, encoding="utf-8", newline="\n")
    return out if r.stdout.count("-->") else None


if __name__ == "__main__":
    if sys.argv[1] == "--align":
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
        print(align(sys.argv[2], sys.argv[3]))
    else:
        sys.path.insert(0, str(ROOT / "tools"))
        import catalog
        full = next(ROOT / v["src"][3:] for v in catalog.scan() if v["id"] == sys.argv[1])
        st = full.stat()
        print(make(sys.argv[1], f"{int(st.st_mtime)}-{st.st_size}", catalog.CACHE / "captions"))
