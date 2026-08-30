#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Replace the weak images with better real photos."""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "images"

TOPICS = [
    ("welding industrial robot factory", "real_arm.jpg"),
    ("person typing code laptop", "real_code.jpg"),
    ("NVIDIA graphics card GPU", "real_ai.jpg"),
]

API = (
    "https://commons.wikimedia.org/w/api.php?action=query&generator=search"
    "&gsrnamespace=6&gsrlimit=10&prop=imageinfo&iiprop=url|mime|size"
    "&iiurlwidth=1280&format=json&gsrsearch="
)


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def search_images(query):
    url = API + urllib.parse.quote(query)
    data = fetch_json(url)
    pages = data.get("query", {}).get("pages", {})
    results = []
    for page in pages.values():
        ii = page.get("imageinfo", [{}])[0]
        mime = ii.get("mime", "")
        if not mime.startswith("image") or mime in ("image/gif", "image/svg+xml"):
            continue
        w = ii.get("thumbwidth") or ii.get("width") or 0
        h = ii.get("thumbheight") or ii.get("height") or 0
        if w < 800 or h < 500:
            continue
        results.append((ii.get("thumburl") or ii.get("url"), w, h, page.get("title", ""), ii.get("size", 0)))
    return results


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research)"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    dest.write_bytes(data)
    return len(data)


for query, fname in TOPICS:
    dest = OUT / fname
    try:
        results = search_images(query)
        if not results:
            print(f"[NONE] {query}")
            time.sleep(8)
            continue
        # prefer larger byte size to avoid tiny/low-detail thumbs
        results.sort(key=lambda r: r[4], reverse=True)
        url, w, h, title, bsize = results[0]
        size = download(url, dest)
        print(f"[OK]   {query} -> {fname} ({w}x{h}, {size//1024}KB) [{title}]")
    except Exception as e:
        print(f"[FAIL] {query}: {e!r}")
    time.sleep(9)
