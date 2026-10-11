"""Frame renderer: decodes the source once (sequentially), applies the style's
camera moves, cuts/dissolves, B-roll and grade, and pipes frames to FFmpeg,
which burns the captions (libass) and muxes the finished audio."""
import collections
import os
import subprocess

import cv2
import numpy as np

from .broll import Source

W, H, FPS = 1080, 1920, 30


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * t * (t * (6 * t - 15) + 10)  # smootherstep


def ease_out(t):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


class Reader:
    """Sequential decoder of the source, scaled/cropped to 9:16 at 30 fps.
    Keeps the last few frames so short look-backs (dissolves) are free."""

    def __init__(self, path):
        vf = (f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,"
              f"crop={W}:{H},setsar=1")
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", vf, "-an",
                                   "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.idx, self.cur = -1, np.zeros((H, W, 3), np.uint8)
        self.cache = collections.OrderedDict()

    def get(self, i):
        if i in self.cache:
            return self.cache[i]
        while self.idx < i:
            buf = self.p.stdout.read(W * H * 3)
            self.idx += 1
            if len(buf) == W * H * 3:  # past the end: keep repeating the last frame
                self.cur = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            self.cache[self.idx] = self.cur
            if len(self.cache) > 40:
                self.cache.popitem(last=False)
        return self.cache.get(i, self.cur)

    def close(self):
        self.p.stdout.close()
        self.p.terminate()


def zoom(img, z, cx=0.5, cy=0.42):
    """Zoom about a point (default: upper-middle, where a face usually is)."""
    if abs(z - 1) < 1e-3:
        return img
    h, w = img.shape[:2]
    cw, ch = w / z, h / z
    x0 = min(max(cx * w - cw / 2, 0), w - cw)
    y0 = min(max(cy * h - ch / 2, 0), h - ch)
    m = np.float32([[z, 0, -x0 * z], [0, z, -y0 * z]])
    return cv2.warpAffine(img, m, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def make_grade(kind):
    x = np.arange(256) / 255.0
    if kind == "punchy":
        curve = x + 0.32 * x * (1 - x) * (2 * x - 1)  # S-curve
        lut = np.clip(curve * 255, 0, 255).astype(np.uint8)
        sat, warm, vig_amt, grain = 1.10, (1.0, 1.0, 1.0), 0.10, 0.0
    else:  # editorial: soft contrast, lifted blacks, warm highlights, gentle vignette, grain
        curve = x + 0.18 * x * (1 - x) * (2 * x - 1)
        curve = curve * 0.94 + 0.03
        lut = np.clip(curve * 255, 0, 255).astype(np.uint8)
        sat, warm, vig_amt, grain = 0.93, (0.975, 1.0, 1.035), 0.20, 1.6
    gy, gx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((gx - W / 2) / (W / 2)) ** 2 + ((gy - H / 2) / (H / 2)) ** 2)
    vig = (1 - vig_amt * np.clip(r - 0.55, 0, None) ** 1.6)[..., None]
    gain = (np.array(warm, np.float32)[None, None, :] * vig).astype(np.float32)
    rng = np.random.default_rng(5)
    grains = [rng.normal(0, grain, (H, W, 1)).astype(np.float32) for _ in range(4)] if grain else None

    def apply(f, k):
        f = cv2.LUT(f, lut)
        if sat != 1.0:
            hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
            hsv[..., 1] = cv2.convertScaleAbs(hsv[..., 1], alpha=sat)
            f = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        g = f.astype(np.float32) * gain
        if grains:
            g += grains[k % 4]
        return np.clip(g, 0, 255).astype(np.uint8)
    return apply


def render(src, timeline, placements, preset, ass, audio, out, log=print):
    dur = timeline[-1]["out_e"]
    n_out = int(round(dur * FPS))
    grade = make_grade(preset["grade"])
    vf = f"ass={ass}"
    if preset["name"] == "elegant":
        vf = f"fade=in:st=0:d=0.35,fade=out:st={max(0, dur - 0.5):.3f}:d=0.5," + vf
    enc = ["ffmpeg", "-v", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", audio, "-vf", vf, "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-maxrate", "11M", "-bufsize", "22M",
           "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
           "-shortest", out]
    ff = subprocess.Popen(enc, stdin=subprocess.PIPE)
    rd = Reader(src)
    sources = {}
    tails = {}
    ci = 0
    nd = preset["cut_frames"]
    for k in range(n_out):
        t = k / FPS
        while ci < len(timeline) - 1 and t >= timeline[ci]["out_e"]:
            ci += 1
        c = timeline[ci]
        local = t - c["out_s"]
        si = int(round((c["src_s"] + local) * FPS))
        frame = rd.get(si)
        # dissolve from the previous clip's continuation into this one
        j = int(local * FPS + 1e-6)
        if nd and ci > 0 and j < nd:
            if ci not in tails:
                pe = int(round(timeline[ci - 1]["src_e"] * FPS))
                tails[ci] = [rd.get(pe + j) for j in range(nd)]
                frame = rd.get(si)
            a = ease((j + 1) / (nd + 1))
            frame = cv2.addWeighted(tails[ci][j], 1 - a, frame, a, 0)
        # camera
        z = preset["zoom_levels"][ci % 2]
        if preset["punch"] and ci > 0:
            z += preset["punch"] * (1 - ease_out(local / preset["punch_dur"]))
        if preset["drift"]:
            z += preset["drift"] * ease(t / dur)
        frame = zoom(frame, z)
        # B-roll on top
        for (b0, b1, item, _) in placements:
            if not (b0 <= t < b1):
                continue
            key = item["path"]
            if key not in sources:
                sources[key] = Source(item, int((b1 - b0) * FPS) + 2, FPS)
            p = (t - b0) / (b1 - b0)
            z0, z1 = preset["broll_zoom"]
            bz = z0 + (z1 - z0) * (ease_out(p * 2.2) if preset["broll_in"] == "hard" else ease(p))
            bimg = sources[key].frame(int((t - b0) * FPS))
            mh, mw = bimg.shape[:2]
            cw, chh = mw / bz / 1.08, mh / bz / 1.08  # 8% headroom for the pan
            # slow lateral drift for the editorial look
            pan = (p - 0.5) * 0.25 * (mw - cw) if preset["broll_in"] == "dissolve" else 0
            x0 = (mw - cw) / 2 + pan
            y0 = (mh - chh) / 2
            crop = bimg[int(y0):int(y0 + chh), int(x0):int(x0 + cw)]
            bfr = cv2.resize(crop, (W, H), interpolation=cv2.INTER_AREA)
            nf = preset["broll_fade_frames"]
            if nf:
                fi, fo = (t - b0) * FPS, (b1 - t) * FPS
                a = ease(min(fi / nf, fo / nf, 1.0))
                frame = cv2.addWeighted(frame, 1 - a, bfr, a, 0)
            else:
                frame = bfr
        frame = grade(frame, k)
        if preset["progress_bar"]:
            x1 = int(W * (k + 1) / n_out)
            ov = frame.copy()
            cv2.rectangle(ov, (0, 226), (x1, 234), (71, 217, 255), -1)
            frame = cv2.addWeighted(ov, 0.85, frame, 0.15, 0)
        ff.stdin.write(frame.tobytes())
        if k % (FPS * 5) == 0:
            log(f"  rendering {t:5.1f}/{dur:.1f}s")
    ff.stdin.close()
    rc = ff.wait()
    rd.close()
    if rc:
        raise RuntimeError("ffmpeg encode failed")
    return out


def fit_size(path, limit_mb=29.5, log=print):
    """Re-encode if the file is over Instagram-share size limit (<30 MB)."""
    size = os.path.getsize(path) / 1e6
    if size <= limit_mb:
        return size
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                         "-of", "csv=p=0", path]))
    kbps = int(limit_mb * 8000 / dur * 0.93) - 192
    tmp = path + ".fit.mp4"
    log(f"  {size:.1f} MB > {limit_mb} MB, re-encoding at {kbps} kb/s")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-c:v", "libx264", "-preset", "medium",
                    "-b:v", f"{kbps}k", "-maxrate", f"{kbps}k", "-bufsize", f"{2 * kbps}k",
                    "-profile:v", "high", "-pix_fmt", "yuv420p", "-c:a", "copy",
                    "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, path)
    return os.path.getsize(path) / 1e6
