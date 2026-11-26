"""Procedural reconstruction of the Roman Theatre of Philadelphia (Amman) and its surroundings, ancient and modern.
Proportions are an artistic reconstruction; layout (3 maeniana, semicircular orchestra, stage, scaenae frons) follows the
published description. The stage building is reconstructed from comparable Roman theatres and is NOT surviving fabric."""
import bpy, math
import numpy as np
from mathutils import Vector
import lib, amman_mats as M, amman_gn as GN
from geo import *

# ------------------------------------------------------------------ cavea parameters (metres)
R0 = 12.6
TIERS = [(12, 0.78, 0.40), (11, 0.74, 0.41), (10, 0.70, 0.42)]      # rows, tread depth, riser height
DIAZ, WALL, BACK = 2.8, 1.3, 5.0
STAGE_Z = 1.5; FRONS_Y = -8.5; WING_X = 27.0
rng_global = np.random.default_rng(2026)

def cavea_profile():
    pts = []; r = R0; z = 0.0; pts.append((r, z, 0))
    for ti, (rows, tread, riser) in enumerate(TIERS):
        for i in range(rows):
            z += riser + (WALL if (i == 0 and ti > 0) else 0.0); pts.append((r, z, ti))
            r += tread; pts.append((r, z, ti))
        if ti < len(TIERS) - 1: r += DIAZ - tread; pts.append((r, z, ti))
    z += BACK; pts.append((r, z, 2)); r += 1.3; pts.append((r, z, 2))
    return pts
PROF = cavea_profile(); R_OUT = PROF[-1][0]; Z_TOP = PROF[-1][1]
_u = {}
for r_, z_, _t in PROF: _u[round(r_, 3)] = max(_u.get(round(r_, 3), -9), z_)
_ur = np.array(sorted(_u)); _uz = np.array([_u[k] for k in _ur])
def cavea_floor(r): return np.interp(r, _ur, _uz)

# ------------------------------------------------------------------ terrain
def hill(x, y):
    t = smoothstep((y - 5) / 110.0); z = 70 * t + 22 * smoothstep((y - 110) / 140.0)
    z += 0.0007 * np.clip(np.abs(x) - 60, 0, None) ** 1.55 * smoothstep((y + 40) / 120.0)
    z += (2.5 * np.sin(x * 0.045 + 1.3) * np.cos(y * 0.037) + 1.6 * np.sin(x * 0.11 + y * 0.09)) * smoothstep(y / 40.0)
    z = np.where(y < -92, -0.04 * (-92 - y) - 0.0 * x, z)
    r = np.hypot(x, y); skirt = Z_TOP * (1 - smoothstep((r - R_OUT) / 32.0)) * smoothstep((y + 2) / 14.0)
    return np.maximum(z, skirt)
def height(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float); r = np.hypot(x, y)
    z = hill(x, y); inside = (r < R_OUT + 0.5) & (y > -1)
    return np.where(inside, cavea_floor(np.minimum(r, R_OUT)) - 0.35, z)

def plaza_mask(x, y):
    return smoothstep((66 - np.abs(x)) / 6.0) * smoothstep((y + 94) / 6.0) * smoothstep((-8 - y) / 4.0)
def road_mask(x, y):
    m = np.exp(-((y + 108) / 6.5) ** 2) + np.exp(-((np.abs(x) - 86) / 4.5) ** 2) * smoothstep((-y + 150) / 40.0) * smoothstep((y + 220) / 30.0)
    return np.clip(m, 0, 1) * (1 - plaza_mask(x, y))

def mesh_obj(sc, name, acc, mat=None, coll=None, smooth=False):
    me = bpy.data.meshes.new(name); me.from_pydata(acc.verts().tolist(), [], acc.faces()); me.update()
    if smooth: me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    uvl = me.uv_layers.new(name="UVMap"); li = np.empty(len(me.loops), dtype=np.int32); me.loops.foreach_get("vertex_index", li)
    uvl.data.foreach_set("uv", acc.uvs()[li].ravel())
    for k, v in acc.fl.items():
        a = me.attributes.new(name=k, type='FLOAT', domain='POINT'); a.data.foreach_set("value", np.concatenate(v).astype(np.float32))
    for k, v in acc.co.items():
        a = me.color_attributes.new(name=k, type='FLOAT_COLOR', domain='POINT'); a.data.foreach_set("color", np.concatenate(v).ravel().astype(np.float32))
    for k, v in acc.ve.items():
        a = me.attributes.new(name=k, type='FLOAT_VECTOR', domain='POINT'); a.data.foreach_set("vector", np.concatenate(v).ravel().astype(np.float32))
    ob = lib.link_obj(sc, name, me, coll)
    if mat is not None: ob.data.materials.append(mat)
    return ob

def build_terrain(sc, coll):
    nx, ny = 300, 300; xs = np.linspace(-300, 300, nx); ys = np.linspace(-300, 300, ny); X, Y = np.meshgrid(xs, ys)
    Z = height(X, Y); V = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1); idx = np.arange(nx * ny).reshape(ny, nx)
    F = np.stack([idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()], 1)
    acc = Acc(floats=['plaza', 'road']); acc.add(V, F, uv=np.stack([X.ravel(), Y.ravel()], 1), plaza=plaza_mask(X, Y).ravel(), road=road_mask(X, Y).ravel())
    ob = mesh_obj(sc, "Terrain", acc, M.get('terrain'), coll, smooth=True); return ob

# ------------------------------------------------------------------ cavea, orchestra, stage
def build_cavea(sc, coll, cx=0.0, cy=0.0):
    acc = Acc(floats=['tier', 'theta']); nth = 120; th = np.linspace(0, math.pi, nth + 1)
    for k in range(len(PROF) - 1):
        (r0, z0, t0), (r1, z1, t1) = PROF[k], PROF[k + 1]
        if abs(r1 - r0) < 1e-6 and abs(z1 - z0) < 1e-6: continue
        a = np.stack([r0 * np.cos(th), r0 * np.sin(th), np.full(nth + 1, z0)], 1); b = np.stack([r1 * np.cos(th), r1 * np.sin(th), np.full(nth + 1, z1)], 1)
        V = np.concatenate([a, b]); m = nth + 1
        F = np.array([[i, i + 1, m + i + 1, m + i] for i in range(nth)])
        arc = th * ((r0 + r1) / 2); uv = np.concatenate([np.stack([arc, np.zeros(m)], 1), np.stack([arc, np.full(m, math.hypot(r1 - r0, z1 - z0))], 1)])
        acc.add(V, F, uv=uv, tier=float(t1), theta=np.concatenate([th, th]))
    for sgn in (1, -1):          # cheek walls closing the cavea ends, down to the foundation
        for k in range(len(PROF) - 1):
            (r0, z0, t0), (r1, z1, t1) = PROF[k], PROF[k + 1]
            if abs(r1 - r0) < 1e-6 and abs(z1 - z0) < 1e-6: continue
            V = np.array([[sgn * r0, 0, z0], [sgn * r1, 0, z1], [sgn * r1, 0, -3], [sgn * r0, 0, -3]]); acc.add(V, [[0, 1, 2, 3]], tier=float(t1), theta=0.0 if sgn > 0 else math.pi)
    ob = mesh_obj(sc, "Cavea_Seating", acc, M.get('cavea'), coll)
    # orchestra floor (semicircle) + straight strip to the stage
    a2 = Acc(); n = 64; ang = np.linspace(0, math.pi, n + 1)
    V = np.concatenate([[[0, 0, 0.0]], np.stack([R0 * np.cos(ang), R0 * np.sin(ang), np.zeros(n + 1)], 1)]); F = [[0, 1 + i, 2 + i] for i in range(n)]
    a2.add(V, F, uv=V[:, :2]); v, f = box((0, -0.6, -0.05), (2 * R0 + 2, 1.4, 0.1)); a2.add(v, f, uv=np.zeros((8, 2)))
    mesh_obj(sc, "Orchestra_Floor", a2, M.get('floor'), coll)
    return ob

def build_hercules_niche(sc, coll):
    stone = Acc(floats=['rev', 'bz']); dark = Acc(floats=['rev', 'bz']); y = R_OUT - 0.9; z = Z_TOP
    for sx in (-1, 1):
        v, f = column((sx * 1.9, y - 0.4, z), 3.6, 0.28, 12); stone.add(v, f, rev=0.9, bz=z)
    v, f = box((0, y - 0.4, z + 3.9), (5.2, 1.0, 0.6)); stone.add(v, f, rev=0.9, bz=z)
    v, f = box((0, y + 0.1, z + 1.8), (2.6, 0.5, 3.3)); dark.add(v, f, rev=0.9, bz=z)
    v, f = box((0, y - 0.4, z + 4.5), (3.6, 1.0, 0.7)); stone.add(v, f, rev=0.9, bz=z)
    return mesh_obj(sc, "Niche_Hercules", stone, M.get('marble'), coll), mesh_obj(sc, "Niche_Hercules_Recess", dark, M.get('dark'), coll)

def build_stage(sc, coll, rng):
    """returns dict of objects. All frons pieces carry rev/bz so they can crumble top-down (decay animation)."""
    zf = STAGE_Z; AF = lambda: Acc(floats=['rev', 'bz'])
    wall, col, stuc, dark, wood = AF(), AF(), AF(), AF(), AF()
    def rev_for(zb, lo=0.07, span=0.82): return lo + span * np.clip((zb - zf) / 19.5, 0, 1) + rng.uniform(0, 0.06)
    def put(acc, vf, zb): acc.add(vf[0], vf[1], rev=rev_for(zb), bz=zb - 0.4)
    XM = 43.6
    # stage floor + pulpitum front wall with alternating niches
    v, f = box((0, FRONS_Y / 2 - 0.6, zf - 0.1), (2 * XM, -FRONS_Y + 0.6 - 0.2, 0.2)); wood.add(v, f, rev=0.04, bz=zf - 0.5)
    nb = 24; bw = 2 * XM / nb
    for i in range(nb):
        x = -XM + bw * (i + 0.5); put(wall, box((x, -0.7, zf / 2 - 0.1), (bw, 0.9, zf - 0.1)), 0.0)
        if 0 < i < nb - 1: put(dark, box((x, -1.2, zf / 2), (bw * 0.5, 0.15, zf * 0.62)), 0.0)
    # podium under the columnar order
    pb = 3.0; zp = zf + 1.4
    for i in range(int(2 * XM / pb)):
        x = -XM + pb * (i + 0.5); put(wall, box((x, -9.1, zf + 0.7), (pb, 2.4, 1.4)), zf)
    # ground order: columns, entablature, doors and niches
    cxs = [-27 + 3.6 * i for i in range(16)]; ch = 6.3; cr = 0.46
    doors = [(0.0, 3.6, 4.7), (-13.0, 2.5, 4.0), (13.0, 2.5, 4.0)]
    for x in cxs:
        put(col, column((x, -8.0, zp), ch, cr, 16), zp)
        put(wall, box((x, -8.0, zp + ch + 0.65), (3.75, 1.8, 1.3)), zp + ch)
    for i in range(len(cxs) - 1):
        xm = (cxs[i] + cxs[i + 1]) / 2; isdoor = any(abs(xm - d[0]) < 0.9 for d in doors)
        put(wall, box((xm, -8.0, zp + ch + 0.65), (3.6, 1.8, 1.3)), zp + ch)
        put(stuc, box((xm, -7.05, zp + ch + 0.65), (3.4, 0.25, 0.8)), zp + ch)
        if not isdoor:
            put(dark, box((xm, -9.05, zp + 2.0), (1.6, 0.35, 3.4)), zp)
            v, f = ellipsoid((xm, -9.2, zp + 0.9 + 1.2), (0.26, 0.26, 1.0)); put(wall, (v, f), zp)
    for (dx, dw, dh) in doors:
        put(dark, box((dx, -9.05, zp + dh / 2), (dw, 0.4, dh)), zp)
        if dx == 0.0: put(wall, arch_xz(0.0, zp + dh - 0.6, dw / 2, 0.55, -9.4, -8.65), zp + dh)
        else: put(wall, box((dx, -9.0, zp + dh + 0.3), (dw + 1.0, 0.7, 0.6)), zp + dh)
    # back wall behind the columns
    for i in range(int((2 * 31) / 3.0)):
        x = -31 + 3.0 * (i + 0.5); put(wall, box((x, -9.9, zp + 4.5), (3.0, 1.3, 9.0)), zp)
    # second order
    z2 = zp + ch + 1.3 + 0.7; ch2 = 4.7
    for i, x in enumerate(cxs[1:-1]):
        put(wall, box((x, -8.0, z2 - 0.35), (1.3, 1.3, 0.7)), z2 - 0.7)
        put(col, column((x, -8.1, z2), ch2, 0.38, 14), z2)
        put(wall, box((x, -8.1, z2 + ch2 + 0.55), (3.75, 1.5, 1.1)), z2 + ch2)
    for i in range(len(cxs) - 3):
        xm = (cxs[i + 1] + cxs[i + 2]) / 2; put(wall, box((xm, -8.1, z2 + ch2 + 0.55), (3.6, 1.5, 1.1)), z2 + ch2)
        put(stuc, box((xm, -7.3, z2 + 2.3), (2.4, 0.22, 3.0)), z2)
    for i in range(int(62 / 3.0)):
        x = -31 + 3.0 * (i + 0.5); put(wall, box((x, -9.9, z2 + 3.0), (3.0, 1.3, 6.0)), z2)
    # pediments over doors + attic and cornice
    for (dx, dw, dh) in doors:
        w = 4.4; h = 1.5; zb = z2 + ch2 + 1.1
        V = np.array([[-w / 2, -8.6, zb], [w / 2, -8.6, zb], [0, -8.6, zb + h], [-w / 2, -7.7, zb], [w / 2, -7.7, zb], [0, -7.7, zb + h]]) + (dx, 0, 0)
        put(wall, (V, [[0, 1, 2], [3, 5, 4], [0, 3, 4, 1], [0, 2, 5, 3], [1, 4, 5, 2]]), zb)
    zA = z2 + ch2 + 1.1
    for i in range(int(62 / 3.0)):
        x = -31 + 3.0 * (i + 0.5); put(wall, box((x, -9.3, zA + 1.2), (3.0, 1.6, 2.4)), zA); put(wall, box((x, -8.9, zA + 2.7), (3.1, 2.2, 0.6)), zA + 2.4)
    # flanking wings (versurae) with arched openings
    for sg in (-1, 1):
        for i in range(int((XM - 31) / 3.0) + 1):
            x = sg * (31 + 3.0 * (i + 0.5))
            for j in range(5):
                zb = zp + j * 3.4; put(wall, box((x, -8.8, zb + 1.7), (3.0, 3.4, 3.4)), zb)
                if j in (1, 3) and abs(x) < XM - 1.5: put(dark, box((x, -7.05, zb + 1.7), (1.1, 0.2, 1.9)), zb)
            put(wall, box((x, -8.8, zp + 5 * 3.4 + 0.35), (3.3, 3.8, 0.7)), zp + 5 * 3.4)
        for yy in np.arange(-0.2, -7.2, -3.0):
            for j in range(5):
                zb = zp + j * 3.4; put(wall, box((sg * (XM - 0.7), yy - 1.5, zb + 1.7), (1.4, 3.0, 3.4)), zb)
    return dict(wall=mesh_obj(sc, "Stage_Wall", wall, M.get('wall'), coll), col=mesh_obj(sc, "Stage_Columns", col, M.get('marble'), coll),
                stucco=mesh_obj(sc, "Stage_Stucco", stuc, M.get('plaster'), coll), dark=mesh_obj(sc, "Stage_Doors", dark, M.get('dark'), coll),
                wood=mesh_obj(sc, "Stage_Floor", wood, M.get('wood'), coll))

def build_colonnade(sc, coll, rng):
    col = Acc(floats=['rev', 'bz']); bm = Acc(floats=['rev', 'bz'])
    lines = [((-58, y), ) for y in np.arange(-16, -88, -4.8)] + [((58, y), ) for y in np.arange(-16, -88, -4.8)] + [((x, -90),) for x in np.arange(-52, 53, 4.8)]
    for ((x, y),) in lines:
        r = rng.uniform(0, 0.5); col.add(*column((x, y, 0.0), 6.2, 0.42, 14), rev=r, bz=0.0)
    for x in (-58, 58): bm.add(*box((x, -52, 6.6), (1.2, 74, 0.8)), rev=0.2, bz=6.0)
    bm.add(*box((0, -90, 6.6), (112, 1.2, 0.8)), rev=0.2, bz=6.0)
    return mesh_obj(sc, "Forum_Colonnade", col, M.get('marble'), coll), mesh_obj(sc, "Forum_Beams", bm, M.get('wall'), coll)

# ------------------------------------------------------------------ people
SKIN = np.array([(0.55, 0.36, 0.24), (0.42, 0.27, 0.17), (0.68, 0.48, 0.34), (0.33, 0.2, 0.13), (0.6, 0.42, 0.3)])
def fig_local(kind, sitting=True):
    """local-space figure, faces +Y. returns V,F, group (0 skin,1 cloth,2 accent/hair)"""
    V = []; F = []; G = []; n = 0
    def add(v, f, g):
        nonlocal n
        v = np.asarray(v, float); V.append(v); F.extend([[i + n for i in q] for q in f]); G.append(np.full(len(v), g)); n += len(v)
    kid = kind == 'child'
    s = 0.72 if kid else 1.0
    if sitting:
        add(*box((0, 0, 0.12 * s), (0.36 * s, 0.24 * s, 0.2 * s)), 1)
        add(*cyl((0, 0, 0.2 * s), 0.19 * s, 0.56 * s, 8, 0.23 * s), 1)
        add(*ellipsoid((0, 0.01, 0.86 * s), (0.095 * s, 0.1 * s, 0.115 * s), 8, 6), 0)
        add(*ellipsoid((0, -0.012, 0.9 * s), (0.1 * s, 0.1 * s, 0.1 * s), 8, 5), 2)
        for sx in (-1, 1):
            add(*box((sx * 0.1 * s, 0.24 * s, 0.17 * s), (0.13 * s, 0.5 * s, 0.14 * s)), 1)
            add(*box((sx * 0.1 * s, 0.46 * s, -0.12 * s), (0.11 * s, 0.12 * s, 0.5 * s)), 0 if kind == 'sandals' else 1)
            add(*cyl((sx * 0.215 * s, 0.05 * s, 0.4 * s), 0.05 * s, 0.34 * s, 5, 0.04 * s), 1)
            add(*box((sx * 0.22 * s, 0.17 * s, 0.38 * s), (0.07 * s, 0.22 * s, 0.07 * s)), 0)
    else:
        add(*cyl((0, 0, 0.0), 0.2 * s, 0.82 * s, 8, 0.16 * s), 1)
        add(*cyl((0, 0, 0.82 * s), 0.17 * s, 0.56 * s, 8, 0.2 * s), 1)
        add(*ellipsoid((0, 0.01, 1.52 * s), (0.095 * s, 0.1 * s, 0.115 * s), 8, 6), 0)
        add(*ellipsoid((0, -0.012, 1.56 * s), (0.1 * s, 0.1 * s, 0.1 * s), 8, 5), 2)
        for sx in (-1, 1): add(*cyl((sx * 0.23 * s, 0.02, 0.84 * s), 0.05 * s, 0.5 * s, 5, 0.04 * s), 1)
    return np.concatenate(V), F, np.concatenate(G)

_FIG = {}
def _fig(kind, sitting):
    k = (kind, sitting)
    if k not in _FIG: _FIG[k] = fig_local(kind, sitting)
    return _FIG[k]

def _cloth(rng, tier, kind):
    if kind == 'woman': pal = [(0.46, 0.08, 0.07), (0.1, 0.22, 0.4), (0.12, 0.3, 0.16), (0.55, 0.35, 0.08), (0.35, 0.1, 0.3), (0.7, 0.62, 0.5)]
    elif tier == 0: pal = [(0.72, 0.68, 0.6)] * 5 + [(0.56, 0.1, 0.12)]       # white togas, some purple-red
    elif tier == 1: pal = [(0.5, 0.38, 0.22), (0.45, 0.2, 0.12), (0.28, 0.3, 0.14), (0.6, 0.52, 0.4), (0.2, 0.26, 0.4)]
    else: pal = [(0.32, 0.26, 0.18), (0.26, 0.2, 0.14), (0.4, 0.32, 0.2), (0.22, 0.24, 0.16)]
    c = np.array(pal[rng.integers(0, len(pal))]) * rng.uniform(0.85, 1.12); return np.clip(c, 0, 1)

def build_crowd(sc, coll, rng):
    acc = Acc(floats=['rev', 'sway'], colors=['Col']); spacing = 0.47
    nst = lambda ti: 2.6 + 0.4 * ti
    row_i = 0; total = 0
    prof = PROF; seat_rows = []
    k = 0
    for ti, (rows, tread, riser) in enumerate(TIERS):
        for i in range(rows):
            # locate the profile points of this row: riser top (r0,z), then tread end
            while not (prof[k][2] == ti and prof[k + 1][0] > prof[k][0] and abs(prof[k + 1][1] - prof[k][1]) < 1e-6): k += 1
            r0, z0 = prof[k][0], prof[k][1]; seat_rows.append((ti, r0 + tread * 0.52, z0, row_i, tread)); k += 1; row_i += 1
    nrows = len(seat_rows)
    for ti, r, z, ri, tread in seat_rows:
        nseat = int(math.pi * r / spacing)
        for s_ in range(nseat):
            th = (s_ + 0.5) / nseat * math.pi
            frac = (th * nst(ti)) % 1.0
            if abs(frac - 0.5) * (1.0 / nst(ti)) * r < 0.72: continue       # leave the radial stairways clear
            if rng.random() < 0.07: continue
            woman = rng.random() < (0.35 if ti > 0 else 0.1); kid = rng.random() < 0.06
            kind = 'child' if kid else ('woman' if woman else 'man')
            V0, F0, G0 = _fig(kind, True)
            facing = th + math.pi + rng.normal(0, 0.12)                       # look toward the orchestra / stage
            cr, sr = math.cos(facing - math.pi / 2), math.sin(facing - math.pi / 2)
            Rm = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]]); sc_ = rng.uniform(0.93, 1.07)
            P = (V0 * sc_) @ Rm.T + np.array([r * math.cos(th), r * math.sin(th), z])
            cloth = _cloth(rng, ti, kind); skin = SKIN[rng.integers(0, len(SKIN))] * rng.uniform(0.85, 1.1)
            hair = np.array([0.04, 0.03, 0.025]) * rng.uniform(0.6, 2.2) if rng.random() > 0.08 else np.array([0.45, 0.43, 0.4])
            colv = np.where((G0 == 0)[:, None], skin, np.where((G0 == 1)[:, None], cloth, hair)); sway = np.where(G0 == 1, 0.7, 1.0) * (np.clip((V0[:, 2] - 0.1) * 1.6, 0, 1))
            rev = (ri / nrows) * 0.82 + rng.uniform(0, 0.18)
            acc.add(P, F0, rev=rev, sway=sway, Col=np.concatenate([colv, np.ones((len(colv), 1))], 1)); total += 1
    ob = mesh_obj(sc, "Crowd_6000", acc, M.get('people'), coll)
    lib.add_wind(ob, 0.035, 1.1); ob['seats'] = total; return ob

def figure_object(sc, name, kind, cloth, skin, hair=(0.04, 0.03, 0.025), mask=None, coll=None, scale=1.0):
    V0, F0, G0 = _fig(kind, False); acc = Acc(floats=['rev', 'sway'], colors=['Col'])
    colv = np.where((G0 == 0)[:, None], np.array(skin), np.where((G0 == 1)[:, None], np.array(cloth), np.array(hair)))
    acc.add(V0 * scale, F0, rev=-1.0, sway=np.clip(V0[:, 2] * 0.5, 0, 1), Col=np.concatenate([colv, np.ones((len(colv), 1))], 1))
    return mesh_obj(sc, name, acc, M.get('people'), coll)

def build_visitors(sc, coll, rng, n=170):
    acc = Acc(floats=['rev', 'ph', 'sway'], colors=['Col'], vecs=['vel'])
    pal = [(0.05, 0.06, 0.08), (0.45, 0.1, 0.08), (0.12, 0.2, 0.35), (0.6, 0.58, 0.5), (0.08, 0.08, 0.08), (0.2, 0.32, 0.18), (0.7, 0.45, 0.1), (0.85, 0.85, 0.82)]
    V0, F0, G0 = _fig('man', False)
    for i in range(n):
        zone = rng.random()
        if zone < 0.62: x, y = rng.uniform(-55, 55), rng.uniform(-85, -14)
        elif zone < 0.82: x, y = rng.uniform(-9, 9), rng.uniform(1, 9)           # orchestra
        else:
            tt = rng.integers(0, 3); rows = [(0, 7), (1, 8), (2, 6)][tt]; rr = R0 + rng.uniform(2, 22); th = rng.uniform(0.2, 2.9); x, y = rr * math.cos(th), rr * math.sin(th)
        z = float(height(x, y)) + (0.0)
        ang = rng.uniform(0, math.tau); sp = rng.uniform(0.25, 0.7) if zone < 0.82 else 0.0
        c, s_ = math.cos(ang), math.sin(ang); R = np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1]]); sc_ = rng.uniform(0.92, 1.06)
        P = (V0 * sc_) @ R.T + np.array([x, y, z]); cloth = np.array(pal[rng.integers(0, len(pal))]) * rng.uniform(0.8, 1.1); skin = SKIN[rng.integers(0, len(SKIN))]
        colv = np.where((G0 == 0)[:, None], skin, np.where((G0 == 1)[:, None], cloth, np.array([0.04, 0.03, 0.03])))
        vel = np.array([-s_ * sp, c * sp, 0.0]); acc.add(P, F0, rev=rng.uniform(0, 1), ph=rng.uniform(0, 6.28), sway=0.0, Col=np.concatenate([colv, np.ones((len(colv), 1))], 1), vel=vel)
    ob = mesh_obj(sc, "Visitors_2026", acc, M.get('visitors'), coll); GN.add_mod(ob, GN.drift_group(), "Drift", T0=80.0); return ob

# ------------------------------------------------------------------ city
def building_set(sc, name, mat, coll, rng, spacing, jitter, prob, fw, fd, floors, fh, modern=True, exclusion=None, seed_bias=None, zrange=None, tanks=True):
    wallacc = Acc(floats=['rev', 'bz', 'isroof'], colors=['Col']); extra = Acc(floats=['rev', 'bz']); metal = Acc(floats=['rev', 'bz'])
    pal = [(0.66, 0.57, 0.44), (0.72, 0.64, 0.5), (0.6, 0.5, 0.38), (0.78, 0.72, 0.62), (0.68, 0.5, 0.4), (0.55, 0.52, 0.48), (0.8, 0.77, 0.7)]
    for gx in np.arange(-230, 231, spacing[0]):
        for gy in np.arange(-230, 231, spacing[1]):
            if rng.random() > prob: continue
            x = gx + rng.uniform(-jitter, jitter); y = gy + rng.uniform(-jitter, jitter)
            if exclusion and exclusion(x, y): continue
            w = rng.uniform(*fw); d = rng.uniform(*fd); nf = int(rng.integers(floors[0], floors[1] + 1)); rot = rng.choice([0, 0.0, 0.08, -0.08, 0.35])
            cs = np.array([[-w / 2, -d / 2], [w / 2, -d / 2], [w / 2, d / 2], [-w / 2, d / 2]]); cr, sr = math.cos(rot), math.sin(rot)
            cs = cs @ np.array([[cr, sr], [-sr, cr]]) + (x, y); zs = height(cs[:, 0], cs[:, 1]); zb = float(zs.min()); zt = float(zs.max()) + nf * fh
            if zrange and not (zrange[0] <= float(zs.mean()) <= zrange[1]): continue
            zbot = zb - 6.0; col = np.array(pal[rng.integers(0, len(pal))]) * rng.uniform(0.9, 1.08)
            prox = np.hypot(x, y + 50) / 260.0; rev = float(np.clip(prox * 0.75 + rng.uniform(0, 0.25), 0, 0.97))
            zref = zt - nf * fh
            for k in range(4):
                a, b = cs[k], cs[(k + 1) % 4]; L = float(np.hypot(*(b - a)))
                V = np.array([[a[0], a[1], zbot], [b[0], b[1], zbot], [b[0], b[1], zt], [a[0], a[1], zt]])
                uv = np.array([[0, (zbot - zref) / fh], [L / 3.0, (zbot - zref) / fh], [L / 3.0, nf], [0, nf]])
                wallacc.add(V, [[0, 1, 2, 3]], uv=uv, rev=rev, bz=zbot, isroof=0.0, Col=np.append(col, 1))
            V = np.array([[*cs[0], zt], [*cs[1], zt], [*cs[2], zt], [*cs[3], zt]]); wallacc.add(V, [[0, 1, 2, 3]], uv=np.zeros((4, 2)), rev=rev, bz=zbot, isroof=1.0, Col=np.append(col, 1))
            if tanks and rng.random() < 0.55:
                tx, ty = x + rng.uniform(-w / 4, w / 4), y + rng.uniform(-d / 4, d / 4)
                v, f = cyl((tx, ty, zt), 0.55, 1.2, 9, 0.5); metal.add(v, f, rev=rev, bz=zbot)
                v, f = box((x + w * 0.25, y - d * 0.2, zt + 1.1), (1.8, 1.8, 2.2)); extra.add(v, f, rev=rev, bz=zbot)
    obs = [mesh_obj(sc, name, wallacc, mat, coll)]
    if extra.n: obs.append(mesh_obj(sc, name + "_Stairwells", extra, M.get('roof'), coll))
    if metal.n: obs.append(mesh_obj(sc, name + "_Tanks", metal, M.get('metal'), coll))
    for o in obs: GN.add_mod(o, GN.grow_group(), "Grow", T=0.0)
    return obs

def tree_set(sc, name, coll, rng, n, kind, region, exclusion=None):
    acc = Acc(floats=['rev', 'bz'], colors=['Col']); trunk = Acc(floats=['rev', 'bz'])
    for i in range(n):
        x = rng.uniform(*region[0]); y = rng.uniform(*region[1])
        if exclusion and exclusion(x, y): continue
        z = float(height(x, y)); rev = rng.uniform(0, 0.9); s = rng.uniform(0.8, 1.35)
        if kind == 'cypress':
            v, f = ellipsoid((x, y, z + 4.5 * s), (0.9 * s, 0.9 * s, 4.6 * s), 8, 7); c = (0.03, 0.09, 0.03)
        elif kind == 'pine':
            v, f = ellipsoid((x, y, z + 7 * s), (3.2 * s, 3.2 * s, 2.0 * s), 9, 6); c = (0.05, 0.12, 0.04)
            tv, tf = cyl((x, y, z), 0.2 * s, 6 * s, 6); trunk.add(tv, tf, rev=rev, bz=z - 1)
        else:   # olive
            v, f = ellipsoid((x, y, z + 3.0 * s), (2.4 * s, 2.4 * s, 1.6 * s), 9, 6); c = (0.14, 0.2, 0.1)
            tv, tf = cyl((x, y, z), 0.22 * s, 2.6 * s, 6); trunk.add(tv, tf, rev=rev, bz=z - 1)
        acc.add(v, f, rev=rev, bz=z - 1, Col=(*(np.array(c) * rng.uniform(0.8, 1.25, 3)), 1))
    obs = [mesh_obj(sc, name, acc, M.get('tree'), coll)]
    if trunk.n: obs.append(mesh_obj(sc, name + "_Trunks", trunk, M.get('wall'), coll))
    for o in obs: GN.add_mod(o, GN.grow_group(), "Grow", T=0.0)
    return obs

def build_weeds(sc, coll, rng, n=700):
    acc = Acc(floats=['rev', 'bz'], colors=['Col'])
    for i in range(n):
        ti = rng.integers(0, 3); rows = TIERS[ti][0]; r = R0 + rng.uniform(1, R_OUT - R0 - 4); th = rng.uniform(0.03, math.pi - 0.03); z = float(cavea_floor(r))
        s = rng.uniform(0.18, 0.55); v, f = ellipsoid((r * math.cos(th), r * math.sin(th), z + s * 0.4), (s, s, s * 0.75), 7, 5)
        g = rng.random(); c = (0.12, 0.2, 0.05) if g < 0.55 else (0.33, 0.28, 0.1)
        acc.add(v, f, rev=rng.uniform(0, 1), bz=z - 0.3, Col=(*(np.array(c) * rng.uniform(0.7, 1.3, 3)), 1))
    ob = mesh_obj(sc, "Weeds_Vegetation", acc, M.get('weed'), coll); GN.add_mod(ob, GN.grow_group(), "Grow", T=0.0); return ob

# ------------------------------------------------------------------ whole world
def build_world(sc, quality=1.0):
    rng = np.random.default_rng(2026); W = {}
    c_env = lib.collection(sc, "Environment"); c_arch = lib.collection(sc, "Theatre"); c_city = lib.collection(sc, "City"); c_people = lib.collection(sc, "People")
    W['terrain'] = build_terrain(sc, c_env)
    W['cavea'] = build_cavea(sc, c_arch); W['niche'] = build_hercules_niche(sc, c_arch)
    W['stage'] = build_stage(sc, c_arch, rng); W['colonnade'] = build_colonnade(sc, c_arch, rng)
    W['crowd'] = build_crowd(sc, c_people, rng); W['visitors'] = build_visitors(sc, c_people, rng)
    W['weeds'] = build_weeds(sc, c_arch, rng)
    keep_out = lambda x, y: (np.hypot(x, y) < R_OUT + 6 and y > -14) or (abs(x) < 70 and -98 < y < -6)
    house = M.get('house'); modern = M.get('modern')
    W['ancient'] = building_set(sc, "Ancient_Houses", house, c_city, rng, (30, 27), 7, 0.7, (6.5, 10.5), (6, 9.5), (1, 2), 3.2, False, keep_out, tanks=False)
    W['mid'] = building_set(sc, "Medieval_Houses", house, c_city, rng, (17, 16), 4, 0.72, (6, 9.5), (6, 9), (1, 3), 3.0, False, keep_out, tanks=False)
    W['modern'] = building_set(sc, "Modern_Amman", modern, c_city, rng, (11.5, 12.5), 2.2, 0.9, (7.5, 11.5), (7.5, 11), (3, 7), 3.1, True, keep_out)
    W['trees_pine'] = tree_set(sc, "Trees_Modern", c_env, rng, 380, 'pine', ((-200, 200), (-200, 200)), lambda x, y: keep_out(x, y) and not (abs(x) < 70 and -98 < y < -8 and abs(abs(x) - 60) > 6))
    W['trees_olive'] = tree_set(sc, "Trees_Ancient", c_env, rng, 420, 'olive', ((-220, 220), (-200, 220)), keep_out)
    W['trees_cypress'] = tree_set(sc, "Trees_Cypress", c_env, rng, 160, 'cypress', ((-200, 200), (-200, 200)), keep_out)
    return W
