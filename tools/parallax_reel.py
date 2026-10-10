"""Cinematic 9:16 reel from stills using depth-based 3D camera moves.

Needs the output of prep_assets.py (upscaled image + disparity map per still).
Each shot is a virtual camera: crop pan/zoom plus a real camera translation
that produces depth parallax, depth-of-field with focus pulls, and optional
breeze motion on curtain regions. Shots are joined with cuts/dissolves and
given a shared warm cinematic grade.

Usage: parallax_reel.py ASSETS_DIR OUT.mp4
"""
import subprocess
import sys

import cv2
import numpy as np

W, H, FPS = 1080, 1920, 30
SRC_SCALE = 3  # prep_assets upscale factor; shot coords below are in original px
ZN, ZF = 1.0, 4.0  # depth range mapped from disparity
rng = np.random.default_rng(3)


def ease(t):
    return t * t * t * (t * (6 * t - 15) + 10)  # smootherstep


def lerp(a, b, t):
    return np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * t


# ---------------------------------------------------------------- grading
# per-image white balance (BGR gain) so the grey Homestyler renders match
BALANCE = {
    "dining": (1.0, 1.0, 1.0, 1.0),
    "living": (1.0, 1.0, 1.0, 1.0),
    "day": (0.9, 1.0, 1.1, 1.25),
    "table": (0.88, 1.0, 1.12, 1.35),
    "chair": (0.88, 1.0, 1.12, 1.5),
    "sconce": (0.88, 1.0, 1.12, 1.35),
}

# Shots. Coordinates are in ORIGINAL image pixels:
#   a/b      crop (cx, cy, h) at start/end
#   t0/t1    camera translation (tx, ty, tz) in depth units at start/end
#   focus    (x, y) start/end focus points, dof = blur strength
#   sway     curtain regions (x0, x1, y0, y1, feather)
SHOTS = [
    dict(img="dining", dur=3.2, a=(1150, 440, 820), b=(880, 440, 800),
         t0=(0.10, 0, 0), t1=(-0.10, 0, 0.12), focus=((880, 420), (880, 420)), dof=3,
         sway=[(1345, 1774, 0, 887, 40)]),
    dict(img="dining", dur=2.6, a=(830, 330, 470), b=(830, 345, 410),
         t0=(0, 0, 0), t1=(0, 0, 0.12), focus=((825, 160), (830, 380)), dof=7, cut="dissolve"),
    dict(img="living", dur=3.0, a=(470, 440, 860), b=(620, 450, 830),
         t0=(0.09, 0, 0), t1=(-0.09, 0, 0.06), focus=((620, 690), (620, 690)), dof=4,
         sway=[(0, 590, 0, 887, 45)]),
    dict(img="sconce", dur=2.8, a=(700, 450, 860), b=(980, 440, 800),
         t0=(0.06, 0, 0), t1=(-0.06, 0, 0.05), focus=((420, 300), (900, 700)), dof=8),
    dict(img="chair", dur=2.6, a=(480, 500, 1060), b=(470, 620, 900),
         t0=(0, -0.05, 0), t1=(0, 0.05, 0.1), focus=((450, 720), (450, 760)), dof=6),
    dict(img="table", dur=2.6, a=(500, 560, 1120), b=(560, 650, 860),
         t0=(0, 0, 0), t1=(0, 0, 0.12), rot=(-3.0, 2.0), focus=((565, 690), (565, 690)), dof=6),
    dict(img="living", dur=2.8, a=(1330, 440, 860), b=(1180, 450, 840),
         t0=(-0.08, 0, 0.04), t1=(0.08, 0, 0), focus=((1350, 380), (1350, 380)), dof=4,
         cut="dissolve"),
    dict(img="dining", dur=3.8, a=(880, 420, 620), b=(880, 440, 840),
         t0=(0, 0, 0.18), t1=(0, 0, 0), focus=((880, 420), (880, 420)), dof=3,
         sway=[(1345, 1774, 0, 887, 40)]),
]
DISSOLVE = 10  # frames


class Asset:
    def __init__(self, d, name):
        bgr = cv2.imread(f"{d}/{name}.png").astype(np.float32)
        b, g, r, gain = BALANCE[name]
        self.img = np.clip(bgr * np.array([b, g, r], np.float32) * gain, 0, 255)
        disp = np.load(f"{d}/{name}_depth.npy")
        # grow foreground edges so objects move as solid shapes
        disp = cv2.dilate(disp, np.ones((9, 9), np.uint8))
        disp = cv2.GaussianBlur(disp, (0, 0), 3)
        self.disp = disp
        self.Z = 1.0 / (disp * (1 / ZN - 1 / ZF) + 1 / ZF)


def sample(img, mx, my, interp=cv2.INTER_LINEAR):
    return cv2.remap(img, mx.astype(np.float32), my.astype(np.float32), interp,
                     borderMode=cv2.BORDER_REFLECT)


def render_shot(s, assets, gx, gy):
    A = assets[s["img"]]
    n = int(round(s["dur"] * FPS))
    k = SRC_SCALE
    r0, r1 = s.get("rot", (0.0, 0.0))
    drift = rng.uniform(0, 2 * np.pi, 4)
    (fa, fb) = s["focus"]
    for i in range(n):
        e = ease(i / (n - 1))
        cx, cy, ch = lerp(s["a"], s["b"], e) * k
        tx, ty, tz = lerp(s["t0"], s["t1"], e)
        tsec = i / FPS
        # tiny gimbal float so nothing feels locked-off
        cx += np.sin(0.7 * tsec + drift[0]) * ch * 0.002
        cy += np.sin(0.5 * tsec + drift[1]) * ch * 0.002
        rot = np.deg2rad(lerp(r0, r1, e) + 0.15 * np.sin(0.4 * tsec + drift[2]))
        sc = ch / H * 0.97
        # output grid -> base source coords (rotation about crop centre)
        ox, oy = gx * sc, gy * sc
        u0 = cx + ox * np.cos(rot) - oy * np.sin(rot)
        v0 = cy + ox * np.sin(rot) + oy * np.cos(rot)
        # inverse parallax warp (fixed-point iteration on depth)
        f = ch * 1.1
        u, v = u0.copy(), v0.copy()
        for _ in range(5):
            Z = sample(A.Z, u, v)
            x, y = (u - cx) / f, (v - cy) / f
            du = f * ((x * Z - tx) / (Z - tz) - x)
            dv = f * ((y * Z - ty) / (Z - tz) - y)
            u, v = u0 - du, v0 - dv
        # curtain breeze: travelling wave, stronger toward the hem
        for (x0, x1, y0, y1, fe) in s.get("sway", []):
            x0, x1, y0, y1, fe = (c * k for c in (x0, x1, y0, y1, fe))
            m = np.clip((u - x0) / fe, 0, 1) * np.clip((x1 - u) / fe, 0, 1)
            m *= np.clip((v - y0) / (y1 - y0), 0, 1) ** 1.5
            wave = (np.sin(2 * np.pi * (u / (180 * k) - 0.45 * tsec))
                    + 0.5 * np.sin(2 * np.pi * (u / (70 * k) + 0.8 * tsec) + 1.3))
            gust = 0.6 + 0.4 * np.sin(2 * np.pi * 0.25 * tsec)
            u = u + m * wave * gust * 6 * k
        frame = sample(A.img, u, v, cv2.INTER_CUBIC)
        # depth of field around the (moving) focus point
        if s.get("dof"):
            fx, fy = lerp(fa, fb, ease(min(1, max(0, (i / (n - 1) - 0.15) / 0.6)))) * k
            fd = float(np.median(A.disp[int(fy) - 8:int(fy) + 8, int(fx) - 8:int(fx) + 8]))
            d = sample(A.disp, u, v)
            coc = np.clip(np.abs(d - fd) * s["dof"] * 4, 0, 4)  # blur level 0..4
            levels = [frame] + [cv2.GaussianBlur(frame, (0, 0), sg) for sg in (1.5, 3.5, 6, 9)]
            lo = np.floor(coc).astype(int)
            fr = (coc - lo)[..., None]
            out = np.zeros_like(frame)
            for L in range(5):
                wgt = ((lo == L) * (1 - fr[..., 0]) + (lo == L - 1) * fr[..., 0])[..., None]
                out += levels[L] * wgt
            frame = out
        yield frame


def grade(f, vig, t):
    f = f / 255.0
    # gentle bloom on highlights
    hi = np.clip((f - 0.7) / 0.3, 0, 1)
    f = f + cv2.GaussianBlur(hi, (0, 0), 25) * 0.18
    # soft S-curve, lifted blacks, warm highlights
    f = np.clip(f, 0, 1)
    f = f + 0.25 * f * (1 - f) * (2 * f - 1)  # S-curve: deeper shadows, brighter highs
    f = f * 0.95 + 0.025
    lum = f.mean(axis=2, keepdims=True)
    f = f + np.array([-0.015, 0.0, 0.012]) * lum
    f *= vig[..., None]
    # fine luminance grain
    g = rng.normal(0, 0.012, (H, W)).astype(np.float32)
    f += g[..., None]
    return (np.clip(f, 0, 1) * 255).astype(np.uint8)


def sharpen(f):
    b = cv2.GaussianBlur(f, (0, 0), 1.2)
    return cv2.addWeighted(f, 1.35, b, -0.35, 0)


def main(assets_dir, out):
    names = {s["img"] for s in SHOTS}
    assets = {nm: Asset(assets_dir, nm) for nm in names}
    gy, gx = np.mgrid[0:H, 0:W].astype(np.float32)
    gx -= W / 2
    gy -= H / 2
    r = np.sqrt((gx / (W / 2)) ** 2 + (gy / (H / 2)) ** 2)
    vig = (1 - 0.22 * np.clip(r - 0.5, 0, None) ** 1.5).astype(np.float32)
    total_frames = sum(int(round(s["dur"] * FPS)) for s in SHOTS) \
        - DISSOLVE * sum(1 for s in SHOTS if s.get("cut") == "dissolve")
    total = total_frames / FPS
    ff = subprocess.Popen(
        ["ffmpeg", "-loglevel", "error", "-y",
         "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
         "-vf", f"fade=in:st=0:d=0.5,fade=out:st={total - 0.6:.3f}:d=0.6",
         "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
         "-profile:v", "high", "-movflags", "+faststart",
         "-c:a", "aac", "-shortest", out],
        stdin=subprocess.PIPE)
    tail = []  # last frames of previous shot, held back for dissolves
    fi = 0
    for si, s in enumerate(SHOTS):
        frames = render_shot(s, assets, gx, gy)
        nxt_dissolve = si + 1 < len(SHOTS) and SHOTS[si + 1].get("cut") == "dissolve"
        n = int(round(s["dur"] * FPS))
        buf = []
        for i, f in enumerate(frames):
            f = sharpen(f)
            if tail and i < DISSOLVE:
                a = ease((i + 1) / (DISSOLVE + 1))
                f = tail[i] * (1 - a) + f * a
            if i == DISSOLVE - 1 and tail:
                tail = []
            if nxt_dissolve and i >= n - DISSOLVE:
                buf.append(f)
                continue
            ff.stdin.write(grade(f, vig, fi / FPS).tobytes())
            fi += 1
        tail = buf
        print(f"shot {si + 1}/{len(SHOTS)} done", flush=True)
    ff.stdin.close()
    ff.wait()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
