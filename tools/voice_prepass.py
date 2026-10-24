"""Generate a video's narration before its scenes render, with one voice model per worker instead of one per scene.

Scenes render as separate manim processes; left to themselves, each loads its own copy of Chatterbox and Whisper, so
side-by-side scenes fill the GPU's memory and take turns on it. This reads every voiceover text from the script
(vlint's parser), loads the model once, and writes each line into the scene's own cache (m_<Scene>/voiceovers) exactly
as the render would, so the render then only reads cached audio and needs no GPU. A line already cached in another scene of the same
video (a renamed or split scene) is copied instead of regenerated. Computed texts, which the parser cannot read,
are left for the render.
  pixi run python ../tools/voice_prepass.py meta_vo.py [Scene ...]     from the video folder; all scenes when none named
Each scene's cache gets a .ready file when its narration is done, so render_lib.sh renders it (CPU) while the
rest is still being voiced (GPU).
"""
import ast
import json
import multiprocessing as mp
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]

from manim_voiceover.defaults import DEFAULT_VOICEOVER_CACHE_DIR, DEFAULT_VOICEOVER_CACHE_JSON_FILENAME  # noqa: E402
from manim_voiceover.helper import remove_bookmarks  # noqa: E402
from manim_voiceover.services.cache import append_voiceover_cache_entry  # noqa: E402
from vlint.script import load_script, render_scenes  # noqa: E402
from voices import make_service  # noqa: E402

# Model copies run side by side. One copy leaves the GPU ~60% idle (token-by-token sampling); each copy takes
# ~4.6 GB, so 2 fit an 11 GB card. VOICE_WORKERS=1 on a smaller card.
WORKERS = int(os.environ.get("VOICE_WORKERS", "2"))
READY = ".ready"   # in m_<Scene>/voiceovers once all of that scene's narration is cached


def scene_texts(script):
    """{scene: [voiceover text or None, ...]} in source order."""
    out = {}
    for cls in script.scenes:
        vos = {id(v.node): v for v in script.voiceovers}
        withs = sorted((n for n in ast.walk(cls) if id(n) in vos), key=lambda n: n.lineno)
        out[cls.name] = [vos[id(w)].text for w in withs]
    return out


def main():
    path = Path(sys.argv[1])
    s = load_script(path, None)
    texts = scene_texts(s)
    scenes = sys.argv[2:] or render_scenes(s.render_sh) or list(texts)
    svc = make_service(cache_dir=".")
    # every cached line of this video, so a line that moved to another scene is copied, not regenerated
    known = {}
    for cj in Path(".").glob(f"m_*/{DEFAULT_VOICEOVER_CACHE_DIR}/{DEFAULT_VOICEOVER_CACHE_JSON_FILENAME}"):
        for e in json.loads(cj.read_text() or "[]"):
            known.setdefault(json.dumps(e.get("input_data"), sort_keys=True), (cj.parent, e))
    todo, skipped = [], 0
    for sc in scenes:
        cache = Path(f"m_{sc}") / DEFAULT_VOICEOVER_CACHE_DIR
        (cache / READY).unlink(missing_ok=True)
        for t in texts.get(sc, []):
            if t is None:
                skipped += 1
                continue
            spoken = " ".join(remove_bookmarks(t).split())
            data = {"input_text": spoken, "service": svc.name, "voice": getattr(svc, "voice", "")}
            cache.mkdir(parents=True, exist_ok=True)
            if svc.get_cached_result(data, cache) is not None:
                continue
            hit = known.get(json.dumps(data, sort_keys=True))
            if hit:
                src, e = hit
                for f in (e["original_audio"], Path(e["original_audio"]).with_suffix(".words.json").name):
                    if (src / f).exists():
                        shutil.copy2(src / f, cache / f)
                append_voiceover_cache_entry(cache / DEFAULT_VOICEOVER_CACHE_JSON_FILENAME, {**e, "input_text": t})
                print(f"  copied  {sc}: {spoken[:60]}")
                continue
            todo.append((sc, cache, t, spoken))
    if skipped:
        print(f"  {skipped} computed text(s) left for the render")
    waiting = {item[0] for item in todo}
    for sc in scenes:
        if sc not in waiting:
            (Path(f"m_{sc}") / DEFAULT_VOICEOVER_CACHE_DIR / READY).touch()
    if not todo:
        print("== narration: all cached")
        return
    chars = sum(len(sp) for *_, sp in todo)
    # whole scenes per worker (two processes never append to one cache.json), in render order onto the lightest
    # worker, so the first scenes are ready first and the render can start on them (render_lib.sh)
    by_scene = {}
    for item in todo:
        by_scene.setdefault(item[0], []).append(item)
    n = max(1, min(WORKERS, len(by_scene)))
    shares, load = [[] for _ in range(n)], [0] * n
    for items in by_scene.values():
        k = load.index(min(load))
        shares[k] += items
        load[k] += sum(len(x[3]) for x in items)
    print(f"== narration: {len(todo)} line(s), {chars} characters, {n} model cop{'y' if n == 1 else 'ies'}", flush=True)
    t0 = time.time()
    if n == 1:
        work(shares[0], 0)
    else:
        ctx = mp.get_context("spawn")
        procs = [ctx.Process(target=work, args=(sh, k)) for k, sh in enumerate(shares)]
        for pr in procs:
            pr.start()
        for pr in procs:
            pr.join()
        if any(pr.exitcode for pr in procs):
            sys.exit("voice_prepass: a worker failed")
    dt = time.time() - t0
    print(f"== narration: {len(todo)} line(s) in {dt:.0f} s ({1000 * dt / chars:.0f} ms per character)")


def work(items, wid):
    svc = make_service(cache_dir=".")
    for k, (sc, cache, t, spoken) in enumerate(items, 1):
        svc.cache_dir = str(cache)
        t1 = time.time()
        svc._wrap_generate_from_text(t)
        print(f"  w{wid} [{k}/{len(items)}] {sc} {time.time() - t1:5.1f} s  {spoken[:60]}", flush=True)
        if k == len(items) or items[k][0] != sc:
            (cache / READY).touch()


if __name__ == "__main__":
    main()
