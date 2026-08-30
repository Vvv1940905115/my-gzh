#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Upload images and push the generated article into the WeChat draft box."""

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from md_to_wechat import (
    ROOT,
    build_preview,
    make_local_srcs_relative,
    parse_blocks,
    render_blocks,
    render_footer,
)


WECHAT_API = "https://api.weixin.qq.com"


def default_config_paths():
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    return [
        codex_home / "skills" / "wechat-publisher" / "config.json",
        ROOT / "wechat-config.json",
    ]


def load_config():
    for path in default_config_paths():
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            app_id = str(data.get("app_id", "")).strip()
            app_secret = str(data.get("app_secret", "")).strip()
            if (
                app_id
                and app_secret
                and "你的" not in app_id
                and "你的" not in app_secret
                and "YOUR_" not in app_id
                and "YOUR_" not in app_secret
            ):
                return {"app_id": app_id, "app_secret": app_secret, "path": str(path)}
            raise SystemExit(
                f"Config found but incomplete: {path}\n"
                "Fill in app_id and app_secret, then run again."
            )
    raise SystemExit(
        "No WeChat config found. Create one of:\n"
        "- ~/.codex/skills/wechat-publisher/config.json\n"
        "- my-gzh/wechat-config.json\n"
        "with {\"app_id\": \"...\", \"app_secret\": \"...\"}."
    )


def check_error(data):
    errcode = data.get("errcode")
    if errcode is not None and errcode != 0:
        raise RuntimeError(f"WeChat API error {errcode}: {data.get('errmsg', 'unknown')}")


def get_json(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    check_error(data)
    return data


def post_json(url, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    check_error(data)
    return data


def post_file(url, file_path):
    boundary = "----CodexWechatBoundary" + uuid.uuid4().hex
    file_path = Path(file_path)
    ext = file_path.suffix.lower()
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext, "image/png")
    parts = [
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="media"; filename="{file_path.name}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8"),
        file_path.read_bytes(),
        b"\r\n",
        f"--{boundary}--\r\n".encode("utf-8"),
    ]
    request = urllib.request.Request(
        url,
        data=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    check_error(data)
    return data


def post_video_file(url, file_path, title, introduction):
    boundary = "----CodexWechatBoundary" + uuid.uuid4().hex
    file_path = Path(file_path)
    description = json.dumps(
        {"title": title, "introduction": introduction}, ensure_ascii=False
    )
    parts = [
        (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="description"\r\n\r\n'
            f"{description}\r\n"
        ).encode("utf-8"),
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="media"; filename="{file_path.name}"\r\n'
            "Content-Type: video/mp4\r\n\r\n"
        ).encode("utf-8"),
        file_path.read_bytes(),
        b"\r\n",
        f"--{boundary}--\r\n".encode("utf-8"),
    ]
    request = urllib.request.Request(
        url,
        data=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        data = json.loads(response.read().decode("utf-8"))
    check_error(data)
    return data


def upload_video(token, video_path, title="", introduction=""):
    url = f"{WECHAT_API}/cgi-bin/material/add_material?type=video&access_token={token}"
    data = post_video_file(url, video_path, title, introduction)
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


def get_access_token(config):
    query = urllib.parse.urlencode(
        {
            "grant_type": "client_credential",
            "appid": config["app_id"],
            "secret": config["app_secret"],
        }
    )
    data = get_json(f"{WECHAT_API}/cgi-bin/token?{query}")
    token = data.get("access_token")
    if not token:
        raise RuntimeError("Access token was not returned.")
    return token


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


def upload_cover(token, cover_path):
    url = f"{WECHAT_API}/cgi-bin/material/add_material?type=image&access_token={token}"
    data = post_file(url, cover_path)
    media_id = data.get("media_id")
    if not media_id:
        raise RuntimeError("Cover media_id was not returned.")
    return media_id


def upload_body_image(token, image_path):
    url = f"{WECHAT_API}/cgi-bin/media/uploadimg?access_token={token}"
    data = post_file(url, image_path)
    url = str(data.get("url", "")).replace("http://", "https://")
    if not url:
        raise RuntimeError("Image URL was not returned.")
    return url


def render_content(image_map):
    meta = json.loads((ROOT / "meta.json").read_text(encoding="utf-8"))
    blocks = parse_blocks((ROOT / "article.md").read_text(encoding="utf-8").splitlines())
    content = render_blocks(blocks, image_map)
    content += "\n" + render_footer(meta)
    return make_local_srcs_relative(content, ROOT / "out"), meta


def read_last_draft_id():
    path = ROOT / "out" / "last-draft-id.txt"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return None


def save_last_draft_id(media_id):
    path = ROOT / "out" / "last-draft-id.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(media_id, encoding="utf-8")


def update_draft(token, media_id, article):
    payload = {"media_id": media_id, "index": 0, "articles": article}
    return post_json(f"{WECHAT_API}/cgi-bin/draft/update?access_token={token}", payload)


def delete_draft(token, media_id):
    return post_json(
        f"{WECHAT_API}/cgi-bin/draft/delete?access_token={token}",
        {"media_id": media_id},
    )


def main():
    parser = argparse.ArgumentParser(description="Push the article to WeChat draft box")
    parser.add_argument("--config", default=None)
    parser.add_argument("--draft-media-id", default=None)
    parser.add_argument("--new-draft", action="store_true", help="Create a new draft instead of updating the last one.")
    parser.add_argument("--delete-draft-id", default=None)
    args = parser.parse_args()

    if args.config:
        custom = Path(args.config)
        data = json.loads(custom.read_text(encoding="utf-8"))
        config = {
            "app_id": str(data["app_id"]).strip(),
            "app_secret": str(data["app_secret"]).strip(),
            "path": str(custom),
        }
        if "YOUR_" in config["app_id"] or "YOUR_" in config["app_secret"]:
            raise SystemExit(
                f"Config still contains placeholders: {custom}\n"
                "Replace YOUR_APP_ID_HERE and YOUR_APP_SECRET_HERE with real values."
            )
        if "你的" in config["app_id"] or "你的" in config["app_secret"]:
            raise SystemExit(
                f"Config still contains placeholders: {custom}\n"
                "Replace the placeholder AppID and AppSecret with real values."
            )
    else:
        config = load_config()

    article_text = (ROOT / "article.md").read_text(encoding="utf-8")
    meta = json.loads((ROOT / "meta.json").read_text(encoding="utf-8"))
    images = extract_images(article_text, meta.get("cover", ""))
    video_match = re.search(r"@video\[([^\]]+)\]", article_text)
    video_path = video_match.group(1).strip() if video_match else None
    if not images:
        raise SystemExit("No local images found to upload.")

    print(f"Using config: {config['path']}")
    print("Requesting access token...")
    token = get_access_token(config)

    cover_path = ROOT / str(meta.get("cover", ""))
    print(f"Uploading cover: {cover_path}")
    thumb_media_id = upload_cover(token, cover_path)

    image_map = {}
    for path in images:
        if path == meta.get("cover", ""):
            continue
        full_path = ROOT / path
        print(f"Uploading image: {full_path}")
        image_map[path] = upload_body_image(token, full_path)

    print("Rendering final article content...")
    content, meta = render_content(image_map)

    video_media_id = None
    video_iframe = None
    configured_vid = str(meta.get("video_vid", "")).strip()
    if video_path:
        full_video = ROOT / video_path
        if not full_video.exists():
            raise SystemExit(f"Video file not found: {full_video}")
        if configured_vid:
            vid = configured_vid
            cover_url = ""
            print(f"Using configured video vid: {vid}")
        else:
            print(f"Uploading video: {full_video}")
            video_media_id = upload_video(
                token,
                full_video,
                title=meta.get("title", "公众号视频"),
                introduction=meta.get("summary", ""),
            )
            print(f"Video media_id: {video_media_id}")
            vid, cover_url = get_video_vid(token, video_media_id)
            print(f"Video vid: {vid or '(none)'}")
        if vid and not vid.startswith("apiv_"):
            video_iframe = build_video_iframe(vid, cover_url)

    video_placeholder_re = re.compile(
        r'<div class="wechat-video" data-video-src="([^"]*)"[^>]*>.*?</div>',
        re.S,
    )
    if video_path and video_iframe:
        content = video_placeholder_re.sub(video_iframe, content)
    elif video_path:
        content = video_placeholder_re.sub(
            '<p style="margin:16px 0;padding:14px 16px;background:#fff7e6;'
            'border:1px solid #ffd591;border-radius:6px;font-size:14px;'
            'line-height:1.7;color:#8c5a10;">文末视频已上传素材库，'
            '请在公众号后台插入该视频后保存草稿。</p>',
            content,
        )

    local_left = re.findall(r'src="((?!https?://|//|data:)[^"]+)"', content)
    if local_left:
        raise SystemExit(f"Some images were not replaced with WeChat URLs: {local_left}")

    article_payload = {
        "title": meta.get("title", ""),
        "author": meta.get("author", ""),
        "digest": meta.get("summary", ""),
        "content": content,
        "content_source_url": "",
        "thumb_media_id": thumb_media_id,
        "need_open_comment": 1,
        "only_fans_can_comment": 0,
    }

    draft_id = args.draft_media_id
    if draft_id is None and not args.new_draft:
        draft_id = read_last_draft_id()

    if draft_id:
        print("Updating existing draft...")
        update_draft(token, draft_id, article_payload)
        media_id = draft_id
        save_last_draft_id(media_id)
    else:
        print("Pushing new draft...")
        draft = post_json(
            f"{WECHAT_API}/cgi-bin/draft/add?access_token={token}",
            {"articles": [article_payload]},
        )
        media_id = draft.get("media_id")
        if not media_id:
            raise RuntimeError("Draft media_id was not returned.")
        save_last_draft_id(media_id)

    if args.delete_draft_id:
        print(f"Deleting duplicate draft: {args.delete_draft_id}")
        delete_draft(token, args.delete_draft_id)

    (ROOT / "out" / "article.wechat.uploaded.html").write_text(
        build_preview(meta.get("title", ""), content, []),
        encoding="utf-8",
    )
    (ROOT / "out" / "article.wechat.html").write_text(
        build_preview(meta.get("title", ""), content, []),
        encoding="utf-8",
    )
    (ROOT / "out" / "article.wechat.fragment.html").write_text(
        content + "\n",
        encoding="utf-8",
    )

    print("Draft saved successfully.")
    print(f"Draft media_id: {media_id}")
    print(f"Cover media_id: {thumb_media_id}")
    for path, url in image_map.items():
        print(f"Image URL: {path} -> {url}")


if __name__ == "__main__":
    main()
