#!/usr/bin/env python3
"""Render a portrait as a terminal-style ASCII SVG for the profile hero."""
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
ART_W = COLS * CELL_W
ART_H = ROWS * CELL_H
PAD, TITLE_H, STATUS_H = 20, 30, 30
WIDTH, HEIGHT = ART_W + PAD * 2, TITLE_H + ART_H + STATUS_H + PAD
RAMP = " .`:-=+*cs#%@"
BG, BG2, FRAME, MUTED, INK = "#0d1117", "#111722", "#30363d", "#7d8590", "#c9d1d9"

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
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH:.0f}" height="{HEIGHT:.0f}" viewBox="0 0 {WIDTH:.0f} {HEIGHT:.0f}" role="img" aria-label="Vansh Rally portrait rendered in ASCII art">',
    f"<style>{css}</style>",
    f'<defs><linearGradient id="ascii-bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#111722"/><stop offset="1" stop-color="#0d1117"/></linearGradient><clipPath id="ascii-window"><rect x="0" y="0" width="{WIDTH:.0f}" height="{HEIGHT:.0f}" rx="12"/></clipPath></defs>',
    f'<g clip-path="url(#ascii-window)"><rect width="{WIDTH:.0f}" height="{HEIGHT:.0f}" fill="url(#ascii-bg)"/><rect x="0.5" y="0.5" width="{WIDTH-1:.0f}" height="{HEIGHT-1:.0f}" rx="12" fill="none" stroke="{FRAME}"/><line x1="0" y1="{TITLE_H}" x2="{WIDTH}" y2="{TITLE_H}" stroke="{FRAME}"/>',
]
for i, color in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
    parts.append(f'<circle cx="{PAD + i*16}" cy="{TITLE_H/2:g}" r="5" fill="{color}"/>')
parts.append(f'<text x="{WIDTH/2:g}" y="{TITLE_H/2+4:g}" fill="{MUTED}" font-family="ProfileMono,monospace" font-size="12" text-anchor="middle">vansh@github:~$ ./portrait.sh</text>')
art_top = TITLE_H + PAD * .35
font_size = CELL_H * .86
duration = 5.8 / ROWS
for row, line in enumerate(lines):
    y = art_top + row * CELL_H + CELL_H * .74
    row_y = art_top + row * CELL_H
    safe = html.escape(line)
    text = f'<text xml:space="preserve" x="{PAD}" y="{y:.1f}" fill="{INK}" font-family="ProfileMono,monospace" font-size="{font_size:.1f}" textLength="{ART_W:.1f}" lengthAdjust="spacing">{safe}</text>'
    parts.append(f'<g class="ascii-fallback">{text}</g>')
    if STATIC:
        parts.append(text)
    else:
        begin = row * duration
        parts.append(f'<g class="ascii-motion"><clipPath id="ascii-row-{row}"><rect x="{PAD}" y="{row_y:.1f}" width="0" height="{CELL_H:.1f}"><animate attributeName="width" from="0" to="{ART_W:.1f}" begin="{begin:.3f}s" dur="{duration:.3f}s" fill="freeze"/></rect></clipPath><g clip-path="url(#ascii-row-{row})">{text}</g><rect x="{PAD}" y="{row_y+1:.1f}" width="{CELL_W:.1f}" height="{CELL_H-2:.1f}" fill="{INK}" opacity="0"><animate attributeName="x" from="{PAD}" to="{PAD+ART_W:.1f}" begin="{begin:.3f}s" dur="{duration:.3f}s" fill="freeze"/><set attributeName="opacity" to=".85" begin="{begin:.3f}s"/><set attributeName="opacity" to="0" begin="{begin+duration:.3f}s"/></rect></g>')
status_line_y = TITLE_H + ART_H + PAD * .35
status_y = status_line_y + 19
parts.append(f'<line x1="0" y1="{status_line_y:.1f}" x2="{WIDTH}" y2="{status_line_y:.1f}" stroke="{FRAME}"/><text x="{PAD}" y="{status_y:.1f}" fill="{MUTED}" font-family="ProfileMono,monospace" font-size="13">vansh@github:~$ whoami <tspan fill="{INK}">Vansh Rally</tspan></text>')
if not STATIC:
    cursor_x = PAD + len("vansh@github:~$ whoami Vansh Rally ") * 13 * .6
    parts.append(f'<rect x="{cursor_x:.1f}" y="{status_y-12:.1f}" width="8" height="14" fill="{INK}"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" dur="1s" repeatCount="indefinite"/></rect>')
parts.append("</g></svg>\n")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("".join(parts), encoding="utf-8")
print(f"wrote {OUTPUT} ({WIDTH:.0f} x {HEIGHT:.0f}, {len(lines)} rows)")
