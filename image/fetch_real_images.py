#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch real, freely-licensed images from Wikimedia Commons for the MHS article.

Searches Commons for each topic, downloads the best candidate thumbnail to
images/real_N.jpg. No API key needed; Commons media is CC/PD.
"""
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "images"
OUT.mkdir(parents=True, exist_ok=True)

# topic -> (search query, target filename)
TOPICS = [
    ("humanoid robot", "real_robot.jpg"),
    ("quantum computer", "real_quantum.jpg"),
    ("industrial robot arm", "real_arm.jpg"),
    ("USB-C connector", "real_usbc.jpg"),
    ("quadruped robot", "real_quad.jpg"),
    ("data center server room", "real_datacenter.jpg"),
    ("circuit board motherboard", "real_circuit.jpg"),
    ("computer code screen", "real_code.jpg"),
    ("artificial intelligence neural network", "real_ai.jpg"),
]

API = (
    "https://commons.wikimedia.org/w/api.php?action=query&generator=search"
    "&gsrnamespace=6&gsrlimit=8&prop=imageinfo&iiprop=url|mime|size"
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
        if not mime.startswith("image") or mime == "image/gif":
            continue
        w = ii.get("thumbwidth") or ii.get("width") or 0
        h = ii.get("thumbheight") or ii.get("height") or 0
        # skip tiny or extreme aspect ratios
        if w < 600 or h < 400:
            continue
        results.append((ii.get("thumburl") or ii.get("url"), w, h, page.get("title", "")))
    return results


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research)"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    dest.write_bytes(data)
    return len(data)


def main():
    import urllib.parse

    summary = []
    for query, fname in TOPICS:
        dest = OUT / fname
        try:
            results = search_images(query)
        except Exception as e:
            summary.append(f"[FAIL] {query}: search error {e!r}")
            continue
        if not results:
            summary.append(f"[NONE] {query}: no usable image")
            continue
        # pick the largest by area among first few
        results.sort(key=lambda r: r[1] * r[2], reverse=True)
        url, w, h, title = results[0]
        try:
            size = download(url, dest)
            summary.append(f"[OK]   {query} -> {fname} ({w}x{h}, {size//1024}KB) [{title}]")
        except Exception as e:
            summary.append(f"[FAIL] {query}: download error {e!r}")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
