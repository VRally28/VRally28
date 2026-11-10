#!/usr/bin/env python3
"""Remove the portrait background and prepare a high-contrast grayscale image."""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "assets" / "portrait.png"
OUTPUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "assets" / "portrait-prepped.png"
LINE_WEIGHT = 0.6

cutout = remove(Image.open(SOURCE).convert("RGBA"))
rgb = np.asarray(cutout.convert("RGB"))
alpha = np.asarray(cutout.getchannel("A"))
if not np.any(alpha > 128):
    raise ValueError("Background removal found no portrait subject.")

gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
smooth = gray
for _ in range(3):
    smooth = cv2.bilateralFilter(smooth, 9, 40, 9)
lo, hi = np.percentile(smooth[alpha > 128], [2, 92])
tone = np.zeros_like(smooth, dtype=np.float32) if hi <= lo else np.clip((smooth.astype(np.float32) - lo) / (hi - lo), 0, 1)
fine = cv2.GaussianBlur(smooth, (0, 0), 1.5).astype(np.float32)
coarse = cv2.GaussianBlur(smooth, (0, 0), 6).astype(np.float32)
lines = np.clip((coarse - fine) / 40.0, 0, 1)
out = np.clip(tone - LINE_WEIGHT * lines, 0, 1) * 255
mask = cv2.GaussianBlur(alpha.astype(np.float32) / 255.0, (0, 0), 1.0)
out = out * mask + 255.0 * (1.0 - mask)

ys, xs = np.where(alpha > 20)
side = max(xs.max() - xs.min(), ys.max() - ys.min()) + 60
cx, cy = (xs.min() + xs.max()) // 2, (ys.min() + ys.max()) // 2
x0, y0 = cx - side // 2, cy - side // 2
canvas = np.full((side, side), 255, np.uint8)
sx0, sy0 = max(x0, 0), max(y0, 0)
sx1, sy1 = min(x0 + side, out.shape[1]), min(y0 + side, out.shape[0])
canvas[sy0-y0:sy1-y0, sx0-x0:sx1-x0] = out[sy0:sy1, sx0:sx1].astype(np.uint8)
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
Image.fromarray(canvas).save(OUTPUT)
print(f"wrote {OUTPUT} ({side} x {side})")
