"""Reels: every scene of every explainer as a short clip in a vertical, swipe-to-scroll feed for phones, served by
catalog.py at /reels (linked from the catalogue's header). A video is an account (@folder, its paper's front page as
the avatar, the video's title as the name) and each scene is a reel that account posted. A reel is the scene's span
of the published mp4 (the small copy when there is one), played in place, so nothing is cut or stored apart from
small poster frames and one rewind copy per video (the picture backwards, for smooth hold-to-rewind) in .catalog/reels/.

Scene spans come from the render's list.txt in the WSL mirror, timed from each scene file's mp4 header. Captions are
the first sentence a scene's narration speaks; tapping one adds the scene class's docstring from <video>/*_vo.py
(search covers both).
The feed itself (For you, Latest, Liked, search, profiles) is all in PAGE; likes live in the phone's localStorage.
"""
import ast
import json
import os
import re
import subprocess
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".catalog" / "reels"
_spans, _caps, _lock = {}, {}, threading.Lock()
_ff = threading.Semaphore(2)                             # ffmpeg runs through WSL; a few at a time is plenty


def mp4_duration(path):
    """Seconds, from the mvhd box, walking the top-level boxes so only headers are read (mdat is skipped)."""
    try:
        with open(path, "rb") as f:
            while True:
                h = f.read(8)
                if len(h) < 8:
                    return 0.0
                size, kind = int.from_bytes(h[:4], "big"), h[4:]
                head = 8
                if size == 1:
                    size, head = int.from_bytes(f.read(8), "big"), 16
                if kind == b"moov":
                    d = f.read(size - head if size else 1 << 24)
                    i = d.find(b"mvhd")
                    if i < 0:
                        return 0.0
                    v = d[i + 4]
                    if v == 0:
                        ts, du = int.from_bytes(d[i + 16:i + 20], "big"), int.from_bytes(d[i + 20:i + 24], "big")
                    else:
                        ts, du = int.from_bytes(d[i + 24:i + 28], "big"), int.from_bytes(d[i + 28:i + 36], "big")
                    return du / ts if ts else 0.0
                if size == 0:
                    return 0.0
                f.seek(size - head, 1)
    except OSError:
        return 0.0


def spans(render_root, vid):
    """[(scene, start, end)] in seconds of the joined video, cached until the render's list.txt changes."""
    lst = Path(render_root) / vid / "list.txt"
    try:
        key = (vid, lst.stat().st_mtime)
    except OSError:
        return []
    with _lock:
        if key in _spans:
            return _spans[key]
    out, t = [], 0.0
    for line in lst.read_text().splitlines():
        m = re.match(r"file '/home/h/slab_render/(.+)'", line.strip())
        if m:
            d = mp4_duration(Path(render_root) / m.group(1))
            out.append((Path(m.group(1)).stem, round(t, 3), round(t + d, 3)))
            t += d
    with _lock:
        _spans[key] = out
    return out


def _say(text):
    """The first sentence a narration speaks, without its bookmarks."""
    s = " ".join(re.sub(r"<bookmark[^>]*/>", "", text).split())
    m = re.match(r"(.+?[.!?])(?:\s|$)", s)
    return (m.group(1) if m else s)[:220]


def captions(folder):
    """{scene class: (docstring, first narration sentence, all its narration)} from the video's *_vo.py, cached per
    file version."""
    py = next(iter(sorted(folder.glob("*_vo.py"))), None)
    if py is None:
        return {}
    key = (str(py), py.stat().st_mtime)
    with _lock:
        if key in _caps:
            return _caps[key]
    out = {}
    try:
        tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:
        tree = ast.Module(body=[], type_ignores=[])
    for c in tree.body:
        if not isinstance(c, ast.ClassDef):
            continue
        doc = " ".join((ast.get_docstring(c) or "").split())
        texts = [t for _, t in sorted(                   # ast.walk is breadth first: put them back in spoken order
            (n.lineno, kw.value.value) for n in ast.walk(c)
            if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "voiceover"
            for kw in n.keywords if kw.arg == "text" and isinstance(kw.value, ast.Constant)
            and isinstance(kw.value.value, str))]
        full = " ".join(re.sub(r"<bookmark[^>]*/>", "", " ".join(texts)).split())
        out[c.name] = (doc, _say(texts[0]) if texts else "", full)
    with _lock:
        _caps[key] = out
    return out


def nice(scene):
    """'ImagesHigh' -> 'Images high'; scene files named S03_Foo keep only Foo."""
    s = re.sub(r"^[Ss]\d+_?", "", scene)
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s).replace("_", " ").strip()
    return s[:1].upper() + s[1:].lower() if s else scene


def index(videos, render_root):
    """One account per video, newest first, each with its reels in order."""
    out = []
    for v in videos:
        folder = ROOT / v["id"]
        caps = captions(folder)
        reels = []
        for i, (scene, a, b) in enumerate(spans(render_root, v["id"])):
            if b - a < 1:
                continue
            doc, said, full = caps.get(scene, ("", "", ""))
            reels.append({"i": i, "scene": scene, "name": nice(scene), "a": a, "b": b, "cap": said or doc,
                          "doc": doc if said else "", "words": full.lower(), "thumb": f"/rthumb/{v['id']}/{i}.jpg?{int(v['mtime'])}"})
        if reels:
            out.append({"id": v["id"], "title": v["title"], "mtime": v["mtime"], "dur": v["dur"], "src": v["src"],
                        "small": v["small"], "avatar": f"/avatar/{v['id']}.jpg?{int(v['mtime'])}",
                        "rev": f"/rev/{v['id']}.mp4?{int(v['mtime'])}", "reels": reels})
    return out


def wsl_path(p):
    p = str(p).replace("\\", "/")
    return f"/mnt/{p[0].lower()}{p[2:]}"


def _ffmpeg(ffmpeg, args, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    with _ff:
        if out.exists():
            return out
        try:
            subprocess.run((["wsl"] if os.name == "nt" else []) + [ffmpeg, "-loglevel", "error", "-y"] + args +
                           [wsl_path(out)], timeout=60, capture_output=True)
        except (OSError, subprocess.TimeoutExpired):
            return None
    return out if out.exists() else None


def _full(vid):
    return next(iter((ROOT / vid).glob("*_narrated.mp4")), None)


def poster(ffmpeg, render_root, vid, i):
    """A frame a little into reel i (cut once per render, 480 px wide)."""
    full = _full(vid)
    sp = spans(render_root, vid)
    if full is None or not 0 <= i < len(sp):
        return None
    _, a, b = sp[i]
    out = CACHE / f"{vid}_{i}_{int(full.stat().st_mtime)}.jpg"
    if out.exists():
        return out
    t = a + min(4.0, (b - a) * 0.4)
    return _ffmpeg(ffmpeg, ["-ss", f"{t:.2f}", "-i", wsl_path(full), "-frames:v", "1", "-vf", "scale=480:-2",
                            "-q:v", "5"], out)


def avatar(ffmpeg, vid):
    """The top of the paper's front page (assets/front.png) as a square, else a square from the video's middle."""
    full = _full(vid)
    if full is None:
        return None
    front = ROOT / vid / "assets" / "front.png"
    out = CACHE / f"av_{vid}_{int(full.stat().st_mtime)}.jpg"
    if out.exists():
        return out
    if front.exists():
        args = ["-i", wsl_path(front), "-frames:v", "1", "-vf", "crop=iw*0.8:iw*0.8:iw*0.1:ih*0.03,scale=200:200"]
    else:
        args = ["-ss", "40", "-i", wsl_path(full), "-frames:v", "1", "-vf", "crop=ih:ih,scale=200:200"]
    return _ffmpeg(ffmpeg, args + ["-q:v", "4"], out)


_rev_busy, _rev_one = set(), threading.Lock()


def reverse(ffmpeg, vid, wait=False):
    """The rewind copy (tools/reels_reverse.sh: the picture backwards, 640 px, no sound), made once per render. Until
    it exists this starts it in the background and returns None, and the page rewinds by seeking instead."""
    full = _full(vid)
    if full is None:
        return None
    out = CACHE / f"rev_{vid}_{int(full.stat().st_mtime)}.mp4"
    if out.exists():
        return out
    if wait:
        _make_rev(ffmpeg, vid, full, out)
    else:
        threading.Thread(target=_make_rev, args=(ffmpeg, vid, full, out), daemon=True).start()
    return out if out.exists() else None


def _make_rev(ffmpeg, vid, full, out):
    """Build one rewind copy; a second request for the same video while it is being made does nothing."""
    with _lock:
        if vid in _rev_busy:
            return
        _rev_busy.add(vid)
    try:
        with _rev_one:                                   # one at a time: each runs ffmpeg flat out for ~30 s
            if out.exists():
                return
            out.parent.mkdir(parents=True, exist_ok=True)
            src = max(full.parent.glob("*small*.mp4"), key=lambda p: p.stat().st_mtime, default=full)
            script = Path(__file__).resolve().parent / "reels_reverse.sh"
            subprocess.run((["wsl"] if os.name == "nt" else []) + ["bash", wsl_path(script), ffmpeg, wsl_path(src),
                           wsl_path(out)], timeout=1800, capture_output=True)
    except (OSError, subprocess.TimeoutExpired):
        pass
    finally:
        with _lock:
            _rev_busy.discard(vid)


def warm(ffmpeg, render_root, accounts):
    """Cut every missing poster and avatar in the background, so profile grids fill in fast, then make the rewind
    copies; drop stale ones."""
    keep = set()
    for acc in accounts:
        if (p := avatar(ffmpeg, acc["id"])) is not None:
            keep.add(p.name)
        for r in acc["reels"]:
            if (p := poster(ffmpeg, render_root, acc["id"], r["i"])) is not None:
                keep.add(p.name)
    for acc in accounts:
        if (p := reverse(ffmpeg, acc["id"], wait=True)) is not None:
            keep.add(p.name)
    for f in [*CACHE.glob("*.jpg"), *CACHE.glob("rev_*.mp4")]:
        if f.name not in keep:
            f.unlink(missing_ok=True)


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#000"><meta name="apple-mobile-web-app-capable" content="yes">
<title>Reels</title>
<style>
:root{--bg:#000;--card:#121318;--line:#25272e;--text:#f1f1f1;--mute:#9a9ca3;--acc:#fe2c55;--acc2:#25f4ee}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;height:100%;background:var(--bg);color:var(--text);font:15px/1.35 system-ui,-apple-system,sans-serif;overflow:hidden}
button{font:inherit;color:inherit;background:none;border:0;padding:0;cursor:pointer}
#app{position:fixed;inset:0;max-width:520px;margin:auto;background:#000}
.view{position:absolute;inset:0 0 calc(54px + env(safe-area-inset-bottom));display:none}.view.on{display:block}
#nav{position:absolute;left:0;right:0;bottom:0;height:calc(54px + env(safe-area-inset-bottom));padding-bottom:env(safe-area-inset-bottom);
  display:flex;background:#000;border-top:1px solid #1c1d22;z-index:5}
#nav a{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--mute);text-decoration:none;font-size:11px;gap:2px}
#nav a.on{color:var(--text)}#nav svg{width:24px;height:24px}
/* feed */
#feed{height:100%;overflow-y:scroll;scroll-snap-type:y mandatory;overscroll-behavior:contain;scrollbar-width:none}
#feed::-webkit-scrollbar{display:none}
.slide{position:relative;height:100%;scroll-snap-align:start;scroll-snap-stop:always;overflow:hidden;background:#000}
.bg{position:absolute;inset:-30px;background-size:cover;background-position:center;filter:blur(26px) brightness(.45);transform:scale(1.1)}
.stage{position:absolute;left:0;right:0;top:max(80px,calc(42% - 28vw));aspect-ratio:16/9}
.stage img,.stage video{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:#000}
.stage video{opacity:0;transition:opacity .15s;z-index:1}.slide.ready .stage video{opacity:1}
.stage video.rv{z-index:2;opacity:0!important;transition:none}.stage video.rv.on{opacity:1!important}
.tap{position:absolute;inset:0;z-index:1;-webkit-user-select:none;user-select:none;-webkit-touch-callout:none;touch-action:pan-y}
.spd{position:absolute;top:calc(96px + env(safe-area-inset-top));left:50%;transform:translateX(-50%);z-index:3;display:none;
  background:#000a;border:1px solid #fff3;border-radius:16px;padding:5px 14px;font-weight:600;pointer-events:none;white-space:nowrap}
.slide.fast .spd,.slide.rew .spd{display:block}.slide.fast .spd::after{content:'2\00d7  \25b6\25b6'}.slide.rew .spd::after{content:'\25c0\25c0  Rewind'}
.side{position:absolute;right:8px;bottom:110px;display:flex;flex-direction:column;align-items:center;gap:18px;z-index:2}
.side button,.side a{display:flex;flex-direction:column;align-items:center;font-size:12px;gap:3px;color:#fff;text-decoration:none;text-shadow:0 1px 3px #000}
.side svg{width:34px;height:34px;filter:drop-shadow(0 1px 2px #000a)}
.av{width:46px;height:46px;border-radius:50%;border:2px solid #fff;background:#333 center/cover}
.liked svg{fill:var(--acc);stroke:var(--acc)}
.cap{position:absolute;left:12px;right:72px;bottom:28px;z-index:2;text-shadow:0 1px 3px #000}
.who{font-weight:700;font-size:16px;color:#fff;text-decoration:none}
.txt{margin-top:6px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}.txt.open{-webkit-line-clamp:unset}.doc{display:none;color:#bbb;font-size:13px}.txt.open .doc{display:block;margin-top:6px}
.meta{margin-top:7px;font-size:13px;color:#ddd;display:flex;gap:6px;align-items:center}
/* the progress bar: a thin line with a finger-sized grab strip; dragging it scrubs through the reel */
.prog{position:absolute;left:0;right:0;bottom:0;height:24px;z-index:3;touch-action:none;cursor:pointer}
.prog b{position:absolute;left:0;right:0;bottom:0;height:3px;background:#ffffff26;transition:height .1s}
.prog i{position:relative;display:block;height:100%;width:0;background:#fff}
.prog i::after{content:'';position:absolute;right:-7px;top:50%;width:14px;height:14px;margin-top:-7px;border-radius:50%;background:#fff;display:none}
.slide.drag .prog b{height:6px}.slide.drag .prog i::after{display:block}
.scrub{position:absolute;left:50%;bottom:64px;transform:translateX(-50%);z-index:3;font-size:28px;font-weight:700;text-shadow:0 1px 4px #000;
  display:none;pointer-events:none;white-space:nowrap}
.slide.drag .scrub{display:block}.slide.drag .cap,.slide.drag .side{opacity:0}
/* notes, shown like comments */
#sheet{position:absolute;inset:0;z-index:8;display:none}#sheet.on{display:block}
#sheet .dim{position:absolute;inset:0;background:#0007}
#sheet .pan{position:absolute;left:0;right:0;bottom:0;height:64%;background:#1a1b20;border-radius:14px 14px 0 0;display:flex;flex-direction:column;
  padding-bottom:env(safe-area-inset-bottom)}
#sheet .hd{text-align:center;font-weight:700;font-size:14px;padding:14px 44px 10px;position:relative}
#sheet .x{position:absolute;right:14px;top:6px;font-size:26px;color:#aaa}
#clist{flex:1;overflow-y:auto;padding:0 14px}
#clist h4{margin:12px 0 2px;font-size:12px;color:var(--mute);font-weight:600}
.cm{display:flex;gap:10px;padding:9px 0}.cm.done{opacity:.55}
.cm .ts{flex:none;align-self:flex-start;background:#2a2b31;color:var(--acc2);border-radius:10px;padding:2px 8px;font-size:12px;font-weight:600}
.cm .bd{flex:1;min-width:0}.cm .sn{font-size:12px;color:var(--mute)}.cm .st{color:#8bd17c;margin-left:6px}
.cm .tx{margin-top:2px;white-space:pre-wrap;overflow-wrap:anywhere}
#cform{display:flex;gap:8px;padding:10px 12px;border-top:1px solid #2a2b31}
#cin{flex:1;min-width:0;background:#2a2b31;border:0;border-radius:18px;color:var(--text);padding:9px 14px;font:16px system-ui,sans-serif;outline:none}
#cform button{color:var(--acc);font-weight:700;padding:0 6px}
.top{position:absolute;top:0;left:0;right:0;z-index:4;display:flex;justify-content:center;align-items:center;gap:18px;
  padding:calc(10px + env(safe-area-inset-top)) 12px 10px;background:linear-gradient(#0009,#0000);pointer-events:none}
.top>*{pointer-events:auto}.top a{color:#ffffffa8;text-decoration:none;font-weight:600;font-size:16px;padding-bottom:3px}
.top a.on{color:#fff;border-bottom:2px solid #fff}.top .back{position:absolute;left:12px;font-size:22px;color:#fff}
.top .ttl{font-weight:700}.top .auto{position:absolute;right:12px;font-size:12px;color:#fffc;border:1px solid #fff6;border-radius:12px;padding:2px 8px}
.top .auto.on{background:#fff;color:#000}
.pz{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);z-index:2;pointer-events:none;opacity:0;transition:opacity .15s}
.pz svg{width:72px;height:72px;fill:#fffb}.slide.paused .pz{opacity:1}
.heart{position:absolute;z-index:3;pointer-events:none;width:90px;height:90px;fill:var(--acc);animation:pop .7s forwards}
@keyframes pop{0%{transform:translate(-50%,-50%) scale(.3);opacity:0}25%{transform:translate(-50%,-50%) scale(1.1);opacity:1}
  100%{transform:translate(-50%,-90%) scale(1);opacity:0}}
#toast{position:fixed;left:50%;bottom:90px;transform:translateX(-50%);background:#fff;color:#000;border-radius:8px;padding:8px 14px;
  z-index:9;display:none;font-weight:600}
/* lists */
.page{height:100%;overflow-y:auto;padding:calc(10px + env(safe-area-inset-top)) 0 20px}
.bar{display:flex;align-items:center;gap:10px;padding:0 12px 10px}
.bar input{flex:1;background:#1e1f25;border:0;border-radius:8px;color:var(--text);padding:10px 12px;font:inherit;outline:none}
.bar .back{font-size:22px}
h3{font-size:14px;color:var(--mute);font-weight:600;margin:14px 12px 8px;text-transform:uppercase;letter-spacing:.04em}
.acc{display:flex;gap:12px;align-items:center;padding:8px 12px;color:var(--text);text-decoration:none}
.acc .av{width:54px;height:54px;border:0;flex:none}.acc b{display:block}.acc span{color:var(--mute);font-size:13px;display:block}
.acc .t{overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:2px}
.tile{position:relative;aspect-ratio:3/4;background:#111 center/cover;color:#fff;text-decoration:none;overflow:hidden}
.tile span{position:absolute;left:5px;bottom:4px;font-size:12px;font-weight:600;text-shadow:0 1px 3px #000}
.tile em{position:absolute;right:5px;top:4px;font-size:11px;font-style:normal;background:#000a;border-radius:4px;padding:0 5px}
.tile .nm{position:absolute;left:0;right:0;bottom:0;padding:18px 5px 4px;font-size:12px;background:linear-gradient(#0000,#000c);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.prof{text-align:center;padding:0 16px}.prof .av{width:96px;height:96px;margin:6px auto 10px;border:0}
.prof .h{font-weight:700;font-size:17px}.prof .n{color:#ddd;margin-top:6px}
.stats{display:flex;justify-content:center;gap:26px;margin:14px 0}.stats b{display:block;font-size:17px}.stats span{color:var(--mute);font-size:13px}
.btns{display:flex;gap:8px;justify-content:center;margin-bottom:14px}
.btns a{background:var(--acc);color:#fff;border-radius:6px;padding:9px 18px;text-decoration:none;font-weight:600}
.btns a.alt{background:#2a2b31}
.empty{color:var(--mute);padding:30px 16px;text-align:center}
</style></head><body><div id="app">
<div id="v-feed" class="view"><div id="feed"></div><div class="top" id="ftop"></div></div>
<div id="v-search" class="view"><div class="page"><div class="bar"><input id="q" type="search" placeholder="Search accounts and reels" autocomplete="off"></div><div id="sres"></div></div></div>
<div id="v-liked" class="view"><div class="page"><div class="bar"><b style="font-size:17px">Liked</b></div><div id="lres"></div></div></div>
<div id="v-prof" class="view"><div class="page" id="pres"></div></div>
<nav id="nav">
 <a href="#/" data-v="feed"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 3 2 11h3v9h5v-6h4v6h5v-9h3z"/></svg>Home</a>
 <a href="#/search" data-v="search"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></svg>Search</a>
 <a href="#/liked" data-v="liked"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.7 4.5c2.2 0 3.6 1.2 4.3 2.4h2c.7-1.2 2.1-2.4 4.3-2.4 3.7 0 5.8 3.9 4.3 7.3C19.5 16.4 12 21 12 21z"/></svg>Liked</a>
 <a href="/" data-v="cat"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8"/></svg>Catalogue</a>
</nav>
<div id="sheet"><div class="dim"></div><div class="pan"><div class="hd"><span id="shd"></span><button class="x" aria-label="Close">&times;</button></div>
 <div id="clist"></div><form id="cform"><input id="cin" enterkeyhint="send" autocomplete="off"><button>Post</button></form></div></div>
</div><div id="toast"></div>
<script>
const $=s=>document.querySelector(s),esc=s=>String(s).replace(/[&<>"']/g,c=>'&#'+c.charCodeAt(0)+';');
const fmt=s=>{s=Math.max(0,Math.round(s));return Math.floor(s/60)+':'+String(s%60).padStart(2,'0')};
const ls={get(k,d){try{const v=localStorage.getItem(k);return v==null?d:JSON.parse(v)}catch(e){return d}},
  set(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}};
let accs=[],by={},all=[],likes=new Set(ls.get('reels:likes',[])),auto=ls.get('reels:auto',false);
const key=r=>r.vid+':'+r.scene;
const ICON={heart:'<svg viewBox="0 0 24 24" fill="#fff" stroke="#fff" stroke-width="1"><path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.7 4.5c2.2 0 3.6 1.2 4.3 2.4h2c.7-1.2 2.1-2.4 4.3-2.4 3.7 0 5.8 3.9 4.3 7.3C19.5 16.4 12 21 12 21z"/></svg>',
  note:'<svg viewBox="0 0 24 24" fill="#fff"><path d="M4 4h16v12H8l-4 4z"/></svg>',
  full:'<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.2"><rect x="3" y="5" width="18" height="12" rx="2"/><path d="m10 8.5 4.5 2.5-4.5 2.5z" fill="#fff"/></svg>',
  play:'<svg viewBox="0 0 24 24"><path d="M7 4v16l13-8z"/></svg>'};
// one <video> for the whole page, moved into whichever reel is on screen: a phone unlocks sound once for it, and
// only one stream is ever loading
const V=document.createElement('video');V.playsInline=true;V.muted=true;V.preload='auto';
for(const k of ['playsinline','webkit-playsinline','muted'])V.setAttribute(k,'');
// the rewind copy: the same picture played backwards (made by the server, tools/reels_reverse.sh), shown over V and
// played forwards at 3x while the left half is held; a moment t of the video is revD - t in it
const R=document.createElement('video');R.className='rv';R.playsInline=true;R.muted=true;R.preload='auto';
for(const k of ['playsinline','webkit-playsinline','muted'])R.setAttribute(k,'');
R.onerror=()=>{R.dataset.src=''};                       // not made yet: ask again on the next reel
let revD=0;
// sound is on from the start; a browser that refuses to autoplay with sound gets the reel silent, and the first tap
// turns the sound on for the rest of the visit
let list=[],mode='',cur=null,curSl=null,userPaused=false,soundOn=true,jumpT=null;
// the reel on screen: the observer, and the scroll position once scrolling stops (a backgrounded tab may skip the observer)
function settle(){const f=$('#feed'),s=f.children[Math.round(f.scrollTop/(f.clientHeight||1))];if(s)activate(s)}
$('#feed').addEventListener('scroll',()=>{clearTimeout(settle._t);settle._t=setTimeout(settle,150)},{passive:true});
const io=new IntersectionObserver(es=>{for(const e of es)if(e.isIntersecting)activate(e.target)},{root:$('#feed'),threshold:.6});
function slide(r,k){const a=by[r.vid],s=document.createElement('section');s.className='slide';s._r=r;s._k=k;
  s.innerHTML=`<div class="bg"></div><div class="stage"><img alt=""></div>
   <div class="tap"></div><div class="pz">${ICON.play}</div><div class="spd"></div>
   <div class="side"><a class="av" href="#/@${encodeURIComponent(r.vid)}" style="background-image:url('${a.avatar}')" aria-label="Account"></a>
    <button class="lk${likes.has(key(r))?' liked':''}">${ICON.heart}<span>Like</span></button>
    <button class="nt">${ICON.note}<span>Note</span></button>
    <a class="fl" href="#">${ICON.full}<span>Full</span></a></div>
   <div class="cap"><a class="who" href="#/@${encodeURIComponent(r.vid)}">@${esc(r.vid)}</a>
    <div class="txt">${esc(r.cap||r.name)}${r.doc?`<span class="doc"> ${esc(r.doc)}</span>`:''}</div>
    <div class="meta">&#9835; ${esc(r.name)} &middot; ${r.n}/${a.reels.length} &middot; <span class="tm">0:00</span> / ${fmt(r.b-r.a)}</div></div>
   <div class="prog"><b><i></i></b></div><div class="scrub"></div>`;
  if(notes[r.vid])noteCount(s);
  s.querySelector('.txt').onclick=e=>e.currentTarget.classList.toggle('open');
  // drag the bar to a moment of the reel: the picture follows the finger, and play carries on from there on release
  const pg=s.querySelector('.prog');
  const scrubTo=e=>{const rc=pg.getBoundingClientRect(),f=Math.max(0,Math.min(1,(e.clientX-rc.left)/rc.width)),t=r.a+f*(r.b-r.a);
    s._drag.t=Math.min(t,r.b-.1);pg.querySelector('i').style.width=f*100+'%';
    s.querySelector('.scrub').textContent=fmt(t-r.a)+' / '+fmt(r.b-r.a);s.querySelector('.tm').textContent=fmt(t-r.a);
    if(!V.seeking)V.currentTime=s._drag.t};
  pg.addEventListener('pointerdown',e=>{if(s!==curSl)return;e.preventDefault();e.stopPropagation();pg.setPointerCapture(e.pointerId);
    s._drag={was:V.paused,t:V.currentTime};V.pause();s.classList.add('drag');scrubTo(e)});
  pg.addEventListener('pointermove',e=>{if(s._drag)scrubTo(e)});
  const drop=()=>{const d=s._drag;if(!d)return;s._drag=null;s.classList.remove('drag');V.currentTime=d.t;
    if(!d.was&&!userPaused)V.play().catch(()=>{})};
  pg.addEventListener('pointerup',drop);pg.addEventListener('pointercancel',drop);pg.onclick=e=>e.stopPropagation();
  s.querySelector('.lk').onclick=()=>like(s,false);
  s.querySelector('.nt').onclick=()=>note(s);
  s.querySelector('.fl').onclick=e=>{e.preventDefault();location.href='/#v='+encodeURIComponent(r.vid)+'&t='+Math.floor(s===curSl?V.currentTime:r.a)};
  let last=0;
  // act on the tap itself, never after a timer: a phone only lets play() and sound through inside the tap's handler.
  // A second tap within 300 ms undoes the first one's pause or play and likes the reel instead
  let toggled=false,hold=null,held=false;
  const tp=s.querySelector('.tap');
  tp.onclick=e=>{if(held){held=false;return}const now=Date.now(),dbl=now-last<300;last=dbl?0:now;
    if(dbl){if(toggled)toggle(s);toggled=false;like(s,true,e);return}
    if(!soundOn){soundOn=true;V.muted=false}           // a reel left silent by the browser gets its sound with the first tap
    toggled=true;toggle(s)};
  // press and hold: the right half plays at 2x, the left half rewinds, until the finger lifts (a swipe cancels it)
  tp.addEventListener('pointerdown',e=>{held=false;if(s!==curSl)return;
    const right=e.clientX-s.getBoundingClientRect().left>s.clientWidth/2;
    hold={x:e.clientX,y:e.clientY,t:setTimeout(()=>{held=true;startHold(s,right)},350)}});
  tp.addEventListener('pointermove',e=>{if(hold&&!held&&Math.hypot(e.clientX-hold.x,e.clientY-hold.y)>12){clearTimeout(hold.t);hold=null}});
  for(const k of ['pointerup','pointercancel','pointerleave'])tp.addEventListener(k,()=>{if(hold){clearTimeout(hold.t);hold=null}if(held)stopHold(s)});
  tp.oncontextmenu=e=>e.preventDefault();
  return s}
let rew=null,holdPaused=false;
function startHold(s,right){holdPaused=V.paused;s.classList.add(right?'fast':'rew');
  if(right){V.playbackRate=2;V.play().catch(()=>{})}
  else{V.pause();const D=R.duration;
    if(R.readyState>=2&&isFinite(D)&&Math.abs(D-V.duration)<2){revD=D;R.currentTime=Math.max(0,D-V.currentTime);
      R.addEventListener('seeked',()=>{if(!s.classList.contains('rew'))return;R.classList.add('on');R.playbackRate=3;R.play().catch(()=>{})},{once:true})}
    else{revD=0;if(R.readyState<1)R.play().then(()=>R.pause()).catch(()=>{});   // fallback: step back by seeking
      rew=setInterval(()=>{if(!V.seeking&&cur)V.currentTime=Math.max(cur.a,V.currentTime-.6)},100)}}}
function stopHold(s){if(!s.classList.contains('fast')&&!s.classList.contains('rew'))return;
  const back=s.classList.contains('rew')&&revD;s.classList.remove('fast','rew');V.playbackRate=1;clearInterval(rew);rew=null;
  if(back){V.currentTime=Math.max(cur.a,revD-R.currentTime);R.pause();revD=0;   // keep the rewind frame up until V is there
    V.addEventListener('seeked',()=>R.classList.remove('on'),{once:true})}
  holdPaused?V.pause():V.play().catch(()=>{})}
// posters only for the reel on screen and its neighbours: a phone opens few connections to the server, and a
// screenful of poster requests would hold up the video itself
function hydrate(s){if(s&&!s._h){s._h=1;s.querySelector('.bg').style.backgroundImage=`url('${s._r.thumb}')`;s.querySelector('.stage img').src=s._r.thumb}}
function toggle(s){if(V.paused){userPaused=false;s.classList.remove('blocked');V.play().catch(()=>{})}else{userPaused=true;V.pause()}
  s.classList.toggle('paused',userPaused)}
// start the reel: muted autoplay is allowed everywhere; if even that is refused, show the play button and wait for a tap
function start(){const s=curSl;V.play().then(()=>s&&s.classList.remove('blocked')).catch(()=>{
  if(!V.muted){V.muted=true;soundOn=false;return start()}
  if(s===curSl){s.classList.add('paused','blocked')}})}
function like(s,burst,e){const k=key(s._r),b=s.querySelector('.lk');
  if(burst){const h=document.createElementNS('http://www.w3.org/2000/svg','svg');h.setAttribute('viewBox','0 0 24 24');h.setAttribute('class','heart');
    h.innerHTML=ICON.heart.replace(/^<svg[^>]*>|<\/svg>$/g,'');h.style.left=e.clientX-s.getBoundingClientRect().left+'px';
    h.style.top=e.clientY-s.getBoundingClientRect().top+'px';s.append(h);setTimeout(()=>h.remove(),800);likes.add(k)}
  else likes.has(k)?likes.delete(k):likes.add(k);
  b.classList.toggle('liked',likes.has(k));ls.set('reels:likes',[...likes])}
// notes read like comments: the sheet lists this reel's notes, then the rest of the video's, each with the moment it
// is about (tap it to go there), and a box to add one at the moment the reel was paused on
const notes={};      // video id -> its notes from feedback.json, fetched when one of its reels first comes up
const inReel=(n,r)=>n.t>=r.a&&n.t<r.b;
async function loadNotes(vid){try{notes[vid]=await (await fetch('/api/notes?id='+encodeURIComponent(vid))).json()}catch(e){notes[vid]=notes[vid]||[]}
  document.querySelectorAll('.slide').forEach(s=>{if(s._r.vid===vid)noteCount(s)})}
function noteCount(s){const k=(notes[s._r.vid]||[]).filter(n=>inReel(n,s._r)).length;s.querySelector('.nt span').textContent=k||'Notes'}
let sheetSl=null,sheetT=0,sheetWas=false;
async function note(s){const r=s._r;sheetSl=s;sheetT=s===curSl?V.currentTime:r.a;sheetWas=V.paused;if(s===curSl)V.pause();
  $('#cin').placeholder='Add a note at '+fmt(sheetT-r.a)+'…';$('#sheet').classList.add('on');renderSheet();
  await loadNotes(r.vid);if(sheetSl===s)renderSheet()}
function renderSheet(){const r=sheetSl._r,a=by[r.vid],ns=(notes[r.vid]||[]).slice().sort((x,y)=>x.t-y.t);
  const reelOf=t=>a.reels.find(q=>t>=q.a&&t<q.b)||a.reels[a.reels.length-1];
  const row=n=>{const q=reelOf(n.t),done=n.status!=='open';return `<div class="cm${done?' done':''}">
     <button class="ts" data-n="${q.n-1}" data-t="${n.t}">${fmt(n.t-q.a)}</button>
     <div class="bd"><div class="sn">${esc(q.name)}${done?'<span class="st">&#10003; resolved</span>':''}</div><div class="tx">${esc(n.text)}</div>
     ${done&&n.resolution?`<div class="sn">&rarr; ${esc(n.resolution)}</div>`:''}</div></div>`};
  const mine=ns.filter(n=>inReel(n,r)),rest=ns.filter(n=>!inReel(n,r));
  $('#shd').textContent=ns.length+(ns.length===1?' note':' notes');
  $('#clist').innerHTML=(mine.length?mine.map(row).join(''):'<div class="empty" style="padding:18px">No notes on this reel yet.</div>')+
    (rest.length?`<h4>Elsewhere in @${esc(r.vid)}</h4>`+rest.map(row).join(''):'')}
function closeSheet(jump){if(!sheetSl)return;const s=sheetSl;sheetSl=null;$('#sheet').classList.remove('on');$('#cin').blur();
  if(!jump&&s===curSl&&!sheetWas&&!userPaused)V.play().catch(()=>{})}
$('#sheet .dim').onclick=$('#sheet .x').onclick=()=>closeSheet();
$('#clist').onclick=e=>{const b=e.target.closest('.ts');if(!b)return;const t=+b.dataset.t,s=sheetSl;closeSheet(true);
  if(s===curSl&&inReel({t},cur)){V.currentTime=t;userPaused=false;s.classList.remove('paused');V.play().catch(()=>{})}
  else{jumpT=t;setTimeout(()=>{jumpT=null},3000);location.hash='#/@'+encodeURIComponent(s._r.vid)+'/'+b.dataset.n}};
$('#cform').onsubmit=async e=>{e.preventDefault();const s=sheetSl,text=$('#cin').value.trim();if(!s||!text)return;
  const ok=await fetch('/api/notes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:s._r.vid,t:sheetT,text})}).then(x=>x.ok).catch(()=>false);
  if(!ok)return toast('Could not save the note');$('#cin').value='';await loadNotes(s._r.vid);if(sheetSl===s)renderSheet()};
function toast(t){const e=$('#toast');e.textContent=t;e.style.display='block';clearTimeout(e._t);e._t=setTimeout(()=>e.style.display='none',1600)}
function activate(s){if(curSl===s)return;if(curSl){curSl.classList.remove('ready','paused')}curSl=s;cur=s._r;userPaused=false;
  const a=by[cur.vid],src=a.small||a.src;s.querySelector('.stage').prepend(V);
  R.classList.remove('on');revD=0;s.querySelector('.stage').append(R);if(R.dataset.src!==a.rev){R.dataset.src=a.rev;R.src=a.rev;R.load()}
  let n=s;hydrate(s);for(let i=0;i<3&&n;i++){n=n.nextElementSibling;hydrate(n)}hydrate(s.previousElementSibling);
  // a new file: start it at once (an iPhone loads nothing until play() is called), silent until it has jumped to
  // the scene, then seek when its length is known
  // a note's moment to start at: kept until its reel comes up, since the rebuilt feed may pass the first reel on the way
  const t0=jumpT!=null&&inReel({t:jumpT},cur)?jumpT:cur.a+.01;if(t0===jumpT)jumpT=null;
  if(notes[cur.vid])noteCount(s);else loadNotes(cur.vid);
  if(V.dataset.src!==src){V.dataset.src=src;V.src=src;V.muted=true;V.load();
    V.addEventListener('loadedmetadata',()=>{V.currentTime=t0},{once:true});start()}
  else{V.currentTime=t0;start()}
  ls.set('reels:pos:'+mode,s._k);if(s._k>list.length-4&&mode==='foryou')more()}
function inScene(){return cur&&V.currentTime>=cur.a-.3&&V.currentTime<=cur.b}
// once at the scene, turn the sound on; a browser that will not play with sound without a tap pauses or refuses,
// and the reel then carries on silent
V.addEventListener('seeked',()=>{const d=curSl&&curSl._drag;if(d&&Math.abs(V.currentTime-d.t)>.15)V.currentTime=d.t;   // catch up with the finger
  if(!curSl||!inScene())return;curSl.classList.add('ready');
  if(V.muted&&soundOn){V.muted=false;if(!V.paused)V.play().catch(()=>{V.muted=true;soundOn=false;V.play().catch(()=>{})})}});
V.addEventListener('playing',()=>{if(curSl&&inScene())curSl.classList.add('ready')});
// keep the clip inside its scene: every frame while visible, and on timeupdate as a backstop
function shown(t){const e=curSl.querySelector('.tm'),v=fmt(Math.min(cur.b,Math.max(cur.a,t))-cur.a);if(e.textContent!==v)e.textContent=v;
  curSl.querySelector('.prog i').style.width=Math.max(0,Math.min(100,100*(t-cur.a)/(cur.b-cur.a)))+'%'}
function check(){
  if(curSl&&curSl._drag)return;                                                              // the finger has the bar
  if(revD&&cur&&curSl&&R.classList.contains('on')){const t=revD-R.currentTime;if(t<=cur.a)R.pause();   // rewinding: stop at the scene's start
    shown(t);return}
  if(cur&&curSl&&!V.seeking&&V.readyState>1){const t=V.currentTime;
    if(t>=cur.b-.06||t<cur.a-1){if(auto&&t>=cur.b-.06&&curSl.nextElementSibling){V.pause();curSl.nextElementSibling.scrollIntoView({behavior:'smooth'})}else V.currentTime=cur.a}
    shown(t)}}
V.addEventListener('timeupdate',check);(function tick(){check();requestAnimationFrame(tick)})();
function shuffled(){const a=all.slice();for(let i=a.length-1;i>0;i--){const j=Math.random()*(i+1)|0;[a[i],a[j]]=[a[j],a[i]]}return a}
function more(){const add=shuffled(),f=$('#feed');add.forEach(r=>{const s=slide(r,list.length);list.push(r);f.append(s);io.observe(s)})}
function showFeed(m,items,start,top){if(mode!==m||!list.length||m.startsWith('@')||m==='liked'){mode=m;list=items;curSl=null;cur=null;
    const f=$('#feed');io.disconnect();f.replaceChildren(...list.map((r,k)=>slide(r,k)));f.querySelectorAll('.slide').forEach(s=>io.observe(s));
    setTimeout(()=>{f.scrollTop=(start||0)*f.clientHeight;settle()})}
  else if(curSl&&!userPaused)V.play().catch(()=>{});
  $('#ftop').innerHTML=top;const au=$('#ftop .auto');if(au)au.onclick=()=>{auto=!auto;ls.set('reels:auto',auto);au.classList.toggle('on',auto)}}
const autoBtn=()=>`<button class="auto${auto?' on':''}">Auto &darr;</button>`;
function tile(r,href,label){return `<a class="tile" href="${href}" style="background-image:url('${r.thumb}')"><em>${fmt(r.b-r.a)}</em><div class="nm">${label}</div></a>`}
function accRow(a){return `<a class="acc" href="#/@${encodeURIComponent(a.id)}"><div class="av" style="background-image:url('${a.avatar}')"></div>
  <div><b>@${esc(a.id)}</b><span class="t">${esc(a.title)}</span><span>${a.reels.length} reels &middot; ${fmt(a.dur)}</span></div></a>`}
function search(){const q=$('#q').value.trim().toLowerCase(),hit=s=>!q||String(s).toLowerCase().includes(q);
  const as=accs.filter(a=>hit(a.id)||hit(a.title)),rs=q?all.filter(r=>hit(r.name)||hit(r.cap)||hit(r.doc)||hit(r.words)||hit(r.vid)):[];
  $('#sres').innerHTML=(as.length?'<h3>Accounts</h3>'+as.map(accRow).join(''):'')+
    (rs.length?'<h3>Reels</h3><div class="grid">'+rs.slice(0,90).map(r=>tile(r,'#/@'+encodeURIComponent(r.vid)+'/'+(r.n-1),esc(r.name))).join('')+'</div>':'')+
    (!as.length&&!rs.length?'<div class="empty">Nothing matches.</div>':'')}
function liked(k){const rs=all.filter(r=>likes.has(key(r)));
  if(k!=null&&rs.length)return showFeed('liked',rs,Math.min(k,rs.length-1),`<a class="back" href="#/liked">&larr;</a><span class="ttl">Liked</span>${autoBtn()}`);
  $('#lres').innerHTML=rs.length?'<div class="grid">'+rs.map((r,k)=>tile(r,'#/liked/'+k,esc(r.name))).join('')+'</div>':'<div class="empty">Double-tap a reel to like it.</div>'}
function profile(a){const tot=a.reels.reduce((s,r)=>s+r.b-r.a,0);
  $('#pres').innerHTML=`<div class="bar"><a class="back" href="javascript:history.back()" style="color:#fff;text-decoration:none">&larr;</a><b>@${esc(a.id)}</b></div>
   <div class="prof"><div class="av" style="background-image:url('${a.avatar}')"></div><div class="h">@${esc(a.id)}</div><div class="n">${esc(a.title)}</div>
   <div class="stats"><div><b>${a.reels.length}</b><span>Reels</span></div><div><b>${fmt(tot)}</b><span>Length</span></div>
    <div><b>${new Date(a.mtime*1000).toLocaleDateString()}</b><span>Posted</span></div></div>
   <div class="btns"><a href="#/@${encodeURIComponent(a.id)}/0">Play all</a><a class="alt" href="/#v=${encodeURIComponent(a.id)}&t=0">Full video</a></div></div>
   <div class="grid">${a.reels.map(r=>tile(r,'#/@'+encodeURIComponent(a.id)+'/'+(r.n-1),r.n+' &middot; '+esc(r.name))).join('')}</div>`;
  $('#pres').scrollTop=0}
function show(v){document.querySelectorAll('.view').forEach(e=>e.classList.toggle('on',e.id==='v-'+v));
  closeSheet(true);if(v!=='feed'){V.pause()}}
function route(){const h=decodeURIComponent(location.hash.slice(1)||'/');let m,nav='feed';
  if(h==='/'||h==='/latest'){const lat=h==='/latest';show('feed');
    const items=lat?accs.flatMap(a=>a.reels.map(r=>r)):null;
    showFeed(lat?'latest':'foryou',lat?items:shuffled(),lat?ls.get('reels:pos:latest',0):0,
      `<a href="#/" class="${lat?'':'on'}">For you</a><a href="#/latest" class="${lat?'on':''}">Latest</a>${autoBtn()}`)}
  else if(h.startsWith('/search')){show('search');nav='search';search();}
  else if((m=h.match(/^\/liked(?:\/(\d+))?$/))){nav='liked';if(m[1]!=null){show('feed');liked(+m[1])}else{show('liked');liked()}}
  else if((m=h.match(/^\/@([^/]+)(?:\/(\d+))?$/))&&by[m[1]]){const a=by[m[1]];nav='';
    if(m[2]!=null){show('feed');showFeed('@'+a.id,a.reels,Math.min(+m[2],a.reels.length-1),
      `<a class="back" href="#/@${encodeURIComponent(a.id)}">&larr;</a><span class="ttl">@${esc(a.id)}</span>${autoBtn()}`)}
    else{show('prof');profile(a)}}
  else{location.hash='#/';return}
  document.querySelectorAll('#nav a').forEach(e=>e.classList.toggle('on',e.dataset.v===nav))}
$('#q').oninput=search;window.onhashchange=route;
document.addEventListener('visibilitychange',()=>{if(document.hidden)V.pause()});
fetch('/api/reels').then(r=>r.json()).then(d=>{accs=d;by=Object.fromEntries(d.map(a=>[a.id,a]));
  all=d.flatMap(a=>a.reels.map((r,k)=>Object.assign(r,{vid:a.id,n:k+1})));route()});
</script></body></html>"""
