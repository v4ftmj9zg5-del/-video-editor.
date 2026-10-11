"""B-roll: match the user's own photos/renders/clips to what is being said.

Files in the B-roll folder are tagged by their file name, e.g.
  ספה-סלון.jpg   sofa_living.png   מנורה.mp4   צמחים-plant.webp
A tag matches a spoken word with or without a Hebrew prefix (ה, ו, ב, ל, מ, ש, כ),
so "הספה", "בסלון" and "לצמחים" match the files above.
"""
import os
import re

import cv2
import numpy as np

from .cuts import norm, to_out

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm"}
PREFIXES = "הובלמשכ"
W, H = 1080, 1920


def stems(word):
    """The word plus versions with up to two Hebrew prefix letters removed."""
    out = {word}
    w = word
    for _ in range(2):
        if len(w) > 3 and w[0] in PREFIXES:
            w = w[1:]
            out.add(w)
    # plural / construct endings
    for suf in ("ים", "ות"):
        for x in list(out):
            if x.endswith(suf) and len(x) > 4:
                out.add(x[:-2])
    return out


def library(folder):
    items = []
    if not folder or not os.path.isdir(folder):
        return items
    for f in sorted(os.listdir(folder)):
        base, ext = os.path.splitext(f)
        if ext.lower() not in IMAGE_EXT | VIDEO_EXT:
            continue
        tags = {t.lower() for t in re.split(r"[-_ ,.]+", base) if t and not t.isdigit()}
        items.append(dict(path=os.path.join(folder, f), tags=tags,
                          video=ext.lower() in VIDEO_EXT))
    return items


def place(phrases, timeline, items, preset, out_dur, log=print):
    """[(out_start, out_end, item, keyword)] — each file used at most once,
    spaced apart, never in the first 1.2 s (the hook) or past the end."""
    used, placed = set(), []
    for ph in phrases:
        for w in ph["words"]:
            if not norm(w["w"]):
                continue
            word = norm(w["w"])[0].lower()
            cands = stems(word)
            for it in items:
                if it["path"] in used or not (cands & {s for t in it["tags"] for s in stems(t)}):
                    continue
                t = to_out(timeline, w["s"])
                if t is None or t < 1.2:
                    continue
                t = max(1.2, t - 0.1)
                if placed and t < max(placed[-1][0] + preset["broll_min_gap"], placed[-1][1] + 0.5):
                    continue
                e = min(t + preset["broll_dur"], out_dur - 0.3)
                if e - t < 0.8:
                    continue
                placed.append((t, e, it, w["w"]))
                used.add(it["path"])
                log(f"  B-roll {os.path.basename(it['path'])} at {t:.2f}-{e:.2f}s (word {w['w']!r})")
                break
    return placed


def cover(img, w=W, h=H, scale=1.0):
    ih, iw = img.shape[:2]
    s = max(w / iw, h / ih) * scale
    r = cv2.resize(img, (int(np.ceil(iw * s)), int(np.ceil(ih * s))), interpolation=cv2.INTER_AREA)
    y, x = (r.shape[0] - h) // 2, (r.shape[1] - w) // 2
    return r[y:y + h, x:x + w]


class Source:
    """Frames of one B-roll item, already covering 1080x1920 with some margin
    for the camera move."""

    MARGIN = 1.15

    def __init__(self, item, n_frames, fps):
        if item["video"]:
            import subprocess
            raw = subprocess.check_output([
                "ffmpeg", "-v", "error", "-i", item["path"], "-t", f"{n_frames / fps + 0.2:.3f}",
                "-vf", f"fps={fps},scale={int(W * self.MARGIN)}:{int(H * self.MARGIN)}:"
                       "force_original_aspect_ratio=increase,"
                       f"crop={int(W * self.MARGIN)}:{int(H * self.MARGIN)}",
                "-f", "rawvideo", "-pix_fmt", "bgr24", "-"])
            fs = int(W * self.MARGIN) * int(H * self.MARGIN) * 3
            self.frames = [np.frombuffer(raw[i:i + fs], np.uint8).reshape(int(H * self.MARGIN), int(W * self.MARGIN), 3)
                           for i in range(0, len(raw) - fs + 1, fs)]
        else:
            img = cv2.imread(item["path"])
            self.frames = [cover(img, int(W * self.MARGIN), int(H * self.MARGIN))]

    def frame(self, i):
        return self.frames[min(i, len(self.frames) - 1)]
