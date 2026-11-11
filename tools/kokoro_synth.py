"""Kokoro-82M synthesis for voices.py, run inside its own env (~/kokoro_env, Python 3.12; the render env's 3.13 cannot
load kokoro). Reads one text per line on stdin, tab-separated from its output wav path, so one process (one model
load) serves a whole batch:  printf 'text\tout.wav\n' | pixi run --manifest-path ~/kokoro_env/pixi.toml python
kokoro_synth.py af_heart 1.0"""
import sys

import numpy as np
import soundfile as sf
from kokoro import KPipeline

voice, speed = sys.argv[1], float(sys.argv[2])
pipe = KPipeline(lang_code=voice[0], repo_id="hexgrad/Kokoro-82M")
for line in sys.stdin:
    if not line.strip():
        continue
    text, out = line.rstrip("\n").rsplit("\t", 1)
    audio = np.concatenate([np.asarray(a) for _, _, a in pipe(text, voice=voice, speed=speed)])
    sf.write(out, audio, 24000)
    print(out, flush=True)
