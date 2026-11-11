import numpy as np
def bp(nd=48, n=64, seed=5, spread=0.15, norm=False):
    rng = np.random.default_rng(seed)
    eff = np.clip(rng.normal(1, spread, nd), 0.6, 1.4)
    ang = np.arange(nd) * 2 * np.pi / nd
    P = np.stack([np.cos(ang), np.sin(ang)], 1)
    img = np.zeros((n, n)); w = np.zeros((n, n))
    t = np.linspace(0, 1, 400)
    for i in range(nd):
        for j in range(i + 1, nd):
            pts = P[i][None] * (1 - t[:, None]) + P[j][None] * t[:, None]
            inside = (pts ** 2).sum(1) < 0.6 ** 2
            if inside.sum() < 3: continue
            r = 1.0 if norm else eff[i] * eff[j]
            ix = ((pts[inside] + 1) / 2 * (n - 1)).round().astype(int)
            u = np.unique(ix[:, 1] * n + ix[:, 0])
            img.flat[u] += r; w.flat[u] += 1
    yy, xx = np.mgrid[0:n, 0:n]
    disk = ((xx - (n - 1) / 2) ** 2 + (yy - (n - 1) / 2) ** 2) < (0.58 * (n - 1) / 2) ** 2
    out = np.where(w > 0, img / np.maximum(w, 1), 0)
    return out, disk, eff
o, d, e = bp()
print("std inside", o[d].std(), "min", o[d].min(), "max", o[d].max())
o2, d, e = bp(norm=True); print("norm std", o2[d].std())
