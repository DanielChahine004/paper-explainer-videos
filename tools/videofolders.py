"""Where a video's folder is. A video is a folder at the repo root (the worked examples live there), or under
private/: your own videos, kept in a git repository of their own that this one ignores. Every tool finds a video by
name in both, so your videos use the pipeline without being part of it, and what you improve here everyone gets."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = "private"


def roots(root=None):
    """[root, root/private]: where video folders are."""
    r = Path(root) if root else ROOT
    return [r, r / PRIVATE]


def folder(vid, root=None):
    """<root>/<vid>, else <root>/private/<vid>. A video that does not exist yet goes under private/ when there is
    one (your own videos stay out of the public repo by default), else at the root."""
    top, priv = roots(root)
    if (top / vid).is_dir():
        return top / vid
    return priv / vid if (priv / vid).is_dir() or priv.is_dir() else top / vid


def glob(pattern, root=None):
    """pattern ("*/feedback.json") matched at the root and under private/."""
    return [p for r in roots(root) for p in sorted(r.glob(pattern))]


def data(name, root=None):
    """A project file that is yours rather than the pipeline's (playlists.json): private/<name> when private/ has
    one, else <root>/<name>."""
    top, priv = roots(root)
    return priv / name if (priv / name).exists() else top / name
