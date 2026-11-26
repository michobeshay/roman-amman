"""Film timeline: 3150 frames @30fps (105 s). Scene frame ranges and all state/camera animation."""
import bpy, math, json
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
import lib, amman_mats as M, amman_gn as GN, amman_build as B

SC = {'S1': (1, 240), 'S2': (241, 750), 'S3': (751, 1290), 'S4': (1291, 1950), 'S5': (1951, 2700), 'S6': (2701, 3150)}
END = 3150
SUN_ROT = 300.0

def kv(sock, keys, interp=None):
    for f, v in keys:
        sock.default_value = v; sock.keyframe_insert('default_value', frame=f)

def key_all(nodes, keys):
    for n in nodes: kv(n, keys)

def grow(objs, keys):
    for o in (objs if isinstance(objs, (list, tuple)) else [objs]): GN.key_mod(o, "Grow", "T", keys)

def anchors():
    R = lambda r, th: (r * math.cos(math.radians(th)), r * math.sin(math.radians(th)), float(B.cavea_floor(r)) + 0.4)
    return {'orchestra': (0, 5.5, 0.3), 'stage': (0, -5, B.STAGE_Z + 0.2), 'frons': (0, -9.6, 11.0), 'tier0': R(B.R0 + 5, 62), 'tier1': R(B.R0 + 15.5, 62), 'tier2': R(B.R0 + 24, 62),
            'crowd': R(B.R0 + 12, 118), 'niche': (0, B.R_OUT - 1.0, B.Z_TOP + 2.0)}

def make_cam(sc, name, keys, tkeys, lens=32, fstop=8.0, dof=False, start=1):
    cam, tg = lib.make_camera(sc, name, keys[0][1], tkeys[0][1], lens=lens, fstop=fstop)
    cam.data.dof.use_dof = dof; cam.data.dof.focus_object = tg
    lib.key_path(cam, 'location', keys); lib.key_path(tg, 'location', tkeys)
    mk = sc.timeline_markers.new(name, frame=start); mk.camera = cam
    return cam, tg

def arc_pos(center, az_deg, R, z):
    a = math.radians(az_deg); return (center[0] + R * math.sin(a), center[1] - R * math.cos(a), z)

def build_film(sc, quality=1.0):
    W = B.build_world(sc, quality); rng = np.random.default_rng(5)
    # actors
    actors = []
    cols = [((0.55, 0.08, 0.06), (0.55, 0.38, 0.26)), ((0.82, 0.78, 0.66), (0.4, 0.27, 0.17)), ((0.12, 0.25, 0.45), (0.6, 0.44, 0.32)), ((0.6, 0.45, 0.08), (0.33, 0.21, 0.14)), ((0.35, 0.1, 0.3), (0.55, 0.38, 0.26)), ((0.15, 0.32, 0.18), (0.42, 0.28, 0.18))]
    for i, (c, s_) in enumerate(cols):
        a = B.figure_object(sc, f"Actor_{i}", 'man', c, s_, scale=1.0)
        xs = -7.5 + 3.0 * i + rng.uniform(-0.6, 0.6); ys = -3.8 - rng.uniform(0, 2.4); side = -1 if i % 2 == 0 else 1
        a.location = (side * 40, -6.5, B.STAGE_Z); a.keyframe_insert('location', frame=1050)
        a.location = (xs, ys, B.STAGE_Z); a.keyframe_insert('location', frame=1100)
        a.location = (xs + rng.uniform(-1.2, 1.2), ys + rng.uniform(-0.6, 0.6), B.STAGE_Z); a.keyframe_insert('location', frame=1200)
        a.location = (xs + rng.uniform(-1.5, 1.5), ys + 0.4, B.STAGE_Z); a.keyframe_insert('location', frame=1290)
        a.rotation_euler = (0, 0, 0 + 0.3 * (1 if i % 2 else -1)); a.hide_render = True; a.keyframe_insert('hide_render', frame=1049)
        a.hide_render = False; a.keyframe_insert('hide_render', frame=1050); a.hide_render = True; a.keyframe_insert('hide_render', frame=1291)
        actors.append(a)
    W['actors'] = actors
    # --------------------------------------------------------------- world + render
    lib.setup_render(sc, res=(1080, 1920), samples=48, start=1, end=END)
    w = lib.sky(sc, elevation=24, rotation=SUN_ROT, strength=1.0, dust=2.0); sky = [n for n in w.node_tree.nodes if n.type == 'TEX_SKY'][0]
    sc.view_settings.exposure = -1.35
    kv_sky = lambda keys: [(sky.__setattr__('sun_rotation', math.radians(v)), sky.keyframe_insert('sun_rotation', frame=f)) for f, v in keys]
    kv_sky([(1, SUN_ROT), (1290, SUN_ROT), (1950, SUN_ROT + 380), (2100, SUN_ROT + 400), (3150, SUN_ROT + 405)])
    # --------------------------------------------------------------- state animation
    terr = M.get('terrain'); mod_node = terr.node_tree.nodes[terr['modern_node']]
    kv(mod_node.outputs[0], [(1, 1.0), (60, 1.0), (200, 0.0), (1700, 0.0), (2050, 1.0)])
    wnodes = [n.outputs[0] for (_m, n) in M.WEATHER_NODES]
    key_all(wnodes, [(1, 0.5), (80, 0.5), (230, 0.0), (1290, 0.05), (1900, 0.95), (2100, 0.42), (3150, 0.42)])
    # tier highlight (architecture explains itself): tiers glow in turn during S3
    for (_m, idx, lev) in M.HILITE_NODES:
        kv(idx.outputs[0], [(1, -1.0), (1169, -1.0), (1170, 0.0), (1199, 0.0), (1200, 1.0), (1229, 1.0), (1230, 2.0), (1260, 2.0)])
        kv(lev.outputs[0], [(1, 0.0), (1170, 0.0), (1183, 2.2), (1199, 0.0), (1200, 0.0), (1213, 2.2), (1229, 0.0), (1230, 0.0), (1243, 2.2), (1262, 0.0)])
    # modern layers
    grow(W['modern'], [(1, 1.1), (60, 1.1), (200, 0.0), (1690, 0.0), (1950, 0.55), (2100, 1.1)])
    grow(W['trees_pine'], [(1, 1.1), (80, 1.1), (200, 0.0), (1800, 0.0), (2100, 1.1)])
    grow(W['mid'], [(1, 0.0), (1380, 0.0), (1570, 1.1), (1850, 0.85), (2000, 0.55), (2120, 0.0)])
    grow(W['ancient'], [(1, 0.0), (100, 0.0), (230, 1.1), (1380, 1.1), (1800, 0.25), (2000, 0.0)])
    grow(W['trees_olive'], [(1, 0.0), (110, 0.0), (230, 1.1), (1500, 1.1), (1900, 0.3), (2100, 0.0)])
    grow(W['trees_cypress'], [(1, 1.1), (3150, 1.1)])
    grow(W['weeds'], [(1, 0.0), (1400, 0.0), (1800, 0.95), (2000, 0.95), (2110, 0.0)])
    st = W['stage']
    for k in ('wall', 'col', 'stucco', 'dark', 'wood'): GN.add_mod(st[k], GN.grow_group(), "Grow", T=0.12)
    frons_keys = [(1, 0.12), (110, 0.12), (235, 1.1), (1330, 1.1), (1500, 0.8), (1850, 0.12), (3150, 0.12)]
    for k in ('wall', 'col', 'stucco', 'dark', 'wood'): grow(st[k], frons_keys)
    for o in W['colonnade']: GN.add_mod(o, GN.grow_group(), "Grow", T=0.0)
    grow(list(W['colonnade']), [(1, 0.0), (120, 0.0), (240, 1.1), (1500, 1.1), (1750, 0.0)])
    # crowd + visitors
    grow(W['crowd'], [(1, 0.0), (750, 0.0), (751, 0.0), (905, 1.05), (1291, 1.05), (1330, 0.0)])
    grow(W['visitors'], [(1, 1.05), (45, 1.05), (125, 0.0), (1960, 0.0), (2110, 1.05)])
    # --------------------------------------------------------------- cameras
    A = anchors(); cams = {}
    cx0 = (0, 0)
    cams['C1'] = make_cam(sc, "Cam_S1_Aerial", [(1, (60, -310, 235)), (240, (20, -122, 68))], [(1, (0, 25, 10)), (240, (0, 6, 12))], lens=28, fstop=16, start=1)
    pos = [(241 + i * 14, arc_pos((0, -5), 24 - 58 * (i / 9), 140 - 36 * (i / 9), 76 - 28 * (i / 9))) for i in range(10)]
    cams['C2a'] = make_cam(sc, "Cam_S2_AerialOrbit", pos, [(241, (0, 5, 12)), (370, (0, 6, 11))], lens=32, fstop=16, start=241)
    cams['C2b'] = make_cam(sc, "Cam_S2_Frontal", [(371, (0, -125, 78)), (480, (0, -75, 50))], [(371, (0, 6, 8)), (480, (0, 6, 6))], lens=32, fstop=11, start=371)
    th0, th1, rr = 72, 90, 23.4; zf = float(B.cavea_floor(rr)) + 0.55
    cams['C2c'] = make_cam(sc, "Cam_S2_StoneCloseup", [(481, (rr * math.cos(math.radians(th0)), rr * math.sin(math.radians(th0)), zf)), (580, (rr * math.cos(math.radians(th1)), rr * math.sin(math.radians(th1)), zf + 0.05))],
                           [(481, (20.5 * math.cos(math.radians(th0 + 4)), 20.5 * math.sin(math.radians(th0 + 4)), float(B.cavea_floor(20.5)) + 0.25)), (580, (20.5 * math.cos(math.radians(th1 + 4)), 20.5 * math.sin(math.radians(th1 + 4)), float(B.cavea_floor(20.5)) + 0.25))], lens=55, fstop=2.2, dof=True, start=481)
    cams['C2d'] = make_cam(sc, "Cam_S2_FromStage", [(581, (0, -4.6, 3.3)), (750, (0, -1.8, 3.5))], [(581, (0, 24, 11)), (750, (0, 20, 12.5))], lens=22, fstop=8, start=581)
    cams['C3a'] = make_cam(sc, "Cam_S3_WideFill", [(751, (0, -5.5, 12.5)), (900, (0, -7.5, 13.5))], [(751, (0, 28, 9.5)), (900, (0, 26, 10.5))], lens=22, fstop=11, start=751)
    cams['C3b'] = make_cam(sc, "Cam_S3_Tracking", [(901, (-11, 2.0, 3.1)), (1050, (11, 3.0, 3.3))], [(901, (-2, 28, 11)), (1050, (2, 28, 11))], lens=30, fstop=5.6, dof=True, start=901)
    cams['C3c'] = make_cam(sc, "Cam_S3_Actors", [(1051, (7.5, 9.5, 3.6)), (1170, (5.0, 8.0, 3.2))], [(1051, (-1, -4.8, 3.0)), (1170, (-1, -4.8, 3.0))], lens=42, fstop=3.2, dof=True, start=1051)
    cams['C3d'] = make_cam(sc, "Cam_S3_Crane", [(1171, (0, 8, 4)), (1290, (0, -62, 52))], [(1171, (0, 24, 10)), (1290, (0, 18, 9))], lens=26, fstop=11, start=1171)
    cams['C4'] = make_cam(sc, "Cam_S4_TimeLapse", [(1291, (0, -75, 50)), (1950, (11, -73, 51.5))], [(1291, (0, 6, 6)), (1950, (0, 6, 6))], lens=32, fstop=11, start=1291)
    cams['C5a'] = make_cam(sc, "Cam_S5_SameAngle", [(1951, (11, -73, 51.5)), (2100, (0, -75, 50))], [(1951, (0, 6, 6)), (2100, (0, 6, 6))], lens=32, fstop=11, start=1951)
    cams['C5b'] = make_cam(sc, "Cam_S5_Seating", [(2101, (-4, 3.5, 2.0)), (2250, (3, 2.5, 2.3))], [(2101, (0, 26, 11)), (2250, (0, 26, 11.5))], lens=30, fstop=4.0, dof=True, start=2101)
    cams['C5c'] = make_cam(sc, "Cam_S5_Plaza", [(2251, (-44, -42, 3.0)), (2450, (-22, -48, 3.2))], [(2251, (8, -4, 8)), (2450, (4, -2, 8))], lens=32, fstop=5.6, dof=True, start=2251)
    cams['C5d'] = make_cam(sc, "Cam_S5_FromTop", [(2451, (-12, 32, 18)), (2700, (12, 34, 19))], [(2451, (0, -100, 6)), (2700, (-6, -100, 7))], lens=24, fstop=11, start=2451)
    cams['C6'] = make_cam(sc, "Cam_S6_PullBack", [(2701, (0, -98, 40)), (3150, (70, -330, 210))], [(2701, (0, 0, 9)), (3150, (0, 10, 4))], lens=30, fstop=16, start=2701)
    sc.frame_set(1)
    return W, cams, A

def dump_labels(sc, A, path, frames):
    out = {}
    for f in frames:
        sc.frame_set(f); cam = sc.camera; row = {}
        for k, p in A.items():
            c = world_to_camera_view(sc, cam, Vector(p)); row[k] = [round(c.x, 4), round(1 - c.y, 4), round(c.z, 2)]
        out[str(f)] = row
    json.dump(out, open(path, 'w')); print("RS labels", len(out))
