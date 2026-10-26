"""Reels: every scene of every explainer as a short clip in a vertical, swipe-to-scroll feed for phones, served by
catalog.py at /reels (linked from the catalogue's header). A video is an account (@folder, its paper's front page as
the avatar, the video's title as the name) and each scene is a reel that account posted. A reel is the scene's span
of the published mp4 (the small copy when there is one), played in place, so nothing is cut or stored apart from
small poster frames in .catalog/reels/.

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
                        "small": v["small"], "avatar": f"/avatar/{v['id']}.jpg?{int(v['mtime'])}", "reels": reels})
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


def warm(ffmpeg, render_root, accounts):
    """Cut every missing poster and avatar in the background, so profile grids fill in fast; drop stale ones."""
    keep = set()
    for acc in accounts:
        if (p := avatar(ffmpeg, acc["id"])) is not None:
            keep.add(p.name)
        for r in acc["reels"]:
            if (p := poster(ffmpeg, render_root, acc["id"], r["i"])) is not None:
                keep.add(p.name)
    for f in CACHE.glob("*.jpg"):
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
.stage video{opacity:0;transition:opacity .15s}.slide.ready .stage video{opacity:1}
.tap{position:absolute;inset:0;z-index:1}
.side{position:absolute;right:8px;bottom:110px;display:flex;flex-direction:column;align-items:center;gap:18px;z-index:2}
.side button,.side a{display:flex;flex-direction:column;align-items:center;font-size:12px;gap:3px;color:#fff;text-decoration:none;text-shadow:0 1px 3px #000}
.side svg{width:34px;height:34px;filter:drop-shadow(0 1px 2px #000a)}
.av{width:46px;height:46px;border-radius:50%;border:2px solid #fff;background:#333 center/cover}
.liked svg{fill:var(--acc);stroke:var(--acc)}
.cap{position:absolute;left:12px;right:72px;bottom:22px;z-index:2;text-shadow:0 1px 3px #000}
.who{font-weight:700;font-size:16px;color:#fff;text-decoration:none}
.txt{margin-top:6px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}.txt.open{-webkit-line-clamp:unset}.doc{display:none;color:#bbb;font-size:13px}.txt.open .doc{display:block;margin-top:6px}
.meta{margin-top:7px;font-size:13px;color:#ddd;display:flex;gap:6px;align-items:center}
.prog{position:absolute;left:0;right:0;bottom:0;height:3px;background:#ffffff26;z-index:2}.prog i{display:block;height:100%;width:0;background:#fff}
.top{position:absolute;top:0;left:0;right:0;z-index:4;display:flex;justify-content:center;align-items:center;gap:18px;
  padding:calc(10px + env(safe-area-inset-top)) 12px 10px;background:linear-gradient(#0009,#0000);pointer-events:none}
.top>*{pointer-events:auto}.top a{color:#ffffffa8;text-decoration:none;font-weight:600;font-size:16px;padding-bottom:3px}
.top a.on{color:#fff;border-bottom:2px solid #fff}.top .back{position:absolute;left:12px;font-size:22px;color:#fff}
.top .ttl{font-weight:700}.top .auto{position:absolute;right:12px;font-size:12px;color:#fffc;border:1px solid #fff6;border-radius:12px;padding:2px 8px}
.top .auto.on{background:#fff;color:#000}
#hint{position:absolute;left:50%;top:calc(58px + env(safe-area-inset-top));transform:translateX(-50%);z-index:4;background:#000a;
  border:1px solid #fff3;border-radius:16px;padding:5px 12px;font-size:13px;display:none}
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
<div id="v-feed" class="view"><div id="feed"></div><div class="top" id="ftop"></div><div id="hint">Tap for sound</div></div>
<div id="v-search" class="view"><div class="page"><div class="bar"><input id="q" type="search" placeholder="Search accounts and reels" autocomplete="off"></div><div id="sres"></div></div></div>
<div id="v-liked" class="view"><div class="page"><div class="bar"><b style="font-size:17px">Liked</b></div><div id="lres"></div></div></div>
<div id="v-prof" class="view"><div class="page" id="pres"></div></div>
<nav id="nav">
 <a href="#/" data-v="feed"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 3 2 11h3v9h5v-6h4v6h5v-9h3z"/></svg>Home</a>
 <a href="#/search" data-v="search"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></svg>Search</a>
 <a href="#/liked" data-v="liked"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.7 4.5c2.2 0 3.6 1.2 4.3 2.4h2c.7-1.2 2.1-2.4 4.3-2.4 3.7 0 5.8 3.9 4.3 7.3C19.5 16.4 12 21 12 21z"/></svg>Liked</a>
 <a href="/" data-v="cat"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8"/></svg>Catalogue</a>
</nav></div><div id="toast"></div>
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
const V=document.createElement('video');V.playsInline=true;V.setAttribute('playsinline','');V.muted=true;V.preload='auto';
let list=[],mode='',cur=null,curSl=null,userPaused=false,soundOn=false;
// the reel on screen: the observer, and the scroll position once scrolling stops (a backgrounded tab may skip the observer)
function settle(){const f=$('#feed'),s=f.children[Math.round(f.scrollTop/(f.clientHeight||1))];if(s)activate(s)}
$('#feed').addEventListener('scroll',()=>{clearTimeout(settle._t);settle._t=setTimeout(settle,150)},{passive:true});
const io=new IntersectionObserver(es=>{for(const e of es)if(e.isIntersecting)activate(e.target)},{root:$('#feed'),threshold:.6});
function slide(r,k){const a=by[r.vid],s=document.createElement('section');s.className='slide';s._r=r;s._k=k;
  s.innerHTML=`<div class="bg"></div><div class="stage"><img alt=""></div>
   <div class="tap"></div><div class="pz">${ICON.play}</div>
   <div class="side"><a class="av" href="#/@${encodeURIComponent(r.vid)}" style="background-image:url('${a.avatar}')" aria-label="Account"></a>
    <button class="lk${likes.has(key(r))?' liked':''}">${ICON.heart}<span>Like</span></button>
    <button class="nt">${ICON.note}<span>Note</span></button>
    <a class="fl" href="#">${ICON.full}<span>Full</span></a></div>
   <div class="cap"><a class="who" href="#/@${encodeURIComponent(r.vid)}">@${esc(r.vid)}</a>
    <div class="txt">${esc(r.cap||r.name)}${r.doc?`<span class="doc"> ${esc(r.doc)}</span>`:''}</div>
    <div class="meta">&#9835; ${esc(r.name)} &middot; ${r.n}/${a.reels.length} &middot; ${fmt(r.b-r.a)}</div></div><div class="prog"><i></i></div>`;
  s.querySelector('.txt').onclick=e=>e.currentTarget.classList.toggle('open');
  s.querySelector('.lk').onclick=()=>like(s,false);
  s.querySelector('.nt').onclick=()=>note(s);
  s.querySelector('.fl').onclick=e=>{e.preventDefault();location.href='/#v='+encodeURIComponent(r.vid)+'&t='+Math.floor(s===curSl?V.currentTime:r.a)};
  let last=0,timer=null;
  s.querySelector('.tap').onclick=e=>{const now=Date.now();
    if(now-last<300){clearTimeout(timer);last=0;like(s,true,e);return}last=now;
    timer=setTimeout(()=>{if(!soundOn){unmute();return}userPaused=!V.paused;userPaused?V.pause():V.play().catch(()=>{});s.classList.toggle('paused',userPaused)},300)};
  return s}
// posters only for the reel on screen and its neighbours: a phone opens few connections to the server, and a
// screenful of poster requests would hold up the video itself
function hydrate(s){if(s&&!s._h){s._h=1;s.querySelector('.bg').style.backgroundImage=`url('${s._r.thumb}')`;s.querySelector('.stage img').src=s._r.thumb}}
function unmute(){soundOn=true;V.muted=false;$('#hint').style.display='none';V.play().catch(()=>{})}
function like(s,burst,e){const k=key(s._r),b=s.querySelector('.lk');
  if(burst){const h=document.createElementNS('http://www.w3.org/2000/svg','svg');h.setAttribute('viewBox','0 0 24 24');h.setAttribute('class','heart');
    h.innerHTML=ICON.heart.replace(/^<svg[^>]*>|<\/svg>$/g,'');h.style.left=e.clientX-s.getBoundingClientRect().left+'px';
    h.style.top=e.clientY-s.getBoundingClientRect().top+'px';s.append(h);setTimeout(()=>h.remove(),800);likes.add(k)}
  else likes.has(k)?likes.delete(k):likes.add(k);
  b.classList.toggle('liked',likes.has(k));ls.set('reels:likes',[...likes])}
async function note(s){const r=s._r,t=s===curSl?V.currentTime:r.a;V.pause();
  const text=prompt('Note at '+fmt(t)+' ('+r.name+')');if(!userPaused)V.play().catch(()=>{});if(!text||!text.trim())return;
  const ok=await fetch('/api/notes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:r.vid,t,text})}).then(x=>x.ok).catch(()=>false);
  toast(ok?'Note saved':'Could not save the note')}
function toast(t){const e=$('#toast');e.textContent=t;e.style.display='block';clearTimeout(e._t);e._t=setTimeout(()=>e.style.display='none',1600)}
function activate(s){if(curSl===s)return;if(curSl){curSl.classList.remove('ready','paused')}curSl=s;cur=s._r;userPaused=false;
  const a=by[cur.vid],src=a.small||a.src;s.querySelector('.stage').prepend(V);
  let n=s;hydrate(s);for(let i=0;i<3&&n;i++){n=n.nextElementSibling;hydrate(n)}hydrate(s.previousElementSibling);
  const go=()=>{V.currentTime=cur.a+.01;V.play().catch(()=>{if(!V.muted){V.muted=true;soundOn=false;$('#hint').style.display='block';V.play().catch(()=>{})}})};
  if(V.dataset.src!==src){V.dataset.src=src;V.src=src;V.addEventListener('loadedmetadata',go,{once:true})}else go();
  ls.set('reels:pos:'+mode,s._k);if(s._k>list.length-4&&mode==='foryou')more()}
V.addEventListener('seeked',()=>curSl&&curSl.classList.add('ready'));V.addEventListener('playing',()=>curSl&&curSl.classList.add('ready'));
// keep the clip inside its scene: every frame while visible, and on timeupdate as a backstop
function check(){if(cur&&curSl&&!V.seeking&&V.readyState>1){const t=V.currentTime;
    if(t>=cur.b-.06||t<cur.a-1){if(auto&&t>=cur.b-.06&&curSl.nextElementSibling){V.pause();curSl.nextElementSibling.scrollIntoView({behavior:'smooth'})}else V.currentTime=cur.a}
    curSl.querySelector('.prog i').style.width=Math.min(100,100*(t-cur.a)/(cur.b-cur.a))+'%'}}
V.addEventListener('timeupdate',check);(function tick(){check();requestAnimationFrame(tick)})();
function shuffled(){const a=all.slice();for(let i=a.length-1;i>0;i--){const j=Math.random()*(i+1)|0;[a[i],a[j]]=[a[j],a[i]]}return a}
function more(){const add=shuffled(),f=$('#feed');add.forEach(r=>{const s=slide(r,list.length);list.push(r);f.append(s);io.observe(s)})}
function showFeed(m,items,start,top){if(mode!==m||!list.length||m.startsWith('@')||m==='liked'){mode=m;list=items;curSl=null;cur=null;
    const f=$('#feed');io.disconnect();f.replaceChildren(...list.map((r,k)=>slide(r,k)));f.querySelectorAll('.slide').forEach(s=>io.observe(s));
    setTimeout(()=>{f.scrollTop=(start||0)*f.clientHeight;settle()})}
  else if(curSl&&!userPaused)V.play().catch(()=>{});
  $('#ftop').innerHTML=top;const au=$('#ftop .auto');if(au)au.onclick=()=>{auto=!auto;ls.set('reels:auto',auto);au.classList.toggle('on',auto)};
  $('#hint').style.display=soundOn?'none':'block'}
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
  if(v!=='feed'){V.pause()}}
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
