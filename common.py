"""Shared look and plumbing for the narrated paper videos; each video folder imports it (`from common import *`).
ENGINE picks the renderer: gx (default since 2026-10-25) is ManimGX on the GPU (common_gx.py), ce is Manim CE
(common_ce.py), which older videos pin in their render.sh and which vlint's skip-mode checks always use. Scenes are
written in the API the two share, so the same file renders under both."""
import os

if os.environ.get("ENGINE", "gx") == "gx":
    from common_gx import *  # noqa: F401,F403
else:
    from common_ce import *  # noqa: F401,F403
