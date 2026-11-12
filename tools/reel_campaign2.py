"""Paid ad v2: fast, beat-cut, every shot with its own transition, process explained,
Hebrew captions for the designer's voice-over (1080x1920, 30 fps).

Shots (each has its own move; transitions differ per cut):
 sketch -> render (diagonal split) -> FLASH -> forms (cards slide in) -> PUSH LEFT ->
 plan (lines draw on) -> CIRCLE OPEN -> walkthrough clip -> SPIN -> shopping list (scroll,
 rows tick) -> CUT -> rooms x3 (curtain wipe / push down / centre doors) -> details x4
 (hard cuts on the beat) -> DISSOLVE -> CTA.

Usage: reel_campaign2.py ASSETS.json OUT.mp4 [AUDIOPLAN.json]
ASSETS adds to v1: "forms": [png, ...], "list": png, optional "durations": {shot: seconds},
"captions": {shot: text}. Without durations, shots are timed in beats at BPM.
"""
import json
import math
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reel_campaign import CREAM, INK, grade, load, put, text_layer  # noqa: E402
from reel_how_it_works import ease_io, ease_out, font  # noqa: E402
from reel_room_build import pencil  # noqa: E402

W, H, FPS = 1080, 1920, 30
BPM = 112
BEAT = 60 / BPM
PAPER = np.array([247, 243, 236], np.float32)

SHOTS = [("sketch", 3), ("render", 3), ("forms", 6), ("plan", 6), ("clip", 5), ("list", 6),
         ("room0", 3), ("room1", 3), ("room2", 3), ("det0", 2), ("det1", 2), ("det2", 2), ("det3", 2), ("cta", 8)]
# transition INTO each shot (name -> kind); missing = hard cut
TRANS = {"render": "split", "forms": "flash", "plan": "push_left", "clip": "circle", "list": "spin",
         "room1": "curtain", "room2": "push_down", "det0": "doors", "cta": "dissolve"}
CAPTIONS = {
    "sketch": "ככה זה מתחיל…", "render": "וככה זה נגמר.",
    "forms": "קודם את ממלאת שאלון קצר ושולחת מידות",
    "plan": "אני בונה תוכנית העמדה מדויקת, לפי החדר שלך",
    "clip": "ואז את רואה הדמיה, איך החדר ייראה באמת",
    "list": "ומקבלת רשימת קניות עם כל פריט, מידה ומחיר",
    "room0": "כל ילד, והסיפור שלו",
}
STEPS = {"forms": "שלב 1 · שאלון ומדידות", "plan": "שלב 2 · תוכנית העמדה", "clip": "שלב 3 · הדמיה",
         "list": "שלב 4 · רשימת קניות"}


def fit(img, w, h):
    """Crop-to-fill img (float) into w x h, centred."""
    ih, iw = img.shape[:2]
    s = max(w / iw, h / ih)
    r = cv2.resize(img, (int(iw * s + .5), int(ih * s + .5)), interpolation=cv2.INTER_AREA)
    y0, x0 = (r.shape[0] - h) // 2, (r.shape[1] - w) // 2
    return r[y0:y0 + h, x0:x0 + w]


def pan(img, t, fx=.5, fy=.5, dx=0.0, dy=0.0, zoom=1.06):
    """Fixed-zoom camera that slides (no zoom in/out)."""
    ih, iw = img.shape[:2]
    s = max(W / iw, H / ih) * zoom
    cw, ch = W / s, H / s
    k = ease_io(t) - .5
    cx = min(max(fx * iw + dx * iw * k, cw / 2), iw - cw / 2)
    cy = min(max(fy * ih + dy * ih * k, ch / 2), ih - ch / 2)
    M = np.float32([[s, 0, -(cx - cw / 2) * s], [0, s, -(cy - ch / 2) * s]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


def card_on(bg, img, cx, cy, width, ang=0.0, alpha=1.0, shadow=.3):
    h, w = img.shape[:2]
    cw, ch = int(width), int(width * h / w)
    c = cv2.resize(img, (cw, ch), interpolation=cv2.INTER_AREA)
    M = cv2.getRotationMatrix2D((cw / 2, ch / 2), ang, 1.0)
    M[:, 2] += (cx - cw / 2, cy - ch / 2)
    warped = cv2.warpAffine(c, M, (W, H), flags=cv2.INTER_LINEAR)
    m = cv2.warpAffine(np.ones((ch, cw), np.float32), M, (W, H))
    Ms = M.copy()
    Ms[:, 2] += (8, 22)
    sh = cv2.GaussianBlur(cv2.warpAffine(np.ones((ch, cw), np.float32), Ms, (W, H)), (0, 0), 18)
    bg = bg * (1 - shadow * alpha * sh[..., None])
    return bg * (1 - alpha * m[..., None]) + warped * (alpha * m[..., None])


class Ad2:
    def __init__(self, A):
        self.A = A
        self.hero = load(A["hero"])
        self._sk = pencil(self.hero)
        h, w = self.hero.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        n = cv2.resize(cv2.GaussianBlur(np.random.default_rng(3).standard_normal((h // 16 + 2, w // 16 + 2)).astype(np.float32), (0, 0), 2),
                       (w, h), interpolation=cv2.INTER_CUBIC)
        self.order = (yy / h) * .65 + (xx / w) * .35 + .1 * n
        self.rooms = [(load(p), fx, fy) for p, fx, fy in A["rooms"]]
        self.dets = [(load(p), fx, fy) for p, fx, fy in A["details"]]
        self._forms = [load(p) for p in A["forms"]]
        self.lst = load(A["list"])
        plan = load(A["plan"])
        self._plan = plan
        g = plan.mean(2)
        ph, pw = g.shape
        py, px = np.mgrid[0:ph, 0:pw].astype(np.float32)
        self.plan_ink = np.clip((235 - g) / 120, 0, 1)                    # how "drawn" a pixel is
        self.plan_order = np.where(self.plan_ink > .5, (px / pw) * .5 + (py / ph) * .5, 0) \
            + .05 * cv2.resize(np.random.default_rng(4).random((ph // 40 + 1, pw // 40 + 1)).astype(np.float32), (pw, ph))
        cap = cv2.VideoCapture(A["clip"])
        cap.set(cv2.CAP_PROP_POS_MSEC, A.get("clip_from", 0) * 1000)
        self.clipf = []
        for _ in range(240):
            ok, fr = cap.read()
            if not ok:
                break
            self.clipf.append(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
        self.f = {"cap": font("Heebo.ttf", 48, 500), "step": font("Heebo.ttf", 40, 500),
                  "big": font("FrankRuhlLibre.ttf", 104, 500), "cta": font("FrankRuhlLibre.ttf", 78, 500),
                  "cta2": font("Heebo.ttf", 48, 400), "small": font("Heebo.ttf", 34, 400)}
        self.caps = dict(CAPTIONS, **A.get("captions", {}))

    # ---------- shots (t in 0..1, d seconds) ----------
    def sketch(self, t, d):
        k = np.clip((t * 1.4 + .3 - self.order) * 7, 0, 1)[..., None]
        return pan(PAPER * (1 - k) + self._sk * k, t, .5, .5, dy=-.05, zoom=1.08)

    def render(self, t, d):
        return grade(pan(self.hero, t, .5, .5, dx=.05, zoom=1.08))

    def forms(self, t, d):
        bg = np.empty((H, W, 3), np.float32)
        bg[:] = (233, 227, 218)
        fr = bg
        n = len(self._forms)
        for i, img in enumerate(self._forms):
            st = i * .16
            a = ease_out((t - st) / .22)
            if a <= 0:
                continue
            x = W * .5 + (i - (n - 1) / 2) * 70 + (1 - a) * 900 * (1 if i % 2 else -1)
            y = H * .44 + (i - (n - 1) / 2) * 40
            fr = card_on(fr, img, x, y, 640, ang=(-7 + i * 4.5) * a, alpha=min(1, a * 1.2))
        return fr

    def plan(self, t, d):
        bg = np.empty((H, W, 3), np.float32)
        bg[:] = (252, 251, 248)
        p = self._plan
        drawn = np.clip((t * 1.3 + .15 - self.plan_order) * 14, 0, 1)
        drawn = np.where(self.plan_ink > .5, drawn, np.clip((t - .55) / .3, 0, 1))
        img = 255 - (255 - p) * drawn[..., None]
        return card_on(bg, img, W / 2 + 20 * (ease_io(t) - .5), H * .44, 1000, alpha=1, shadow=.15)

    def clip(self, t, d):
        i = min(int(t * d * FPS), len(self.clipf) - 1)
        return grade(self.clipf[i].astype(np.float32))

    def list(self, t, d):
        bg = np.empty((H, W, 3), np.float32)
        bg[:] = (233, 227, 218)
        L = self.lst
        lh, lw = L.shape[:2]
        s = 940 / lw
        view = int(1020 / s)
        y0 = int((lh - view) * ease_io(min(t * 1.15, 1)))
        crop = L[y0:y0 + view]
        fr = card_on(bg, crop, W / 2, H * .43, 940, alpha=1, shadow=.22)
        return fr

    def _room(self, i, t):
        img, fx, fy = self.rooms[i]
        moves = [dict(dx=.10), dict(dy=.08), dict(dx=-.10)]
        return grade(pan(img, t, fx, fy, zoom=1.12, **moves[i]))

    def room0(self, t, d): return self._room(0, t)
    def room1(self, t, d): return self._room(1, t)
    def room2(self, t, d): return self._room(2, t)

    def _det(self, i, t):
        img, fx, fy = self.dets[i]
        moves = [dict(dx=.06), dict(dy=-.06), dict(dx=-.06), dict(dy=.06)]
        return grade(pan(img, t, fx, fy, zoom=1.14, **moves[i]))

    def det0(self, t, d): return self._det(0, t)
    def det1(self, t, d): return self._det(1, t)
    def det2(self, t, d): return self._det(2, t)
    def det3(self, t, d): return self._det(3, t)

    def cta(self, t, d):
        fr = grade(pan(self.hero, t, .5, .5, dx=-.04, zoom=1.06))
        top = np.clip((np.arange(H, dtype=np.float32) - 820) / 240, 0, 1)[:, None, None] * .86
        fr = fr * (1 - top) + np.array(CREAM, np.float32) * top
        tt = t * d
        l1 = text_layer(["רוצה לראות את החדר", "של הילדים שלך,", "לפני שקונים?"], [self.f["cta"]] * 3, INK, gap=1.08)
        l2 = text_layer(["כתבי לי ״חדר״ בהודעה"], [self.f["cta2"]], CREAM, pill=(*INK, 240))
        l3 = text_layer(["⁦@roomstorytell_⁩ · הדמיות"], [self.f["small"]], INK)
        a = ease_out((tt - .15) / .4)
        fr = put(fr, l1, 960, a, 30 * (1 - a))
        fr = put(fr, l2, 1330, ease_out((tt - .7) / .35))
        return put(fr, l3, 1450, .85 * ease_out((tt - 1.0) / .35))

    def overlay(self, name, fr, tt, d):
        if name in STEPS:
            lay = text_layer([STEPS[name]], [self.f["step"]], CREAM, pill=(*INK, 230))
            a = ease_out((tt - .05) / .25)
            fr = put(fr, lay, 250, a, -20 * (1 - a))
        cap = self.caps.get(name)
        if cap and name != "cta":
            segs = cap if isinstance(cap, list) else [[0.0, cap]]          # [[start_s, text], ...]
            for k, (st, txt) in enumerate(segs):
                end = segs[k + 1][0] if k + 1 < len(segs) else d
                if not (st - .05 <= tt < end):
                    continue
                lines = wrap(txt, self.f["cap"], 700)
                lay = text_layer(lines, [self.f["cap"]] * len(lines), INK, pill=(*CREAM, 228), gap=1.12)
                a = ease_out((tt - st + .05) / .2) * (1 - ease_io((tt - (end - .12)) / .12))
                fr = put(fr, lay, 1340, a)
        return fr


def wrap(text, fnt, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if cur and fnt.getlength(trial) > maxw:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    lines.append(cur)
    return lines


def transition(kind, A, B, k):
    """Blend outgoing frame A into incoming B at progress k (0..1)."""
    if kind == "flash":
        w = np.exp(-((k - .5) / .18) ** 2)
        base = A if k < .5 else B
        return base * (1 - w) + 255 * w
    if kind == "split":                     # diagonal edge sweeping right->left
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        edge = (1 - ease_io(k)) * 1.5 - .25
        m = np.clip(((xx / W) + (yy / H) * .3 - edge) / .03, 0, 1)[..., None]
        return A * (1 - m) + B * m
    if kind in ("push_left", "push_down"):
        e = ease_io(k)
        out = np.empty_like(A)
        if kind == "push_left":
            o = int(W * e)
            out[:, :W - o] = A[:, o:]
            out[:, W - o:] = B[:, :o]
        else:
            o = int(H * e)
            out[o:] = A[:H - o]
            out[:o] = B[H - o:]
        return out
    if kind == "circle":
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = ease_in_out_r(k) * math.hypot(W, H) * .55
        m = np.clip((r - np.hypot(xx - W / 2, yy - H * .45)) / 6, 0, 1)[..., None]
        return A * (1 - m) + B * m
    if kind == "spin":
        e = ease_io(k)
        src = A if e < .5 else B
        ang = (e - .5) * 2 * 40
        sc = 1 + .35 * (1 - abs(e - .5) * 2)
        M = cv2.getRotationMatrix2D((W / 2, H / 2), ang, sc)
        out = cv2.warpAffine(src, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        b = int(1 + 30 * (1 - abs(e - .5) * 2)) | 1
        return cv2.GaussianBlur(out, (b, b), 0)
    if kind == "curtain":                   # vertical slats close over A and open on B
        xx = np.arange(W, dtype=np.float32)[None, :, None]
        slat = (xx % 135) / 135
        m = (slat < ease_io(k)).astype(np.float32)
        return A * (1 - m) + B * m
    if kind == "doors":
        e = ease_io(k)
        xx = np.arange(W, dtype=np.float32)[None, :, None]
        m = (np.abs(xx - W / 2) < e * W / 2).astype(np.float32)
        return A * (1 - m) + B * m
    if kind == "dissolve":
        e = ease_io(k)
        return A * (1 - e) + B * e
    return B


def ease_in_out_r(k):
    return ease_io(k)


def timeline(A):
    dur = A.get("durations", {})
    shots = [(n, dur.get(n, b * BEAT)) for n, b in SHOTS]
    starts = np.concatenate([[0], np.cumsum([d for _, d in shots])[:-1]])
    return shots, starts


def render(A, out, plan=None):
    ad = Ad2(A)
    shots, starts = timeline(A)
    total = float(starts[-1] + shots[-1][1])
    n = int(round(total * FPS))
    rng = np.random.default_rng(9)
    grain = [rng.normal(0, 2.4, (H // 2, W // 2, 1)).astype(np.float32) for _ in range(6)]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-preset", "slow", "-crf", "19",
           "-maxrate", "9M", "-bufsize", "14M", "-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    TW = .26                                 # transition window (centred on the cut)
    names = [s[0] for s in shots]

    def shot(i, tt):
        name, d = shots[i]
        tt = min(max(tt, 0), d)
        fr = getattr(ad, name)(tt / d, d)
        return ad.overlay(name, fr, tt, d)
    for f in range(n):
        t = f / FPS
        i = int(np.searchsorted(starts, t, side="right") - 1)
        fr = shot(i, t - starts[i])
        # transition straddling the next cut / previous cut
        for j in (i, i + 1):
            if 0 < j < len(shots) and names[j] in TRANS:
                c = starts[j]
                if c - TW / 2 <= t < c + TW / 2:
                    k = (t - (c - TW / 2)) / TW
                    fa = shot(j - 1, t - starts[j - 1])
                    fb = shot(j, max(t - c, 0))
                    fr = transition(TRANS[names[j]], fa, fb, k)
        fr = fr + cv2.resize(grain[f % 6], (W, H))[..., None]
        proc.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
        if f % 90 == 0:
            print("frame", f, "/", n, flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"wrote {out} ({total:.2f}s)")
    if plan:
        idx = {nm: k for k, nm in enumerate(names)}
        json.dump({"bpm": BPM, "scenes": [round(d / BEAT, 3) for _, d in shots], "vo": A.get("vo", []),
                   "whooshes": [idx[k] for k in ("plan", "list", "room1", "room2", "det0")],
                   "thuds": [[idx["forms"], 0.0], [idx["clip"], 0.0], [idx["det0"], 0.0], [idx["det1"], 0.0],
                             [idx["det2"], 0.0], [idx["det3"], 0.0]],
                   "papers": [[0, 0.05], [0, 0.6], [idx["forms"], 0.15], [idx["forms"], 0.45], [idx["plan"], 0.3]],
                   "ticks": [idx["list"], idx["room0"]],
                   "pops": [[idx["list"], 0.4 + .25 * k] for k in range(5)],
                   "sparkle": [idx["render"], 0.0]}, open(plan, "w"))


if __name__ == "__main__":
    render(json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
