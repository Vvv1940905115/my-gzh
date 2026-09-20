# -*- coding: utf-8 -*-
# check_article.py -- 发布前检查：查重（连续 N 字不重复 + shingle 重复率）与配图资产校验。
# 只用标准库。查重来源默认读 references/archive/（已发文章 / 参考稿的 .md/.txt）。

import argparse
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_LIMIT_DEFAULT = 13
RATE_LIMIT_DEFAULT = 25.0


def resolve_path(p):
    path = Path(p)
    if not path.is_absolute():
        cand = Path.cwd() / path
        if cand.exists():
            return cand.resolve()
        path = ROOT / path
    return path


def read_text(path):
    return path.read_bytes().decode("utf-8-sig", errors="replace")


def default_meta_for(article_path):
    stem = article_path.stem
    if stem == "article":
        return ROOT / "meta.json"
    if stem.startswith("article"):
        return ROOT / ("meta" + stem[len("article"):] + ".json")
    return ROOT / ("meta-" + stem + ".json")


def normalize(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[#>*`|]+", " ", text)
    text = re.sub(r"(?m)^\s*[-+]\s+", " ", text)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[^\w]+", "", text)
    return text.lower()


def collect_source_files(entries):
    files = []
    for entry in entries:
        p = resolve_path(entry)
        if p.is_dir():
            files.extend(
                f for f in sorted(p.rglob("*"))
                if f.is_file()
                and f.suffix.lower() in (".md", ".txt")
                and f.name.lower() != "readme.md"
            )
        elif p.is_file():
            files.append(p)
        else:
            print("来源不存在，跳过: %s" % entry)
    return files


def dedup_check(article_text, source_files, run_limit, rate_limit):
    a_norm = normalize(article_text)
    if len(a_norm) <= run_limit:
        print("文章太短（%d 字），跳过查重" % len(a_norm))
        return True
    grams = [a_norm[i:i + run_limit] for i in range(len(a_norm) - run_limit + 1)]
    source_grams = set()
    worst = (0, "", "")
    for f in source_files:
        b_norm = normalize(read_text(f))
        if len(b_norm) <= run_limit:
            continue
        source_grams.update(b_norm[i:i + run_limit] for i in range(len(b_norm) - run_limit + 1))
        matcher = SequenceMatcher(None, a_norm, b_norm, autojunk=False)
        match = matcher.find_longest_match(0, len(a_norm), 0, len(b_norm))
        if match.size > worst[0]:
            start = max(0, match.a - 8)
            ctx = a_norm[start:match.a + match.size + 8]
            worst = (match.size, a_norm[match.a:match.a + match.size], ctx)
    if not source_grams:
        print("查重来源不足，跳过查重（把已发文章/参考稿放入 references/archive/ 或用 --sources 指定）")
        return True
    hit = sum(1 for g in grams if g in source_grams)
    rate = hit / len(grams) * 100.0
    rate_ok = rate < rate_limit
    run_ok = worst[0] < run_limit
    print("查重来源: %d 个文件" % len(source_files))
    print("%d 字片段重复率: %.1f%%（阈值 <%.0f%%）%s" % (
        run_limit, rate, rate_limit, "PASS" if rate_ok else "FAIL"))
    if worst[0]:
        print("最长连续重复: %d 字（阈值 <%d）%s" % (
            worst[0], run_limit, "PASS" if run_ok else "FAIL"))
        print("  上下文: %s" % worst[2])
        print("  需改写片段: %s" % worst[1])
    else:
        print("最长连续重复: 0 字 PASS")
    return rate_ok and run_ok


def image_refs_in(text):
    refs = []
    for m in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", text):
        ref = m.group(1).strip()
        if not re.match(r"^(https?|data):", ref):
            refs.append(ref)
    return refs


def asset_check(article_text, meta):
    refs = image_refs_in(article_text)
    if meta and meta.get("cover"):
        refs.append(str(meta["cover"]).strip())
    refs = [r for r in refs if r]
    problems = []
    for ref in refs:
        if not resolve_path(ref).exists():
            problems.append(ref)
    print("配图资产检查: 引用 %d 个本地图片路径" % len(refs))
    if problems:
        for ref in problems:
            print("  缺失: %s" % ref)
        print("图片资产: FAIL")
        return False
    print("图片资产: PASS")
    return True


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="发布前检查：查重与配图资产")
    parser.add_argument("--article", default=str(ROOT / "article.md"))
    parser.add_argument("--meta", default=None)
    parser.add_argument("--sources", action="append", default=None,
                        help="查重来源文件或目录，可多次；默认 references/archive/")
    parser.add_argument("--run-limit", type=int, default=RUN_LIMIT_DEFAULT)
    parser.add_argument("--rate-limit", type=float, default=RATE_LIMIT_DEFAULT)
    parser.add_argument("--skip-dedup", action="store_true")
    parser.add_argument("--skip-images", action="store_true")
    args = parser.parse_args()

    article_path = resolve_path(args.article)
    if not article_path.exists():
        sys.exit("Article file not found: %s" % article_path)
    meta_path = resolve_path(args.meta) if args.meta else default_meta_for(article_path)
    meta = None
    if meta_path.exists():
        meta = json.loads(read_text(meta_path))
    else:
        print("meta 不存在，跳过封面检查: %s" % meta_path)

    article_text = read_text(article_path)
    ok = True
    print("== check_article: %s ==" % article_path.name)
    if not args.skip_images:
        ok = asset_check(article_text, meta) and ok
    if not args.skip_dedup:
        entries = args.sources if args.sources else [str(ROOT / "references" / "archive")]
        files = collect_source_files(entries)
        if files:
            ok = dedup_check(article_text, files, args.run_limit, args.rate_limit) and ok
        else:
            print("查重来源: 无可用文件，跳过查重（不是失败）")
    print("结果: %s" % ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
