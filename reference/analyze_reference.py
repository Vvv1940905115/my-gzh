#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读分析参考素材，并报告当前稿件中的高风险表述。

这个工具不修改当前稿件。若确实要导出分析结果，必须显式传入 --output。
"""

import argparse
import json
import re
import sys
from pathlib import Path


def configure_stdio():
    for stream in (sys.stdout, sys.stderr):
        if stream and stream.encoding.lower() not in ("utf-8", "utf8"):
            stream.reconfigure(encoding="utf-8", errors="replace")


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ARTICLE = BASE_DIR / "article.md"
REFERENCES_DIR = BASE_DIR / "references"

RISK_PATTERNS = {
    "绝对化表述": [r"百分百", r"100%", r"绝对", r"顶级", r"第一", r"首选"],
    "互动诱导": [r"必看", r"必读", r"必转", r"速看", r"不转不是中国人"],
    "流量运营": [r"暴力引流", r"引流", r"涨粉", r"截流", r"霸屏"],
    "收益承诺": [r"月入过万", r"日赚千元", r"稳赚不赔", r"零风险", r"躺赚"],
    "医疗宣称": [r"包治百病", r"一针见效", r"根除", r"无副作用", r"神效"],
}


def iter_reference_files(references_dir):
    """收集文本类参考素材；跳过敏感目录。"""
    if not references_dir.exists():
        return []

    files = []
    for path in references_dir.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(references_dir)
        if relative.parts and relative.parts[0] == "sensitive":
            continue
        if path.suffix.lower() in {".txt", ".md", ".json"}:
            files.append(path)
    return sorted(files)


def read_reference(path):
    """读取单份参考素材，损坏文件不阻断分析。"""
    try:
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return str(data.get("content") or data.get("text") or "")
            if isinstance(data, list):
                return "\n".join(str(item) for item in data)
            return str(data)
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return ""


def scan_text(text):
    """按风险类别统计命中次数，并返回最小上下文。"""
    findings = []
    for category, patterns in RISK_PATTERNS.items():
        for pattern in patterns:
            matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))
            if not matches:
                continue
            examples = []
            for match in matches[:3]:
                start = max(0, match.start() - 12)
                end = min(len(text), match.end() + 12)
                examples.append(text[start:end].replace("\n", " "))
            findings.append({
                "category": category,
                "pattern": pattern,
                "count": len(matches),
                "examples": examples,
            })
    return sorted(findings, key=lambda item: (-item["count"], item["category"], item["pattern"]))


def parse_args():
    parser = argparse.ArgumentParser(description="只读分析参考素材和当前稿件风险表述")
    parser.add_argument("--article", default=str(DEFAULT_ARTICLE), help="当前稿件路径，默认 article.md")
    parser.add_argument("--references", default=str(REFERENCES_DIR), help="参考素材目录，默认 references/")
    parser.add_argument("--output", default=None, help="可选分析报告输出路径；不会写入稿件")
    parser.add_argument("--force", action="store_true", help="允许覆盖已存在的 --output 文件")
    return parser.parse_args()


def resolve_project_path(path_text):
    path = Path(path_text)
    return path if path.is_absolute() else BASE_DIR / path


def build_report(article_path, article_text, reference_files, reference_text, findings):
    lines = [
        f"稿件: {article_path}",
        f"稿件字数: {len(re.sub(r'\s', '', article_text))}",
        f"参考文件数: {len(reference_files)}",
        f"参考素材字数: {len(reference_text)}",
        "",
        "风险命中:",
    ]
    if not findings:
        lines.append("- 无")
    for item in findings:
        examples = " / ".join(item["examples"])
        lines.append(f"- [{item['category']}] {item['pattern']} x{item['count']}：{examples}")
    return "\n".join(lines) + "\n"


def main():
    configure_stdio()
    args = parse_args()
    article_path = resolve_project_path(args.article)
    references_path = resolve_project_path(args.references)

    if not article_path.exists():
        print(f"未找到当前稿件：{article_path}", file=sys.stderr)
        return 2

    reference_files = iter_reference_files(references_path)
    reference_text = "\n\n".join(
        content
        for path in reference_files
        for content in [read_reference(path)]
        if content
    )
    article_text = article_path.read_text(encoding="utf-8")
    findings = scan_text(article_text)
    report = build_report(article_path, article_text, reference_files, reference_text, findings)

    print(report, end="")

    if args.output:
        output_path = resolve_project_path(args.output)
        if output_path.resolve() == article_path.resolve():
            print("拒绝将分析报告写回当前稿件。", file=sys.stderr)
            return 2
        if output_path.exists() and not args.force:
            print(f"输出文件已存在，如需覆盖请加 --force：{output_path}", file=sys.stderr)
            return 2
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        print(f"分析报告已写入：{output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())