"""Shared building blocks for the bee documentary. Blender 5.0 API."""
import bpy, math, random, time
import numpy as np
from mathutils import Vector

# ------------------------------------------------------------------ meshes
def mesh_from_arrays(name, verts, faces, uv=None, attrs=None, colors=None, smooth=True):
    """verts (N,3) float, faces: list of index tuples (tri/quad mixed ok).
    uv (N,2) per-vertex, attrs {name: (N,) float} point attributes,
    colors {name: (N,4)} point colour attributes."""
    me = bpy.data.meshes.new(name)
    me.from_pydata(np.asarray(verts, dtype=np.float32).tolist(), [], [list(map(int, f)) for f in faces] if not isinstance(faces, np.ndarray) else faces.tolist())
    me.update()
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    if uv is not None:
        uvl = me.uv_layers.new(name="UVMap")
        li = np.empty(len(me.loops), dtype=np.int32)
        me.loops.foreach_get("vertex_index", li)
        uvl.data.foreach_set("uv", np.asarray(uv, dtype=np.float32)[li].ravel())
    for k, v in (attrs or {}).items():
        a = me.attributes.new(name=k, type='FLOAT', domain='POINT')
        a.data.foreach_set("value", np.asarray(v, dtype=np.float32))
    for k, v in (colors or {}).items():
        a = me.color_attributes.new(name=k, type='FLOAT_COLOR', domain='POINT')
        a.data.foreach_set("color", np.asarray(v, dtype=np.float32).ravel())
    return me

def link_obj(sc, name, data, coll=None):
    ob = bpy.data.objects.new(name, data)
    (coll or sc.collection).objects.link(ob)
    return ob

def collection(sc, name):
    c = bpy.data.collections.new(name)
    sc.collection.children.link(c)
    return c

# ------------------------------------------------------------------ materials
def _n(nt, t, loc=(0, 0), **kw):
    n = nt.nodes.new(t); n.location = loc
    for k, v in kw.items(): setattr(n, k, v)
    return n

def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL': nt.nodes.remove(n)
    out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    return m, nt, out

def ramp(nt, stops, loc=(0, 0)):
    r = _n(nt, 'ShaderNodeValToRGB', loc)
    el = r.color_ramp.elements
    while len(el) > len(stops): el.remove(el[-1])
    while len(el) < len(stops): el.new(0.5)
    for e, (p, c) in zip(el, stops):
        e.position = p; e.color = c
    return r

def mat_grass(name="Grass", base=(0.012, 0.06, 0.008, 1), tip=(0.10, 0.27, 0.03, 1), dry=(0.35, 0.28, 0.08, 1), dryness=0.0):
    m, nt, out = new_mat(name)
    uv = _n(nt, 'ShaderNodeTexCoord', (-900, 0))
    sep = _n(nt, 'ShaderNodeSeparateXYZ', (-700, 0)); nt.links.new(uv.outputs['UV'], sep.inputs[0])
    at = _n(nt, 'ShaderNodeAttribute', (-900, -250), attribute_name='Col', attribute_type='GEOMETRY')
    r = ramp(nt, [(0.0, base), (1.0, tip)], (-480, 100)); nt.links.new(sep.outputs['Y'], r.inputs[0])
    var = _n(nt, 'ShaderNodeMix', (-480, -150), data_type='RGBA', blend_type='MULTIPLE' if False else 'MIX')
    # per-blade variation: mix toward dry colour using attribute R
    var.inputs[0].default_value = dryness
    nt.links.new(r.outputs['Color'], var.inputs[6]); var.inputs[7].default_value = dry
    fac = _n(nt, 'ShaderNodeMath', (-700, -250), operation='MULTIPLY'); nt.links.new(at.outputs['Fac'], fac.inputs[0]); fac.inputs[1].default_value = min(1.0, max(dryness, 0.01))
    nt.links.new(fac.outputs[0], var.inputs[0]) if dryness > 0 else None
    pb = _n(nt, 'ShaderNodeBsdfPrincipled', (-200, 100))
    pb.inputs['Roughness'].default_value = 0.5; pb.inputs['Specular IOR Level'].default_value = 0.35
    nt.links.new(var.outputs[2], pb.inputs['Base Color'])
    tr = _n(nt, 'ShaderNodeBsdfTranslucent', (-200, -150)); nt.links.new(var.outputs[2], tr.inputs['Color'])
    mx = _n(nt, 'ShaderNodeMixShader', (60, 0)); mx.inputs[0].default_value = 0.22
    nt.links.new(pb.outputs[0], mx.inputs[1]); nt.links.new(tr.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs['Surface'])
    return m

def mat_ground(name="Ground", a=(0.025, 0.05, 0.012, 1), b=(0.06, 0.09, 0.02, 1), soil=(0.06, 0.04, 0.025, 1)):
    m, nt, out = new_mat(name)
    tc = _n(nt, 'ShaderNodeTexCoord', (-900, 0))
    n1 = _n(nt, 'ShaderNodeTexNoise', (-650, 100), noise_dimensions='3D'); n1.inputs['Scale'].default_value = 1.6; n1.inputs['Detail'].default_value = 8
    nt.links.new(tc.outputs['Object'], n1.inputs['Vector'])
    n2 = _n(nt, 'ShaderNodeTexNoise', (-650, -150), noise_dimensions='3D'); n2.inputs['Scale'].default_value = 35; n2.inputs['Detail'].default_value = 10
    nt.links.new(tc.outputs['Object'], n2.inputs['Vector'])
    r = ramp(nt, [(0.35, a), (0.65, b)], (-400, 100)); nt.links.new(n1.outputs['Fac'], r.inputs[0])
    sm = _n(nt, 'ShaderNodeMix', (-180, 0), data_type='RGBA')
    nt.links.new(n2.outputs['Fac'], sm.inputs[0]); nt.links.new(r.outputs['Color'], sm.inputs[6]); sm.inputs[7].default_value = soil
    bp = _n(nt, 'ShaderNodeBump', (-180, -250)); bp.inputs['Strength'].default_value = 0.6; nt.links.new(n2.outputs['Fac'], bp.inputs['Height'])
    pb = _n(nt, 'ShaderNodeBsdfPrincipled', (80, 0)); pb.inputs['Roughness'].default_value = 0.9
    nt.links.new(sm.outputs[2], pb.inputs['Base Color']); nt.links.new(bp.outputs[0], pb.inputs['Normal'])
    nt.links.new(pb.outputs[0], out.inputs['Surface'])
    return m

# ------------------------------------------------------------------ geometry
def terrain(sc, name, size=40.0, res=160, amp=0.25, freq=0.18, seed=1, mat=None, coll=None):
    rng = np.random.default_rng(seed)
    xs = np.linspace(-size / 2, size / 2, res); X, Y = np.meshgrid(xs, xs)
    ph = rng.uniform(0, 6.28, (4, 2))
    Z = sum(amp / (i + 1) * np.sin(freq * (i + 1) * 2.3 * X + ph[i, 0]) * np.cos(freq * (i + 1) * 1.9 * Y + ph[i, 1]) for i in range(4))
    V = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    idx = np.arange(res * res).reshape(res, res)
    F = np.stack([idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()], 1)
    me = mesh_from_arrays(name, V, F)
    ob = link_obj(sc, name, me, coll)
    if mat: ob.data.materials.append(mat)
    def height(x, y):
        z = 0
        for i in range(4):
            z += amp / (i + 1) * np.sin(freq * (i + 1) * 2.3 * x + ph[i, 0]) * np.cos(freq * (i + 1) * 1.9 * y + ph[i, 1])
        return z
    return ob, height

def grass_mesh(name, n, area, height_fn, hmin=0.18, hmax=0.5, width=0.016, lean=0.35, seed=2, center=(0, 0), density_fn=None, hscale_fn=None, return_tips=False):
    """n blades inside rectangle area=(w,d) around center. 7 verts/blade."""
    rng = np.random.default_rng(seed)
    px = rng.uniform(-area[0] / 2, area[0] / 2, n * 2); py = rng.uniform(-area[1] / 2, area[1] / 2, n * 2)
    if density_fn is not None:
        keep = rng.random(n * 2) < density_fn(px, py)
        px, py = px[keep][:n], py[keep][:n]
    n = len(px)
    px = px + center[0]; py = py + center[1]
    pz = height_fn(px, py)
    h = rng.uniform(hmin, hmax, n) * (0.7 + 0.6 * rng.random(n) ** 2)
    if hscale_fn is not None: h = h * hscale_fn(px, py)
    th = rng.uniform(0, math.tau, n); ph = rng.uniform(0, math.tau, n)
    ln = rng.uniform(0.05, lean, n)
    ts = np.array([0, 1 / 3, 2 / 3, 1.0])
    dx, dy = np.cos(ph), np.sin(ph)          # lean direction
    wx, wy = -np.sin(th), np.cos(th)         # width direction
    V = np.zeros((n, 7, 3), np.float32); SW = np.zeros((n, 7), np.float32); UV = np.zeros((n, 7, 2), np.float32)
    for i, t in enumerate(ts[:3]):
        w = width * (1 - 0.55 * t) * (0.7 + 0.6 * rng.random(n))
        bend = ln * h * t * t * 1.6
        cx = px + dx * bend; cy = py + dy * bend; cz = pz + h * t * (1 - 0.25 * ln * t)
        V[:, 2 * i, 0] = cx - wx * w; V[:, 2 * i, 1] = cy - wy * w; V[:, 2 * i, 2] = cz
        V[:, 2 * i + 1, 0] = cx + wx * w; V[:, 2 * i + 1, 1] = cy + wy * w; V[:, 2 * i + 1, 2] = cz
        SW[:, 2 * i] = SW[:, 2 * i + 1] = t; UV[:, 2 * i, 0] = 0; UV[:, 2 * i + 1, 0] = 1; UV[:, 2 * i, 1] = UV[:, 2 * i + 1, 1] = t
    t = 1.0; bend = ln * h * 1.6
    V[:, 6, 0] = px + dx * bend; V[:, 6, 1] = py + dy * bend; V[:, 6, 2] = pz + h * (1 - 0.25 * ln)
    SW[:, 6] = 1.0; UV[:, 6] = (0.5, 1.0)
    base = (np.arange(n) * 7)[:, None]
    faces = np.concatenate([base + np.array([0, 1, 3, 2]), base + np.array([2, 3, 5, 4])], 0)
    tris = base + np.array([4, 5, 6])
    flist = faces.tolist() + tris.tolist()
    col = np.zeros((n, 7, 4), np.float32); col[:, :, :3] = rng.random(n)[:, None, None]; col[:, :, 3] = 1
    me = mesh_from_arrays(name, V.reshape(-1, 3), flist, uv=UV.reshape(-1, 2), attrs={"sway": SW.ravel()}, colors={"Col": col.reshape(-1, 4)})
    return (me, V[:, 6, :].copy()) if return_tips else me

# ------------------------------------------------------------------ wind (geometry nodes)
def wind_group():
    if "WindSway" in bpy.data.node_groups: return bpy.data.node_groups["WindSway"]
    ng = bpy.data.node_groups.new("WindSway", 'GeometryNodeTree')
    ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    s1 = ng.interface.new_socket("Strength", in_out='INPUT', socket_type='NodeSocketFloat'); s1.default_value = 0.12
    s2 = ng.interface.new_socket("Speed", in_out='INPUT', socket_type='NodeSocketFloat'); s2.default_value = 1.6
    N = ng.nodes
    gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')
    pos = N.new('GeometryNodeInputPosition'); tm = N.new('GeometryNodeInputSceneTime')
    sway = N.new('GeometryNodeInputNamedAttribute'); sway.data_type = 'FLOAT'; sway.inputs['Name'].default_value = 'sway'
    sp = N.new('ShaderNodeSeparateXYZ'); ng.links.new(pos.outputs[0], sp.inputs[0])
    def M(op, a=None, b=None, c=None):
        n = N.new('ShaderNodeMath'); n.operation = op
        for i, v in enumerate((a, b, c)):
            if v is None: continue
            if isinstance(v, (int, float)): n.inputs[i].default_value = v
            else: ng.links.new(v, n.inputs[i])
        return n.outputs[0]
    t = M('MULTIPLY', tm.outputs['Seconds'], gi.outputs['Speed'])
    ph = M('ADD', M('MULTIPLY', sp.outputs['X'], 0.45), M('MULTIPLY', sp.outputs['Y'], 0.31))
    a1 = M('SINE', M('ADD', t, ph))
    a2 = M('SINE', M('ADD', M('MULTIPLY', t, 2.7), M('MULTIPLY', ph, 1.9)))
    wx = M('ADD', a1, M('MULTIPLY', a2, 0.35))
    wy = M('MULTIPLY', M('SINE', M('ADD', M('MULTIPLY', t, 1.3), M('MULTIPLY', ph, 0.7))), 0.6)
    k = M('MULTIPLY', M('MULTIPLY', sway.outputs[0], sway.outputs[0]), gi.outputs['Strength'])
    cx = N.new('ShaderNodeCombineXYZ')
    ng.links.new(M('MULTIPLY', wx, k), cx.inputs['X']); ng.links.new(M('MULTIPLY', wy, k), cx.inputs['Y'])
    setp = N.new('GeometryNodeSetPosition')
    ng.links.new(gi.outputs['Geometry'], setp.inputs['Geometry']); ng.links.new(cx.outputs[0], setp.inputs['Offset'])
    ng.links.new(setp.outputs[0], go.inputs['Geometry'])
    return ng

def add_wind(ob, strength=0.12, speed=1.6):
    ng = wind_group()
    md = ob.modifiers.new("Wind", 'NODES'); md.node_group = ng
    for it in ng.interface.items_tree:
        if getattr(it, 'in_out', '') == 'INPUT' and it.name == 'Strength': md[it.identifier] = strength
        if getattr(it, 'in_out', '') == 'INPUT' and it.name == 'Speed': md[it.identifier] = speed
    return md

# ------------------------------------------------------------------ world / render / camera
def sky(sc, elevation=10, rotation=40, strength=1.0, dust=1.0, sun_size=0.6, multi=True):
    w = bpy.data.worlds.new(sc.name + "_World"); w.use_nodes = True; nt = w.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_WORLD': nt.nodes.remove(n)
    out = [n for n in nt.nodes if n.type == 'OUTPUT_WORLD'][0]
    s = _n(nt, 'ShaderNodeTexSky', (-300, 0), sky_type='MULTIPLE_SCATTERING' if multi else 'SINGLE_SCATTERING')
    s.sun_elevation = math.radians(elevation); s.sun_rotation = math.radians(rotation)
    for attr in ('aerosol_density', 'dust_density'):
        if hasattr(s, attr): setattr(s, attr, dust)
    s.sun_size = math.radians(sun_size)
    bg = _n(nt, 'ShaderNodeBackground', (-50, 0)); bg.inputs['Strength'].default_value = strength
    nt.links.new(s.outputs[0], bg.inputs['Color']); nt.links.new(bg.outputs[0], out.inputs['Surface'])
    sc.world = w
    return w

def setup_render(sc, res=(1080, 1920), fps=30, samples=32, start=1, end=150, percent=100):
    r = sc.render
    r.engine = 'CYCLES'; r.resolution_x, r.resolution_y = res; r.resolution_percentage = percent
    r.fps = fps; sc.frame_start, sc.frame_end = start, end
    r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGB'; r.image_settings.compression = 15
    c = sc.cycles
    c.device = 'CPU'; c.samples = samples; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.03
    c.use_denoising = False
    c.use_animated_seed = True
    try: c.denoiser = 'OPENIMAGEDENOISE'
    except Exception as e: print("denoiser set failed", e)
    c.max_bounces = 6; c.diffuse_bounces = 2; c.glossy_bounces = 3; c.transmission_bounces = 4
    c.transparent_max_bounces = 6; c.volume_bounces = 0
    c.sample_clamp_indirect = 8.0; c.caustics_reflective = False; c.caustics_refractive = False
    c.use_light_tree = True
    sc.view_settings.view_transform = 'AgX'
    try: sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception: pass
    r.use_motion_blur = False
    r.film_transparent = False

def make_camera(sc, name, loc, target, lens=35, fstop=2.8, sensor=24):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = sensor
    cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop
    cam = link_obj(sc, name, cd)
    cam.location = loc
    tg = bpy.data.objects.new(name + "_Target", None); sc.collection.objects.link(tg); tg.location = target
    tg.empty_display_type = 'SPHERE'; tg.empty_display_size = 0.05
    c = cam.constraints.new('TRACK_TO'); c.target = tg; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    cd.dof.focus_object = tg
    sc.camera = cam
    return cam, tg

def key_path(ob, prop, keys, interp='BEZIER'):
    """keys: [(frame, value)] value is a Vector/tuple (for 'location') or float."""
    for f, v in keys:
        setattr(ob, prop, v); ob.keyframe_insert(prop, frame=f)
    ad = ob.animation_data
    if ad and ad.action:
        # Blender 5 layered actions: iterate through all fcurves we can reach
        try:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points: kp.interpolation = interp
        except Exception:
            try:
                for layer in ad.action.layers:
                    for strip in layer.strips:
                        for cb in strip.channelbags:
                            for fc in cb.fcurves:
                                for kp in fc.keyframe_points: kp.interpolation = interp
            except Exception as e:
                print("interp set skipped", e)


def fix_normals(me):
    import bmesh
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free(); me.update()
