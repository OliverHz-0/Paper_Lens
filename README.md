# PaperLens — 论文深度解剖、跨文对比与文献汇报工作台

> 把任意学术论文 PDF（或 Zotero 文献库）丢进 **PaperLens**，自动完成：**双栏版面精准逐段切图 + 高清图表裁切 + 六大核心维度深度剖析 + 可点击交互式思维导图（丝滑分屏联动） + 零基础大白话翻译与术语库 + 点击 `[Ref #]` 实时展开引文溯源 + GitHub/SI 自动抓取 + 同方向多文对比与关联图谱 + 可编辑文献汇报 PPT 生成（原生集成 `ppt-master`）**。

---

## 核心特性

### 1. 六大维度总览 & 交互式思维导图（丝滑分屏联动）
- **六大维度结构化剖析**：研究背景 / 研究目的 / 核心方法 / 验证体系 / 核心结果 / 创新与批判性审读，附全局研究逻辑闭环与零基础看图指南；
- **论文全局思维导图**：以左右双翼大地图形式呈现论文逻辑脉络，支持缩放与全屏；点击任意节点后，思维导图**丝滑收窄停靠至页面左侧**，右侧自动精准滚动并高亮对应的原文切片或精读图表，实现“左图导航、右文精读”。

### 2. 从头到尾逐段切片精读（英中双语 + 零基础大白话 + 图表穿插）
- 基于 Poppler (`pdftotext -bbox-layout` + `pdftoppm`) 与 Pillow 实现双栏学术论文精准阅读顺序切分与段落高清截图；
- 每段同步展示：**原文高清截图 + 英文原文 + 中文精译 + 写作作用定位 + 零基础大白话类比 + 可点击术语词条**；
- 论文核心图表与数据表自动裁切并按上下文穿插在对应章节，配有逐图/逐子图解读与正文关联说明；
- 顶栏提供 **「大白话模式」** 一键开关与深浅色主题切换。

### 3. 实时展开引文溯源 (`[Ref #]`) & 关联资源自动抓取
- 自动解析全部参考文献与正文行内引用角标；点击任意 `[Ref #]` 在右侧抽屉实时展示完整书目、引用上下文跳转，并在线查询 Crossref / Europe PMC / Semantic Scholar 获取摘要、被引数与 OA 链接（本地自动缓存）；
- 自动识别正文（含跨行折断 URL）中的 GitHub 仓库、DOI、Supporting Information 与在线工具，拉取仓库结构与 README。

### 4. 研究课题侧边栏（拖拽分类） & Zotero / MCP 一键导入
- **左侧研究课题管理**：自由新建/删除课题、按课题筛选文献；
- **拖拽归类 & 卡片内快捷改分类**：按住文献卡片 `⋮⋮` 直接拖放到目标课题（或拖到「未分类文献」移出，按住 `Option/Alt` 拖放可复制到多课题），也可点卡片上的 `🏷️ 分类` 展开多选浮层；
- **Zotero / Zotero MCP 连接器**：安全只读快照读取本机 `~/Zotero/zotero.sqlite` + `~/Zotero/storage`（支持 Zotero 7 Local API 与 Zotero MCP 握手探测），按分类批量导入已下载 PDF 并自动同步课题。

### 5. 同方向文章对比关联 (`⚖️ 文章对比关联`)
- 按研究课题筛选并勾选 2 篇及以上论文，支持 **双模式对比**：
  - **⚡ 瞬时并排对比**：0 秒对齐六大核心维度，自动挖掘共同引文（Bibliographic Coupling）、直接互引关系与共享模型/数据库/概念；
  - **✨ AI 跨文深度对比与关联挖掘**：自动输出全景定位、零基础流派对决类比、每篇论文流派角色/优势/短板卡、**交互式 SVG 论文关联网络图**（`方法互补` / `技术演进` / `范式分歧` / `靶标重叠` / `证据互印`）、AI 精炼对比矩阵、互补融合机会 vs 范式张力，以及下一步可落地课题创新切入点；
- 支持对比报告历史保存、切换与一键导出 Markdown 对比综述。

### 6. 文献汇报 PPT 制作工作台（原生集成 `ppt-master`）
- 制作前通过向导配置**视觉风格模板、汇报对象、汇报重点、信息密度与转场动画**；
- 若本机已安装 [`ppt-master`](https://github.com/hughes-y/ppt-master)（默认检测 `~/ppt-master`，可在设置中自定义路径），自动跑通其官方完整管线：项目初始化 → 1280×720 语义化 SVG 生成 → 演讲稿切分 → SVG 质量检查 → `.pptx` 编译（含演讲者备注），并支持在网页内直接唤起官方 SVG 实时可视化编辑器二次精修与重新编译。

### 7. 灵活的大模型接入（零 API Key / 任意 OpenAI 兼容接口）
- **Antigravity CLI (`agy`) 模式**：本机已登录 `agy` 时零 API Key 一键直连（支持 `gemini-4-neon-high` 等模型，带一键连通性测试）；
- **标准 HTTP API 模式**：支持任意 OpenAI 兼容端点（Gemini / OpenAI / DeepSeek / OpenRouter / 本地 Ollama）与自定义 HTTP 代理，配置持久化保存在本机 `~/.paperlens/config.json`（不会进入代码仓库）。

---

## 快速开始

### 环境依赖
- **Python 3.10+**
- **Poppler**（用于高精度双栏 PDF 文本坐标解析与页面渲染）
  - macOS: `brew install poppler`
  - Ubuntu/Debian: `sudo apt-get install poppler-utils`

### 安装与启动
```bash
git clone https://github.com/OliverHz-0/Paper_Lens.git
cd Paper_Lens

# 安装 Python 依赖
pip install -r requirements.txt

# 启动本地 Web 工作台（默认 http://127.0.0.1:8765）
python3 -m paperlens serve --host 127.0.0.1 --port 8765
```
启动后在浏览器打开 **http://127.0.0.1:8765**，即可上传 PDF 或从本机 Zotero 一键导入文献开始精读与汇报制作。

### CLI 命令行用法
```bash
# 解析一篇新 PDF（自动切段截图 + 裁图 + 抓取 GitHub/SI）
python3 -m paperlens ingest /path/to/paper.pdf

# 解析并同时调用配置好的大模型生成零基础深度解读
python3 -m paperlens ingest /path/to/paper.pdf --llm

# 实时溯源某篇论文的第 33 条参考文献
python3 -m paperlens trace-ref <paper_id> 33

# 重新在线抓取某篇论文的 GitHub 仓库与 DOI/SI 资源
python3 -m paperlens fetch-resources <paper_id> --force

# 导出带原文截图与大白话解读的 Markdown 深度报告
python3 -m paperlens export-md <paper_id> -o report.md
```

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
