# PaperLens — 论文深度解剖、跨文对比与文献汇报工作台

> 把任意学术论文 PDF（或 Zotero 文献库）丢进 **PaperLens**，自动完成：**双栏版面精准逐段切图 + 高清图表裁切 + 六大核心维度深度剖析 + 可点击交互式思维导图（丝滑分屏联动） + 零基础大白话翻译与术语库 + 点击 `[Ref #]` 实时展开引文溯源 + GitHub/SI 自动抓取 + 同方向多文对比与关联图谱 + 可编辑文献汇报 PPT 生成（原生集成 `ppt-master`）**。

## 目录
- [核心功能一览](#核心功能一览)
- [零基础部署到自己电脑（5 分钟上手）](#零基础部署到自己电脑5-分钟上手)
  - [第 1 步：安装系统前置依赖（Python + Poppler）](#第-1-步安装系统前置依赖python--poppler)
  - [第 2 步：下载代码并安装 Python 依赖](#第-2-步下载代码并安装-python-依赖)
  - [第 3 步：启动本地 Web 工作台](#第-3-步启动本地-web-工作台)
  - [第 4 步：配置大模型（开启 AI 深度解读与跨文对比）](#第-4-步配置大模型开启-ai-深度解读与跨文对比)
  - [第 5 步（可选）：连接 Zotero 与 ppt-master](#第-5-步可选连接-zotero-与-ppt-master)
- [完整使用流程说明](#完整使用流程说明)
- [CLI 命令行用法](#cli-命令行用法)
- [常见问题排查（FAQ）](#常见问题排查faq)
- [目录结构](#目录结构)

---

## 核心功能一览

1. **六大维度总览 & 交互式思维导图（丝滑分屏联动）**
   - 自动提炼：研究背景 / 研究目的 / 核心方法 / 验证体系 / 核心结果 / 创新与批判性审读，附全局逻辑闭环与零基础看图指南；
   - **论文全局思维导图**：点击任意节点后，导图**丝滑收窄停靠到左侧**，右侧自动滚动并高亮对应原文段落或图表，实现“左图导航、右文精读”。
2. **逐段切片精读（英中双语 + 零基础大白话 + 图表穿插）**
   - 精准识别双栏学术排版阅读顺序，为每一段提供：**原文高清截图 + 英文原文 + 中文精译 + 写作作用 + 零基础类比 + 可点击术语词条**；
   - 自动裁切论文 Figure/Table 并按上下文穿插解读；顶栏支持一键开关 **「大白话模式」** 与深浅色主题。
3. **实时引文溯源 (`[Ref #]`) & 关联资源自动抓取**
   - 点击正文任意 `[Ref #]` 在右侧抽屉实时展示完整书目、引用上下文跳转，并在线查询 Crossref / Europe PMC / Semantic Scholar 获取摘要、被引数与 OA 链接（本地缓存）；
   - 自动抓取文中提到的 GitHub 仓库（含目录树与 README）、DOI、Supporting Information 与在线工具。
4. **研究课题侧边栏（拖拽分类） & Zotero / MCP 一键导入**
   - 左侧管理自定义研究课题，支持**按住文献卡片直接拖拽到目标课题**（或拖到「未分类文献」移出，按住 `Option/Alt` 拖放可复制到多课题），也支持点击卡片 `🏷️ 分类` 多选；
   - 直接以安全只读快照读取本机 Zotero 文献库，按分类批量导入已下载 PDF。
5. **同方向文章对比关联 (`⚖️ 文章对比关联`)**
   - 支持 **⚡ 瞬时并排对比**（六大维度对齐 + 共同引文/直接互引/共享模型数据库）与 **✨ AI 跨文深度对比**（零基础流派对决、交互式 SVG 关联网络图、AI 精炼维表、互补融合机会 vs 范式分歧、下一步课题创新 Idea），支持导出 Markdown 对比综述。
6. **文献汇报 PPT 工作台（原生集成 `ppt-master`）**
   - 先选择视觉风格、汇报对象、汇报重点与信息密度，自动生成可修改的汇报 PPT 与逐页演讲稿；若本机安装了 `ppt-master`，自动走完 SVG 质检 + `.pptx` 编译，并支持网页内唤起可视化编辑器二次精修。

---

## 零基础部署到自己电脑（5 分钟上手）

> 全程本地运行，不依赖 Node.js 或前端构建工具，仅需 **Python 3.10+** 与 **Poppler**。

### 第 1 步：安装系统前置依赖（Python + Poppler）

PaperLens 使用 **Poppler**（`pdftotext` / `pdftoppm` / `pdfinfo`）进行双栏 PDF 坐标解析与高清切图，请按你的操作系统安装：

#### macOS
```bash
# 如未安装 Homebrew，可先访问 https://brew.sh 安装
brew install poppler python
```

#### Windows
推荐方式 A（使用 winget）：
```powershell
winget install Python.Python.3.12
winget install oschwartz10612.Poppler
```
或推荐方式 B（已装 Anaconda / Miniconda 的同学最省心）：
```powershell
conda create -n paperlens python=3.11 poppler -y
conda activate paperlens
```
> 安装完成后，重新打开一个终端验证：`pdftotext -v` 和 `python --version`（或 `python3 --version`）均有版本号输出即成功。

#### Ubuntu / Debian Linux
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv poppler-utils
```

---

### 第 2 步：下载代码并安装 Python 依赖

```bash
# 1. 克隆仓库到本地
git clone https://github.com/OliverHz-0/Paper_Lens.git
cd Paper_Lens

# 2. 创建并激活独立虚拟环境（推荐，避免污染系统 Python）
python3 -m venv .venv

# macOS / Linux 激活：
source .venv/bin/activate
# Windows PowerShell 激活：
# .\.venv\Scripts\Activate.ps1

# 3. 安装 Python 依赖（仅 4 个轻量包，约 10 秒完成）
pip install -r requirements.txt
```

---

### 第 3 步：启动本地 Web 工作台

```bash
python3 -m paperlens serve --host 127.0.0.1 --port 8765
```
看到终端输出：
```text
PaperLens server running at http://127.0.0.1:8765
```
打开浏览器访问 **http://127.0.0.1:8765** 即可进入 PaperLens 工作台！

> **提示**：如需修改端口（例如 8765 已被占用），改成 `--port 8899` 即可；如需局域网内其他设备访问，可使用 `--host 0.0.0.0`。

---

### 第 4 步：配置大模型（开启 AI 深度解读与跨文对比）

不配置大模型也可以完成 PDF 双栏切图、图表裁切、引文溯源与 GitHub 抓取；配置大模型后即可解锁**六大维度深度剖析、逐段中文精译、大白话类比、思维导图与 AI 跨文对比**。

点击页面右上角 **⚙️ 设置** 图标，支持两种接入方式：

#### 方式 A：使用任意 OpenAI 兼容 HTTP API（推荐大多数用户）
在设置弹窗中将模型引擎切换为 **HTTP API（OpenAI 兼容接口）**，点击对应厂商快捷预设或手动填写：

| 服务商 | Base URL | 推荐模型示例 |
| :--- | :--- | :--- |
| **DeepSeek**（国内直连性价比高） | `https://api.deepseek.com/v1` | `deepseek-chat` / `deepseek-reasoner` |
| **Google Gemini**（OpenAI 兼容端点） | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemini-2.5-pro` / `gemini-2.5-flash` |
| **OpenAI** | `https://api.openai.com/v1` | `gpt-4.1` / `gpt-4o` |
| **OpenRouter** | `https://openrouter.ai/api/v1` | `google/gemini-2.5-pro` / `anthropic/claude-sonnet-4` |
| **本地 Ollama**（完全离线免费） | `http://127.0.0.1:11434/v1` | `qwen2.5:14b` / `llama3.1`（API Key 可留空） |

- 填好 `Base URL`、`API Key`、`Model`（如需代理可填 `HTTP 代理`，如 `http://127.0.0.1:7890`）；
- 点击 **「🧪 测试连接」**，显示绿色连通提示后点击 **「保存设置」**。
- 所有配置均保存在你本机的 `~/.paperlens/config.json`，不会写入项目代码目录。

*(也支持通过环境变量启动覆盖：`PAPERLENS_API_KEY`、`PAPERLENS_BASE_URL`、`PAPERLENS_MODEL`、`HTTPS_PROXY`。)*

#### 方式 B：使用 Antigravity CLI (`agy`)（零 API Key）
若本机已安装并登录 Antigravity CLI（`agy`），在设置中选择 **Antigravity CLI (`agy`)**，即可免 API Key 直接调用 `gemini-4-neon-high` 等模型。

---

### 第 5 步（可选）：连接 Zotero 与 `ppt-master`

这两个集成均为**可选增强**，不安装也不影响 PaperLens 其余全部功能：

1. **连接本机 Zotero 文献库**
   - 默认自动检测 `~/Zotero`（Windows 通常为 `C:\Users\<你的用户名>\Zotero`），如路径不同可在 **⚙️ 设置 → Zotero 数据目录** 修改；
   - 若同时打开了 Zotero 7，建议在 Zotero 设置 → 高级中勾选 **「允许此计算机上的其他应用程序与 Zotero 通信」**（开启 Local API `23119` 端口）；
   - 点击左侧栏底部 **「从 Zotero / MCP 导入」** 即可浏览分类并勾选批量导入 PDF。
2. **原生集成 `ppt-master`（高颜值 SVG → PPTX 管线）**
   - 如希望文献汇报 PPT 直接走 [`ppt-master`](https://github.com/hughes-y/ppt-master) 官方工具链与可视化 SVG 编辑器，将 `ppt-master` 克隆到 `~/ppt-master`（或在 **⚙️ 设置 → ppt-master 目录** 填入实际路径）并完成其 Python 依赖安装；
   - PaperLens 会自动检测并在 **`📽️ 文献汇报 PPT`** 页面启用完整 `ppt-master` 流水线；未安装时会自动降级使用内置的 `python-pptx` 引擎导出可编辑 `.pptx`。

---

## 完整使用流程说明

1. **导入论文**
   - 点击顶部 **「＋ 上传 PDF」** 拖入本地论文 PDF（勾选「上传后立即执行 AI 深度解读」），或从左下角 **Zotero** 一键批量导入。
2. **左侧课题分类与拖拽整理**
   - 点击左侧 **「+ 新建课题」** 按研究方向建组；
   - 按住任意文献卡片左侧 `⋮⋮` **直接拖拽到上方目标课题**完成归类（拖到「未分类文献」可移出，按住 `Option/Alt` 拖放可复制到多个课题），也可点击卡片上的 **`🏷️ 分类`** 按钮多选所属课题。
3. **快速把握全篇 → 逐段精读**
   - 先看 **`🧭 六大维度总览`** 了解研究脉络与大白话类比；
   - 点击 **`🗺️ 论文全局思维导图`** 中的任意节点，导图自动丝滑停靠至页面左侧，右侧直接跳转到对应原文段落或精读图表；
   - 遇到不懂的术语点击彩色词条看大白话解释；遇到 `[Ref #]` 点击直接右侧展开引文溯源。
4. **跨论文横向对比与找关联**
   - 切换顶部 **`⚖️ 文章对比关联`**，按课题筛选并勾选 2 篇及以上论文；
   - 点 **「⚡ 瞬时并排对比」** 立刻查看六大维度并排表与客观共享线索，或点 **「✨ 深度对比与关联挖掘」** 生成交互式关联网络图、流派对比与下一步课题 Idea，并可导出 `.md`。
5. **一键制作文献汇报 PPT**
   - 切换顶部 **`📽️ 文献汇报 PPT`**，在向导中选好风格模板、听众对象（如组会/零基础跨学科/答辩）和重点维度，生成后支持在线修改大纲/演讲稿、调用 SVG 编辑器精修并下载 `.pptx`（含演讲者备注）。

---

## CLI 命令行用法

除了 Web 界面，也可以在终端直接调用底层管线进行批处理：

```bash
# 1. 启动 Web 服务
python3 -m paperlens serve --host 127.0.0.1 --port 8765

# 2. 解析一篇新 PDF（双栏切段截图 + 裁图 + 抓取 GitHub/SI）
python3 -m paperlens ingest /path/to/paper.pdf

# 3. 解析并同时调用已配置的大模型生成零基础深度解读
python3 -m paperlens ingest /path/to/paper.pdf --llm

# 4. 实时溯源某篇论文的第 33 条参考文献
python3 -m paperlens trace-ref <paper_id> 33

# 5. 重新在线抓取某篇论文的 GitHub 仓库与 DOI/SI 资源
python3 -m paperlens fetch-resources <paper_id> --force

# 6. 导出带原文截图与大白话解读的 Markdown 深度报告
python3 -m paperlens export-md <paper_id> -o report.md
```

---

## 常见问题排查（FAQ）

- **上传 PDF 报错 `FileNotFoundError: pdftotext` 或 `pdftoppm` 找不到？**
  - 说明系统未安装 **Poppler** 或未加入环境变量 `PATH`。请按 [第 1 步](#第-1-步安装系统前置依赖python--poppler) 安装 Poppler 后重开终端，运行 `pdftotext -v` 确认可用再重启 PaperLens。
- **启动后页面空白，提示没有论文？**
  - 为避免版权与体积问题，GitHub 仓库默认不包含 `data/` 下的示例 PDF。点击顶部 **「＋ 上传 PDF」** 或左下角 **「Zotero 导入」** 导入你的第一篇论文即可。
- **点击 AI 深度解读提示连接失败或超时？**
  - 点击右上角 **⚙️ 设置**：若本机没有安装 `agy`，请将模型引擎切换为 **HTTP API（OpenAI 兼容接口）** 并填入有效 API Key；如果访问 OpenAI / Gemini 需要网络代理，请在设置中填入本机 `HTTP 代理`（如 `http://127.0.0.1:7890`）后点「测试连接」。
- **端口 `8765` 被占用怎么办？**
  - 启动命令换一个端口即可：`python3 -m paperlens serve --port 8899`，然后访问 `http://127.0.0.1:8899`。
- **数据存放在哪里？如何备份或迁移？**
  - 所有导入的论文切图、AI 解读、课题分类与跨文对比报告都以纯文件形式保存在项目目录下的 `data/` 文件夹中；模型与路径配置保存在 `~/.paperlens/config.json`。迁移电脑时直接复制这两处即可完整恢复。

---

## 目录结构

```text
Paper_Lens/
├── paperlens/                 # Python 后端核心管线与 HTTP 服务
│   ├── __main__.py            # CLI 入口（serve / ingest / trace-ref / fetch-resources / export-md）
│   ├── server.py              # 零依赖多线程 HTTP API 与静态资源服务
│   ├── pdf_parser.py          # 双栏 PDF 版面解析、逐段切图、图表裁切与 XML 清洗
│   ├── llm_analyzer.py        # 两阶段大模型深度剖析（agy CLI & OpenAI 兼容 API）
│   ├── comparator.py          # 跨论文客观线索提取与 AI 深度对比/关联图谱引擎
│   ├── ref_tracer.py          # 参考文献实时溯源（Crossref / Europe PMC / Semantic Scholar）
│   ├── resource_fetcher.py    # GitHub 仓库、DOI 与 SI 自动抓取
│   ├── topics.py              # 研究课题管理与文献拖拽分类持久化
│   ├── zotero_bridge.py       # 本机 Zotero SQLite/Storage & Zotero MCP 桥接
│   ├── ppt_studio.py          # 文献汇报 PPT 结构化大纲与导出引擎
│   ├── ppt_master_bridge.py   # 本机 ppt-master 完整工具链原生集成
│   ├── exporter.py            # 单篇论文 Markdown 深度报告导出
│   └── config.py              # 本地配置管理（~/.paperlens/config.json）
├── web/                       # 零构建依赖交互式前端
│   ├── index.html             # 工作台主页面与模态框
│   ├── styles.css             # 完整双主题响应式样式系统
│   ├── app.js                 # 核心阅读器、思维导图分屏与引文溯源抽屉
│   ├── studio.js              # 课题侧边栏（拖拽分类）、Zotero 导入与 PPT 工作台
│   └── compare.js             # 跨论文对比与交互式 SVG 关联网络图
├── scripts/                   # 示例与辅助脚本
├── requirements.txt           # Python 依赖清单
└── .gitignore                 # 自动忽略本地 data/ 论文文件与缓存
```
