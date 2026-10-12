"""Unified Reel covers for the profile grid (editorial cream card + Hebrew serif title).

Usage: covers.py SPEC.json OUT_DIR
SPEC is a list of {"name", "src", "label", "title", "crop": [x0, y0, w] (normalised,
card-aspect height derived), "clean_yellow": bool (inpaint burned-in yellow text)}.
Writes OUT_DIR/<name>.jpg at 1080x1920. The profile grid shows the central 3:4
window (y 240..1680), so title and card both sit inside it.
"""
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
BG = (241, 235, 227)
INK = (63, 52, 44)
TAUPE = (154, 134, 118)
CARD = (90, 650, 990, 1610)  # 900x960, inside the 3:4 grid window
FONTS = os.path.expanduser("~/.fonts")


def font(name, size, weight):
    f = ImageFont.truetype(os.path.join(FONTS, name), size, layout_engine=ImageFont.Layout.RAQM)
    f.set_variation_by_axes([weight])
    return f


def clean_yellow(img, keep=None):
    """Remove bright yellow burned-in captions from a flat backdrop.

    keep: normalised box (x0, y0, x1, y1) around the person. GrabCut separates
    them from the backdrop; caption pixels outside the person are refilled from
    a smooth backdrop estimated only from clean background pixels, so scarf and
    hair colours never bleed into the patch.
    """
    a = np.array(img)[..., ::-1].copy()
    h, w = a.shape[:2]
    hsv = cv2.cvtColor(a, cv2.COLOR_BGR2HSV)
    text = cv2.inRange(hsv, (15, 70, 150), (40, 255, 255))
    text[int(h * 0.6):] = 0
    text = cv2.dilate(text, np.ones((5, 5), np.uint8), iterations=3) > 0

    person = np.zeros((h, w), bool)
    if keep:
        x0, y0, x1, y1 = (int(v * s) for v, s in zip(keep, (w, h, w, h)))
        gc = np.full((h, w), cv2.GC_BGD, np.uint8)
        gc[y0:y1, x0:x1] = cv2.GC_PR_FGD
        gc[(text) & (gc == cv2.GC_PR_FGD)] = cv2.GC_PR_BGD
        bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
        cv2.grabCut(a, gc, None, bgd, fgd, 6, cv2.GC_INIT_WITH_MASK)
        person = np.isin(gc, (cv2.GC_FGD, cv2.GC_PR_FGD))
        person = cv2.erode(person.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0

    m = text & ~person
    clean = (~text & ~person).astype(np.float32)
    num = cv2.GaussianBlur(a.astype(np.float32) * clean[..., None], (0, 0), 14)
    den = cv2.GaussianBlur(clean, (0, 0), 14)[..., None]
    fill = num / np.maximum(den, 1e-3)
    # far from any clean pixel: fall back to a much wider estimate
    num2 = cv2.GaussianBlur(a.astype(np.float32) * clean[..., None], (0, 0), 80)
    den2 = cv2.GaussianBlur(clean, (0, 0), 80)[..., None]
    t = np.clip(den / 0.15, 0, 1)
    fill = fill * t + num2 / np.maximum(den2, 1e-4) * (1 - t)
    fill += np.random.default_rng(3).normal(0, 1.8, fill.shape)  # match sensor noise
    soft = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.2)[..., None]
    a = (a * (1 - soft) + fill * soft).clip(0, 255).astype(np.uint8)
    return Image.fromarray(a[..., ::-1])


def grade(img):
    """Shared warm, soft-contrast grade so every cover reads as one family."""
    a = np.asarray(img).astype(np.float32) / 255
    a = 0.04 + a * 0.93                      # lift blacks, soften whites
    a = a * np.array([1.025, 1.0, 0.965])    # gentle warmth
    lum = a.mean(axis=2, keepdims=True)
    a = lum + (a - lum) * 0.9                # slight desaturation
    return Image.fromarray((a.clip(0, 1) * 255).astype(np.uint8))


def card_image(spec):
    img = Image.open(spec["src"]).convert("RGB")
    if spec.get("clean_yellow"):
        img = clean_yellow(img, spec.get("keep"))
    cw, ch = CARD[2] - CARD[0], CARD[3] - CARD[1]
    x0, y0, w = spec["crop"]
    sw, sh = img.size
    pw = w * sw
    ph = pw * ch / cw
    box = (x0 * sw, y0 * sh, x0 * sw + pw, y0 * sh + ph)
    img = img.crop(tuple(round(v) for v in box)).resize((cw, ch), Image.LANCZOS)
    if pw < cw * 0.7:  # heavy upscale: recover a little crispness
        img = img.filter(ImageFilter.UnsharpMask(radius=2.2, percent=70, threshold=2))
    return grade(img)


def render(spec, out):
    rng = np.random.default_rng(7)
    grain = rng.normal(0, 2.2, (H, W, 1))
    canvas = Image.fromarray((np.array(BG, np.float32) + grain).clip(0, 255).astype(np.uint8))

    # soft card shadow
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).rectangle((CARD[0], CARD[1] + 18, CARD[2], CARD[3] + 18), fill=70)
    sh = sh.filter(ImageFilter.GaussianBlur(28))
    canvas = Image.composite(Image.new("RGB", (W, H), (120, 100, 85)), canvas, sh)
    canvas.paste(card_image(spec), CARD[:2])

    d = ImageDraw.Draw(canvas)
    lab = font("Heebo.ttf", 38, 400)
    d.text((W / 2, 330), spec["label"], font=lab, fill=TAUPE, anchor="mm",
           direction="rtl", language="he")
    d.line((W / 2 - 40, 378, W / 2 + 40, 378), fill=TAUPE, width=2)

    tf = font("FrankRuhlLibre.ttf", 92, 600)
    lines = spec["title"].split("\n")
    lh = 112
    y = 505 - (len(lines) - 1) * lh / 2
    for ln in lines:
        d.text((W / 2, y), "\u200f" + ln, font=tf, fill=INK, anchor="mm", direction="rtl", language="he")
        y += lh
    canvas.save(out, quality=95, subsampling=0)


def main():
    specs = json.load(open(sys.argv[1], encoding="utf-8"))
    os.makedirs(sys.argv[2], exist_ok=True)
    for s in specs:
        render(s, os.path.join(sys.argv[2], s["name"] + ".jpg"))
        print("wrote", s["name"])


if __name__ == "__main__":
    main()
