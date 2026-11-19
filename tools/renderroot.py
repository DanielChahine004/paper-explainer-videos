"""Where the renders are, and how to run the render env's own programs on them, on Linux, macOS and Windows.

The render root (RENDER_ROOT, default ~/slab_render) is where tools/sync.sh copies each video and renders it; its
pixi env holds ffmpeg and the Python the captions are aligned with. On Windows the render root is native (the
tools run from Git Bash) unless the only one is inside WSL: a Windows checkout rendered in WSL, whose programs are
then run through `wsl` and given /mnt/c paths. Nothing else in the publishing tools needs to know which it is.
"""
import os
import re
import subprocess
from pathlib import Path


def _default():
    if os.environ.get("RENDER_ROOT"):
        return Path(os.environ["RENDER_ROOT"])
    home = Path.home() / "slab_render"
    if os.name == "nt" and not home.exists():
        try:   # a Windows checkout rendered in WSL: the first WSL home with a render root
            return next(Path(r"\\wsl.localhost").glob("*/home/*/slab_render"))
        except (OSError, StopIteration):
            pass
    return home


RENDER = _default()


def set_root(p):
    global RENDER
    RENDER = Path(p)


def via_wsl():
    """True when the render root is inside WSL and this is Windows: its programs run through `wsl`."""
    return os.name == "nt" and str(RENDER).replace("/", "\\").lower().startswith("\\\\wsl")


def inside(p):
    """A path as the render env's programs see it: itself, unless they run in WSL (a /mnt/c or WSL-native path)."""
    s = str(Path(p).resolve() if not str(p).startswith(("\\\\", "//")) else p)
    if not via_wsl():
        return s
    s = s.replace("\\", "/")
    m = re.match(r"//wsl(?:\.localhost|\$)/[^/]+(/.*)", s, re.I)
    if m:
        return m.group(1)
    return f"/mnt/{s[0].lower()}{s[2:]}"


def run(cmd, **kw):
    """subprocess.run, through `wsl` when the render env lives there."""
    return subprocess.run((["wsl"] if via_wsl() else []) + [str(c) for c in cmd], **kw)


def env_bin(name):
    """A program from the render root's pixi env (ffmpeg, ffprobe, python), as run() needs it named."""
    env = RENDER / ".pixi" / "envs" / "default"
    if via_wsl():
        return inside(RENDER) + f"/.pixi/envs/default/bin/{name}"
    if os.name == "nt":
        return str(env / "python.exe") if name == "python" else str(env / "Library" / "bin" / f"{name}.exe")
    return str(env / "bin" / name)


def scene_files(vid, root=None):
    """The scene mp4s of a video's last join, in order, from its list.txt (written by render_lib.sh with whatever
    absolute path the render root had there: /home/x/slab_render/..., C:/Users/x/slab_render/...)."""
    root = Path(root or RENDER)
    out = []
    for line in (root / vid / "list.txt").read_text().splitlines():
        m = re.match(r"file '(.+)'", line.strip())
        if m:
            rel = re.split(r"[/\\]" + re.escape(root.name) + r"[/\\]", m.group(1).replace("\\", "/"), maxsplit=1)
            out.append(root / rel[-1] if len(rel) == 2 else Path(m.group(1)))
    return out
