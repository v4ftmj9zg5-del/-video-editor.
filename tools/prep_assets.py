"""AI-upscale renders (Real-ESRGAN x4) and estimate depth (Depth Anything V2).

Usage: prep_assets.py OUT_DIR name=path [name=path ...]
Writes OUT_DIR/<name>.png (upscaled x3) and OUT_DIR/<name>_depth.npy
(relative disparity in [0,1], 1 = nearest, same size as the upscaled image).
"""
import os
import sys

import cv2
import numpy as np
import torch
from PIL import Image
from spandrel import ModelLoader
from transformers import pipeline

MODELS = os.path.expanduser(os.environ.get("MODELS", "/home/user/models"))
SCALE_OUT = 3  # final size relative to the original
torch.set_num_threads(os.cpu_count())


def upscale(model, img, tile=320, pad=16):
    """Tiled x4 super-resolution of a BGR uint8 image."""
    h, w = img.shape[:2]
    x = torch.from_numpy(img[..., ::-1].copy()).permute(2, 0, 1).float()[None] / 255
    out = torch.zeros(1, 3, h * 4, w * 4)
    for y0 in range(0, h, tile):
        for x0 in range(0, w, tile):
            ya, yb = max(y0 - pad, 0), min(y0 + tile + pad, h)
            xa, xb = max(x0 - pad, 0), min(x0 + tile + pad, w)
            with torch.no_grad():
                o = model(x[:, :, ya:yb, xa:xb])
            ty, tx = (y0 - ya) * 4, (x0 - xa) * 4
            th, tw = (min(y0 + tile, h) - y0) * 4, (min(x0 + tile, w) - x0) * 4
            out[:, :, y0 * 4:y0 * 4 + th, x0 * 4:x0 * 4 + tw] = o[:, :, ty:ty + th, tx:tx + tw]
    o = (out[0].permute(1, 2, 0).clamp(0, 1).numpy() * 255).round().astype(np.uint8)
    return o[..., ::-1]


def main():
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    sr_model = os.environ.get("SR_MODEL", "RealESRGAN_x4plus.pth")
    sr = ModelLoader().load_from_file(f"{MODELS}/{sr_model}").model.eval()
    depth = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Large-hf")
    for arg in sys.argv[2:]:
        name, path = arg.split("=", 1)
        img = cv2.imread(path)
        h, w = img.shape[:2]
        big = upscale(sr, img)
        # blend a little of the plain Lanczos upscale back in to keep natural texture
        lz = cv2.resize(img, big.shape[1::-1], interpolation=cv2.INTER_LANCZOS4)
        big = cv2.addWeighted(big, 0.8, lz, 0.2, 0)
        big = cv2.resize(big, (w * SCALE_OUT, h * SCALE_OUT), interpolation=cv2.INTER_AREA)
        cv2.imwrite(f"{out_dir}/{name}.png", big)
        d = depth(Image.fromarray(img[..., ::-1]))["predicted_depth"].squeeze().numpy()
        d = cv2.resize(d, (w * SCALE_OUT, h * SCALE_OUT), interpolation=cv2.INTER_CUBIC)
        d = (d - d.min()) / (d.max() - d.min())
        np.save(f"{out_dir}/{name}_depth.npy", d.astype(np.float32))
        print("done", name, big.shape, flush=True)


if __name__ == "__main__":
    main()
