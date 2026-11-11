"""Which words of a narration line the voice got wrong, from the line and Whisper's transcript of it.

A score for the whole line does not answer that. On geant4, the first build the check ran in, all three lines
it reported were false alarms on spelling -- "1994" for "nineteen ninety-four", "C++" for "C plus plus" -- and
the one real fault, "Geant" heard as "Gint", sat inside one of them where nobody was told to look. So numbers,
however either side writes them, are left out (vlint number-unsourced is what holds a number to the source),
and what is compared is the words: a word of the script that the transcript has as a different word, or does
not have at all.

    python tools/heard.py "what was said" "what was heard"      prints the changed words, or nothing
"""
import difflib
import re
import sys

_ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
         "seventeen eighteen nineteen").split()
_TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()
_ORD = ("first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth hundredth "
        "thousandth millionth").split()
# everything a number is said with; Whisper writes all of it as digits and signs
NUMBER = (set(_ONES) | set(_TENS) | set(_ORD) | {w + "th" for w in _ONES[13:]} | {w[:-1] + "ieth" for w in _TENS}
          | {w[:-1] + "ies" for w in _TENS} | {"hundred", "thousand", "million", "billion", "point", "oh", "and",
                                                "plus", "minus", "times", "percent", "half", "a"})
UNITS = {"mm": "millimetres", "cm": "centimetres", "nm": "nanometres", "km": "kilometres", "ps": "picoseconds",
         "ns": "nanoseconds", "ms": "milliseconds", "kev": "kiloelectronvolts", "mev": "megaelectronvolts"}
SAME = 0.85          # 'millimetres' and 'millimeters' are one word (0.91); 'geant' and 'gint' are not (0.67)


def _words(text, heard=False):
    text = text.lower().replace("-", " ").replace("’", "'")
    if True:                                             # digits on either side: a script may write "1990s" too
        text = re.sub(r"\d[\d.,:]*(?:(?:th|st|nd|rd|s|k)(?![a-z]))?", " ", text)   # 1994, 3.21, 15th, 1990s, 200k
    text = re.sub(r"'s\b", "", text)                     # Khufu's is heard as Khufu often enough, and is no fault
    out, letters = [], ""
    for w in re.findall(r"[a-z']+", text):
        w = w.strip("'")
        if len(w) == 1 and w != "a":                     # L H C is said letter by letter and heard as LHC
            letters += w
            continue
        if letters:
            out.append(letters)
            letters = ""
        if w and w not in NUMBER:
            out.append(UNITS.get(w, w) if heard else w)
    if letters:
        out.append(letters)
    return out


def changed(said, heard):
    """[(the script's words, what was heard in their place)], '' for words that were not heard at all."""
    a, b = _words(said), _words(heard, heard=True)
    out = []
    for op, i, j, k, m in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        x, y = "".join(a[i:j]), "".join(b[k:m])
        if op == "equal" or not x:                       # a word heard that was not written: Whisper's, usually
            continue
        if difflib.SequenceMatcher(None, x, y, autojunk=False).ratio() < SAME:
            out.append((" ".join(a[i:j]), " ".join(b[k:m])))
    return out


if __name__ == "__main__":
    for was, got in changed(sys.argv[1], sys.argv[2]):
        print(f"{was!r} heard as {got!r}" if got else f"{was!r} not heard")
