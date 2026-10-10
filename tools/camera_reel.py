"""Turn still interior renders into a 9:16 "handheld camera" reel.

Each shot is a virtual camera moving over a still image: eased pans/push-ins,
smooth handheld shake, optional autofocus pull, whip-pan transitions,
then a shared warm grade, vignette and film grain.
"""
import subprocess
import sys

import cv2
import numpy as np

W, H, FPS = 1080, 1920, 30
UP = "/root/.claude/uploads/d30f61ec-3c55-5ef0-9593-d1592e986dc7/"
rng = np.random.default_rng(7)


def ease(t):
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


class Shake:
    """Smooth pseudo-random handheld motion (sum of slow sines)."""

    def __init__(self, amp=1.0):
        self.f = rng.uniform(0.25, 1.6, (3, 4))
        self.p = rng.uniform(0, 2 * np.pi, (3, 4))
        self.amp = amp

    def __call__(self, t):
        v = (np.sin(2 * np.pi * self.f * t + self.p) / np.arange(1, 5)).sum(1)
        return v * self.amp  # dx, dy (fraction of crop h), rot (deg scale)


def load(name, gain=1.0, warm=(1.0, 1.0, 1.0)):
    im = cv2.imread(UP + name + "-image.png").astype(np.float32)
    im *= np.array(warm, np.float32) * gain  # BGR multipliers
    return np.clip(im, 0, 255)


# Grey Homestyler renders get lifted and warmed to match the warm renders.
GREY = dict(gain=1.35, warm=(0.88, 1.0, 1.12))
IMG = {
    "dining": load("d9a7e0f8"),
    "living": load("2eb10629"),
    "day": load("f6a2f5b4", gain=1.25, warm=(0.9, 1.0, 1.1)),
    "table": load("f9b38b01", **GREY),
    "chair": load("d6bf0d4f", gain=1.55, warm=(0.88, 1.0, 1.12)),
    "sconce": load("82084be0", **GREY),
}

# Each shot: image, seconds, start/end (cx, cy, crop_h) in source px.
# Crops are kept clear of the bottom-right corner of the Homestyler renders.
SHOTS = [
    dict(img="dining", dur=3.0, a=(560, 443, 887), b=(900, 450, 860), whip_out=+1),
    dict(img="living", dur=2.6, a=(700, 470, 860), b=(800, 520, 720), whip_in=+1),
    dict(img="sconce", dur=2.3, a=(900, 430, 840), b=(1010, 440, 800), focus=0.7),
    dict(img="chair", dur=2.2, a=(470, 470, 1080), b=(470, 600, 900)),
    dict(img="table", dur=2.4, a=(470, 560, 1150), b=(540, 640, 880), rot=(-2.0, 1.5), whip_out=-1),
    dict(img="day", dur=2.2, a=(420, 370, 720), b=(760, 380, 700), whip_in=-1),
    dict(img="dining", dur=3.2, a=(880, 430, 600), b=(880, 445, 887)),
]

WHIP = 6  # frames on each side of a whip pan


def render_shot(s):
    src = IMG[s["img"]]
    sh_, sw_ = src.shape[:2]
    n = int(s["dur"] * FPS)
    shake = Shake()
    r0, r1 = s.get("rot", (0.0, 0.0))
    for i in range(n):
        t = i / (n - 1)
        e = ease(t)
        cx, cy, ch = (lerp(a, b, e) for a, b in zip(s["a"], s["b"]))
        dx, dy, dr = shake(i / FPS)
        cx += dx * ch * 0.006
        cy += dy * ch * 0.006
        rot = lerp(r0, r1, e) + dr * 0.25
        blur_x = 0.0
        # whip pans: fling the camera sideways with motion blur
        if s.get("whip_out") and i >= n - WHIP:
            k = (i - (n - WHIP) + 1) / WHIP
            cx += s["whip_out"] * ch * 0.9 * k**2
            blur_x = 120 * k
        if s.get("whip_in") and i < WHIP:
            k = 1 - i / WHIP
            cx -= s["whip_in"] * ch * 0.9 * k**2
            blur_x = 120 * k
        cw = ch * W / H
        # keep the crop inside the image
        cx = np.clip(cx, cw / 2, sw_ - cw / 2) if not blur_x else cx
        cy = np.clip(cy, ch / 2, sh_ - ch / 2)
        sc = H / ch * 1.04  # margin so shake/rotation never shows edges
        M = cv2.getRotationMatrix2D((cx, cy), rot, sc)
        M[0, 2] += W / 2 - cx
        M[1, 2] += H / 2 - cy
        f = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LANCZOS4,
                           borderMode=cv2.BORDER_REFLECT)
        if blur_x > 2:
            k = int(blur_x) | 1
            ker = np.zeros((k, k), np.float32)
            ker[k // 2, :] = 1 / k
            f = cv2.filter2D(f, -1, ker)
        fs = s.get("focus")
        if fs and i / FPS < fs:
            sig = 9 * (1 - ease(i / FPS / fs)) ** 1.5
            if sig > 0.3:
                f = cv2.GaussianBlur(f, (0, 0), sig)
        yield f


def grade(f, vig):
    # gentle sharpen to offset upscaling
    b = cv2.GaussianBlur(f, (0, 0), 1.6)
    f = cv2.addWeighted(f, 1.45, b, -0.45, 0)
    f /= 255.0
    f = f * 0.94 + 0.03  # slightly lifted blacks, soft highlights
    f = f + 0.08 * (f - f**2) * 2  # soft S-ish contrast
    f *= vig[..., None]
    g = rng.normal(0, 0.018, (H // 2, W // 2)).astype(np.float32)
    f += cv2.resize(g, (W, H))[..., None]
    return (np.clip(f, 0, 1) * 255).astype(np.uint8)


def main(out):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    vig = (1 - 0.28 * np.clip(r - 0.45, 0, None) ** 1.6).astype(np.float32)
    total = sum(s["dur"] for s in SHOTS)
    ff = subprocess.Popen(
        ["ffmpeg", "-loglevel", "error", "-y",
         "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-f", "lavfi", "-t", str(total), "-i", "anullsrc=r=48000:cl=stereo",
         "-vf", f"fade=in:st=0:d=0.4,fade=out:st={total - 0.5}:d=0.5",
         "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
         "-profile:v", "high", "-movflags", "+faststart",
         "-c:a", "aac", "-shortest", out],
        stdin=subprocess.PIPE)
    for s in SHOTS:
        for f in render_shot(s):
            ff.stdin.write(grade(f, vig).tobytes())
    ff.stdin.close()
    ff.wait()


if __name__ == "__main__":
    main(sys.argv[1])
