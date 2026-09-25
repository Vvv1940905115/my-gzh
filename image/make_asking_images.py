#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate figures for the AI asking framework article."""

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
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = left + ((right - left) - width) // 2 - bbox[0]
    y = top + ((bottom - top) - height) // 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=fill)


def ltext(draw, x, top, bottom, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    height = bbox[3] - bbox[1]
    y = top + ((bottom - top) - height) // 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=fill)


def arrow(draw, x1, x2, y, color=TEAL, width=4):
    draw.line((x1, y, x2 - 14, y), fill=color, width=width)
    draw.polygon([(x2, y), (x2 - 15, y - 9), (x2 - 15, y + 9)], fill=color)


def fig1():
    image, draw = canvas(1200, 510)
    ctext(draw, (56, 48, 700, 96), "AI \u63d0\u95ee\u56db\u6bb5\u5f0f", load_font(26, bold=False), GRAY)
    ctext(draw, (56, 110, 1150, 210), "\u8ba9 AI \u5c11\u731c\u4e00\u70b9", load_font(60), INK)
    ctext(
        draw,
        (56, 225, 1150, 280),
        "\u80cc\u666f \u2192 \u4efb\u52a1 \u2192 \u9650\u5236 \u2192 \u9a8c\u6536",
        load_font(28, bold=False),
        GRAY,
    )
    labels = ["\u80cc\u666f", "\u4efb\u52a1", "\u9650\u5236", "\u9a8c\u6536"]
    xs = [100, 380, 660, 940]
    for x, label in zip(xs, labels):
        draw.rounded_rectangle((x, 330, x + 200, 396), radius=14, fill=SOFT, outline=TEAL, width=2)
        ctext(draw, (x, 330, x + 200, 396), label, load_font(30), TEAL)
    for x in xs[:-1]:
        arrow(draw, x + 214, x + 266, 363)
    out = IMAGES_DIR / "fig1-asking-cover.png"
    image.save(out)
    print("saved", out)


def fig2():
    image, draw = canvas(1200, 675)
    ctext(draw, (56, 44, 1000, 110), "\u95ee\u4e4b\u524d\uff0c\u5148\u68c0\u67e5\u56db\u4ef6\u4e8b", load_font(40), INK)
    rows = [
        ("\u80cc\u666f", "\u6211\u5728\u505a\u4ec0\u4e48\uff0c\u7ed9\u8c01\u770b\uff0c\u5728\u4ec0\u4e48\u573a\u666f"),
        ("\u4efb\u52a1", "\u4ea7\u51fa\u4ec0\u4e48\uff0c\u7ed9\u51e0\u7248\uff0c\u7528\u4ec0\u4e48\u52a8\u8bcd"),
        ("\u9650\u5236", "\u5b57\u6570\u3001\u53e3\u543b\u3001\u7981\u6b62\u9879\u3001\u5fc5\u7559\u4fe1\u606f"),
        ("\u9a8c\u6536", "\u4ec0\u4e48\u7b97\u5408\u683c\uff0c\u600e\u4e48\u81ea\u67e5"),
    ]
    for index, (title, desc) in enumerate(rows):
        top = 150 + index * 122
        draw.rounded_rectangle((60, top, 1140, top + 104), radius=12, fill=WHITE, outline=BORDER, width=2)
        draw.rounded_rectangle((92, top + 25, 136, top + 79), radius=9, fill=SOFT, outline=TEAL, width=2)
        ctext(draw, (92, top + 25, 136, top + 79), f"0{index + 1}", load_font(24), TEAL)
        ltext(draw, 170, top, top + 104, title, load_font(30), INK)
        ltext(draw, 310, top, top + 104, desc, load_font(24, bold=False), GRAY)
        draw.text((1068, top + 38), f"0{index + 1}", font=load_font(26), fill=BORDER)
    out = IMAGES_DIR / "fig2-asking-checklist.png"
    image.save(out)
    print("saved", out)


def fig3():
    image, draw = canvas(1200, 675)
    ctext(draw, (56, 44, 1000, 110), "\u76f4\u63a5\u6539\u8fd9\u6bb5\u6a21\u677f", load_font(40), INK)
    draw.rounded_rectangle((80, 155, 1120, 600), radius=16, fill=SOFT, outline=TEAL, width=2)
    lines = [
        "\u80cc\u666f\uff1a\u6211\u5728\u505a\u3010\u4e8b\u60c5\u3011\uff0c\u8bfb\u8005/\u5ba2\u6237\u662f\u3010\u8c01\u3011\u3002",
        "\u4efb\u52a1\uff1a\u8bf7\u4ea7\u51fa\u3010\u4ea4\u4ed8\u7269\u3011\uff0c\u7ed9\u3010\u6570\u91cf\u3011\u7248\u3002",
        "\u9650\u5236\uff1a\u4e0d\u8d85\u8fc7\u3010\u5b57\u6570\u3011\uff1b\u4e0d\u8981\u3010\u7981\u6b62\u9879\u3011\u3002",
        "\u9a8c\u6536\uff1a\u6bcf\u7248\u9644\u4e00\u53e5\u4e3a\u4ec0\u4e48\u53ef\u7528\u3002",
    ]
    for index, line in enumerate(lines):
        draw.text((132, 210 + index * 96), line, font=load_font(28), fill=INK)
        draw.line((132, 292 + index * 96, 1068, 292 + index * 96), fill=(210, 234, 227), width=1)
    out = IMAGES_DIR / "fig3-asking-template.png"
    image.save(out)
    print("saved", out)


def fig4():
    image, draw = canvas(1200, 675)
    ctext(draw, (0, 44, 1200, 112), "\u968f\u624b\u95ee vs \u56db\u6bb5\u95ee", load_font(40), INK)
    draw.rounded_rectangle((80, 165, 560, 570), radius=16, fill=LIGHT)
    draw.rounded_rectangle((640, 165, 1120, 570), radius=16, fill=SOFT, outline=TEAL, width=2)
    ctext(draw, (80, 210, 560, 295), "\u968f\u624b\u95ee", load_font(46), MID_GRAY)
    ctext(draw, (80, 315, 560, 367), "\u5e2e\u6211\u5199\u4e00\u6761\u6587\u6848", load_font(30), INK)
    for index, line in enumerate(["\u8bfb\u8005\u9760\u731c", "\u53e3\u543b\u9760\u60f3", "\u5b57\u6570\u9760\u731c"]):
        ctext(draw, (80, 405 + index * 55, 560, 445 + index * 55), line, load_font(24, bold=False), GRAY)
    ctext(draw, (640, 210, 1120, 295), "\u56db\u6bb5\u95ee", load_font(46), TEAL)
    ctext(draw, (640, 315, 1120, 367), "\u80cc\u666f\u3001\u4efb\u52a1\u3001\u9650\u5236\u3001\u9a8c\u6536", load_font(27), INK)
    for index, line in enumerate(["\u4fe1\u606f\u9f50", "\u8fb9\u754c\u6e05", "\u53ef\u8fed\u4ee3"]):
        ctext(draw, (640, 405 + index * 55, 1120, 445 + index * 55), line, load_font(24, bold=False), GRAY)
    draw.ellipse((556, 324, 644, 412), fill=TEAL)
    ctext(draw, (556, 324, 644, 412), "VS", load_font(32), WHITE)
    out = IMAGES_DIR / "fig4-asking-vs.png"
    image.save(out)
    print("saved", out)


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    fig4()
