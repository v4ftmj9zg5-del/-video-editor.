"""Empty-room 'shell' from a finished render: LaMa (ONNX) removes the furniture.

Each object box (from reel_room_build.REGIONS) is inpainted in its own square crop at
up to full resolution, so walls, mural edges and floor tiles stay sharp.

Usage: room_shell.py RENDER.png LAMA.onnx OUT_SHELL.png
"""
import os
import sys

import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reel_room_build import REGIONS, mask  # noqa: E402

REMOVE = ["rug", "crib", "chair", "dresser", "decor", "mirror", "lamp", "rod", "curtain_l", "curtain_r"]
GROW = {"crib": 22, "chair": 26, "dresser": 18, "rug": 16}   # include contact shadows


def lama(sess, img, m):
    x = cv2.resize(img, (512, 512), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    mm = (cv2.resize(m, (512, 512), interpolation=cv2.INTER_NEAREST) > .5).astype(np.float32)
    out = sess.run(None, {"image": x.transpose(2, 0, 1)[None], "mask": mm[None, None]})[0][0].transpose(1, 2, 0)
    if out.max() <= 1.5:
        out = out * 255
    return np.clip(out, 0, 255)


RAIL, BASE_TOP, FLOOR_Y = 682, 1001, 1010     # chair-rail bottom, baseboard top, floor start (render px)


def fix_lower(sess, img, orig):
    """Rebuild the pink lower wall, baseboard and floor behind crib / chair / dresser / rug."""
    h, w = img.shape[:2]
    hole = np.zeros((h, w), np.uint8)
    for name in ("crib", "chair", "dresser", "rug"):
        m = (mask((h, w), *REGIONS[name], feather=0) > .5).astype(np.uint8)
        hole |= cv2.dilate(m, np.ones((GROW[name], GROW[name]), np.uint8))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    grain = (np.random.default_rng(3).normal(0, 1.3, (h, w, 1))).astype(np.float32)

    def separable(y0, y1, x0, x1, ok, ref_x, ref_y):
        """colour(y) from the clean reference columns x ref_x, scaled by brightness(x) from rows ref_y."""
        prof = np.array([np.median(orig[y, ref_x[0]:ref_x[1]], axis=0) for y in range(y0, y1)], np.float32)
        prof = cv2.GaussianBlur(prof[:, None], (0, 0), 3)[:, 0] if len(prof) > 8 else prof
        band = orig[ref_y[0]:ref_y[1], x0:x1].mean(2)
        okb = ok[ref_y[0]:ref_y[1], x0:x1]
        col = np.array([band[:, i][okb[:, i]].mean() if okb[:, i].any() else np.nan for i in range(x1 - x0)])
        idx = np.arange(len(col))
        good = ~np.isnan(col)
        col = np.interp(idx, idx[good], col[good])
        col = cv2.GaussianBlur(col[None].astype(np.float32), (0, 0), 25)[0]
        ref = col[ref_x[0] - x0:ref_x[1] - x0].mean()
        return prof[:, None, :] * (col / ref)[None, :, None]

    clean = hole == 0
    CORNER = 1110                                   # back wall / right wall corner (render px)

    def rows_profile(y0, y1, ok, src):
        prof = np.full((y1 - y0, 3), np.nan, np.float32)
        for i, y in enumerate(range(y0, y1)):
            if ok[y].sum() > 4:
                prof[i] = np.median(src[y][ok[y]], axis=0)
        r = np.arange(y1 - y0)
        g = ~np.isnan(prof[:, 0])
        for c in range(3):
            prof[:, c] = np.interp(r, r[g], prof[g, c])
        return cv2.GaussianBlur(prof[:, None], (0, 0), 4)[:, 0]

    def cols_factor(x0, x1, y0, y1, ok, src):
        lum = src[y0:y1, x0:x1].mean(2)
        okb = ok[y0:y1, x0:x1]
        col = np.array([lum[:, i][okb[:, i]].mean() if okb[:, i].any() else np.nan for i in range(x1 - x0)])
        idx = np.arange(len(col))
        g = ~np.isnan(col)
        col = np.interp(idx, idx[g], col[g])
        col = cv2.GaussianBlur(col[None].astype(np.float32), (0, 0), 30)[0]
        return col / col.mean()

    def paint(y0, y1, x0, x1, tone, feather=2):
        m = np.zeros((h, w), np.float32)
        m[y0:y1, x0:x1] = 1
        m = cv2.GaussianBlur(m, (0, 0), feather)[..., None]
        full = np.zeros_like(img)
        full[y0:y1, x0:x1] = tone + grain[y0:y1, x0:x1]
        return img * (1 - m) + full * m

    # A. back lower wall, fully repainted so there are no patch seams
    y0, y1 = RAIL + 4, BASE_TOP
    okA = clean & (xx > 384) & (xx < CORNER)
    colA = cols_factor(384, CORNER, 690, 728, okA, orig)
    profA = rows_profile(y0, y1, okA & (xx > 734) & (xx < 776), orig)
    img = paint(y0, y1, 384, CORNER, profA[:, None, :] * colA[None, :, None])
    # B. right lower wall: same paint, slightly darker side plane
    img = paint(y0, y1, CORNER, w, np.broadcast_to(profA[:, None, :] * colA[-1] * .955, (y1 - y0, w - CORNER, 3)))
    # C. right upper wall (mirror removed): tone from the clean sliver beside the mural
    okC = (xx >= CORNER) & (xx < 1122) & clean
    profC = rows_profile(250, RAIL - 8, okC | ((xx >= CORNER) & (yy < 286)), orig)
    img = paint(250, RAIL - 8, CORNER + 2, w, np.broadcast_to(profC[:, None, :], (RAIL - 8 - 250, w - CORNER - 2, 3)), 3)
    # D. baseboard: tile the clean strip seen between crib and chair
    strip = orig[BASE_TOP:FLOOR_Y, 736:776]
    tiled = np.tile(strip, (1, w // strip.shape[1] + 1, 1))[:, :w]
    img[BASE_TOP:FLOOR_Y, 384:] = tiled[:, 384:]
    # E. floor: per-row tone from every clean floor pixel, whole floor repainted
    geom = yy >= np.maximum(FLOOR_Y, 1010 + (310 - xx))
    profE = rows_profile(FLOOR_Y, h, clean & geom & (xx >= 150), orig)
    fm = geom.astype(np.float32)
    fm[:, :150] = 0
    fm = cv2.GaussianBlur(fm, (0, 0), 2)[..., None]
    fl = np.zeros_like(img)
    fl[FLOOR_Y:] = profE[:, None, :] + grain[FLOOR_Y:]
    img = img * (1 - fm) + fl * fm
    return img


def main(render, model, out):
    sess = ort.InferenceSession(model)
    img = np.asarray(Image.open(render).convert("RGB"), np.float32)
    h, w = img.shape[:2]
    for name in REMOVE:
        m = mask((h, w), *REGIONS[name], feather=0)
        g = GROW.get(name, 12)
        m = cv2.dilate((m > .5).astype(np.uint8), np.ones((g, g), np.uint8)).astype(np.float32)
        ys, xs = np.where(m > 0)
        cy, cx = (ys.min() + ys.max()) / 2, (xs.min() + xs.max()) / 2
        side = int(max(np.ptp(ys), np.ptp(xs)) * 1.45 + 60)
        side = min(max(side, 512), max(h, w))
        x0 = int(min(max(cx - side / 2, 0), w - side))
        y0 = int(min(max(cy - side / 2, 0), h - side))
        crop, mc = img[y0:y0 + side, x0:x0 + side], m[y0:y0 + side, x0:x0 + side]
        fill = cv2.resize(lama(sess, crop.astype(np.uint8), mc), (side, side), interpolation=cv2.INTER_CUBIC)
        soft = cv2.GaussianBlur(mc, (0, 0), 3)[..., None]
        img[y0:y0 + side, x0:x0 + side] = crop * (1 - soft) + fill * soft
        print("removed", name, side)
    img = fix_lower(sess, img, np.asarray(Image.open(render).convert("RGB"), np.float32))
    Image.fromarray(img.astype(np.uint8)).save(out)
    print("wrote", out)


if __name__ == "__main__":
    main(*sys.argv[1:4])
