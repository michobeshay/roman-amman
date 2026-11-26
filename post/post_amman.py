"""Post: grade + Arabic titles/labels/timeline/subtitles -> ffmpeg pipe.  usage: post_amman.py FRAMES_DIR OUT.mp4 AUDIO.wav LABELS.json [--limit N] [--nosubs]"""
import sys, os, json, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, features
sys.path.insert(0, os.path.dirname(__file__)); from script_ar import VO, TITLES, LABELS, TIMELINE
W, H, FPS, N = 1080, 1920, 30, 3150
def find_font():
    for p in ["/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf", "/usr/share/fonts/opentype/noto/NotoSansArabic-Bold.ttf",
              "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if os.path.exists(p): return p
    import matplotlib; return os.path.join(matplotlib.get_data_path(), "fonts/ttf/DejaVuSans-Bold.ttf")
FP = find_font(); RAQM = features.check('raqm') and features.check('fribidi')
if not RAQM:
    import arabic_reshaper; from bidi.algorithm import get_display
def font(sz): return ImageFont.truetype(FP, sz, layout_engine=ImageFont.Layout.RAQM) if RAQM else ImageFont.truetype(FP, sz)
def tl(d, t, f): return d.textlength(t, font=f, direction='rtl', language='ar') if RAQM else d.textlength(get_display(arabic_reshaper.reshape(t)), font=f)
def put(d, xy, t, f, fill, anchor='ma'):
    if RAQM: d.text(xy, t, font=f, fill=fill, anchor=anchor, direction='rtl', language='ar')
    else: d.text(xy, get_display(arabic_reshaper.reshape(t)), font=f, fill=fill, anchor=anchor)
def ease(t): t = min(max(t, 0), 1); return t * t * (3 - 2 * t)
def layer(draw_fn):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); draw_fn(ImageDraw.Draw(im)); return im
def fit(d, t, maxw, sz):
    while sz > 40 and tl(d, t, font(sz)) > maxw: sz -= 4
    return font(sz)
def comp(x, im, op):
    a = np.asarray(im.split()[3], np.float32)[..., None] / 255
    sh = np.asarray(im.split()[3].filter(ImageFilter.GaussianBlur(9)), np.float32)[..., None] / 255
    x *= 1 - np.clip(sh * 1.4, 0, .75) * op
    rgb = np.asarray(im.convert('RGB'), np.float32) / 255; a = a * op
    x[:] = x * (1 - a) + rgb * a
def title_layer(kind, lines):
    def f(d):
        if kind == 'title':
            for k, ln in enumerate(lines): put(d, (W / 2, 250 + k * 150), ln, fit(d, ln, 960, 96), (255, 255, 255, 255))
            d.rectangle([W / 2 - 60, 250 + 150 * len(lines) - 10, W / 2 + 60, 250 + 150 * len(lines) - 4], fill=(255, 196, 60, 255))
        else:
            put(d, (W / 2, 640), lines[0], fit(d, lines[0], 960, 84), (255, 255, 255, 255))
            put(d, (W / 2, 800), lines[1], fit(d, lines[1], 960, 100), (255, 214, 120, 255))
    return layer(f)
def label_layer(t, px, py):
    def f(d):
        fo = font(46); w = tl(d, t, fo); x, y = int(px * W), int(py * H)
        y2 = max(y - 150, 330); xl = min(max(x, 140 + w / 2), W - 140 - w / 2)
        d.rounded_rectangle([xl - w / 2 - 26, y2 - 12, xl + w / 2 + 26, y2 + 78], 22, fill=(10, 10, 10, 190))
        put(d, (xl, y2), t, fo, (255, 255, 255, 255)); d.line([xl, y2 + 78, x, y], fill=(255, 196, 60, 255), width=4)
        d.ellipse([x - 10, y - 10, x + 10, y + 10], fill=(255, 196, 60, 255))
    return layer(f)
def sub_layer(t):
    def f(d):
        fo = fit(d, t, 940, 54); put(d, (W / 2, 1500), t, fo, (255, 255, 255, 255))
    return layer(f)
def timeline_layer(active):
    def f(d):
        y = 1640; d.line([140, y, W - 140, y], fill=(255, 255, 255, 180), width=4); xs = [W - 190, W / 2, 190]
        for k, ((_, t), x) in enumerate(zip(TIMELINE, xs)):
            on = k <= active; d.ellipse([x - 16, y - 16, x + 16, y + 16], fill=(255, 196, 60, 255) if on else (255, 255, 255, 120))
            put(d, (x, y + 34), t, font(36), (255, 255, 255, 255 if on else 120))
    return layer(f)
def main():
    fr, out, audio, labj = sys.argv[1:5]; limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else N
    subs = '--nosubs' not in sys.argv; labels = json.load(open(labj)) if os.path.exists(labj) else {}
    ends = [t0 + 4.6 for t0, _ in VO]; ends = [min(e, VO[i + 1][0] - .1) if i + 1 < len(VO) else e for i, e in enumerate(ends)]
    SUBS = [(int(a * FPS), int(b * FPS), sub_layer(t)) for (a, t), b in zip(VO, ends)]
    TL = [(a, b, title_layer(k, l)) for a, b, k, l in TITLES]; TLN = [timeline_layer(k) for k in range(3)]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    vig = (1 - .28 * np.clip((r - .45) / .9, 0, 1) ** 1.6)[..., None]; rng = np.random.default_rng(1)
    pr = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-i', audio,
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out + '.tmp.mp4'], stdin=subprocess.PIPE)
    last = None; lab_keys = sorted(int(k) for k in labels)
    for f in range(1, limit + 1):
        p = f"{fr}/F_{f:04d}.png"
        if os.path.exists(p):
            try: last = Image.open(p).convert('RGB'); last.load()
            except Exception: pass
        im = last.resize((W, H), Image.LANCZOS) if last.size != (W, H) else last
        x = np.asarray(im, np.float32) / 255; lum = (x @ np.array([.2126, .7152, .0722], np.float32))[..., None]
        x = np.clip(lum + (x - lum) * 1.06, 0, 1); x = x + .12 * (x * x * (3 - 2 * x) - x); x = x * vig
        for a, b, L in TL:
            if a <= f <= b: comp(x, L, ease((f - a) / 14) * ease((b - f) / 14))
        for key, t, a, b in LABELS:
            if a <= f <= b and lab_keys:
                k = min(lab_keys, key=lambda q: abs(q - f)); v = labels[str(k)].get(key)
                if v and v[2] > 0 and 0 < v[0] < 1 and 0 < v[1] < 1: comp(x, label_layer(t, v[0], v[1]), ease((f - a) / 12) * ease((b - f) / 12))
        if 1290 <= f <= 1950:
            ai = sum(f >= s for s, _ in TIMELINE) - 1
            if ai >= 0: comp(x, TLN[ai], ease((f - 1300) / 14) * ease((1945 - f) / 14))
        if subs:
            for a, b, L in SUBS:
                if a <= f <= b: comp(x, L, ease((f - a) / 6) * ease((b - f) / 6))
        x += rng.normal(0, .008, (H, W, 1)).astype(np.float32)
        fade = min(1, f / 20, (N - f + 1) / 40); x *= fade
        pr.stdin.write((np.clip(x, 0, 1) * 255 + .5).astype(np.uint8).tobytes())
        if f % 200 == 0: print("post", f, flush=True)
    pr.stdin.close(); pr.wait(); os.replace(out + '.tmp.mp4', out); print("wrote", out)
if __name__ == '__main__': main()
