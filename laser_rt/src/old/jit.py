import sys, numpy as np, importlib.util
src = open(sys.argv[1], encoding="utf-8").read()
ns = {"np": np}
exec(src[src.index("def bragg("):src.index("def bragg_curve(")], ns)
R = np.linspace(15.0, 15.3, 31)
v = np.array([ns["bragg"](5.0, r) for r in R])
print("dose at 5 cm as R moves 15.0 -> 15.3:", np.round(v, 3))
print("max frame-to-frame jump:", np.abs(np.diff(v)).max().round(4))
