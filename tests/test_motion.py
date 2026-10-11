"""Check that every storyboard scene is actually visible and animated in a rendered Reel.

Usage: test_motion.py FINAL.mp4 WORK_DIR [SHEET.png]

WORK_DIR is the --keep-work folder of make_reel.py (needs base.mp4 and storyboard.json).
For each scene:
  visible  - the final frame differs clearly from the base video at the same time
             (mean abs difference over the frame, so a caption alone does not pass)
  animated - two frames inside the scene differ in the overlay (motion, not a still card)
Writes a contact sheet (three frames per scene) when SHEET.png is given.
"""
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
VISIBLE = 18.0    # mean abs diff (0-255) final vs base; captions alone give ~5-9
ANIMATED = 4.0    # mean abs diff of the overlay between two in-scene frames


def frame(path, t):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                                   "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    return np.frombuffer(raw, np.uint8).reshape(H, W, 3).astype(np.float32)


def diff(a, b):
    return float(np.abs(a - b).mean())


def check(final, work):
    scenes = json.load(open(os.path.join(work, "storyboard.json")))["scenes"]
    base = os.path.join(work, "base.mp4")
    rows = []
    for s in scenes:
        d = s["e"] - s["s"]
        ts = [s["s"] + d * k for k in (0.3, 0.55, 0.85)]
        fin = [frame(final, t) for t in ts]
        bas = [frame(base, t) for t in ts]
        vis = max(diff(f, b) for f, b in zip(fin, bas))
        # overlay = final - base; compare overlay at two moments so camera motion in the base is ignored
        anim = diff(fin[0] - bas[0], fin[2] - bas[2])
        rows.append(dict(kind=s["kind"], s=s["s"], e=s["e"], visible=vis, animated=anim,
                         ok=vis >= VISIBLE and anim >= ANIMATED, frames=fin))
    return rows


def sheet(rows, out, thumb=270):
    th = int(thumb * H / W)
    img = Image.new("RGB", (thumb * 3 + 280, (th + 10) * len(rows)), "#111")
    dr = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "remotion", "public", "fonts", "Rubik.ttf"), 26)
    except OSError:
        font = ImageFont.load_default()
    for i, r in enumerate(rows):
        y = i * (th + 10)
        for j, f in enumerate(r["frames"]):
            img.paste(Image.fromarray(f.astype(np.uint8)).resize((thumb, th)), (j * thumb, y))
        x = thumb * 3 + 14
        dr.text((x, y + 10), r["kind"], fill="#FFD947", font=font)
        dr.text((x, y + 46), f"{r['s']:.1f}-{r['e']:.1f}s", fill="#ddd", font=font)
        dr.text((x, y + 82), f"vis {r['visible']:.0f}", fill="#ddd", font=font)
        dr.text((x, y + 118), f"anim {r['animated']:.0f}", fill="#ddd", font=font)
        dr.text((x, y + 154), "OK" if r["ok"] else "FAIL", fill="#7CFC9A" if r["ok"] else "#FF6B6B", font=font)
    img.save(out)


def main(final, work, out=None):
    rows = check(final, work)
    kinds = set()
    for r in rows:
        print(f"{'PASS' if r['ok'] else 'FAIL'}  {r['kind']:<11} {r['s']:5.1f}-{r['e']:5.1f}s  "
              f"visible {r['visible']:5.1f}  animated {r['animated']:5.1f}")
        if r["ok"]:
            kinds.add(r["kind"])
    if out:
        sheet(rows, out)
        print("contact sheet:", out)
    ok = all(r["ok"] for r in rows) and len(kinds) >= 5
    print(f"{sum(r['ok'] for r in rows)}/{len(rows)} scenes visible and animated, "
          f"{len(kinds)} different animation types -> {'PASS' if ok else 'FAIL'}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main(*sys.argv[1:4]) else 1)
