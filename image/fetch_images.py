#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Search, download, crop, and preview reusable article images.

Examples:
  python image/fetch_images.py search --query "humanoid robot"
  python image/fetch_images.py fetch --source commons --spec "humanoid robot::real_robot.jpg" --retry 3
  python image/fetch_images.py fetch --source pexels --spec "10498787::p01_group.jpg"
  python image/fetch_images.py crop --input images/p01_group.jpg --output images/cover.jpg --ratio 1200:510
  python image/fetch_images.py sheet --input-dir images/_candidates --output images/sheet.png
"""

import argparse
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "images"
USER_AGENT = "Mozilla/5.0 (WeChat-article-image-tool)"

COMMONS_API = (
    "https://commons.wikimedia.org/w/api.php?action=query&generator=search"
    "&gsrnamespace=6&prop=imageinfo&iiprop=url|mime|size"
    "&iiurlwidth=1280&format=json&gsrsearch="
)


def configure_stdio():
    import sys
    for stream in (sys.stdout, sys.stderr):
        if stream and getattr(stream, "encoding", "").lower() not in ("utf-8", "utf8"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def request_bytes(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read(), response.headers.get("Content-Type", "")


def request_json(url, timeout=30):
    data, _ = request_bytes(url, timeout)
    return json.loads(data)


def search_commons(query, limit=10, min_width=800, min_height=500):
    url = COMMONS_API + urllib.parse.quote(query) + f"&gsrlimit={limit}"
    data = request_json(url)
    pages = data.get("query", {}).get("pages", {})
    rows = []
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        mime = info.get("mime", "")
        if not mime.startswith("image") or mime in ("image/gif", "image/svg+xml"):
            continue
        width = info.get("thumbwidth") or info.get("width") or 0
        height = info.get("thumbheight") or info.get("height") or 0
        if width < min_width or height < min_height:
            continue
        rows.append({
            "width": width,
            "height": height,
            "title": page.get("title", ""),
            "url": info.get("thumburl") or info.get("url"),
            "bytes": info.get("size", 0),
        })
    rows.sort(key=lambda item: item["width"] * item["height"], reverse=True)
    return rows


def pexels_url(photo_id, width):
    return (
        f"https://images.pexels.com/photos/{photo_id}/pexels-photo-{photo_id}.jpeg"
        f"?auto=compress&cs=tinysrgb&w={width}"
    )


def parse_spec(spec, source):
    if "::" not in spec:
        raise ValueError(f"spec must use 'query::filename' or 'id::filename': {spec}")
    key, filename = (part.strip() for part in spec.split("::", 1))
    if not key or not filename:
        raise ValueError(f"invalid image spec: {spec}")
    if any(sep in filename for sep in ("/", "\\", ":")) or filename.startswith("."):
        raise ValueError(f"output filename must be a simple name: {filename}")
    if source == "pexels":
        if not key.isdigit():
            raise ValueError(f"Pexels spec needs a numeric photo ID: {spec}")
        return int(key), OUTPUT_DIR / filename
    return key, OUTPUT_DIR / filename


def download_one(source, spec, width, retries, delay):
    query, destination = parse_spec(spec, source)
    for attempt in range(1, max(1, retries) + 1):
        try:
            if source == "commons":
                rows = search_commons(query, min_width=600, min_height=400)
                if not rows:
                    raise RuntimeError("no usable image")
                url = rows[0]["url"]
            elif source == "pexels":
                url = pexels_url(query, width)
            else:
                raise ValueError(f"unsupported source: {source}")
            data, content_type = request_bytes(url, timeout=60)
            if len(data) < 3000:
                raise RuntimeError(f"suspiciously small response: {len(data)} bytes")
            if content_type and not content_type.lower().startswith("image/"):
                raise RuntimeError(f"non-image response: {content_type}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            return destination, len(data), attempt
        except Exception as exc:
            if attempt >= retries:
                print(f"[FAIL] {spec}: {exc}")
                return destination, 0, attempt
            print(f"[RETRY {attempt}/{retries}] {spec}: {exc}")
            time.sleep(delay)
    return destination, 0, retries


def command_search(args):
    rows = search_commons(args.query, args.limit, args.min_width, args.min_height)
    for index, row in enumerate(rows[:args.show], 1):
        print(f"{index}. {row['width']}x{row['height']} | {row['title'][:80]}")
        print(f"   {row['url']}")
    print(f"showing {min(args.show, len(rows))} of {len(rows)} results")
    return 0


def command_fetch(args):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    specs = args.spec
    if args.worker > 1:
        with ThreadPoolExecutor(max_workers=args.worker) as pool:
            results = list(pool.map(lambda spec: download_one(args.source, spec, args.width, args.retry, args.delay), specs))
    else:
        results = []
        for spec in specs:
            results.append(download_one(args.source, spec, args.width, args.retry, args.delay))
            if args.delay and spec is not specs[-1]:
                time.sleep(args.delay)
    ok = sum(size > 0 for _, size, _ in results)
    for path, size, attempt in results:
        if size:
            print(f"[OK] {path.name}: {size // 1024}KB, attempt {attempt}")
    print(f"downloaded {ok}, failed {len(results) - ok}")
    return 0 if ok == len(results) else 1


def command_crop(args):
    source = Path(args.input)
    if not source.is_absolute():
        source = ROOT / source
    target = Path(args.output)
    if not target.is_absolute():
        target = ROOT / target
    ratio_w, ratio_h = (int(part) for part in args.ratio.split(":", 1))
    target_ratio = ratio_w / ratio_h
    with Image.open(source).convert("RGB") as image:
        width, height = image.size
        if width / height > target_ratio:
            new_width = int(height * target_ratio)
            left = (width - new_width) // 2
            image = image.crop((left, 0, left + new_width, height))
        else:
            new_height = int(width / target_ratio)
            top = (height - new_height) // 2
            image = image.crop((0, top, width, top + new_height))
        if args.resize_width:
            image = image.resize((args.resize_width, int(args.resize_width / target_ratio)), Image.LANCZOS)
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, quality=args.quality)
    print(f"cropped {source} -> {target}")
    return 0


def command_sheet(args):
    directory = Path(args.input_dir)
    if not directory.is_absolute():
        directory = ROOT / directory
    paths = sorted(directory.glob(args.pattern))
    if args.limit:
        paths = paths[: args.limit]
    if not paths:
        print(f"no images found in {directory}", file=__import__("sys").stderr)
        return 2
    cols = min(args.columns, len(paths))
    rows = (len(paths) + cols - 1) // cols
    cell_w, cell_h = args.cell_width, args.cell_height
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), (24, 26, 32))
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(paths):
        x, y = (index % cols) * cell_w, (index // cols) * cell_h
        try:
            with Image.open(path) as image:
                image.thumbnail((cell_w - 8, cell_h - 30), Image.LANCZOS)
                sheet.paste(image, (x + 4, y + 4))
        except Exception:
            draw.text((x + 12, y + 40), "LOAD FAIL", fill=(255, 120, 120))
        draw.rectangle((x, y + cell_h - 26, x + cell_w, y + cell_h), fill=(0, 0, 0))
        draw.text((x + 8, y + cell_h - 20), f"#{index} {path.stem}", fill=(120, 255, 190))
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)
    print(f"sheet -> {output} ({len(paths)} images)")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    search = subparsers.add_parser("search", help="search Wikimedia Commons")
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--min-width", type=int, default=800)
    search.add_argument("--min-height", type=int, default=500)
    search.add_argument("--show", type=int, default=6)
    search.set_defaults(handler=command_search)

    fetch = subparsers.add_parser("fetch", help="download Commons or Pexels images")
    fetch.add_argument("--source", choices=("commons", "pexels"), required=True)
    fetch.add_argument("--spec", action="append", required=True, help="commons: query::filename; pexels: id::filename")
    fetch.add_argument("--width", type=int, default=1400, help="requested width for Pexels")
    fetch.add_argument("--retry", type=int, default=3, help="retry count per image")
    fetch.add_argument("--delay", type=float, default=5.0, help="seconds between attempts")
    fetch.add_argument("--worker", type=int, default=1, help="parallel workers")
    fetch.set_defaults(handler=command_fetch)

    crop = subparsers.add_parser("crop", help="center-crop an image to a fixed ratio")
    crop.add_argument("--input", required=True)
    crop.add_argument("--output", required=True)
    crop.add_argument("--ratio", default="1200:510")
    crop.add_argument("--resize-width", type=int)
    crop.add_argument("--quality", type=int, default=92)
    crop.set_defaults(handler=command_crop)

    sheet = subparsers.add_parser("sheet", help="build a contact sheet from local images")
    sheet.add_argument("--input-dir", required=True)
    sheet.add_argument("--pattern", default="*.jpg")
    sheet.add_argument("--output", required=True)
    sheet.add_argument("--columns", type=int, default=6)
    sheet.add_argument("--cell-width", type=int, default=420)
    sheet.add_argument("--cell-height", type=int, default=280)
    sheet.add_argument("--limit", type=int)
    sheet.set_defaults(handler=command_sheet)
    return parser


def main():
    configure_stdio()
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.handler(args)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=__import__("sys").stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())