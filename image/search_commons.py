#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Search Wikimedia Commons for real photos; print candidates so a human can pick."""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

API = (
    "https://commons.wikimedia.org/w/api.php?action=query&generator=search"
    "&gsrnamespace=6&gsrlimit=10&prop=imageinfo&iiprop=url|mime|size"
    "&iiurlwidth=1400&format=json&gsrsearch="
)

QUERIES = [
    "university student laptop study",
    "student using laptop computer",
    "college students studying together",
    "student library reading laptop",
    "university lecture hall students",
    "students group discussion classroom",
    "young student writing notes desk",
    "student dormitory desk computer",
    "person typing laptop desk",
    "students campus walking backpack",
]


def get_json(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (research)", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main():
    for query in QUERIES:
        print(f"\n=== {query} ===")
        try:
            data = get_json(API + urllib.parse.quote(query))
        except Exception as e:
            print(f"  search error: {e!r}")
            continue
        pages = data.get("query", {}).get("pages", {})
        rows = []
        for page in pages.values():
            ii = (page.get("imageinfo") or [{}])[0]
            mime = ii.get("mime", "")
            if not mime.startswith("image") or mime == "image/gif":
                continue
            w = ii.get("thumbwidth") or ii.get("width") or 0
            h = ii.get("thumbheight") or ii.get("height") or 0
            if w < 800 or h < 500:
                continue
            rows.append((w * h, w, h, page.get("title", ""), ii.get("thumburl") or ii.get("url")))
        rows.sort(reverse=True)
        for area, w, h, title, url in rows[:6]:
            print(f"  {w}x{h} | {title[:70]}")


if __name__ == "__main__":
    main()
