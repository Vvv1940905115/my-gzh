#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenAI-compatible text generator for the WeChat automation workflow."""

import os
import re
import sys

import requests

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"


def post_chat(url, **kwargs):
    """Indirection keeps the network call mockable in tests."""
    return requests.post(url, **kwargs)


def _strip_fence(text):
    text = text.strip()
    match = re.fullmatch(r"```(?:markdown|md)?\s*\n(.*)\n```", text, re.S)
    return match.group(1).strip() if match else text


def build_prompt(task):
    brief = task.get("brief", "")
    audience = task.get("audience", "关注 AI 与效率工具的公众号读者")
    tone = task.get("tone", "务实、具体、不夸张")
    keywords = ", ".join(task.get("keywords", []))
    requirements = "\n".join(f"- {item}" for item in task.get("requirements", []))
    return f"""请写一篇可直接发到微信公众号的 Markdown 文章。

标题：{task['title']}
主题简介：{brief}
目标读者：{audience}
口吻：{tone}
关键词：{keywords or '无'}

写作要求：
- 输出以 # 开头的一级标题。
- 用短段落和小节，避免营销套话和空泛结论。
- 只写可执行、可验证的内容；不要编造数据。
- 如需数据，必须写“来源：...”；没有可靠来源就不要写数字。
- 如使用图片，只使用 ```![](images/ai-generated.png)``` 这个占位符，后续会被替换。
- 结尾给出一个明确行动建议。
{('- ' + requirements) if requirements else ''}
"""


def generate_article(task, api_key=None, base_url=None, model=None, timeout=90):
    """Call an OpenAI-compatible chat endpoint and return Markdown."""
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "No article content and no OPENAI_API_KEY. "
            "Put content_markdown in the task or set OPENAI_API_KEY."
        )
    base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    model = model or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
    response = post_chat(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a senior Chinese WeChat Official Account writer. Return Markdown only.",
                },
                {"role": "user", "content": build_prompt(task)},
            ],
            "temperature": 0.6,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    text = data["choices"][0]["message"]["content"]
    return _strip_fence(text), {
        "generator": "openai-compatible",
        "model": model,
        "base_url": base_url,
    }
