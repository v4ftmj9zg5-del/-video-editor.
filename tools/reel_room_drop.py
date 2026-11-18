"""'Furniture drops in' Reel (1080x1920, 30 fps).

The empty room shell is shown first; then the furniture falls into place one piece
at a time (with a soft landing and motion blur), the small decor pops in, the table
lamp switches on, and the shot settles on the finished render.

Inputs: the final render and an EMPTY version of the same image (e.g. made with an
AI editor: "remove all furniture, keep everything else"). The shell is aligned to the
render automatically (ORB + homography), and each object's cut-out is the difference
between the two images inside its region, so pieces land exactly where they belong.

Usage: reel_room_drop.py RENDER.png SHELL.png OUT.mp4 [PLAN.json]
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reel_how_it_works import ease_io, ease_out  # noqa: E402
from reel_room_build import INK, REGIONS, Build, mask  # noqa: E402

W, H, FPS = 1080, 1920, 30
BPM = 90
BEAT = 60 / BPM
SCENES = [("shell", 3), ("furniture", 7), ("details", 4), ("final", 6)]

SUB = {   # small decor split out of the big regions
    "mobile": ("rect", (418, 636, 532, 812)),
    "toylamp": ("rect", (1030, 618, 1112, 752)),
    "basket": ("rect", (1112, 690, 1254, 756)),
    "bottles": ("rect", (1130, 640, 1254, 700)),
}
# (pieces, motion, start s, length s)
ITEMS = [
    (("rug",), "unroll", 2.00, .60),
    (("crib",), "drop", 2.45, .62),
    (("chair",), "drop", 2.95, .58),
    (("lamp",), "lower", 3.35, .70),
    (("dresser",), "drop", 4.45, .62),
    (("curtain_l", "curtain_r", "rod"), "lower", 5.70, .80),
    (("mobile",), "pop", 7.10, .42),
    (("mirror",), "pop", 7.70, .45),
    (("toylamp",), "pop", 8.00, .40),
    (("basket",), "pop", 8.20, .40),
    (("bottles",), "pop", 8.38, .40),
]
LAMP_ON = 8.75
# camera keyframes: (time s, render-x centre, zoom)
CAM = [(0, 627, 1.0), (2.0, 627, 1.02), (3.9, 627, 1.02), (4.45, 905, 1.0), (5.05, 905, 1.0),
       (5.75, 330, 1.0), (6.7, 330, 1.0), (8.1, 905, 1.0), (9.6, 905, 1.0), (11.2, 627, 1.0)]


def align(shell, render):
    """Warp the shell onto the render's pixel grid using the furniture-free top half."""
    g1 = cv2.cvtColor(shell.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    g2 = cv2.cvtColor(render.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    roi = np.zeros_like(g2)
    roi[: int(g2.shape[0] * .55)] = 255
    orb = cv2.ORB_create(4000)
    k1, d1 = orb.detectAndCompute(g1, None)
    k2, d2 = orb.detectAndCompute(g2, roi)
    if d1 is None or d2 is None:
        return cv2.resize(shell, render.shape[1::-1])
    m = sorted(cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d1, d2), key=lambda x: x.distance)[:600]
    if len(m) < 30:
        return cv2.resize(shell, render.shape[1::-1])
    src = np.float32([k1[x.queryIdx].pt for x in m])
    dst = np.float32([k2[x.trainIdx].pt for x in m])
    Hm, _ = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
    return cv2.warpPerspective(shell, Hm, render.shape[1::-1], flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)


def ease_back(t, s=1.25):
    t = min(max(t, 0), 1) - 1
    return 1 + t * t * ((s + 1) * t + s)


class Drop:
    def __init__(self, render, shell):
        self.b = Build(render, render)            # reuse text, camera and colour-diff masks
        self.R = self.b.R
        h, w = self.R.shape[:2]
        self.shape = (h, w)
        self.Sh = align(np.asarray(Image.open(shell).convert("RGB"), np.float32), self.R)
        lab = lambda a: cv2.cvtColor(a.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
        diff = np.linalg.norm(lab(self.R) - lab(self.Sh), axis=2)
        solid = np.clip((diff - 10) / 12, 0, 1)
        solid = cv2.morphologyEx(solid, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        solid = cv2.GaussianBlur(solid, (0, 0), 1.2)
        regions = dict(REGIONS, **SUB)
        boxes = {k: mask(self.shape, *v, feather=4) for k, v in regions.items()}
        carve = {"crib": ["mobile"], "dresser": ["toylamp", "basket", "bottles"]}
        self.alpha, self.box, self.anchor, self.raw = {}, {}, {}, {}
        for pieces, *_ in ITEMS:
            a = np.zeros(self.shape, np.float32)
            bx = np.zeros(self.shape, np.float32)
            for p in pieces:
                bp = boxes[p].copy()
                for c in carve.get(p, []):
                    bp *= 1 - boxes[c]
                if p in ("crib", "chair", "dresser", "rug"):
                    bp *= 1 - boxes["mural"]         # floor-standing pieces never carry wallpaper
                a = np.maximum(a, bp * solid)
                bx = np.maximum(bx, boxes[p])
            self.alpha[pieces] = a
            # settle region: the box grown downwards to pick up contact shadows
            k = np.zeros((41, 41), np.uint8)
            k[10:, :] = 1
            self.box[pieces] = cv2.GaussianBlur(cv2.dilate(bx, k), (0, 0), 6)
            self.raw[pieces] = bx
            ys, xs = np.where(a > .5)
            self.anchor[pieces] = (xs.mean(), ys.mean(), ys.min(), ys.max(), xs.min(), xs.max())
        # a piece may only settle where no later piece will land
        for i, (pieces, *_) in enumerate(ITEMS):
            for later, *_ in ITEMS[i + 1:]:
                self.box[pieces] = self.box[pieces] * (1 - cv2.GaussianBlur(self.raw[later], (0, 0), 3))
        lum = self.R.mean(2) / 255
        lampm = boxes["toylamp"] * np.clip((lum - .80) / .15, 0, 1)
        src = lampm[..., None] * np.array([255, 226, 180], np.float32)
        self.glow = cv2.GaussianBlur(src, (0, 0), 16) * .9 + cv2.GaussianBlur(src, (0, 0), 60) * .6

    def piece(self, pieces, motion, p):
        """Warped (colour, alpha) for a moving piece at progress p."""
        a = self.alpha[pieces]
        cx, cy, y0, y1, x0, x1 = self.anchor[pieces]
        blur = 0
        if motion == "drop":
            e = ease_back(p, 1.1)
            dy = -(y1 + 40) * (1 - e)
            M = np.float32([[1, 0, 0], [0, 1, dy]])
            blur = int(min(abs(dy) * .08, 28)) if p < .7 else 0
            fade = 1
        elif motion == "lower":
            e = ease_out(p)
            dy = -(y1 - y0 + 60) * (1 - e)
            M = np.float32([[1, 0, 0], [0, 1, dy]])
            fade = ease_out(p / .35)
        elif motion == "unroll":
            e = ease_out(p)
            s = max(e, .02)
            M = np.float32([[s, 0, x0 * (1 - s)], [0, 1, 0]])
            fade = ease_out(p / .2)
        else:   # pop
            e = ease_back(p, 1.6)
            s = .82 + .18 * e
            M = np.float32([[s, 0, cx * (1 - s)], [0, s, cy * (1 - s)]])
            fade = ease_out(p / .5)
        h, w = self.shape
        col = cv2.warpAffine(self.R, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        al = cv2.warpAffine(a, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        if blur > 1:
            col = cv2.blur(col, (1, blur))
            al = cv2.blur(al, (1, blur))
        return col, al * fade

    def compose(self, t):
        img = self.Sh.copy()
        settle = np.zeros(self.shape, np.float32)
        active = []
        for pieces, motion, st, ln in ITEMS:
            p = (t - st) / ln
            if p <= 0:
                continue
            if p >= 1:
                k = ease_io((p - 1) * ln / .3)        # 0.3 s settle into the real render (shadows)
                settle = np.maximum(settle, self.box[pieces] * k)
                active.append((pieces, "rest", 1.0))  # landed pieces stay drawn on top
            else:
                active.append((pieces, motion, p))
        img = img * (1 - settle[..., None]) + self.R * settle[..., None]
        for pieces, motion, p in active:
            if motion == "rest":
                col, al = self.R, self.alpha[pieces]
            else:
                col, al = self.piece(pieces, motion, p)
            img = img * (1 - al[..., None]) + col * al[..., None]
        on = ease_out((t - LAMP_ON) / .35) - .45 * ease_io((t - LAMP_ON - .5) / 1.2)
        if on > 0:
            img = img + self.glow * on
        return np.clip(img, 0, 255)

    def cam(self, t):
        for (t0, x0, z0), (t1, x1, z1) in zip(CAM, CAM[1:]):
            if t <= t1:
                k = ease_io((t - t0) / max(t1 - t0, 1e-6))
                return x0 + (x1 - x0) * k, z0 + (z1 - z0) * k
        return CAM[-1][1], CAM[-1][2]

    def frame(self, t, starts):
        b = self.b
        cx, z = self.cam(t)
        fr = b.camera(self.compose(t), cx, z)
        f = b.fonts
        if t < starts[1]:
            l1, _ = b.label("המעטפת מוכנה.", f["cta"], INK)
            l2, _ = b.label("עכשיו נכניס את הרהיטים", f["cta2"], INK, pill=False)
            a = ease_out((t - .1) / .45) * (1 - ease_io((t - (starts[1] - .3)) / .3))
            b.put(fr, l1, 330 - 130, a, dy=20 * (1 - ease_out(t / .5)))
            b.put(fr, l2, 440 - 130, ease_out((t - .5) / .4) * (1 - ease_io((t - (starts[1] - .3)) / .3)))
        for name, txt in (("details", "והפרטים הקטנים"),):
            i = [s[0] for s in SCENES].index(name)
            lt = t - starts[i]
            d = SCENES[i][1] * BEAT
            if 0 <= lt < d:
                lay, y = b.label(txt, f["hand"])
                b.put(fr, lay, y, ease_out((lt - .1) / .4) * (1 - ease_io((lt - (d - .35)) / .3)))
        i = len(SCENES) - 1
        lt = t - starts[i]
        if lt >= 0:
            c1, _ = b.label("רוצה חדר כזה?", f["cta"], INK)
            c2, _ = b.label("כתבי לי ״חדר״ בהודעה", f["cta2"], INK)
            c3, _ = b.label("⁦@roomstorytell_⁩", f["small"], INK)
            a = ease_out((lt - 1.6) / .5)
            b.put(fr, c1, 1240 - 130, a, dy=24 * (1 - a))
            b.put(fr, c2, 1390 - 130, ease_out((lt - 2.0) / .5))
            b.put(fr, c3, 1495 - 130, .85 * ease_out((lt - 2.3) / .5))
        return fr


def render(render_png, shell_png, out, plan=None):
    d = Drop(render_png, shell_png)
    durs = [beats * BEAT for _, beats in SCENES]
    starts = np.concatenate([[0], np.cumsum(durs)[:-1]])
    total = sum(durs)
    n = int(round(total * FPS))
    rng = np.random.default_rng(5)
    grain = [rng.normal(0, 3.0, (H // 2, W // 2, 1)).astype(np.float32) for _ in range(6)]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-preset", "slow", "-crf", "19",
           "-maxrate", "8M", "-bufsize", "12M", "-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(n):
        t = f / FPS
        fr = d.frame(t, starts) + cv2.resize(grain[f % 6], (W, H))[..., None]
        proc.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
    proc.stdin.close()
    proc.wait()
    print(f"wrote {out} ({total:.2f}s, {n} frames)")
    if plan:     # sound plan for reel_audio.py: thud on each landing, pops for the decor
        def at(sec):
            i = int(np.searchsorted(starts, sec, side="right") - 1)
            return [i, round(sec - starts[i], 3)]
        thuds = [at(st + ln * .55) for _, m, st, ln in ITEMS if m == "drop"]
        pops = [at(st + .05) for _, m, st, ln in ITEMS if m in ("pop", "unroll", "lower")]
        json.dump({"bpm": BPM, "scenes": [b for _, b in SCENES], "vo": [], "whooshes": [],
                   "thuds": thuds, "pops": pops, "sparkle": at(LAMP_ON)}, open(plan, "w"))


if __name__ == "__main__":
    render(*sys.argv[1:5])
