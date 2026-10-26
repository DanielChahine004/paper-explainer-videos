"""A local streaming page for the rendered explainers: every <video>/*_narrated.mp4 under the project, served to
phones, tablets and TVs on the home network. The list is rescanned on every request, so a video shows up as soon as
its render finishes; open pages poll for new ones. Standard library only; run with Windows Python so the LAN can
reach it (WSL2's network sits behind NAT):

    python tools/catalog.py            # then open http://<this PC's LAN address>:8765 on any device

Thumbnails are cut by ffmpeg (through WSL, from the render env) into .catalog/ and cached; without ffmpeg the page
falls back to the video's own first frames. Playback position is remembered per device.

Playlists live in playlists.json at the project root, {"name": ["folder", ...]} in viewing order. Each shows as its
own row above the full list, counting the videos rendered so far; inside a playlist, the next video plays on its own.

Feedback: in the player, Note (or the n key) pauses and saves a note at that moment into <video>/feedback.json, with
the scene playing there and a frame grab in <video>/review/feedback/. tools/feedback.py lists the open notes for
triage (an incidental fix, or a DESIGN/vlint rule for every future video).
"""
import json
import mimetypes
import os
import re
import socket
import struct
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".catalog"
PORT = int(os.environ.get("CATALOG_PORT", "8765"))
FFMPEG = os.environ.get("FFMPEG", "/home/h/slab_render/.pixi/envs/default/bin/ffmpeg")   # inside WSL
PLAYLISTS = ROOT / "playlists.json"
RENDER = Path(os.environ.get("RENDER_ROOT", r"\\wsl.localhost\Ubuntu\home\h\slab_render"))   # the WSL render mirror
SKIP = {"voice_ab"}                                      # voice tests, not explainers
_meta, _lock = {}, threading.Lock()


def duration(path):
    """Seconds, from the mp4's mvhd box (at the front with +faststart, else near the end)."""
    size = path.stat().st_size
    with open(path, "rb") as f:
        for off in (0, max(0, size - 4_000_000)):
            f.seek(off)
            d = f.read(4_000_000)
            i = d.find(b"mvhd")
            if i >= 0:
                v = d[i + 4]
                ts, du = struct.unpack(">II", d[i + 16:i + 24]) if v == 0 else struct.unpack(">IQ", d[i + 24:i + 36])
                return du / ts
    return 0.0


def title(folder):
    """The first clause of the video script's docstring ("Explainer: ..."), else the folder name."""
    for py in sorted(folder.glob("*_vo.py")):
        m = re.match(r'\s*"""(.*?)(?:"""|\n\s*\n)', py.read_text(encoding="utf-8", errors="ignore"), re.S)
        if m:
            t = " ".join(m.group(1).split())
            t = re.sub(r"^.*?[Ee]xplainer(?: \([^)]*\))?(?: of)?:?\s*", "", t, count=1)
            q = re.search(r"(?:^|[\s,])'([^']{12,})'", t)          # a paper's quoted title, named up front, wins
            t = q.group(1) if q and q.start() < 100 else re.split(r" \(|\. |; | -- ", t)[0]
            t = t.strip(" .'\"")
            if t:
                t = t if len(t) <= 90 else t[:88].rsplit(" ", 1)[0] + "…"
                return t[0].upper() + t[1:]
    return folder.name.replace("_", " ")


def scan():
    """All explainers, newest first: one entry per folder, its full render plus the small copy if there is one."""
    out = []
    for full in ROOT.glob("*/*_narrated.mp4"):
        folder = full.parent
        if folder.name in SKIP:
            continue
        st = full.stat()
        key = (str(full), st.st_mtime, st.st_size)
        with _lock:
            m = _meta.get(key)
        if m is None:
            m = {"title": title(folder), "dur": duration(full)}
            with _lock:
                _meta[key] = m
        small = max(folder.glob("*small*.mp4"), key=lambda p: p.stat().st_mtime, default=None)   # newest, if a stale one is left
        out.append({"id": folder.name, "notes": sum(n.get("status") == "open" for n in load_notes(folder.name)), "title": m["title"], "dur": m["dur"], "mtime": st.st_mtime,
                    "size": st.st_size, "src": f"/v/{folder.name}/{full.name}",
                    "small": f"/v/{folder.name}/{small.name}" if small else None,
                    "thumb": f"/thumb/{folder.name}.jpg?{int(st.st_mtime)}"})
    return sorted(out, key=lambda v: -v["mtime"])


def playlists():
    """[{name, ids}] in file order; a malformed file is shown as no playlists rather than a broken page."""
    try:
        d = json.loads(PLAYLISTS.read_text(encoding="utf-8"))
        return [{"name": k, "ids": [str(i) for i in v]} for k, v in d.items()]
    except (OSError, ValueError, AttributeError):
        return []


def scene_spans(vid):
    """[(scene, start, end)] in seconds of the joined video, from the render's scene list in the WSL mirror."""
    out, t = [], 0.0
    try:
        for line in (RENDER / vid / "list.txt").read_text().splitlines():
            m = re.match(r"file '/home/h/slab_render/(.+)'", line.strip())
            if m:
                f = RENDER / m.group(1)
                d = duration(f)
                out.append((f.stem, t, t + d))
                t += d
    except OSError:
        return []
    return out


def scene_at(vid, t):
    for name, a, b in scene_spans(vid):
        if a <= t < b:
            return name, round(t - a, 1)
    return None, None


_fb_lock = threading.Lock()


def load_notes(vid):
    try:
        return json.loads((ROOT / vid / "feedback.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def save_notes(vid, notes):
    (ROOT / vid / "feedback.json").write_text(json.dumps(notes, indent=1, ensure_ascii=False), encoding="utf-8")


def grab(vid, t, nid):
    """The frame a note is about, cut once (in the background) so it survives a re-render."""
    full = next(iter((ROOT / vid).glob("*_narrated.mp4")), None)
    if full is None:
        return
    out = ROOT / vid / "review" / "feedback" / f"{nid}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [FFMPEG, "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i", wsl_path(full), "-frames:v", "1",
           "-vf", "scale=1280:-2", "-q:v", "3", wsl_path(out)]
    try:
        subprocess.run((["wsl"] if os.name == "nt" else []) + cmd, timeout=60, capture_output=True)
    except (OSError, subprocess.TimeoutExpired):
        pass


def add_note(vid, t, text):
    full = next(iter((ROOT / vid).glob("*_narrated.mp4")))
    scene, local = scene_at(vid, t)
    n = {"nid": uuid.uuid4().hex[:8], "t": round(t, 1), "scene": scene, "scene_t": local, "text": text.strip(),
         "at": time.strftime("%Y-%m-%d %H:%M"), "render": int(full.stat().st_mtime), "status": "open"}
    with _fb_lock:
        notes = load_notes(vid)
        notes.append(n)
        save_notes(vid, notes)
    threading.Thread(target=grab, args=(vid, t, n["nid"]), daemon=True).start()
    return n


def wsl_path(p):
    p = str(p).replace("\\", "/")
    return f"/mnt/{p[0].lower()}{p[2:]}"


def thumb(vid):
    """A 480-px frame from 30% of the way in, cut once per render and cached."""
    full = next(iter((ROOT / vid).glob("*_narrated.mp4")), None)
    if full is None:
        return None
    out = CACHE / f"{vid}_{int(full.stat().st_mtime)}.jpg"
    if not out.exists():
        CACHE.mkdir(exist_ok=True)
        t = duration(full) * 0.3
        cmd = [FFMPEG, "-loglevel", "error", "-y", "-ss", f"{t:.1f}", "-i", wsl_path(full), "-frames:v", "1",
               "-vf", "scale=480:-2", "-q:v", "4", wsl_path(out)]
        try:
            subprocess.run((["wsl"] if os.name == "nt" else []) + cmd, timeout=60, capture_output=True)
        except (OSError, subprocess.TimeoutExpired):
            return None
        for old in CACHE.glob(f"{vid}_*.jpg"):
            if old != out:
                old.unlink(missing_ok=True)
    return out if out.exists() else None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send(self, code, body, ctype, extra=()):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_POST(self):
        path = unquote(self.path.split("?", 1)[0])
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0) or 0)) or b"{}")
            vid = str(body.get("id", ""))
            if vid not in {v["id"] for v in scan()}:
                return self.send(404, b"no such video", "text/plain")
            if path == "/api/notes" and str(body.get("text", "")).strip():
                n = add_note(vid, float(body.get("t", 0)), str(body["text"])[:4000])
                return self.send(200, json.dumps(n).encode(), "application/json")
            if path == "/api/notes/delete":
                with _fb_lock:
                    save_notes(vid, [n for n in load_notes(vid) if n["nid"] != body.get("nid")])
                return self.send(200, b"{}", "application/json")
            self.send(400, b"bad request", "text/plain")
        except (ValueError, TypeError):
            self.send(400, b"bad request", "text/plain")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        path = unquote(self.path.split("?", 1)[0])
        try:
            if path == "/":
                self.send(200, PAGE.encode(), "text/html; charset=utf-8", [("Cache-Control", "no-cache")])
            elif path == "/api/videos":
                self.send(200, json.dumps(scan()).encode(), "application/json", [("Cache-Control", "no-cache")])
            elif path == "/api/notes":
                vid = unquote(self.path.split("id=", 1)[1]) if "id=" in self.path else ""
                ok = vid in {v["id"] for v in scan()}
                self.send(200, json.dumps(load_notes(vid) if ok else []).encode(), "application/json",
                          [("Cache-Control", "no-cache")])
            elif path == "/api/playlists":
                self.send(200, json.dumps(playlists()).encode(), "application/json", [("Cache-Control", "no-cache")])
            elif path.startswith("/thumb/"):
                t = thumb(path[7:].removesuffix(".jpg"))
                if t is None:
                    self.send(404, b"", "text/plain")
                else:
                    self.send(200, t.read_bytes(), "image/jpeg", [("Cache-Control", "max-age=86400")])
            elif path.startswith("/v/"):
                self.video(path[3:])
            else:
                self.send(404, b"not found", "text/plain")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def video(self, rel):
        """Stream one listed video, honouring Range so players can seek (Safari won't play without it)."""
        vs = scan()
        allowed = {v["src"][3:] for v in vs} | {v["small"][3:] for v in vs if v["small"]}
        if rel not in allowed:
            return self.send(404, b"not found", "text/plain")
        f = ROOT / rel
        size = f.stat().st_size
        a, b = 0, size - 1
        m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        if m and (m.group(1) or m.group(2)):
            if m.group(1):
                a, b = int(m.group(1)), int(m.group(2)) if m.group(2) else size - 1
            else:
                a = size - int(m.group(2))
            b = min(b, size - 1)
            if a > b:
                return self.send(416, b"", "text/plain", [("Content-Range", f"bytes */{size}")])
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {a}-{b}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(f.name)[0] or "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(b - a + 1))
        self.end_headers()
        if self.command == "HEAD":
            return
        with open(f, "rb") as fh:
            fh.seek(a)
            left = b - a + 1
            while left > 0:
                chunk = fh.read(min(1 << 20, left))
                if not chunk:
                    break
                self.wfile.write(chunk)
                left -= len(chunk)


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Explainers</title>
<style>
:root{--bg:#0e1015;--card:#171a21;--line:#262a33;--text:#e8e6e1;--mute:#9a9ca3;--acc:#e8915a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.4 system-ui,-apple-system,sans-serif}
header{padding:20px 16px 8px;max-width:1200px;margin:auto;display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
h1{font-size:22px;margin:0;font-weight:600}#count{color:var(--mute)}
#q{margin-left:auto;background:var(--card);border:1px solid var(--line);color:var(--text);border-radius:8px;padding:8px 10px;
  font:inherit;width:min(260px,100%)}
main{max-width:1200px;margin:auto;padding:0 16px 40px}
h2{font-size:17px;margin:22px 0 10px;font-weight:600}h2 .n{color:var(--mute);font-weight:400;margin-left:8px;font-size:14px}
.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fill,minmax(260px,1fr))}
.ep{position:absolute;left:8px;bottom:8px;background:#000c;padding:1px 6px;border-radius:4px;font-size:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;cursor:pointer;transition:transform .15s}
.card:hover{transform:translateY(-2px)}.card:focus-visible{outline:2px solid var(--acc)}
.th{position:relative;aspect-ratio:16/9;background:#000}.th img,.th video{width:100%;height:100%;object-fit:cover;display:block}
.dur{position:absolute;right:8px;bottom:8px;background:#000c;padding:1px 6px;border-radius:4px;font-size:12px}
.new{position:absolute;left:8px;top:8px;background:var(--acc);color:#111;padding:1px 7px;border-radius:4px;font-size:12px;font-weight:600}
.bar{position:absolute;left:0;bottom:0;height:3px;background:var(--acc)}
.meta{padding:10px 12px 12px}.t{font-weight:600}.s{color:var(--mute);font-size:13px;margin-top:4px}
#player{position:fixed;inset:0;background:#000;display:none;flex-direction:column;z-index:9}
#player.on{display:flex}#player video{flex:1;width:100%;min-height:0;background:#000}
#pbar{display:flex;gap:10px;align-items:center;padding:10px 16px;background:#111}
#pbar button{background:#222;color:var(--text);border:1px solid #333;border-radius:8px;padding:8px 14px;font:inherit;cursor:pointer}
#ptitle{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#pbody{flex:1;display:flex;min-height:0}#pbody video{flex:1;min-width:0}
#notes{width:min(340px,40vw);background:#14161c;border-left:1px solid #262a33;display:none;flex-direction:column;min-height:0}
#notes.on{display:flex}#nlist{flex:1;overflow:auto;padding:8px}
.note{display:flex;gap:8px;padding:8px;border-bottom:1px solid #222;font-size:14px}
.note .ts{color:var(--acc);cursor:pointer;font-variant-numeric:tabular-nums;white-space:nowrap}
.note .tx{flex:1;white-space:pre-wrap;word-break:break-word}.note .sc{color:var(--mute);font-size:12px}
.note .x{background:none;border:0;color:var(--mute);cursor:pointer;font-size:16px}
.note.done{opacity:.55}.note .rs{color:var(--mute);font-size:12px;margin-top:4px}.note .k{color:var(--acc);font-weight:600}
#rtog{background:none;border:0;color:var(--mute);cursor:pointer;font:inherit;font-size:13px;padding:10px 8px;text-align:left;width:100%}
#nform{padding:10px;border-top:1px solid #262a33;display:none;flex-direction:column;gap:8px}#nform.on{display:flex}
#nform textarea{background:#0e1015;color:var(--text);border:1px solid #333;border-radius:8px;padding:8px;font:inherit;min-height:90px;resize:vertical}
#nform .row{display:flex;gap:8px;align-items:center}#nat{color:var(--acc);flex:1}
#nform button,#notes .hd button{background:#222;color:var(--text);border:1px solid #333;border-radius:8px;padding:6px 12px;font:inherit;cursor:pointer}
#notes .hd{display:flex;align-items:center;padding:10px;border-bottom:1px solid #262a33;gap:8px}#notes .hd b{flex:1}
.nb{position:absolute;right:8px;top:8px;background:#e05d5d;color:#fff;padding:1px 7px;border-radius:4px;font-size:12px;font-weight:600}
@media (max-width:700px){#pbody{flex-direction:column}#notes{width:100%;max-height:45vh;border-left:0;border-top:1px solid #262a33}}
</style></head><body>
<header><h1>Explainers</h1><span id="count"></span><input id="q" placeholder="Search" aria-label="Search"></header>
<main id="grid"></main>
<div id="player"><div id="pbar"><button id="back">&larr; Back</button><span id="ptitle"></span><button id="qual"></button>
<button id="nbtn" title="Note at this moment (n)">Note</button><button id="ntog">Notes</button></div>
<div id="pbody"><video id="vid" controls playsinline preload="metadata"></video>
<div id="notes"><div class="hd"><b>Feedback</b><button id="nclose">Hide</button></div><div id="nlist"></div>
<div id="nform"><div class="row"><span id="nat"></span></div>
<textarea id="ntext" placeholder="What should change here? (Enter saves, Shift+Enter for a new line)"></textarea>
<div class="row"><button id="nsave">Save</button><button id="ncancel">Cancel</button></div></div></div></div></div>
<script>
const grid=document.getElementById('grid'),vid=document.getElementById('vid'),player=document.getElementById('player');
let list=[],pls=[],cur=null,curPl=null,small=false;
const fmt=s=>{s=Math.round(s);return Math.floor(s/60)+':'+String(s%60).padStart(2,'0')};
const pos=id=>{try{return +localStorage.getItem('pos:'+id)||0}catch(e){return 0}};
const save=(id,t)=>{try{localStorage.setItem('pos:'+id,t)}catch(e){}};
function card(v,ep){
  const d=document.createElement('div');d.className='card';d.tabIndex=0;
  const age=(Date.now()/1000-v.mtime)/86400,p=pos(v.id);
  d.innerHTML=`<div class="th"><img loading="lazy" alt=""><span class="dur">${fmt(v.dur)}</span>${ep?`<span class="ep">${ep}</span>`:''}${age<2?'<span class="new">NEW</span>':''}${v.notes?`<span class="nb">${v.notes} note${v.notes>1?'s':''}</span>`:''}
    ${p>5?`<div class="bar" style="width:${Math.min(100,100*p/v.dur)}%"></div>`:''}</div>
    <div class="meta"><div class="t"></div><div class="s">${new Date(v.mtime*1000).toLocaleDateString()} · ${(v.size/1048576).toFixed(0)} MB</div></div>`;
  d.querySelector('.t').textContent=v.title;
  const img=d.querySelector('img');img.src=v.thumb;
  img.onerror=()=>{const f=document.createElement('video');f.src=v.src+'#t=20';f.muted=true;f.preload='metadata';f.playsInline=true;img.replaceWith(f)};
  d.onclick=()=>play(v,ep&&d.dataset.pl);d.onkeydown=e=>{if(e.key==='Enter')play(v,ep&&d.dataset.pl)};
  return d}
function section(name,n,cards){const s=document.createElement('section'),h=document.createElement('h2'),g=document.createElement('div');
  h.textContent=name;if(n){const c=document.createElement('span');c.className='n';c.textContent=n;h.append(c)}
  g.className='grid';g.append(...cards);s.append(h,g);return s}
function render(){const q=document.getElementById('q').value.toLowerCase(),by=Object.fromEntries(list.map(v=>[v.id,v]));
  const hit=v=>v.title.toLowerCase().includes(q)||v.id.includes(q),out=[];
  for(const p of pls){const cards=[];p.ids.forEach((id,i)=>{const v=by[id];if(v&&hit(v)){const c=card(v,(i+1)+' / '+p.ids.length);c.dataset.pl=p.name;cards.push(c)}});
    const have=p.ids.filter(id=>by[id]).length;if(cards.length)out.push(section(p.name,have+' of '+p.ids.length+' ready',cards))}
  const shown=list.filter(hit).map(v=>card(v));if(shown.length)out.push(section(pls.length?'All videos':'',null,shown));
  grid.replaceChildren(...out);document.getElementById('count').textContent=list.length+' videos'}
function next(){if(!cur||!curPl)return null;const p=pls.find(p=>p.name===curPl);if(!p)return null;
  const by=Object.fromEntries(list.map(v=>[v.id,v]));const rest=p.ids.slice(p.ids.indexOf(cur.id)+1).map(id=>by[id]).filter(Boolean);return rest[0]||null}
function play(v,pl){cur=v;curPl=pl||null;document.getElementById('ptitle').textContent=v.title;
  document.getElementById('qual').style.display=v.small?'':'none';load(pos(v.id));player.classList.add('on');
  if(!history.state)history.pushState({p:1},'')}
function load(t){loadNotes();vid.src=small&&cur.small?cur.small:cur.src;document.getElementById('qual').textContent=small?'Small':'HD';
  vid.addEventListener('loadedmetadata',()=>{if(t>5&&t<vid.duration-10)vid.currentTime=t;vid.play().catch(()=>{})},{once:true})}
const notesEl=document.getElementById('notes'),nform=document.getElementById('nform'),ntext=document.getElementById('ntext');
let noteT=0,notes=[],showDone=false;
// Open notes are the to-do list. Resolved ones stay in feedback.json as the record of what each led to, folded
// away below them; one made on an earlier cut may point at a moment that has since moved.
function noteRow(n){const d=document.createElement('div');d.className='note'+(n.status==='open'?'':' done');
  d.innerHTML='<span class="ts"></span><div class="tx"></div><button class="x" title="Delete">&times;</button>';
  const ts=d.querySelector('.ts');ts.textContent=fmt(n.t);ts.onclick=()=>{vid.currentTime=n.t;vid.pause()};
  const tx=d.querySelector('.tx');tx.textContent=n.text;
  if(n.scene){const s=document.createElement('div');s.className='sc';s.textContent=n.scene+' @ '+n.scene_t+' s'+
    (n.status!=='open'&&n.render&&cur.mtime&&Math.abs(n.render-cur.mtime)>2?' · earlier cut':'');tx.append(s)}
  if(n.resolution){const r=document.createElement('div');r.className='rs';const k=document.createElement('span');k.className='k';
    k.textContent=(n.kind||'done')+': ';r.append(k,n.resolution);tx.append(r)}
  d.querySelector('.x').onclick=async()=>{if(!confirm('Delete this note?'))return;
    await fetch('/api/notes/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:cur.id,nid:n.nid})});loadNotes()};
  return d}
async function loadNotes(){if(!cur)return;try{notes=await (await fetch('/api/notes?id='+encodeURIComponent(cur.id))).json()}catch(e){notes=[]}
  const by=(a,b)=>a.t-b.t,open=notes.filter(n=>n.status==='open').sort(by),done=notes.filter(n=>n.status!=='open').sort(by);
  const rows=open.map(noteRow);
  if(!open.length)rows.push(Object.assign(document.createElement('div'),{className:'sc',textContent:'No open notes.',style:'padding:8px'}));
  if(done.length){const b=document.createElement('button');b.id='rtog';b.textContent=(showDone?'▾':'▸')+' Resolved ('+done.length+')';
    b.onclick=()=>{showDone=!showDone;loadNotes()};rows.push(b);if(showDone)rows.push(...done.map(noteRow))}
  document.getElementById('nlist').replaceChildren(...rows);
  document.getElementById('ntog').textContent='Notes'+(open.length?' ('+open.length+')':'')}
function startNote(){if(!cur)return;vid.pause();noteT=vid.currentTime;notesEl.classList.add('on');nform.classList.add('on');
  document.getElementById('nat').textContent='at '+fmt(noteT);ntext.value='';ntext.focus()}
async function saveNote(){const text=ntext.value.trim();if(!text||!cur)return;
  await fetch('/api/notes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:cur.id,t:noteT,text})});
  nform.classList.remove('on');loadNotes()}
document.getElementById('nbtn').onclick=startNote;
document.getElementById('ntog').onclick=()=>notesEl.classList.toggle('on');
document.getElementById('nclose').onclick=()=>notesEl.classList.remove('on');
document.getElementById('nsave').onclick=saveNote;
document.getElementById('ncancel').onclick=()=>nform.classList.remove('on');
ntext.onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();saveNote()}if(e.key==='Escape')nform.classList.remove('on');e.stopPropagation()};
document.addEventListener('keydown',e=>{const a=document.activeElement;
  if(cur&&e.key==='n'&&a!==ntext&&a!==document.getElementById('q')){e.preventDefault();startNote()}});
function close(){nform.classList.remove('on');if(cur)save(cur.id,vid.currentTime);vid.pause();vid.removeAttribute('src');vid.load();player.classList.remove('on');cur=null;render()}
document.getElementById('qual').onclick=()=>{small=!small;load(vid.currentTime)};
document.getElementById('back').onclick=()=>history.back();
window.onpopstate=()=>{if(cur)close()};
vid.ontimeupdate=()=>{if(cur&&Math.floor(vid.currentTime)%5===0)save(cur.id,vid.currentTime)};
vid.onended=()=>{if(!cur)return;save(cur.id,0);const n=next();if(n)play(n,curPl)};
document.getElementById('q').oninput=render;
async function refresh(){try{const [n,p]=await Promise.all([fetch('/api/videos').then(r=>r.json()),fetch('/api/playlists').then(r=>r.json())]);
  if(JSON.stringify([n,p])!==JSON.stringify([list,pls])){list=n;pls=p;if(!cur)render()}}catch(e){}}
refresh();setInterval(refresh,20000);
</script></body></html>"""


def lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.168.0.1", 9))                       # no packet is sent; this just picks the LAN route
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"{len(scan())} videos; open http://{lan_ip()}:{PORT} on any device on this network", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
