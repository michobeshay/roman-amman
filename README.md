# عمّان عبر الزمن — Amman Through Time
Blender/Cycles reconstruction of the Roman Theatre of Philadelphia (Amman), c. 138–161 CE → 2026. 3150 frames, 1080×1920, 30 fps.

- `blender/` procedural scene (numpy geometry + Geometry Nodes), `render_amman.py` driver
- `post/` Arabic (Jordanian) titles, labels, timeline, subtitles (`script_ar.py` holds all text), audio + TTS (`ar-JO-TaimNeural` via edge-tts)
- `amman_colab.ipynb` final GPU render on Colab, resume-safe via Google Drive
- `tools/preview.sh` + Actions workflow: cheap CPU previews only

## Evidence vs reconstruction
Confirmed: Roman theatre in Philadelphia, built under Antoninus Pius (c. 138–161 CE), cut into the hillside, ~6,000 seats (commonly cited), Hercules niche above the cavea, Hellenistic/Roman Philadelphia on the Citadel hill area.
Reconstructed / artistic: stage-building (scaenae frons) façade and its decoration, row counts, tier proportions, vegetation, crowd, costumes, medieval-to-modern building history, exact camera/plaza layout.
Sources to cite on release: Jordan Dept. of Antiquities; Amman Municipality; Dept. of Antiquities/ACOR publications on Philadelphia; Encyclopaedia Britannica "Amman"; UNESCO tentative list entries. Verify figures before publishing.
