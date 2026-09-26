#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Media upload helpers for the WeChat material APIs."""

import re
import sys
sys.dont_write_bytecode = True
from pathlib import Path

_PUBLISH_DIR = Path(__file__).resolve().parent
if str(_PUBLISH_DIR) not in sys.path:
    sys.path.insert(0, str(_PUBLISH_DIR))

from wechat_api import (  # noqa: E402
    WECHAT_API,
    post_file,
    post_json,
    post_video_file,
    with_retry,
)


def upload_cover(token, cover_path):
    url = f"{WECHAT_API}/cgi-bin/material/add_material?type=image&access_token={token}"
    data = with_retry(lambda: post_file(url, cover_path))
    media_id = data.get("media_id")
    if not media_id:
        raise RuntimeError("Cover media_id was not returned.")
    return media_id


def upload_body_image(token, image_path):
    url = f"{WECHAT_API}/cgi-bin/media/uploadimg?access_token={token}"
    data = with_retry(lambda: post_file(url, image_path))
    url = str(data.get("url", "")).replace("http://", "https://")
    if not url:
        raise RuntimeError("Image URL was not returned.")
    return url


def upload_video(token, video_path, title="", introduction=""):
    url = f"{WECHAT_API}/cgi-bin/material/add_material?type=video&access_token={token}"
    data = with_retry(lambda: post_video_file(url, video_path, title, introduction))
    media_id = data.get("media_id")
    if not media_id:
        raise RuntimeError("Video media_id was not returned.")
    return media_id


def get_video_vid(token, media_id):
    data = post_json(
        f"{WECHAT_API}/cgi-bin/material/get_material?access_token={token}",
        {"media_id": media_id},
    )
    vid = str(data.get("vid", "")).strip()
    cover_url = str(data.get("cover_url", "") or "").strip()
    if vid:
        return vid, cover_url
    batch = post_json(
        f"{WECHAT_API}/cgi-bin/material/batchget_material?access_token={token}",
        {"type": "video", "offset": 0, "count": 20},
    )
    for item in batch.get("item", []):
        if item.get("media_id") == media_id:
            return (
                str(item.get("vid", "")).strip(),
                str(item.get("cover_url", "") or "").strip(),
            )
    return "", ""


def build_video_iframe(vid, cover_url=""):
    cover_attr = f" data-cover='{cover_url}'" if cover_url else ""
    return (
        f"<iframe class='video_iframe rich_pages' data-vidtype='2' "
        f"data-mpvid='{vid}'{cover_attr} allowfullscreen='' frameborder='0' "
        f"style='z-index:1;height:320px;' data-w='1920' "
        f"data-src='https://mp.weixin.qq.com/mp/readtemplate?t=pages/"
        f"video_player_tmpl&action=mpvideo&auto=0&vid={vid}'></iframe>"
    )


def extract_images(article_text, cover_path):
    images = []
    for match in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", article_text):
        path = match.group(1).strip()
        if path and not path.startswith(("http://", "https://", "//", "data:")):
            images.append(path)
    if cover_path:
        images.append(cover_path)
    seen = set()
    unique = []
    for path in images:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique
