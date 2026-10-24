# How the narration voice is made

The narration is written into each scene as `self.voiceover(text=...)` blocks and turned into speech by
`voices.py` while the scene renders. You don't run a separate voice step: `render.sh` generates the
narration on the first draft render and caches it, and later renders reuse it.

## What happens for each voiceover

1. **Bookmarks are stripped.** The `<bookmark mark='x'/>` tags are removed from the text before
   synthesis and before the cache lookup. Adding or moving a bookmark never regenerates audio.
2. **Cache lookup.** The key is the spoken text plus the voice settings. A hit reuses the stored mp3
   from `m_<Scene>/voiceovers/`, so changing a scene's visuals costs no voice time. Changing a
   voiceover's words regenerates that voiceover only.
3. **Sentence by sentence with Chatterbox.** The text is split at `. ? ! :`. Each sentence is
   synthesised by [Chatterbox](https://github.com/resemble-ai/chatterbox) on the GPU (exaggeration 0.45,
   cfg weight 0.5).
4. **Checked by ear (Whisper).** Each take is transcribed with Whisper `small.en` and compared with the
   script letter by letter, after normalising both sides: numbers to words, "8x8" to "eight by eight",
   "mm" to "millimetre", and -ise to -ize. A take that matches at least 95% is kept. Otherwise the
   sentence is regenerated with a new seed, up to 5 tries, and the best take is kept. This is what
   stops a mumbled, truncated or hallucinated sentence from reaching the video.
5. **Joined and trimmed.** Sentences are joined with 0.28 s pauses, trailing silence is trimmed,
   and the result is saved as mp3.
6. **Word timings.** Whisper transcribes the final audio again (on the CPU) with word timestamps. These
   are aligned to the script so each `<bookmark/>` gets an exact time, which `self.at("x", ...)` waits
   for. The timings are cached beside the audio as `<name>.words.json`.

## Writing narration that the voice reads well

These rules are also in [DESIGN.md](DESIGN.md) (Part II, Narration):

- **Spell out what must be said.** Write "one point eight two", "millimetres", "L S O" (acronyms
  letter by letter) and "caesium iodide", not "1.82", "mm", "LSO" or "CsI".
- **Keep sentences short.** Use a colon or full stop where a pause helps, since each sentence is
  generated and checked on its own.
- **Avoid a bare letter "l".** Write "scattering length" or "ell".
- **Respell any word Whisper keeps mishearing.** "Poisson" came out as "Hwasong" once.

## Checking the result

After a draft render, search the logs for sentences that never reached 95%:

```bash
grep -h "\[tts\] best take only" videos/<name>/m_*.log
```

Each line names the sentence and its best score. Respell the word it trips on, or split the sentence.
Then delete that scene's `m_<Scene>/voiceovers/` entry (or just change the words) and re-render. Listen
to the draft as well: the check catches wrong words, not odd intonation.

## Options

| Setting | Effect |
|---|---|
| `TTS=chatterbox` (default) | Chatterbox on CUDA, with the Whisper check above |
| `TTS_VOICE=/path/clip.wav` | clone a voice from 10–20 s of clean speech; only use a voice you have permission to use |
| `TTS=espeak` | robotic; only for checking timing without a GPU, never for a finished video; needs `espeak-ng` installed on the system |

To change Chatterbox's delivery, edit `make_service()` in `voices.py`: `exaggeration` (expressiveness),
`cfg_weight` (pacing), `min_match` (the 0.95 threshold) and `tries`.

## Cost

Each Chatterbox job needs about 4 GB of GPU memory, so draft with `JOBS=2` while narration is being
generated (3 jobs on an 11 GB card run about 20 times slower). Once everything is cached, renders
use no GPU, so final renders can run every scene at once. A 10-minute video takes roughly 10–15
minutes of voice generation on an RTX 2080 Ti.
