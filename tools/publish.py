"""Put the catalogue on the web for friends: the same pages as tools/catalog.py (the catalogue and Reels), with every
video the catalogue shows, at https://danielchahine004.github.io/explainers/. Videos, thumbnails and the reels' posters
are files on GitHub releases of the public repo DanielChahine004/explainers (one release per video);
the pages and the lists they read are on the same repo's GitHub Pages.

    python tools/publish.py              # pull new notes, upload what changed, then the pages and lists
    python tools/publish.py --pull       # only pull new notes into feedback.json (and reply to resolved ones)
    python tools/publish.py --dry-run    # say what would change, touch nothing
    python tools/publish.py --to DIR --api URL   # into a folder and a fake GitHub instead (site/tests use this)

Notes on the site are comments by signed-in GitHub users on the video's issue in that repo, each carrying its moment.
A publish (or --pull) brings new ones into <video>/feedback.json with the scene and a frame grab, like a note made in
the local catalogue, so the next fix sees them; once a pulled note is resolved there, the next publish replies on the
issue with what it led to and the site shows it resolved. Only these GitHub notes are ever published: notes made in
the local catalogue stay on this machine.

Each file goes up under a name made from its contents (<hash>.mp4), so a browser never plays a stale copy of a replaced
video; the old files are deleted once the new list is up. GitHub is reached through the gh CLI, signed in here.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from email.utils import formatdate
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
import captions  # noqa: E402
import catalog  # noqa: E402  (scan, titles, playlists, notes and thumbnails, shared with the local catalogue)
import reels  # noqa: E402

PUBLIC = Path(__file__).resolve().parent.parent / "site" / "public"
REPO = "DanielChahine004/explainers"
AUTH = "https://paperstore-auth.daniel-chahine004.workers.dev"   # the paperstore GitHub App's sign-in worker
MEDIA = "https://explainers-media.daniel-chahine004.workers.dev"   # site/media/worker.js, in front of the release files
LIMIT = 2 * 1024 ** 3 - 1      # GitHub's limit for one release file
MARK = re.compile(r"<!--\s*note\s+(\{.*?\})\s*-->", re.S)
OLD_FILES = ["app.js", "style.css"]   # the first hand-made site's files, removed from the repo


def blob_sha(data):
    """What GitHub calls a file's sha, so an unchanged file is not committed again."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


class GitHub:
    """Videos and their pictures as release files (release <video id>), the pages and lists on the repo's Pages,
    notes as comments on one issue per video."""

    def __init__(self, repo):
        self.repo = repo
        owner, name = repo.split("/")
        self.site = f"https://{owner.lower()}.github.io/{name}/"
        self.api = "https://api.github.com"
        self.releases = None

    def gh(self, *args, check=True, input=None):
        r = subprocess.run(["gh", *args], capture_output=True, input=input, text=True, encoding="utf-8", errors="replace")
        if check and r.returncode:
            raise SystemExit(f"gh {' '.join(args[:3])} failed:\n{r.stderr[-1500:]}")
        return r

    def call(self, method, path, body=None):
        r = self.gh("api", "-X", method, path.lstrip("/"), *(["--input", "-"] if body is not None else []),
                    input=json.dumps(body) if body is not None else None, check=False)
        if r.returncode:
            return None
        return json.loads(r.stdout) if r.stdout.strip() else {}

    def comments(self, n):
        r = self.gh("api", "--paginate", f"repos/{self.repo}/issues/{n}/comments?per_page=100", check=False)
        if r.returncode:
            return None
        return json.loads(r.stdout.replace("][", ",")) if r.stdout.strip() else []

    def url(self, tag, name):
        # through the media worker (site/media): GitHub serves release files as downloads, which an iPhone won't play
        return f"{MEDIA}/{tag}/{name}"

    def read(self, path):
        r = self.gh("api", "-H", "Accept: application/vnd.github.raw", f"repos/{self.repo}/contents/{path}", check=False)
        return r.stdout if r.returncode == 0 else None

    def write(self, path, data, message):
        r = self.gh("api", f"repos/{self.repo}/contents/{path}", "--jq", ".sha", check=False)
        sha = r.stdout.strip() if r.returncode == 0 else None
        if sha == blob_sha(data):
            return False
        body = {"message": message, "content": base64.b64encode(data).decode(), **({"sha": sha} if sha else {})}
        self.gh("api", "-X", "PUT", f"repos/{self.repo}/contents/{path}", "--input", "-", input=json.dumps(body))
        return True

    def remove(self, path):
        r = self.gh("api", f"repos/{self.repo}/contents/{path}", "--jq", ".sha", check=False)
        if r.returncode == 0:
            self.call("DELETE", f"repos/{self.repo}/contents/{path}", {"message": f"site: drop {path}", "sha": r.stdout.strip()})

    def upload(self, tag, title, files):
        """files: [(path, name)], all into release <tag> (made if missing), each under its given name."""
        for path, _ in files:
            if path.stat().st_size > LIMIT:
                raise SystemExit(f"{path} is over 2 GB, GitHub's limit for one release file")
        if self.releases is None:
            out = self.gh("release", "list", "--repo", self.repo, "--limit", "1000", "--json", "tagName").stdout
            self.releases = {r["tagName"] for r in json.loads(out or "[]")}
        if tag not in self.releases:
            self.gh("release", "create", tag, "--repo", self.repo, "--title", title, "--notes", f"{self.site}#v={tag}", "--latest=false")
            self.releases.add(tag)
        with tempfile.TemporaryDirectory() as d:   # a file goes up under its own name, so give each the wanted one
            named = []
            for path, name in files:
                n = Path(d) / name
                try:
                    os.link(path, n)
                except OSError:
                    shutil.copyfile(path, n)
                named.append(str(n))
            self.gh("release", "upload", tag, *named, "--repo", self.repo, "--clobber")

    def delete(self, tag, name):
        self.gh("release", "delete-asset", tag, name, "--repo", self.repo, "-y", check=False)

    def drop(self, tag):
        self.gh("release", "delete", tag, "--repo", self.repo, "--cleanup-tag", "-y", check=False)


class Folder(GitHub):
    """The same layout in a local folder, and issues on a fake GitHub API: what the tests serve."""

    def __init__(self, root, api, repo=REPO):
        self.root, self.repo, self.api, self.site = Path(root), repo, api.rstrip("/"), "./"
        self.root.mkdir(parents=True, exist_ok=True)

    def call(self, method, path, body=None):
        req = urllib.request.Request(self.api + "/" + path.lstrip("/"), method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                d = r.read()
            return json.loads(d) if d.strip() else {}
        except (urllib.error.URLError, ValueError):
            return None

    def comments(self, n):
        return self.call("GET", f"repos/{self.repo}/issues/{n}/comments?per_page=100")

    def url(self, tag, name):
        return f"releases/download/{tag}/{name}"

    def read(self, path):
        p = self.root / path
        return p.read_text(encoding="utf-8") if p.exists() else None

    def write(self, path, data, message):
        p = self.root / path
        if p.exists() and p.read_bytes() == data:
            return False
        p.write_bytes(data)
        return True

    def remove(self, path):
        (self.root / path).unlink(missing_ok=True)

    def upload(self, tag, title, files):
        d = self.root / "releases" / "download" / tag
        d.mkdir(parents=True, exist_ok=True)
        for path, name in files:
            shutil.copyfile(path, d / name)

    def delete(self, tag, name):
        (self.root / "releases" / "download" / tag / name).unlink(missing_ok=True)

    def drop(self, tag):
        shutil.rmtree(self.root / "releases" / "download" / tag, ignore_errors=True)


def fname(url):
    """A release file's name from its link (links change with where they are served from; names only with the file)."""
    return url.rsplit("/", 1)[1] if url else None


def sha(path, cache):
    """The file's hash, remembered by (size, mtime) so an unchanged render is not read again."""
    st = path.stat()
    c = cache.get(str(path))
    if c and c[0] == st.st_size and c[1] == st.st_mtime:
        return c[2]
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    cache[str(path)] = [st.st_size, st.st_mtime, h.hexdigest()]
    return cache[str(path)][2]


# ---- notes ----------------------------------------------------------------------------------------------------------

def pull(dest, index, dry=False):
    """New GitHub comments into each video's feedback.json; comments deleted on GitHub out of it while still open;
    a reply on the issue for each pulled note resolved since. Returns (pulled, dropped, replied)."""
    got = dropped = replied = 0
    for v in index.get("videos", []):
        n, vid = v.get("issue"), v["id"]
        if not n or not (catalog.ROOT / vid).is_dir():
            continue
        cs = dest.comments(n)
        if cs is None:
            print(f"  couldn't read the notes on {vid} (issue {n})")
            continue
        with catalog._fb_lock:
            ns = catalog.load_notes(vid)
            known = {x.get("gh"): x for x in ns if x.get("gh")}
            live = {c["id"] for c in cs}
            changed, grabs = False, []
            for c in cs:
                body = (c.get("body") or "").replace("\r\n", "\n")
                m = MARK.search(body)
                if not m or c["id"] in known:
                    continue
                try:
                    t = float(json.loads(m.group(1)).get("t", 0))
                except (ValueError, TypeError, AttributeError):
                    continue
                text = MARK.sub("", "\n\n".join(body.split("\n\n")[1:])).strip()
                full = next(iter((catalog.ROOT / vid).glob("*_narrated.mp4")), None)
                scene, local = catalog.scene_at(vid, t)
                nid = f"gh{c['id']}"
                ns.append({"nid": nid, "gh": c["id"], "by": (c.get("user") or {}).get("login"), "t": round(t, 1),
                           "scene": scene, "scene_t": local, "text": text,
                           "at": (c.get("created_at") or "")[:16].replace("T", " "),
                           "render": int(full.stat().st_mtime) if full else 0, "status": "open"})
                grabs.append((t, nid))
                got += 1
                changed = True
                print(f"  note from @{ns[-1]['by']} on {vid} at {int(t) // 60}:{int(t) % 60:02d}: {text[:60]}")
            for x in list(ns):
                if x.get("gh") and x["gh"] not in live and x.get("status") == "open":
                    ns.remove(x)
                    dropped += 1
                    changed = True
            for x in ns:
                if x.get("gh") and x.get("status") != "open" and not x.get("replied") and x["gh"] in live:
                    quote = "\n".join("> " + line for line in x.get("text", "").splitlines()) or "> (note)"
                    what = x.get("resolution") or "Fixed."
                    if not dry and dest.call("POST", f"repos/{dest.repo}/issues/{n}/comments",
                                             {"body": f"{quote}\n\n**Resolved** ({x.get('kind') or 'done'}): {what}"}) is not None:
                        x["replied"] = True
                        replied += 1
                        changed = True
            if changed and not dry:
                catalog.save_notes(vid, ns)
        if not dry:
            for t, nid in grabs:
                catalog.grab(vid, t, nid)
    return got, dropped, replied


def public_notes(vid):
    """The notes the site may show: only those that came from GitHub comments, with what each led to."""
    keep = ("nid", "gh", "by", "t", "scene", "scene_t", "text", "status", "kind", "resolution", "at")
    return [{k: x[k] for k in keep if k in x} for x in catalog.load_notes(vid) if x.get("gh")]


def feed(videos, site):
    """RSS, newest change first: a new video is "New: <title>", a replaced one "Updated: <title>"."""
    items = []
    for v in sorted(videos, key=lambda v: -v["updated"])[:50]:
        title = ("Updated: " if v["updated"] > v["added"] else "New: ") + v["title"]
        items.append(f"<item><title>{escape(title)}</title><link>{escape(site + '#v=' + v['id'] + '&t=0')}</link>"
                     f'<guid isPermaLink="false">{escape(v["id"] + "@" + v["v"])}</guid>'
                     f"<pubDate>{formatdate(v['updated'], usegmt=True)}</pubDate></item>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>Explainers</title>'
            f"<link>{escape(site)}</link><description>Narrated explainer videos, as they are made and updated</description>\n"
            + "\n".join(items) + "\n</channel></rss>\n")


def page(html, ver):
    """One of the catalogue's pages, with the site's adapter loaded before its own script."""
    inject = (f'<script src="config.js?v={ver}"></script><script src="site.js?v={ver}"></script>'
              '<link rel="alternate" type="application/rss+xml" title="Explainers" href="feed.xml">')
    return html.replace("<head>", "<head>" + inject, 1).encode("utf-8")


# ---- main -----------------------------------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="say what would change, touch nothing")
    ap.add_argument("--pull", action="store_true", help="only pull new notes (and reply to resolved ones)")
    ap.add_argument("--to", help="a local folder instead of GitHub")
    ap.add_argument("--api", help="with --to: the fake GitHub API the notes live on")
    ap.add_argument("--root", help="the project to publish (default: this one)")
    ap.add_argument("--render", help="the render mirror reels are timed from (default: catalog.RENDER)")
    a = ap.parse_args()

    if a.root:   # tests publish a stand-in project
        root = Path(a.root).resolve()
        catalog.ROOT = reels.ROOT = root
        catalog.CACHE = root / ".catalog"
        reels.CACHE = root / ".catalog" / "reels"
        catalog.PLAYLISTS = root / "playlists.json"
        catalog.PAPERS = root / "papers.json"
    if a.render:
        catalog.RENDER = Path(a.render)
    root = catalog.ROOT
    hashes_file = catalog.CACHE / "publish_hashes.json"
    try:
        hashes = json.loads(hashes_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        hashes = {}

    dest = Folder(a.to, a.api or "http://127.0.0.1:9") if a.to else GitHub(REPO)
    old = json.loads(dest.read("index.json") or '{"videos": []}')
    got, dropped, replied = pull(dest, old, dry=a.dry_run)
    if got or dropped or replied:
        print(f"notes: {got} new, {dropped} deleted on GitHub, {replied} resolved and replied to")
    if a.pull:
        return
    before = {v["id"]: v for v in old["videos"]}
    first = not before
    now = int(time.time())

    items = catalog.scan()
    papers = catalog.papers()
    r = str(catalog.RENDER).replace("\\", "/")
    wsl_root = "/home/h/slab_render" if "wsl.localhost" in r.lower() else captions._wsl(catalog.RENDER)
    accounts = {acc["id"]: acc for acc in reels.index(items, catalog.RENDER)}
    videos, uploads, gone = [], [], []   # uploads: (video id, title, [(path or a maker, name)])
    for item in items:
        vid = item["id"]
        full = root / vid / item["src"].rsplit("/", 1)[1]
        small = root / vid / item["small"].rsplit("/", 1)[1] if item["small"] else None
        h = sha(full, hashes)[:12]
        names = {"src": f"{h}.mp4", "thumb": f"{h}.jpg", "small": f"{sha(small, hashes)[:12]}-s.mp4" if small else None}
        e = {"id": vid, "title": item["title"], "dur": round(item["dur"], 1), "v": h, "size": full.stat().st_size,
             **{k: dest.url(vid, n) if n else None for k, n in names.items()}}
        p = before.get(vid, {})
        e["issue"] = p.get("issue")
        e["notes"] = sum(1 for x in public_notes(vid) if x.get("status") == "open")
        files = []
        if p.get("v") == h and fname(p.get("small")) == names["small"]:
            e["added"], e["updated"] = p["added"], p["updated"]
        else:
            # the first publish dates each video by its own history; after that, by when it went up
            e["added"] = p["added"] if p else (int(catalog.born(root / vid)) if first else now)
            if first:   # re-rendered more than a day after it was started counts as updated
                m = int(full.stat().st_mtime)
                e["updated"] = m if m - e["added"] > 86400 else e["added"]
            else:
                e["updated"] = now
            if p.get("v") != h:
                files += [(full, names["src"]), (lambda vid=vid: catalog.thumb(vid), names["thumb"])]
            if small and fname(p.get("small")) != names["small"]:
                files.append((small, names["small"]))
            if p:
                gone += [(vid, fname(k)) for k in (p["src"], p.get("small"), p["thumb"]) if k and fname(k) not in names.values()]
        # the reels: a poster per scene and the account's avatar, named by the render they came from. A reel plays its
        # span of the video's small copy, and no rewind copy goes up: holding to rewind steps back by seeking instead
        acc = accounts.get(vid)
        e["reels"] = []
        if acc:
            rn = [f"r{r['i']}-{h}.jpg" for r in acc["reels"]] + [f"av-{h}.jpg"]
            e["reels"] = rn
            if p.get("reels") != rn:
                files += [(lambda vid=vid, i=r["i"]: reels.poster(catalog.FFMPEG, catalog.RENDER, vid, i), n) for r, n in zip(acc["reels"], rn)]
                files.append((lambda vid=vid: reels.avatar(catalog.FFMPEG, vid), rn[-1]))
                gone += [(vid, n) for n in p.get("reels", []) if n not in rn]
            acc.update(src=e["src"], small=e["small"], mtime=e["updated"], avatar=dest.url(vid, rn[-1]), rev="")
            for r, n in zip(acc["reels"], rn):
                r["thumb"] = dest.url(vid, n)
        # subtitles from the narration (tools/captions.py), named by the render they time
        st = full.stat()
        cap = captions.make(vid, f"{int(st.st_mtime)}-{st.st_size}", catalog.CACHE / "captions", wsl_root)
        e["vtt"] = dest.url(vid, f"{h}.vtt") if cap else None
        if cap and fname(p.get("vtt")) != f"{h}.vtt":
            files.append((cap, f"{h}.vtt"))
            if p.get("vtt"):
                gone.append((vid, fname(p["vtt"])))
        e["chapters"] = [[r["name"], r["a"]] for r in acc["reels"]] if acc else []
        e["paper"] = papers.get(vid)
        if files:
            uploads.append((vid, e["title"], files))
        videos.append(e)   # a retitled video keeps its dates: the title is not the video
    ids = {v["id"] for v in videos}
    removed = sorted(set(before) - ids)

    new = [v["id"] for v in videos if v["id"] not in before]
    changed = [v["id"] for v in videos if v["id"] in before and before[v["id"]]["v"] != v["v"]]
    size = sum(f.stat().st_size for _, _, fs in uploads for f, _ in fs if isinstance(f, Path))
    print(f"{len(videos)} videos: {len(new)} new, {len(changed)} updated, {len(removed)} removed; "
          f"{sum(len(fs) for _, _, fs in uploads)} files to upload ({size / 1e6:.0f} MB)", flush=True)
    for label, xs in (("new", new), ("updated", changed), ("removed", removed)):
        if xs and (len(xs) <= 20 or not first):
            print(f"  {label}: {', '.join(xs)}")
    if a.dry_run:
        return

    for n, (vid, title, files) in enumerate(uploads, 1):
        ready = []
        for f, name in files:
            path = f if isinstance(f, Path) else f()   # pictures and rewind copies are cut (or reused) on demand
            if path is None or not Path(path).exists():
                print(f"  couldn't make {vid}/{name} (ffmpeg in WSL, or the render mirror?)")
                continue
            ready.append((Path(path), name))
        if ready:
            dest.upload(vid, title, ready)
        hashes_file.parent.mkdir(exist_ok=True)
        hashes_file.write_text(json.dumps(hashes), encoding="utf-8")
        print(f"  [{n}/{len(uploads)}] {vid}: {len(ready)} files", flush=True)

    # one issue per video holds its notes, opened once
    for e in videos:
        if not e["issue"]:
            r = dest.call("POST", f"repos/{dest.repo}/issues", {"title": f"Notes: {e['title']}", "body":
                          f"Notes on [{e['title']}]({dest.site}#v={e['id']}&t=0) from the site: each comment is one note at a "
                          "moment of the video. Leave them from the video's Note button."})
            e["issue"] = (r or {}).get("number")
            time.sleep(0.5 if a.to is None else 0)   # GitHub limits how fast new issues can be opened

    what = ", ".join(f"{len(x)} {k}" for k, x in (("new", new), ("updated", changed), ("removed", removed)) if x) or "no video changes"
    ver = hashlib.sha1((PUBLIC / "site.js").read_bytes() + catalog.PAGE.encode() + reels.PAGE.encode()).hexdigest()[:8]
    cfg = {"repo": dest.repo, "api": dest.api, "auth": AUTH, "base": dest.site if a.to is None else ""}
    out = {
        "index.html": page(catalog.PAGE, ver), "reels.html": page(reels.PAGE, ver),
        "site.js": (PUBLIC / "site.js").read_bytes(),
        "config.js": f"window.SITE_CFG = {json.dumps(cfg)};\n".encode(),
        "index.json": json.dumps({"generated": now, "playlists": catalog.playlists(), "videos": videos}, ensure_ascii=False, indent=0).encode(),
        "reels.json": json.dumps([accounts[v["id"]] for v in videos if v["id"] in accounts], ensure_ascii=False).encode(),
        "notes.json": json.dumps({v["id"]: public_notes(v["id"]) for v in videos}, ensure_ascii=False).encode(),
        "feed.xml": feed(videos, dest.site).encode("utf-8"),
    }
    sent = [k for k, data in out.items() if dest.write(k, data, f"{k}: {what}")]
    for f in OLD_FILES:
        dest.remove(f)
    for tag, name in gone:
        dest.delete(tag, name)
    for tag in removed:
        dest.drop(tag)
    print(f"site updated ({what}; {', '.join(sent) or 'no files changed'})" + (f", {len(gone)} old files deleted" if gone else ""))


if __name__ == "__main__":
    main()
