#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Business flow for pushing a rendered article into the WeChat draft box."""

import argparse
import json
import os
import re
import subprocess
import sys
sys.dont_write_bytecode = True
from pathlib import Path

_PUBLISH_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _PUBLISH_DIR.parent
for _path in (str(_PUBLISH_DIR), str(_PROJECT_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from lib.common import resolve_path as _resolve_path  # noqa: E402
from md_to_wechat import (  # noqa: E402
    ROOT,
    article_slug,
    build_preview,
    default_meta_for,
    make_local_srcs_relative,
    render_footer,
    safe_slug,
)
from wechat_api import (  # noqa: E402
    WECHAT_API,
    delete_draft,
    get_access_token,
    post_json,
    update_draft,
)
from wechat_render import render_article  # noqa: E402
from wechat_upload import (  # noqa: E402
    build_video_iframe,
    extract_images,
    get_video_vid,
    upload_body_image,
    upload_cover,
    upload_video,
)
from quality.stage_gate import require as gate_require  # noqa: E402
from quality.stage_gate import slug_of as gate_slug  # noqa: E402


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


def resolve_path(raw, default_name=None):
    """Resolve a user-supplied path: absolute as-is, else CWD, else project root."""
    return _resolve_path(raw, ROOT, default_name)


def draft_id_path(record_stem):
    """Store one draft-id file per article slug."""
    slug = safe_slug(record_stem)
    if slug == "article":
        return ROOT / "out" / "last-draft-id.txt"
    return ROOT / "out" / f"last-draft-id-{slug}.txt"


def cleanup_push_records(record_stem):
    """Remove temporary records created by this push after manual review."""
    slug = safe_slug(record_stem)
    paths = [
        draft_id_path(slug),
        ROOT / "out" / f"{slug}.wechat.uploaded.html",
        ROOT / "out" / f"{slug}.wechat.html",
        ROOT / "out" / f"{slug}.wechat.fragment.html",
    ]
    for path in paths:
        path.unlink(missing_ok=True)

    out_dir = ROOT / "out"
    if out_dir.exists() and not any(out_dir.iterdir()):
        out_dir.rmdir()


def confirm_cleanup(record_stem):
    """Ask for explicit confirmation before deleting local push records."""
    print("\n请在公众号后台检查草稿内容。")
    while True:
        try:
            answer = input(
                "检查无误后输入 y 删除本地推送记录；输入 n 保留记录："
            ).strip().lower()
        except EOFError:
            print("未收到确认，已保留本地推送记录。")
            return
        if answer in {"y", "yes"}:
            cleanup_push_records(record_stem)
            print("已删除本地推送记录。")
            return
        if answer in {"n", "no"}:
            print("已保留本地推送记录。")
            return
        print("请输入 y 或 n。")


def confirm_archive(article_file, meta_file):
    """Ask whether to archive the published article for dedup."""
    archive_dir = ROOT / "references" / "private" / "archive"
    print("\n文章已发布成功。是否将本篇正文自动归档至 references/private/archive/ 以丰富查重库？")
    while True:
        try:
            answer = input("输入 y 归档 / 输入 n 跳过：").strip().lower()
        except EOFError:
            print("未收到确认，已跳过归档。")
            return
        if answer in {"y", "yes"}:
            archive_dir.mkdir(parents=True, exist_ok=True)
            dest = archive_dir / f"{article_file.parent.name}-{article_file.name}"
            dest.write_text(article_file.read_text(encoding="utf-8"), encoding="utf-8")
            if meta_file.exists():
                meta_dest = archive_dir / f"{meta_file.parent.name}-{meta_file.name}"
                meta_dest.write_text(meta_file.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"已归档至 {dest}")
            return
        if answer in {"n", "no"}:
            print("已跳过归档。")
            return
        print("请输入 y 或 n。")


def render_content(image_map, article_path=None, meta_path=None):
    meta_file = Path(meta_path) if meta_path else ROOT / "meta.json"
    article_file = Path(article_path) if article_path else ROOT / "article.md"
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    content = render_article(article_file.read_text(encoding="utf-8"), image_map)
    content += "\n" + render_footer(meta)
    return make_local_srcs_relative(content, ROOT / "out"), meta


def read_last_draft_id(path=None):
    path = path or ROOT / "out" / "last-draft-id.txt"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return None


def save_last_draft_id(media_id, path=None):
    path = path or ROOT / "out" / "last-draft-id.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(media_id, encoding="utf-8")


def push_draft(
    article=None,
    meta=None,
    config=None,
    config_path=None,
    draft_media_id=None,
    new_draft=False,
    delete_draft_id=None,
    dry_run=False,
    interactive=True,
):
    """Create or update one WeChat draft and return the reusable artifacts.

    ``interactive=False`` is used by the AI workflow so unattended runs do not
    stop at the manual cleanup/archive confirmation prompts.
    """
    article_file = resolve_path(article, "article.md")
    meta_file = resolve_path(meta) if meta else default_meta_for(article_file)
    if not article_file.exists():
        raise SystemExit(f"Article file not found: {article_file}")
    if not meta_file.exists():
        raise SystemExit(f"Meta file not found: {meta_file}")
    record_stem = article_slug(article_file, meta_file)
    id_file = draft_id_path(record_stem)
    out_stem = record_stem

    if config is None:
        if config_path:
            custom = Path(config_path)
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
        elif dry_run:
            config = {"path": "dry-run"}
        else:
            config = load_config()

    print(f"Article: {article_file}")
    print(f"Meta:    {meta_file}")
    print(f"Record key: {record_stem}")
    article_text = article_file.read_text(encoding="utf-8")
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    images = extract_images(article_text, meta.get("cover", ""))
    video_match = re.search(r"@video\[([^\]]+)\]", article_text)
    video_path = video_match.group(1).strip() if video_match else None
    if not images:
        raise SystemExit("No local images found to upload.")

    print(f"Using config: {config.get('path', 'injected config')}")

    if dry_run:
        print("\n=== DRY RUN MODE: no API calls will be made ===")
        print(f"Article: {article_file}")
        print(f"Meta:    {meta_file}")
        print(f"Record key: {record_stem}")
        missing = [img for img in images if not (ROOT / img).exists()]
        if missing:
            print(f"\nWARNING: {len(missing)} image(s) not found:")
            for img in missing:
                print(f"  MISSING: {img}")
        else:
            print(f"\nAll {len(images)} image(s) found.")
        cover = ROOT / str(meta.get("cover", ""))
        if not cover.exists():
            print(f"WARNING: Cover image not found: {cover}")
        content = render_article(article_text, {})
        content += "\n" + render_footer(meta)
        payload = {
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "digest": meta.get("summary", ""),
            "thumb_media_id": "<would-be-uploaded>",
            "need_open_comment": 1,
            "only_fans_can_comment": 0,
        }
        print("\nDraft payload (title/author/digest):")
        for key, value in payload.items():
            print(f"  {key}: {value}")
        print(f"\nContent length: {len(content)} chars")
        out_dir = ROOT / "out"
        out_dir.mkdir(parents=True, exist_ok=True)
        preview_path = out_dir / f"{out_stem}.wechat.dry-run.html"
        preview_path.write_text(
            build_preview(meta.get("title", "Dry Run"), content, []),
            encoding="utf-8",
        )
        print(f"\nPreview written: {preview_path.relative_to(ROOT)}")
        print("Dry run complete. No API calls were made.")
        return {
            "record_stem": record_stem,
            "article_file": str(article_file),
            "meta_file": str(meta_file),
            "preview_file": str(preview_path),
            "images": images,
            "dry_run": True,
        }

    print("Requesting access token...")
    token = get_access_token(config)

    cover_path = ROOT / str(meta.get("cover", ""))
    print(f"Uploading cover: {cover_path}")
    thumb_media_id = upload_cover(token, cover_path)

    image_map = {}
    for path in images:
        full_path = ROOT / path
        print(f"Uploading image: {full_path}")
        image_map[path] = upload_body_image(token, full_path)

    print("Rendering final article content...")
    content, meta = render_content(image_map, article_file, meta_file)

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

    draft_id = draft_media_id
    if draft_id is None and not new_draft:
        draft_id = read_last_draft_id(id_file)

    if draft_id:
        print("Updating existing draft...")
        update_draft(token, draft_id, article_payload)
        media_id = draft_id
        save_last_draft_id(media_id, id_file)
    else:
        print("Pushing new draft...")
        draft = post_json(
            f"{WECHAT_API}/cgi-bin/draft/add?access_token={token}",
            {"articles": [article_payload]},
        )
        media_id = draft.get("media_id")
        if not media_id:
            raise RuntimeError("Draft media_id was not returned.")
        save_last_draft_id(media_id, id_file)
        print(f"Draft id file: {id_file}")

    if delete_draft_id:
        print(f"Deleting duplicate draft: {delete_draft_id}")
        delete_draft(token, delete_draft_id)

    out_dir = ROOT / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    uploaded_preview = out_dir / f"{out_stem}.wechat.uploaded.html"
    preview_file = out_dir / f"{out_stem}.wechat.html"
    fragment_file = out_dir / f"{out_stem}.wechat.fragment.html"
    preview = build_preview(meta.get("title", ""), content, [])
    uploaded_preview.write_text(preview, encoding="utf-8")
    preview_file.write_text(preview, encoding="utf-8")
    fragment_file.write_text(content + "\n", encoding="utf-8")

    print("Draft saved successfully.")
    print(f"Draft media_id: {media_id}")
    print(f"Cover media_id: {thumb_media_id}")
    for path, url in image_map.items():
        print(f"Image URL: {path} -> {url}")
    if interactive:
        confirm_cleanup(record_stem)
        confirm_archive(article_file, meta_file)
    else:
        print("Interactive review skipped; local push records were kept.")

    slug = article_file.parent.name
    print(f"\nRecording publish metrics for '{slug}'...")
    pp = subprocess.run(
        [sys.executable, str(ROOT / "quality" / "post_publish.py"),
         "--slug", slug, "--views", "0"],
        capture_output=True, text=True, cwd=str(ROOT), encoding="utf-8",
    )
    if pp.returncode == 0:
        print(pp.stdout.strip())
    else:
        print(f"WARNING: post_publish failed (exit {pp.returncode}): {pp.stderr.strip()}")

    return {
        "record_stem": record_stem,
        "article_file": str(article_file),
        "meta_file": str(meta_file),
        "preview_file": str(preview_file),
        "fragment_file": str(fragment_file),
        "draft_media_id": media_id,
        "cover_media_id": thumb_media_id,
        "video_media_id": video_media_id,
        "image_map": image_map,
        "dry_run": False,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Push an article to the WeChat draft box"
    )
    parser.add_argument("--config", default=None)
    parser.add_argument(
        "--article",
        default=None,
        help="Markdown file to push (default: article.md). Meta file is inferred.",
    )
    parser.add_argument(
        "--meta",
        default=None,
        help="Meta JSON file (default: meta.json, or inferred from --article).",
    )
    parser.add_argument("--draft-media-id", default=None)
    parser.add_argument("--new-draft", action="store_true", help="Create a new draft instead of updating the last one.")
    parser.add_argument("--delete-draft-id", default=None)
    parser.add_argument("--dry-run", action="store_true",
                        help="Render HTML and validate images without calling the WeChat API.")
    parser.add_argument("--gate", choices=("auto", "strict", "off"), default="auto",
                        help="阶段闸门：auto=无 state.json 时放行，strict=无 state.json 也阻断，off=跳过闸门")
    args = parser.parse_args()
    if args.gate != "off":
        gate_require(
            gate_slug(args.article or (ROOT / "article.md")),
            "publish",
            strict=(args.gate == "strict"),
        )
    push_draft(
        article=args.article,
        meta=args.meta,
        config_path=args.config,
        draft_media_id=args.draft_media_id,
        new_draft=args.new_draft,
        delete_draft_id=args.delete_draft_id,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
