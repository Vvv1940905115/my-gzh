#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Download Pexels candidate thumbnails and build contact sheets for visual picking."""

import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
CAND = ROOT / "images" / "_candidates"
CAND.mkdir(parents=True, exist_ok=True)

IDS = [
    # student laptop
    8197503, 5905886, 7972331, 5554261, 6147400, 10498787, 5553721, 5553957,
    37368295, 3775128, 8500310, 8199249, 9158795, 5965565, 5537938, 9159076,
    35580877, 6209565, 5553731, 28927920,
    # college students studying
    8199651, 5553065, 37811241, 8199223, 8199762, 37758597, 6549913, 37758607,
    9158769, 7972485, 37758542, 6684506, 7972966, 6146995, 37758609,
    # student library
    15238618, 35551100, 35545651, 8199613, 6281132, 16420457, 8199674, 9572540,
    8199594, 16420473, 32662455, 34260079, 8419263, 8199625,
    # campus / backpack
    2676888, 7683617, 6147164, 6140610, 37846368, 7252752, 7972511, 5538594,
    1454360, 7972544, 7972659, 37762500, 7683629, 5537929, 7973031,
    # phone / qr
    278430, 8372635, 7289731, 8383882, 2451622, 12935064, 8372628, 8372639,
    16345589, 8372632, 8372622, 7289717, 8372636, 8372640, 8383895,
]

THUMB_W = 420


def thumb_url(pid, width):
    return (
        f"https://images.pexels.com/photos/{pid}/pexels-photo-{pid}.jpeg"
        f"?auto=compress&cs=tinysrgb&fit=crop&w={width}"
    )


def download(pid, dest, width):
    req = urllib.request.Request(
        thumb_url(pid, width),
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = resp.read()
    if len(data) < 3000:
        raise ValueError(f"suspiciously small: {len(data)} bytes")
    dest.write_bytes(data)
    return len(data)


def build_sheet(pairs, out_path, cols=6, cw=420, ch=280):
    rows = (len(pairs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw, rows * ch), (24, 26, 32))
    draw = ImageDraw.Draw(sheet)
    for idx, (pid, path) in enumerate(pairs):
        r, c = divmod(idx, cols)
        x, y = c * cw, r * ch
        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail((cw - 8, ch - 30), Image.LANCZOS)
            sheet.paste(img, (x + 4, y + 4))
        except Exception:
            draw.text((x + 12, y + 40), f"{pid} LOAD FAIL", fill=(255, 120, 120))
        draw.rectangle((x, y + ch - 26, x + cw, y + ch), fill=(0, 0, 0))
        draw.text((x + 8, y + ch - 20), f"#{idx}  {pid}", fill=(120, 255, 190))
    sheet.save(out_path)
    print(f"sheet -> {out_path} ({len(pairs)} imgs)")


def main():
    from concurrent.futures import ThreadPoolExecutor

    def work(pid):
        dest = CAND / f"{pid}.jpg"
        if dest.exists() and dest.stat().st_size > 3000:
            return pid, dest, None
        try:
            download(pid, dest, THUMB_W)
            return pid, dest, None
        except Exception as e:
            return pid, None, str(e)[:60]

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(work, IDS))

    ok = [(pid, dest) for pid, dest, err in results if dest]
    failed = [(pid, err) for pid, dest, err in results if not dest]
    for pid, err in failed:
        print(f"[FAIL] {pid}: {err}")
    print(f"\ndownloaded {len(ok)}, failed {len(failed)}")

    half = (len(ok) + 1) // 2
    build_sheet(ok[:half], CAND / "sheet_a.png")
    build_sheet(ok[half:], CAND / "sheet_b.png")
    print(f"NOTE: sheet_b indices continue from sheet_a (offset {half})")


if __name__ == "__main__":
    main()
