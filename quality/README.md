# Quality Scripts

Skill 编排流程，脚本执行重活。Skill 绝不亲自调用外部 API 或处理大量数据。

| 脚本 | 用途 | 状态 |
|------|------|------|
| `init_article.py` | 创建文章工作区（从模板初始化 state.json + article.md） | 已完成 |
| `check_duplication.py` | 13 字片段查重，比对 references/private/archive/ | 已完成 |
| `check_forbidden.py` | 违禁词扫描，高风险阻断 / 中低风险警告 | 已完成 |
| `token_count.py` | 字数、段落数、Token 估算，段落超限检查 | 已完成 |
| `format.py` | Markdown → 微信 HTML（优先用 markdown 库，回退正则） | 已完成 |
| `post_publish.py` | 发布后提取数据，追加到 learned/performance.md | 已完成 |

## 发布对接（publish/ 目录）

| 脚本 | 用途 | 状态 |
|------|------|------|
| `publish/push_wechat_draft.py` | 微信草稿推送（access_token 缓存、封面上传、重试、自动回流） | 已完成 |

push_wechat_draft.py 在草稿创建成功后，自动调用本目录的 post_publish.py 完成数据沉淀。

## 完整工作流

```bash
python quality/init_article.py --slug my-article --title "标题" --track "AI编程"
python quality/check_forbidden.py --file articles/my-article/article.md
python quality/check_duplication.py --file articles/my-article/article.md
python quality/token_count.py --file articles/my-article/article.md
python quality/format.py --file articles/my-article/article.md
python publish/push_wechat_draft.py --file articles/my-article/article.html --slug my-article --dry-run
# 确认无误后去掉 --dry-run 实际推送
python publish/push_wechat_draft.py --file articles/my-article/article.html --slug my-article --cover cover.jpg
```

