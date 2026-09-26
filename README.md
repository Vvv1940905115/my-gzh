# my-gzh 公众号内容工作台

![Python](https://img.shields.io/badge/Python-3.11%2B-blue) ![Dependencies](https://img.shields.io/badge/Markdown-3.11-blue) ![License](https://img.shields.io/badge/License-MIT-yellow)

一个本地优先的公众号内容生产工程：选题、写作、质检、配图、转微信 HTML、推送草稿箱。核心转换和推送脚本使用 Python 标准库与 Markdown 3.11；参考文章抓取和部分配图脚本需要可选依赖。

## 能力概览

| 目录 | 作用 |
| --- | --- |
| `SKILL.md` | 内容生成与质检流程规范 |
| `templates/` | 标题、摘要、正文结构模板 |
| `articles/` | 按稿件 slug 存放正文和元信息 |
| `publish/` | Markdown 转微信 HTML、上传图片并推送公众号草稿 |
| `quality/` | 发布前综合质检 |
| `image/` | 抓图、候选图管理、封面裁剪、本地示意图生成 |
| `tools/` | 参考文章抓取与只读分析 |
| `references/` | 公共方法、私密素材、敏感词与平台规则 |
| `config/` | 依赖清单和公众号配置模板 |

## 目录结构

```text
my-gzh/
├── SKILL.md
├── README.md
├── LICENSE
├── .gitignore
├── articles/
│   └── <slug>/
│       ├── article.md
│       └── meta.json
├── config/
│   ├── requirements.txt
│   └── wechat-config.example.json
├── lib/
│   └── common.py
├── publish/
│   ├── md_to_wechat.py
│   ├── wechat_render.py
│   └── push_wechat_draft.py
├── quality/
│   ├── check_article.py
│   └── check_assets.py
├── tests/
│   ├── test_contracts.py
│   └── test_quality_and_render.py
├── image/           # 图片工具与主题定义；本地素材放 images/
│   ├── themes.json
│   ├── make_theme_images.py
│   ├── fetch_images.py
│   └── ocr-crops.ps1
├── tools/
│   ├── fetch_reference.py
│   └── analyze_reference.py
├── references/
│   ├── public/
│   ├── private/
│   └── sensitive/
├── templates/
│   ├── viral-titles.md
│   ├── viral-summary.md
│   └── viral-copy.md
├── images/          # 本地素材，不入库
├── out/             # 本地预览与推送记录，不入库
└── private/         # 本地私密数据，不入库
```

> `articles/` 里的 `<slug>` 是稿件标识，例如 `ai-asking-framework`。每个稿件目录必须有一对 `article.md` 和 `meta.json`。`image/` 是脚本与主题定义目录，`images/` 才是本地图片素材目录。

## 环境准备

安装 Python 3.11 或更高版本。Windows 安装时勾选 `Add python.exe to PATH`。

```text
python --version
```

推荐使用虚拟环境隔离依赖（一条命令完成创建 + 安装）：

```text
python -m venv venv
venv\Scripts\activate
pip install -r config/requirements.lock
```

如果你不想用虚拟环境，也可以全局安装：

```text
pip install -r config/requirements.lock
```

核心转换需要 Markdown 3.11。以下任务按需安装：

| 任务 | 命令 |
| --- | --- |
| Markdown 转换 | `python -m pip install markdown==3.11` |
| 抓取参考文章 | `python -m pip install requests trafilatura` |
| 生成或裁剪本地图片 | `python -m pip install pillow` |
| 一次性安装可选依赖 | `python -m pip install -r config/requirements.txt` |

## 配置公众号接口

只在把文章同步到公众号草稿箱时需要配置。手动复制正文可跳过。

1. 复制模板：

```text
config/wechat-config.example.json -> wechat-config.json
```

2. 填入公众号后台拿到的 `app_id` 和 `app_secret`。
3. 在公众号后台「设置与开发」->「基本配置」->「IP 白名单」加入当前公网 IP。

推送脚本按以下顺序查找默认配置。第一项是 Codex 技能环境的显式路径；普通复用者通常只需第二项：

1. `$CODEX_HOME/skills/wechat-publisher/config.json`
2. 项目根目录的 `wechat-config.json`

也可以显式指定：

```text
python publish/push_wechat_draft.py --config 路径/config.json
```

> `wechat-config.json` 含 AppSecret，已被 `.gitignore` 忽略。不要提交、截图或分享。如怀疑泄露，立即在公众号后台重置 AppSecret。

## 稿件结构

推荐每篇文章独立放在 `articles/<slug>/`：

```text
articles/
└── my-new-post/
    ├── article.md
    └── meta.json
```

`meta.json` 示例：

```json
{
  "title": "文章标题",
  "summary": "120 字以内的摘要",
  "author": "作者名",
  "source": "公众号：公众号名",
  "cover": "images/cover.jpg",
  "tags": ["AI", "职场"],
  "video_vid": ""
}
```

封面路径应指向 `images/` 下真实存在的文件。正文里的本地图片也建议使用相对路径，例如 `images/example.jpg`。

## 写作与排版

正文使用标准 Markdown（由 `markdown==3.11` 解析），转换器额外支持公众号特有块：

- `#`、`##`、`###` 标题
- 第一段作为导语
- 图片：`![说明](images/example.jpg)`
- 图注：紧跟图片下一行写 `图注：xxx`
- 引用：`> 内容`
- 高亮框：

```markdown
:::highlight
这里是重点提示。
:::
```

- 笔记框、金句框、卡片框分别使用 `:::note`、`:::quote`、`:::card`
- 表格使用标准 Markdown 表格
- 视频占位：`@video[images/xxx.mp4]`

写作前先读 `SKILL.md` 和 `templates/`。质量评分以 `quality/check_article.py` 的硬指标输出为准，结合 `references/public/quality-score.md` 的四维权重评估。

## 生成预览 HTML

从项目根目录运行：

```text
python publish/md_to_wechat.py --article articles/my-new-post/article.md --meta articles/my-new-post/meta.json
```

默认输出：

```text
out/<slug>.wechat.html
out/<slug>.wechat.fragment.html
```

`<slug>` 是稿件唯一标识：优先读取 `meta.json` 的 `slug` 字段，缺省时用 `articles/` 下的目录名。脚本仍兼容旧入口：根目录存在 `article.md` 和 `meta.json` 时，可直接运行 `python publish/md_to_wechat.py`，输出为 `out/article.wechat.html`。

浏览器打开预览 HTML，点页面顶部的「复制正文」，再粘贴到公众号后台。

## 开发者设置

启用 pre-commit hook（每次 commit 自动跑测试）：

```text
git config core.hooksPath .githooks
```

只需要在新 clone 的环境里执行一次。CI 会在 GitHub Actions 上自动运行，不受本地配置影响。

## 发布前质检

```text
python quality/check_article.py --article articles/my-new-post/article.md
```

该脚本会检查：

- 违禁词：默认读取 `references/sensitive/banned-words.txt`
- 文本重复：13 字连续查重和 shingle 重复率
- 配图资产：`article.md` 与 `meta.json` 引用的本地图片是否存在
- 引用来源：含百分比、倍数、金额、人数等数据的段落没有来源标记时输出 WARN

详细规则、阈值和输出契约见 `references/public/toolchain.md`。引用来源检查只提示人工补充，可用 `--skip-citations` 显式跳过。

运行 python quality/check_assets.py 可全量扫描所有稿件，检查缺失 meta、封面和正文图片，并将清单写入 out/missing-assets.txt。

可用参数：

```text
--meta articles/my-new-post/meta.json
--sources references/private/archive
--banned-words references/sensitive/banned-words.txt
--skip-dedup
--skip-banned
--skip-images
```

## 推送到公众号草稿箱

```text
python publish/push_wechat_draft.py --article articles/my-new-post/article.md
```

脚本会：

1. 解析 `--article` 指定的 Markdown；当文件名是 `article.md` 时，自动读取同目录 `meta.json`。
2. 上传封面和正文本地图片。
3. 生成微信兼容 HTML。
4. 调用公众号草稿接口，写入草稿箱。
5. 在公众号后台检查完成后询问是否删除本地推送记录。

本地推送记录按稿件唯一标识分文件保存：

```text
out/last-draft-id-<slug>.txt
out/<slug>.wechat.html
out/<slug>.wechat.fragment.html
out/<slug>.wechat.uploaded.html
```

推送脚本最后会提示：

- 输入 `y`：确认已检查草稿，删除本地推送记录。
- 输入 `n`：保留本地推送记录。
- 无输入或 EOF：保留记录。

强制新建草稿：

```text
python publish/push_wechat_draft.py --article articles/my-new-post/article.md --new-draft
```

更新指定草稿：

```text
python publish/push_wechat_draft.py --article articles/my-new-post/article.md --draft-media-id 草稿ID
```

> 草稿 ID 与本地记录按稿件唯一标识（`meta.json` 的 `slug` 字段，缺省时为 `articles/` 下的目录名）分文件保存，多篇文章互不覆盖；路径异常时会用路径哈希兜底，保证 key 唯一。

## 图片方案

### Wikimedia Commons

适合科技、器物、公开照片类素材：

```text
python image/fetch_images.py search --query "humanoid robot"
python image/fetch_images.py fetch --source commons --spec "humanoid robot::real_robot.jpg" --retry 3
```

### Pexels

适合人像、校园、生活场景：

```text
python image/fetch_images.py fetch --source pexels --spec "10498787::p01_group.jpg"
python image/fetch_images.py sheet --input-dir images/_candidates --output images/sheet.png
```

流程是先搜索或下载候选图，必要时生成联系表，人工挑选后用图片 ID 或 Commons 查询词下载高清图。

### 本地生成

```text
python image/make_theme_images.py --list
python image/make_theme_images.py --theme article
python image/fetch_images.py crop --input images/p01_group.jpg --output images/cover.jpg --ratio 1200:510
```

生成图片依赖 Pillow。生成的封面建议裁剪为 1200×510，符合公众号 2.35:1 首图比例。

### 手动准备

把图片放入 `images/`，在 `article.md` 引用：

```markdown
![图片说明](images/example.jpg)
```

## 参考素材

抓取网页或文章：

```text
python tools/fetch_reference.py "https://example.com/article"
```

只读分析素材和稿件：

```text
python tools/analyze_reference.py --slug my-new-post
```

`references/` 分层如下：

| 目录 | 用途 | 是否入库 |
| --- | --- | --- |
| `references/public/` | 风格、评分、热点、爆款分析方法 | 入库 |
| `references/private/` | 知识库、选题库、历史归档 | 不入库 |
| `references/sensitive/` | 违禁词、平台规则 | 不入库 |

## 数据备份

`references/private/` 与 `references/sensitive/` 不入库，只存在于本机磁盘；磁盘一旦损坏，归档、选题库和知识库会直接丢失。请定期执行：

```text
bash backup_private.sh               # Linux/macOS/Git Bash；--encrypt 用 AES-256 加密
powershell -File backup_private.ps1  # Windows 无 bash 时的打包方案（用系统自带 tar）
```

加密功能需要 openssl 环境（Git Bash、Linux、macOS）。加密归档的还原命令：

```text
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -in private-<时间戳>.tar.gz.enc -out restore.tar.gz
```

生成后把归档复制到云盘、私有 Git 仓库或另一台机器。`backups/` 已在 .gitignore 中排除，建议每周至少备份一次，发布重要文章后立即备份。

## 常用流程

```text
1) 明确选题和目标读者
2) 读 SKILL.md、templates/ 和 references/public/
3) 写 articles/<slug>/article.md 与 articles/<slug>/meta.json
4) 准备或确认 images/ 下的图片
5) python quality/check_article.py --article articles/<slug>/article.md
6) python quality/check_assets.py
7) python publish/md_to_wechat.py --article articles/<slug>/article.md --meta articles/<slug>/meta.json
8) 浏览器检查 out/<slug>.wechat.html
9) python publish/push_wechat_draft.py --article articles/<slug>/article.md
10) 到公众号后台人工确认草稿
11) 确认无误后，在终端输入 y 清理本地推送记录
```

## 常见问题

### `python` 不是内部或外部命令

重新安装 Python，勾选 `Add python.exe to PATH`，然后新开终端。

### 找不到 `No WeChat config found`

确认 `wechat-config.json` 在项目根目录，或用 `--config` 显式指定配置文件。

### `Config found but incomplete`

`app_id` 或 `app_secret` 为空，或仍保留 `YOUR_*` 占位符。

### `errcode 40164`

当前公网 IP 不在公众号 IP 白名单内。

### `No local images found to upload.`

`article.md` 或 `meta.json` 引用的图片不存在。先补齐 `images/` 下的文件。

### 预览页图片不显示

确认图片相对路径正确，并从项目根目录运行转换脚本。

### 推送后找不到预览 HTML

检查 `out/`。如果推送后输入了 `y`，本地预览和推送记录会被删除；这是确认后的预期行为。

## 安全提醒

- 不要提交或分享 `wechat-config.json`。
- 不要提交 `private/`、`references/private/`、`references/sensitive/`、`images/`、`out/`。
- 公众号文章必须经过人工事实核查、违禁词审查和后台预览。
- 推送脚本只写入公众号草稿箱，不会群发。

## License

MIT。