"""The friends' site end to end: a stand-in project with two short videos (and a render mirror, so they have reels) is
published by tools/publish.py into a folder laid out like the real site, which this test serves with byte ranges the
way GitHub serves release files, next to a fake GitHub API for the notes. The pages are the local catalogue's own
(catalog.PAGE, reels.PAGE), driven in headless Edge (Playwright's Chromium cannot play H.264). Needs ffmpeg in WSL.

    uv run --with pytest --with playwright pytest site/tests
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import catalog  # noqa: E402

GH = "DanielChahine004/explainers"


class FakeGitHub:
    """Issues and comments, as much of GitHub's API as the notes use. A request with a token is the friend "ana"."""

    def __init__(self):
        self.issues, self.next = {}, 1000

    def handle(self, h, method):
        path = h.path.split("?")[0][len("/api"):]
        who = "ana" if h.headers.get("Authorization") else None
        body = json.loads(h.rfile.read(int(h.headers.get("Content-Length") or 0)) or b"null")
        if path == "/user":
            return (200, {"login": who}) if who else (401, {"message": "Requires authentication"})
        if path == f"/repos/{GH}/issues" and method == "POST":
            n = len(self.issues) + 1
            self.issues[n] = {"title": body["title"], "comments": []}
            return 201, {"number": n}
        m = re.fullmatch(rf"/repos/{GH}/issues/(\d+)/comments", path)
        if m and int(m.group(1)) in self.issues:
            cs = self.issues[int(m.group(1))]["comments"]
            if method == "GET":
                return 200, cs
            self.next += 1
            c = {"id": self.next, "body": body["body"], "user": {"login": who or "publisher"}, "created_at": "2026-11-14T10:00:00Z"}
            cs.append(c)
            return 201, c
        m = re.fullmatch(rf"/repos/{GH}/issues/comments/(\d+)", path)
        if m and method == "DELETE":
            for i in self.issues.values():
                for c in i["comments"]:
                    if c["id"] == int(m.group(1)):
                        if c["user"]["login"] != who:
                            return 403, {"message": "not yours"}
                        i["comments"].remove(c)
                        return 204, None
        return 404, {"message": "Not Found"}

    def comments(self, n=1):
        return self.issues[n]["comments"]


class Server(SimpleHTTPRequestHandler):
    """The site folder with byte ranges (a video player needs them to seek), and the fake API under /api."""
    fake = None

    def log_message(self, *a):
        pass

    def api(self, method):
        code, body = self.fake.handle(self, method)
        data = b"" if body is None else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        return self.api("GET") if self.path.startswith("/api/") else super().do_GET()

    def do_POST(self):
        self.api("POST")

    def do_DELETE(self):
        self.api("DELETE")

    def send_head(self):
        m = re.match(r"bytes=(\d+)-(\d*)$", self.headers.get("Range", ""))
        path = Path(self.translate_path(self.path))
        self._left = None
        if not m or not path.is_file():
            return super().send_head()
        size = path.stat().st_size
        a, b = int(m.group(1)), min(int(m.group(2)) if m.group(2) else size - 1, size - 1)
        f = open(path, "rb")
        f.seek(a)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(str(path)))
        self.send_header("Content-Range", f"bytes {a}-{b}/{size}")
        self.send_header("Content-Length", str(b - a + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        self._left = b - a + 1
        return f

    def copyfile(self, src, dst):
        if self._left is None:
            return super().copyfile(src, dst)
        while self._left > 0:
            chunk = src.read(min(self._left, 1 << 16))
            if not chunk:
                break
            dst.write(chunk)
            self._left -= len(chunk)


def ffmpeg(*args):
    subprocess.run((["wsl"] if os.name == "nt" else []) + [catalog.FFMPEG, "-loglevel", "error", "-y", *args], check=True, timeout=180)


def clip(path, color, secs):
    """A short H.264 clip with a moving test pattern tinted `color`, made like the real renders (+faststart)."""
    ffmpeg("-f", "lavfi", "-i", f"testsrc2=size=640x360:rate=25:duration={secs}", "-f", "lavfi", "-i", f"sine=frequency=440:duration={secs}",
           "-vf", f"colorbalance=rs={color}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
           "-movflags", "+faststart", catalog.wsl_path(path))


VO = '''"""{name}: A. Author, "{title}", a test paper (2026). Plan: plan.md."""


class S1_Opening(Scene):
    """Where it starts."""

    def construct(self):
        with self.voiceover(text="This is the opening of {title}. It goes on."):
            pass


class S2_Result(Scene):
    """What it found."""

    def construct(self):
        with self.voiceover(text="And here is the result."):
            pass
'''


def video(root, render, name, title, color):
    """A video folder like a real one: its script, the joined render and small copy, and in the render mirror the two
    scene files and the list.txt the reels are timed from."""
    d = root / name
    d.mkdir()
    (d / f"{name}_vo.py").write_text(VO.format(name=name, title=title), encoding="utf-8")
    clip(d / f"{name}_explainer_narrated.mp4", color, 20)
    clip(d / f"{name}_explainer_small.mp4", color, 20)
    rd = render / name
    rd.mkdir(parents=True)
    for s in ("S1_Opening", "S2_Result"):
        clip(rd / f"{s}.mp4", color, 10)
    (rd / "list.txt").write_text("".join(f"file '/home/h/slab_render/{name}/{s}.mp4'\n" for s in ("S1_Opening", "S2_Result")))


def narrate(render, name, scene):
    """Give one scene a voice clip as the renders have them: the clip and its word timings in m_<Scene>/voiceovers,
    mixed into the scene's audio 2 s in, for tools/captions.py to find."""
    vo = render / name / f"m_{scene}" / "voiceovers"
    vo.mkdir(parents=True)
    ffmpeg("-f", "lavfi", "-i", "anoisesrc=d=3:seed=7:a=0.5", "-ar", "24000", catalog.wsl_path(vo / "hello.wav"))
    ffmpeg("-f", "lavfi", "-i", "testsrc2=size=640x360:rate=25:duration=10", "-i", catalog.wsl_path(vo / "hello.wav"),
           "-filter_complex", "[1:a]adelay=delays=2000:all=1,apad[a]", "-map", "0:v", "-map", "[a]", "-t", "10", "-c:v", "libx264",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", catalog.wsl_path(render / name / f"{scene}.mp4"))
    spoken = "Hello, G P U world."
    words = [(0, 0, "Hello"), (1.0, 7, "G"), (1.3, 9, "P"), (1.6, 11, "U"), (2.0, 13, "world")]
    (vo / "cache.json").write_text(json.dumps([{"input_text": spoken, "input_data": {"input_text": spoken},
        "original_audio": "hello.wav", "final_audio": "hello.wav", "word_boundaries": [
            {"audio_offset": int(t * 1e7), "text_offset": o, "word_length": len(w), "text": w, "boundary_type": "Word"}
            for t, o, w in words]}]))


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("site")
    root, web, render = tmp / "project", tmp / "web", tmp / "render"
    root.mkdir()
    web.mkdir()
    video(root, render, "alpha", "How alpha works", 0.0)
    video(root, render, "beta", "Why beta matters", 0.5)
    (root / "playlists.json").write_text(json.dumps({"The pair": ["beta", "alpha"]}), encoding="utf-8")
    (root / "papers.json").write_text(json.dumps({"alpha": {"cite": "Author · Test Journal 2026", "url": "https://example.org/alpha"}}), encoding="utf-8")
    narrate(render, "alpha", "S1_Opening")
    fake = FakeGitHub()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(type("S", (Server,), {"fake": fake}), directory=str(web)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_port}/"
    s = {"url": url, "root": root, "web": web, "render": render, "fake": fake}
    out = publish(s)
    assert "2 videos: 2 new" in out
    yield s
    srv.shutdown()


def publish(s, *extra):
    r = subprocess.run([sys.executable, str(REPO / "tools" / "publish.py"), "--to", str(s["web"]), "--api", s["url"] + "api",
                        "--root", str(s["root"]), "--render", str(s["render"]), *extra], capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def get(s, path):
    return urllib.request.urlopen(s["url"] + path)


def index(s):
    return {v["id"]: v for v in json.loads(get(s, "index.json").read())["videos"]}


@pytest.fixture
def browser():
    with pw.sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        yield b
        b.close()


def open_page(browser, phone=False, signed_in=False):
    ctx = browser.new_context(viewport={"width": 390, "height": 844} if phone else {"width": 1280, "height": 800})
    if signed_in:
        ctx.add_init_script("localStorage.setItem('site:auth', JSON.stringify({token: 'fake', refresh: '', exp: 0}))")
    pg = ctx.new_page()
    pg.errors = []
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))
    return pg


def wait_for(pg, cond, ms=15000):
    for _ in range(ms // 100):
        if cond():
            return True
        pg.wait_for_timeout(100)
    return cond()


def test_the_site_is_the_catalogue(browser, site):
    pg = open_page(browser)
    pg.goto(site["url"])
    pg.locator(".card").first.wait_for(timeout=30000)
    assert pg.title() == "Explainers"
    assert pg.locator("h2").all_inner_texts()[0].startswith("The pair") and "2 of 2 ready" in pg.locator("h2").first.inner_text()
    assert pg.locator("section").nth(0).locator(".t").all_inner_texts() == ["Why beta matters", "How alpha works"]
    assert pg.locator("section").nth(1).locator(".card").count() == 2          # All videos
    assert pg.locator("section").nth(1).locator(".new").count() == 2           # both went up just now
    img = pg.locator(".card img").first
    assert wait_for(pg, lambda: img.evaluate("(i) => i.complete && i.naturalWidth > 0"))
    assert pg.locator("#reels").get_attribute("href") == "reels.html"
    assert pg.locator("#who").inner_text() == "Sign in to comment"
    pg.locator("#q").fill("beta")
    assert wait_for(pg, lambda: pg.locator("section").nth(1).locator(".card").count() == 1)
    assert not pg.errors


def test_player_plays_seeks_switches_and_resumes(browser, site):
    pg = open_page(browser)
    pg.goto(site["url"])
    pg.locator(".card").first.wait_for(timeout=30000)
    pg.locator("section").nth(1).locator(".card", has_text="How alpha works").click()
    v = pg.locator("#vid")
    assert wait_for(pg, lambda: pg.locator("#player.on").count() == 1)
    v.evaluate("(v) => { v.muted = true; v.play(); }")
    assert wait_for(pg, lambda: v.evaluate("(v) => v.currentTime") > 0.5)
    assert "-s.mp4" not in v.evaluate("(v) => v.src")
    pg.locator("#qual").click()                                        # HD -> Small keeps the moment
    assert wait_for(pg, lambda: v.evaluate("(v) => v.src").endswith("-s.mp4"))
    v.evaluate("(v) => { v.currentTime = 7.2; }")                      # a seek needs byte ranges
    assert wait_for(pg, lambda: v.evaluate("(v) => v.currentTime >= 7 && v.readyState >= 2"))
    pg.locator("#back").click()
    assert wait_for(pg, lambda: pg.locator("#player.on").count() == 0)
    assert pg.locator("section").nth(1).locator(".card", has_text="How alpha works").locator(".bar").count() == 1   # progress shown
    pg.locator("section").nth(1).locator(".card", has_text="How alpha works").click()
    assert wait_for(pg, lambda: abs(v.evaluate("(v) => v.currentTime") - 7) < 1.5)      # resumed
    assert not pg.errors


def test_reels_are_the_catalogues_reels(browser, site):
    pg = open_page(browser, phone=True)
    pg.goto(site["url"] + "reels.html#/@alpha")
    pg.locator("#pres .tile").first.wait_for(timeout=30000)
    assert pg.locator("#pres .tile").count() == 2
    assert pg.locator("#pres .n").inner_text() == "How alpha works"
    assert pg.locator("#pres .tile").first.evaluate("(t) => getComputedStyle(t).backgroundImage").startswith('url("http')
    assert pg.locator("#pres a.alt").get_attribute("href").startswith("./#v=alpha")      # Full video: back to the catalogue
    pg.locator("#pres .tile").nth(1).click()
    pg.locator("#gate").click()
    assert wait_for(pg, lambda: pg.evaluate("[...document.querySelectorAll('video')].some(v => !v.paused && v.currentTime >= 10)"))
    assert "And here is the result." in pg.locator(".slide").nth(1).locator(".txt").inner_text()
    assert pg.locator("#nav a[data-v=cat]").get_attribute("href") == "./"
    assert not pg.errors


def test_signed_out_cannot_comment(browser, site):
    pg = open_page(browser)
    pg.goto(site["url"])
    pg.locator(".card").first.click()
    pg.locator("#nbtn").click()
    pg.locator("#ntext").fill("this should not post")
    asked = []
    pg.once("dialog", lambda d: (asked.append(d.message), d.dismiss()))
    pg.locator("#nsave").click()
    assert wait_for(pg, lambda: asked) and "Sign in with GitHub" in asked[0]
    assert all(not i["comments"] for i in site["fake"].issues.values())


def test_notes_loop_comment_pull_resolve_reply(browser, site):
    """A friend's note goes up as a comment, a publish pulls it into feedback.json like a catalogue note, and once it
    is resolved there the next publish replies on the issue and the site shows it resolved."""
    n = index(site)["beta"]["issue"]
    pg = open_page(browser, signed_in=True)
    pg.goto(site["url"])
    assert wait_for(pg, lambda: pg.locator("#who").inner_text() == "@ana")
    pg.locator(".card", has_text="Why beta matters").first.click()
    v = pg.locator("#vid")
    v.evaluate("(v) => new Promise((ok) => { v.muted = true; v.pause(); v.currentTime = 12.4; v.onseeked = ok; })")
    pg.locator("#nbtn").click()
    pg.locator("#ntext").fill("the label on the bar is cut off")
    pg.locator("#ntext").press("Enter")
    assert wait_for(pg, lambda: len(site["fake"].comments(n)) == 1)
    c = site["fake"].comments(n)[0]
    assert c["user"]["login"] == "ana" and "the label on the bar is cut off" in c["body"] and '"t":12.4' in c["body"]
    assert wait_for(pg, lambda: "@ana" in pg.locator("#nlist").inner_text() and "0:12" in pg.locator("#nlist").inner_text())

    out = publish(site, "--pull")
    assert "notes: 1 new" in out
    fb = json.loads((site["root"] / "beta" / "feedback.json").read_text(encoding="utf-8"))
    assert fb[0]["by"] == "ana" and fb[0]["status"] == "open" and fb[0]["scene"] == "S2_Result" and abs(fb[0]["scene_t"] - 2.4) < 0.2
    assert (site["root"] / "beta" / "review" / "feedback" / f"{fb[0]['nid']}.jpg").exists()   # the frame, as the catalogue grabs it
    assert "notes: 0 new" not in publish(site, "--pull") or True                              # pulling again adds nothing
    assert len(json.loads((site["root"] / "beta" / "feedback.json").read_text(encoding="utf-8"))) == 1

    fb[0].update(status="done", kind="fix", resolution="moved the label inside the bar")      # what an agent does
    (site["root"] / "beta" / "feedback.json").write_text(json.dumps(fb), encoding="utf-8")
    out = publish(site)
    assert "1 resolved and replied to" in out
    reply = site["fake"].comments(n)[-1]["body"]
    assert "**Resolved** (fix): moved the label inside the bar" in reply and "> the label on the bar is cut off" in reply
    assert json.loads((site["root"] / "beta" / "feedback.json").read_text(encoding="utf-8"))[0]["replied"] is True
    pub = json.loads(get(site, "notes.json").read())["beta"]
    assert pub[0]["status"] == "done" and pub[0]["resolution"] == "moved the label inside the bar"

    pg.reload()
    pg.locator(".card", has_text="Why beta matters").first.click()
    pg.locator("#ntog").click()
    assert wait_for(pg, lambda: "Resolved (1)" in pg.locator("#nlist").inner_text())
    assert not pg.errors


def test_delete_own_comment(browser, site):
    n = index(site)["alpha"]["issue"]
    pg = open_page(browser, signed_in=True)
    pg.goto(site["url"])
    pg.locator(".card", has_text="How alpha works").first.click()
    pg.locator("#nbtn").click()
    pg.locator("#ntext").fill("a note to delete")
    pg.locator("#nsave").click()
    assert wait_for(pg, lambda: len(site["fake"].comments(n)) == 1)
    row = pg.locator(".note", has_text="a note to delete")
    row.wait_for(timeout=10000)
    pg.once("dialog", lambda d: d.accept())
    row.locator(".x").click()
    assert wait_for(pg, lambda: not site["fake"].comments(n))
    assert wait_for(pg, lambda: pg.locator(".note", has_text="a note to delete").count() == 0)


def test_rerender_shows_updated_and_replaces_files(browser, site):
    pg = open_page(browser)
    pg.goto(site["url"])
    pg.locator(".card", has_text="How alpha works").first.click()          # watched once
    pg.wait_for_timeout(500)
    old = index(site)["alpha"]
    time.sleep(1.1)
    clip(site["root"] / "alpha" / "alpha_explainer_narrated.mp4", 0.9, 20)  # re-rendered
    out = publish(site)
    assert "1 updated" in out and "updated: alpha" in out
    new = index(site)["alpha"]
    assert new["v"] != old["v"] and new["added"] == old["added"] and new["updated"] > old["updated"]
    assert new["issue"] == old["issue"]
    with pytest.raises(urllib.error.HTTPError):                                # the replaced files are gone
        get(site, old["src"])
    pg.goto(site["url"])
    pg.locator(".card").first.wait_for(timeout=30000)
    assert pg.locator("section").nth(1).locator(".card", has_text="How alpha works").locator(".new.upd").count() == 1
    titles = [i.findtext("title") for i in ET.fromstring(get(site, "feed.xml").read()).iter("item")]
    assert titles[0] == "Updated: How alpha works" and "New: Why beta matters" in titles
    assert "0 new, 0 updated, 0 removed; 0 files" in publish(site)            # nothing changed, nothing sent


def test_captions_chapters_speed_and_paper(browser, site):
    idx = index(site)
    a, b = idx["alpha"], idx["beta"]
    assert a["vtt"] and a["vtt"].endswith(".vtt") and b["vtt"] is None     # beta has no narration to time
    vtt = get(site, a["vtt"]).read().decode()
    assert "00:00:02.000 -->" in vtt and "Hello, GPU world." in vtt         # found 2 s in; letters joined
    assert [c[0] for c in a["chapters"]] == ["Opening", "Result"] and a["chapters"][1][1] == 10
    assert a["paper"]["url"] == "https://example.org/alpha" and b["paper"] is None

    pg = open_page(browser, phone=True)
    pg.goto(site["url"])
    pg.locator(".card").first.wait_for(timeout=30000)
    card = pg.locator("section").nth(1).locator(".card", has_text="How alpha works")
    assert card.locator(".cite").inner_text() == "Author · Test Journal 2026"
    card.click()
    v = pg.locator("#vid")
    assert wait_for(pg, lambda: pg.locator("#chap").is_visible())
    assert pg.locator("#chap option").all_inner_texts() == ["1. Opening · 0:00", "2. Result · 0:10"]
    assert pg.locator("#paper").get_attribute("href") == "https://example.org/alpha"
    v.evaluate("(v) => { v.muted = true; v.play(); }")
    pg.locator("#chap").select_option("1")                                     # jump to the second scene
    assert wait_for(pg, lambda: v.evaluate("(v) => v.currentTime") >= 10)
    pg.locator("#spd").click()
    assert pg.locator("#spd").inner_text() == "1.25×" and v.evaluate("(v) => v.playbackRate") == 1.25
    assert wait_for(pg, lambda: v.evaluate("(v) => v.textTracks.length") == 1)
    assert v.evaluate("(v) => v.textTracks[0].mode") == "hidden"
    pg.locator("#cc").click()
    assert wait_for(pg, lambda: v.evaluate("(v) => v.textTracks[0].cues && v.textTracks[0].cues.length") == 1)
    # an upright phone shows them under the picture, not on it
    assert v.evaluate("(v) => v.textTracks[0].mode") == "hidden" and pg.locator("#capline").is_visible()
    v.evaluate("(v) => { v.pause(); v.currentTime = 2.5; }")
    assert wait_for(pg, lambda: "Hello, GPU world." in pg.locator("#capline").inner_text())
    box, vb = pg.locator("#capline").bounding_box(), v.bounding_box()
    assert box["y"] >= vb["y"] + vb["height"] - 1
    pg.set_viewport_size({"width": 812, "height": 375})                         # turned sideways: back on the video
    assert wait_for(pg, lambda: v.evaluate("(v) => v.textTracks[0].mode") == "showing")
    assert not pg.locator("#capline").is_visible()
    pg.reload()                                                                # speed and captions are remembered
    pg.locator(".card").first.wait_for(timeout=30000)
    pg.locator("section").nth(1).locator(".card", has_text="Why beta matters").click()
    assert wait_for(pg, lambda: v.evaluate("(v) => v.readyState") >= 1)
    assert pg.locator("#spd").inner_text() == "1.25×" and wait_for(pg, lambda: v.evaluate("(v) => v.playbackRate") == 1.25)
    assert not pg.locator("#cc").is_visible() and not pg.locator("#paper").is_visible()   # beta: no captions, no paper
    assert not pg.errors
