#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate cover + comparison infographic for the robot-games article."""
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

IMAGES_DIR = Path(__file__).resolve().parent.parent / "images"
FONT_DIR = Path(os.environ.get("WINDIR", "")) / "Fonts"


def load_font(size, bold=True):
    candidates = (
        [FONT_DIR / "msyhbd.ttc", FONT_DIR / "msyh.ttc", FONT_DIR / "simhei.ttf"]
        if bold
        else [FONT_DIR / "msyh.ttc", FONT_DIR / "msyhbd.ttc", FONT_DIR / "arial.ttf"]
    )
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if draw.textlength(cur + ch, font=font) > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(draw, box, text, font, fill, line_h=None, center=True):
    lines = wrap(draw, text, font, box[2] - box[0])
    line_h = line_h or (font.size + 8)
    total = line_h * len(lines)
    y = box[1] + (box[3] - box[1] - total) // 2 if center else box[1]
    for ln in lines:
        w = draw.textlength(ln, font=font)
        x = (box[0] + box[2] - w) // 2 if center else box[0]
        draw.text((x, y), ln, font=font, fill=fill)
        y += line_h


def vgrad(size, colors):
    w, h = size
    img = Image.new("RGB", size)
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1) * (len(colors) - 1)
        i = min(int(t), len(colors) - 2)
        loc = t - i
        a, b = colors[i], colors[i + 1]
        c = tuple(round(a[k] + (b[k] - a[k]) * loc) for k in range(3))
        for x in range(w):
            px[x, y] = c
    return img


def make_cover():
    img = vgrad((1200, 510), [(11, 18, 38), (23, 55, 120), (13, 110, 120)])
    d = ImageDraw.Draw(img, "RGBA")
    # accent stripe
    d.rectangle([0, 0, 1200, 6], fill=(20, 220, 200, 255))
    # big headline number
    draw_wrapped(d, [60, 70, 1140, 175], "天工 Ultra 跑出 8.64 秒", load_font(58, True), (255, 255, 255), line_h=66)
    draw_wrapped(d, [60, 182, 1140, 250], "百米破人类纪录，人形机器人运动会落幕", load_font(30, False), (200, 235, 255), line_h=40)
    # bottom takeaway bar
    d.rectangle([60, 360, 1140, 440], fill=(255, 255, 255, 22))
    draw_wrapped(d, [80, 366, 1120, 434], "从「更快」到「更智」：自主作业 · 2500h 数据集免费开放 · 行业进入算账时代", load_font(24, False), (235, 245, 255), line_h=34)
    draw_wrapped(d, [60, 458, 1140, 500], "公众号 · 精神小哥的思绪 | AI coding 与具身智能日报", load_font(20, False), (150, 180, 210), line_h=26)
    out = IMAGES_DIR / "cover.jpg"
    img.save(out, "JPEG", quality=92)
    print("wrote", out)


def make_compare():
    W, H = 1200, 700
    img = Image.new("RGB", (W, H), (244, 247, 251))
    d = ImageDraw.Draw(img, "RGBA")
    # title
    draw_wrapped(d, [40, 24, 1160, 86], "首届 vs 第二届：一年之间的跨越", load_font(38, True), (17, 28, 54), line_h=46)
    rows = [
        ("百米（秒）", "21.50", "8.64", "↓ 59.8%"),
        ("原地跳高（米）", "0.956", "3.40", "↑ 255%"),
        ("1500 米", "6:34", "2:21", "↓ 64.3%"),
        ("参赛机器人（台）", "—", "2056", "16 国 666 队"),
    ]
    top = 120
    rh = 118
    # header
    hb = [40, top, 1160, top + 50]
    d.rectangle(hb, fill=(23, 55, 120))
    cols = [(40, 360), (360, 640), (640, 920), (920, 1160)]
    hdrs = ["项目", "首届", "第二届", "变化"]
    for (x0, x1), htxt in zip(cols, hdrs):
        draw_wrapped(d, [x0 + 8, top, x1 - 8, top + 50], htxt, load_font(26, True), (255, 255, 255), line_h=30)
    y = top + 50
    for i, (name, a, b, chg) in enumerate(rows):
        bg = (255, 255, 255) if i % 2 == 0 else (232, 238, 246)
        d.rectangle([40, y, 1160, y + rh], fill=bg)
        draw_wrapped(d, [cols[0][0] + 8, y, cols[0][1] - 8, y + rh], name, load_font(26, True), (23, 28, 54), line_h=32)
        draw_wrapped(d, [cols[1][0] + 8, y, cols[1][1] - 8, y + rh], a, load_font(26, False), (120, 130, 145), line_h=32)
        draw_wrapped(d, [cols[2][0] + 8, y, cols[2][1] - 8, y + rh], b, load_font(30, True), (10, 132, 110), line_h=36)
        draw_wrapped(d, [cols[3][0] + 8, y, cols[3][1] - 8, y + rh], chg, load_font(22, False), (200, 90, 30), line_h=30)
        y += rh
    # footer note
    draw_wrapped(d, [40, y + 14, 1160, y + 70], "数据来源：第二届世界人形机器人运动会官方赛果、人民网、封面新闻", load_font(20, False), (130, 140, 155), line_h=28)
    out = IMAGES_DIR / "robot_compare.png"
    img.save(out, "PNG")
    print("wrote", out)


if __name__ == "__main__":
    make_cover()
    make_compare()
