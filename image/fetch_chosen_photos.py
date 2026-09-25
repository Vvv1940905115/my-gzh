#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Download the final 9 chosen Pexels photos at high resolution."""

import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "images"
IMG.mkdir(parents=True, exist_ok=True)

# id, target filename, intended role
PICKS = [
    (10498787, "p01_group.jpg",     "学生围坐讨论（封面）"),
    (6147400,  "p02_laptop_boy.jpg", "男生专注用电脑"),
    (8500310,  "p03_study_girl.jpg", "女生独坐学习"),
    (8199249,  "p04_reading.jpg",    "女生读书记笔记"),
    (37758542, "p05_note_laptop.jpg","男生笔记+电脑"),
    (15238618, "p06_classroom.jpg",  "大学教室"),
    (35545651, "p07_library.jpg",    "图书馆"),
    (7972511,  "p08_campus.jpg",     "校园学生背包"),
    (12935064, "p09_qr_scan.jpg",    "手机扫二维码"),
]

W = 1400


def fetch(pair):
    pid, name, role = pair
    dest = IMG / name
    url = (
        f"https://images.pexels.com/photos/{pid}/pexels-photo-{pid}.jpeg"
        f"?auto=compress&cs=tinysrgb&w={W}"
    )
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    dest.write_bytes(data)
    return pid, name, role, len(data), resp.headers.get("Content-Type", "")


def main():
    with ThreadPoolExecutor(max_workers=9) as pool:
        results = list(pool.map(fetch, PICKS))
    for pid, name, role, size, ct in results:
        print(f"[OK] {pid:>8} -> {name}  {size//1024:>4}KB  {ct:20}  | {role}")


if __name__ == "__main__":
    main()
