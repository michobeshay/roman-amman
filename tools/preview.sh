#!/bin/bash
# usage: preview.sh "frames" spp pct
mkdir -p out
for i in 1 2 3; do
  curl -fL --retry 3 -o /tmp/bl.tar.xz https://download.blender.org/release/Blender5.0/blender-5.0.1-linux-x64.tar.xz && break
  echo "download attempt $i failed"; sleep 5
done
ls -la /tmp/bl.tar.xz
mkdir -p /tmp/bl && tar -xf /tmp/bl.tar.xz -C /tmp/bl --strip-components=1 && ls /tmp/bl | head -3
/tmp/bl/blender -b -P blender/render_amman.py -- --frames "$1" --spp $2 --pct $3 --out out > out/log.txt 2>&1
grep -E "RS |Error|Traceback|File \"|rror:|Exception" out/log.txt | head -60
