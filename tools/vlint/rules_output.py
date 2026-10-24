"""Output rules: read what the render produced. Mode "parts" runs before the scenes are joined (is every scene
there, fresh, and clean at runtime?); mode "final" runs on the joined file (resolution, sync, length). Each rule
gets an OutputCtx and yields (where, message), where is a scene name or a file name."""
import json
import shutil
import subprocess

from .core import Finding, opt, rule, undump
from .fingerprint import fingerprint


def probe(path):
    """{'video': seconds, 'audio': seconds, 'width', 'height'} from ffprobe."""
    exe = shutil.which("ffprobe") or "ffprobe"
    r = subprocess.run([exe, "-v", "error", "-show_entries", "stream=codec_type,duration,width,height:format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    out = {"format": float(d.get("format", {}).get("duration", 0) or 0)}
    for s in d.get("streams", []):
        t = s.get("codec_type")
        if t in ("video", "audio") and t not in out:
            out[t] = float(s.get("duration") or out["format"])
            if t == "video":
                out["width"], out["height"] = int(s["width"]), int(s["height"])
    return out


class OutputCtx:
    def __init__(self, video_dir, script, res, scenes, config, mode, final=None, pattern=None):
        self.video_dir, self.script, self.res, self.scenes = video_dir, script, res, scenes
        self.config, self.mode, self.final = config, mode, final
        pattern = pattern or "m_{scene}/videos/{stem}/{res}/{scene}.mp4"
        self.parts = {s: video_dir / pattern.format(scene=s, stem=script.stem, res=res) for s in scenes}
        self._fp, self._rec, self._probe = {}, {}, {}

    def record(self, scene):
        if scene not in self._rec:
            p = self.parts[scene]
            r = p.with_name(p.stem + ".vlint.json")
            self._rec[scene] = json.loads(r.read_text(encoding="utf-8")) if r.exists() else None
        return self._rec[scene]

    def fp(self, scene):
        if scene not in self._fp:
            self._fp[scene] = fingerprint(self.script, scene)
        return self._fp[scene]

    def probe(self, path):
        if path not in self._probe:
            self._probe[path] = probe(path)
        return self._probe[path]

    def stale(self, scene):
        """Why this scene's video can't be reused, or None if it can."""
        p = self.parts[scene]
        if not p.exists():
            return "not rendered"
        rec = self.record(scene)
        if rec is None:
            return "rendered without a vlint record, so its source is unknown"
        if rec.get("fingerprint") != self.fp(scene):
            return "its code, shared helpers or assets changed since it was rendered"
        recf = p.with_name(p.stem + ".vlint.json")
        if p.stat().st_mtime + 2 < recf.stat().st_mtime:
            return "its last render did not finish writing the video"
        return None


@rule("missing-scene", "output", "error", "A scene's video is missing at join time.", "Part III, step 6",
      "render it (render.sh renders every missing or stale scene)")
def missing_scene(ctx):
    if ctx.mode != "parts":
        return
    for s, p in ctx.parts.items():
        if not p.exists():
            yield s, f"no video at {p.relative_to(ctx.video_dir)}"


@rule("stale-scene", "output", "error", "A scene's video was rendered from older code than the script now holds, so the "
      "join would ship an old version (i3M revision).", "Part III, step 6",
      "re-render it: delete its mp4 or run render.sh, which re-renders stale scenes itself")
def stale_scene(ctx):
    if ctx.mode != "parts":
        return
    for s, p in ctx.parts.items():
        why = ctx.stale(s) if p.exists() else None
        if why and ctx.record(s) is not None:
            yield s, why


@rule("unchecked-scene", "output", "warn", "A scene was rendered without the runtime monitor (old video, or a scene "
      "not built on common.Narrated), so runtime rules never saw it.", "", "re-render it once")
def unchecked_scene(ctx):
    if ctx.mode != "parts":
        return
    for s, p in ctx.parts.items():
        if p.exists() and (ctx.record(s) is None or not ctx.record(s).get("monitor", True)):
            yield s, "no runtime record"


@rule("output-resolution", "output", "error", "The joined video is above 1080p.", "Part III, step 6",
      "render with QUALITY=-qh or lower")
def output_resolution(ctx):
    if ctx.mode == "final":
        d = ctx.probe(ctx.final)
        if d.get("height", 0) > 1080 or d.get("width", 0) > 1920:
            yield ctx.final.name, f"{d['width']}x{d['height']}"


@rule("av-sync", "output", "error", "The joined narration does not end where the scenes say it should, so it drifts "
      "against the picture (the stream-copy join bug lost ~1 s per scene).", "Part III, step 6",
      "join with re-encoded audio (aresample=async=1)")
def av_sync(ctx):
    if ctx.mode == "final":
        d = ctx.probe(ctx.final)
        parts = [p for p in ctx.parts.values() if p.exists()]
        if "audio" not in d:
            yield ctx.final.name, "no audio stream"
            return
        last = ctx.probe(parts[-1])
        # every scene but the last contributes its full video length; the last scene's silent tail has no audio
        want = sum(ctx.probe(p)["video"] for p in parts[:-1]) + last.get("audio", last["video"])
        if abs(d["audio"] - want) > float(opt(ctx, "av_tolerance", 0.5)):
            yield ctx.final.name, f"narration ends at {d['audio']:.2f}s, scenes put it at {want:.2f}s"
        durs = audio_packets(ctx.final)
        if durs:
            typical = sorted(durs)[len(durs) // 2]
            long_ = [x for x in durs if x > 3 * typical]
            if long_:
                yield ctx.final.name, (f"{len(long_)} stretched audio packet(s) up to {max(long_):.2f}s: gaps that "
                                       "players skip, so the voice runs ahead")


def audio_packets(path):
    exe = shutil.which("ffprobe") or "ffprobe"
    r = subprocess.run([exe, "-v", "error", "-select_streams", "a:0", "-show_entries", "packet=duration_time",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return [float(x) for x in r.stdout.split() if x.replace(".", "", 1).isdigit()]


@rule("join-duration", "output", "error", "The joined video is not as long as its scenes put together: a scene was "
      "dropped or duplicated.", "Part III, step 6", "check list.txt and the SCENES list")
def join_duration(ctx):
    if ctx.mode == "final":
        total = sum(ctx.probe(p)["video"] for p in ctx.parts.values() if p.exists())
        got = ctx.probe(ctx.final)["video"]
        if abs(total - got) > float(opt(ctx, "join_tolerance", 1.0)):
            yield ctx.final.name, f"{got:.1f}s joined vs {total:.1f}s of scenes"


def runtime_findings(ctx):
    """Findings the monitor saved while each scene rendered, so they gate the join like any other."""
    out = []
    for s in ctx.scenes:
        rec = ctx.record(s) if ctx.parts[s].exists() else None
        if rec and rec.get("fingerprint") == ctx.fp(s):
            for f in undump(rec.get("findings", [])):
                f.file = ctx.script.name
                out.append(f)
    return out
