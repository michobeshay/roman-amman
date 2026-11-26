"""Materials. Every stone-like material carries Weather (0 fresh .. 1 ruined) and tier-highlight values that shots can keyframe."""
import bpy, math
import lib
from lib import _n, new_mat, ramp

WEATHER_NODES = []     # (material, node) so a shot can keyframe weathering everywhere at once
HILITE_NODES = []

def _val(nt, name, v, loc=(-1400, 0)):
    n = _n(nt, 'ShaderNodeValue', loc); n.name = name; n.label = name; n.outputs[0].default_value = v; return n

def _stone(name, light, dark, moss=True, scale=1.0, brick=(0.9, 0.42), rough=0.88, tier_highlight=False, theta_stairs=False):
    m, nt, out = new_mat(name); tc = _n(nt, 'ShaderNodeTexCoord', (-1500, 0))
    W = _val(nt, 'Weather', 0.0, (-1500, 350)); WEATHER_NODES.append((m, W))
    mp = _n(nt, 'ShaderNodeMapping', (-1300, 0)); mp.inputs['Scale'].default_value = (scale, scale, scale); nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    br = _n(nt, 'ShaderNodeTexBrick', (-1050, 100)); br.inputs['Scale'].default_value = 1.0; br.inputs['Mortar Size'].default_value = 0.012; br.inputs['Brick Width'].default_value = brick[0]; br.inputs['Row Height'].default_value = brick[1]
    br.inputs['Color1'].default_value = light; br.inputs['Color2'].default_value = dark; br.inputs['Mortar'].default_value = (0.07, 0.055, 0.04, 1); br.inputs['Bias'].default_value = 0.0
    nt.links.new(mp.outputs[0], br.inputs['Vector'])
    n1 = _n(nt, 'ShaderNodeTexNoise', (-1050, -200), noise_dimensions='3D'); n1.inputs['Scale'].default_value = 1.8 / scale; n1.inputs['Detail'].default_value = 8; nt.links.new(tc.outputs['Object'], n1.inputs['Vector'])
    n2 = _n(nt, 'ShaderNodeTexNoise', (-1050, -450), noise_dimensions='3D'); n2.inputs['Scale'].default_value = 40; n2.inputs['Detail'].default_value = 6; nt.links.new(tc.outputs['Object'], n2.inputs['Vector'])
    # weathering: darken + desaturate + grime in crevices + moss patches
    dk = _n(nt, 'ShaderNodeMix', (-760, 100), data_type='RGBA'); dk.inputs[7].default_value = (0.09, 0.075, 0.06, 1)
    f1 = _n(nt, 'ShaderNodeMath', (-900, 300), operation='MULTIPLY'); nt.links.new(W.outputs[0], f1.inputs[0]); f1.inputs[1].default_value = 0.55
    f2 = _n(nt, 'ShaderNodeMath', (-900, 440), operation='MULTIPLY'); nt.links.new(n1.outputs['Fac'], f2.inputs[0]); nt.links.new(W.outputs[0], f2.inputs[1])
    f3 = _n(nt, 'ShaderNodeMath', (-760, 300), operation='ADD'); nt.links.new(f1.outputs[0], f3.inputs[0]); nt.links.new(f2.outputs[0], f3.inputs[1]); f3.use_clamp = True
    nt.links.new(f3.outputs[0], dk.inputs[0]); nt.links.new(br.outputs['Color'], dk.inputs[6])
    last = dk
    if moss:
        mo = _n(nt, 'ShaderNodeMix', (-560, 100), data_type='RGBA'); mo.inputs[7].default_value = (0.06, 0.13, 0.025, 1)
        th = _n(nt, 'ShaderNodeMath', (-760, -150), operation='SUBTRACT'); nt.links.new(n1.outputs['Fac'], th.inputs[0]); nt.links.new(W.outputs[0], th.inputs[1])
        th2 = _n(nt, 'ShaderNodeMath', (-620, -150), operation='MULTIPLY'); nt.links.new(th.outputs[0], th2.inputs[0]); th2.inputs[1].default_value = -9; th2.use_clamp = True
        mf = _n(nt, 'ShaderNodeMath', (-460, -150), operation='MULTIPLY'); nt.links.new(th2.outputs[0], mf.inputs[0]); nt.links.new(n2.outputs['Fac'], mf.inputs[1]); mf.use_clamp = True
        mg = _n(nt, 'ShaderNodeMath', (-300, -150), operation='MULTIPLY'); nt.links.new(mf.outputs[0], mg.inputs[0]); mg.inputs[1].default_value = 2.2; mg.use_clamp = True
        nt.links.new(mg.outputs[0], mo.inputs[0]); nt.links.new(dk.outputs[2], mo.inputs[6]); last = mo
    bp = _n(nt, 'ShaderNodeBump', (-300, -380)); bp.inputs['Strength'].default_value = 0.6; nt.links.new(br.outputs['Fac'], bp.inputs['Height'])
    bp2 = _n(nt, 'ShaderNodeBump', (-120, -380)); bp2.inputs['Strength'].default_value = 0.35; nt.links.new(n2.outputs['Fac'], bp2.inputs['Height']); nt.links.new(bp.outputs[0], bp2.inputs['Normal'])
    base = last.outputs[2]
    if theta_stairs:    # radial stair strips: slightly lighter, worn centre line
        at = _n(nt, 'ShaderNodeAttribute', (-1300, -500), attribute_name='theta', attribute_type='GEOMETRY')
        at2 = _n(nt, 'ShaderNodeAttribute', (-1300, -650), attribute_name='tier', attribute_type='GEOMETRY')
        nst = _n(nt, 'ShaderNodeMath', (-1100, -520), operation='MULTIPLY'); nt.links.new(at2.outputs['Fac'], nst.inputs[0]); nst.inputs[1].default_value = 0.4
        nsc = _n(nt, 'ShaderNodeMath', (-1000, -520), operation='ADD'); nt.links.new(nst.outputs[0], nsc.inputs[0]); nsc.inputs[1].default_value = 2.6
        mul = _n(nt, 'ShaderNodeMath', (-900, -520), operation='MULTIPLY'); nt.links.new(at.outputs['Fac'], mul.inputs[0]); nt.links.new(nsc.outputs[0], mul.inputs[1])
        fr = _n(nt, 'ShaderNodeMath', (-800, -520), operation='FRACT'); nt.links.new(mul.outputs[0], fr.inputs[0])
        ab = _n(nt, 'ShaderNodeMath', (-700, -520), operation='SUBTRACT'); nt.links.new(fr.outputs[0], ab.inputs[0]); ab.inputs[1].default_value = 0.5
        ab2 = _n(nt, 'ShaderNodeMath', (-600, -520), operation='ABSOLUTE'); nt.links.new(ab.outputs[0], ab2.inputs[0])
        lt = _n(nt, 'ShaderNodeMath', (-500, -520), operation='LESS_THAN'); nt.links.new(ab2.outputs[0], lt.inputs[0]); lt.inputs[1].default_value = 0.07
        sm = _n(nt, 'ShaderNodeMix', (-120, -150), data_type='RGBA'); sm.inputs[7].default_value = (0.78, 0.68, 0.52, 1); nt.links.new(lt.outputs[0], sm.inputs[0]); sm.inputs[0].default_value = 0.0
        nt.links.new(lt.outputs[0], sm.inputs[0]); nt.links.new(base, sm.inputs[6]); base = sm.outputs[2]
    pb = _n(nt, 'ShaderNodeBsdfPrincipled', (200, 0)); pb.inputs['Roughness'].default_value = rough; pb.inputs['Specular IOR Level'].default_value = 0.25
    nt.links.new(base, pb.inputs['Base Color']); nt.links.new(bp2.outputs[0], pb.inputs['Normal'])
    surf = pb.outputs[0]
    if tier_highlight:
        at = _n(nt, 'ShaderNodeAttribute', (-300, -700), attribute_name='tier', attribute_type='GEOMETRY')
        idx = _val(nt, 'HiIndex', -1.0, (-300, -850)); lev = _val(nt, 'HiLevel', 0.0, (-300, -950)); HILITE_NODES.append((m, idx, lev))
        d = _n(nt, 'ShaderNodeMath', (-100, -750), operation='SUBTRACT'); nt.links.new(at.outputs['Fac'], d.inputs[0]); nt.links.new(idx.outputs[0], d.inputs[1])
        a = _n(nt, 'ShaderNodeMath', (60, -750), operation='ABSOLUTE'); nt.links.new(d.outputs[0], a.inputs[0])
        l = _n(nt, 'ShaderNodeMath', (200, -750), operation='LESS_THAN'); nt.links.new(a.outputs[0], l.inputs[0]); l.inputs[1].default_value = 0.5
        e = _n(nt, 'ShaderNodeMath', (340, -750), operation='MULTIPLY'); nt.links.new(l.outputs[0], e.inputs[0]); nt.links.new(lev.outputs[0], e.inputs[1])
        em = _n(nt, 'ShaderNodeEmission', (480, -700)); em.inputs['Color'].default_value = (1.0, 0.62, 0.16, 1); nt.links.new(e.outputs[0], em.inputs['Strength'])
        ad = _n(nt, 'ShaderNodeAddShader', (640, -300)); nt.links.new(surf, ad.inputs[0]); nt.links.new(em.outputs[0], ad.inputs[1]); surf = ad.outputs[0]
    nt.links.new(surf, out.inputs['Surface']); return m

_cache = {}
def get(name):
    if name in _cache: return _cache[name]
    if name == 'cavea': m = _stone("Cavea_Sandstone", (0.42, 0.29, 0.16, 1), (0.36, 0.25, 0.14, 1), True, 1.0, (0.95, 0.40), tier_highlight=True, theta_stairs=True)
    elif name == 'wall': m = _stone("Wall_Limestone", (0.46, 0.34, 0.2, 1), (0.39, 0.29, 0.17, 1), True, 1.0, (1.1, 0.5))
    elif name == 'marble': m = _stone("Column_Limestone", (0.66, 0.56, 0.42, 1), (0.58, 0.49, 0.37, 1), True, 3.0, (2.5, 2.5), rough=0.6)
    elif name == 'floor': m = _stone("Orchestra_Paving", (0.58, 0.48, 0.34, 1), (0.46, 0.38, 0.27, 1), True, 1.3, (0.9, 0.9))
    elif name == 'plaster': m = _plaster("Stucco_Ochre")
    elif name == 'wood': m = _wood()
    elif name == 'dark': m = _flat("Door_Bronze", (0.025, 0.02, 0.016, 1), 0.4, 0.8)
    elif name == 'modern': m = _modern()
    elif name == 'house': m = _stone("House_Stone", (0.46, 0.36, 0.24, 1), (0.41, 0.32, 0.21, 1), False, 0.6, (0.7, 0.35), rough=0.92)
    elif name == 'terrain': m = _terrain()
    elif name == 'people': m = _people()
    elif name == 'visitors': m = _people("Visitors")
    elif name == 'tree': m = _tree()
    elif name == 'weed': m = _weed()
    elif name == 'roof': m = _flat("Roof_Concrete", (0.32, 0.31, 0.29, 1), 0.9)
    elif name == 'metal': m = _flat("Tank_Metal", (0.8, 0.8, 0.78, 1), 0.35, 0.6)
    else: raise KeyError(name)
    _cache[name] = m; return m

def _flat(name, col, rough=0.8, metal=0.0):
    m, nt, out = new_mat(name); pb = _n(nt, 'ShaderNodeBsdfPrincipled'); pb.inputs['Base Color'].default_value = col; pb.inputs['Roughness'].default_value = rough; pb.inputs['Metallic'].default_value = metal
    nt.links.new(pb.outputs[0], out.inputs['Surface']); return m

def _plaster(name):
    m, nt, out = new_mat(name); tc = _n(nt, 'ShaderNodeTexCoord'); n1 = _n(nt, 'ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = 8; n1.inputs['Detail'].default_value = 8; nt.links.new(tc.outputs['Object'], n1.inputs['Vector'])
    r = ramp(nt, [(0.3, (0.30, 0.075, 0.045, 1)), (0.7, (0.42, 0.12, 0.07, 1))]); nt.links.new(n1.outputs['Fac'], r.inputs[0])
    W = _val(nt, 'Weather', 0.0); WEATHER_NODES.append((m, W))
    mx = _n(nt, 'ShaderNodeMix', data_type='RGBA'); mx.inputs[7].default_value = (0.12, 0.09, 0.07, 1); nt.links.new(W.outputs[0], mx.inputs[0]); nt.links.new(r.outputs[0], mx.inputs[6])
    bp = _n(nt, 'ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.2; nt.links.new(n1.outputs['Fac'], bp.inputs['Height'])
    pb = _n(nt, 'ShaderNodeBsdfPrincipled'); pb.inputs['Roughness'].default_value = 0.85; nt.links.new(mx.outputs[2], pb.inputs['Base Color']); nt.links.new(bp.outputs[0], pb.inputs['Normal']); nt.links.new(pb.outputs[0], out.inputs['Surface']); return m

def _wood():
    m, nt, out = new_mat("Stage_Wood"); tc = _n(nt, 'ShaderNodeTexCoord'); mp = _n(nt, 'ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.0, 4.0, 1.0); nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    wv = _n(nt, 'ShaderNodeTexWave', wave_type='BANDS', bands_direction='X'); wv.inputs['Scale'].default_value = 3.0; wv.inputs['Distortion'].default_value = 1.2; wv.inputs['Detail'].default_value = 4; nt.links.new(mp.outputs[0], wv.inputs['Vector'])
    r = ramp(nt, [(0.2, (0.12, 0.065, 0.03, 1)), (0.8, (0.26, 0.15, 0.07, 1))]); nt.links.new(wv.outputs[0], r.inputs[0])
    bp = _n(nt, 'ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.3; nt.links.new(wv.outputs[0], bp.inputs['Height'])
    pb = _n(nt, 'ShaderNodeBsdfPrincipled'); pb.inputs['Roughness'].default_value = 0.65; nt.links.new(r.outputs[0], pb.inputs['Base Color']); nt.links.new(bp.outputs[0], pb.inputs['Normal']); nt.links.new(pb.outputs[0], out.inputs['Surface']); return m

def _modern():
    m, nt, out = new_mat("Modern_Facade"); uv = _n(nt, 'ShaderNodeTexCoord', (-1200, 0)); sep = _n(nt, 'ShaderNodeSeparateXYZ', (-1000, 0)); nt.links.new(uv.outputs['UV'], sep.inputs[0])
    def fr(src, loc):
        f = _n(nt, 'ShaderNodeMath', loc, operation='FRACT'); nt.links.new(src, f.inputs[0]); return f.outputs[0]
    fu = fr(sep.outputs['X'], (-800, 100)); fv = fr(sep.outputs['Y'], (-800, -100))
    def rng(v, a, b, loc):
        g = _n(nt, 'ShaderNodeMath', loc, operation='GREATER_THAN'); nt.links.new(v, g.inputs[0]); g.inputs[1].default_value = a
        l = _n(nt, 'ShaderNodeMath', (loc[0] + 140, loc[1]), operation='LESS_THAN'); nt.links.new(v, l.inputs[0]); l.inputs[1].default_value = b
        mu = _n(nt, 'ShaderNodeMath', (loc[0] + 280, loc[1]), operation='MULTIPLY'); nt.links.new(g.outputs[0], mu.inputs[0]); nt.links.new(l.outputs[0], mu.inputs[1]); return mu.outputs[0]
    wu = rng(fu, 0.2, 0.62, (-700, 100)); wv = rng(fv, 0.2, 0.78, (-700, -100))
    win = _n(nt, 'ShaderNodeMath', (-300, 0), operation='MULTIPLY'); nt.links.new(wu, win.inputs[0]); nt.links.new(wv, win.inputs[1])
    roof = _n(nt, 'ShaderNodeAttribute', (-1000, -300), attribute_name='isroof', attribute_type='GEOMETRY')
    nowin = _n(nt, 'ShaderNodeMath', (-120, 0), operation='MULTIPLY'); nt.links.new(win.outputs[0], nowin.inputs[0])
    inv = _n(nt, 'ShaderNodeMath', (-300, -300), operation='SUBTRACT'); inv.inputs[0].default_value = 1.0; nt.links.new(roof.outputs['Fac'], inv.inputs[1]); nt.links.new(inv.outputs[0], nowin.inputs[1])
    col = _n(nt, 'ShaderNodeAttribute', (-700, 300), attribute_name='Col', attribute_type='GEOMETRY')
    nz = _n(nt, 'ShaderNodeTexNoise', (-900, 400)); nz.inputs['Scale'].default_value = 0.7; nz.inputs['Detail'].default_value = 4; uvn = _n(nt, 'ShaderNodeTexCoord', (-1100, 400)); nt.links.new(uvn.outputs['Object'], nz.inputs['Vector'])
    wallv = _n(nt, 'ShaderNodeMix', (-450, 300), data_type='RGBA'); wallv.inputs[0].default_value = 0.18; wallv.inputs[7].default_value = (0.2, 0.17, 0.12, 1); nt.links.new(col.outputs['Color'], wallv.inputs[6]); nt.links.new(nz.outputs['Fac'], wallv.inputs[0])
    rc = _n(nt, 'ShaderNodeMix', (-250, 300), data_type='RGBA'); rc.inputs[7].default_value = (0.3, 0.29, 0.27, 1); nt.links.new(roof.outputs['Fac'], rc.inputs[0]); nt.links.new(wallv.outputs[2], rc.inputs[6])
    glass = _n(nt, 'ShaderNodeMix', (0, 200), data_type='RGBA'); glass.inputs[7].default_value = (0.012, 0.018, 0.026, 1); nt.links.new(nowin.outputs[0], glass.inputs[0]); nt.links.new(rc.outputs[2], glass.inputs[6])
    rg = _n(nt, 'ShaderNodeMath', (0, -100), operation='MULTIPLY'); nt.links.new(nowin.outputs[0], rg.inputs[0]); rg.inputs[1].default_value = -0.7
    rr = _n(nt, 'ShaderNodeMath', (140, -100), operation='ADD'); rr.inputs[0].default_value = 0.9; nt.links.new(rg.outputs[0], rr.inputs[1])
    pb = _n(nt, 'ShaderNodeBsdfPrincipled', (300, 100)); nt.links.new(glass.outputs[2], pb.inputs['Base Color']); nt.links.new(rr.outputs[0], pb.inputs['Roughness'])
    nt.links.new(pb.outputs[0], out.inputs['Surface']); return m

def _terrain():
    m, nt, out = new_mat("Terrain"); tc = _n(nt, 'ShaderNodeTexCoord', (-1400, 0))
    n1 = _n(nt, 'ShaderNodeTexNoise', (-1150, 300), noise_dimensions='3D'); n1.inputs['Scale'].default_value = 0.035; n1.inputs['Detail'].default_value = 7; nt.links.new(tc.outputs['Object'], n1.inputs['Vector'])
    n2 = _n(nt, 'ShaderNodeTexNoise', (-1150, 0), noise_dimensions='3D'); n2.inputs['Scale'].default_value = 1.6; n2.inputs['Detail'].default_value = 8; nt.links.new(tc.outputs['Object'], n2.inputs['Vector'])
    earth = ramp(nt, [(0.35, (0.2, 0.135, 0.07, 1)), (0.65, (0.31, 0.22, 0.12, 1))], (-900, 300)); nt.links.new(n1.outputs['Fac'], earth.inputs[0])
    scrub = _n(nt, 'ShaderNodeMix', (-650, 300), data_type='RGBA'); scrub.inputs[7].default_value = (0.17, 0.15, 0.065, 1); nt.links.new(n2.outputs['Fac'], scrub.inputs[0]); nt.links.new(earth.outputs[0], scrub.inputs[6])
    pl = _n(nt, 'ShaderNodeAttribute', (-1150, -300), attribute_name='plaza', attribute_type='GEOMETRY'); rd = _n(nt, 'ShaderNodeAttribute', (-1150, -450), attribute_name='road', attribute_type='GEOMETRY')
    mo = _val(nt, 'Modern', 0.0, (-1150, -600))
    slab = _n(nt, 'ShaderNodeTexBrick', (-900, -300)); slab.inputs['Scale'].default_value = 0.25; slab.inputs['Mortar Size'].default_value = 0.012; slab.inputs['Color1'].default_value = (0.24, 0.19, 0.13, 1); slab.inputs['Color2'].default_value = (0.21, 0.17, 0.115, 1); slab.inputs['Mortar'].default_value = (0.2, 0.17, 0.13, 1)
    nt.links.new(tc.outputs['Object'], slab.inputs['Vector'])
    p1 = _n(nt, 'ShaderNodeMix', (-450, 100), data_type='RGBA'); nt.links.new(pl.outputs['Fac'], p1.inputs[0]); nt.links.new(scrub.outputs[2], p1.inputs[6]); nt.links.new(slab.outputs['Color'], p1.inputs[7])
    rm = _n(nt, 'ShaderNodeMath', (-700, -500), operation='MULTIPLY'); nt.links.new(rd.outputs['Fac'], rm.inputs[0]); nt.links.new(mo.outputs[0], rm.inputs[1])
    p2 = _n(nt, 'ShaderNodeMix', (-250, 100), data_type='RGBA'); p2.inputs[7].default_value = (0.045, 0.045, 0.05, 1); nt.links.new(rm.outputs[0], p2.inputs[0]); nt.links.new(p1.outputs[2], p2.inputs[6])
    bp = _n(nt, 'ShaderNodeBump', (-250, -200)); bp.inputs['Strength'].default_value = 0.5; nt.links.new(n2.outputs['Fac'], bp.inputs['Height'])
    pb = _n(nt, 'ShaderNodeBsdfPrincipled', (0, 0)); pb.inputs['Roughness'].default_value = 0.92; nt.links.new(p2.outputs[2], pb.inputs['Base Color']); nt.links.new(bp.outputs[0], pb.inputs['Normal'])
    nt.links.new(pb.outputs[0], out.inputs['Surface']); m['modern_node'] = mo.name; return m

def _people(name="People"):
    m, nt, out = new_mat(name); col = _n(nt, 'ShaderNodeAttribute', (-600, 0), attribute_name='Col', attribute_type='GEOMETRY')
    pb = _n(nt, 'ShaderNodeBsdfPrincipled', (-200, 100)); pb.inputs['Roughness'].default_value = 0.75; pb.inputs['Sheen Weight'].default_value = 0.2
    nt.links.new(col.outputs['Color'], pb.inputs['Base Color']); nt.links.new(pb.outputs[0], out.inputs['Surface']); return m

def _tree():
    m, nt, out = new_mat("Foliage"); col = _n(nt, 'ShaderNodeAttribute', (-600, 0), attribute_name='Col', attribute_type='GEOMETRY'); tc = _n(nt, 'ShaderNodeTexCoord', (-900, 200))
    n1 = _n(nt, 'ShaderNodeTexNoise', (-700, 200)); n1.inputs['Scale'].default_value = 5; n1.inputs['Detail'].default_value = 6; nt.links.new(tc.outputs['Object'], n1.inputs['Vector'])
    mx = _n(nt, 'ShaderNodeMix', (-400, 100), data_type='RGBA'); mx.inputs[7].default_value = (0.02, 0.05, 0.015, 1); mx.inputs[0].default_value = 0.35; nt.links.new(col.outputs['Color'], mx.inputs[6]); nt.links.new(n1.outputs['Fac'], mx.inputs[0])
    pb = _n(nt, 'ShaderNodeBsdfPrincipled', (-150, 100)); pb.inputs['Roughness'].default_value = 0.6; nt.links.new(mx.outputs[2], pb.inputs['Base Color'])
    tr = _n(nt, 'ShaderNodeBsdfTranslucent', (-150, -100)); nt.links.new(mx.outputs[2], tr.inputs['Color'])
    ms = _n(nt, 'ShaderNodeMixShader', (100, 0)); ms.inputs[0].default_value = 0.25; nt.links.new(pb.outputs[0], ms.inputs[1]); nt.links.new(tr.outputs[0], ms.inputs[2]); nt.links.new(ms.outputs[0], out.inputs['Surface']); return m

def _weed():
    m, nt, out = new_mat("Weeds"); pb = _n(nt, 'ShaderNodeBsdfPrincipled'); col = _n(nt, 'ShaderNodeAttribute', attribute_name='Col', attribute_type='GEOMETRY'); nt.links.new(col.outputs['Color'], pb.inputs['Base Color']); pb.inputs['Roughness'].default_value = 0.7
    nt.links.new(pb.outputs[0], out.inputs['Surface']); return m
