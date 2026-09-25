#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate cover and inline diagrams for the Doubao back-to-school article."""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_article_images import (  # noqa: E402
    IMAGES_DIR,
    draw_centered,
    load_font,
    vertical_gradient,
)

# Doubao-ish palette
BG_TOP = (23, 26, 58)
BG_MID = (63, 76, 222)
BG_BOT = (124, 92, 255)

ACCENT_BLUE = (91, 140, 255)
ACCENT_PURPLE = (139, 108, 255)
ACCENT_TEAL = (13, 170, 160)
ACCENT_AMBER = (240, 160, 40)

INK = (26, 32, 44)
INK_SOFT = (100, 116, 139)
CARD_BG = (255, 255, 255)
PAGE_BG = (246, 248, 252)


def wrap(draw, text, font, max_width):
    """Greedy CJK-friendly wrap: break on any character."""
    lines, current = [], ""
    for ch in text:
        trial = current + ch
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(current)
            current = ch
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def draw_wrapped(draw, box, text, font, fill, line_gap=8, centered=True):
    x0, y0, x1, _ = box
    lines = wrap(draw, text, font, x1 - x0)
    font_bbox = draw.textbbox((0, 0), "字", font=font)
    line_h = font_bbox[3] - font_bbox[1]
    total = len(lines) * line_h + (len(lines) - 1) * line_gap
    y = y0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = x0 + ((x1 - x0 - w) // 2) if centered else x0
        draw.text((x, y - bbox[1]), line, font=font, fill=fill)
        y += line_h + line_gap
    return total


def cover():
    """2.35:1 hero image for the WeChat article cover."""
    image = vertical_gradient((1200, 510), [BG_TOP, BG_MID, BG_BOT])
    draw = ImageDraw.Draw(image, "RGBA")

    # soft glow blobs
    draw.ellipse((-120, -160, 320, 280), fill=(255, 255, 255, 18))
    draw.ellipse((880, 260, 1400, 700), fill=(160, 130, 255, 46))

    # top pill
    draw.rounded_rectangle(
        (420, 48, 780, 108), radius=30, fill=(255, 255, 255, 34),
        outline=(255, 255, 255, 160), width=2,
    )
    draw_centered(draw, (420, 48, 780, 108), "2026 开学季 · 学生专属",
                  load_font(30), (233, 238, 255))

    # headline
    draw_centered(draw, (60, 132, 1140, 232), "豆包免费领 3 个月",
                  load_font(76), (255, 255, 255))
    draw_centered(draw, (60, 240, 1140, 300), "完成学生认证，订阅权益直接到账",
                  load_font(34, bold=False), (214, 226, 255))

    # three chips
    chips = [
        ("3 个月订阅", ACCENT_BLUE),
        ("额度重置 ×1", ACCENT_PURPLE),
        ("月卡立减 30", ACCENT_TEAL),
    ]
    chip_w, chip_h, gap = 224, 62, 24
    total_w = chip_w * 3 + gap * 2
    x = (1200 - total_w) // 2
    for label, color in chips:
        draw.rounded_rectangle(
            (x, 330, x + chip_w, 330 + chip_h), radius=14, fill=color,
        )
        draw_centered(draw, (x, 330, x + chip_w, 330 + chip_h),
                      label, load_font(28), (255, 255, 255))
        x += chip_w + gap

    # footer warning bar
    draw.rounded_rectangle(
        (240, 424, 960, 472), radius=24, fill=(255, 255, 255, 30),
    )
    draw_centered(draw, (240, 424, 960, 472),
                  "仅限豆包电脑客户端 · 手机 App 与网页版不可认证",
                  load_font(26, bold=False), (255, 232, 214))

    image.save(IMAGES_DIR / "doubao_cover.png")


def flow():
    """Four-step claim flow diagram."""
    image = Image.new("RGB", (1200, 660), PAGE_BG)
    draw = ImageDraw.Draw(image, "RGBA")

    draw.rectangle((0, 0, 1200, 6), fill=ACCENT_BLUE)
    draw_centered(draw, (0, 44, 1200, 108), "豆包开学季 · 领取流程",
                  load_font(44), INK)
    draw_centered(draw, (0, 112, 1200, 152), "全程约 5 分钟，必须在一台电脑上的豆包客户端里完成",
                  load_font(24, bold=False), INK_SOFT)

    steps = [
        (ACCENT_BLUE, "装 / 更新电脑版",
         "下载豆包 PC 客户端并登录\n版本建议 2.26.0 及以上"),
        (ACCENT_PURPLE, "左下角找入口",
         "点头像 → 开学免费送 3 个月\n进入活动页点「立即认证」"),
        (ACCENT_TEAL, "扫码 + 学信网",
         "抖音 App 扫码绑定账号\n学信网核验在读学籍"),
        (ACCENT_AMBER, "点「领取全部奖励」",
         "认证通过不等于到账\n手动点一次才发放"),
    ]

    card_w, card_h, gap = 258, 330, 24
    total_w = card_w * 4 + gap * 3
    x = (1200 - total_w) // 2
    y = 190

    for index, (color, title, body) in enumerate(steps, start=1):
        # card
        draw.rounded_rectangle(
            (x, y, x + card_w, y + card_h), radius=18,
            fill=CARD_BG, outline=(226, 232, 240), width=2,
        )
        draw.rounded_rectangle((x, y, x + card_w, y + 6), radius=3, fill=color)

        # number badge
        cx = x + card_w // 2
        draw.ellipse((cx - 34, y + 40, cx + 34, y + 108), fill=color)
        draw_centered(draw, (cx - 34, y + 40, cx + 34, y + 108),
                      str(index), load_font(42), (255, 255, 255))

        # title
        draw_wrapped(draw, (x + 20, y + 130, x + card_w - 20, y + 210),
                     title, load_font(28), INK, line_gap=6)

        # body
        draw_wrapped(draw, (x + 22, y + 212, x + card_w - 22, y + 320),
                     body.replace("\n", ""), load_font(21, bold=False),
                     INK_SOFT, line_gap=10)

        # arrow
        if index < len(steps):
            ax = x + card_w + 2
            draw.line((ax, y + card_h // 2, ax + gap - 6, y + card_h // 2),
                      fill=(203, 213, 225), width=4)
            draw.polygon(
                [(ax + gap - 6, y + card_h // 2 - 9),
                 (ax + gap - 6, y + card_h // 2 + 9),
                 (ax + gap, y + card_h // 2)],
                fill=(203, 213, 225),
            )
        x += card_w + gap

    draw_centered(draw, (0, 556, 1200, 596),
                  "学信网密码、验证码、身份证号、人脸信息 —— 一律不要发进豆包对话框",
                  load_font(23, bold=False), (190, 90, 60))
    draw_centered(draw, (0, 596, 1200, 636),
                  "界面快讯 · 中国青年网 · 快科技（2026-08-31 起）",
                  load_font(20, bold=False), (148, 163, 184))

    image.save(IMAGES_DIR / "doubao_flow.png")


def rights():
    """Three-benefit card diagram."""
    image = Image.new("RGB", (1200, 620), PAGE_BG)
    draw = ImageDraw.Draw(image, "RGBA")

    draw.rectangle((0, 0, 1200, 6), fill=ACCENT_PURPLE)
    draw_centered(draw, (0, 44, 1200, 108), "认证通过后能拿到什么",
                  load_font(44), INK)
    draw_centered(draw, (0, 112, 1200, 152), "三项权益需在活动页手动点「领取全部奖励」才会到账",
                  load_font(24, bold=False), INK_SOFT)

    cards = [
        (ACCENT_BLUE, "01", "3 个月订阅权益",
         ["豆包专业版标准套餐", "免费使用 90 天", "每账号限领一次"]),
        (ACCENT_PURPLE, "02", "1 次额度重置机会",
         ["额度用完后可重置一次", "自获得日起 30 天有效", "单账号最多持有 10 次"]),
        (ACCENT_TEAL, "03", "学生专属优惠",
         ["免费额度升级至 2.5 倍", "标准套餐 38 元 / 月", "原价 68 元，立减 30"]),
    ]

    card_w, card_h, gap = 356, 330, 24
    total_w = card_w * 3 + gap * 2
    x = (1200 - total_w) // 2
    y = 186

    for color, num, title, points in cards:
        draw.rounded_rectangle(
            (x, y, x + card_w, y + card_h), radius=18,
            fill=CARD_BG, outline=(226, 232, 240), width=2,
        )
        draw.rounded_rectangle((x, y, x + card_w, y + 6), radius=3, fill=color)

        draw.text((x + 28, y + 34), num, font=load_font(40), fill=color)
        draw.text((x + 28, y + 106), title, font=load_font(32), fill=INK)

        py = y + 168
        for point in points:
            draw.ellipse((x + 34, py + 9, x + 42, py + 17), fill=color)
            draw.text((x + 58, py), point,
                      font=load_font(23, bold=False), fill=INK_SOFT)
            py += 46

        x += card_w + gap

    draw.rounded_rectangle(
        (150, 552, 1050, 600), radius=24, fill=(255, 243, 224),
    )
    draw_centered(draw, (150, 552, 1050, 600),
                  "开学季 3 个月与此前的学生特惠可叠加使用 · 以账号内活动页实际展示为准",
                  load_font(24, bold=False), (146, 64, 14))

    image.save(IMAGES_DIR / "doubao_rights.png")


def main():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    cover()
    flow()
    rights()
    print(f"Doubao article images written to {IMAGES_DIR}")


if __name__ == "__main__":
    main()
