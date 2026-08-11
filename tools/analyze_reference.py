#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辅助内容优化工具
功能：
1. 读取参考素材与当前稿件
2. 对内容进行中性化处理
3. 统一输出格式
"""

import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
REFERENCES_DIR = BASE_DIR / "references"
ARTICLE_MD = BASE_DIR / "article.md"

# 内容调整映射表
# 命中项统一替换为空字符串，避免留下替身表达。
content_filters = {
    # 替换过于绝对的表述
    r"百分百": "",
    r"100%": "",
    r"绝对": "",
    r"最": "",
    r"顶级": "",
    r"第一": "",
    r"首选": "",
    r"必看": "",
    r"必读": "",
    r"必转": "",
    r"神器": "",
    r"完美": "",
    r"无敌": "",
    r"极致": "",
    # 替换互动诱导类表述
    r"点个赞": "",
    r"点赞": "",
    r"关注": "",
    r"转发": "",
    r"在看": "",
    r"速看": "",
    r"重磅": "",
    r"下次接着聊": "",
    r"记得分享": "",
    r"不转不是中国人": "",
    r"疯传": "",
    r"刷屏": "",
    # 替换运营相关表述
    r"暴力引流": "",
    r"引流": "",
    r"涨粉": "",
    r"截流": "",
    r"霸屏": "",
    r"私域": "",
    r"公域": "",
    r"流量": "",
    r"访问量": "",
    r"获客": "",
    r"变现": "",
    r"吸粉": "",
    # 替换收益承诺类表述
    r"月入过万": "",
    r"日赚千元": "",
    r"稳赚不赔": "",
    r"零风险": "",
    r"躺赚": "",
    r"暴利": "",
    # 替换医疗宣称类表述
    r"包治百病": "",
    r"一针见效": "",
    r"治愈": "",
    r"根除": "",
    r"无副作用": "",
    r"神效": "",
}


def split_sentences(text):
    """按中文句读切分句子。"""
    return re.split(r"(?<=[。！？!?])\s*", text)


def is_usable_sentence(sentence):
    """判断替换后的句子是否还保留完整语义。"""
    core = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]+", "", sentence)
    if not core:
        return False
    if len(core) < 4:
        return False
    if re.match(r"^(的|了|着|和|与|在|也|都|就|把|被|对|从|向|给)", core):
        return False
    if re.search(r"(的|了|着|和|与|在|也|都|就|把|被|对|从|向|给)$", core):
        return False
    return True


def apply_content_filters(text):
    """对输入文本执行内容净化逻辑。"""
    cleaned_sentences = []
    for sentence in split_sentences(text):
        cleaned = sentence
        for pattern in content_filters:
            try:
                cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
            except re.error:
                continue
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        if is_usable_sentence(cleaned):
            cleaned_sentences.append(cleaned)

    result = "".join(cleaned_sentences)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def load_reference_content():
    """加载参考目录下的素材内容。"""
    if not REFERENCES_DIR.exists():
        return ""

    content_parts = []
    for file in sorted(REFERENCES_DIR.iterdir()):
        if file.suffix not in (".txt", ".json"):
            continue
        try:
            if file.suffix == ".json":
                data = json.loads(file.read_text(encoding="utf-8"))
                content_parts.append(data.get("content") or data.get("text") or "")
            else:
                content_parts.append(file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

    return "\n\n".join(part for part in content_parts if part)


def construct_final_output(body):
    """构建最终输出，强制追加标准结尾。"""
    body = re.split(r"我是精神小哥的思绪", body)[0]
    filtered = apply_content_filters(body)
    ending = (
        "\n\n这篇就当是我折腾xxx的一个起点，"
        "后面要是跑通了更稳的流程，我再慢慢写出来。我是精神小哥的思绪。"
    )
    return filtered + ending


def main():
    """主执行逻辑。"""
    if not ARTICLE_MD.exists():
        print("未找到 article.md，请确认文件路径。")
        return

    # 1. 读取当前稿件。
    current_draft = ARTICLE_MD.read_text(encoding="utf-8")

    # 2. 读取参考素材，仅作为上下文备用。
    reference_material = load_reference_content()

    # 3. 此处预留 AI 接口：把 current_draft 和 reference_material 交给模型重写。
    # 当前默认直接处理原稿，保证脚本在无外部依赖时也能运行。
    processed_body = current_draft

    # 4. 强制应用内容净化逻辑。
    filtered_body = apply_content_filters(processed_body)

    # 5. 构建最终输出并写回。
    final_article = construct_final_output(filtered_body)
    ARTICLE_MD.write_text(final_article, encoding="utf-8")
    print("内容优化完成，已更新 article.md")


if __name__ == "__main__":
    main()
