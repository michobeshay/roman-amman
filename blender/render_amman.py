import bpy, sys, os, time, argparse
sys.path.insert(0, os.path.join(os.getcwd(), "blender"))
import lib, amman_shots as S
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser(); ap.add_argument("--frames", default=""); ap.add_argument("--range", default=""); ap.add_argument("--spp", type=int, default=0)
ap.add_argument("--pct", type=int, default=100); ap.add_argument("--out", default="out"); ap.add_argument("--save", default=""); ap.add_argument("--labels", default="")
a = ap.parse_args(argv)
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene; sc.name = "Amman"; t0 = time.time()
W, cams, A = S.build_film(sc)
if a.spp: sc.cycles.samples = a.spp
sc.render.resolution_percentage = a.pct
print("RS build seconds", round(time.time() - t0, 1), "objects", len(sc.objects), "seats", W['crowd'].get('seats'))
if os.environ.get('BEE_GPU') == '1':
    prefs = bpy.context.preferences.addons['cycles'].preferences; ok = False
    for t in ('OPTIX', 'CUDA', 'HIP', 'METAL', 'ONEAPI'):
        try:
            prefs.compute_device_type = t
            try: prefs.refresh_devices()
            except Exception: prefs.get_devices()
            devs = [d for d in prefs.devices if d.type == t]
            if devs:
                for d in prefs.devices: d.use = (d.type == t)
                sc.cycles.device = 'GPU'; ok = True; print("RS gpu", t, [d.name for d in devs]); break
        except Exception as e: print("RS gpu try", t, e)
    if not ok: print("RS WARNING no GPU found, using CPU")
if a.save: bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.save), compress=True)
os.makedirs(a.out, exist_ok=True)
if a.labels:
    lf = list(range(241, 1291, 2)); S.dump_labels(sc, A, a.labels, lf)
if a.frames:
    for f in [int(x) for x in a.frames.split(",")]:
        sc.frame_set(f); sc.render.filepath = os.path.abspath(f"{a.out}/F_{f:04d}.png")
        t = time.time(); bpy.ops.render.render(write_still=True); print("RS frame", f, "seconds", round(time.time() - t, 1))
elif a.range:
    s, e = [int(x) for x in a.range.split("-")]; sc.frame_start, sc.frame_end = s, e
    sc.render.use_overwrite = False; sc.render.use_placeholder = True; sc.render.filepath = os.path.abspath(f"{a.out}/F_")
    t = time.time(); bpy.ops.render.render(animation=True); print("RS range seconds", round(time.time() - t, 1))
