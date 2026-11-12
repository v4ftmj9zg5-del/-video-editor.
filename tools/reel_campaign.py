"""Paid Instagram ad: "see the room before it exists" (1080x1920, 30 fps, ~25 s).

Hook: the nursery render as a pencil sketch that inks itself, wiped into the colour
render -> the designer's own walkthrough clip -> three different rooms -> quick detail
cuts -> what the client gets (render + CAD plan + shopping list) -> CTA.
Scene lengths are in beats at BPM so reel_audio.py can score it with cuts on the beat.

Usage: reel_campaign.py ASSETS.json OUT.mp4 [PLAN.json]
ASSETS: {"hero": png, "clip": mp4, "clip_from": s, "rooms": [[img, fx, fy], ...],
         "details": [[img, fx, fy], ...], "plan": png}
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reel_how_it_works import ease_io, ease_out, font  # noqa: E402
from reel_room_build import pencil  # noqa: E402

W, H, FPS = 1080, 1920, 30
BPM = 90
BEAT = 60 / BPM
TX = 470                                   # text centre, clear of the IG action rail
INK, CREAM = (43, 33, 28), (250, 246, 240)
SCENES = [("hook", 3), ("reveal", 3), ("clip", 6), ("rooms", 9), ("details", 6), ("deliver", 5), ("cta", 7)]


def load(path):
    return np.asarray(Image.open(path).convert("RGB"), np.float32)


def kb(img, t, fx=.5, fy=.5, z0=1.0, z1=1.08, dx=0.0):
    """Ken Burns crop to 9:16 with eased zoom and drift; img float RGB."""
    h, w = img.shape[:2]
    z = z0 + (z1 - z0) * ease_io(t)
    s = max(W / w, H / h) * z
    cw, ch = W / s, H / s
    cx = min(max(fx * w + dx * w * (ease_io(t) - .5), cw / 2), w - cw / 2)
    cy = min(max(fy * h, ch / 2), h - ch / 2)
    M = np.float32([[s, 0, -(cx - cw / 2) * s], [0, s, -(cy - ch / 2) * s]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


def grade(f):
    """Shared warm, slightly lifted grade so renders, photos and clip match."""
    f = f * np.array([1.015, 1.0, .975], np.float32) + 3
    lum = f.mean(2, keepdims=True)
    f = lum + (f - lum) * .96
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = 1 - .22 * (((xx - W / 2) / (W * .75)) ** 2 + ((yy - H / 2) / (H * .75)) ** 2)
    return np.clip(f * v[..., None], 0, 255)


_cache = {}


def text_layer(lines, size_font, color, pill=None, cx=TX, gap=1.2, shadow=False):
    key = (tuple(lines), id(size_font[0]), color, pill, shadow)
    if key in _cache:
        return _cache[key]
    fonts = size_font
    lay = Image.new("RGBA", (W, 600), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    y = 40
    for ln, f in zip(lines, fonts):
        a, de = f.getmetrics()
        d.text((cx, y), "‏" + ln, font=f, fill=color, anchor="ma", direction="rtl", language="he")
        y += int((a + de) * gap)
    box = lay.getbbox()
    out = Image.new("RGBA", lay.size, (0, 0, 0, 0))
    if pill and box:
        p = Image.new("RGBA", lay.size, (0, 0, 0, 0))
        ImageDraw.Draw(p).rounded_rectangle((box[0] - 48, box[1] - 30, box[2] + 48, box[3] + 34), 46, fill=pill)
        out.alpha_composite(p)
    if shadow:
        sh = Image.new("RGBA", lay.size, (0, 0, 0, 0))
        sh.putalpha(lay.getchannel("A").filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * .6)))
        out.alpha_composite(sh)
    out.alpha_composite(lay)
    arr = np.asarray(out, np.float32)
    _cache[key] = arr
    return arr


def put(frame, lay, y, alpha, dy=0.0):
    if alpha <= 0:
        return frame
    y = int(y + dy)
    y0, y1 = max(y, 0), min(y + lay.shape[0], H)
    a = lay[y0 - y:y1 - y]
    al = a[..., 3:4] / 255 * min(alpha, 1)
    frame[y0:y1] = frame[y0:y1] * (1 - al) + a[..., :3] * al
    return frame


def inout(t, d, a=.12, b=.32):
    return ease_out((t - a) / .35) * (1 - ease_io((t - (d - b)) / .28))


class Ad:
    def __init__(self, A):
        self.A = A
        self.hero = load(A["hero"])
        self.sketch = pencil(self.hero)
        h, w = self.hero.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        rng = np.random.default_rng(3)
        n = cv2.GaussianBlur(rng.standard_normal((h // 16 + 2, w // 16 + 2)).astype(np.float32), (0, 0), 2)
        n = cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC)
        self.draw_order = (yy / h) * .7 + (xx / w) * .3 + .12 * n            # pencil fills top-left -> bottom-right
        self._rooms = [(load(p), fx, fy) for p, fx, fy in A["rooms"]]
        self._details = [(load(p), fx, fy) for p, fx, fy in A["details"]]
        self.plan = load(A["plan"])
        cap = cv2.VideoCapture(A["clip"])
        cap.set(cv2.CAP_PROP_POS_MSEC, A.get("clip_from", 0) * 1000)
        self._clip = []
        for _ in range(int(6 * BEAT * FPS) + 4):
            ok, fr = cap.read()
            if not ok:
                break
            self._clip.append(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
        F = lambda n, s, w=None: font(n, s, w)
        self.f = {"big": F("FrankRuhlLibre.ttf", 104, 500), "mid": F("FrankRuhlLibre.ttf", 84, 500),
                  "sub": F("Heebo.ttf", 46, 300), "lab": F("Heebo.ttf", 50, 400), "small": F("Heebo.ttf", 34, 400),
                  "cta": F("FrankRuhlLibre.ttf", 78, 500), "cta2": F("Heebo.ttf", 48, 400)}

    # ---- scenes ------------------------------------------------------------
    def hook(self, t, d):
        p = t / d
        k = np.clip((p * 1.35 + .32 - self.draw_order) * 7, 0, 1)[..., None]
        paper = np.array([247, 243, 236], np.float32)
        img = paper * (1 - k) + self.sketch * k
        fr = kb(img, p, .5, .5, 1.12, 1.04)
        lay = text_layer(["ככה זה מתחיל"], [self.f["big"]], INK, shadow=False)
        return put(fr, lay, 300, ease_out((t - .1) / .4), 26 * (1 - ease_out(t / .5)))

    def reveal(self, t, d):
        p = t / d
        h, w = self.hero.shape[:2]
        edge = (1 - ease_io(p / .55)) * 1.25 - .1                        # colour sweeps in from the right
        xx = np.linspace(0, 1, w, dtype=np.float32)[None, :]
        k = np.clip((xx - edge) / .06, 0, 1)[..., None]
        img = self.sketch * (1 - k) + self.hero * k
        fr = grade(kb(img, p, .5, .5, 1.04, 1.0))
        lay = text_layer(["וככה זה נגמר"], [self.f["big"]], INK, pill=(*CREAM, 215))
        return put(fr, lay, 300, ease_out((t - .45) / .4) * (1 - ease_io((t - (d - .25)) / .25)))

    def clip(self, t, d):
        i = min(int(t * FPS), len(self._clip) - 1)
        fr = grade(self._clip[i].astype(np.float32))
        lay = text_layer(["כל פרט מתוכנן"], [self.f["lab"]], INK, pill=(*CREAM, 225))
        return put(fr, lay, 1330, inout(t, d))

    def rooms(self, t, d):
        n = len(self._rooms)
        seg = d / n
        i = min(int(t / seg), n - 1)
        lt = t - i * seg
        img, fx, fy = self._rooms[i]
        fr = grade(kb(img, lt / seg, fx, fy, 1.10, 1.02, dx=.04 * (-1) ** i))
        lay = text_layer(["כל ילד, הסיפור שלו"], [self.f["lab"]], INK, pill=(*CREAM, 225))
        return put(fr, lay, 1330, inout(t, d, .2, .35))

    def details(self, t, d):
        n = len(self._details)
        seg = d / n
        i = min(int(t / seg), n - 1)
        img, fx, fy = self._details[i]
        return grade(kb(img, (t - i * seg) / seg, fx, fy, 1.16, 1.06))

    def deliver(self, t, d):
        bg = grade(kb(self.hero, t / d, .5, .5, 1.2, 1.25))
        bg = cv2.GaussianBlur(bg, (0, 0), 18) * .78 + np.array(CREAM, np.float32) * .22
        fr = bg.copy()
        cards = [(self.hero, -14, 0.0), (self.plan, 8, .35)]
        for img, ang, st in cards:
            a = ease_out((t - st) / .5)
            if a <= 0:
                continue
            h, w = img.shape[:2]
            cw = 560
            ch = int(cw * h / w)
            card = cv2.resize(img, (cw, ch), interpolation=cv2.INTER_AREA)
            card = cv2.copyMakeBorder(card, 18, 18, 18, 18, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            ch, cw = card.shape[:2]
            cx, cy = (330 if ang < 0 else 610), (640 if ang < 0 else 1080) + 60 * (1 - a)
            M = cv2.getRotationMatrix2D((cw / 2, ch / 2), ang * (.6 + .4 * a), .92 + .08 * a)
            M[:, 2] += (cx - cw / 2, cy - ch / 2)
            warped = cv2.warpAffine(card, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0))
            mask = cv2.warpAffine(np.ones((ch, cw), np.float32), M, (W, H))
            sh = cv2.GaussianBlur(cv2.warpAffine(np.ones((ch, cw), np.float32), M + np.float32([[0, 0, 10], [0, 0, 22]]), (W, H)), (0, 0), 16)
            fr = fr * (1 - .28 * a * sh[..., None])
            fr = fr * (1 - a * mask[..., None]) + warped * (a * mask[..., None])
        lay = text_layer(["הדמיה · תוכנית · רשימת קניות"], [self.f["lab"]], INK, pill=(*CREAM, 235))
        return put(fr, lay, 1420, ease_out((t - .6) / .4))

    def cta(self, t, d):
        p = t / d
        fr = grade(kb(self.hero, p, .5, .52, 1.0, 1.10))
        top = np.clip((np.arange(H, dtype=np.float32) - 820) / 240, 0, 1)[:, None, None] * .86
        fr = fr * (1 - top) + np.array(CREAM, np.float32) * top
        l1 = text_layer(["רוצה לראות את החדר", "של הילדים שלך,", "לפני שקונים?"], [self.f["cta"]] * 3, INK, gap=1.08)
        l2 = text_layer(["כתבי לי ״חדר״ בהודעה"], [self.f["cta2"]], CREAM, pill=(*INK, 240))
        l3 = text_layer(["⁦@roomstorytell_⁩ · הדמיות"], [self.f["small"]], INK)
        a = ease_out((t - .25) / .5)
        fr = put(fr, l1, 960, a, 30 * (1 - a))
        fr = put(fr, l2, 1330, ease_out((t - .9) / .4))
        return put(fr, l3, 1450, .85 * ease_out((t - 1.3) / .4))


def render(A, out, plan=None):
    ad = Ad(A)
    durs = [b * BEAT for _, b in SCENES]
    starts = np.concatenate([[0], np.cumsum(durs)[:-1]])
    total = sum(durs)
    n = int(round(total * FPS))
    rng = np.random.default_rng(9)
    grain = [rng.normal(0, 2.6, (H // 2, W // 2, 1)).astype(np.float32) for _ in range(6)]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-preset", "slow", "-crf", "19",
           "-maxrate", "9M", "-bufsize", "14M", "-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    XF = .22
    for f in range(n):
        t = f / FPS
        i = int(np.searchsorted(starts, t, side="right") - 1)
        name, d = SCENES[i][0], durs[i]
        fr = getattr(ad, name)(t - starts[i], d)
        if i + 1 < len(SCENES) and SCENES[i + 1][0] in ("deliver", "cta") and t > starts[i + 1] - XF:
            nxt = getattr(ad, SCENES[i + 1][0])(0.0, durs[i + 1])
            k = ease_io((t - (starts[i + 1] - XF)) / XF)
            fr = fr * (1 - k) + nxt * k
        fr = fr + cv2.resize(grain[f % 6], (W, H))[..., None]
        proc.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
        if f % 60 == 0:
            print("frame", f, "/", n, flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"wrote {out} ({total:.2f}s)")
    if plan:
        json.dump({"bpm": BPM, "scenes": [b for _, b in SCENES], "vo": [], "whooshes": [1, 2, 3, 4, 5, 6],
                   "papers": [[0, 0.05], [0, 0.9]], "ticks": [3, 4], "sparkle": [6, 0.9]}, open(plan, "w"))


if __name__ == "__main__":
    render(json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
