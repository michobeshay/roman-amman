import bpy
def _group(name):
    if name in bpy.data.node_groups: return bpy.data.node_groups[name], False
    ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
    ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry'); ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    return ng, True

def _M(ng, op, a=None, b=None, clamp=False):
    n = ng.nodes.new('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None: continue
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: ng.links.new(v, n.inputs[i])
    return n.outputs[0]

def grow_group():
    ng, new = _group("GrowIn")
    if not new: return ng
    t = ng.interface.new_socket("T", in_out='INPUT', socket_type='NodeSocketFloat'); t.default_value = 1.0
    N = ng.nodes; gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')
    pos = N.new('GeometryNodeInputPosition'); sp = N.new('ShaderNodeSeparateXYZ'); ng.links.new(pos.outputs[0], sp.inputs[0])
    rev = N.new('GeometryNodeInputNamedAttribute'); rev.data_type = 'FLOAT'; rev.inputs['Name'].default_value = 'rev'
    bz = N.new('GeometryNodeInputNamedAttribute'); bz.data_type = 'FLOAT'; bz.inputs['Name'].default_value = 'bz'
    s = _M(ng, 'MULTIPLY', _M(ng, 'SUBTRACT', gi.outputs['T'], rev.outputs[0]), 14.0, clamp=True)
    one_minus = _M(ng, 'SUBTRACT', 1.0, s)
    dz = _M(ng, 'MULTIPLY', one_minus, _M(ng, 'SUBTRACT', _M(ng, 'SUBTRACT', bz.outputs[0], sp.outputs['Z']), 40.0))
    cx = N.new('ShaderNodeCombineXYZ'); ng.links.new(dz, cx.inputs['Z'])
    st = N.new('GeometryNodeSetPosition'); ng.links.new(gi.outputs['Geometry'], st.inputs['Geometry']); ng.links.new(cx.outputs[0], st.inputs['Offset']); ng.links.new(st.outputs[0], go.inputs['Geometry'])
    return ng

def drift_group():
    ng, new = _group("Drift")
    if not new: return ng
    t = ng.interface.new_socket("T0", in_out='INPUT', socket_type='NodeSocketFloat'); t.default_value = 80.0
    N = ng.nodes; gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput'); tm = N.new('GeometryNodeInputSceneTime')
    vel = N.new('GeometryNodeInputNamedAttribute'); vel.data_type = 'FLOAT_VECTOR'; vel.inputs['Name'].default_value = 'vel'
    ph = N.new('GeometryNodeInputNamedAttribute'); ph.data_type = 'FLOAT'; ph.inputs['Name'].default_value = 'ph'
    dt = _M(ng, 'SUBTRACT', tm.outputs['Seconds'], gi.outputs['T0'])
    vs = N.new('ShaderNodeVectorMath'); vs.operation = 'SCALE'; ng.links.new(vel.outputs[0], vs.inputs[0]); ng.links.new(dt, vs.inputs['Scale'])
    bob = _M(ng, 'MULTIPLY', _M(ng, 'ABSOLUTE', _M(ng, 'SINE', _M(ng, 'ADD', _M(ng, 'MULTIPLY', tm.outputs['Seconds'], 7.0), ph.outputs[0]))), 0.045)
    sx = N.new('ShaderNodeSeparateXYZ'); ng.links.new(vs.outputs[0], sx.inputs[0]); cx = N.new('ShaderNodeCombineXYZ')
    ng.links.new(sx.outputs['X'], cx.inputs['X']); ng.links.new(sx.outputs['Y'], cx.inputs['Y']); ng.links.new(bob, cx.inputs['Z'])
    st = N.new('GeometryNodeSetPosition'); ng.links.new(gi.outputs['Geometry'], st.inputs['Geometry']); ng.links.new(cx.outputs[0], st.inputs['Offset']); ng.links.new(st.outputs[0], go.inputs['Geometry'])
    return ng

def add_mod(ob, group, name, **vals):
    md = ob.modifiers.new(name, 'NODES'); md.node_group = group
    ids = {}
    for it in group.interface.items_tree:
        if getattr(it, 'in_out', '') == 'INPUT' and it.name in vals: md[it.identifier] = vals[it.name]; ids[it.name] = it.identifier
    ob['_gn_' + name] = ids
    return md

def key_mod(ob, name, socket, keys):
    """keys [(frame, value)] -> keyframes on modifier input"""
    ident = ob['_gn_' + name][socket]
    for f, v in keys:
        ob.modifiers[name][ident] = v
        ob.keyframe_insert(data_path=f'modifiers["{name}"]["{ident}"]', frame=f)
