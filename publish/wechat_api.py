#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pure WeChat API layer: HTTP helpers, token cache, retry logic.

No business logic here. Only network I/O, token management, and error handling.
"""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
WECHAT_API = "https://api.weixin.qq.com"
TOKEN_CACHE_FILE = ROOT / "out" / "access-token.json"
RETRY_DELAYS = [2, 4, 8]


def with_retry(fn, max_retries=3):
    """Retry a network call up to max_retries times with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return fn()
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as exc:
            if attempt == max_retries - 1:
                raise
            delay = RETRY_DELAYS[attempt]
            print(f"  Network error (attempt {attempt + 1}/{max_retries}): {exc}")
            print(f"  Retrying in {delay}s...")
            time.sleep(delay)


def read_cached_token():
    """Return a cached access token if still valid (5 min safety buffer)."""
    if not TOKEN_CACHE_FILE.exists():
        return None
    try:
        data = json.loads(TOKEN_CACHE_FILE.read_text(encoding="utf-8"))
        expires_at = data.get("expires_at", 0)
        if time.time() < expires_at - 300:
            return str(data["access_token"]).strip()
    except (json.JSONDecodeError, KeyError, OSError):
        pass
    return None


def save_token_to_cache(token, expires_in=7200):
    """Persist access token and expiry timestamp to the cache file."""
    TOKEN_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {"access_token": token, "expires_at": time.time() + expires_in}
    TOKEN_CACHE_FILE.write_text(json.dumps(data), encoding="utf-8")


def invalidate_token_cache():
    """Remove a stale access token so the next run fetches a fresh one."""
    TOKEN_CACHE_FILE.unlink(missing_ok=True)


def check_error(data):
    errcode = data.get("errcode")
    if errcode is not None and errcode != 0:
        if errcode in (40001, 42001):
            invalidate_token_cache()
            raise RuntimeError(
                f"WeChat API error {errcode}: {data.get('errmsg', 'unknown')}\n"
                "Stale access token detected and cache cleared. Re-run the script to get a fresh token."
            )
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


def get_access_token(config):
    cached = read_cached_token()
    if cached:
        print("Using cached access token.")
        return cached
    query = urllib.parse.urlencode(
        {
            "grant_type": "client_credential",
            "appid": config["app_id"],
            "secret": config["app_secret"],
        }
    )
    data = with_retry(lambda: get_json(f"{WECHAT_API}/cgi-bin/token?{query}"))
    token = data.get("access_token")
    if not token:
        raise RuntimeError("Access token was not returned.")
    expires_in = int(data.get("expires_in", 7200))
    save_token_to_cache(token, expires_in)
    return token


def update_draft(token, media_id, article):
    payload = {"media_id": media_id, "index": 0, "articles": article}
    return post_json(f"{WECHAT_API}/cgi-bin/draft/update?access_token={token}", payload)


def delete_draft(token, media_id):
    return post_json(
        f"{WECHAT_API}/cgi-bin/draft/delete?access_token={token}",
        {"media_id": media_id},
    )
