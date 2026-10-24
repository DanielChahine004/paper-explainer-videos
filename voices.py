"""Speech services for manim-voiceover.

TTS=chatterbox (default): Resemble AI's Chatterbox on the GPU, a natural narrator voice.
    Each sentence is synthesised separately, transcribed back with Whisper and
    re-synthesised with another seed if the words do not match, so a mumbled or
    truncated take never reaches the video. TTS_VOICE=/path/to/clip.wav clones that
    voice (10-20 s of clean speech); unset uses Chatterbox's built-in voice.
TTS=espeak: robotic, needs only espeak-ng; for checking timing only, never for a finished video.

Every service also returns word timings, so scenes can sync to <bookmark mark='x'/> tags placed
in the narration text (see docs/DESIGN.md). Bookmarks are stripped before synthesis and before the
cache lookup, so adding or moving one never regenerates the audio.
"""
import difflib
import json
import os
import re
import subprocess
from pathlib import Path

import numpy as np
from manim_voiceover.helper import remove_bookmarks
from manim_voiceover.services.base import SpeechService
from manim_voiceover.tracker import AUDIO_OFFSET_RESOLUTION

_ASR = None


def _asr():
    """Whisper on the CPU for word timings, so cached-audio renders never touch the GPU."""
    global _ASR
    if _ASR is None:
        from faster_whisper import WhisperModel

        _ASR = WhisperModel("small.en", device="cpu", compute_type="int8")
    return _ASR


def _word_boundaries(audio_path, text):
    """Start time of every word of `text` in the audio: Whisper's word timestamps, aligned to the
    script word by word, interpolated by character offset where the two disagree ('4mm' for
    'four millimetres'). Cached beside the audio as <name>.words.json."""
    side = Path(audio_path).with_suffix(".words.json")
    if side.exists():
        return json.loads(side.read_text())
    segs, info = _asr().transcribe(str(audio_path), language="en", word_timestamps=True, beam_size=5)
    heard = [(w.word, w.start) for s in segs for w in s.words]
    toks = [(m.start(), m.group()) for m in re.finditer(r"\S+", text)]
    norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())
    sm = difflib.SequenceMatcher(None, [norm(t) for _, t in toks], [norm(w) for w, _ in heard], autojunk=False)
    anchors = {0: 0.0}
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            anchors[toks[blk.a + k][0]] = heard[blk.b + k][1]
    anchors[len(text)] = info.duration
    xs = np.array(sorted(anchors))
    ys = np.maximum.accumulate(np.array([anchors[x] for x in xs]))
    out = [{"audio_offset": int(float(np.interp(off, xs, ys)) * AUDIO_OFFSET_RESOLUTION), "text_offset": off,
            "word_length": len(t), "text": t, "boundary_type": "Word"} for off, t in toks]
    out.append({"audio_offset": int(info.duration * AUDIO_OFFSET_RESOLUTION), "text_offset": len(text),
                "word_length": 0, "text": "", "boundary_type": "Word"})
    side.write_text(json.dumps(out))
    return out


def _to_mp3(wav, mp3):
    # trim trailing silence (not leading: a soft first word can sit under any threshold) and
    # normalise loudness so every line sits at the same level
    af = ("areverse,silenceremove=start_periods=1:start_threshold=-55dB:start_silence=0.08,areverse,"
          "loudnorm=I=-16:TP=-1.5:LRA=7")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(wav), "-af", af, "-ar", "48000",
                    "-b:a", "192k", str(mp3)], check=True)
    Path(wav).unlink()


class _FileService(SpeechService):
    name = "base"

    def synth_wav(self, text, wav_path):
        raise NotImplementedError

    def generate_from_text(self, text, cache_dir=None, path=None, **kwargs):
        cache_dir = cache_dir or self.cache_dir
        spoken = " ".join(remove_bookmarks(text).split())
        input_data = {"input_text": spoken, "service": self.name, "voice": getattr(self, "voice", "")}
        cached = self.get_cached_result(input_data, cache_dir)
        if cached is not None:
            audio = cached["original_audio"]
        else:
            audio = path or self.get_audio_basename(input_data) + ".mp3"
            wav = Path(cache_dir) / (Path(audio).stem + ".wav")
            self.synth_wav(spoken, wav)
            _to_mp3(wav, Path(cache_dir) / audio)
        # the tracker locates bookmarks in input_text, so it keeps them; offsets refer to `spoken`
        return {"input_text": text, "input_data": input_data, "original_audio": audio,
                "word_boundaries": _word_boundaries(Path(cache_dir) / audio, spoken)}


class EspeakService(_FileService):
    name = "espeak"

    def __init__(self, voice="en-us", speed=165, **kwargs):
        self.voice, self.speed = voice, speed
        super().__init__(**kwargs)

    def synth_wav(self, text, wav_path):
        subprocess.run(["espeak-ng", "-v", self.voice, "-s", str(self.speed), "-w", str(wav_path), text], check=True)


def _letters(s):
    """Script or transcript reduced to bare letters, normalised the same way on both sides so that
    Whisper's '8x8', '1,600', '6mm', 'idealized', 'photo peak' and 'L' match the script's
    'eight by eight', 'sixteen hundred', 'six millimetre', 'idealised', 'photopeak' and 'ell'."""
    from num2words import num2words

    s = s.lower().replace("%", " percent").replace(",", "")
    s = re.sub(r"(\d)\s*x\s*(?=\d)", r"\1 by ", s)
    s = re.sub(r"(\d)\s*mm\b", r"\1 millimetre", s)
    s = re.sub(r"\d+(?:\.\d+)?", lambda m: " " + num2words(float(m.group()) if "." in m.group() else int(m.group())) + " ", s)
    s = s.replace(",", "")  # num2words writes 'one thousand, six hundred'
    s = re.sub(r"\bone thousand (\w+) hundred\b", r"\1teen hundred", s)  # 1,600 -> sixteen hundred
    s = re.sub(r"\bell\b", "l", s)
    s = re.sub(r"is(e|ed|es|ing|ation)\b", r"iz\1", s).replace("metre", "meter")
    return re.sub(r"[^a-z]", "", s)


def _match(script, heard):
    return difflib.SequenceMatcher(None, _letters(script), _letters(heard), autojunk=False).ratio()


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.?!:])\s+", text) if s.strip()]


class ChatterboxService(_FileService):
    name = "chatterbox"
    _model = None
    _asr = None

    def __init__(self, voice="", exaggeration=0.45, cfg_weight=0.5, min_match=0.95, tries=5, **kwargs):
        self.voice, self.exaggeration, self.cfg_weight = voice, exaggeration, cfg_weight
        self.min_match, self.tries = min_match, tries
        super().__init__(**kwargs)

    @classmethod
    def _load(cls):
        if cls._model is None:
            from chatterbox.tts import ChatterboxTTS
            from faster_whisper import WhisperModel

            cls._model = ChatterboxTTS.from_pretrained(device="cuda")
            cls._asr = WhisperModel("small.en", device="cuda", compute_type="float16")
        return cls._model, cls._asr

    def _match(self, wav, sr, text):
        import numpy as np
        import torchaudio.functional as AF

        audio = AF.resample(wav, sr, 16000).squeeze(0).cpu().numpy().astype(np.float32)
        segs, _ = self._asr.transcribe(audio, language="en", beam_size=5)
        return _match(text, " ".join(s.text for s in segs))

    def synth_wav(self, text, wav_path):
        import torch
        import torchaudio

        model, _ = self._load()
        gap = torch.zeros(1, int(0.28 * model.sr))
        parts = []
        for k, sent in enumerate(_sentences(text)):
            best, best_score = None, -1.0
            for attempt in range(self.tries):
                torch.manual_seed(1000 * k + attempt + len(sent))
                wav = model.generate(sent, audio_prompt_path=self.voice or None,
                                     exaggeration=self.exaggeration, cfg_weight=self.cfg_weight)
                score = self._match(wav, model.sr, sent)
                if score > best_score:
                    best, best_score = wav, score
                if score >= self.min_match:
                    break
            if best_score < self.min_match:
                print(f"[tts] best take only {best_score:.2f} for: {sent!r}")
            parts += [best.cpu(), gap]
        torchaudio.save(str(wav_path), torch.cat(parts[:-1], dim=1), model.sr)


def make_service():
    choice = os.environ.get("TTS", "chatterbox")
    voice = os.environ.get("TTS_VOICE", "")
    if choice == "chatterbox":
        return ChatterboxService(voice=voice)
    return EspeakService()
