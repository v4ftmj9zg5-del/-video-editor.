"""'The room builds itself' Reel (1080x1920, 30 fps).

Every stage is derived from ONE final render, so all layers stay pixel-aligned:
before photo -> pencil sketch draws itself -> upper walls + pink rising to the
chair rail -> mural bleeds in like watercolour -> furniture colours in one by one
-> the ceiling lamp switches on -> photoreal render with a slow pan.

Usage: reel_room_build.py RENDER.png BEFORE.jpg OUT.mp4 [TIMES.json]
Object regions (in render pixels) are set in REGIONS for the render being used.
Writes a silent video; scene lengths are in beats so reel_audio.py can score it.
"""
import json
import math
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reel_how_it_works import font, ease_io, ease_out  # noqa: E402

W, H, FPS = 1080, 1920, 30
BPM = 90
BEAT = 60 / BPM
PAPER = np.array([247, 243, 236], np.float32)
INK = (58, 44, 38)
TX = 470                  # text centre: clear of the IG action rail on the right
rng = np.random.default_rng(7)

# scene name -> beats
SCENES = [("hook", 3), ("sketch", 3), ("walls", 4), ("mural", 3), ("furniture", 4), ("light", 2), ("final", 6)]

# regions for the nursery render (1254 x 1254): polygons / rects / ellipses
REGIONS = {
    "lamp": ("rect", (492, 40, 795, 275)),
    "rod": ("line", ((22, 72), (385, 332), 26)),
    "curtain_l": ("poly", [(10, 85), (150, 95), (150, 1230), (10, 1230)]),
    "curtain_r": ("poly", [(312, 295), (390, 300), (392, 1112), (312, 1112)]),
    "window": ("poly", [(118, 240), (334, 342), (334, 780), (118, 780)]),
    "mural": ("rect", (378, 318, 1108, 677)),
    "crib": ("rect", (310, 636, 710, 1068)),
    "chair": ("rect", (800, 772, 1038, 1052)),
    "dresser": ("poly", [(1012, 735), (1254, 735), (1254, 1210), (1012, 1210)]),
    "decor": ("rect", (1030, 622, 1254, 752)),
    "mirror": ("rect", (1124, 288, 1252, 666)),
    "rug": ("ellipse", (677, 1150, 395, 108)),
    "floor": ("poly", [(140, 1254), (140, 1168), (310, 1064), (1012, 1050), (1012, 1254)]),
}
RAIL_Y = 674
# furniture reveal order: (regions..., start, length) as fractions of the scene
FURNITURE = [(("rug",), 0.00, .38), (("crib",), .14, .42), (("chair",), .30, .40),
             (("dresser", "decor", "mirror"), .44, .42), (("curtain_l", "curtain_r", "rod"), .58, .42)]

TEXTS = {"sketch": "קודם, סקיצה", "walls": "ורוד עתיק עד הקרניז", "mural": "טפט בצבעי מים",
         "furniture": "ואז הרהיטים", "light": "ואור רך"}


def mask(shape, kind, spec, feather=3):
    h, w = shape
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    if kind == "rect":
        d.rectangle(spec, fill=255)
    elif kind == "poly":
        d.polygon(spec, fill=255)
    elif kind == "ellipse":
        cx, cy, rx, ry = spec
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)
    elif kind == "line":
        a, b, wd = spec
        d.line((a, b), fill=255, width=wd)
    if feather:
        m = m.filter(ImageFilter.GaussianBlur(feather))
    return np.asarray(m, np.float32) / 255


def smooth_noise(shape, scale, seed):
    r = np.random.default_rng(seed).standard_normal((shape[0] // scale + 2, shape[1] // scale + 2)).astype(np.float32)
    n = cv2.resize(r, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)
    n = cv2.GaussianBlur(n, (0, 0), scale / 2)
    return (n - n.min()) / (n.max() - n.min() + 1e-9)


def pencil(img):
    """Warm graphite sketch on cream paper from an RGB float image."""
    g = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    inv = 255 - g
    blur = cv2.GaussianBlur(inv, (0, 0), 6)
    dodge = np.clip(g * 255 / (255 - blur + 1), 0, 255)
    edges = cv2.Canny(cv2.GaussianBlur(g.astype(np.uint8), (0, 0), 1.2), 30, 80).astype(np.float32)
    edges = cv2.GaussianBlur(edges, (0, 0), .7)
    lum = np.clip(dodge / 255, 0, 1) ** 2.2 * (1 - .45 * edges / 255)
    lum = np.clip(.18 + .82 * lum, 0, 1)[..., None]
    ink = np.array(INK, np.float32)
    paper = PAPER * (1 - .035 * smooth_noise(g.shape, 3, 5)[..., None])
    return paper * lum + ink * (1 - lum)


class Build:
    def __init__(self, render, before):
        self.R = np.asarray(Image.open(render).convert("RGB"), np.float32)
        self.B = Image.open(before).convert("RGB")
        h, w = self.R.shape[:2]
        self.shape = (h, w)
        self.S = pencil(self.R)
        m = {k: mask(self.shape, *v) for k, v in REGIONS.items()}
        self.m = m
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        self.yy, self.xx = yy, xx
        lower = np.clip((yy - RAIL_Y) / 3 + .5, 0, 1)
        # expected "empty room" colour behind each pixel: floor / pink lower wall / cream upper wall
        # estimate the empty room behind the furniture: inpaint the object boxes at 1/4 size
        boxes = np.maximum.reduce([m[k] for k in ("lamp", "rod", "curtain_l", "curtain_r", "crib", "chair",
                                                    "dresser", "decor", "mirror", "rug")])
        sm = cv2.resize(self.R.astype(np.uint8), (w // 4, h // 4), interpolation=cv2.INTER_AREA)
        hole = (cv2.resize(boxes, (w // 4, h // 4)) > .05).astype(np.uint8)
        empty = cv2.inpaint(sm, cv2.dilate(hole, np.ones((5, 5), np.uint8)), 12, cv2.INPAINT_TELEA)
        empty = cv2.GaussianBlur(cv2.resize(empty, (w, h), interpolation=cv2.INTER_CUBIC), (0, 0), 6)
        lab = cv2.cvtColor(self.R.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
        bg = cv2.cvtColor(empty, cv2.COLOR_RGB2LAB).astype(np.float32)
        diff = np.linalg.norm(lab - bg, axis=2)
        solid = np.clip((diff - 9) / 10, 0, 1)
        solid = cv2.morphologyEx(solid, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        solid = cv2.GaussianBlur(solid, (0, 0), 1.5)
        lamp = Image.new("L", (w, h), 0)
        dl = ImageDraw.Draw(lamp)
        dl.ellipse((494, 138, 792, 258), fill=255)
        dl.ellipse((604, 40, 680, 62), fill=255)
        dl.rectangle((622, 50, 662, 150), fill=255)
        dl.ellipse((618, 236, 664, 274), fill=255)
        m["lamp"] = np.asarray(lamp.filter(ImageFilter.GaussianBlur(2)), np.float32) / 255
        for k in ("rod", "curtain_l", "curtain_r", "crib", "chair", "dresser", "decor", "mirror"):
            m[k] = m[k] * solid           # keep only pixels that differ from the empty wall/floor
        m["floor"] = m["floor"] * (1 - m["rug"])
        m["mural"] = mask(self.shape, *REGIONS["mural"], feather=10)
        objects = np.zeros(self.shape, np.float32)
        for k in ("lamp", "rod", "curtain_l", "curtain_r", "crib", "chair", "dresser", "decor", "mirror", "rug"):
            objects = np.maximum(objects, m[k])
        arch = np.clip(1 - np.maximum.reduce([objects, m["floor"], m["mural"], m["window"]]), 0, 1)
        self.upper_m = arch * (1 - lower)
        self.lower_m = arch * lower
        self.n_small = smooth_noise(self.shape, 18, 11)
        self.n_big = smooth_noise(self.shape, 70, 12)
        # watercolour bleed distance for the mural: grows from three seeds
        seeds = [(660, 560), (480, 470), (930, 500)]
        d = np.min([np.hypot(xx - sx, yy - sy) for sx, sy in seeds], axis=0)
        self.bleed = d / d[m["mural"] > .5].max() + .28 * (self.n_big - .5)
        # lamp glow source
        lum = self.R.mean(2) / 255
        self.glow_src = (np.clip((lum - .78) / .2, 0, 1) * m["lamp"])[..., None] * np.array([255, 236, 206], np.float32)
        self.glow = cv2.GaussianBlur(self.glow_src, (0, 0), 38) + .6 * cv2.GaussianBlur(self.glow_src, (0, 0), 110)
        self.fonts = {"hand": font("GveretLevin.ttf", 90), "hook": font("Heebo.ttf", 72, 300),
                      "hook2": font("Heebo.ttf", 46, 300), "small": font("Heebo.ttf", 34, 400),
                      "cta": font("FrankRuhlLibre.ttf", 80, 500), "cta2": font("Heebo.ttf", 46, 300)}
        self.cache = {}

    # ---------- composition in render space ----------
    def stage(self, scene, p):
        """Composite (render-space float RGB) for a scene at progress p in [0,1]."""
        S, R = self.S, self.R
        if scene == "sketch":
            k = np.clip((p * 1.35 - (self.xx + self.yy) / sum(self.shape) - .25 * (self.n_small - .5)) * 6, 0, 1)[..., None]
            return PAPER * (1 - k) + S * k
        out = S.copy()
        # walls: upper cream + window fade in, then pink rises from the floor to the rail
        pw = 1.0 if scene != "walls" else p
        a_up = ease_out(pw / .35)
        up = np.maximum(self.upper_m, self.m["window"]) * a_up
        out = out * (1 - up[..., None]) + R * up[..., None]
        rise = ease_io((pw - .22) / .7)
        level = 1064 - (1064 - RAIL_Y + 4) * rise
        wave = 5 * np.sin(self.xx / 38 + pw * 9) + 4 * (self.n_small - .5)
        filled = np.clip((self.yy - level - wave) / 4, 0, 1) * self.lower_m
        out = out * (1 - filled[..., None]) + R * filled[..., None]
        if 0 < rise < 1:      # wet highlight on the paint edge
            edge = np.exp(-((self.yy - level - wave) / 5) ** 2) * self.lower_m
            out += edge[..., None] * 14
        fl = self.m["floor"] * ease_out((pw - .55) / .45)
        out = out * (1 - fl[..., None]) + R * fl[..., None]
        if scene == "walls":
            return out
        # mural bleeds in
        pm = 1.0 if scene != "mural" else p
        t = ease_io(pm) * 1.45 - .05
        bm = np.clip((t - self.bleed) * 9, 0, 1) * self.m["mural"]
        rim = np.exp(-((t - self.bleed) * 14) ** 2) * self.m["mural"] * (pm < 1)
        layer = R * (1 - .10 * rim[..., None])
        out = out * (1 - bm[..., None]) + layer * bm[..., None]
        if scene == "mural":
            return out
        # furniture colours in, bottom-up, one by one
        pf = 1.0 if scene != "furniture" else p
        for names, st, ln in FURNITURE:
            q = ease_io((pf - st) / ln)
            if q <= 0:
                continue
            if names not in self.cache:
                mm = np.maximum.reduce([self.m[n] for n in names])
                ys = np.where(mm.max(1) > .5)[0]
                self.cache[names] = (mm, ys.min(), ys.max())
            mm, y0, y1 = self.cache[names]
            thr = y1 - (y1 - y0 + 40) * q
            k = np.clip((self.yy - thr + 30 * (self.n_small - .5)) / 14, 0, 1) * mm
            out = out * (1 - k[..., None]) + R * k[..., None]
        dim = 1 - .10 * ease_io(pf) if scene == "furniture" else .90
        if scene == "furniture":
            return out * dim
        # light: lamp appears and switches on
        pl = 1.0 if scene != "light" else p
        la = ease_out(pl / .4)
        out = out * (1 - (self.m["lamp"] * la)[..., None]) + R * (self.m["lamp"] * la)[..., None]
        on = ease_out((pl - .3) / .5)
        out = out * (dim + (1 - dim) * on)
        return out

    def glow_amount(self, scene, p):
        if scene == "light":
            return .85 * ease_out((p - .3) / .4) - .3 * ease_io((p - .7) / .3)
        if scene == "final":
            return .75 * (1 - ease_io(p / .5))
        return 0.0

    # ---------- camera ----------
    def camera(self, img, cx, zoom):
        """Crop a 9:16 window centred at render x=cx, scale to W x H."""
        h, w = self.shape
        ch = h / zoom
        cw = ch * W / H
        x0 = min(max(cx - cw / 2, 0), w - cw)
        y0 = (h - ch) / 2
        M = np.float32([[W / cw, 0, -x0 * W / cw], [0, H / ch, -y0 * H / ch]])
        out = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
        blur = cv2.GaussianBlur(out, (0, 0), 1.1)
        return np.clip(out + .35 * (out - blur), 0, 255)

    # ---------- text ----------
    def label(self, text, fnt, color=INK, pill=True, y=1405):
        key = (text, id(fnt), pill)
        if key not in self.cache:
            tmp = Image.new("RGBA", (W, 260), (0, 0, 0, 0))
            d = ImageDraw.Draw(tmp)
            d.text((TX, 130), "‏" + text, font=fnt, fill=color, anchor="mm", direction="rtl", language="he")
            box = tmp.getbbox()
            lay = Image.new("RGBA", (W, 260), (0, 0, 0, 0))
            if pill and box:
                p = Image.new("RGBA", (W, 260), (0, 0, 0, 0))
                ImageDraw.Draw(p).rounded_rectangle((box[0] - 46, box[1] - 26, box[2] + 46, box[3] + 30), 60,
                                                    fill=(250, 246, 240, 215))
                lay.alpha_composite(p.filter(ImageFilter.GaussianBlur(1)))
            lay.alpha_composite(tmp)
            self.cache[key] = lay
        return self.cache[key], y - 130

    @staticmethod
    def put(frame, lay, y, alpha, dy=0):
        if alpha <= 0:
            return
        a = np.asarray(lay, np.float32)
        y = int(y + dy)
        y0, y1 = max(y, 0), min(y + a.shape[0], H)
        a = a[y0 - y:y1 - y]
        al = a[..., 3:4] / 255 * min(alpha, 1)
        frame[y0:y1] = frame[y0:y1] * (1 - al) + a[..., :3] * al

    def scene_text(self, frame, name, t, d):
        if name in TEXTS:
            lay, y = self.label(TEXTS[name], self.fonts["hand"])
            a = ease_out((t - .15) / .45) * (1 - ease_io((t - (d - .35)) / .3))
            self.put(frame, lay, y, a, dy=24 * (1 - ease_out((t - .15) / .5)))

    # ---------- scenes ----------
    def hook(self, t, d):
        z = 1 + .07 * ease_io(t / d)
        b = self.B
        sw, sh = b.size
        s = max(W / sw, H / sh) * z
        cw, chh = W / s, H / s
        x0, y0 = (sw - cw) / 2, (sh - chh) * .45
        img = np.asarray(b.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + chh)), np.float32)
        img = img * .94 + 4
        grad = np.clip(1 - np.arange(H) / 760, 0, 1)[:, None, None] ** 1.6
        img = img * (1 - .55 * grad)
        l1, _ = self.label("חדר ריק. ארגזים. עגלה.", self.fonts["hook"], (255, 255, 255), pill=False)
        l2, _ = self.label("בואי נראה מה אפשר לעשות ממנו", self.fonts["hook2"], (255, 255, 255), pill=False)
        self.put(img, l1, 300 - 130, ease_out(t / .35), dy=18 * (1 - ease_out(t / .5)))
        self.put(img, l2, 395 - 130, ease_out((t - .45) / .4))
        return img

    def built(self, name, t, d):
        p = min(max(t / d, 0), 1)
        img = self.stage(name, p)
        g = self.glow_amount(name, p)
        if g > 0:
            img = img + self.glow * g
        # gentle push-in across the build, centred on the crib and mural
        k = (self.order[name] + p) / 5
        frame = self.camera(np.clip(img, 0, 255), 600, 1 + .05 * k)
        self.scene_text(frame, name, t, d)
        return frame

    def final(self, t, d):
        p = min(max(t / d, 0), 1)
        img = np.clip(self.R + self.glow * self.glow_amount("final", p), 0, 255)
        mv = ease_io(p / .62)
        frame = self.camera(img, 600 + (900 - 600) * mv, 1.05 - .05 * mv)
        c1, _ = self.label("רוצה חדר כזה?", self.fonts["cta"], INK)
        c2, _ = self.label("כתבי לי ״חדר״ בהודעה", self.fonts["cta2"], INK)
        c3, _ = self.label("\u2066@roomstorytell_\u2069", self.fonts["small"], INK)
        a = ease_out((t - 1.9) / .5)
        self.put(frame, c1, 1240 - 130, a, dy=26 * (1 - a))
        self.put(frame, c2, 1390 - 130, ease_out((t - 2.3) / .5))
        self.put(frame, c3, 1495 - 130, .8 * ease_out((t - 2.6) / .5))
        return frame

    def fn(self, name):
        if name == "hook":
            return self.hook
        if name == "final":
            return self.final
        return lambda t, d: self.built(name, t, d)


def render(render_png, before, out):
    b = Build(render_png, before)
    b.order = {n: i for i, n in enumerate(["sketch", "walls", "mural", "furniture", "light"])}
    tl = [(n, beats * BEAT) for n, beats in SCENES]
    starts = np.concatenate([[0], np.cumsum([d for _, d in tl])[:-1]])
    total = sum(d for _, d in tl)
    n = int(round(total * FPS))
    grain = [rng.normal(0, 3.2, (H // 2, W // 2, 1)).astype(np.float32) for _ in range(6)]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-preset", "slow", "-crf", "18",
           "-maxrate", "11M", "-bufsize", "16M", "-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    XF = .3
    for f in range(n):
        t = f / FPS
        i = int(np.searchsorted(starts, t, side="right") - 1)
        name, d = tl[i]
        frame = b.fn(name)(t - starts[i], d)
        if name == "hook" and t > starts[1] - XF:          # photo -> blank paper
            k = ease_io((t - (starts[1] - XF)) / XF)
            frame = frame * (1 - k) + PAPER * k
        g = cv2.resize(grain[f % 6], (W, H))[..., None]
        frame = np.clip(frame + g, 0, 255).astype(np.uint8)
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    proc.wait()
    print(f"wrote {out} ({total:.2f}s, {n} frames)")
    return [beats for _, beats in SCENES]


if __name__ == "__main__":
    beats = render(*sys.argv[1:4])
    if len(sys.argv) > 4:
        json.dump({"bpm": BPM, "scenes": beats}, open(sys.argv[4], "w"))
