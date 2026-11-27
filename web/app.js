import { createStudioController } from "/studio.js";
import { createCompareController } from "/compare.js";

const state = {
  papers: [],
  currentPaperId: null,
  bundle: null,
  activeTab: "overview",
  sectionFilter: "all",
  sliceDisplay: "both", // both | bilingual | img_zh | image
  sliceQuery: "",
  glossaryQuery: "",
  beginnerMode: true,
  mmScale: 1,
  mindmapDocked: false,
  activeMindmapTarget: null, // e.g. "slice:S06" or "figure:fig-2"
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

function esc(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function assetUrl(relPath) {
  return `/papers/${encodeURIComponent(state.currentPaperId)}/${relPath}`;
}

async function apiJson(url, opts = {}) {
  const res = await fetch(url, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

let studioCtrl = null;
let compareCtrl = null;

/* ---------- Boot ---------- */
async function init() {
  bindEvents();
  if (localStorage.getItem("paperlens-theme") === "dark") {
    document.body.classList.add("dark");
  }
  studioCtrl = createStudioController({
    state,
    $,
    $$,
    esc,
    apiJson,
    assetUrl,
    loadPaper,
    refreshPaperList,
    switchTab,
    onTopicsChanged: () => {
      if (state.activeTab === "compare") compareCtrl?.renderCompareTab();
    },
  });
  compareCtrl = createCompareController({
    state,
    $,
    $$,
    esc,
    apiJson,
    loadPaper,
    switchTab,
    getTopics: () => studioCtrl?.getTopics() || [],
  });
  await refreshPaperList();
  await studioCtrl.initStudio();
  if (state.papers.length > 0) {
    const preferred =
      state.papers.find((p) => p.paper_id === "limits-2025") || state.papers[0];
    await loadPaper(preferred.paper_id);
  } else {
    renderEmptyWorkspace();
  }
  window.addEventListener("resize", () => requestAnimationFrame(drawMindMapLines));
  const topbarEl = document.querySelector(".topbar");
  if (topbarEl) {
    const syncTopbarH = () => {
      document.documentElement.style.setProperty("--topbar-h", `${topbarEl.offsetHeight}px`);
    };
    syncTopbarH();
    new ResizeObserver(syncTopbarH).observe(topbarEl);
  }
}

async function refreshPaperList() {
  const { papers } = await apiJson("/api/papers");
  state.papers = papers;
  const sel = $("#paperSelect");
  sel.innerHTML = papers
    .map(
      (p) =>
        `<option value="${esc(p.paper_id)}">${esc(p.title_zh || p.title)} (${p.page_count}页)</option>`
    )
    .join("");
  if (state.currentPaperId) {
    sel.value = state.currentPaperId;
  }
}

async function loadPaper(paperId) {
  document.body.classList.remove("no-paper");
  $("#paperHero").classList.remove("is-empty");
  $("#btnExport").disabled = false;
  state.currentPaperId = paperId;
  $("#paperSelect").value = paperId;
  state.bundle = await apiJson(`/api/papers/${encodeURIComponent(paperId)}`);
  state.sectionFilter = "all";
  state.sliceQuery = "";
  state.mmScale = 1;
  $("#sliceSearch").value = "";

  const m = state.bundle.manifest;
  const a = state.bundle.analysis || {};
  const r = state.bundle.resources || {};

  $("#sliceCountBadge").textContent = (m.slices?.length || 0) + (m.figures?.length || 0);
  $("#glossaryCountBadge").textContent = Object.keys(a.glossary || {}).length;
  const resCount =
    (r.github?.length || 0) +
    (r.web_tools?.length || 0) +
    (r.supporting_info ? 1 : 0);
  $("#resCountBadge").textContent = resCount;

  renderHero();
  renderOverview();
  renderDockedMindMap();
  renderSliceFilters();
  renderSlices();
  renderGlossary();
  renderResources();
  studioCtrl?.onPaperLoaded();
}

/* ---------- Empty workspace (first run) ---------- */
function renderEmptyWorkspace() {
  document.body.classList.add("no-paper");
  $("#btnExport").disabled = true;
  $("#paperHero").classList.add("is-empty");
  $("#paperSelect").innerHTML = `<option value="">尚未导入论文</option>`;
  $("#paperHero").innerHTML = `
    <div class="empty-hero">
      <h1>导入第一篇论文</h1>
      <p>上传一篇 PDF，或从 Zotero 批量导入。PaperLens 会按双栏版面逐段切图、裁出图表、提取参考文献；配置好模型后还会生成六大维度解读、思维导图和逐段中文翻译。</p>
      <div class="empty-actions">
        <button type="button" class="btn btn-primary" data-empty-action="upload">
          <svg class="ic"><use href="#i-upload"/></svg>上传 PDF
        </button>
        <button type="button" class="btn btn-ghost" data-empty-action="zotero">
          <svg class="ic"><use href="#i-library"/></svg>从 Zotero 导入
        </button>
      </div>
      <p class="empty-note">没有配置模型也能使用切图、图表与引文溯源。模型可稍后在 <button type="button" class="link-btn" data-empty-action="settings">设置</button> 中添加。</p>
    </div>`;
  $$("[data-empty-action]").forEach((btn) =>
    btn.addEventListener("click", () => {
      const act = btn.dataset.emptyAction;
      if (act === "upload") $("#btnUpload").click();
      else if (act === "zotero") $("#btnZoteroTop").click();
      else $("#btnSettings").click();
    })
  );
}

/* ---------- Hero ---------- */
function renderHero() {
  const { manifest: m, analysis: a } = state.bundle;
  const isFallback = a.mode !== "llm_deep";
  const modeLabel = isFallback ? "待 AI 解读" : "AI 已解读";
  $("#paperHero").innerHTML = `
    <div class="hero-top-meta">
      <span class="status-tag ${isFallback ? "is-pending" : "is-done"}">${modeLabel}</span>
      <span class="meta-line">
        <span>${m.page_count} 页</span>
        <span>${m.slice_count} 段切片</span>
        <span>${m.figure_count} 张图表</span>
        <span>${m.reference_count} 篇参考文献</span>
      </span>
      <span class="meta-links">
        ${
          m.doi
            ? `<a class="meta-link" href="https://doi.org/${esc(m.doi)}" target="_blank" rel="noopener">DOI ${esc(m.doi)} ↗</a>`
            : ""
        }
        <a class="meta-link" href="${assetUrl("source.pdf")}" target="_blank" rel="noopener">原始 PDF ↗</a>
      </span>
    </div>
    <h1 class="hero-title-zh">${esc(a.paper_title_zh || m.title)}</h1>
    <p class="hero-title-en">${esc(m.title)}</p>
    ${m.authors ? `<p class="hero-authors">${esc(m.authors)}</p>` : ""}
    ${
      isFallback
        ? `<div class="hero-callout hero-pending">
            <div>
              <span class="callout-label">切图与引文提取已完成</span>
              <p>运行 AI 解读后，这里会生成六大维度、思维导图、逐段中文翻译、大白话类比与术语库。</p>
            </div>
            <button id="btnHeroAnalyzeNow" class="btn btn-primary">运行 AI 解读</button>
          </div>
          <div id="heroAnalyzeProgress" class="progress-box hidden" style="margin-bottom:12px">
            <div class="progress-head">
              <span id="heroAnalyzeMsg">正在启动 AI 解读…</span>
              <strong id="heroAnalyzePct">10%</strong>
            </div>
            <div class="progress-track">
              <div id="heroAnalyzeBar" class="progress-fill" style="width:10%"></div>
            </div>
          </div>`
        : ""
    }
    ${
      !isFallback && a.one_sentence_tldr
        ? `<div class="hero-callout hero-tldr"><span class="callout-label">一句话速览</span><p>${esc(a.one_sentence_tldr)}</p></div>`
        : ""
    }
    ${
      !isFallback && a.beginner_hook
        ? `<div class="hero-callout hero-beginner-hook beginner-only"><span class="callout-label">30 秒听懂（大白话）</span><p>${esc(a.beginner_hook)}</p></div>`
        : ""
    }
  `;

  $("#btnHeroAnalyzeNow")?.addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    btn.disabled = true;
    btn.textContent = "解读中…";
    const pbox = $("#heroAnalyzeProgress");
    pbox?.classList.remove("hidden");
    try {
      const { job_id } = await apiJson(
        `/api/papers/${encodeURIComponent(state.currentPaperId)}/analyze`,
        { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }
      );
      const timer = setInterval(async () => {
        try {
          const job = await apiJson(`/api/jobs/${job_id}`);
          $("#heroAnalyzeMsg").textContent = job.message || job.status;
          $("#heroAnalyzePct").textContent = `${job.progress || 0}%`;
          $("#heroAnalyzeBar").style.width = `${job.progress || 0}%`;
          if (job.status === "done") {
            clearInterval(timer);
            await refreshPaperList();
            await loadPaper(state.currentPaperId);
          } else if (job.status === "error") {
            clearInterval(timer);
            btn.disabled = false;
            btn.textContent = "重试 AI 解读";
            $("#heroAnalyzeMsg").textContent = `解读失败：${job.message || "未知错误"}。请检查设置中的模型配置后重试。`;
          }
        } catch {
          clearInterval(timer);
        }
      }, 1200);
    } catch (err) {
      $("#heroAnalyzeMsg").textContent = "启动失败：" + err.message;
      btn.disabled = false;
    }
  });
}

/* ---------- Interactive Paper Mind Map ---------- */
function getMindMapData() {
  const { manifest: m, analysis: a } = state.bundle;
  if (a.mindmap && a.mindmap.branches && a.mindmap.branches.length) {
    return a.mindmap;
  }
  // Auto-generate a mindmap from dimensions + figures for any new PDF
  const colors = ["amber", "blue", "teal", "indigo", "emerald", "purple"];
  const branches = (a.dimensions || []).map((dim, idx) => {
    const children = [];
    (dim.slice_ids || []).slice(0, 2).forEach((sid, i) => {
      children.push({
        label: dim.bullets?.[i] ? dim.bullets[i].slice(0, 28) : `核心段落 ${sid}`,
        detail: `点击跳转至原文切片 ${sid}`,
        target_type: "slice",
        target_id: sid,
      });
    });
    (dim.figure_ids || []).slice(0, 1).forEach((fid) => {
      const fig = (m.figures || []).find((f) => f.id === fid);
      children.push({
        label: fig ? `${fig.label} 核心图解` : fid,
        detail: "点击跳转至完整图表精读卡",
        target_type: "figure",
        target_id: fid,
      });
    });
    return {
      id: `b-${dim.key}`,
      title: `${idx + 1}. ${dim.title}`,
      color: colors[idx % colors.length],
      dim_key: dim.key,
      children: children.length
        ? children
        : [{ label: dim.subtitle || dim.title, detail: "点击跳转该维度解析", target_type: "dimension", target_id: dim.key }],
    };
  });
  return {
    root: {
      title: a.paper_title_zh || m.title,
      subtitle: `${m.page_count} 页 · ${m.slice_count} 切片 · ${m.figure_count} 核心图表`,
    },
    branches,
  };
}

function renderMindMapHtml() {
  const mm = getMindMapData();
  const branches = mm.branches || [];
  const half = Math.ceil(branches.length / 2);
  const leftBranches = branches.slice(0, half);
  const rightBranches = branches.slice(half);

  const renderLeaf = (leaf, color, branchId, leafIdx) => {
    const isFig = leaf.target_type === "figure";
    const isDim = leaf.target_type === "dimension";
    const tagText = isFig
      ? `${leaf.target_id.toUpperCase()}`
      : isDim
      ? `维度`
      : `${leaf.target_id}`;
    const dataAttr = isFig
      ? `data-jump-figure="${esc(leaf.target_id)}" data-from-mindmap="1"`
      : isDim
      ? `data-jump-dim="${esc(leaf.target_id)}"`
      : `data-jump-slice="${esc(leaf.target_id)}" data-from-mindmap="1"`;
    return `
      <button class="mm-leaf mm-${esc(color)}" data-mm-leaf="${esc(branchId)}-${leafIdx}" data-mm-parent="${esc(branchId)}" ${dataAttr} title="点击进入「左导图 + 右原文」分栏对照">
        <div class="mm-leaf-top">
          <span class="mm-leaf-label">${esc(leaf.label)}</span>
          <span class="mm-leaf-tag">${esc(tagText)}</span>
        </div>
        ${leaf.detail ? `<div class="mm-leaf-detail">${esc(leaf.detail)}</div>` : ""}
      </button>
    `;
  };

  const renderBranchRow = (b, side) => {
    const branchBtn = `
      <button class="mm-branch-node mm-${esc(b.color)}" data-mm-branch="${esc(b.id)}" data-mm-side="${side}" data-mm-color="${esc(b.color)}" data-jump-dim="${esc(b.dim_key || "")}" title="点击滚动到下方对应维度剖析">
        ${esc(b.title)}
      </button>
    `;
    const leavesHtml = `<div class="mm-leaves">${(b.children || [])
      .map((leaf, i) => renderLeaf(leaf, b.color, b.id, i))
      .join("")}</div>`;
    return side === "left"
      ? `<div class="mm-branch-row">${leavesHtml}${branchBtn}</div>`
      : `<div class="mm-branch-row">${branchBtn}${leavesHtml}</div>`;
  };

  return `
    <div id="mindmapCard" class="mindmap-card">
      <div class="mindmap-header">
        <div>
          <h2>论文全局思维导图</h2>
          <p class="mindmap-sub">点击任意节点跳到对应原文段落或图表。左侧是问题与方法，右侧是验证、结果与机理。</p>
        </div>
        <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
          <button id="mmZoomOut" class="btn btn-ghost btn-sm" title="缩小">－</button>
          <button id="mmZoomReset" class="btn btn-ghost btn-sm" title="重置缩放">100%</button>
          <button id="mmZoomIn" class="btn btn-ghost btn-sm" title="放大">＋</button>
          <button id="mmFullscreen" class="btn btn-secondary btn-sm">全屏大地图</button>
        </div>
      </div>
      <div id="mindmapViewport" class="mindmap-viewport">
        <div id="mindmapCanvas" class="mindmap-canvas">
          <svg id="mindmapSvg" class="mindmap-svg"></svg>
          <div class="mm-col mm-col-left">
            ${leftBranches.map((b) => renderBranchRow(b, "left")).join("")}
          </div>
          <div class="mm-center-wrap">
            <div id="mmRootNode" class="mm-root">
              <h3>${esc(mm.root?.title || "")}</h3>
              <p>${esc(mm.root?.subtitle || "")}</p>
            </div>
          </div>
          <div class="mm-col mm-col-right">
            ${rightBranches.map((b) => renderBranchRow(b, "right")).join("")}
          </div>
        </div>
      </div>
    </div>
  `;
}

function drawMindMapLines() {
  const canvas = $("#mindmapCanvas");
  const svg = $("#mindmapSvg");
  const rootEl = $("#mmRootNode");
  if (!canvas || !svg || !rootEl) return;

  const colorMap = {
    amber: "#dd5b00",
    blue: "#62aef0",
    teal: "#2a9d99",
    indigo: "#d6b6f6",
    emerald: "#1aae39",
    purple: "#ff64c8",
  };

  // Compute coordinates in unscaled canvas space
  const scale = state.mmScale || 1;
  const cRect = canvas.getBoundingClientRect();
  const rel = (el) => {
    const r = el.getBoundingClientRect();
    return {
      left: (r.left - cRect.left) / scale,
      right: (r.right - cRect.left) / scale,
      top: (r.top - cRect.top) / scale,
      bottom: (r.bottom - cRect.top) / scale,
      cy: (r.top + r.height / 2 - cRect.top) / scale,
    };
  };

  const cw = cRect.width / scale;
  const ch = cRect.height / scale;
  svg.setAttribute("viewBox", `0 0 ${cw} ${ch}`);
  svg.setAttribute("width", cw);
  svg.setAttribute("height", ch);

  const rootBox = rel(rootEl);
  const paths = [];

  $$("[data-mm-branch]").forEach((bEl) => {
    const bid = bEl.dataset.mmBranch;
    const side = bEl.dataset.mmSide;
    const col = colorMap[bEl.dataset.mmColor] || "#2563eb";
    const bBox = rel(bEl);

    // Root -> Branch curve
    const x1 = side === "left" ? rootBox.left : rootBox.right;
    const y1 = rootBox.cy;
    const x2 = side === "left" ? bBox.right : bBox.left;
    const y2 = bBox.cy;
    const mx = (x1 + x2) / 2;
    paths.push(
      `<path d="M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}" fill="none" stroke="${col}" stroke-width="2.4" stroke-opacity="0.72" />`
    );

    // Branch -> Leaf curves
    $$(`[data-mm-parent="${bid}"]`).forEach((lEl) => {
      const lBox = rel(lEl);
      const lx1 = side === "left" ? bBox.left : bBox.right;
      const ly1 = bBox.cy;
      const lx2 = side === "left" ? lBox.right : lBox.left;
      const ly2 = lBox.cy;
      const lmx = (lx1 + lx2) / 2;
      paths.push(
        `<path d="M ${lx1} ${ly1} C ${lmx} ${ly1}, ${lmx} ${ly2}, ${lx2} ${ly2}" fill="none" stroke="${col}" stroke-width="1.6" stroke-opacity="0.52" />`
      );
    });
  });

  svg.innerHTML = paths.join("");
}

/* ---------- Docked Left Vertical Mind Map (inside Slices View) ---------- */
function renderDockedMindMap() {
  const pane = $("#dockedMindmapPane");
  const layout = $("#slicesSplitLayout");
  const toggleBtn = $("#btnToggleDockedMindmap");
  if (!pane || !layout || !state.bundle) return;

  layout.classList.toggle("mindmap-docked", state.mindmapDocked);
  if (toggleBtn) {
    toggleBtn.classList.toggle("btn-primary", state.mindmapDocked);
    toggleBtn.classList.toggle("btn-secondary", !state.mindmapDocked);
    toggleBtn.textContent = state.mindmapDocked ? "导图分栏 (开)" : "导图分栏";
  }

  const mm = getMindMapData();
  const branches = mm.branches || [];

  pane.innerHTML = `
    <div class="dmm-head">
      <strong>论文思维导图导航</strong>
      <div style="display:flex;gap:6px;align-items:center">
        <button id="btnBackToFullMindmap" class="btn btn-ghost btn-xs" title="返回六大维度大地图">大地图</button>
        <button id="btnCloseDockedMindmap" class="icon-close" style="width:24px;height:24px;font-size:12px" title="收起左侧导图">✕</button>
      </div>
    </div>
    <div class="dmm-root-banner">
      <h4>${esc(mm.root?.title || "")}</h4>
      <p>${esc(mm.root?.subtitle || "")}</p>
    </div>
    <div class="dmm-tree">
      ${branches
        .map(
          (b) => `
        <div class="dmm-branch mm-${esc(b.color)}">
          <button class="dmm-branch-title" data-jump-dim="${esc(b.dim_key || "")}" title="点击返回该维度总览">
            <span>${esc(b.title)}</span>
            <span style="font-size:12px;opacity:0.75">↗</span>
          </button>
          <div class="dmm-children">
            ${(b.children || [])
              .map((leaf) => {
                const isFig = leaf.target_type === "figure";
                const isDim = leaf.target_type === "dimension";
                const key = `${leaf.target_type}:${leaf.target_id}`;
                const isActive = state.activeMindmapTarget === key;
                const tagText = isFig
                  ? `${leaf.target_id.toUpperCase()}`
                  : isDim
                  ? `维度`
                  : `${leaf.target_id}`;
                const dataAttr = isFig
                  ? `data-jump-figure="${esc(leaf.target_id)}" data-from-mindmap="1"`
                  : isDim
                  ? `data-jump-dim="${esc(leaf.target_id)}"`
                  : `data-jump-slice="${esc(leaf.target_id)}" data-from-mindmap="1"`;
                return `
                  <button class="dmm-leaf ${isActive ? "active" : ""}" ${dataAttr}>
                    <div class="dmm-leaf-top">
                      <span class="dmm-leaf-label">${esc(leaf.label)}</span>
                      <span class="mm-leaf-tag">${esc(tagText)}</span>
                    </div>
                    ${leaf.detail ? `<div class="dmm-leaf-detail">${esc(leaf.detail)}</div>` : ""}
                  </button>
                `;
              })
              .join("")}
          </div>
        </div>
      `
        )
        .join("")}
    </div>
  `;

  $("#btnCloseDockedMindmap")?.addEventListener("click", () => {
    state.mindmapDocked = false;
    renderDockedMindMap();
  });
  $("#btnBackToFullMindmap")?.addEventListener("click", () => {
    switchTab("overview");
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
}

function setMindmapDocked(docked, targetKey = null) {
  state.mindmapDocked = docked;
  if (targetKey) state.activeMindmapTarget = targetKey;
  // Auto-collapse left topic sidebar on medium screens so split view has plenty of room
  if (docked && window.innerWidth < 1560) {
    $("#workspaceShell")?.classList.add("sidebar-collapsed");
  }
  renderDockedMindMap();
}

/* ---------- Tab 1: 6-Dimension Overview ---------- */
function renderOverview() {
  const { manifest: m, analysis: a } = state.bundle;
  const figMap = Object.fromEntries((m.figures || []).map((f) => [f.id, f]));
  const figNotes = a.figure_notes || {};

  const mindmapHtml = renderMindMapHtml();

  const wfHtml = (a.workflow_steps || []).length
    ? `
    <div class="workflow-card">
      <h2 class="section-heading">
        <span>五步速通论文实验路线</span>
        <button class="btn btn-secondary btn-sm" id="btnJumpSlices">进入从头到尾逐段双语 + 图解精读 →</button>
      </h2>
      <div class="workflow-grid">
        ${a.workflow_steps
          .map(
            (st) => `
          <div class="wf-step">
            <span class="wf-num">${esc(st.step)}</span>
            <h4>${esc(st.title)}</h4>
            <p>${esc(st.desc)}</p>
          </div>
        `
          )
          .join("")}
      </div>
    </div>
  `
    : "";

  const dimsHtml = (a.dimensions || [])
    .map((dim) => {
      const figsHtml = (dim.figure_ids || [])
        .map((fid) => {
          const f = figMap[fid];
          if (!f) return "";
          const note = figNotes[fid] || {};
          return `
            <div class="fig-box">
              <img loading="lazy" src="${assetUrl(f.image)}" alt="${esc(f.label)}" class="zoomable" data-caption="${esc(f.label + " (P" + f.page + "): " + f.caption)}" />
              <div class="fig-meta">
                <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px">
                  <strong>${esc(note.title_zh || f.label + " (P" + f.page + ")")}</strong>
                  <button class="jump-pill" data-jump-figure="${esc(fid)}">完整图解 →</button>
                </div>
                <div>${esc(note.plain_summary || f.caption.slice(0, 140))}</div>
                ${
                  note.how_to_read
                    ? `<div class="fig-guide beginner-only"><strong>零基础看图指南：</strong>${esc(note.how_to_read)}</div>`
                    : ""
                }
              </div>
            </div>
          `;
        })
        .join("");

      const sliceLinks = (dim.slice_ids || [])
        .map(
          (sid) =>
            `<button class="jump-pill" data-jump-slice="${esc(sid)}">原文切片 ${esc(sid)}</button>`
        )
        .join("");

      return `
        <article class="dim-card" id="dim-${esc(dim.key)}">
          <div class="dim-header">
            <div class="dim-title-group">
              <span class="dim-num">${esc(dim.num)}</span>
              <h3>${esc(dim.title)}</h3>
            </div>
            <span class="dim-subtitle">${esc(dim.subtitle || "")}</span>
          </div>
          <p class="dim-summary">${esc(dim.summary || "")}</p>
          ${
            dim.beginner_analogy
              ? `<div class="analogy-box beginner-only"><span class="box-tag">大白话类比：</span>${esc(dim.beginner_analogy)}</div>`
              : ""
          }
          ${
            (dim.bullets || []).length
              ? `<ul class="dim-bullets">${dim.bullets.map((b) => `<li>${esc(b)}</li>`).join("")}</ul>`
              : ""
          }
          ${figsHtml ? `<div class="fig-strip">${figsHtml}</div>` : ""}
          ${sliceLinks ? `<div class="dim-evidence-bar"><span style="font-size:12px;color:var(--text-muted);font-weight:600">原文锚点：</span>${sliceLinks}</div>` : ""}
        </article>
      `;
    })
    .join("");

  const criticalHtml = (a.critical_notes || []).length
    ? `
      <div class="critical-card">
        <h3>批判性审读：局限性、未验证之处与细节核查</h3>
        <ul>${a.critical_notes.map((c) => `<li>${esc(c)}</li>`).join("")}</ul>
      </div>
    `
    : "";

  $("#tab-overview").innerHTML = `${mindmapHtml}${wfHtml}<div class="dim-stack">${dimsHtml}</div>${criticalHtml}`;

  // Bind mindmap controls
  const applyZoom = (newScale) => {
    state.mmScale = Math.max(0.65, Math.min(1.4, newScale));
    const canvas = $("#mindmapCanvas");
    if (canvas) {
      canvas.style.transform = `scale(${state.mmScale})`;
      $("#mmZoomReset").textContent = `${Math.round(state.mmScale * 100)}%`;
      requestAnimationFrame(drawMindMapLines);
    }
  };
  $("#mmZoomOut")?.addEventListener("click", () => applyZoom(state.mmScale - 0.12));
  $("#mmZoomIn")?.addEventListener("click", () => applyZoom(state.mmScale + 0.12));
  $("#mmZoomReset")?.addEventListener("click", () => applyZoom(1));
  $("#mmFullscreen")?.addEventListener("click", (e) => {
    const card = $("#mindmapCard");
    const isFs = card.classList.toggle("is-fullscreen");
    e.currentTarget.textContent = isFs ? "退出全屏" : "全屏大地图";
    requestAnimationFrame(drawMindMapLines);
  });

  $("#btnJumpSlices")?.addEventListener("click", () => switchTab("slices"));

  // Draw SVG mindmap connectors after layout settles (and auto-fit on narrow screens)
  requestAnimationFrame(() => {
    const vp = $("#mindmapViewport");
    if (vp && vp.clientWidth > 0 && vp.clientWidth < 1080) {
      applyZoom(Math.max(0.68, (vp.clientWidth - 44) / 1040));
    }
    drawMindMapLines();
    setTimeout(drawMindMapLines, 150);
  });
}

/* ---------- Tab 2: Slice-by-Slice + Interleaved Figure Reading Cards ---------- */
function renderSliceFilters() {
  const slices = state.bundle.manifest.slices || [];
  const figs = state.bundle.manifest.figures || [];
  const counts = { all: slices.length + figs.length, figures: figs.length };
  for (const s of slices) {
    counts[s.section] = (counts[s.section] || 0) + 1;
  }
  const defs = [
    ["all", "全部（段落+图表）"],
    ["figures", "仅看图表精读"],
    ["abstract", "摘要 Abstract"],
    ["introduction", "引言背景 Intro"],
    ["methods", "研究方法 Methods"],
    ["results", "结果讨论 Results"],
    ["conclusions", "结论局限 Conclusions"],
  ];
  $("#sectionFilters").innerHTML = defs
    .filter(([k]) => counts[k])
    .map(
      ([k, label]) => `
      <button class="chip ${state.sectionFilter === k ? "active" : ""}" data-sec="${k}">
        ${label} (${counts[k]})
      </button>
    `
    )
    .join("");
}

function renderFigureReadingCard(fig, note) {
  const subpanels = note.subpanels || [];
  const relSlices = note.related_slices || [];

  return `
    <article class="fig-reading-card" id="figcard-${esc(fig.id)}">
      <div class="fig-reading-head">
        <div class="fig-reading-head-left">
          <span class="fig-badge">${esc(fig.label)} · P${fig.page}</span>
          <strong style="font-size:16px">${esc(note.title_zh || fig.label)}</strong>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          ${relSlices.map((sid) => `<button class="jump-pill" data-jump-slice="${esc(sid)}">${esc(sid)}</button>`).join("")}
        </div>
      </div>
      <div class="fig-reading-body">
        <div class="fig-reading-img-stage">
          <img loading="lazy" src="${assetUrl(fig.image)}" alt="${esc(fig.label)}" class="zoomable" data-caption="${esc(fig.label + " (P" + fig.page + "): " + fig.caption)}" />
        </div>

        <div class="fig-reading-grid">
          <div class="fig-info-box summary-box">
            <span class="block-label" style="color:var(--primary)">一句话看懂这张图</span>
            <div>${esc(note.plain_summary || fig.caption.slice(0, 200))}</div>
          </div>
          ${
            note.how_to_read
              ? `<div class="fig-info-box guide-box beginner-only">
                  <span class="block-label" style="color:var(--amber)">零基础看图指南</span>
                  <div>${esc(note.how_to_read)}</div>
                </div>`
              : ""
          }
        </div>

        ${
          subpanels.length
            ? `<div>
                <div style="font-size:14px;font-weight:800;color:var(--text-muted);margin-bottom:8px">逐子图 / 逐区块精细拆解</div>
                <div class="subpanel-grid">
                  ${subpanels
                    .map(
                      (sp) => `
                    <div class="subpanel-item">
                      <strong>${esc(sp.label)}</strong>
                      <div>${esc(sp.detail)}</div>
                    </div>
                  `
                    )
                    .join("")}
                </div>
              </div>`
            : ""
        }

        ${
          note.context_connection
            ? `<div class="fig-info-box conn-box">
                <span class="block-label" style="color:var(--teal)">与上下文及前后图表的逻辑联系</span>
                <div>${esc(note.context_connection)}</div>
              </div>`
            : ""
        }

        <details class="fig-caption-details">
          <summary>展开完整图注（英中对照）</summary>
          ${note.caption_zh ? `<div class="cap-zh"><strong>中文图注：</strong>${esc(note.caption_zh)}</div>` : ""}
          <div class="cap-en"><strong>Original Caption:</strong> ${esc(fig.caption)}</div>
        </details>
      </div>
    </article>
  `;
}

function renderSlices() {
  const { manifest: m, analysis: a } = state.bundle;
  const sliceNotes = a.slice_notes || {};
  const glossary = a.glossary || {};
  const figures = m.figures || [];
  const figMap = Object.fromEntries(figures.map((f) => [f.id, f]));
  const figNotes = a.figure_notes || {};
  const q = state.sliceQuery.trim().toLowerCase();

  // Mode: Only Figures
  if (state.sectionFilter === "figures") {
    const matchedFigs = figures.filter((f) => {
      if (!q) return true;
      const n = figNotes[f.id] || {};
      const hay = `${f.id} ${f.label} ${f.caption} ${n.title_zh || ""} ${n.plain_summary || ""} ${n.context_connection || ""}`.toLowerCase();
      return hay.includes(q);
    });
    $("#slicesList").innerHTML = matchedFigs.length
      ? matchedFigs.map((f) => renderFigureReadingCard(f, figNotes[f.id] || {})).join("")
      : `<div class="dim-card"><p>没有匹配当前搜索关键词的图表。</p></div>`;
    return;
  }

  // Build map of insert_after_slice -> [figure, ...]
  const insertAfterMap = {};
  const placedFigIds = new Set();
  for (const f of figures) {
    const note = figNotes[f.id] || {};
    let anchor = note.insert_after_slice;
    if (!anchor) {
      // Fallback: last slice referencing this figure, or first slice on/after its page
      const refSlices = (m.slices || []).filter((s) => (s.linked_figures || []).includes(f.id));
      anchor = refSlices.length
        ? refSlices[refSlices.length - 1].id
        : ((m.slices || []).find((s) => s.page >= f.page) || {}).id;
    }
    if (anchor) {
      insertAfterMap[anchor] = insertAfterMap[anchor] || [];
      insertAfterMap[anchor].push(f);
      placedFigIds.add(f.id);
    }
  }

  const filtered = (m.slices || []).filter((s) => {
    if (state.sectionFilter !== "all" && s.section !== state.sectionFilter) return false;
    if (!q) return true;
    const note = sliceNotes[s.id] || {};
    const hay = `${s.id} ${s.text} ${note.translation_zh || ""} ${note.heading || ""} ${note.role || ""} ${note.plain_explanation || ""} ${(note.terms || []).join(" ")}`.toLowerCase();
    return hay.includes(q);
  });

  if (!filtered.length) {
    $("#slicesList").innerHTML = `<div class="dim-card"><p>没有匹配当前筛选条件的原文切片。</p></div>`;
    return;
  }

  const showImg = state.sliceDisplay === "both" || state.sliceDisplay === "img_zh" || state.sliceDisplay === "image";
  const showEn = state.sliceDisplay === "both" || state.sliceDisplay === "bilingual";
  const showZh = state.sliceDisplay === "both" || state.sliceDisplay === "bilingual" || state.sliceDisplay === "img_zh";

  const chunks = [];
  for (const s of filtered) {
    const note = sliceNotes[s.id] || {};

    const linkedFigsHtml = (s.linked_figures || [])
      .map((fid) => {
        const f = figMap[fid];
        if (!f) return "";
        const fn = figNotes[fid] || {};
        return `
          <div class="linked-fig-mini">
            <img loading="lazy" src="${assetUrl(f.image)}" alt="${esc(f.label)}" class="zoomable" data-caption="${esc(f.label + " (P" + f.page + "): " + f.caption)}" />
            <div class="linked-fig-summary">
              <strong>关联图表 · ${esc(fn.title_zh || f.label)}：</strong>${esc(fn.plain_summary || f.caption.slice(0, 120))}
            </div>
            <div class="linked-fig-footer">
              <span style="font-size:12px;color:var(--text-muted)">本段直接引用了该图作为证据</span>
              <button class="jump-pill" data-jump-figure="${esc(fid)}">展开逐子图精读与因果联系 →</button>
            </div>
          </div>
        `;
      })
      .join("");

    const refsHtml = (s.refs || [])
      .map(
        (r) =>
          `<button class="ref-pill" data-trace-ref="${r}" title="点击实时溯源第 ${r} 条参考文献">Ref ${r}</button>`
      )
      .join("");

    const termsHtml = (note.terms || [])
      .filter((t) => glossary[t])
      .map(
        (t) =>
          `<button class="term-pill" data-open-term="${esc(t)}" title="点击查看零基础术语科普">${esc(t)}</button>`
      )
      .join("");

    chunks.push(`
      <article class="slice-card" id="slice-${esc(s.id)}">
        <div class="slice-head">
          <div class="slice-head-left">
            <span class="slice-id">${esc(s.id)}</span>
            <span class="slice-sec-tag">P${s.page} · ${esc(s.section_label)}</span>
            <span class="slice-title">${esc(note.heading || s.section_label)}</span>
          </div>
          <div class="slice-pills-row">
            ${refsHtml}
          </div>
        </div>
        <div class="slice-body">
          <div class="slice-original">
            ${
              showImg
                ? `<div class="slice-img-wrap">
                    <img loading="lazy" src="${assetUrl(s.image)}" alt="${esc(s.id)} 原文截图" class="zoomable" data-caption="${esc(s.id + " 原文截图 (Page " + s.page + ")")}" />
                  </div>`
                : ""
            }
            <div class="bilingual-box">
              ${
                showEn
                  ? `<div class="slice-raw-text">
                      <span class="lang-tag en">EN 英文原文</span>
                      <div>${esc(s.text)}</div>
                    </div>`
                  : ""
              }
              ${
                showZh && note.translation_zh
                  ? `<div class="slice-translation-zh">
                      <span class="lang-tag zh">ZH 中文逐句翻译</span>
                      <div>${esc(note.translation_zh)}</div>
                    </div>`
                  : ""
              }
            </div>
            ${linkedFigsHtml}
          </div>
          <div class="slice-analysis">
            <div class="analysis-block role-block">
              <span class="block-label">这段文字的作用解析</span>
              <div>${esc(note.role || "正文切片段落。")}</div>
            </div>
            <div class="analysis-block plain-block beginner-only">
              <span class="block-label">零基础大白话翻译</span>
              <div>${esc(note.plain_explanation || "")}</div>
            </div>
            ${
              (note.key_takeaways || []).length
                ? `<ul class="takeaways-list">${note.key_takeaways.map((k) => `<li>${esc(k)}</li>`).join("")}</ul>`
                : ""
            }
            ${
              termsHtml || refsHtml
                ? `<div class="slice-pills-row">
                    ${termsHtml}
                    ${refsHtml}
                  </div>`
                : ""
            }
          </div>
        </div>
      </article>
    `);

    // Interleave full Figure Reading Card right after its anchor slice when browsing All or Results
    if ((state.sectionFilter === "all" || state.sectionFilter === "results") && !q && insertAfterMap[s.id]) {
      for (const fig of insertAfterMap[s.id]) {
        chunks.push(renderFigureReadingCard(fig, figNotes[fig.id] || {}));
      }
    }
  }

  $("#slicesList").innerHTML = chunks.join("");
}

/* ---------- Tab 3: Beginner Glossary ---------- */
function renderGlossary() {
  const glossary = state.bundle.analysis?.glossary || {};
  const entries = Object.entries(glossary);
  const q = state.glossaryQuery.trim().toLowerCase();
  const filtered = entries.filter(([k, v]) => {
    if (!q) return true;
    return `${k} ${v.zh} ${v.simple} ${v.analogy} ${v.in_paper}`.toLowerCase().includes(q);
  });

  $("#tab-glossary").innerHTML = `
    <div class="glossary-header">
      <div>
        <h2 style="margin:0 0 4px">零基础跨学科术语速查库</h2>
        <p style="margin:0;font-size:14px;color:var(--text-muted)">专为非生物/非本专业读者准备：每个晦涩词汇配「大白话 + 生活类比 + 在本文中的作用」。</p>
      </div>
      <input id="glossarySearch" type="search" class="search-input" value="${esc(state.glossaryQuery)}" placeholder="搜索术语（如 MIC、SI、破膜、PCA...）" />
    </div>
    <div class="glossary-grid">
      ${
        filtered.length
          ? filtered
              .map(
                ([k, v]) => `
            <div class="term-card">
              <div class="term-card-head">
                <strong>${esc(k)}</strong>
                <span>${esc(v.zh || "")}</span>
              </div>
              <p class="term-simple">${esc(v.simple || "")}</p>
              ${v.analogy ? `<div class="term-analogy"><strong>生活类比：</strong>${esc(v.analogy)}</div>` : ""}
              ${v.in_paper ? `<p class="term-in-paper"><strong>在本文中：</strong>${esc(v.in_paper)}</p>` : ""}
            </div>
          `
              )
              .join("")
          : `<div class="dim-card">暂无术语词条（配置 API Key 并运行 AI 深度解读后将自动提取）。</div>`
      }
    </div>
  `;

  $("#glossarySearch").addEventListener("input", (e) => {
    state.glossaryQuery = e.target.value;
    renderGlossary();
    $("#glossarySearch").focus();
  });
}

/* ---------- Tab 4: Auto-Fetched Resources + Full References ---------- */
function renderResources() {
  const { manifest: m, resources: r, ref_cache: cache } = state.bundle;

  const ghCards = (r.github || [])
    .map(
      (g) => `
      <div class="res-card">
        <h3>
          <span>GitHub 开源代码与数据集</span>
          <a href="${esc(g.url)}" target="_blank" class="btn btn-primary btn-sm">打开仓库 ↗</a>
        </h3>
        <p style="margin:0 0 8px;font-weight:700">${esc(g.repo)} ${g.language ? `<span class="meta-pill">${esc(g.language)}</span>` : ""}</p>
        <p style="margin:0 0 10px;font-size:14px;color:var(--text-muted)">${esc(g.description || "已从论文正文自动识别开源仓库。")}</p>
        ${
          (g.files || []).length
            ? `<div style="font-size:12px;font-weight:700;color:var(--text-muted)">仓库核心文件结构：</div>
               <div class="file-list">${g.files.map((f) => `<a class="file-chip" href="${esc(f.html_url || g.url)}" target="_blank">${esc(f.name)}</a>`).join("")}</div>`
            : ""
        }
        ${g.readme_excerpt ? `<pre class="readme-pre">${esc(g.readme_excerpt)}</pre>` : ""}
      </div>
    `
    )
    .join("");

  const siCard = r.supporting_info
    ? `
      <div class="res-card">
        <h3>
          <span>补充材料 (Supporting Information)</span>
          ${
            r.supporting_info.url
              ? `<a href="${esc(r.supporting_info.url)}" target="_blank" class="btn btn-secondary btn-sm">直达 SI 页面 ↗</a>`
              : ""
          }
        </h3>
        <p style="white-space:pre-line;font-size:14px;margin:0 0 12px">${esc(r.supporting_info.note || "")}</p>
        ${
          r.doi_meta
            ? `<div class="trace-meta-row">
                ${r.doi_meta.journal ? `<span class="meta-pill accent">${esc(r.doi_meta.journal)}</span>` : ""}
                ${r.doi_meta.published_date ? `<span class="meta-pill">发表：${esc(r.doi_meta.published_date)}</span>` : ""}
                ${r.doi_meta.publisher ? `<span class="meta-pill">${esc(r.doi_meta.publisher)}</span>` : ""}
              </div>`
            : ""
        }
      </div>
    `
    : "";

  const toolsCard = (r.web_tools || []).length
    ? `
      <div class="res-card">
        <h3><span>文中自动发现的数据库与在线工具</span></h3>
        <div style="display:flex;flex-direction:column;gap:10px">
          ${r.web_tools
            .map(
              (t) => `
            <div style="padding:10px 12px;background:var(--surface-alt);border-radius:8px;border:1px solid var(--border)">
              <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
                <strong style="font-size:14px">${esc(t.name)}</strong>
                <a href="${esc(t.url)}" target="_blank" class="btn btn-ghost btn-sm">访问 ↗</a>
              </div>
              ${t.desc ? `<p style="margin:4px 0 0;font-size:14px;color:var(--text-muted)">${esc(t.desc)}</p>` : ""}
            </div>
          `
            )
            .join("")}
        </div>
      </div>
    `
    : "";

  const refsListHtml = (m.references || [])
    .map((ref) => {
      const cached = cache[String(ref.number)];
      return `
        <div class="ref-row">
          <div class="ref-row-main">
            <span class="ref-num-tag">[Ref ${ref.number}]</span>
            ${esc(ref.raw)}
            ${
              cached?.why_cited
                ? `<div style="margin-top:5px;font-size:14px;color:var(--teal)"><strong>已深度溯源：</strong>${esc(cached.why_cited)}</div>`
                : ""
            }
          </div>
          <button class="ref-pill" data-trace-ref="${ref.number}" style="flex-shrink:0">实时溯源 ↗</button>
        </div>
      `;
    })
    .join("");

  $("#tab-resources").innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:10px">
      <div>
        <h2 style="margin:0 0 4px">自动抓取的关联代码仓、SI 与工具</h2>
        <p style="margin:0;font-size:14px;color:var(--text-muted)">解析 PDF 时自动提取文中所有 GitHub、DOI、Supporting Information 与生物信息工具链接。</p>
      </div>
      <button id="btnRefetchResources" class="btn btn-secondary">重新在线抓取资源</button>
    </div>
    <div class="res-grid">
      ${ghCards || `<div class="res-card"><h3>GitHub 仓库</h3><p style="color:var(--text-muted)">本文未检测到 GitHub URL。</p></div>`}
      ${siCard}
      ${toolsCard}
    </div>
    <div style="margin-top:26px">
      <h2 style="margin:0 0 12px">全文参考文献列表（共 ${m.references?.length || 0} 篇 · 点击任意一篇实时展开溯源）</h2>
      <div class="ref-index-list">${refsListHtml}</div>
    </div>
  `;

  $("#btnRefetchResources").addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    btn.disabled = true;
    btn.textContent = "正在联网抓取…";
    try {
      const fresh = await apiJson(
        `/api/papers/${encodeURIComponent(state.currentPaperId)}/fetch-resources`,
        { method: "POST" }
      );
      state.bundle.resources = fresh;
      renderResources();
    } catch (err) {
      alert("在线抓取失败：" + err.message);
    } finally {
      btn.disabled = false;
    }
  });
}

/* ---------- Real-Time Citation Tracer Drawer ---------- */
async function openRefTracer(refNum, force = false) {
  openDrawer(`实时引文溯源 · [Ref ${refNum}]`, `<p style="color:var(--text-muted)">正在从 Crossref / Europe PMC / Semantic Scholar 查询 [Ref ${refNum}]…</p>`);
  try {
    const url = `/api/papers/${encodeURIComponent(state.currentPaperId)}/trace-ref/${refNum}${force ? "?force=1" : ""}`;
    const data = await apiJson(url);
    state.bundle.ref_cache[String(refNum)] = data;

    const citingHtml = (data.citing_slices || []).length
      ? data.citing_slices
          .map(
            (cs) => `
          <div style="padding:9px 11px;background:var(--surface-alt);border-radius:8px;border:1px solid var(--border);margin-bottom:8px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
              <strong style="font-size:14px">${esc(cs.id)} · P${cs.page} (${esc(cs.section_label)})</strong>
              <button class="jump-pill" data-jump-slice="${esc(cs.id)}">跳转段落 →</button>
            </div>
            <div style="font-size:14px;color:var(--text-muted)">${esc(cs.excerpt)}</div>
          </div>
        `
          )
          .join("")
      : `<p style="font-size:14px;color:var(--text-muted)">文中以区间或上标方式间接引用了该文献。</p>`;

    $("#drawerBody").innerHTML = `
      <div class="trace-section">
        <div class="trace-title">${esc(data.title || "未提取到标题")}</div>
        <div style="font-size:14px;color:var(--text-muted);margin-bottom:10px">${esc(data.authors || "")}</div>
        <div class="trace-meta-row">
          ${data.venue ? `<span class="meta-pill accent">${esc(data.venue)}</span>` : ""}
          ${data.year ? `<span class="meta-pill">${data.year}</span>` : ""}
          ${data.citation_count != null ? `<span class="meta-pill">被引 ${data.citation_count} 次</span>` : ""}
          ${data.source ? `<span class="meta-pill">来源：${esc(data.source)}</span>` : ""}
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          ${data.url ? `<a href="${esc(data.url)}" target="_blank" class="btn btn-primary btn-sm">打开原文 DOI ↗</a>` : ""}
          ${data.open_access_pdf ? `<a href="${esc(data.open_access_pdf)}" target="_blank" class="btn btn-secondary btn-sm">免费 OA PDF ↗</a>` : ""}
          ${data.scholar_search_url ? `<a href="${esc(data.scholar_search_url)}" target="_blank" class="btn btn-ghost btn-sm">Google Scholar ↗</a>` : ""}
          <button class="btn btn-ghost btn-sm" id="btnForceTrace">强制在线刷新</button>
        </div>
      </div>

      ${
        data.why_cited
          ? `<div class="trace-section">
              <h4>本文为何在这里引用这篇文献？</h4>
              <div class="analysis-block role-block">${esc(data.why_cited)}</div>
            </div>`
          : ""
      }

      ${
        data.plain_summary
          ? `<div class="trace-section">
              <h4>零基础大白话速览</h4>
              <div class="analysis-block plain-block">${esc(data.plain_summary)}</div>
            </div>`
          : ""
      }

      ${
        data.abstract
          ? `<div class="trace-section">
              <h4>实时抓取的引文摘要 (Abstract)</h4>
              <div class="trace-abstract">${esc(data.abstract)}</div>
            </div>`
          : ""
      }

      <div class="trace-section">
        <h4>在本文中的引用上下文</h4>
        ${citingHtml}
      </div>

      <div class="trace-section">
        <h4>原始参考文献条目</h4>
        <div class="trace-abstract" style="font-size:14px">${esc(data.raw || "")}</div>
      </div>
    `;

    $("#btnForceTrace").addEventListener("click", () => openRefTracer(refNum, true));
  } catch (err) {
    $("#drawerBody").innerHTML = `<p style="color:var(--rose)">溯源失败：${esc(err.message)}</p>`;
  }
}

function openTermDrawer(termKey) {
  const v = state.bundle.analysis?.glossary?.[termKey];
  if (!v) return;
  openDrawer(
    `术语大白话 · ${termKey}`,
    `
      <div class="trace-section">
        <div class="trace-title">${esc(termKey)}</div>
        <div style="font-size:14px;color:var(--teal);font-weight:600;margin-bottom:14px">${esc(v.zh || "")}</div>
        <div class="analysis-block plain-block" style="margin-bottom:12px">
          <span class="block-label">零基础一句话解释</span>
          <div>${esc(v.simple || "")}</div>
        </div>
        ${
          v.analogy
            ? `<div class="analysis-block role-block" style="margin-bottom:12px">
                <span class="block-label">生活化类比</span>
                <div>${esc(v.analogy)}</div>
              </div>`
            : ""
        }
        ${
          v.in_paper
            ? `<div class="trace-abstract"><strong>在这篇论文中的作用：</strong>${esc(v.in_paper)}</div>`
            : ""
        }
      </div>
    `
  );
}

function openDrawer(title, html) {
  $("#drawerTitle").textContent = title;
  $("#drawerBody").innerHTML = html;
  $("#drawerOverlay").classList.remove("hidden");
  $("#sideDrawer").classList.remove("hidden");
}

function closeDrawer() {
  $("#drawerOverlay").classList.add("hidden");
  $("#sideDrawer").classList.add("hidden");
}

/* ---------- Navigation & Jump Helpers ---------- */
function exitMindMapFullscreen() {
  const card = $("#mindmapCard");
  if (card && card.classList.contains("is-fullscreen")) {
    card.classList.remove("is-fullscreen");
    const btn = $("#mmFullscreen");
    if (btn) btn.textContent = "全屏大地图";
  }
}

function switchTab(tabName) {
  exitMindMapFullscreen();
  state.activeTab = tabName;
  $$(".nav-tab").forEach((b) => {
    const on = b.dataset.tab === tabName;
    b.classList.toggle("active", on);
    b.setAttribute("aria-selected", on ? "true" : "false");
  });
  $$(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === `tab-${tabName}`));
  $("#paperHero")?.classList.toggle("hidden", tabName === "compare");
  if (tabName === "overview") {
    requestAnimationFrame(drawMindMapLines);
  } else if (tabName === "compare") {
    compareCtrl?.openCompareTab();
  } else if (tabName === "ppt") {
    studioCtrl?.renderPptTab();
  }
}

function scrollAndFlash(el) {
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: "start" });
  el.classList.add("highlight-flash");
  setTimeout(() => el.classList.remove("highlight-flash"), 2200);
}

function jumpToSlice(sliceId, fromMindmap = false) {
  closeDrawer();
  exitMindMapFullscreen();
  state.sectionFilter = "all";
  state.sliceQuery = "";
  $("#sliceSearch").value = "";
  renderSliceFilters();
  renderSlices();
  switchTab("slices");
  if (fromMindmap) {
    setMindmapDocked(true, `slice:${sliceId}`);
  } else if (state.mindmapDocked) {
    state.activeMindmapTarget = `slice:${sliceId}`;
    renderDockedMindMap();
  }
  requestAnimationFrame(() => {
    scrollAndFlash(document.getElementById(`slice-${sliceId}`));
    setTimeout(() => scrollAndFlash(document.getElementById(`slice-${sliceId}`)), 220);
  });
}

function jumpToFigure(figId, fromMindmap = false) {
  closeDrawer();
  exitMindMapFullscreen();
  state.sectionFilter = "all";
  state.sliceQuery = "";
  $("#sliceSearch").value = "";
  renderSliceFilters();
  renderSlices();
  switchTab("slices");
  if (fromMindmap) {
    setMindmapDocked(true, `figure:${figId}`);
  } else if (state.mindmapDocked) {
    state.activeMindmapTarget = `figure:${figId}`;
    renderDockedMindMap();
  }
  const go = () => {
    let el = document.getElementById(`figcard-${figId}`);
    if (!el) {
      state.sectionFilter = "figures";
      renderSliceFilters();
      renderSlices();
      el = document.getElementById(`figcard-${figId}`);
    }
    scrollAndFlash(el);
  };
  requestAnimationFrame(() => {
    go();
    setTimeout(go, 240);
  });
}

function jumpToDimension(dimKey) {
  if (!dimKey) return;
  exitMindMapFullscreen();
  switchTab("overview");
  requestAnimationFrame(() => scrollAndFlash(document.getElementById(`dim-${dimKey}`)));
}

/* ---------- Upload & Jobs ---------- */
async function uploadPdfFile(file) {
  if (!file) return;
  const box = $("#uploadProgressBox");
  box.classList.remove("hidden");
  $("#uploadStatusText").textContent = "正在上传 PDF...";
  $("#uploadPctText").textContent = "5%";
  $("#uploadProgressBar").style.width = "5%";

  const fd = new FormData();
  fd.append("file", file);
  fd.append("run_llm", $("#uploadRunLlm").checked ? "true" : "false");
  const topicSel = $("#uploadTopicSelect")?.value || "";
  if (topicSel) fd.append("topic_id", topicSel);

  try {
    const { job_id } = await apiJson("/api/upload", { method: "POST", body: fd });
    pollJob(job_id, async (job) => {
      await refreshPaperList();
      await studioCtrl?.onPapersChanged();
      await loadPaper(job.paper_id);
      $("#uploadModal").classList.add("hidden");
      box.classList.add("hidden");
      switchTab("overview");
    });
  } catch (err) {
    $("#uploadStatusText").textContent = "上传失败：" + err.message;
  }
}

async function pollJob(jobId, onDone) {
  const timer = setInterval(async () => {
    try {
      const job = await apiJson(`/api/jobs/${jobId}`);
      $("#uploadStatusText").textContent = job.message || job.status;
      $("#uploadPctText").textContent = `${job.progress || 0}%`;
      $("#uploadProgressBar").style.width = `${job.progress || 0}%`;
      if (job.status === "done") {
        clearInterval(timer);
        if (onDone) await onDone(job);
      } else if (job.status === "error") {
        clearInterval(timer);
      }
    } catch (e) {
      clearInterval(timer);
    }
  }, 700);
}

/* ---------- Settings ---------- */
function syncProviderFieldVisibility() {
  const isAgy = ($("#cfgProvider")?.value || "agy_cli") === "agy_cli";
  $("#cfgBaseUrlRow")?.classList.toggle("hidden", isAgy);
  $("#cfgApiKeyRow")?.classList.toggle("hidden", isAgy);
}

async function openSettings() {
  const cfg = await apiJson("/api/config");
  if ($("#cfgProvider")) $("#cfgProvider").value = cfg.llm_provider || "agy_cli";
  $("#cfgBaseUrl").value = cfg.llm_base_url || "";
  $("#cfgModel").value = cfg.llm_model || "gemini-4-neon-high";
  $("#cfgApiKey").value = cfg.llm_api_key || "";
  if ($("#cfgZoteroDir")) $("#cfgZoteroDir").value = cfg.zotero_data_dir || "";
  if ($("#cfgZoteroMcp")) $("#cfgZoteroMcp").value = cfg.zotero_mcp_command || "";
  if ($("#cfgPptMasterDir")) $("#cfgPptMasterDir").value = cfg.ppt_master_dir || "";
  $("#cfgProxy").value = cfg.http_proxy || "";
  syncProviderFieldVisibility();
  $("#settingsToast").classList.add("hidden");
  $("#settingsModal").classList.remove("hidden");
}

/* ---------- Event Binding ---------- */
function bindEvents() {
  const moreBtn = $("#btnMoreActions");
  const moreMenu = $("#secondaryActions");
  const setMore = (open) => {
    moreMenu.classList.toggle("open", open);
    moreBtn.setAttribute("aria-expanded", open ? "true" : "false");
  };
  moreBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    setMore(!moreMenu.classList.contains("open"));
  });
  moreMenu.addEventListener("click", () => setMore(false));
  document.addEventListener("click", (e) => {
    if (!moreMenu.contains(e.target)) setMore(false);
  });

  const narrow = window.matchMedia("(max-width: 1020px)");
  if (narrow.matches) $("#workspaceShell").classList.add("sidebar-collapsed");
  $("#sidebarScrim").addEventListener("click", () =>
    $("#workspaceShell").classList.add("sidebar-collapsed")
  );

  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    const openModal = $$(".modal-backdrop").find((m) => !m.classList.contains("hidden"));
    if (openModal) openModal.classList.add("hidden");
    else if (!$("#sideDrawer").classList.contains("hidden")) closeDrawer();
    else if (narrow.matches) $("#workspaceShell").classList.add("sidebar-collapsed");
    setMore(false);
  });

  $$(".nav-tab").forEach((btn) =>
    btn.addEventListener("click", () => switchTab(btn.dataset.tab))
  );

  $("#paperSelect").addEventListener("change", (e) => loadPaper(e.target.value));

  $("#beginnerToggle").addEventListener("change", (e) => {
    state.beginnerMode = e.target.checked;
    document.body.classList.toggle("hide-beginner", !state.beginnerMode);
  });

  $("#btnTheme").addEventListener("click", () => {
    document.body.classList.toggle("dark");
    localStorage.setItem(
      "paperlens-theme",
      document.body.classList.contains("dark") ? "dark" : "light"
    );
  });

  $("#btnExport").addEventListener("click", () => {
    if (!state.currentPaperId) return;
    window.open(`/api/papers/${encodeURIComponent(state.currentPaperId)}/export-md`, "_blank");
  });

  $("#btnUpload").addEventListener("click", () => $("#uploadModal").classList.remove("hidden"));
  $("#btnSettings").addEventListener("click", openSettings);

  $$("[data-close-modal]").forEach((btn) =>
    btn.addEventListener("click", () =>
      document.getElementById(btn.dataset.closeModal).classList.add("hidden")
    )
  );

  $("#drawerClose").addEventListener("click", closeDrawer);
  $("#drawerOverlay").addEventListener("click", closeDrawer);

  // Lightbox
  $("#lightboxClose").addEventListener("click", () => $("#lightbox").classList.add("hidden"));
  $("#lightbox").addEventListener("click", (e) => {
    if (e.target.id === "lightbox") $("#lightbox").classList.add("hidden");
  });

  // Slices controls
  $("#sectionFilters").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-sec]");
    if (!btn) return;
    state.sectionFilter = btn.dataset.sec;
    renderSliceFilters();
    renderSlices();
  });

  $("#sliceSearch").addEventListener("input", (e) => {
    state.sliceQuery = e.target.value;
    renderSlices();
  });

  $$(".mode-btn").forEach((btn) =>
    btn.addEventListener("click", () => {
      state.sliceDisplay = btn.dataset.display;
      $$(".mode-btn").forEach((b) => b.classList.toggle("active", b === btn));
      renderSlices();
    })
  );

  $("#btnToggleDockedMindmap")?.addEventListener("click", () => {
    setMindmapDocked(!state.mindmapDocked);
  });

  // Global delegated clicks (Ref Tracer, Term Inspector, Slice/Figure/Dimension Jump, Image Zoom)
  document.addEventListener("click", (e) => {
    const refBtn = e.target.closest("[data-trace-ref]");
    if (refBtn) {
      openRefTracer(Number(refBtn.dataset.traceRef));
      return;
    }
    const termBtn = e.target.closest("[data-open-term]");
    if (termBtn) {
      openTermDrawer(termBtn.dataset.openTerm);
      return;
    }
    const figJump = e.target.closest("[data-jump-figure]");
    if (figJump) {
      jumpToFigure(figJump.dataset.jumpFigure, figJump.dataset.fromMindmap === "1");
      return;
    }
    const sliceJump = e.target.closest("[data-jump-slice]");
    if (sliceJump) {
      jumpToSlice(sliceJump.dataset.jumpSlice, sliceJump.dataset.fromMindmap === "1");
      return;
    }
    const dimJump = e.target.closest("[data-jump-dim]");
    if (dimJump && dimJump.dataset.jumpDim) {
      jumpToDimension(dimJump.dataset.jumpDim);
      return;
    }
    const zoomImg = e.target.closest("img.zoomable");
    if (zoomImg) {
      $("#lightboxImg").src = zoomImg.src;
      $("#lightboxCaption").textContent = zoomImg.dataset.caption || zoomImg.alt || "";
      $("#lightbox").classList.remove("hidden");
    }
  });

  // Upload dropzone
  const dz = $("#dropZone");
  const fileInput = $("#pdfFileInput");
  $("#pickPdfBtn").addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (e) => uploadPdfFile(e.target.files[0]));
  dz.addEventListener("dragover", (e) => {
    e.preventDefault();
    dz.classList.add("dragover");
  });
  dz.addEventListener("dragleave", () => dz.classList.remove("dragover"));
  dz.addEventListener("drop", (e) => {
    e.preventDefault();
    dz.classList.remove("dragover");
    uploadPdfFile(e.dataTransfer.files[0]);
  });

  // LLM provider 1-click presets & live connectivity test
  const LLM_PRESETS = {
    agy_neon: { provider: "agy_cli", url: "", model: "gemini-4-neon-high", proxyHint: "免 API Key！直接调用你本机已登录的官方 Antigravity CLI (Gemini 4 Neon High)" },
    agy_flash: { provider: "agy_cli", url: "", model: "gemini-3.8-flash-high", proxyHint: "免 API Key！极速版 Gemini 3.8 Flash，大批量切段翻译飞快" },
    deepseek: { provider: "openai_compatible", url: "https://api.deepseek.com/v1", model: "deepseek-chat", proxyHint: "国内直连免代理，填入 DeepSeek API Key 即可" },
    gemini: { provider: "openai_compatible", url: "https://generativelanguage.googleapis.com/v1beta/openai", model: "gemini-2.5-flash", proxyHint: "填入 Google AI Studio API Key 即可测试" },
    qwen: { provider: "openai_compatible", url: "https://dashscope.aliyuncs.com/compatible-mode/v1", model: "qwen-plus", proxyHint: "国内直连免代理，填入阿里云百炼 API Key 即可" },
    ollama: { provider: "openai_compatible", url: "http://127.0.0.1:11434/v1", model: "qwen2.5:14b", proxyHint: "本地 Ollama 无需 API Key，确保 ollama serve 正在运行" },
  };
  $("#cfgProvider")?.addEventListener("change", syncProviderFieldVisibility);
  $("#llmPresetBar")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-llm-preset]");
    if (!btn) return;
    const p = LLM_PRESETS[btn.dataset.llmPreset];
    if (!p) return;
    if ($("#cfgProvider")) $("#cfgProvider").value = p.provider;
    if (p.url) $("#cfgBaseUrl").value = p.url;
    $("#cfgModel").value = p.model;
    syncProviderFieldVisibility();
    $$("#llmPresetBar .chip").forEach((c) => c.classList.toggle("active", c === btn));
    const toast = $("#settingsToast");
    toast.classList.remove("hidden");
    toast.textContent = `已切换至 ${btn.textContent}！${p.proxyHint}`;
  });

  $("#btnTestLlm")?.addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    const toast = $("#settingsToast");
    toast.classList.remove("hidden");
    toast.textContent = "正在测试连接…";
    btn.disabled = true;
    try {
      const res = await apiJson("/api/llm/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          llm_provider: $("#cfgProvider")?.value || "agy_cli",
          llm_base_url: $("#cfgBaseUrl").value.trim(),
          llm_model: $("#cfgModel").value.trim(),
          llm_api_key: $("#cfgApiKey").value.trim(),
          http_proxy: $("#cfgProxy").value.trim(),
        }),
      });
      if (res.ok) {
        toast.textContent = `连接成功！引擎：${res.provider || "HTTP"} · 模型：${res.model} · 耗时 ${res.latency_ms} ms · 返回：${res.reply}`;
      } else {
        toast.textContent = `连接失败：${res.error}`;
      }
    } catch (err) {
      toast.textContent = "测试异常：" + err.message;
    } finally {
      btn.disabled = false;
    }
  });

  // Settings save & re-analyze
  $("#btnSaveConfig").addEventListener("click", async () => {
    const toast = $("#settingsToast");
    try {
      await apiJson("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          llm_provider: $("#cfgProvider")?.value || "agy_cli",
          llm_base_url: $("#cfgBaseUrl").value.trim(),
          llm_model: $("#cfgModel").value.trim(),
          llm_api_key: $("#cfgApiKey").value.trim(),
          zotero_data_dir: $("#cfgZoteroDir")?.value.trim() || "",
          zotero_mcp_command: $("#cfgZoteroMcp")?.value.trim() || "",
          ppt_master_dir: $("#cfgPptMasterDir")?.value.trim() || "",
          http_proxy: $("#cfgProxy").value.trim(),
        }),
      });
      toast.textContent = "配置已保存到 ~/.paperlens/config.json";
      toast.classList.remove("hidden");
    } catch (err) {
      toast.textContent = "保存失败：" + err.message;
      toast.classList.remove("hidden");
    }
  });

  $("#btnRunLlmCurrent").addEventListener("click", async () => {
    if (!state.currentPaperId) return;
    const toast = $("#settingsToast");
    toast.classList.remove("hidden");
    toast.textContent = "正在后台运行 AI 解读…";
    try {
      const { job_id } = await apiJson(
        `/api/papers/${encodeURIComponent(state.currentPaperId)}/analyze`,
        { method: "POST" }
      );
      const timer = setInterval(async () => {
        const job = await apiJson(`/api/jobs/${job_id}`);
        toast.textContent = `[${job.progress || 0}%] ${job.message}`;
        if (job.status === "done") {
          clearInterval(timer);
          await loadPaper(state.currentPaperId);
        } else if (job.status === "error") {
          clearInterval(timer);
        }
      }, 900);
    } catch (err) {
      toast.textContent = "启动失败：" + err.message;
    }
  });
}

init();
