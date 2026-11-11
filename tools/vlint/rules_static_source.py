"""Static rules that read the source beside the script: what the video says against what the paper says."""
import ast
import bisect
import re
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

from .core import opt, rule
from .rules_static import _CREDIT, TEX_CALLS
from .script import MARK, TEXT_CLASSES, call_name

_UNITS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen".split())}
_TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
_SCALES = {"hundred": 100, "thousand": 1000, "million": 1000000}
_NUMBER_WORDS = set(_UNITS) | set(_TENS) | set(_SCALES) | {"point", "oh"}
# "page thirty-seven", "figures four and five": where in the source, which a page walk says all the time
_PLACES = {"page", "pages", "figure", "figures", "table", "tables", "section", "sections", "equation", "equations",
           "chapter", "chapters", "reference", "references"}
_DECADES = {w[:-1] + "ies" for w in _TENS}
_NUM = re.compile(r"\d+(?:\.\d+)?")
# 1,600 and LaTeX's 22\,292 and 16{,}384 are one number each; so is 260 000, but only as a second reading,
# since "3 250" in a table row is as often two cells
_THOUSANDS = re.compile(r"(?<=\d)(?:,|\\,|\{,\}|[  ])(?=\d{3}(?!\d))")
_SPACED = re.compile(r"(?<![\d.,])\d{1,3}(?:[  ]\d{3})+(?!\d|\.\d)")
_SCALED = re.compile(r"(\d+(?:\.\d+)?)[  -]?(thousand|million|billion|k)\b")
_HALF = re.compile(r"\b(" + "|".join(sorted(set(_UNITS) | set(_TENS) | set(_SCALES))) + r")\s+and\s+a\s+half\b", re.I)


def _norm(n):
    """'1.50' and '1.5' are one number; '007' is 7."""
    whole, _, frac = n.partition(".")
    frac = frac.rstrip("0")
    return (whole.lstrip("0") or "0") + ("." + frac if frac else "")


def _digits(text):
    return [_norm(n) for n in _NUM.findall(_THOUSANDS.sub("", text))]


def _shown(text):
    """(number, the parts it was joined from) for a text the video shows or says: '260 000' is 260000, and
    only if the source has no such number is it held to be 260 and 0."""
    parts = {}

    def join(m):
        whole = re.sub(r"[ \u00a0]", "", m.group())
        parts[_norm(whole)] = [_norm(p) for p in re.split(r"[ \u00a0]", m.group())]
        return whole
    return [(n, parts.get(n, ())) for n in dict.fromkeys(_digits(_SPACED.sub(join, text)))]


def _run_value(run):
    """The number a run of number words says, as a string, or None when the run is not one number said plainly
    ('two three', a bare 'hundred'). 'sixteen hundred' is 1600, 'one point eight two' 1.82 and 'nineteen ninety
    five' 1995."""
    if "point" in run:
        k = run.index("point")
        head, tail = run[:k], run[k + 1:]
        if not tail or any(w not in _UNITS or _UNITS[w] > 9 for w in tail if w != "oh"):
            return None
        whole = _run_value(head) if head else "0"
        return None if whole is None else _norm(whole + "." + "".join("0" if w == "oh" else str(_UNITS[w]) for w in tail))
    if not run or "oh" in run or run[0] in _SCALES:
        return None
    total = cur = 0
    last = None                                   # 'unit', 'teen', 'tens' or 'scale'
    for w in run:
        if w in _SCALES:
            cur = (cur or 1) * _SCALES[w]
            if _SCALES[w] >= 1000:
                total, cur = total + cur, 0
            last = "scale"
            continue
        v = _UNITS.get(w, _TENS.get(w))
        kind = "tens" if w in _TENS else "teen" if v >= 10 else "unit"
        if last in ("teen", "tens") and kind in ("teen", "tens") and 10 <= cur < 100:
            cur = cur * 100 + v                   # a year said in pairs: nineteen ninety, twenty twenty
        elif last == "tens" and kind == "unit" and v:
            cur += v
        elif last in (None, "scale"):
            cur += v
        else:
            return None                           # 'two three': a list or digits read out, not one number
        last = kind
    return str(total + cur)


def _spoken(text):
    """Every number the narration says, digits and words alike."""
    text = _HALF.sub(r"\1 point five", MARK.sub(" ", text))      # thirty seven and a half
    out = _digits(text)
    run, before, ref = [], "", False              # ref: this run names a place in the source, not a value
    for tok in re.findall(r"[A-Za-z]+|[^A-Za-z\s]", text.replace("-", " ")) + ["."]:
        w = tok.lower()
        if w in _NUMBER_WORDS:
            if not run:
                ref = before in _PLACES or (ref and before in ("and", "to", "through"))
            run.append(w)
            continue
        if w == "and" and run and run[-1] in _SCALES:
            continue                              # two hundred and fourteen
        if run:
            v = _run_value(run)
            if v is not None and not ref and w not in _DECADES:   # 'the nineteen nineties' is an era, not 19
                out.append(v)
            run = []
        elif before not in _PLACES and w not in ("and", "to", "through"):
            ref = False
        before = w
    return out


def _worth_checking(n, least):
    """Decimals always. Whole numbers from `least` up: below it they are counts and ordinals of the telling
    ('three steps', 'the two photons'), which no source states and no viewer takes for a result."""
    return "." in n or int(n) >= least


def _plain(d):
    """A Decimal as the digits _norm would give: no exponent, no trailing zeros."""
    return _norm(format(d, "f"))


_REFS = re.compile(r"(?m)^.*\b(?:References|REFERENCES|Bibliography)[ \t]*$")
_PVAL = re.compile(r"\bp\s*[=<>≤≥]\s*(\d*\.\d+)")
_CITED = re.compile(r"\[\s*\d+(?:\s*[,–—-]\s*\d+)*\s*\]")


def _body(text):
    """The source without its reference list and its [12, 13] citation marks. Left in, they hold nearly every
    year and every whole number under a hundred, so a wrong 1997 or a wrong 70 'matched' (geant4: four planted
    errors passed this way). Only a heading in the back half counts, so a contents line does not cut the paper."""
    heads = [m.start() for m in _REFS.finditer(text) if m.start() > 0.4 * len(text)]
    return _CITED.sub(" ", text[:heads[-1]] if heads else text)


class _Source:
    """Every number in the source's extracted text. A number is in the source when the source prints it, or
    prints one that rounds to it at the precision it is given at: 2.95 for the paper's 2.953, 'about two
    hundred thousand' for 198,400. Rounding is the telling's to do; a different number is not. Nor is the
    way a number is written: the source's '10 million', 'ten million' and '260 000' are 10000000 and 260000,
    and its 93% is the video's 0.93. Where the source could be read either way it is read both ways, so the
    rule stays silent rather than guess."""
    def __init__(self, s):
        src = s.path.parent / "src"
        self.raw = set()
        scale = {"thousand": 3, "million": 6, "billion": 9, "k": 3}
        for f in sorted(src.glob("*.txt")) if src.is_dir() else ():
            t = _body(f.read_text(encoding="utf-8", errors="replace"))
            self.raw.update(_digits(t))
            self.raw.update(n for n, _ in _shown(t))
            self.raw.update(_spoken(t))
            self.raw.update(_plain(Decimal(n).scaleb(scale[w])) for n, w in _SCALED.findall(_THOUSANDS.sub("", t)))
        self.vals = sorted(Decimal(n) for n in self.raw)
        # what may stand for a percentage: not a p-value (pet_g4_configs: a wrong 8.7% passed as p = 0.087)
        self.ratio = self.raw - {_norm(n) for f in (sorted(src.glob("*.txt")) if src.is_dir() else ())
                                 for n in _PVAL.findall(f.read_text(encoding="utf-8", errors="replace"))}

    def has(self, n, parts=()):
        if parts and all(self.has(p) for p in parts):
            return True
        d = Decimal(n)
        if n in self.raw or _plain(d * 100) in self.ratio or _plain(d / 100) in self.ratio:
            return True
        frac = n.partition(".")[2]
        q = Decimal(1).scaleb(-len(frac)) if frac else Decimal(1).scaleb(len(n) - len(n.rstrip("0")))
        lo = bisect.bisect_left(self.vals, d - q)
        for x in self.vals[lo:bisect.bisect_right(self.vals, d + q)]:
            if any((x / q).to_integral_value(r) * q == d for r in (ROUND_HALF_UP, ROUND_HALF_EVEN)):
                return True
        return False


def _said_at(s, vo, n):
    """The line of the voiceover's text that says n, so an ignore on the `with` line, which marks one computed
    number, does not silence every other number the voice says (pet_g4_configs: a wrong 0.464 passed this way).
    The `with` line when the words for n are split across lines."""
    for ln in range(vo.node.lineno + 1, vo.node.body[0].lineno if vo.node.body else vo.node.lineno + 1):
        if n in _spoken(s.lines[ln - 1]):
            node = ast.Pass()
            node.lineno = node.end_lineno = ln
            node.col_offset = node.end_col_offset = 0
            return node
    return vo.node


@rule("number-unsourced", "static", "warn", "A number in the narration or in an on-screen text is not in the source's "
      "extracted text (src/*.txt), so it came from memory, a summary or a calculation nobody marked (shell_pet: 3.66 "
      "from memory was 3.59; liquid_tc: 1.512 became 1.51).", "Part I §4, numbers",
      "take the number from the source, at the source's precision. One the video computed or drew for illustration "
      "keeps its line and says so: `# vlint: ignore[number-unsourced] computed: ...`")
def number_unsourced(s):
    have = _Source(s)
    if not have.raw:
        return                                    # no extracted source here: nothing to hold the number against
    least = int(opt(s, "sourced_from", 13))
    for vo in s.voiceovers:
        if vo.text is None:
            continue
        for n in dict.fromkeys(_spoken(vo.text)):
            if _worth_checking(n, least) and not have.has(n):
                yield _said_at(s, vo, n), f"the voice says {n}, which the source never does"
    # The script's label helpers, and kit's, with the parameters whose value ends up in a Tex or a Text:
    # def lab(t, ...): return Tex(t, ...), and just as much def num(t): return Tex(r"\textbf{" + t + "}"), which
    # is where the headline numbers are (geant4: a helper that wrapped its argument went unread, so every bold
    # number on screen did too). Followed through helpers that call helpers (kit: dim -> num -> lab -> Tex), and
    # for any parameter, not just the first (dim(a, b, "3.1 mm")).
    wrappers = {}                                 # name -> (indices of the label parameters, parameter names)
    defs = [fn for fn in s.defs() if fn.args.args]
    for _ in range(4):
        for fn in defs:
            names = [a.arg for a in fn.args.args]
            found = set()
            for n in ast.walk(fn):
                c = call_name(n)
                if c in TEX_CALLS | TEXT_CLASSES:
                    feeds = list(n.args)
                elif c in wrappers and c != fn.name:
                    idx, pn = wrappers[c]
                    feeds = [n.args[i] for i in idx if i < len(n.args)] + [k.value for k in n.keywords if k.arg in
                                                                            {pn[i] for i in idx if i < len(pn)}]
                else:
                    continue
                for a in feeds:
                    found |= {i for i, p in enumerate(names) if any(isinstance(x, ast.Name) and x.id == p for x in ast.walk(a))}
            if found:
                wrappers[fn.name] = (found | wrappers.get(fn.name, (set(), names))[0], names)
    for node in ast.walk(s.tree):
        name = call_name(node)
        if name in TEX_CALLS | TEXT_CLASSES:
            args = list(node.args)
        elif name in wrappers:
            idx, pn = wrappers[name]
            args = [node.args[i] for i in sorted(idx) if i < len(node.args)] + \
                [k.value for k in node.keywords if k.arg in {pn[i] for i in idx if i < len(pn)}]
        else:
            continue
        for a in args:
            v = s.resolve_str(a)
            if not v or _CREDIT.search(v):          # a citation's year and volume are the reference's, not a result
                continue
            v = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?", " ", v)         # \hspace[..], \frac: commands, not values
            for n, parts in _shown(v):
                if _worth_checking(n, least) and not have.has(n, [p for p in parts if _worth_checking(p, least)]):
                    yield a, f"{n} is on screen and not in the source: {v.strip()[:40]!r}"
