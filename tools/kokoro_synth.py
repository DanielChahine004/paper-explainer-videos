"""Kokoro-82M synthesis for voices.py, run inside its own env (~/kokoro_env, Python 3.12; the render env's 3.13 cannot
load kokoro). Reads one text per line on stdin, tab-separated from its output wav path, so one process (one model
load) serves a whole batch:  printf 'text\tout.wav\n' | pixi run --manifest-path ~/kokoro_env/pixi.toml python
kokoro_synth.py af_heart 1.0"""
import sys
import time

import numpy as np
import soundfile as sf
from kokoro import KPipeline

sys.stdin.reconfigure(encoding="utf-8")    # voices.py writes UTF-8; Windows would read cp1252
sys.stdout.reconfigure(encoding="utf-8", newline="\n")
voice, speed = sys.argv[1], float(sys.argv[2])


def retried(f):
    """Two voice workers start at once and both fetch the model into the Hugging Face cache; on Windows the second's
    rename of a cache file fails while the first holds it (WinError 5, Windows CI). The first finishes it: retry."""
    for i in range(6):
        try:
            return f()
        except PermissionError:
            if i == 5:
                raise
            time.sleep(2 + 3 * i)


pipe = retried(lambda: KPipeline(lang_code=voice[0], repo_id="hexgrad/Kokoro-82M"))
for line in sys.stdin:
    if not line.strip():
        continue
    text, out = line.rstrip("\n").rsplit("\t", 1)
    audio = retried(lambda: np.concatenate([np.asarray(a) for _, _, a in pipe(text, voice=voice, speed=speed)]))
    sf.write(out, audio, 24000)
    print(out, flush=True)
