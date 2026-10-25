"""Output rules: read what the render produced. Mode "parts" runs before the scenes are joined (is every scene
there, fresh, and clean at runtime?); mode "final" runs on the joined file (resolution, sync, length). Each rule
gets an OutputCtx and yields (where, message), where is a scene name or a file name."""
import json
import re
import shutil
import struct
import subprocess

from .core import Finding, opt, rule, undump
from .fingerprint import fingerprint


def track_durations(path):
    """{'vide': seconds, 'soun': seconds} from each track's mdhd box: what the container says each track lasts."""
    def boxes(b, lo, hi):
        while lo + 8 <= hi:
            size, kind = struct.unpack(">I4s", b[lo:lo + 8])
            head = 8
            if size == 1:
                size, head = struct.unpack(">Q", b[lo + 8:lo + 16])[0], 16
            elif size == 0:
                size = hi - lo
            if size < head:
                return
            yield kind, lo + head, lo + size
            lo += size
    with open(path, "rb") as f:
        b = f.read()
    out = {}
    for kind, lo, hi in boxes(b, 0, len(b)):
        if kind != b"moov":
            continue
        for k2, lo2, hi2 in boxes(b, lo, hi):
            if k2 != b"trak":
                continue
            for k3, lo3, hi3 in boxes(b, lo2, hi2):
                if k3 != b"mdia":
                    continue
                dur = typ = None
                for k4, lo4, hi4 in boxes(b, lo3, hi3):
                    if k4 == b"mdhd":
                        v = b[lo4]
                        ts, du = (struct.unpack(">II", b[lo4 + 12:lo4 + 20]) if v == 0
                                  else struct.unpack(">IQ", b[lo4 + 20:lo4 + 32]))
                        dur = du / ts if ts else None
                    elif k4 == b"hdlr":
                        typ = b[lo4 + 8:lo4 + 12].decode("latin-1")
                if dur is not None and typ and typ not in out:
                    out[typ] = dur
    return out


def probe(path):
    """{'video': seconds, 'audio': seconds, 'width', 'height'} from ffprobe. The video length is the longer of
    ffprobe's stream duration and the track's own mdhd duration: after a concat join of ManimGX's variable-rate,
    B-frame h264, ffprobe's stream duration comes out seconds short (i3m_pet: 452.7 s for a 454.9 s track)."""
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
    if "video" in out and str(path).endswith(".mp4"):
        try:
            out["video"] = max(out["video"], track_durations(path).get("vide", 0))
        except (OSError, struct.error):
            pass
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
        if not rec.get("rechecked") and p.stat().st_mtime + 2 < recf.stat().st_mtime:
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


_GX_EDGE = re.compile(r"\[\d+\] t=([\d.]+)\S*\s+\(.*?\)\s+(.*?past the \w+ edge)")


@rule("gx-frame-edge", "output", "error", "ManimGX's own layout pass found something past the frame edge in the real "
      "render. Typst sets maths a little larger than CE's LaTeX, so CE's frame-clip can pass what GX cuts off "
      "(liquid_tc Solver's last equation).", "Part II, Layout (fit_frame)",
      "move it in or shrink the stack (keep ~0.3 from the edge); the render log m_<Scene>.log lists each one")
def gx_frame_edge(ctx):
    if ctx.mode != "parts":
        return
    for s, p in ctx.parts.items():
        log = ctx.video_dir / f"m_{s}.log"
        if not p.exists() or not log.exists():
            continue
        for m in _GX_EDGE.finditer(log.read_bytes().decode("utf-8", "replace")):
            yield s, f"t={float(m.group(1)):.1f}s: {m.group(2)}"


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


def needs_recheck(ctx, scene):
    """The scene's video is current but its findings came from an older rule set."""
    from .fingerprint import rules_hash
    rec = ctx.record(scene) if ctx.parts[scene].exists() else None
    return bool(rec) and ctx.stale(scene) is None and rec.get("monitor", True) and rec.get("rules") != rules_hash(ctx.script)


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
