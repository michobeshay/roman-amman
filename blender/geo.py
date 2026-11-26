"""Pure numpy geometry accumulator + primitives (no bpy). Units = metres."""
import math
import numpy as np

class Acc:
    def __init__(s, floats=(), colors=(), vecs=()):
        s.V = []; s.F = []; s.UV = []; s.n = 0
        s.fl = {k: [] for k in floats}; s.co = {k: [] for k in colors}; s.ve = {k: [] for k in vecs}
    def add(s, v, f, uv=None, **at):
        v = np.asarray(v, np.float32); n = len(v)
        s.V.append(v); s.UV.append(np.zeros((n, 2), np.float32) if uv is None else np.asarray(uv, np.float32))
        f = np.asarray(f, np.int64) if not isinstance(f, list) or (len(f) and len(set(map(len, f))) == 1) else f
        if isinstance(f, np.ndarray): s.F.append(f + s.n)
        else: s.F.append([[i + s.n for i in face] for face in f])
        for k in s.fl: s.fl[k].append(np.broadcast_to(np.asarray(at.get(k, 0.0), np.float32), (n,)).copy())
        for k in s.co:
            c = np.asarray(at.get(k, (1, 1, 1, 1)), np.float32)
            if c.shape[-1] == 3: c = np.concatenate([c, np.ones(c.shape[:-1] + (1,), np.float32)], -1)
            s.co[k].append(np.broadcast_to(c, (n, 4)).copy())
        for k in s.ve: s.ve[k].append(np.broadcast_to(np.asarray(at.get(k, (0, 0, 0)), np.float32), (n, 3)).copy())
        s.n += n
    def faces(s):
        out = []
        for g in s.F: out.extend(g.tolist() if isinstance(g, np.ndarray) else g)
        return out
    def verts(s): return np.concatenate(s.V) if s.V else np.zeros((0, 3), np.float32)
    def uvs(s): return np.concatenate(s.UV)
    def empty(s): return s.n == 0

def box(c, size, rot=0.0):
    cx, cy, cz = c; sx, sy, sz = [q / 2 for q in size]
    V = np.array([[a * sx, b * sy, d * sz] for d in (-1, 1) for b in (-1, 1) for a in (-1, 1)], np.float64)
    if rot:
        cr, sr = math.cos(rot), math.sin(rot); V = V @ np.array([[cr, sr, 0], [-sr, cr, 0], [0, 0, 1]])
    V += (cx, cy, cz)
    F = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
    return V, F

def cyl(c, r, h, sides=12, r2=None, cap=True):
    r2 = r if r2 is None else r2; th = np.linspace(0, math.tau, sides, endpoint=False)
    b = np.stack([c[0] + r * np.cos(th), c[1] + r * np.sin(th), np.full(sides, c[2])], 1)
    t = np.stack([c[0] + r2 * np.cos(th), c[1] + r2 * np.sin(th), np.full(sides, c[2] + h)], 1)
    V = np.concatenate([b, t]); F = [[i, (i + 1) % sides, sides + (i + 1) % sides, sides + i] for i in range(sides)]
    if cap: F.append(list(range(sides - 1, -1, -1))); F.append([sides + i for i in range(sides)])
    return V, F

def column(c, h, r, sides=16, flute=0.05):
    """base + fluted shaft with slight entasis + Corinthian-ish flared capital + abacus. Returns V,F."""
    V = []; F = []; n = 0
    def add(v, f):
        nonlocal n
        v = np.asarray(v); V.append(v); F.extend([[i + n for i in q] for q in f]); n += len(v)
    cx, cy, z = c
    add(*cyl((cx, cy, z), r * 1.35, h * 0.035, sides, r * 1.28)); add(*cyl((cx, cy, z + h * 0.035), r * 1.2, h * 0.025, sides, r * 1.12))
    zs = z + h * 0.06; hs = h * 0.78; rings = 5; th = np.linspace(0, math.tau, sides, endpoint=False)
    sh = []
    for k in range(rings):
        t = k / (rings - 1); rr = r * (1 - 0.16 * t + 0.03 * math.sin(math.pi * t))
        rad = rr * (1 - flute * (np.arange(sides) % 2))
        sh.append(np.stack([cx + rad * np.cos(th), cy + rad * np.sin(th), np.full(sides, zs + hs * t)], 1))
    add(np.concatenate(sh), [[k * sides + i, k * sides + (i + 1) % sides, (k + 1) * sides + (i + 1) % sides, (k + 1) * sides + i] for k in range(rings - 1) for i in range(sides)])
    zc = zs + hs; hc = h * 0.14
    add(*cyl((cx, cy, zc), r * 0.86, hc * 0.5, sides, r * 1.05, cap=False)); add(*cyl((cx, cy, zc + hc * 0.5), r * 1.05, hc * 0.5, sides, r * 1.35))
    add(*box((cx, cy, zc + hc + h * 0.02), (r * 3.0, r * 3.0, h * 0.04)))
    return np.concatenate(V), F

def ring_seg(cx, cy, ri, ro, a0, a1, z0, z1, n=8):
    a = np.linspace(a0, a1, n + 1); V = []
    for r in (ri, ro):
        for z in (z0, z1): V.append(np.stack([cx + r * np.cos(a), cy + r * np.sin(a), np.full(n + 1, z)], 1))
    V = np.concatenate(V); m = n + 1
    ib0, it0, ob0, ot0 = 0, m, 2 * m, 3 * m
    F = []
    for i in range(n):
        F.append([ib0 + i, ib0 + i + 1, it0 + i + 1, it0 + i]); F.append([ob0 + i, ot0 + i, ot0 + i + 1, ob0 + i + 1])
        F.append([it0 + i, it0 + i + 1, ot0 + i + 1, ot0 + i]); F.append([ib0 + i, ob0 + i, ob0 + i + 1, ib0 + i + 1])
    return V, F

def arch_xz(cx, z_spring, r_in, thick, y0, y1, n=9):
    """semicircular arch of voussoirs in the XZ plane, extruded between y0,y1."""
    V = []; F = []; off = 0
    ang = np.linspace(0, math.pi, n + 1)
    for i in range(n):
        a0, a1 = ang[i], ang[i + 1]; pts = []
        for r in (r_in, r_in + thick):
            for a in (a0, a1):
                for y in (y0, y1): pts.append([cx + r * math.cos(a), y, z_spring + r * math.sin(a)])
        v = np.array(pts); V.append(v)
        F.extend([[off + 0, off + 1, off + 3, off + 2], [off + 4, off + 6, off + 7, off + 5], [off + 0, off + 4, off + 5, off + 1], [off + 2, off + 3, off + 7, off + 6], [off + 0, off + 2, off + 6, off + 4], [off + 1, off + 5, off + 7, off + 3]])
        off += 8
    return np.concatenate(V), F

def ellipsoid(c, r, nu=14, nv=9, rot=None):
    u = np.linspace(0, math.tau, nu, endpoint=False); v = np.linspace(0, math.pi, nv); U, Vv = np.meshgrid(u, v)
    P = np.stack([r[0] * np.sin(Vv) * np.cos(U), r[1] * np.sin(Vv) * np.sin(U), r[2] * np.cos(Vv)], -1).reshape(-1, 3)
    if rot is not None: P = P @ rot.T
    P = P + np.asarray(c); idx = np.arange(nv * nu).reshape(nv, nu)
    F = [[idx[i, j], idx[i, (j + 1) % nu], idx[i + 1, (j + 1) % nu], idx[i + 1, j]] for i in range(nv - 1) for j in range(nu)]
    return P, F

def smoothstep(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)
