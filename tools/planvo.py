"""plan.md -> python. Two uses, both so that no spoken word is ever typed twice (DESIGN Part III step 2):

    python tools/planvo.py <video> words > ../slab_work/<video>_words/w_vo.py   a throwaway script, one empty scene
                               per section with every mark cued on a dot: lint the words and voice them before the split
    python tools/planvo.py <video> skeleton [Scene ...]                         the voiceover blocks of the named
                               scenes, with one self.at() per mark, for a writer to fill in
Copied into g4_setup, pet_g4_configs and pet_mrpc before it lived here.
"""
import re
import sys
import textwrap
from pathlib import Path

if len(sys.argv) < 3:
    sys.exit(__doc__)
# a video name, or any folder holding a plan.md (a writer's copy in slab_work, pico40l)
here = Path(sys.argv[1]).resolve() if (Path(sys.argv[1]) / "plan.md").exists() else Path(__file__).resolve().parent.parent / sys.argv[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vlint.plan import load  # noqa: E402

plan = load(here)
KIND = {"new:": "FadeIn(Dot())", "mark:": "Indicate(d)", "side:": "d.animate.shift(RIGHT * 0.01)",
        "morph:": "Transform(d, Dot())"}


def vo(prose, ind):
    text = re.sub(r"\[(\w+)\]", r"<bookmark mark='\1'/>", prose)
    parts = textwrap.wrap(text, 96, break_long_words=False, break_on_hyphens=False)
    # a wrap must not fall inside a bookmark tag
    fixed, buf = [], ""
    for seg in parts:
        buf = (buf + " " + seg) if buf else seg
        if buf.count("<") == buf.count(">"):
            fixed.append(buf)
            buf = ""
    if buf:
        fixed.append(buf)
    lines = [f'{ind}    "{seg}{" " if i < len(fixed) - 1 else ""}"' for i, seg in enumerate(fixed)]
    return f"{ind}with self.voiceover(text=(\n" + "\n".join(lines) + f"\n{ind})):\n"


def scene(name, st, words):
    out = f"class {name}(Narrated):\n    def construct(self):\n"
    if words:
        out += f"        d = Dot()\n        {st.entity} = d\n        self.add(d)\n"
    else:
        out += f"        # focus: {st.focus}\n"
    for k, b in enumerate(st.blocks):
        if k and not words:
            out += "        self.wait(0.3)\n"
        out += vo(b.prose, "        ")
        for mk in b.marks:
            _, action, why = b.actions[mk]
            pre = next((p for p in KIND if action.lower().startswith(p)), "")
            if words:
                out += f'            self.at("{mk}", {KIND.get(pre, st.entity + ".animate.shift(RIGHT * 0.01)")})\n'
            else:
                out += f'            self.at("{mk}", )   # {action}\n'
    return out + ("        self.wait(0.5)\n" if not words else "") + "\n\n"


mode, names = sys.argv[2], sys.argv[3:]
if mode == "words":
    print('import sys\nfrom pathlib import Path\n\nsys.path.insert(0, str(Path(__file__).resolve().parent.parent))\n'
          'from common import *  # noqa\n\n')
for name, st in plan.scenes.items():
    if not names or name in names:
        print(scene(name, st, mode == "words"), end="")
