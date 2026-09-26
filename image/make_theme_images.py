#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate article illustrations from declarative theme configurations."""

import argparse
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "images"
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
    for path in (BOLD_FONTS if bold else REGULAR_FONTS):
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
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
        color = lerp(colors[index], colors[index + 1], t - index)
        for x in range(width):
            pixels[x, y] = color
    return image


def centered(draw, box, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (box[0] + box[2] - bbox[2] + bbox[0]) // 2
    y = (box[1] + box[3] - bbox[3] + bbox[1]) // 2
    draw.text((x, y), text, font=font, fill=fill)


def left_text(draw, x, top, bottom, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    y = top + ((bottom - top) - (bbox[3] - bbox[1])) // 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=fill)


def wrap_text(draw, text, font, max_width):
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for char in paragraph:
            if draw.textlength(line + char, font=font) > max_width and line:
                lines.append(line)
                line = char
            else:
                line += char
        lines.append(line)
    return lines


def draw_wrapped(draw, box, text, font, fill, line_gap=8, center=True):
    x0, y0, x1, _ = box
    lines = wrap_text(draw, text, font, x1 - x0)
    sample = draw.textbbox((0, 0), "字", font=font)
    line_h = sample[3] - sample[1]
    y = y0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = x0 + ((x1 - x0 - (bbox[2] - bbox[0])) // 2) if center else x0
        draw.text((x, y - bbox[1]), line, font=font, fill=fill)
        y += line_h + line_gap


def arrow(draw, x1, x2, y, color, width=4):
    draw.line((x1, y, x2 - 14, y), fill=color, width=width)
    draw.polygon([(x2, y), (x2 - 15, y - 9), (x2 - 15, y + 9)], fill=color)


def parse_color(value):
    if isinstance(value, (list, tuple)):
        return tuple(int(item) for item in value)
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def output_path(fig):
    sub = fig.get("dir")
    base = OUTPUT_DIR / sub if sub else OUTPUT_DIR
    base.mkdir(parents=True, exist_ok=True)
    return base / fig["output"]


def save_image(fig, image):
    path = output_path(fig)
    if path.suffix.lower() == ".jpg":
        image.save(path, "JPEG", quality=fig.get("quality", 92))
    else:
        image.save(path, "PNG")
    print(f"saved {path}")


def render_hero(fig):
    size = fig.get("size", [1200, 630])
    image = vertical_gradient(tuple(size), [parse_color(c) for c in fig["gradient"]])
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, 0, size[0], fig.get("stripe", 8)), fill=(255, 255, 255, 220))
    y = 70
    if fig.get("badge"):
        badge_box = (360, y, size[0] - 360, y + 80)
        draw.rounded_rectangle(badge_box, radius=18, fill=(255, 255, 255, 28), outline=(255, 255, 255, 150), width=2)
        centered(draw, badge_box, fig["badge"], load_font(30), (226, 232, 240))
        y += 112
    title_box = (60, y, size[0] - 60, y + 122)
    centered(draw, title_box, fig["title"], load_font(fig.get("title_size", 72)), (255, 255, 255))
    y = title_box[3] + 12
    if fig.get("subtitle"):
        sub_box = (60, y, size[0] - 60, y + 80)
        centered(draw, sub_box, fig["subtitle"], load_font(fig.get("subtitle_size", 34), False), (214, 226, 255))
        y = sub_box[3] + 16
    if fig.get("chips"):
        chip_w, chip_h, gap = 224, 62, 24
        total = chip_w * len(fig["chips"]) + gap * (len(fig["chips"]) - 1)
        x = (size[0] - total) // 2
        for label, color in fig["chips"]:
            box = (x, y, x + chip_w, y + chip_h)
            draw.rounded_rectangle(box, radius=14, fill=parse_color(color))
            centered(draw, box, label, load_font(28), (255, 255, 255))
            x += chip_w + gap
        y += chip_h + 30
    if fig.get("note"):
        note_box = (80, y, size[0] - 80, y + fig.get("note_height", 80))
        draw.rounded_rectangle(note_box, radius=18, fill=(255, 255, 255, 24), outline=(255, 255, 255, 110), width=2)
        centered(draw, note_box, fig["note"], load_font(26, False), (235, 245, 255))
    if fig.get("footer"):
        centered(draw, (40, size[1] - 52, size[0] - 40, size[1] - 8), fig["footer"], load_font(20, False), (170, 190, 220))
    save_image(fig, image)


def render_flow(fig):
    size = fig.get("size", [1200, 660])
    image = Image.new("RGB", tuple(size), parse_color(fig.get("background", "#f6f8fc")))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, 0, size[0], 6), fill=parse_color(fig.get("accent", "#5b8cff")))
    centered(draw, (0, 44, size[0], 108), fig["title"], load_font(44), (26, 32, 44))
    if fig.get("subtitle"):
        centered(draw, (0, 112, size[0], 152), fig["subtitle"], load_font(24, False), (100, 116, 139))
    items = fig["items"]
    count = len(items)
    gap = fig.get("gap", 24)
    margin = 60
    card_w = (size[0] - margin * 2 - gap * (count - 1)) // count
    card_h = fig.get("card_height", 330)
    x, y = margin, fig.get("top", 190)
    for index, item in enumerate(items, 1):
        color = parse_color(item["color"])
        draw.rounded_rectangle((x, y, x + card_w, y + card_h), radius=18, fill=(255, 255, 255), outline=(226, 232, 240), width=2)
        draw.rounded_rectangle((x, y, x + card_w, y + 6), radius=3, fill=color)
        cx = x + card_w // 2
        draw.ellipse((cx - 34, y + 36, cx + 34, y + 104), fill=color)
        centered(draw, (cx - 34, y + 36, cx + 34, y + 104), str(index), load_font(42), (255, 255, 255))
        draw_wrapped(draw, (x + 20, y + 126, x + card_w - 20, y + 205), item["title"], load_font(28), (26, 32, 44), line_gap=6)
        draw_wrapped(draw, (x + 22, y + 212, x + card_w - 22, y + card_h - 14), item.get("body", ""), load_font(21, False), (100, 116, 139), line_gap=10)
        if index < count:
            ax = x + card_w + 2
            arrow(draw, ax, ax + gap - 4, y + card_h // 2, (203, 213, 225), 4)
        x += card_w + gap
    y = fig.get("footer_y", 556)
    for note in fig.get("footers", []):
        centered(draw, (0, y, size[0], y + 40), note, load_font(22, False), parse_color(fig.get("footer_color", "#64748b")))
        y += 40
    save_image(fig, image)


def render_checklist(fig):
    size = fig.get("size", [1200, 675])
    image = Image.new("RGB", tuple(size), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, size[0], 6), fill=parse_color(fig.get("accent", "#00997f")))
    centered(draw, (0, 44, size[0], 110), fig["title"], load_font(40), (34, 34, 34))
    rows = fig["rows"]
    row_h = fig.get("row_height", 104 if len(rows) <= 4 else 94)
    top = fig.get("top", 150)
    for index, row in enumerate(rows):
        y = top + index * (row_h + fig.get("row_gap", 18))
        draw.rounded_rectangle((60, y, size[0] - 60, y + row_h), radius=12, fill=(255, 255, 255), outline=(228, 228, 228), width=2)
        sx, sy = 92, y + 25
        draw.rounded_rectangle((sx, sy, sx + 44, sy + 44), radius=9, fill=parse_color(fig.get("accent", "#00997f")))
        draw.line(((sx + 12, sy + 23), (sx + 19, sy + 31), (sx + 33, sy + 13)), fill=(255, 255, 255), width=5, joint="curve")
        left_text(draw, 164, y, y + row_h, row["title"], load_font(28), (34, 34, 34))
        left_text(draw, 290, y, y + row_h, row.get("desc", ""), load_font(24, False), (143, 143, 143))
        draw.text((size[0] - 130, y + 30), f"0{index + 1}", font=load_font(26), fill=(228, 228, 228))
    save_image(fig, image)


def render_template(fig):
    size = fig.get("size", [1200, 675])
    image = Image.new("RGB", tuple(size), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, size[0], 6), fill=parse_color(fig.get("accent", "#00997f")))
    centered(draw, (0, 44, size[0], 110), fig["title"], load_font(40), (34, 34, 34))
    draw.rounded_rectangle((80, 155, size[0] - 80, size[1] - 75), radius=16, fill=(240, 249, 246), outline=parse_color(fig.get("accent", "#00997f")), width=2)
    for index, line in enumerate(fig["lines"]):
        y = 210 + index * fig.get("line_height", 96)
        draw.text((132, y), line, font=load_font(28), fill=(34, 34, 34))
        draw.line((132, y + 82, size[0] - 132, y + 82), fill=(210, 234, 227), width=1)
    save_image(fig, image)


def render_columns(fig):
    size = fig.get("size", [1200, 675])
    image = Image.new("RGB", tuple(size), (248, 250, 253))
    draw = ImageDraw.Draw(image, "RGBA")
    centered(draw, (0, 40, size[0], 116), fig["title"], load_font(fig.get("title_size", 52)), (17, 24, 39))
    if fig.get("subtitle"):
        centered(draw, (0, 116, size[0], 168), fig["subtitle"], load_font(27, False), (100, 116, 139))
    top = fig.get("top", 190)
    height = fig.get("height", 380)
    cards = fig["cards"]
    card_w = fig.get("card_width", 460)
    xs = [80, size[0] - 80 - card_w] if len(cards) == 2 else [80, 470, 860]
    for card, left in zip(cards, xs):
        accent = parse_color(card["color"])
        draw.rounded_rectangle((left, top, left + card_w, top + height), radius=18, fill=(255, 255, 255), outline=accent, width=3)
        draw.rounded_rectangle((left + 24, top + 22, left + card_w - 24, top + 90), radius=12, fill=accent)
        centered(draw, (left + 24, top + 22, left + card_w - 24, top + 90), card["title"], load_font(36), (255, 255, 255))
        if card.get("subtitle"):
            draw.text((left + 30, top + 104), card["subtitle"], font=load_font(24, False), fill=(71, 85, 105))
        y = top + 150
        for item in card.get("items", []):
            draw.ellipse((left + 34, y, left + 50, y + 16), fill=accent)
            draw.text((left + 64, y - 10), item, font=load_font(26), fill=(17, 24, 39))
            y += 52
    if len(cards) == 2 and fig.get("center_label"):
        x0, x1 = 80 + card_w, size[0] - 80 - card_w
        cx = (x0 + x1) // 2
        cy = top + height // 2
        draw.line((cx - 40, cy, cx + 40, cy), fill=(148, 163, 184), width=4)
        draw.polygon([(cx + 48, cy), (cx + 32, cy - 10), (cx + 32, cy + 10)], fill=(148, 163, 184))
        draw.ellipse((cx - 44, cy - 44, cx + 44, cy + 44), fill=parse_color(fig.get("accent", "#00997f")))
        centered(draw, (cx - 44, cy - 44, cx + 44, cy + 44), fig["center_label"], load_font(32), (255, 255, 255))
    save_image(fig, image)


def render_pillars(fig):
    size = fig.get("size", [1200, 630])
    image = Image.new("RGB", tuple(size), (248, 250, 253))
    draw = ImageDraw.Draw(image, "RGBA")
    centered(draw, (0, 40, size[0], 116), fig["title"], load_font(52), (17, 24, 39))
    pillars = fig["pillars"]
    width = 320
    gap = (size[0] - len(pillars) * width - 140) // max(1, len(pillars) - 1)
    left = 70
    for index, pillar in enumerate(pillars):
        accent = parse_color(pillar["color"])
        draw.rounded_rectangle((left, 180, left + width, 430), radius=18, fill=(255, 255, 255), outline=accent, width=3)
        draw.ellipse((left + width // 2 - 38, 208, left + width // 2 + 38, 284), fill=accent)
        centered(draw, (left + width // 2 - 38, 208, left + width // 2 + 38, 284), str(index + 1), load_font(34), (255, 255, 255))
        centered(draw, (left, 300, left + width, 348), pillar["title"], load_font(32), (17, 24, 39))
        centered(draw, (left, 356, left + width, 404), pillar.get("subtitle", ""), load_font(22, False), (100, 116, 139))
        left += width + gap
    if fig.get("badge"):
        draw.rounded_rectangle((360, 470, size[0] - 360, 560), radius=16, fill=(13, 148, 136, 22), outline=(13, 148, 136), width=2)
        centered(draw, (360, 470, size[0] - 360, 560), fig["badge"], load_font(30), (13, 116, 110))
    save_image(fig, image)


def render_benefits(fig):
    size = fig.get("size", [1200, 620])
    image = Image.new("RGB", tuple(size), (246, 248, 252))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, 0, size[0], 6), fill=parse_color(fig.get("accent", "#8b6cff")))
    centered(draw, (0, 44, size[0], 108), fig["title"], load_font(44), (26, 32, 44))
    if fig.get("subtitle"):
        centered(draw, (0, 112, size[0], 152), fig["subtitle"], load_font(24, False), (100, 116, 139))
    cards = fig["cards"]
    card_w = fig.get("card_width", 356)
    gap = 24
    total = len(cards) * card_w + (len(cards) - 1) * gap
    x = (size[0] - total) // 2
    for index, card in enumerate(cards, 1):
        color = parse_color(card["color"])
        draw.rounded_rectangle((x, 186, x + card_w, 516), radius=18, fill=(255, 255, 255), outline=(226, 232, 240), width=2)
        draw.rounded_rectangle((x, 186, x + card_w, 192), radius=3, fill=color)
        draw.text((x + 28, 220), f"0{index}", font=load_font(40), fill=color)
        draw_wrapped(draw, (x + 28, 286, x + card_w - 28, 350), card["title"], load_font(32), (26, 32, 44), line_gap=4)
        y = 360
        for point in card.get("points", []):
            draw.ellipse((x + 34, y + 9, x + 42, y + 17), fill=color)
            draw.text((x + 58, y), point, font=load_font(23, False), fill=(100, 116, 139))
            y += 46
        x += card_w + gap
    if fig.get("footer"):
        draw.rounded_rectangle((150, 552, size[0] - 150, 600), radius=24, fill=(255, 243, 224))
        centered(draw, (150, 552, size[0] - 150, 600), fig["footer"], load_font(24, False), (146, 64, 14))
    save_image(fig, image)


def render_table(fig):
    size = fig.get("size", [1200, 700])
    image = Image.new("RGB", tuple(size), (244, 247, 251))
    draw = ImageDraw.Draw(image, "RGBA")
    centered(draw, (40, 24, size[0] - 40, 86), fig["title"], load_font(38), (17, 28, 54))
    headers = fig["headers"]
    bounds = fig.get("columns", [])
    if not bounds:
        bounds = [(40 + i * (size[0] - 80) // len(headers), 40 + (i + 1) * (size[0] - 80) // len(headers)) for i in range(len(headers))]
    top = 120
    draw.rectangle((40, top, size[0] - 40, top + 50), fill=(23, 55, 120))
    for (x0, x1), text in zip(bounds, headers):
        draw_wrapped(draw, (x0 + 8, top, x1 - 8, top + 50), text, load_font(26), (255, 255, 255), line_gap=0)
    y = top + 50
    row_h = fig.get("row_height", 118)
    for index, row in enumerate(fig["rows"]):
        bg = (255, 255, 255) if index % 2 == 0 else (232, 238, 246)
        draw.rectangle((40, y, size[0] - 40, y + row_h), fill=bg)
        for col, (x0, x1), font_size, color in zip(row, bounds, fig.get("font_sizes", [26, 26, 30, 22]), fig.get("colors", [(23, 28, 54), (120, 130, 145), (10, 132, 110), (200, 90, 30)])):
            draw_wrapped(draw, (x0 + 8, y, x1 - 8, y + row_h), str(col), load_font(font_size), color, line_gap=4)
        y += row_h
    if fig.get("footer"):
        draw_wrapped(draw, (40, y + 14, size[0] - 40, y + 70), fig["footer"], load_font(20, False), (130, 140, 155), line_gap=4)
    save_image(fig, image)


RENDERERS = {
    "hero": render_hero,
    "flow": render_flow,
    "checklist": render_checklist,
    "template": render_template,
    "columns": render_columns,
    "pillars": render_pillars,
    "benefits": render_benefits,
    "table": render_table,
}


def main():
    parser = argparse.ArgumentParser(description="Generate configured article illustrations")
    parser.add_argument("--config", default=str(ROOT / "image" / "themes.json"))
    parser.add_argument("--theme", action="append", help="theme name to render; repeat or use all")
    parser.add_argument("--fig", action="append", help="limit rendering to an output filename")
    parser.add_argument("--list", action="store_true", help="list available themes and figures")
    args = parser.parse_args()

    with Path(args.config).open(encoding="utf-8") as handle:
        themes = json.load(handle)["themes"]
    if args.list:
        for name, theme in themes.items():
            print(name + ": " + ", ".join(fig["output"] for fig in theme))
        return 0
    requested = args.theme or ["all"]
    if "all" in requested:
        selected = list(themes)
    else:
        selected = requested
    for name in selected:
        if name not in themes:
            parser.error(f"unknown theme: {name}")
        for fig in themes[name]:
            if args.fig and fig["output"] not in args.fig:
                continue
            renderer = RENDERERS.get(fig.get("layout"))
            if renderer is None:
                raise ValueError(f"unknown layout: {fig.get('layout')}")
            renderer(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())