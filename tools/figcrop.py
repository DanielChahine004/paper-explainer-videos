"""Cut a figure from a page render with every edge in white paper: give a rough box, get a safe crop.

    pixi exec -s pillow -s numpy python tools/figcrop.py <video> <page> <name.png> x0 y0 x1 y1 [--whiten x0 y0 x1 y1]...

The box is fractions of the page, (0, 0) the top left, read off src/lo-NN.png by eye: rough is fine. Each edge
then grows outward until GAP px (2 mm at 300 dpi) of white paper lie beyond it, so a crop that started inside the
tick numbers or the axis title takes them in (the cut that had to be redone in pet_neuroexplorer and rydberg_radar),
while the wider gap to a caption or the next column stops it. Then it is trimmed to the ink plus PAD. --whiten
paints a region white first (a neighbour's panel letter), in fractions of the page as well. Reads
<video>/src/hi-NN.png, writes <video>/assets/<name>, prints the final box in pixels and fractions; an edge that grew
by more than 8% of the page is flagged, so look at it (it may have swallowed a caption: give a box that stops short).
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

INK, GAP, PAD = 200, 24, 12


def safe_box(a, x0, y0, x1, y1):
    """Grow (x0, y0, x1, y1) until GAP px beyond each edge are white, then trim to the ink inside plus PAD."""
    h, w = a.shape
    ink = a < INK
    for _ in range(4000):
        moved = False
        if y0 > 0 and ink[max(0, y0 - GAP):y0, x0:x1].any():
            y0 -= 1; moved = True
        if y1 < h and ink[y1:min(h, y1 + GAP), x0:x1].any():
            y1 += 1; moved = True
        if x0 > 0 and ink[y0:y1, max(0, x0 - GAP):x0].any():
            x0 -= 1; moved = True
        if x1 < w and ink[y0:y1, x1:min(w, x1 + GAP)].any():
            x1 += 1; moved = True
        if not moved:
            break
    rows, cols = np.where(ink[y0:y1, x0:x1].any(1))[0], np.where(ink[y0:y1, x0:x1].any(0))[0]
    if len(rows):
        y0, y1, x0, x1 = y0 + rows[0], y0 + rows[-1] + 1, x0 + cols[0], x0 + cols[-1] + 1
    return max(0, x0 - PAD), max(0, y0 - PAD), min(w, x1 + PAD), min(h, y1 + PAD)


def main(argv):
    if len(argv) < 7:
        sys.exit(__doc__)
    v, page, name = argv[0], int(argv[1]), argv[2]
    fx = [float(x) for x in argv[3:7]]
    wh = []
    rest = argv[7:]
    while rest:
        if rest[0] != "--whiten" or len(rest) < 5:
            sys.exit(f"figcrop: cannot read {' '.join(rest)}")
        wh.append([float(x) for x in rest[1:5]])
        rest = rest[5:]
    root = Path(__file__).resolve().parent.parent / v
    src = next((root / "src" / f"hi-{page:0{k}d}.png" for k in (1, 2, 3)
                if (root / "src" / f"hi-{page:0{k}d}.png").exists()), None)
    if src is None:
        sys.exit(f"figcrop: no {v}/src/hi-{page:02d}.png")
    im = Image.open(src).convert("RGB")
    W, H = im.size
    px = lambda f: (round(f[0] * W), round(f[1] * H), round(f[2] * W), round(f[3] * H))
    arr = np.array(im)
    for f in wh:
        a0, b0, a1, b1 = px(f)
        arr[b0:b1, a0:a1] = 255
    grey = np.array(Image.fromarray(arr).convert("L"))
    r = px(fx)
    b = safe_box(grey, *r)
    out = root / "assets" / name
    out.parent.mkdir(exist_ok=True)
    Image.fromarray(arr).crop(b).save(out)
    b = tuple(int(x) for x in b)
    grew = max(r[0] - b[0], r[1] - b[1], b[2] - r[2], b[3] - r[3])
    fr = f"({b[0] / W:.3f}, {b[1] / H:.3f}, {b[2] / W:.3f}, {b[3] / H:.3f})"
    print(f"{name}: page {page} px {b} frac {fr}"
          + (f"  an edge grew {grew} px: look at it" if grew > 0.08 * H else ""))


if __name__ == "__main__":
    main(sys.argv[1:])
