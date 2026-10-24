"""Shared look and plumbing for the narrated paper videos; each video folder imports it (`from common import *`).
ENGINE picks the renderer: gx is ManimGX on the GPU (common_gx.py), the default wherever manimgx is installed
(since 2026-10-25); ce is Manim CE (common_ce.py), which older videos pin in their render.sh and which vlint's
skip-mode checks always use. Scenes are written in the API the two share, so the same file renders under both."""
import importlib.util
import os

if (os.environ.get("ENGINE") or ("gx" if importlib.util.find_spec("manimgx") else "ce")) == "gx":
    from common_gx import *  # noqa: F401,F403
else:
    from common_ce import *  # noqa: F401,F403
