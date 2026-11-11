import numpy as np
def mono_light(px, py, h, pitch=4.0, n=8):
    c = (np.arange(n) - (n - 1) / 2) * pitch
    gx, gy = np.meshgrid(c, c)
    r2 = (gx - px) ** 2 + (gy - py) ** 2 + h * h
    return h / r2 ** 1.5
rng = np.random.default_rng(2)
pos = np.arange(-15, 15.01, 2.0); refs=[]; lab=[]
for x in pos:
    for y in pos:
        m = mono_light(x, y, 8.0).ravel(); m = m/m.sum()*1500
        for _ in range(8):
            q = rng.poisson(m).astype(float); refs.append(q/q.sum()); lab.append((x,y))
refs=np.array(refs); lab=np.array(lab)
rng = np.random.default_rng(9)
tx,ty=3.3,-5.2
m = mono_light(tx,ty,8.0).ravel(); q=rng.poisson(m/m.sum()*1500).astype(float); q/=q.sum()
nn=np.argsort(((refs-q)**2).sum(1))[:40]; e=lab[nn].mean(0); print("demo err", np.hypot(*(e-[tx,ty])))
errs=[]
r2=np.random.default_rng(1)
for _ in range(300):
    tx,ty=r2.uniform(-14,14,2); m=mono_light(tx,ty,8.0).ravel(); q=r2.poisson(m/m.sum()*1500).astype(float); q/=q.sum()
    nn=np.argsort(((refs-q)**2).sum(1))[:40]; e=lab[nn].mean(0); errs.append(np.hypot(*(e-[tx,ty])))
print("median err", np.median(errs))
