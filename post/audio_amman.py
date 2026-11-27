"""Audio: synthesized ambience/music/footsteps/crowd + narration (edge-tts ar-JO-TaimNeural if available) -> wav. usage: audio_amman.py OUT.wav [workdir]"""
import sys, os, asyncio, subprocess, numpy as np
from scipy.io import wavfile
from scipy.signal import butter, lfilter
sys.path.insert(0, os.path.dirname(__file__)); from script_ar import VO
SR = 44100; DUR = 105; n = SR * DUR; t = np.arange(n) / SR; rng = np.random.default_rng(3)
def bp(x, lo, hi): b, a = butter(2, [lo / (SR / 2), hi / (SR / 2)], 'band'); return lfilter(b, a, x)
def env(a, b, lo, hi): return np.interp(t, [0, a, b, DUR], [lo, lo, hi, hi])
wind = bp(rng.normal(0, 1, n), 120, 900) * (.5 + .5 * np.sin(2 * np.pi * t / 9)) * .12
murmur = bp(rng.normal(0, 1, n), 200, 1800) * np.interp(t, [0, 25, 30, 40, 43, 65, 90, 105], [0, 0, .05, .16, .02, .04, .09, .03]) * (.7 + .3 * np.sin(2 * np.pi * t * 3.1))
traffic = bp(rng.normal(0, 1, n), 60, 500) * np.interp(t, [0, 7, 9, 62, 66, 105], [.09, .09, 0, 0, .09, .06])
def tone(f, a): return a * np.sin(2 * np.pi * f * t)
pad = (tone(110, .05) + tone(164.8, .035) + tone(220, .03) + tone(130.8, .03)) * np.interp(t, [0, 6, 20, 60, 90, 105], [0, .8, 1, 1, .9, 0]) * (.8 + .2 * np.sin(2 * np.pi * t / 7))
hit = np.zeros(n)
for s in np.arange(1, DUR, 2.0):
    i = int(s * SR); L = int(.25 * SR); seg = rng.normal(0, 1, L) * np.exp(-np.arange(L) / (.04 * SR)); hit[i:i + L] += seg[:max(0, min(L, n - i))] * .05 * (1 if 65 < s < 90 else 0)
bed = wind + murmur + traffic + pad + hit
vo = np.zeros(n)
def tts():
    try:
        import edge_tts
    except Exception: return False
    wd = sys.argv[2] if len(sys.argv) > 2 else '.'; os.makedirs(wd, exist_ok=True)
    async def one(k, txt):
        p = f"{wd}/vo_{k}.mp3"; await edge_tts.Communicate(txt, "ar-JO-TaimNeural", rate="-4%").save(p); return p
    async def all_(): return [await one(k, tx) for k, (_, tx) in enumerate(VO)]
    try: files = asyncio.run(all_())
    except Exception as e: print("tts failed", e); return False
    for (s, _), p in zip(VO, files):
        wav = p[:-4] + '.wav'; subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', p, '-ar', str(SR), '-ac', '1', wav], check=True)
        _, d = wavfile.read(wav); d = d.astype(np.float32) / 32768; i = int(s * SR); L = min(len(d), n - i); vo[i:i + L] += d[:L]
    return True
has_vo = False if os.environ.get('NO_VO') == '1' else tts(); print("narration:", "edge-tts ar-JO" if has_vo else "NONE (background sound only)")
duck = np.convolve((np.abs(vo) > .02).astype(float), np.ones(SR // 2) / (SR // 2), 'same'); duck = 1 - .55 * np.clip(duck * 3, 0, 1)
mix = bed * duck + vo * 1.1; mix = mix / max(1, np.abs(mix).max() / .9)
fade = np.minimum(1, np.minimum(t / 1.5, (DUR - t) / 3)); mix *= fade
wavfile.write(sys.argv[1], SR, (mix * 32767).astype(np.int16)); print("wrote", sys.argv[1])
