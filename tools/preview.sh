#!/bin/bash
# usage: preview.sh "frames" spp pct tag
mkdir -p out; wget -q https://download.blender.org/release/Blender5.0/blender-5.0.1-linux-x64.tar.xz -O /tmp/bl.tar.xz && mkdir -p /tmp/bl && tar -xf /tmp/bl.tar.xz -C /tmp/bl --strip-components=1
/tmp/bl/blender -b -P blender/render_amman.py -- --frames "$1" --spp $2 --pct $3 --out out 2>&1 | tee out/log.txt | grep -E "RS |Error|Traceback|File \"|rror:|Exception" | head -60
