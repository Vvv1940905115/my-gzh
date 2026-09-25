#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate MHS-themed cover and inline diagrams for the WeChat article."""

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


IMAGES_DIR = Path(__file__).resolve().parent.parent / "images"
FONT_DIR = Path(os.environ.get("WINDIR", "")) / "Fonts"

BOLD_FONTS = [
    FONT_DIR / "msyhbd.ttc",
    FONT_DIR / "msyh.ttc",
    FONT_DIR / "simhei.ttf",
    FONT_DIR / "arialbd.ttf",
]
REGULAR_FONTS = [
    FONT_DIR / "msyh.ttc",
    FONT_DIR / "msyhbd.ttc",
    FONT_DIR / "arial.ttf",
]


def load_font(size, bold=True):
    candidates = BOLD_FONTS if bold else REGULAR_FONTS
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vertical_gradient(size, colors):
    width, height = size
    image = Image.new("RGB", size)
    pixels = image.load()
    for y in range(height):
        t = y / max(1, height - 1) * (len(colors) - 1)
        index = min(int(t), len(colors) - 2)
        local = t - index
        color = lerp(colors[index], colors[index + 1], local)
        for x in range(width):
            pixels[x, y] = color
    return image


def draw_centered(draw, box, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = (box[0] + box[2] - width) // 2
    y = (box[1] + box[3] - height) // 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=fill)


def wrap_text(draw, text, font, max_width):
    lines = []
    for paragraph in text.split("\n"):
        words = list(paragraph)
        line = ""
        for ch in words:
            test = line + ch
            if draw.textlength(test, font=font) <= max_width or not line:
                line = test
            else:
                lines.append(line)
                line = ch
        lines.append(line)
    return lines


def cover():
    image = vertical_gradient(
        (1200, 630),
        [(13, 17, 38), (29, 66, 138), (13, 116, 130)],
    )
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, 0, 1200, 8), fill=(255, 255, 255, 230))

    draw.rounded_rectangle(
        (360, 70, 840, 150),
        radius=18,
        fill=(255, 255, 255, 26),
        outline=(255, 255, 255, 150),
        width=2,
    )
    draw_centered(
        draw,
        (360, 70, 840, 150),
        "AI 日报 · 具身智能",
        load_font(28),
        (226, 232, 240),
    )

    draw_centered(
        draw,
        (60, 178, 1140, 300),
        "Anthropic 发布 MHS",
        load_font(72),
        (255, 255, 255),
    )
    draw_centered(
        draw,
        (60, 312, 1140, 392),
        "给 AI Agent 一把打开物理世界的钥匙",
        load_font(40, bold=False),
        (206, 232, 252),
    )

    draw_centered(
        draw,
        (60, 430, 1140, 486),
        "硬件世界的 MCP：让智能体从写代码，走向动设备",
        load_font(26, bold=False),
        (148, 197, 224),
    )

    draw.rounded_rectangle(
        (430, 518, 770, 572),
        radius=14,
        fill=(255, 255, 255, 18),
        outline=(255, 255, 255, 120),
        width=2,
    )
    draw_centered(draw, (430, 518, 770, 572), "MCP → 软件    MHS → 硬件", load_font(24), (224, 242, 254))
    image.save(IMAGES_DIR / "cover.png")


def bus_diagram():
    image = Image.new("RGB", (1200, 630), (248, 250, 253))
    draw = ImageDraw.Draw(image)
    draw_centered(draw, (0, 40, 1200, 120), "两条总线，一个 Agent", load_font(52), (17, 24, 39))
    draw_centered(
        draw,
        (0, 116, 1200, 168),
        "MCP 接管软件世界，MHS 接管硬件世界",
        load_font(27, bold=False),
        (100, 116, 139),
    )

    cards = [
        ("MCP", "软件世界的协议层", ["调用 API", "读写文件", "连接数据库"], (37, 99, 235), 80),
        ("MHS", "硬件世界的协议层", ["显微镜", "机械臂", "量子计算机"], (13, 148, 136), 660),
    ]
    top = 210
    card_w = 460
    card_h = 320
    for tag, subtitle, items, accent, left in cards:
        draw.rounded_rectangle(
            (left, top, left + card_w, top + card_h),
            radius=18,
            fill=(255, 255, 255),
            outline=accent,
            width=3,
        )
        draw.rounded_rectangle(
            (left + 24, top + 22, left + card_w - 24, top + 90),
            radius=12,
            fill=accent,
        )
        draw_centered(draw, (left + 24, top + 22, left + card_w - 24, top + 90), tag, load_font(36), (255, 255, 255))
        draw.text((left + 30, top + 104), subtitle, font=load_font(24, bold=False), fill=(71, 85, 105))
        for i, item in enumerate(items):
            y = top + 150 + i * 52
            draw.ellipse((left + 34, y, left + 50, y + 16), fill=accent)
            draw.text((left + 64, y - 10), item, font=load_font(26), fill=(17, 24, 39))

    mid = 80 + card_w + (660 - (80 + card_w)) // 2
    arrow_y = top + card_h // 2
    draw.line((560, arrow_y, 640, arrow_y), fill=(148, 163, 184), width=4)
    draw.polygon(
        [(648, arrow_y), (632, arrow_y - 10), (632, arrow_y + 10)],
        fill=(148, 163, 184),
    )
    draw_centered(draw, (560, arrow_y - 44, 640, arrow_y - 8), "Agent", load_font(24), (71, 85, 105))
    image.save(IMAGES_DIR / "pic1.png")


def pillars_diagram():
    image = Image.new("RGB", (1200, 630), (248, 250, 253))
    draw = ImageDraw.Draw(image)
    draw_centered(draw, (0, 40, 1200, 116), "MHS 落地的三个支点", load_font(52), (17, 24, 39))

    pillars = [
        ("设备互通", "统一发现 / 连接 / 操作", (37, 99, 235), 70),
        ("硬指标", "QuEra 实测 99.3%", (245, 158, 11), 455),
        ("安全前置", "身份 / 权限 / 沙箱", (190, 24, 93), 840),
    ]
    top = 180
    w = 320
    h = 250
    for title, sub, accent, left in pillars:
        draw.rounded_rectangle((left, top, left + w, top + h), radius=18, fill=(255, 255, 255), outline=accent, width=3)
        draw.ellipse((left + w // 2 - 38, top + 28, left + w // 2 + 38, top + 104), fill=accent)
        draw_centered(draw, (left + w // 2 - 38, top + 28, left + w // 2 + 38, top + 104), str(pillars.index((title, sub, accent, left)) + 1), load_font(34), (255, 255, 255))
        draw_centered(draw, (left, top + 120, left + w, top + 168), title, load_font(32), (17, 24, 39))
        draw_centered(draw, (left, top + 176, left + w, top + 214), sub, load_font(22, bold=False), (100, 116, 139))

    badge = ImageDraw.Draw(image, "RGBA")
    badge.rounded_rectangle((360, 470, 840, 560), radius=16, fill=(13, 148, 136, 22), outline=(13, 148, 136), width=2)
    draw_centered(draw, (360, 470, 840, 560), "Coding Agent + 具身智能 = 同一条总线", load_font(30), (13, 116, 110))
    image.save(IMAGES_DIR / "pic2.png")


def main():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    cover()
    bus_diagram()
    pillars_diagram()
    print(f"MHS article images written to {IMAGES_DIR}")


if __name__ == "__main__":
    main()
