#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate cover and inline diagrams for the WeChat article."""

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


def cover():
    image = vertical_gradient(
        (1200, 630),
        [(15, 23, 42), (29, 78, 216), (13, 148, 136)],
    )
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, 0, 1200, 8), fill=(255, 255, 255, 220))

    draw.rounded_rectangle(
        (340, 72, 860, 158),
        radius=18,
        fill=(255, 255, 255, 28),
        outline=(255, 255, 255, 150),
        width=2,
    )
    draw_centered(
        draw,
        (340, 72, 860, 158),
        "WINDOWS 11 · 实操指南",
        load_font(30),
        (226, 232, 240),
    )

    draw_centered(
        draw,
        (50, 185, 1150, 330),
        "用 Codex 做自动化剪辑",
        load_font(72),
        (255, 255, 255),
    )
    draw_centered(
        draw,
        (50, 340, 1150, 410),
        "把重复劳动变成一条可反复使用的流水线",
        load_font(30, bold=False),
        (224, 242, 254),
    )

    timeline_y = 458
    draw.ellipse((118, timeline_y - 8, 218, 548), fill=(255, 255, 255))
    draw.polygon(
        [(160, timeline_y + 18), (160, 522), (194, 500)],
        fill=(15, 23, 42),
    )
    clips = [
        ((37, 99, 235), 258),
        ((13, 148, 136), 190),
        ((245, 158, 11), 218),
        ((168, 85, 247), 196),
    ]
    x = 244
    for color, width in clips:
        draw.rounded_rectangle(
            (x, timeline_y, x + width, timeline_y + 100),
            radius=12,
            fill=color,
        )
        x += width + 16
    draw.line((40, 505, 1160, 505), fill=(255, 255, 255, 110), width=2)
    image.save(IMAGES_DIR / "cover.png")


def workflow():
    image = Image.new("RGB", (1200, 630), (250, 251, 253))
    draw = ImageDraw.Draw(image)
    draw_centered(
        draw,
        (0, 56, 1200, 150),
        "自动化剪辑流程",
        load_font(52),
        (17, 24, 39),
    )
    draw_centered(
        draw,
        (0, 150, 1200, 210),
        "先说清楚，再小范围试跑，最后全量执行",
        load_font(27, bold=False),
        (100, 116, 139),
    )

    steps = [
        ("1", "素材整理", "输入输出分目录", (37, 99, 235)),
        ("2", "描述任务", "规则说清楚", (13, 148, 136)),
        ("3", "脚本试跑", "只用 1 个文件", (245, 158, 11)),
        ("4", "检查输出", "时长与日志", (99, 102, 241)),
        ("5", "全量执行", "人工复核发布", (190, 24, 93)),
    ]
    box_width = 196
    box_height = 150
    gap = 26
    start_x = 52
    top = 256
    x = start_x
    arrow_color = (148, 163, 184)

    for number, title, subtitle, accent in steps:
        draw.rounded_rectangle(
            (x, top, x + box_width, top + box_height),
            radius=16,
            fill=(255, 255, 255),
            outline=accent,
            width=3,
        )
        draw.ellipse((x + 18, top + 16, x + 62, top + 60), fill=accent)
        draw_centered(
            draw,
            (x + 18, top + 16, x + 62, top + 60),
            number,
            load_font(28),
            (255, 255, 255),
        )
        draw.text(
            (x + 20, top + 76),
            title,
            font=load_font(30),
            fill=(17, 24, 39),
        )
        draw.text(
            (x + 20, top + 116),
            subtitle,
            font=load_font(21, bold=False),
            fill=(100, 116, 139),
        )
        x += box_width
        if number != "5":
            arrow_x = x + gap // 2
            mid_y = top + box_height // 2
            draw.line((x + 6, mid_y, x + gap - 8, mid_y), fill=arrow_color, width=3)
            draw.polygon(
                [
                    (x + gap - 2, mid_y),
                    (x + gap - 12, mid_y - 8),
                    (x + gap - 12, mid_y + 8),
                ],
                fill=arrow_color,
            )
            x += gap

    draw_centered(
        draw,
        (0, 470, 1200, 560),
        "每一步都让 Codex 先说明要做什么，再碰你的素材",
        load_font(26, bold=False),
        (71, 85, 105),
    )
    image.save(IMAGES_DIR / "pic1.png")


def checklist():
    image = Image.new("RGB", (1200, 630), (250, 251, 253))
    draw = ImageDraw.Draw(image)
    draw_centered(
        draw,
        (0, 48, 1200, 140),
        "Win 11 准备清单",
        load_font(52),
        (17, 24, 39),
    )

    items = [
        ("Python 3.10+", "安装时勾选 Add to PATH", (37, 99, 235)),
        ("FFmpeg", "配置环境变量，命令行可识别", (13, 148, 136)),
        ("素材备份", "原片单独保留一份", (245, 158, 11)),
        ("独立输出目录", "不覆盖输入素材", (190, 24, 93)),
    ]
    top = 172
    for index, (title, subtitle, accent) in enumerate(items):
        y = top + index * 112
        draw.rounded_rectangle(
            (90, y, 1110, y + 88),
            radius=16,
            fill=(255, 255, 255),
            outline=(226, 232, 240),
            width=2,
        )
        draw.ellipse((126, y + 22, 182, y + 66), fill=accent)
        draw.line(
            (142, y + 40, 156, y + 52),
            fill=(255, 255, 255),
            width=6,
        )
        draw.line(
            (156, y + 52, 172, y + 34),
            fill=(255, 255, 255),
            width=6,
        )
        draw.text(
            (212, y + 15),
            title,
            font=load_font(32),
            fill=(17, 24, 39),
        )
        draw.text(
            (212, y + 51),
            subtitle,
            font=load_font(23, bold=False),
            fill=(100, 116, 139),
        )
    image.save(IMAGES_DIR / "pic2.png")


def fit_split():
    image = Image.new("RGB", (1200, 630), (250, 251, 253))
    draw = ImageDraw.Draw(image)
    draw_centered(
        draw,
        (0, 48, 1200, 140),
        "适合什么人用",
        load_font(52),
        (17, 24, 39),
    )

    columns = [
        ("适合", (13, 148, 136), ["素材多，规则固定", "愿意把需求写清楚", "能接受先试跑再全量"], 70),
        ("不太适合", (190, 24, 93), ["追求精细转场调色", "一点命令行都不想看", "素材乱到没有规律"], 620),
    ]
    top = 168
    card_width = 510

    for title, accent, items, left in columns:
        draw.rounded_rectangle(
            (left, top, left + card_width, 574),
            radius=16,
            fill=(255, 255, 255),
            outline=accent,
            width=3,
        )
        draw.rounded_rectangle(
            (left + 20, top + 20, left + card_width - 20, top + 82),
            radius=10,
            fill=accent,
        )
        draw_centered(
            draw,
            (left + 20, top + 20, left + card_width - 20, top + 82),
            title,
            load_font(30),
            (255, 255, 255),
        )
        for index, item in enumerate(items):
            y = top + 112 + index * 108
            draw.ellipse((left + 34, y + 2, left + 66, y + 34), fill=accent)
            draw.line((left + 44, y + 16, left + 52, y + 24), fill=(255, 255, 255), width=5)
            draw.line((left + 52, y + 24, left + 60, y + 10), fill=(255, 255, 255), width=5)
            draw.text(
                (left + 82, y + 1),
                item,
                font=load_font(27),
                fill=(17, 24, 39),
            )
    image.save(IMAGES_DIR / "pic3.png")


def main():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    cover()
    workflow()
    checklist()
    fit_split()
    print(f"Article images written to {IMAGES_DIR}")


if __name__ == "__main__":
    main()
