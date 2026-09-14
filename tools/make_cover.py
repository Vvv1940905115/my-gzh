#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Crop p01 to 2.35:1 for the WeChat cover, and archive the old illustrations."""

import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "images"

src = Image.open(IMG / "p01_group.jpg").convert("RGB")
w, h = src.size
print(f"p01 original: {w}x{h}")

target_ratio = 1200 / 510  # 2.3529...
src_ratio = w / h
if src_ratio > target_ratio:
    # too wide → crop sides
    new_w = int(h * target_ratio)
    left = (w - new_w) // 2
    cropped = src.crop((left, 0, left + new_w, h))
else:
    new_h = int(w / target_ratio)
    top = (h - new_h) // 2
    cropped = src.crop((0, top, w, top + new_h))

# Resize to 1200x510 for WeChat 首图
cover = cropped.resize((1200, 510), Image.LANCZOS)
cover.save(IMG / "cover.jpg", quality=92)
print(f"cover saved: 1200x510 -> {IMG / 'cover.jpg'}")


# Archive old generated illustrations (do not delete, just stash in _archive)
ARCHIVE = IMG / "_archive_illustrations"
ARCHIVE.mkdir(exist_ok=True)
for name in ("doubao_cover.png", "doubao_flow.png", "doubao_rights.png"):
    p = IMG / name
    if p.exists():
        shutil.move(str(p), ARCHIVE / name)
        print(f"archived {name}")


# Clean candidates folder
cand = IMG / "_candidates"
if cand.exists():
    shutil.rmtree(cand, ignore_errors=True)
    print("removed _candidates/")
