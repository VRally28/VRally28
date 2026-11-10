#!/usr/bin/env python3
"""Turn the prepared portrait into a frameless ASCII SVG for the hero card."""
import base64
import html
import os
import sys
from pathlib import Path

from PIL import Image, ImageEnhance

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "assets" / "portrait-prepped.png"
OUTPUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "cards" / "portrait-ascii.svg"
FONT = ROOT / "assets" / "Mono-subset.woff2"
COLS = int(os.getenv("COLS", "180"))
STATIC = os.getenv("STATIC") == "1"
if COLS < 40:
    raise ValueError("COLS must be at least 40 for facial details to read clearly.")

ART_W = 800
CELL_W = ART_W / COLS
CELL_H = CELL_W * 15 / 8
ROWS = round(COLS * 8 / 15)
ART_H = ROWS * CELL_H
PAD = 20
WIDTH, HEIGHT = ART_W + PAD * 2, ART_H
RAMP = " .`:-=+*cs#%@"
INK = "#77797f"

image = Image.open(SOURCE).convert("L")
image = ImageEnhance.Contrast(image).enhance(1.05).resize((COLS, ROWS), Image.Resampling.LANCZOS)
pixels = image.load()
lines = []
for y in range(ROWS):
    chars = []
    for x in range(COLS):
        lum = (pixels[x, y] / 255) ** 1.18
        if lum >= 0.80:
            chars.append(" ")
        else:
            index = max(0, min(len(RAMP) - 1, round((1 - lum) * (len(RAMP) - 1))))
            chars.append(RAMP[index])
    lines.append("".join(chars))

font_css = ""
if FONT.exists():
    encoded = base64.b64encode(FONT.read_bytes()).decode("ascii")
    font_css = f"@font-face{{font-family:ProfileMono;src:url(data:font/woff2;base64,{encoded}) format('woff2')}}"
css = font_css + ".ascii-motion{display:inline}.ascii-fallback{display:none}@media(prefers-reduced-motion:reduce){.ascii-motion{display:none!important}.ascii-fallback{display:inline!important}}"
parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH:.0f}" height="{HEIGHT:.0f}" viewBox="0 0 {WIDTH:.0f} {HEIGHT:.0f}" role="img" aria-label="Vansh Rally portrait in monochrome ASCII art">',
    f"<style>{css}</style>",
]
duration = 5.8 / ROWS
for row, line in enumerate(lines):
    row_y = row * CELL_H
    y = row_y + CELL_H * .74
    safe = html.escape(line)
    text = f'<text xml:space="preserve" x="{PAD}" y="{y:.1f}" fill="{INK}" font-family="ProfileMono,monospace" font-size="{CELL_H*.86:.1f}" textLength="{ART_W:.1f}" lengthAdjust="spacing">{safe}</text>'
    parts.append(f'<g class="ascii-fallback">{text}</g>')
    if STATIC:
        parts.append(text)
    else:
        begin = row * duration
        parts.append(f'<g class="ascii-motion"><clipPath id="ascii-row-{row}"><rect x="{PAD}" y="{row_y:.1f}" width="0" height="{CELL_H:.1f}"><animate attributeName="width" from="0" to="{ART_W:.1f}" begin="{begin:.3f}s" dur="{duration:.3f}s" fill="freeze"/></rect></clipPath><g clip-path="url(#ascii-row-{row})">{text}</g></g>')
parts.append("</svg>\n")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("".join(parts), encoding="utf-8")
print(f"wrote {OUTPUT} ({WIDTH:.0f} x {HEIGHT:.0f}, {len(lines)} rows)")
