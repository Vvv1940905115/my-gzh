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
    parts = [
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="media"; filename="{file_path.name}"\r\n'
            "Content-Type: image/png\r\n\r\n"
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
