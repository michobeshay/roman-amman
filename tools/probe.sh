#!/bin/bash
mkdir -p out; exec > >(tee out/probe.txt) 2>&1
echo "PROBE nproc $(nproc)"; echo "PROBE mem $(free -g | awk '/Mem/{print $2" GB"}')"; echo "PROBE disk $(df -h / | awk 'NR==2{print $4" free of "$2}')"
echo "PROBE gpu: $(nvidia-smi -L 2>&1 | head -1)"; echo "PROBE pci: $(lspci 2>/dev/null | grep -iE 'vga|3d|nvidia' | head -2)"
echo "PROBE cpu: $(lscpu | grep 'Model name' | sed 's/.*: *//')"
cd /tmp; t=$(date +%s)
wget -q https://download.blender.org/release/Blender5.0/blender-5.0.1-linux-x64.tar.xz && echo "PROBE blender_download ok $(( $(date +%s)-t ))s size $(du -h blender-5.0.1-linux-x64.tar.xz | cut -f1)" || echo "PROBE blender_download FAILED"
mkdir -p bl && tar -xf blender-5.0.1-linux-x64.tar.xz -C bl --strip-components=1 && bl/blender --version | head -2
cat > p.py <<'PY'
import bpy
c = bpy.context.scene.cycles
print("PROBE denoisers", [i.identifier for i in c.bl_rna.properties['denoiser'].enum_items])
print("PROBE engines", [i.identifier for i in bpy.context.scene.render.bl_rna.properties['engine'].enum_items])
p = bpy.context.preferences.addons['cycles'].preferences
for t in ('OPTIX','CUDA'):
    try:
        p.compute_device_type = t; p.refresh_devices(); print("PROBE devices", t, [d.name for d in p.devices if d.type == t])
    except Exception as e: print("PROBE dev err", t, e)
print("PROBE denoise_ok", hasattr(c, 'use_denoising'))
PY
bl/blender -b -P p.py 2>&1 | grep PROBE
echo "PROBE colab_reach $(curl -s -o /dev/null -w '%{http_code}' -m 10 https://colab.research.google.com)"
