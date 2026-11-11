"""A reused figure with a fraction grid on it, so a frame or a pointer is placed by reading numbers, not by eye.

    pixi exec -s pillow python tools/figgrid.py <video>/assets/fig2.png [step]

Writes <png>_grid.png beside it (step 0.05 by default: a thin line every 5%, a labelled one every 10%). Open it, read
the fractions of the region off the grid, and put them in the plan note: fig_box(card, x0, y0, x1, y1), with (0, 0)
the top left. A level on a plot (a threshold line, a peak) is read the same way and handed to the writer
(pet_entangled: writers measured Fig. 2's 1.63 line themselves, and two frames were placed by eye).
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def grid(path, step=0.05):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    over = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    n = round(1 / step)
    for k in range(1, n):
        f = k * step
        major = round(f * 100) % 10 == 0
        col = (230, 0, 120, 200) if major else (0, 150, 230, 110)
        wd = 2 if major else 1
        d.line([(f * w, 0), (f * w, h)], fill=col, width=wd)
        d.line([(0, f * h), (w, f * h)], fill=col, width=wd)
        if major:
            t = f"{f:.1f}"
            for xy in ((f * w + 3, 2), (f * w + 3, h - 14), (2, f * h + 1), (w - 26, f * h + 1)):
                d.rectangle([xy[0] - 1, xy[1] - 1, xy[0] + 22, xy[1] + 11], fill=(255, 255, 255, 220))
                d.text(xy, t, fill=(200, 0, 100, 255))
    out = Path(path).with_name(Path(path).stem + "_grid.png")
    Image.alpha_composite(im.convert("RGBA"), over).convert("RGB").save(out)
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    print(grid(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 0.05))
