# my-gzh 公众号文章工程

一个**纯本地**的公众号文章生产流水线：用 Markdown 写正文，转成带内联样式的微信兼容 HTML，既能手动复制进后台，也能通过公众号接口一键同步到草稿箱。

本工程所有截图、配图、HTML 都在本地生成，不依赖任何付费服务。核心脚本只用 Python 标准库即可运行；只有「生成配图」和「抓取参考文章」两步需要额外装包。

---

## 目录结构

```text
my-gzh/
├── article.md                    # 正文，用标准 Markdown 写（含本项目扩展语法）
├── meta.json                     # 标题、摘要、作者、来源、封面、标签
├── README.md                     # 本教程
├── .gitignore                    # 忽略 wechat-config.json，避免泄露凭据
├── wechat-config.example.json    # 配置模板（提交到仓库）
├── wechat-config.json            # 本地公众号凭据（不提交，被 .gitignore 忽略）
├── requirements.txt              # 可选第三方依赖（仅抓取参考文章/生成配图时用）
├── images/                       # 本地素材（被 .gitignore 忽略，不提交）
│   ├── real_robot.jpg            # 正文配图（由 fetch 脚本从 Wikimedia 拉取）
│   ├── real_circuit.jpg
│   ├── ...（real_*.jpg 若干）
│   ├── cover.png / pic1.png      # 由 make_*.py 本地生成的示意图（可选）
│   └── wechat-urls.json          # 手动发布时，填微信图片链接的映射表
├── references/                   # 抓取回来的参考文章（被 .gitignore 忽略）
├── tools/
│   ├── md_to_wechat.py           # Markdown → 微信兼容 HTML + 本地预览页（标准库）
│   ├── push_wechat_draft.py      # 上传图片并同步到公众号草稿箱（标准库）
│   ├── fetch_real_images.py      # 从 Wikimedia Commons 抓取真实可商用图片（标准库）
│   ├── fetch_real_images_retry.py    # 对限流的主题重试抓取（标准库）
│   ├── fetch_real_images_retry2.py   # 替换 3 张质量偏弱的真实图片（标准库）
│   ├── make_mhs_images.py        # 用 Pillow 生成 MHS 主题封面与示意图（需 Pillow）
│   ├── make_article_images.py    # 通用封面/示意图生成器（需 Pillow）
│   ├── fetch_reference.py        # 抓取网页/公众号/知乎文章到 references/（需 requests+trafilatura）
│   └── analyze_reference.py      # 分析 references/ 下的参考素材（标准库）
└── out/                          # 生成结果（被 .gitignore 忽略，不提交）
    ├── article.wechat.html       # 本地预览页，可点「复制正文」
    ├── article.wechat.fragment.html  # 纯片段 HTML（供程序二次处理）
    ├── article.wechat.uploaded.html  # 推送成功后的最终页
    └── last-draft-id.txt         # 记录上次草稿 media_id，用于自动更新
```

> ⚠️ `images/`、`references/`、`out/`、`wechat-config.json` 都在 `.gitignore` 里，**不会提交到仓库**。克隆到新机器后，这些目录需要本地重新生成或配置（详见下文）。

---

## 一、环境准备

### 1. 安装 Python 3.10+

本工程脚本都是 Python 写的，需要本机有 Python 3.10 或更高版本（建议 3.12）。

1. 打开官网 `https://www.python.org/downloads/`，下载 3.10+（建议 3.12）。
2. 安装时**必须勾选 `Add python.exe to PATH`**（Windows 最关键的一步）。
3. 安装完成后，**新开一个终端窗口**（让 PATH 生效），运行：

   ```text
   python --version
   ```

   能看到版本号（如 `Python 3.12.x`）即说明装好。若提示「python 不是内部或外部命令」，通常是没勾选 PATH，重新安装一次即可。

### 2. 第三方依赖（按需安装，不是全部都要）

核心流水线（`md_to_wechat.py`、`push_wechat_draft.py`、三个 `fetch_real_images*.py`、`analyze_reference.py`）**只用 Python 标准库，完全不用装任何第三方包**。

只有下面两种情况需要装包：

| 你想做的事 | 需要的包 | 安装命令 |
| --- | --- | --- |
| 用脚本**生成**封面/示意图（`make_mhs_images.py` / `make_article_images.py`） | Pillow | `python -m pip install pillow` |
| 用脚本**抓取**网页参考文章（`fetch_reference.py`） | requests + trafilatura | `python -m pip install requests trafilatura` |

> 如果你只打算「写 Markdown → 转 HTML → 复制/推送」，且图片已经准备好（或走手动上传），**可以一个包都不装**，直接跳到「二、配置公众号接口」。

一次性把可选依赖都装上也可以：

```text
python -m pip install -r requirements.txt
```

（仓库里的 `requirements.txt` 含 `trafilatura / requests / markdown / lxml`，主要用于 `fetch_reference.py`；`markdown` 与 `lxml` 多为 trafilatura 的传递依赖，装了无害。）

---

## 二、配置公众号接口

只有走「接口同步到草稿箱」模式才需要这一步。若只手动复制正文，可跳过。

### 1. 获取 AppID 和 AppSecret

登录公众号后台 `https://mp.weixin.qq.com/`：

1. 进入「设置与开发」→「基本配置」。
2. 复制 `AppID`（一串 18 位字符）。
3. 点击「查看」或「重置」`AppSecret`。

> AppSecret **只显示一次**，重置后旧值立即失效。复制出来后妥善保存到本地密码管理器，不要截图发到任何群里。

### 2. 填写本地配置文件

把模板复制一份并重命名：

```text
wechat-config.example.json  →  wechat-config.json
```

填入真实值（注意去掉 `YOUR_*` 占位符）：

```json
{
  "app_id": "wx1234567890abcdef",
  "app_secret": "a1b2c3d4e5f6..."
}
```

脚本会按以下顺序查找配置，命中第一个即停止：

1. `~/.codex/skills/wechat-publisher/config.json`
2. 项目根目录下的 `wechat-config.json`（本工程已存在该文件，且被 `.gitignore` 忽略，不会提交）

> 如果你在别的电脑上克隆了本项目，仓库里只有 `wechat-config.example.json`，需要按上面步骤重新创建 `wechat-config.json`。

### 3. 配置 IP 白名单（最常见卡点）

公众号接口要求调用方 IP 在白名单内。

1. 在公众号后台「设置与开发」→「基本配置」→「IP 白名单」里，添加当前电脑的**公网 IP**。
2. 查看公网 IP（任选其一）：

   ```text
   curl https://ipinfo.io/ip
   ```

   或浏览器打开 `https://ipinfo.io/ip`。

3. 如果推送时微信返回：

   ```text
   errcode 40164, invalid ip xxx.xxx.xxx.xxx, not in whitelist
   ```

   就把报错里的 `xxx.xxx.xxx.xxx` 加进白名单。

> ⚠️ 家庭宽带多为动态 IP，换 WiFi / 热点 / 重启光猫后白名单可能又要重加。公司固定 IP 一般一次配置即可。

---

## 三、准备图片素材

本工程有**两套**图片方案，可二选一，也可混用。封面与正文图片都放在 `images/` 下，并在 `article.md` 里用相对路径引用。

### 方案 A：抓取真实可商用图片（推荐，当前文章即用此方案）

`article.md` 当前引用的是 `images/real_robot.jpg`、`real_circuit.jpg`、`real_usbc.jpg`、`real_code.jpg`、`real_arm.jpg`、`real_quantum.jpg`、`real_quad.jpg`、`real_datacenter.jpg`、`real_ai.jpg` 等。这些来自 Wikimedia Commons（CC/PD 协议，可商用），由脚本自动抓取：

```text
python tools/fetch_real_images.py
```

- 脚本会把每张主题的最佳候选缩略图下载到 `images/real_*.jpg`，并打印 `[OK]/[FAIL]/[NONE]` 结果。
- 部分主题若被限流或没拿到好图，再补跑重试脚本（带延时，降低被限流概率）：

  ```text
  python tools/fetch_real_images_retry.py
  python tools/fetch_real_images_retry2.py
  ```

- 抓完请用文件管理器确认 `images/real_*.jpg` 都在；**推送前这一步必须完成**，否则 `push_wechat_draft.py` 会因找不到本地图片而报错。

> 想换主题或换图？直接改这三个脚本顶部的 `TOPICS = [...]` 列表（格式为 `("搜索词", "目标文件名")`），重跑即可。

### 方案 B：本地生成封面/示意图

若你想用自绘的科技风示意图，运行：

```text
python tools/make_mhs_images.py
```

会生成 `images/cover.png`（封面）、`images/pic1.png`（总线对比图）、`images/pic2.png`（落地支点图）。

> 注意：`make_mhs_images.py` 生成的是 `cover.png`，而当前 `meta.json` 的封面字段是 `"cover": "images/real_ai.jpg"`。若改用生成的封面，请把 `meta.json` 里的 `cover` 改成 `images/cover.png`，并在 `article.md` 里把对应插图路径改成 `images/pic1.png` / `images/pic2.png`。两套图不要混着引用同一个不存在的文件。

### 方案 C：手动准备图片（最省事，零脚本）

直接在 `images/` 里放你自己的图（如 `myphoto.jpg`），在 `article.md` 里写 `![说明](images/myphoto.jpg)` 即可。`make_local_srcs_relative` 会自动把路径处理成预览可用的相对路径。

---

## 四、写文章

### 1. 编辑正文 `article.md`

用标准 Markdown 写，并支持以下**本项目扩展语法**：

| 写法 | 效果 |
| --- | --- |
| `#` / `##` / `###` | 一/二/三级标题（左侧蓝条样式） |
| 第一段 | 自动作为「导语」，浅蓝底加粗 |
| `**粗**` `*斜*` `` `代码` `` | 行内样式 |
| `![说明](images/x.jpg)` | 图片（居中圆角） |
| 紧跟图片下一行的 `图注：xxx` | 图片下方居中灰字说明 |
| `> 引用内容` | 金句引用框（浅黄底，左金线） |
| `:::highlight` … `:::` | 高亮提示框（蓝渐变 + ⚡ 图标） |
| `:::note` … `:::` | 笔记框（浅蓝底） |
| `:::quote` … `:::` | 深色金句框 |
| `:::card` … `:::` | 卡片框（首行加 `**` 为标题） |
| `\| 表头 \| 列 \|`（下一行 `---` 分隔） | 表格 |
| `---` | 分隔线 |
| `@video[images/xxx.mp4]` | 视频占位（推送时自动替换为公众号视频 iframe） |

示例片段：

```markdown
## 小标题

第一段会作为导语展示。

![人形机器人](images/real_robot.jpg)
图注：人形机器人是「物理世界」最直观的代表。

:::highlight
一句话总结：MCP 接管软件，MHS 接管硬件。
:::

> 这是一句金句引用。
```

### 2. 编辑元信息 `meta.json`

```json
{
  "title": "文章标题",
  "summary": "文章摘要（用作草稿 digest）",
  "author": "作者名",
  "source": "公众号：公众号名",
  "cover": "images/real_ai.jpg",
  "tags": ["标签1", "标签2"],
  "video_vid": ""
}
```

字段说明：

- `title` / `summary` / `author` / `source`：必填，推送时写入草稿。
- `cover`：封面图路径，**推送时会被作为永久素材上传**，拿 `thumb_media_id`。必须指向 `images/` 下真实存在的文件。
- `tags`：可选，渲染在正文末尾的标签条。
- `video_vid`：可选。若文章用 `@video[...]` 且你已有现成视频 `vid`（如之前上传过的），填这里可跳过重新上传；留空则推送时自动上传 `images/` 下的视频文件并取 `vid`。

### 3. 图片引用规则

- 用相对路径，如 `images/real_robot.jpg`。
- 不要写 `<div class="...">`、不要引入外部 CSS/JS（微信会过滤）。
- 代码块用 ```` ``` ```` 包裹。

---

## 五、本地预览 HTML

运行转换脚本（**标准库，无需装包**）：

```text
python tools/md_to_wechat.py
```

成功后生成：

```text
out/article.wechat.html
```

用浏览器打开这个文件，页面顶部有「复制正文」按钮，点一下即可复制**带内联样式**的微信 HTML，直接粘到公众号后台。

- 若正文里还有本地图片未替换成微信链接，预览页顶部会有黄色提示。
- 纯片段版在 `out/article.wechat.fragment.html`，供程序二次处理。

常用参数（都有默认值，一般不用改）：

```text
python tools/md_to_wechat.py --article article.md --meta meta.json \
       --images-map images/wechat-urls.json --out out/article.wechat.html
```

---

## 六、两种发布方式

### 方式 A：手动复制到公众号后台（免接口、免白名单）

适合偶尔写、不想配接口的情况。

1. 到公众号后台「素材管理」上传 `images/` 里的图片。
2. 复制每张图返回的 `https://mmbiz.qpic.cn/...` 链接。
3. 打开 `images/wechat-urls.json`，按「本地路径 → 微信链接」填好映射：

   ```json
   {
     "images/real_robot.jpg": "https://mmbiz.qpic.cn/xxxx",
     "images/real_circuit.jpg": "https://mmbiz.qpic.cn/yyyy"
   }
   ```

4. 重新运行转换：

   ```text
   python tools/md_to_wechat.py
   ```

5. 打开 `out/article.wechat.html`，点「复制正文」。
6. 到公众号后台新建图文，粘贴正文；上传封面、填标题和摘要，存草稿，人工确认后发布。

> `md_to_wechat.py` 会读取 `wechat-urls.json`，自动把正文里的本地路径替换成你填的微信链接。

### 方式 B：接口同步到草稿箱（自动上传图片）

适合已配好 AppID / AppSecret / IP 白名单的情况。

```text
python tools/push_wechat_draft.py
```

脚本依次执行：

1. 在配置的 `.json` 里读取凭据，调用接口拿 `access_token`。
2. 把 `meta.json` 里 `cover` 指向的封面作为永久素材上传，拿到 `thumb_media_id`。
3. 遍历 `article.md` 里所有本地图片，通过 `media/uploadimg` 上传，拿到 `https://mmbiz.qpic.cn/...` 链接并替换正文路径。
4. 若正文有 `@video[...]`，上传视频并生成公众号视频 iframe（或读取 `meta.json` 的 `video_vid`）。
5. 调用草稿接口，把标题、摘要、作者、正文、封面同步到草稿箱。
6. 把草稿 `media_id` 写入 `out/last-draft-id.txt`。

**草稿更新策略：**

- 第一次运行：新建草稿，并记录 `media_id`。
- 之后再运行：读取 `out/last-draft-id.txt`，**自动更新同一篇草稿**，不会重复建草稿。
- 想强制新建一篇：

  ```text
  python tools/push_wechat_draft.py --new-draft
  ```

- 想更新指定草稿（不用记录文件）：

  ```text
  python tools/push_wechat_draft.py --draft-media-id 草稿ID
  ```

- 想顺手删掉某篇重复草稿：

  ```text
  python tools/push_wechat_draft.py --delete-draft-id 要删的草稿ID
  ```

- 想指定别的配置文件（而不是默认的 `wechat-config.json`）：

  ```text
  python tools/push_wechat_draft.py --config 路径/config.json
  ```

推送完成后，刷新公众号后台「草稿箱」即可看到最新版本。发布前仍建议人工确认一遍。

> 推送要求 `images/` 下的图片和封面**真实存在**（见「三、准备图片素材」）。若图片缺失，会报 `No local images found to upload.` 或上传失败。

---

## 七、参考素材工具（可选）

写稿前想抓取同类文章做素材，可用：

```text
# 抓取一篇网页/公众号/知乎文章，存到 references/
python tools/fetch_reference.py "https://example.com/some-article"

# 分析 references/ 下的素材（提取标题、正文等）
python tools/analyze_reference.py
```

`fetch_reference.py` 需要 `requests` + `trafilatura`（见「一、2」）。公众号链接常有访问限制，抓不到时会提示你手动保存。

---

## 八、常见问题

### `python` 不是内部或外部命令
重装 Python，安装时勾选 `Add python.exe to PATH`，然后**新开终端窗口**。

### `ModuleNotFoundError: No module named 'PIL'`
运行了需要 Pillow 的脚本（`make_mhs_images.py` / `make_article_images.py`）。装一下：
```text
python -m pip install pillow
```

### `ModuleNotFoundError: No module named 'requests'`（或 `trafilatura'）
运行了 `fetch_reference.py`。装一下：
```text
python -m pip install requests trafilatura
```

### `No WeChat config found`
没找到 `wechat-config.json`，也没放到 `~/.codex/skills/wechat-publisher/config.json`。按「二、2」创建并填写。

### `Config found but incomplete`
配置文件里 `app_id` 或 `app_secret` 为空，或还留着 `YOUR_APP_ID_HERE` 这类占位文字。改成真实值。

### `errcode 40164, invalid ip`
当前公网 IP 不在白名单。把报错里的 IP 加到「设置与开发」→「基本配置」→「IP 白名单」（见「二、3」）。

### `errcode 40001 invalid credential`
`app_secret` 填错，或 AppSecret 被重置过。回到后台重新查看/重置并填入。

### `No local images found to upload.`
`article.md` / `meta.json` 里引用的图片在 `images/` 下找不到。先跑 `fetch_real_images.py` 或把图片放进 `images/`。

### 本地预览里图片不显示
先运行 `python tools/md_to_wechat.py`。预览页图片路径应是 `../images/xxx.jpg`。仍看不到就检查图片是否真的在 `images/` 下。

### 复制到后台后图片还是本地路径
手动发布（方式 A）时，要先在「素材管理」上传图片，并把 `mmbiz.qpic.cn` 链接填进 `images/wechat-urls.json`，再重新转换。接口发布（方式 B）会自动上传并替换，无需手动填。

### 封面图和正文图是两套，搞混了
`fetch_real_images*.py` 产出 `real_*.jpg`；`make_mhs_images.py` 产出 `cover.png/pic1.png/pic2.png`。`meta.json` 的 `cover` 与 `article.md` 的图片路径要指向**同一套**实际存在的文件，不要混用。

---

## 九、命令速查

```text
# —— 图片素材 ——
python tools/fetch_real_images.py          # 抓取真实可商用图片到 images/real_*.jpg
python tools/fetch_real_images_retry.py    # 限流主题重试
python tools/fetch_real_images_retry2.py   # 替换 3 张偏弱图片
python tools/make_mhs_images.py            # 生成本地封面/示意图（需 Pillow）

# —— 转换与预览 ——
python tools/md_to_wechat.py               # 转微信兼容 HTML + 预览页

# —— 推送草稿箱 ——
python tools/push_wechat_draft.py                       # 更新上次草稿（默认）
python tools/push_wechat_draft.py --new-draft          # 新建草稿
python tools/push_wechat_draft.py --draft-media-id ID  # 更新指定草稿
python tools/push_wechat_draft.py --delete-draft-id ID # 顺手删重复草稿
python tools/push_wechat_draft.py --config path.json   # 指定配置文件

# —— 参考素材（可选，需 requests+trafilatura）——
python tools/fetch_reference.py "文章URL"
python tools/analyze_reference.py
```

完整推荐流程：

```text
1) 配接口：  cp wechat-config.example.json wechat-config.json   # 填 AppID/AppSecret + 加 IP 白名单
2) 备图片：  python tools/fetch_real_images.py                 # 确认 images/real_*.jpg 到位
3) 写文章：  编辑 article.md 与 meta.json
4) 预览：    python tools/md_to_wechat.py                      # 浏览器打开 out/article.wechat.html
5) 推送：    python tools/push_wechat_draft.py                 # 到后台草稿箱确认
```

---

## 十、安全提醒

- `wechat-config.json` 含 AppSecret，**不要发到群里、不要提交到公开仓库、不要截图展示**。
- 本工程已用 `.gitignore` 忽略它；若把整个文件夹复制给别人，注意别把配置文件一起带出去。
- 若怀疑 AppSecret 泄露，立即登录公众号后台「基本配置」重置 AppSecret（旧值即刻失效）。
- 所有接口调用均使用微信官方接口（`api.weixin.qq.com`）；正文图片必须来自 `media/uploadimg` 返回的 `mmbiz.qpic.cn` 链接，外部图链会被微信过滤。
- 推送成功后仍建议到公众号后台**人工确认一遍**再发布。
