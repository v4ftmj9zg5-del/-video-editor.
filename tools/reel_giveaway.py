"""Short giveaway Reel (1080x1920, 30 fps, ~12 s), cut on the beat.

hook on the hero render -> 4 rooms in fast beat cuts (each with its own move) ->
"I come to you + 1,000 NIS" -> how to enter -> date card.

Usage: reel_giveaway.py ASSETS.json OUT.mp4 [AUDIOPLAN.json]
ASSETS: {"hero": png, "rooms": [png, ...4], "nook": png, "vo": [...] (optional)}
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reel_campaign import CREAM, INK, grade, load, put, text_layer  # noqa: E402
from reel_campaign2 import pan, transition, wrap  # noqa: E402
from reel_how_it_works import ease_io, ease_out, font  # noqa: E402

W, H, FPS = 1080, 1920, 30
BPM = 112
BEAT = 60 / BPM
SHOTS = [("hook", 4), ("r0", 1), ("r1", 1), ("r2", 1), ("r3", 1), ("prize", 5), ("how", 6), ("end", 6)]
TRANS = {"r0": "flash", "prize": "doors", "how": "push_left", "end": "circle"}


class Reel:
    def __init__(self, A):
        self.hero = load(A["hero"])
        self.rooms = [load(p) for p in A["rooms"]]
        self.nook = load(A["nook"])
        self.f = {"hand": font("GveretLevin.ttf", 128), "hand2": font("GveretLevin.ttf", 96),
                  "lab": font("Heebo.ttf", 52, 500), "big": font("Heebo.ttf", 64, 500), "sub": font("Heebo.ttf", 44, 400),
                  "date": font("Heebo.ttf", 150, 500)}

    def hook(self, t, d):
        fr = grade(pan(self.hero, t, .5, .5, dy=-.05, zoom=1.08))
        tt = t * d
        l1 = text_layer(["מתנה לעוקבות"], [self.f["hand"]], INK, pill=(*CREAM, 225))
        a = ease_out((tt - .05) / .3)
        return put(fr, l1, 300, a, -30 * (1 - a))

    def _room(self, i, t):
        moves = [dict(dx=.12), dict(dy=.1), dict(dx=-.12), dict(dy=-.1)]
        fr = grade(pan(self.rooms[i], t, .5, .5, zoom=1.14, **moves[i]))
        lay = text_layer(["3 מייקאוברים", "לחדר ילדים"], [self.f["hand2"]] * 2, INK, pill=(*CREAM, 225), gap=1.0)
        return put(fr, lay, 1200, 1.0)

    def r0(self, t, d): return self._room(0, t)
    def r1(self, t, d): return self._room(1, t)
    def r2(self, t, d): return self._room(2, t)
    def r3(self, t, d): return self._room(3, t)

    def prize(self, t, d):
        fr = grade(pan(self.nook, t, .5, .5, dx=.08, zoom=1.1))
        tt = t * d
        l1 = text_layer(["אני מגיעה אליכן", "ומעצבת את החדר"], [self.f["big"]] * 2, INK, pill=(*CREAM, 230), gap=1.15)
        l2 = text_layer(["+ 1,000 ₪ לקניות, עליי"], [self.f["big"]], CREAM, pill=(*INK, 240))
        a = ease_out((tt - .05) / .3)
        fr = put(fr, l1, 1040, a, 30 * (1 - a))
        b = ease_out((tt - .9) / .3)
        return put(fr, l2, 1290, b, 30 * (1 - b))

    def how(self, t, d):
        bg = np.empty((H, W, 3), np.float32)
        bg[:] = (240, 238, 231)
        tt = t * d
        fr = put(bg, text_layer(["איך משתתפות?"], [self.f["hand"]], INK), 330, ease_out(tt / .25))
        steps = ["1  עוקבות אחריי", "2  מספרות בתגובה בפוסט", "למה החדר צריך מייקאובר", "3  משתפות בסטורי (בונוס)"]
        ys = [620, 800, 880, 1060]
        for k, (s, y) in enumerate(zip(steps, ys)):
            st = .35 + (k if k < 2 else k - 1) * .45
            a = ease_out((tt - st) / .25)
            fnt = self.f["sub"] if k == 2 else self.f["big"]
            fr = put(fr, text_layer([s], [fnt], INK if k != 2 else (110, 100, 90)), y, a, 24 * (1 - a))
        return fr

    def end(self, t, d):
        fr = grade(pan(self.hero, t, .5, .5, dx=-.05, zoom=1.08))
        fr = fr * .45 + np.array(CREAM, np.float32) * .55
        tt = t * d
        l0 = text_layer(["עד"], [self.f["sub"]], INK)
        l1 = text_layer(["26.11"], [self.f["date"]], INK)
        l2 = text_layer(["כל הפרטים בפוסט"], [self.f["sub"]], CREAM, pill=(*INK, 240))
        l3 = text_layer(["⁦@roomstorytell_⁩"], [self.f["sub"]], INK)
        a = ease_out((tt - .05) / .3)
        fr = put(fr, l0, 560, a)
        fr = put(fr, l1, 640, a, 40 * (1 - a))
        fr = put(fr, l2, 960, ease_out((tt - .5) / .3))
        return put(fr, l3, 1100, ease_out((tt - .8) / .3))


def render(A, out, plan=None):
    rl = Reel(A)
    beats = dict(SHOTS, **A.get("beats", {}))
    shots = [(n, beats[n] * BEAT) for n, _ in SHOTS]
    starts = np.concatenate([[0], np.cumsum([d for _, d in shots])[:-1]])
    names = [n for n, _ in shots]
    total = float(starts[-1] + shots[-1][1])
    n = int(round(total * FPS))
    grain = [np.random.default_rng(k).normal(0, 2.4, (H // 2, W // 2, 1)).astype(np.float32) for k in range(6)]
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
                             "-preset", "slow", "-crf", "19", "-maxrate", "9M", "-bufsize", "14M", "-movflags", "+faststart", out],
                            stdin=subprocess.PIPE)
    TW = .24

    def shot(i, tt):
        name, d = shots[i]
        return getattr(rl, name)(min(max(tt, 0), d) / d, d)
    for f in range(n):
        t = f / FPS
        i = int(np.searchsorted(starts, t, side="right") - 1)
        fr = shot(i, t - starts[i])
        for j in (i, i + 1):
            if 0 < j < len(shots) and names[j] in TRANS:
                c = starts[j]
                if c - TW / 2 <= t < c + TW / 2:
                    fr = transition(TRANS[names[j]], shot(j - 1, t - starts[j - 1]), shot(j, max(t - c, 0)), (t - (c - TW / 2)) / TW)
        fr = fr + cv2.resize(grain[f % 6], (W, H))[..., None]
        proc.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
    proc.stdin.close()
    proc.wait()
    print(f"wrote {out} ({total:.2f}s)")
    if plan:
        idx = {k: v for v, k in enumerate(names)}
        json.dump({"bpm": BPM, "scenes": [beats[n] for n, _ in SHOTS], "vo": A.get("vo", []),
                   "whooshes": [idx["prize"], idx["how"], idx["end"]],
                   "thuds": [[idx[k], 0.0] for k in ("r0", "r1", "r2", "r3")],
                   "pops": [[idx["how"], .35 + .45 * k] for k in range(3)] + [[idx["prize"], .9]],
                   "sparkle": [idx["hook"], 0.05]}, open(plan, "w"))


if __name__ == "__main__":
    render(json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
