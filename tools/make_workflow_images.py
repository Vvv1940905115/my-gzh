#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the four figures for the AI desktop workflow article.

Style follows the QbitAI reference layout: clean white background,
teal accent (#00997f), dark-gray ink, no heavy shadows.
"""

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

IMAGES_DIR = Path(__file__).resolve().parent.parent / "images"
FONT_DIR = Path(os.environ.get("WINDIR", "")) / "Fonts"

BOLD_FONTS = [FONT_DIR / "msyhbd.ttc", FONT_DIR / "msyh.ttc", FONT_DIR / "simhei.ttf"]
REGULAR_FONTS = [FONT_DIR / "msyh.ttc", FONT_DIR / "arial.ttf"]

INK = (34, 34, 34)
TEAL = (0, 153, 127)
GRAY = (143, 143, 143)
MID_GRAY = (110, 110, 110)
LIGHT = (246, 246, 246)
BORDER = (228, 228, 228)
SOFT = (240, 249, 246)
WHITE = (255, 255, 255)


def load_font(size, bold=True):
    for path in (BOLD_FONTS if bold else REGULAR_FONTS):
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default()


def canvas(width, height):
    image = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, 6), fill=TEAL)
    return image, draw


def ctext(draw, box, text, font, fill):
    left, top, right, bottom = box
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = left + ((right - left) - w) // 2 - bbox[0]
    y = top + ((bottom - top) - h) // 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=fill)


def ltext(draw, x, top, bottom, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    h = bbox[3] - bbox[1]
    y = top + ((bottom - top) - h) // 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=fill)


def arrow(draw, x1, x2, y, color=TEAL, width=4):
    draw.line((x1, y, x2 - 14, y), fill=color, width=width)
    draw.polygon([(x2, y), (x2 - 15, y - 9), (x2 - 15, y + 9)], fill=color)


def fig1():
    image, draw = canvas(1200, 510)
    ctext(draw, (56, 48, 700, 96), "AI \u684c\u9762\u5de5\u4f5c\u6d41", load_font(26, bold=False), GRAY)
    ctext(draw, (56, 110, 1150, 210), "\u4e09\u6bb5\u63a5\u529b\uff0c\u628a\u60f3\u6cd5\u505a\u6210\u4e8b", load_font(60), INK)
    ctext(
        draw,
        (56, 225, 1150, 280),
        "\u60f3\u6cd5 \u2192 \u8349\u7a3f \u2192 \u4efb\u52a1 \u2192 \u53ef\u590d\u7528\u7ed3\u8bba",
        load_font(28, bold=False),
        GRAY,
    )
    labels = ["\u60f3\u6cd5", "\u8349\u7a3f", "\u4efb\u52a1", "\u7ed3\u8bba"]
    xs = [100, 380, 660, 940]
    for x, label in zip(xs, labels):
        draw.rounded_rectangle((x, 330, x + 200, 396), radius=14, fill=SOFT, outline=TEAL, width=2)
        ctext(draw, (x, 330, x + 200, 396), label, load_font(30), TEAL)
    for x in xs[:-1]:
        arrow(draw, x + 214, x + 266, 363)
    out = IMAGES_DIR / "fig1-workflow-v2.png"
    image.save(out)
    print("saved", out)


def fig2():
    image, draw = canvas(1200, 675)
    ctext(draw, (56, 44, 1000, 110), "\u4e09\u4e2a\u5de5\u5177\uff0c\u5404\u5e72\u4e00\u4ef6\u4e8b", load_font(40), INK)
    cards = [
        ("01", "\u8c46\u5305\u8f93\u5165\u6cd5", "\u968f\u624b\u6355\u6349", ["\u788e\u60f3\u6cd5\u9a6c\u4e0a\u53d8\u6210", "\u7ed3\u6784\u5316\u7684\u8349\u7a3f"]),
        ("02", "Loomy", "\u62c6\u89e3\u4efb\u52a1", ["\u628a\u8349\u7a3f\u53d8\u6210\u4eca\u5929\u3001", "\u660e\u5929\u80fd\u505a\u7684\u6e05\u5355"]),
        ("03", "Gemini", "\u6536\u53e3\u5224\u65ad", ["\u6311\u51fa\u5173\u952e\u52a8\u4f5c\u548c", "\u53ef\u590d\u7528\u7684\u7ed3\u8bba"]),
    ]
    for index, (number, name, role, desc) in enumerate(cards):
        x = 60 + index * 380
        draw.rounded_rectangle((x, 150, x + 340, 600), radius=14, fill=WHITE, outline=BORDER, width=2)
        draw.text((x + 28, 184), number, font=load_font(42), fill=TEAL)
        draw.text((x + 28, 258), name, font=load_font(36), fill=INK)
        draw.line((x + 28, 336, x + 108, 336), fill=TEAL, width=4)
        draw.text((x + 28, 366), role, font=load_font(28), fill=INK)
        for line_index, line in enumerate(desc):
            draw.text((x + 28, 430 + line_index * 42), line, font=load_font(23, bold=False), fill=GRAY)
    out = IMAGES_DIR / "fig2-three-tools-v2.png"
    image.save(out)
    print("saved", out)


def fig3():
    image, draw = canvas(1200, 675)
    ctext(draw, (56, 44, 1000, 110), "\u6311\u684c\u9762 AI \u7684\u4e94\u5173", load_font(40), INK)
    rows = [
        ("\u5524\u8d77\u5feb", "\u4e24\u4e09\u79d2\u5185\u53ef\u7528\uff0c\u4e0d\u7528\u5148\u5207\u7a97\u53e3"),
        ("\u4e0d\u6253\u65ad", "\u5728\u539f\u754c\u9762\u65c1\u8fb9\u63a5\u4f4f\u4efb\u52a1"),
        ("\u80fd\u6c89\u6dc0", "\u8349\u7a3f\u3001\u6e05\u5355\u3001\u7ed3\u8bba\u90fd\u80fd\u4fdd\u5b58"),
        ("\u8ffd\u95ee\u987a", "\u4e0d\u7528\u6bcf\u6b21\u91cd\u65b0\u89e3\u91ca\u80cc\u666f"),
        ("\u5e38\u9a7b", "\u9700\u8981\u65f6\u5c31\u5728\uff0c\u4e0d\u9700\u8981\u65f6\u4e0d\u5435"),
    ]
    for index, (title, desc) in enumerate(rows):
        top = 150 + index * 102
        draw.rounded_rectangle((60, top, 1140, top + 94), radius=12, fill=WHITE, outline=BORDER, width=2)
        sx, sy = 92, top + 25
        draw.rounded_rectangle((sx, sy, sx + 44, sy + 44), radius=9, fill=TEAL)
        draw.line(((sx + 12, sy + 23), (sx + 19, sy + 31), (sx + 33, sy + 13)), fill=WHITE, width=5, joint="curve")
        ltext(draw, 164, top, top + 94, title, load_font(28), INK)
        ltext(draw, 290, top, top + 94, desc, load_font(24, bold=False), GRAY)
        draw.text((1070, top + 30), f"0{index + 1}", font=load_font(26), fill=BORDER)
    out = IMAGES_DIR / "fig3-checklist-v2.png"
    image.save(out)
    print("saved", out)


def fig4():
    image, draw = canvas(1200, 675)
    ctext(draw, (0, 44, 1200, 112), "\u8dd1\u5206 vs \u4f53\u9a8c", load_font(40), INK)
    draw.rounded_rectangle((80, 160, 560, 560), radius=16, fill=LIGHT)
    draw.rounded_rectangle((640, 160, 1120, 560), radius=16, fill=SOFT, outline=TEAL, width=2)
    ctext(draw, (80, 200, 560, 285), "\u8dd1\u5206", load_font(46), MID_GRAY)
    ctext(draw, (80, 300, 560, 352), "\u51b3\u5b9a\u5019\u9009\u540d\u5355", load_font(30), INK)
    for index, line in enumerate(["\u699c\u5355\u6392\u540d", "\u8dd1\u5206\u5bf9\u6bd4", "\u65b0\u529f\u80fd\u5806\u53e0"]):
        ctext(draw, (80, 390 + index * 52, 560, 430 + index * 52), line, load_font(24, bold=False), GRAY)
    ctext(draw, (640, 200, 1120, 285), "\u4f53\u9a8c", load_font(46), TEAL)
    ctext(draw, (640, 300, 1120, 352), "\u51b3\u5b9a\u7559\u4e0b\u540d\u5355", load_font(30), INK)
    for index, line in enumerate(["\u5524\u8d77\u5feb", "\u4e0d\u6253\u65ad", "\u80fd\u6c89\u6dc0"]):
        ctext(draw, (640, 390 + index * 52, 1120, 430 + index * 52), line, load_font(24, bold=False), GRAY)
    draw.ellipse((556, 316, 644, 404), fill=TEAL)
    ctext(draw, (556, 316, 644, 404), "VS", load_font(32), WHITE)
    out = IMAGES_DIR / "fig4-vs-v2.png"
    image.save(out)
    print("saved", out)


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    fig4()
