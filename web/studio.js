/**
 * studio.js — Research Topics Sidebar, Zotero/MCP Importer & Editable Literature PPT Studio
 */

const COLOR_HEX = {
  teal: "#2a9d99",
  blue: "#62aef0",
  amber: "#dd5b00",
  purple: "#d6b6f6",
  emerald: "#1aae39",
  rose: "#ff64c8",
};

export function createStudioController(ctx) {
  const { state, $, $$, esc, apiJson, assetUrl, loadPaper, refreshPaperList, switchTab, onTopicsChanged } = ctx;

  const studio = {
    topics: [],
    activeTopicId: "all", // all | uncategorized | <topic_id>
    newTopicColor: "teal",
    draggingPaperId: null,
    editingPaperTopicsId: null,
    toastTimer: null,
    zoteroStatus: null,
    zoteroLib: null,
    zoteroColFilter: "all",
    zoteroQuery: "",
    zoteroHideTranslated: true,
    zoteroSelectedKeys: new Set(),

    pptPresets: null,
    pptWizardOpen: false,
    pptWizardConfig: {
      style_id: "academic-research",
      audience: "cross_discipline",
      focus: ["background", "objective", "methods", "validation", "results", "innovations", "critical"],
      density: "standard",
      transition: "fade",
      animation: "none",
      custom_note: "",
      use_llm: false,
    },
    activeSlideIdx: 0,
    presentIdx: 0,
    svgCacheBust: Date.now(),
    dirtySlide: false,
  };

  /* ==================== 1. TOPICS SIDEBAR ==================== */
  function showSidebarToast(msg) {
    const sidebar = $("#topicSidebar");
    if (!sidebar) return;
    let el = $("#sidebarToast");
    if (!el) {
      el = document.createElement("div");
      el.id = "sidebarToast";
      el.className = "sidebar-toast";
      sidebar.appendChild(el);
    }
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(studio.toastTimer);
    studio.toastTimer = setTimeout(() => el.classList.remove("show"), 2600);
  }

  function getPaperTopics(paperId) {
    return studio.topics.filter((t) => (t.paper_ids || []).includes(paperId));
  }

  async function loadTopics() {
    const { topics } = await apiJson("/api/topics");
    studio.topics = topics || [];
    renderTopicsSidebar();
    populateTopicSelects();
    onTopicsChanged?.();
  }

  function getFilteredSidebarPapers() {
    const all = state.papers || [];
    if (studio.activeTopicId === "all") return all;
    if (studio.activeTopicId === "uncategorized") {
      const assigned = new Set(studio.topics.flatMap((t) => t.paper_ids || []));
      return all.filter((p) => !assigned.has(p.paper_id));
    }
    const topic = studio.topics.find((t) => t.id === studio.activeTopicId);
    const idSet = new Set(topic?.paper_ids || []);
    return all.filter((p) => idSet.has(p.paper_id));
  }

  function populateTopicSelects() {
    const opts = [
      `<option value="">不指定课题（或自动按 Zotero 分类新建）</option>`,
      ...studio.topics.map((t) => `<option value="${esc(t.id)}">${esc(t.name)}</option>`),
    ].join("");
    const uSel = $("#uploadTopicSelect");
    if (uSel) {
      uSel.innerHTML = opts;
      if (studio.activeTopicId !== "all" && studio.activeTopicId !== "uncategorized") {
        uSel.value = studio.activeTopicId;
      }
    }
    const zSel = $("#zoteroTargetTopic");
    if (zSel) {
      zSel.innerHTML = [
        `<option value="">自动按 Zotero 分类同步课题</option>`,
        ...studio.topics.map((t) => `<option value="${esc(t.id)}">归入：${esc(t.name)}</option>`),
      ].join("");
      if (studio.activeTopicId !== "all" && studio.activeTopicId !== "uncategorized") {
        zSel.value = studio.activeTopicId;
      }
    }
  }

  function renderTopicsSidebar() {
    const allPapers = state.papers || [];
    const assignedSet = new Set(studio.topics.flatMap((t) => t.paper_ids || []));
    const uncatCount = allPapers.filter((p) => !assignedSet.has(p.paper_id)).length;

    const listEl = $("#topicList");
    if (!listEl) return;

    const baseItems = `
      <button class="topic-item ${studio.activeTopicId === "all" ? "active" : ""}" data-select-topic="all">
        <span class="topic-item-left"><span class="topic-dot" style="background:var(--text-muted)"></span><span class="topic-name-txt">全部文献</span></span>
        <span class="badge">${allPapers.length}</span>
      </button>
      <button class="topic-item droppable-topic ${studio.activeTopicId === "uncategorized" ? "active" : ""}" data-select-topic="uncategorized" data-drop-topic="uncategorized" title="拖拽文献到此可移出所有课题">
        <span class="topic-item-left"><span class="topic-dot" style="background:var(--text-faint)"></span><span class="topic-name-txt">未分类文献</span></span>
        <span class="topic-right-actions">
          <span class="drop-hint-pill">松开移出</span>
          <span class="badge">${uncatCount}</span>
        </span>
      </button>
    `;

    const customItems = studio.topics
      .map((t) => {
        const count = (t.paper_ids || []).filter((pid) => allPapers.some((p) => p.paper_id === pid)).length;
        const cHex = COLOR_HEX[t.color] || COLOR_HEX.blue;
        return `
          <div class="topic-item droppable-topic ${studio.activeTopicId === t.id ? "active" : ""}" data-select-topic="${esc(t.id)}" data-drop-topic="${esc(t.id)}" title="${esc(t.description || t.name)}（可拖拽文献卡片到此归类）">
            <span class="topic-item-left">
              <span class="topic-dot" style="background:${cHex}"></span>
              <span class="topic-name-txt">${esc(t.name)}</span>
            </span>
            <span class="topic-right-actions">
              <span class="drop-hint-pill">+ 移入</span>
              <span class="badge">${count}</span>
              <button class="topic-del-btn" data-delete-topic="${esc(t.id)}" title="删除此课题">✕</button>
            </span>
          </div>
        `;
      })
      .join("");

    listEl.innerHTML = baseItems + customItems;

    // Render papers inside selected topic
    const curTopic = studio.topics.find((t) => t.id === studio.activeTopicId);
    $("#sidebarPaperListTitle").textContent =
      studio.activeTopicId === "all"
        ? `全部文献 (${allPapers.length})`
        : studio.activeTopicId === "uncategorized"
        ? `未分类文献 (${uncatCount})`
        : `${curTopic?.name || "课题文献"}`;

    const assignBtn = $("#btnAssignCurrentPaper");
    if (assignBtn) {
      const canAssign = Boolean(curTopic && state.currentPaperId && !(curTopic.paper_ids || []).includes(state.currentPaperId));
      assignBtn.classList.toggle("hidden", !canAssign);
    }

    const papers = getFilteredSidebarPapers();
    const pListEl = $("#sidebarPaperList");
    if (!papers.length) {
      pListEl.innerHTML = `<div style="font-size:12px;color:var(--text-muted);padding:10px 6px">该课题下暂无文献，可直接将「全部文献 / 未分类文献」中的卡片拖拽到上方课题中。</div>`;
      return;
    }

    pListEl.innerHTML =
      `<div class="sb-drag-tip">拖动卡片到上方课题即可归类，或点「分类」修改</div>` +
      papers
        .map((p) => {
          const pTopics = getPaperTopics(p.paper_id);
          const isEditing = studio.editingPaperTopicsId === p.paper_id;
          const topicTagsHtml = pTopics.length
            ? pTopics
                .map((t) => {
                  const cHex = COLOR_HEX[t.color] || COLOR_HEX.blue;
                  return `<span class="sb-topic-tag" style="--tag-c:${cHex}" data-toggle-paper-cat="${esc(p.paper_id)}" title="点击修改所属课题"><span class="sb-topic-tag-dot" style="background:${cHex}"></span>${esc(t.name)}</span>`;
                })
                .join("")
            : `<span class="sb-topic-tag uncat" data-toggle-paper-cat="${esc(p.paper_id)}" title="点击分配到课题">未分类</span>`;

          const popoverHtml = isEditing
            ? `
              <div class="sb-topic-popover" data-cat-popover="${esc(p.paper_id)}">
                <div class="sb-topic-popover-head">
                  <span>选择所属课题（可多选）</span>
                  <button class="link-btn" data-close-cat-popover="1">完成</button>
                </div>
                ${
                  studio.topics.length
                    ? studio.topics
                        .map((t) => {
                          const checked = (t.paper_ids || []).includes(p.paper_id);
                          const cHex = COLOR_HEX[t.color] || COLOR_HEX.blue;
                          return `
                            <label class="sb-topic-opt ${checked ? "checked" : ""}">
                              <input type="checkbox" data-cat-check="${esc(p.paper_id)}::${esc(t.id)}" ${checked ? "checked" : ""} />
                              <span class="topic-dot" style="background:${cHex}"></span>
                              <span class="sb-topic-opt-name">${esc(t.name)}</span>
                            </label>
                          `;
                        })
                        .join("")
                    : `<div style="font-size:12px;color:var(--text-muted);padding:4px 0">暂无课题，请先点击上方「+ 新建课题」</div>`
                }
                ${
                  pTopics.length
                    ? `<button class="sb-topic-clear-btn" data-clear-paper-topics="${esc(p.paper_id)}">移出所有课题（设为未分类）</button>`
                    : ""
                }
              </div>
            `
            : "";

          return `
            <div class="sb-paper-card ${p.paper_id === state.currentPaperId ? "active" : ""}" draggable="true" data-paper-id="${esc(p.paper_id)}" data-open-paper="${esc(p.paper_id)}" title="点击阅读 · 拖拽到上方课题框可直接修改分类">
              <div class="sb-paper-head">
                <span class="sb-drag-handle" title="按住拖拽到上方课题">⋮⋮</span>
                <div class="sb-paper-title">${esc(p.title_zh || p.title)}</div>
              </div>
              <div class="sb-paper-tags">${topicTagsHtml}</div>
              <div class="sb-paper-meta">
                <span>${p.page_count}页 · ${p.figure_count}图 ${p.has_ppt ? "· 已有 PPT" : ""}</span>
                <div style="display:flex;align-items:center;gap:6px">
                  <button class="sb-cat-btn ${isEditing ? "active" : ""}" data-toggle-paper-cat="${esc(p.paper_id)}" title="修改所属课题分类">分类</button>
                  ${
                    curTopic
                      ? `<button class="link-btn" style="color:var(--text-muted)" data-remove-paper-topic="${esc(curTopic.id)}::${esc(p.paper_id)}" title="移出当前课题">移出</button>`
                      : ""
                  }
                </div>
              </div>
              ${popoverHtml}
            </div>
          `;
        })
        .join("");
  }

  /* ==================== 2. ZOTERO / ZOTERO MCP BRIDGE ==================== */
  async function refreshZoteroStatus() {
    try {
      const st = await apiJson("/api/zotero/status");
      studio.zoteroStatus = st;
      const dot = $("#zoteroStatusDot");
      const sub = $("#zoteroStatusSub");
      if (st.local_sqlite_available) {
        dot?.classList.add("online");
        const extra = st.mcp_configured
          ? "MCP + 本机库就绪"
          : st.local_api_available
          ? "Zotero 7 本地 API + 文献库就绪"
          : "本机 Zotero 文献库已连接";
        if (sub) sub.textContent = extra;
      } else {
        if (sub) sub.textContent = "点击配置 Zotero 路径或 MCP";
      }
    } catch {
      const sub = $("#zoteroStatusSub");
      if (sub) sub.textContent = "点击连接 Zotero / MCP";
    }
  }

  async function openZoteroModal() {
    $("#zoteroModal").classList.remove("hidden");
    $("#zoteroProgressBox").classList.add("hidden");
    studio.zoteroSelectedKeys.clear();
    populateTopicSelects();

    const [st, lib] = await Promise.all([
      apiJson("/api/zotero/status"),
      apiJson("/api/zotero/library"),
    ]);
    studio.zoteroStatus = st;
    studio.zoteroLib = lib;
    $("#zoteroMcpCmdInput").value = st.mcp_command || "";

    $("#zoteroConnBanner").innerHTML = `
      <span class="meta-pill accent">${st.local_sqlite_available ? "✓ 本机 Zotero SQLite 已连接" : "✗ 未找到本机 zotero.sqlite"}</span>
      <span class="meta-pill">${st.local_api_available ? "✓ Zotero 7 Local API 在线 (23119)" : "○ Zotero Local API 未开启"}</span>
      <span class="meta-pill">${st.mcp_configured ? `✓ Zotero MCP: ${esc(st.mcp_command)}` : "○ Zotero MCP 可选配置"}</span>
      ${lib.available ? `<span class="meta-pill">共发现 <strong>${lib.collections.length}</strong> 个分类 · <strong>${lib.total_pdfs}</strong> 份本地 PDF</span>` : ""}
    `;

    renderZoteroCollections();
    renderZoteroItems();
  }

  function renderZoteroCollections() {
    const cols = studio.zoteroLib?.collections || [];
    const el = $("#zoteroColChips");
    if (!el) return;
    const total = studio.zoteroLib?.total_pdfs || 0;
    el.innerHTML = [
      `<button class="chip ${studio.zoteroColFilter === "all" ? "active" : ""}" data-zcol="all">全部分类 (${total})</button>`,
      ...cols.map(
        (c) =>
          `<button class="chip ${String(studio.zoteroColFilter) === String(c.id) ? "active" : ""}" data-zcol="${c.id}">${esc(c.name)} (${c.pdf_count})</button>`
      ),
    ].join("");
  }

  function renderZoteroItems() {
    const items = studio.zoteroLib?.items || [];
    const q = studio.zoteroQuery.trim().toLowerCase();
    const filtered = items.filter((it) => {
      if (studio.zoteroHideTranslated && it.is_translated_copy) return false;
      if (studio.zoteroColFilter !== "all" && !(it.collection_ids || []).includes(Number(studio.zoteroColFilter))) {
        return false;
      }
      if (!q) return true;
      return `${it.title} ${it.authors} ${it.journal} ${it.filename} ${(it.collection_names || []).join(" ")}`
        .toLowerCase()
        .includes(q);
    });

    const listEl = $("#zoteroItemList");
    if (!studio.zoteroLib?.available) {
      listEl.innerHTML = `<div style="padding:16px;font-size:14px;color:var(--rose)">${esc(studio.zoteroLib?.error || "无法读取 Zotero 目录")}</div>`;
      return;
    }
    if (!filtered.length) {
      listEl.innerHTML = `<div style="padding:16px;font-size:14px;color:var(--text-muted)">当前筛选条件下没有本地 PDF 附件。</div>`;
      updateZoteroCount();
      return;
    }

    listEl.innerHTML = filtered
      .map((it) => {
        const checked = studio.zoteroSelectedKeys.has(it.attachment_key);
        return `
          <label class="z-item-row ${checked ? "selected" : ""}">
            <input type="checkbox" data-zkey="${esc(it.attachment_key)}" ${checked ? "checked" : ""} />
            <div class="z-item-main">
              <div class="z-item-title">
                ${esc(it.title)}
                ${it.is_translated_copy ? `<span class="meta-pill" style="margin-left:6px">译文副本</span>` : ""}
              </div>
              <div class="z-item-sub">
                ${it.authors ? `<span>${esc(it.authors)}</span>` : ""}
                ${it.year ? `<span>${it.year}</span>` : ""}
                ${it.journal ? `<span>${esc(it.journal)}</span>` : ""}
                <span>${it.size_mb} MB</span>
                ${(it.collection_names || []).map((cn) => `<span class="meta-pill accent">${esc(cn)}</span>`).join("")}
              </div>
            </div>
          </label>
        `;
      })
      .join("");
    updateZoteroCount();
  }

  function updateZoteroCount() {
    const n = studio.zoteroSelectedKeys.size;
    $("#zoteroSelectedCount").textContent = `已选 ${n} 篇`;
    $("#btnDoZoteroImport").disabled = n === 0;
  }

  async function runZoteroImport() {
    const keys = Array.from(studio.zoteroSelectedKeys);
    if (!keys.length) return;
    const box = $("#zoteroProgressBox");
    box.classList.remove("hidden");
    $("#zoteroProgressMsg").textContent = "正在提交 Zotero 导入任务...";
    $("#zoteroProgressPct").textContent = "5%";
    $("#zoteroProgressBar").style.width = "5%";
    $("#btnDoZoteroImport").disabled = true;

    const targetTopic = $("#zoteroTargetTopic").value || null;
    try {
      const { job_id } = await apiJson("/api/zotero/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          attachment_keys: keys,
          target_topic_id: targetTopic,
          auto_create_topic: !targetTopic,
          run_llm: $("#zoteroRunLlm").checked,
        }),
      });
      const timer = setInterval(async () => {
        try {
          const job = await apiJson(`/api/jobs/${job_id}`);
          $("#zoteroProgressMsg").textContent = job.message || job.status;
          $("#zoteroProgressPct").textContent = `${job.progress || 0}%`;
          $("#zoteroProgressBar").style.width = `${job.progress || 0}%`;
          if (job.status === "done") {
            clearInterval(timer);
            await refreshPaperList();
            await loadTopics();
            if (job.topic_id) {
              studio.activeTopicId = job.topic_id;
              renderTopicsSidebar();
            }
            if (job.paper_id) {
              await loadPaper(job.paper_id);
            }
            $("#zoteroModal").classList.add("hidden");
            switchTab("overview");
          } else if (job.status === "error") {
            clearInterval(timer);
            $("#btnDoZoteroImport").disabled = false;
          }
        } catch {
          clearInterval(timer);
          $("#btnDoZoteroImport").disabled = false;
        }
      }, 750);
    } catch (err) {
      $("#zoteroProgressMsg").textContent = "导入失败：" + err.message;
      $("#btnDoZoteroImport").disabled = false;
    }
  }

  /* ==================== 3. LITERATURE PPT STUDIO ==================== */
  async function ensurePptPresets() {
    if (!studio.pptPresets) {
      studio.pptPresets = await apiJson("/api/ppt/presets");
    }
    return studio.pptPresets;
  }

  function getThemeById(styleId) {
    const styles = studio.pptPresets?.styles || [];
    return styles.find((s) => s.id === styleId) || styles[0] || {
      id: "nature_minimal",
      bg: "#FFFFFF",
      surface: "#F4F6FA",
      primary: "#1E3A8A",
      accent: "#0F766E",
      text: "#171B26",
      muted: "#5B6476",
      callout_bg: "#EFF6FF",
      cover_bg: "#0F1E46",
      cover_text: "#FFFFFF",
    };
  }

  async function renderPptTab() {
    const root = $("#tab-ppt");
    if (!root || !state.bundle) return;
    await ensurePptPresets();

    const deck = state.bundle.deck;
    if (!deck || studio.pptWizardOpen) {
      renderPptWizard(root, Boolean(deck));
    } else {
      renderPptWorkbench(root, deck);
    }
  }

  function renderPptWizard(root, hasExistingDeck) {
    const { styles, audiences, focus_options, transitions, animations, installed, ppt_master_dir, brands } = studio.pptPresets;
    const cfg = studio.pptWizardConfig;
    // Show top 8 curated styles + toggle for all 14 official ppt-master styles
    const visibleStyles = styles.slice(0, 7);

    root.innerHTML = `
      <div class="ppt-wizard-card">
        <div class="zotero-conn-banner" style="justify-content:space-between">
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
            <span class="meta-pill accent">${installed ? "已连接本机 PPT-Master" : "未检测到 PPT-Master，将使用内置导出"}</span>
            ${installed ? `<span class="meta-pill">目录：<code>${esc(ppt_master_dir)}</code></span>` : ""}
            ${installed ? `<span class="meta-pill">${styles.length} 套风格 · ${(brands || []).length} 套品牌库</span>` : ""}
          </div>
          ${
            hasExistingDeck
              ? `<button id="btnBackToDeck" class="btn btn-ghost btn-sm">← 返回当前工程</button>`
              : ""
          }
        </div>

        <div>
          <h2 style="margin:0 0 4px">文献汇报 PPT</h2>
          <p style="margin:0;font-size:14px;color:var(--text-muted)">选好风格、听众和重点，生成可编辑的 .pptx 与逐页演讲稿。生成后可在 SVG 编辑器里继续精修。</p>
        </div>

        <div>
          <div class="ppt-step-title">① 风格</div>
          <div class="ppt-style-grid">
            ${visibleStyles
              .map(
                (st) => `
              <button type="button" class="ppt-style-option ${cfg.style_id === st.id ? "active" : ""}" data-ppt-style="${esc(st.id)}">
                <div class="style-mini-preview" style="background:${st.bg}">
                  <div style="display:flex;justify-content:space-between;align-items:center">
                    <div class="style-mini-bar" style="background:${st.primary}"></div>
                    <span style="width:14px;height:14px;border-radius:4px;background:${st.accent}"></span>
                  </div>
                  <div class="style-mini-lines">
                    <span style="width:88%;background:${st.text}"></span>
                    <span style="width:68%;background:${st.muted}"></span>
                  </div>
                  <div style="height:12px;border-radius:4px;background:${st.callout_bg};border-left:3px solid ${st.accent}"></div>
                </div>
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;gap:4px">
                  <strong style="font-size:14px">${esc(st.name)}</strong>
                </div>
                <div style="margin-bottom:4px"><span class="meta-pill" style="font-size:12px">${esc(st.tag)}</span></div>
                <div style="font-size:12px;color:var(--text-muted);line-height:1.4">${esc((st.desc || "").slice(0, 76))}</div>
              </button>
            `
              )
              .join("")}
          </div>
        </div>

        <div>
          <div class="ppt-step-title">② 选择汇报对象（自动调整讲解深度与大白话比例）</div>
          <div class="ppt-aud-grid">
            ${audiences
              .map(
                (aud) => `
              <button type="button" class="ppt-aud-option ${cfg.audience === aud.id ? "active" : ""}" data-ppt-aud="${esc(aud.id)}">
                <div style="font-weight:800;font-size:14px;margin-bottom:4px">${esc(aud.label)}</div>
                <div style="font-size:12px;color:var(--text-muted)">${esc(aud.hint)}</div>
              </button>
            `
              )
              .join("")}
          </div>
        </div>

        <div>
          <div class="ppt-step-title">③ 勾选本次汇报重点（多选）</div>
          <div class="ppt-focus-chips">
            ${focus_options
              .map(
                (fo) => `
              <button type="button" class="focus-chip ${cfg.focus.includes(fo.id) ? "active" : ""}" data-ppt-focus="${esc(fo.id)}">
                ${cfg.focus.includes(fo.id) ? "✓ " : "＋ "}${esc(fo.label)}
              </button>
            `
              )
              .join("")}
          </div>
        </div>

        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px">
          <div>
            <div class="ppt-step-title">④ 篇幅、转场与动画（PPT-Master 参数）</div>
            <div class="filter-chips" style="margin-bottom:10px">
              ${[
                ["compact", "精简速报 (7–8 页)"],
                ["standard", "标准组会 (10–12 页)"],
                ["deep", "深度精讲 (13–15 页)"],
              ]
                .map(
                  ([id, label]) =>
                    `<button type="button" class="chip ${cfg.density === id ? "active" : ""}" data-ppt-density="${id}">${label}</button>`
                )
                .join("")}
            </div>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr));gap:8px;margin-bottom:10px">
              <label class="form-field">
                <span style="font-size:12px">页面切换转场 (-t)</span>
                <select id="pptTransitionSel" class="paper-select" style="width:100%;max-width:100%;min-width:0">
                  ${(transitions || []).map((tr) => `<option value="${esc(tr.id)}" ${cfg.transition === tr.id ? "selected" : ""}>${esc(tr.label)}</option>`).join("")}
                </select>
              </label>
              <label class="form-field">
                <span style="font-size:12px">对象出场动画 (-a)</span>
                <select id="pptAnimSel" class="paper-select" style="width:100%;max-width:100%;min-width:0">
                  ${(animations || []).map((an) => `<option value="${esc(an.id)}" ${cfg.animation === an.id ? "selected" : ""}>${esc(an.label)}</option>`).join("")}
                </select>
              </label>
            </div>
            <label class="checkbox-row">
              <input type="checkbox" id="pptUseLlm" ${cfg.use_llm ? "checked" : ""} />
              <span>启用已配置大模型润色脚本（不勾选也能秒级走完 PPT-Master SVG 质检与编译）</span>
            </label>
          </div>
          <div>
            <div class="ppt-step-title">⑤ 额外定制重点（可选）</div>
            <textarea id="pptCustomNote" rows="4" style="width:100%;padding:9px 12px;border-radius:8px;border:1px solid var(--border);background:var(--surface-alt);color:var(--text);font-family:var(--font-sans);font-size:14px" placeholder="例如：重点讲清楚 13-mer 外膜匹配机制、MAD5.1 与 MAD2.2 的权衡，以及对我们课题组的启发...">${esc(cfg.custom_note)}</textarea>
          </div>
        </div>

        <div style="display:flex;justify-content:flex-end;align-items:center;gap:12px;border-top:1px solid var(--border);padding-top:16px">
          <span id="pptGenStatus" style="font-size:14px;color:var(--text-muted)"></span>
          <button id="btnGeneratePpt" class="btn btn-primary" style="padding:10px 22px;font-size:15px">生成汇报 PPT</button>
        </div>
      </div>
    `;

    $("#btnBackToDeck")?.addEventListener("click", () => {
      studio.pptWizardOpen = false;
      renderPptTab();
    });

    $$("[data-ppt-style]").forEach((btn) =>
      btn.addEventListener("click", () => {
        cfg.style_id = btn.dataset.pptStyle;
        renderPptTab();
      })
    );
    $$("[data-ppt-aud]").forEach((btn) =>
      btn.addEventListener("click", () => {
        cfg.audience = btn.dataset.pptAud;
        renderPptTab();
      })
    );
    $$("[data-ppt-focus]").forEach((btn) =>
      btn.addEventListener("click", () => {
        const fid = btn.dataset.pptFocus;
        if (cfg.focus.includes(fid)) {
          if (cfg.focus.length > 1) cfg.focus = cfg.focus.filter((x) => x !== fid);
        } else {
          cfg.focus.push(fid);
        }
        renderPptTab();
      })
    );
    $$("[data-ppt-density]").forEach((btn) =>
      btn.addEventListener("click", () => {
        cfg.density = btn.dataset.pptDensity;
        renderPptTab();
      })
    );
    $("#pptTransitionSel")?.addEventListener("change", (e) => { cfg.transition = e.target.value; });
    $("#pptAnimSel")?.addEventListener("change", (e) => { cfg.animation = e.target.value; });
    $("#pptUseLlm")?.addEventListener("change", (e) => { cfg.use_llm = e.target.checked; });
    $("#pptCustomNote")?.addEventListener("input", (e) => { cfg.custom_note = e.target.value; });

    $("#btnGeneratePpt").addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      btn.disabled = true;
      $("#pptGenStatus").textContent = "正在生成：初始化工程 → 生成幻灯片 → 拆分演讲稿 → 质量检查 → 编译 .pptx…";
      try {
        const res = await apiJson(
          `/api/papers/${encodeURIComponent(state.currentPaperId)}/ppt/generate`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(cfg),
          }
        );
        state.bundle.deck = res.deck;
        state.bundle.ppt_master = res.ppt_master;
        studio.pptWizardOpen = false;
        studio.activeSlideIdx = 0;
        studio.svgCacheBust = Date.now();
        studio.dirtySlide = false;
        await refreshPaperList();
        renderTopicsSidebar();
        renderPptTab();
      } catch (err) {
        $("#pptGenStatus").textContent = "生成失败：" + err.message;
        btn.disabled = false;
      }
    });
  }

  function renderSlidePreviewHtml(slide, idx, total, styleId) {
    const t = getThemeById(styleId);
    const figs = state.bundle.manifest?.figures || [];
    const fig = figs.find((f) => f.id === slide.figure_id);

    if (slide.layout === "cover") {
      return `
        <div class="slide-aspect-frame">
          <div class="slide-render" style="background:${t.cover_bg};color:${t.cover_text};justify-content:center;padding-left:38px">
            <div class="slide-cover-bar" style="background:${t.accent}"></div>
            <div class="slide-tag" style="display:inline-block;align-self:flex-start;background:${t.accent};color:#fff;padding:3px 10px;border-radius:6px;margin-bottom:14px">${esc(slide.tag || "LITERATURE SEMINAR")}</div>
            <h2 class="slide-title" style="color:${t.cover_text};font-size:clamp(20px,2.5vw,30px);margin-bottom:8px">${esc(slide.title)}</h2>
            ${slide.subtitle ? `<p class="slide-subtitle" style="color:#cbd5e1;margin-bottom:18px">${esc(slide.subtitle)}</p>` : ""}
            <ul style="margin:0;padding-left:18px;font-size:13px;color:#e2e8f0;line-height:1.7">
              ${(slide.bullets || []).map((b) => `<li>${esc(b)}</li>`).join("")}
            </ul>
          </div>
        </div>
      `;
    }

    const metrics = slide.metrics || [];
    const kpiHtml = metrics.length
      ? `<div class="slide-kpi-row">
          ${metrics
            .map(
              (m) => `
            <div class="slide-kpi-card" style="background:${t.surface};border-color:${t.accent}">
              <div class="slide-kpi-val" style="color:${t.accent}">${esc(m.value)}</div>
              <div class="slide-kpi-lbl" style="color:${t.muted}">${esc(m.label)}</div>
            </div>
          `
            )
            .join("")}
        </div>`
      : "";

    const bullets = slide.bullets || [];
    let bodyHtml = "";
    if (fig) {
      bodyHtml = `
        <div class="slide-body-grid with-fig">
          <div class="slide-bullets-card" style="background:${t.surface};color:${t.text}">
            <ul>${bullets.map((b) => `<li>${esc(b)}</li>`).join("")}</ul>
          </div>
          <div class="slide-fig-card">
            <img src="${assetUrl(fig.image)}" alt="${esc(fig.label)}" />
            <span style="font-size:10px;color:#64748b;margin-top:4px">${esc(fig.label)} (P${fig.page})</span>
          </div>
        </div>
      `;
    } else if (slide.layout === "two_column" && bullets.length >= 4) {
      const mid = Math.ceil(bullets.length / 2);
      bodyHtml = `
        <div class="slide-body-grid two-col">
          <div class="slide-bullets-card" style="background:${t.surface};color:${t.text}">
            <ul>${bullets.slice(0, mid).map((b) => `<li>${esc(b)}</li>`).join("")}</ul>
          </div>
          <div class="slide-bullets-card" style="background:${t.surface};color:${t.text}">
            <ul>${bullets.slice(mid).map((b) => `<li>${esc(b)}</li>`).join("")}</ul>
          </div>
        </div>
      `;
    } else {
      bodyHtml = `
        <div class="slide-body-grid">
          <div class="slide-bullets-card" style="background:${t.surface};color:${t.text}">
            <ul>${bullets.map((b) => `<li>${esc(b)}</li>`).join("")}</ul>
          </div>
        </div>
      `;
    }

    return `
      <div class="slide-aspect-frame">
        <div class="slide-render" style="background:${t.bg};color:${t.text}">
          <div class="slide-top-strip" style="background:${t.primary}"></div>
          <div class="slide-tag" style="color:${t.accent}">${esc(slide.tag || `SLIDE ${idx + 1}`)}</div>
          <h2 class="slide-title" style="color:${t.primary}">${esc(slide.title)}</h2>
          ${slide.subtitle ? `<p class="slide-subtitle" style="color:${t.muted}">${esc(slide.subtitle)}</p>` : ""}
          ${kpiHtml}
          ${bodyHtml}
          ${
            slide.callout
              ? `<div class="slide-callout" style="background:${t.callout_bg};border-left-color:${t.accent};color:${t.text}">${esc(slide.callout)}</div>`
              : ""
          }
          <div class="slide-footer" style="color:${t.muted}">
            <span>PaperLens 文献汇报 · ${esc(state.bundle.manifest?.doi || state.currentPaperId)}</span>
            <strong>${idx + 1} / ${total}</strong>
          </div>
        </div>
      </div>
    `;
  }

  function scaleSlideFrames() {
    $$(".slide-aspect-frame").forEach((frame) => {
      const inner = frame.querySelector(".slide-render");
      if (!inner) return;
      const w = frame.clientWidth;
      if (w > 0) {
        inner.style.transform = `scale(${w / 960})`;
      }
    });
  }

  function renderRealSvgOrFallback(slide, idx, total, styleId, useRealSvg = true) {
    const pm = state.bundle.ppt_master;
    if (useRealSvg && pm && slide.svg_filename) {
      const url = `/api/papers/${encodeURIComponent(state.currentPaperId)}/ppt/svg/${encodeURIComponent(slide.svg_filename)}?t=${studio.svgCacheBust}`;
      return `
        <div class="slide-aspect-frame" style="background:#fff">
          <object type="image/svg+xml" data="${url}" aria-label="${esc(slide.svg_filename)}" style="width:100%;height:100%;display:block;pointer-events:none"></object>
        </div>
      `;
    }
    return renderSlidePreviewHtml(slide, idx, total, styleId);
  }

  function renderPptWorkbench(root, deck) {
    const slides = deck.slides || [];
    if (!slides.length) {
      studio.pptWizardOpen = true;
      renderPptTab();
      return;
    }
    if (studio.activeSlideIdx >= slides.length) studio.activeSlideIdx = slides.length - 1;
    const cur = slides[studio.activeSlideIdx];
    const figs = state.bundle.manifest?.figures || [];
    const styles = (studio.pptPresets.styles || []).slice(0, 7);
    const pm = state.bundle.ppt_master;
    const qsum = pm?.quality_summary;

    root.innerHTML = `
      ${
        pm
          ? `<div class="zotero-conn-banner" style="justify-content:space-between;margin-bottom:12px">
              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
                <span class="meta-pill accent">PPT-Master 工程</span>
                <span class="meta-pill">${pm.checker_rc === 0 ? `SVG 质检通过 (${qsum?.errors ?? 0} Errors)` : `质检返回码 ${pm.checker_rc}`}</span>
                <span class="meta-pill">${pm.export_rc === 0 ? "DrawingML .pptx 已就绪" : "导出待重试"}</span>
                <span class="meta-pill" title="${esc(pm.project_path)}">${esc(pm.project_name)}</span>
              </div>
              <div style="display:flex;gap:8px;flex-wrap:wrap">
                <button id="btnLaunchSvgEditor" class="btn btn-secondary btn-sm">在 SVG 编辑器中精修</button>
                <button id="btnRecompilePm" class="btn btn-ghost btn-sm" title="若在官方 SVG 编辑器做了拖拽修改，点此重新质检并编译 .pptx">重新质检编译</button>
              </div>
            </div>`
          : ""
      }

      <div class="ppt-workbench-bar">
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
          <strong style="font-size:15px">PPT-Master 工作台</strong>
          <select id="pptQuickStyle" class="paper-select" style="max-width:210px" title="一键实时换肤并重编 SVG">
            ${styles.map((st) => `<option value="${esc(st.id)}" ${deck.style_id === st.id ? "selected" : ""}>${esc(st.name)}</option>`).join("")}
          </select>
          <button id="btnPptAddSlide" class="btn btn-ghost btn-sm">＋ 新增一页</button>
          <button id="btnPptReconfig" class="btn btn-ghost btn-sm">重配前置条件</button>
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
          <span id="pptSaveIndicator" style="font-size:12px;color:var(--teal)">${pm ? "✓ 当前预览为 PPT-Master 原生矢量 SVG" : ""}</span>
          <button id="btnPptPresent" class="btn btn-secondary btn-sm">全屏放映</button>
          <button id="btnPptSave" class="btn btn-ghost btn-sm">保存并重编 SVG/PPTX</button>
          <button id="btnPptDownload" class="btn btn-primary btn-sm">下载 .pptx</button>
        </div>
      </div>

      <div class="ppt-workbench">
        <div class="ppt-thumbs-col" id="pptThumbsCol">
          ${slides
            .map(
              (s, i) => `
            <div class="ppt-thumb ${i === studio.activeSlideIdx ? "active" : ""}" data-slide-idx="${i}">
              <div class="ppt-thumb-head">
                <span>P${i + 1} · ${esc(s.svg_filename || s.layout)}</span>
                <div style="display:flex;gap:4px">
                  ${i > 0 ? `<button class="link-btn" data-move-slide="${i}:-1" title="上移">↑</button>` : ""}
                  ${i < slides.length - 1 ? `<button class="link-btn" data-move-slide="${i}:1" title="下移">↓</button>` : ""}
                  ${slides.length > 1 ? `<button class="link-btn" style="color:var(--rose)" data-del-slide="${i}" title="删除页">✕</button>` : ""}
                </div>
              </div>
              <div class="ppt-thumb-title">${esc(s.title || "未命名页面")}</div>
              ${s.figure_id ? `<span class="meta-pill accent" style="font-size:12px;margin-top:4px;display:inline-block">${esc(s.figure_id)}</span>` : ""}
            </div>
          `
            )
            .join("")}
        </div>

        <div class="ppt-stage-col">
          <div id="pptLivePreview">
            ${renderRealSvgOrFallback(cur, studio.activeSlideIdx, slides.length, deck.style_id, !studio.dirtySlide)}
          </div>
          <div class="ppt-notes-preview">
            <strong style="color:var(--teal);font-size:12px">当前页演讲者备注（已同步至 <code>notes/total.md</code> 并由 <code>total_md_split.py</code> 写入 .pptx）：</strong>
            <div id="pptNotesPreviewTxt" style="margin-top:4px;color:var(--text-muted)">${esc(cur.speaker_notes || "可在右侧编辑该页口语演讲稿...")}</div>
          </div>
          ${
            pm?.steps_log?.length
              ? `<details class="fig-caption-details">
                  <summary>查看 PPT-Master 官方管线执行日志（${pm.steps_log.length} 步）</summary>
                  ${pm.steps_log
                    .map(
                      (st) => `<div style="margin-top:8px">
                        <strong>${st.rc === 0 ? "" : ""} ${esc(st.step)} (rc=${st.rc})</strong>
                        <pre class="readme-pre" style="max-height:110px;margin-top:4px">${esc(st.output || "")}</pre>
                      </div>`
                    )
                    .join("")}
                </details>`
              : ""
          }
        </div>

        <div class="ppt-editor-col">
          <strong style="font-size:14px">编辑第 ${studio.activeSlideIdx + 1} 页内容</strong>
          <label>
            版式布局
            <select id="edLayout">
              ${[
                ["cover", "封面页 (Cover)"],
                ["agenda", "导览页 (Agenda)"],
                ["figure_focus", "图文并排 (Figure Focus)"],
                ["two_column", "双栏/列表 (Two Column)"],
                ["takeaways", "总结/审读页 (Takeaways)"],
              ]
                .map(([v, l]) => `<option value="${v}" ${cur.layout === v ? "selected" : ""}>${l}</option>`)
                .join("")}
            </select>
          </label>
          <label>
            顶部短标签 (Tag)
            <input id="edTag" type="text" value="${esc(cur.tag || "")}" />
          </label>
          <label>
            主标题
            <input id="edTitle" type="text" value="${esc(cur.title || "")}" />
          </label>
          <label>
            副标题
            <input id="edSubtitle" type="text" value="${esc(cur.subtitle || "")}" />
          </label>
          <label>
            嵌入论文原图 / 原表
            <select id="edFigure">
              <option value="">（不配图，纯文字版式）</option>
              ${figs
                .map(
                  (f) =>
                    `<option value="${esc(f.id)}" ${cur.figure_id === f.id ? "selected" : ""}>${esc(f.label)} (P${f.page})</option>`
                )
                .join("")}
            </select>
          </label>
          <label>
            核心要点（每行一条要点）
            <textarea id="edBullets" rows="5">${esc((cur.bullets || []).join("\n"))}</textarea>
          </label>
          <label>
            底部高亮总结 / 大白话提示 (Callout)
            <textarea id="edCallout" rows="2">${esc(cur.callout || "")}</textarea>
          </label>
          <label>
            演讲者逐字稿备注 (Speaker Notes)
            <textarea id="edNotes" rows="3">${esc(cur.speaker_notes || "")}</textarea>
          </label>
        </div>
      </div>
    `;

    // Instant HTML preview while typing; saving syncs straight to ppt-master SVGs + svg_quality_checker + svg_to_pptx
    const syncPreview = () => {
      studio.dirtySlide = true;
      $("#pptLivePreview").innerHTML = renderSlidePreviewHtml(
        cur,
        studio.activeSlideIdx,
        slides.length,
        deck.style_id
      );
      requestAnimationFrame(scaleSlideFrames);
      $("#pptNotesPreviewTxt").textContent = cur.speaker_notes || "可在右侧编辑该页口语演讲稿...";
      $("#pptSaveIndicator").textContent = "● 已修改（点「保存并重编」更新 SVG & PPTX）";
    };
    requestAnimationFrame(scaleSlideFrames);

    const persistDeck = async (silent = false) => {
      if (!silent) $("#pptSaveIndicator").textContent = "正在重新编译并更新 .pptx…";
      const res = await apiJson(`/api/papers/${encodeURIComponent(state.currentPaperId)}/ppt`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(deck),
      });
      if (res.deck) state.bundle.deck = res.deck;
      if (res.ppt_master) state.bundle.ppt_master = res.ppt_master;
      studio.svgCacheBust = Date.now();
      studio.dirtySlide = false;
      if (!silent) renderPptTab();
    };

    $("#btnLaunchSvgEditor")?.addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      btn.disabled = true;
      const orig = btn.textContent;
      btn.textContent = "正在启动 SVG 编辑器…";
      try {
        const info = await apiJson(
          `/api/papers/${encodeURIComponent(state.currentPaperId)}/ppt/launch-editor`,
          { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }
        );
        $("#svgEditorExternalLink").href = info.url;
        $("#svgEditorIframe").src = info.url;
        $("#svgEditorModal").classList.remove("hidden");
      } catch (err) {
        alert("启动 PPT-Master SVG 编辑器失败：" + err.message);
      } finally {
        btn.disabled = false;
        btn.textContent = orig;
      }
    });

    const triggerRecompile = async () => {
      $("#pptSaveIndicator").textContent = "正在重新质检并编译 .pptx…";
      const res = await apiJson(
        `/api/papers/${encodeURIComponent(state.currentPaperId)}/ppt/recompile`,
        { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }
      );
      state.bundle.ppt_master = res.ppt_master;
      studio.svgCacheBust = Date.now();
      studio.dirtySlide = false;
      renderPptTab();
    };

    $("#btnRecompilePm")?.addEventListener("click", triggerRecompile);

    $("#pptQuickStyle").addEventListener("change", async (e) => {
      deck.style_id = e.target.value;
      await persistDeck(false);
    });

    $("#edLayout").addEventListener("change", (e) => { cur.layout = e.target.value; syncPreview(); });
    $("#edTag").addEventListener("input", (e) => { cur.tag = e.target.value; syncPreview(); });
    $("#edTitle").addEventListener("input", (e) => { cur.title = e.target.value; syncPreview(); });
    $("#edSubtitle").addEventListener("input", (e) => { cur.subtitle = e.target.value; syncPreview(); });
    $("#edFigure").addEventListener("change", (e) => {
      cur.figure_id = e.target.value || null;
      if (cur.figure_id && cur.layout === "two_column") cur.layout = "figure_focus";
      syncPreview();
    });
    $("#edBullets").addEventListener("input", (e) => {
      cur.bullets = e.target.value.split("\n").map((x) => x.trim()).filter(Boolean);
      syncPreview();
    });
    $("#edCallout").addEventListener("input", (e) => { cur.callout = e.target.value; syncPreview(); });
    $("#edNotes").addEventListener("input", (e) => { cur.speaker_notes = e.target.value; syncPreview(); });

    $("#btnPptSave").addEventListener("click", () => persistDeck(false));
    $("#btnPptDownload").addEventListener("click", async () => {
      if (studio.dirtySlide) await persistDeck(true);
      window.open(`/api/papers/${encodeURIComponent(state.currentPaperId)}/ppt/export-pptx`, "_blank");
    });
    $("#btnPptReconfig").addEventListener("click", () => {
      studio.pptWizardOpen = true;
      renderPptTab();
    });
    $("#btnPptAddSlide").addEventListener("click", async () => {
      slides.splice(studio.activeSlideIdx + 1, 0, {
        id: `slide-${Date.now().toString(36)}`,
        layout: "two_column",
        tag: "CUSTOM · 新增页面",
        title: "补充讨论 / 课题结合点",
        subtitle: "在右侧编辑器或 PPT-Master SVG 编辑器自由修改内容",
        bullets: ["要点一：本文方法如何迁移到我们的实验场景", "要点二：需要进一步验证的关键参数"],
        callout: "",
        figure_id: null,
        metrics: [],
        speaker_notes: "",
      });
      studio.activeSlideIdx += 1;
      await persistDeck(false);
    });
    $("#btnPptPresent").addEventListener("click", () => openPresentationMode(deck));

    $("#pptThumbsCol").addEventListener("click", async (e) => {
      const mv = e.target.closest("[data-move-slide]");
      if (mv) {
        e.stopPropagation();
        const [iStr, deltaStr] = mv.dataset.moveSlide.split(":");
        const i = Number(iStr);
        const j = i + Number(deltaStr);
        if (j >= 0 && j < slides.length) {
          [slides[i], slides[j]] = [slides[j], slides[i]];
          studio.activeSlideIdx = j;
          await persistDeck(false);
        }
        return;
      }
      const del = e.target.closest("[data-del-slide]");
      if (del) {
        e.stopPropagation();
        const i = Number(del.dataset.delSlide);
        slides.splice(i, 1);
        studio.activeSlideIdx = Math.max(0, Math.min(studio.activeSlideIdx, slides.length - 1));
        await persistDeck(false);
        return;
      }
      const th = e.target.closest("[data-slide-idx]");
      if (th) {
        if (studio.dirtySlide) await persistDeck(true);
        studio.activeSlideIdx = Number(th.dataset.slideIdx);
        studio.dirtySlide = false;
        renderPptTab();
      }
    });
  }

  function openPresentationMode(deck) {
    studio.presentIdx = studio.activeSlideIdx;
    $("#presentOverlay").classList.remove("hidden");
    renderPresentFrame(deck);
  }

  function renderPresentFrame(deck) {
    const slides = deck.slides || [];
    const cur = slides[studio.presentIdx];
    if (!cur) return;
    $("#presentCounter").textContent = `${studio.presentIdx + 1} / ${slides.length} · ${deck.title || ""}`;
    $("#presentStage").innerHTML = renderRealSvgOrFallback(cur, studio.presentIdx, slides.length, deck.style_id, true);
    $("#presentNotesBar").textContent = cur.speaker_notes || "（本页暂无演讲备注）";
    requestAnimationFrame(scaleSlideFrames);
  }

  /* ==================== EVENT BINDINGS ==================== */
  function bindStudioEvents() {
    $("#btnToggleSidebar")?.addEventListener("click", () => {
      $("#workspaceShell").classList.toggle("sidebar-collapsed");
      setTimeout(scaleSlideFrames, 240);
    });
    window.addEventListener("resize", () => requestAnimationFrame(scaleSlideFrames));

    $("#btnNewTopic")?.addEventListener("click", () => {
      $("#newTopicForm").classList.toggle("hidden");
      $("#newTopicName").focus();
    });
    $("#btnCancelNewTopic")?.addEventListener("click", () => $("#newTopicForm").classList.add("hidden"));

    $("#newTopicColors")?.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-color]");
      if (!btn) return;
      studio.newTopicColor = btn.dataset.color;
      $$("#newTopicColors .cdot").forEach((b) => b.classList.toggle("active", b === btn));
    });

    $("#btnSaveNewTopic")?.addEventListener("click", async () => {
      const name = $("#newTopicName").value.trim();
      if (!name) return;
      const desc = $("#newTopicDesc").value.trim();
      const { topic } = await apiJson("/api/topics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, description: desc, color: studio.newTopicColor }),
      });
      $("#newTopicName").value = "";
      $("#newTopicDesc").value = "";
      $("#newTopicForm").classList.add("hidden");
      studio.activeTopicId = topic.id;
      await loadTopics();
    });

    $("#topicList")?.addEventListener("click", async (e) => {
      const del = e.target.closest("[data-delete-topic]");
      if (del) {
        e.stopPropagation();
        if (!confirm("确定删除该课题？（不会删除已解析的论文文件）")) return;
        const tid = del.dataset.deleteTopic;
        await apiJson(`/api/topics/${encodeURIComponent(tid)}`, { method: "DELETE" });
        if (studio.activeTopicId === tid) studio.activeTopicId = "all";
        await loadTopics();
        return;
      }
      const item = e.target.closest("[data-select-topic]");
      if (item) {
        studio.activeTopicId = item.dataset.selectTopic;
        studio.editingPaperTopicsId = null;
        renderTopicsSidebar();
      }
    });

    // Drag-and-drop paper cards onto topic items
    const topicListEl = $("#topicList");
    const paperListEl = $("#sidebarPaperList");

    paperListEl?.addEventListener("dragstart", (e) => {
      // Do not start dragging if user is interacting inside the category popover
      if (e.target.closest(".sb-topic-popover")) {
        e.preventDefault();
        return;
      }
      const card = e.target.closest(".sb-paper-card[data-paper-id]");
      if (!card) return;
      const pid = card.dataset.paperId;
      studio.draggingPaperId = pid;
      card.classList.add("dragging");
      topicListEl?.classList.add("drag-active");
      if (e.dataTransfer) {
        e.dataTransfer.effectAllowed = "copyMove";
        e.dataTransfer.setData("text/plain", pid);
        e.dataTransfer.setData("application/x-paperlens-paper", pid);
      }
    });

    paperListEl?.addEventListener("dragend", () => {
      studio.draggingPaperId = null;
      $$("#sidebarPaperList .sb-paper-card.dragging").forEach((el) => el.classList.remove("dragging"));
      topicListEl?.classList.remove("drag-active");
      $$("#topicList .topic-item.drag-over").forEach((el) => el.classList.remove("drag-over"));
    });

    topicListEl?.addEventListener("dragover", (e) => {
      const target = e.target.closest("[data-drop-topic]");
      if (!target) return;
      e.preventDefault();
      if (e.dataTransfer) {
        e.dataTransfer.dropEffect = e.altKey ? "copy" : "move";
      }
      if (!target.classList.contains("drag-over")) {
        $$("#topicList .topic-item.drag-over").forEach((el) => el.classList.remove("drag-over"));
        target.classList.add("drag-over");
      }
    });

    topicListEl?.addEventListener("dragleave", (e) => {
      const target = e.target.closest("[data-drop-topic]");
      if (!target) return;
      if (!target.contains(e.relatedTarget)) {
        target.classList.remove("drag-over");
      }
    });

    topicListEl?.addEventListener("drop", async (e) => {
      const target = e.target.closest("[data-drop-topic]");
      topicListEl?.classList.remove("drag-active");
      $$("#topicList .topic-item.drag-over").forEach((el) => el.classList.remove("drag-over"));
      if (!target) return;
      e.preventDefault();
      const pid =
        studio.draggingPaperId ||
        e.dataTransfer?.getData("application/x-paperlens-paper") ||
        e.dataTransfer?.getData("text/plain");
      studio.draggingPaperId = null;
      if (!pid) return;

      const targetTopicId = target.dataset.dropTopic;
      const sourceTopicId = studio.activeTopicId;
      const copyMode = Boolean(e.altKey);

      try {
        const { topics } = await apiJson("/api/topics/move-paper", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            paper_id: pid,
            target_topic_id: targetTopicId,
            source_topic_id: sourceTopicId,
            copy: copyMode,
          }),
        });
        studio.topics = topics || [];
        renderTopicsSidebar();
        populateTopicSelects();
        onTopicsChanged?.();

        const pObj = (state.papers || []).find((p) => p.paper_id === pid);
        const pName = (pObj?.title_zh || pObj?.title || pid).slice(0, 14);
        if (targetTopicId === "uncategorized") {
          showSidebarToast(`✓ 已将「${pName}…」移出所有课题`);
        } else {
          const tObj = studio.topics.find((t) => t.id === targetTopicId);
          showSidebarToast(`✓ 已移入课题「${tObj?.name || targetTopicId}」`);
        }
      } catch (err) {
        showSidebarToast(`移动失败：${err.message}`);
      }
    });

    paperListEl?.addEventListener("click", async (e) => {
      // Toggle inline category picker popover
      const toggleCat = e.target.closest("[data-toggle-paper-cat]");
      if (toggleCat) {
        e.stopPropagation();
        const pid = toggleCat.dataset.togglePaperCat;
        studio.editingPaperTopicsId = studio.editingPaperTopicsId === pid ? null : pid;
        renderTopicsSidebar();
        return;
      }
      if (e.target.closest("[data-close-cat-popover]")) {
        e.stopPropagation();
        studio.editingPaperTopicsId = null;
        renderTopicsSidebar();
        return;
      }
      const clearBtn = e.target.closest("[data-clear-paper-topics]");
      if (clearBtn) {
        e.stopPropagation();
        const pid = clearBtn.dataset.clearPaperTopics;
        const { topics } = await apiJson(`/api/papers/${encodeURIComponent(pid)}/topics`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic_ids: [] }),
        });
        studio.topics = topics || [];
        studio.editingPaperTopicsId = null;
        renderTopicsSidebar();
        populateTopicSelects();
        onTopicsChanged?.();
        showSidebarToast("✓ 已移至未分类文献");
        return;
      }
      // Do not trigger paper open when clicking inside popover
      if (e.target.closest(".sb-topic-popover")) {
        e.stopPropagation();
        return;
      }
      const rem = e.target.closest("[data-remove-paper-topic]");
      if (rem) {
        e.stopPropagation();
        const [tid, pid] = rem.dataset.removePaperTopic.split("::");
        await apiJson(`/api/topics/${encodeURIComponent(tid)}/papers/${encodeURIComponent(pid)}`, {
          method: "DELETE",
        });
        await loadTopics();
        showSidebarToast("✓ 已移出当前课题");
        return;
      }
      const card = e.target.closest("[data-open-paper]");
      if (card) {
        await loadPaper(card.dataset.openPaper);
      }
    });

    paperListEl?.addEventListener("change", async (e) => {
      const cb = e.target.closest("[data-cat-check]");
      if (!cb) return;
      e.stopPropagation();
      const [pid, tid] = cb.dataset.catCheck.split("::");
      const currentIds = new Set(getPaperTopics(pid).map((t) => t.id));
      if (cb.checked) currentIds.add(tid);
      else currentIds.delete(tid);

      try {
        const { topics } = await apiJson(`/api/papers/${encodeURIComponent(pid)}/topics`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic_ids: Array.from(currentIds) }),
        });
        studio.topics = topics || [];
        renderTopicsSidebar();
        populateTopicSelects();
        onTopicsChanged?.();
        const tObj = studio.topics.find((t) => t.id === tid);
        showSidebarToast(cb.checked ? `✓ 已加入「${tObj?.name || tid}」` : `✓ 已移出「${tObj?.name || tid}」`);
      } catch (err) {
        showSidebarToast(`更新分类失败：${err.message}`);
      }
    });

    $("#btnAssignCurrentPaper")?.addEventListener("click", async () => {
      if (!state.currentPaperId || studio.activeTopicId === "all" || studio.activeTopicId === "uncategorized") return;
      await apiJson(`/api/topics/${encodeURIComponent(studio.activeTopicId)}/papers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ paper_id: state.currentPaperId }),
      });
      await loadTopics();
    });

    // Zotero modal triggers
    $("#btnOpenZotero")?.addEventListener("click", openZoteroModal);
    $("#btnZoteroTop")?.addEventListener("click", openZoteroModal);

    $("#zoteroColChips")?.addEventListener("click", (e) => {
      const chip = e.target.closest("[data-zcol]");
      if (!chip) return;
      studio.zoteroColFilter = chip.dataset.zcol;
      renderZoteroCollections();
      renderZoteroItems();
    });

    $("#zoteroSearch")?.addEventListener("input", (e) => {
      studio.zoteroQuery = e.target.value;
      renderZoteroItems();
    });

    $("#zoteroHideTranslated")?.addEventListener("change", (e) => {
      studio.zoteroHideTranslated = e.target.checked;
      renderZoteroItems();
    });

    $("#zoteroItemList")?.addEventListener("change", (e) => {
      const cb = e.target.closest("[data-zkey]");
      if (!cb) return;
      const k = cb.dataset.zkey;
      if (cb.checked) studio.zoteroSelectedKeys.add(k);
      else studio.zoteroSelectedKeys.delete(k);
      cb.closest(".z-item-row")?.classList.toggle("selected", cb.checked);
      updateZoteroCount();
    });

    $("#btnDoZoteroImport")?.addEventListener("click", runZoteroImport);

    $("#btnProbeZoteroMcp")?.addEventListener("click", async () => {
      const cmd = $("#zoteroMcpCmdInput").value.trim();
      $("#zoteroMcpResult").textContent = "正在连接 Zotero MCP…";
      try {
        if (cmd) {
          await apiJson("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ zotero_mcp_command: cmd }),
          });
        }
        const res = await apiJson("/api/zotero/mcp-probe", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ command: cmd }),
        });
        $("#zoteroMcpResult").textContent =
          (res.connected ? "" : "提示：") +
          res.message +
          (res.tools?.length ? `（工具：${res.tools.slice(0, 8).join(", ")}）` : "");
        refreshZoteroStatus();
      } catch (err) {
        $("#zoteroMcpResult").textContent = "探测失败：" + err.message;
      }
    });

    // Recompile button inside embedded official PPT-Master SVG Editor modal
    $("#btnRecompileAfterEdit")?.addEventListener("click", async (e) => {
      const btn = e.currentTarget;
      btn.disabled = true;
      btn.textContent = "质检与编译中…";
      try {
        const res = await apiJson(
          `/api/papers/${encodeURIComponent(state.currentPaperId)}/ppt/recompile`,
          { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }
        );
        state.bundle.ppt_master = res.ppt_master;
        studio.svgCacheBust = Date.now();
        studio.dirtySlide = false;
        $("#svgEditorModal").classList.add("hidden");
        renderPptTab();
      } catch (err) {
        alert("重新编译失败：" + err.message);
      } finally {
        btn.disabled = false;
        btn.textContent = "重新质检并编译 .pptx";
      }
    });

    // Presentation Mode controls
    $("#presentExit")?.addEventListener("click", () => $("#presentOverlay").classList.add("hidden"));
    $("#presentToggleNotes")?.addEventListener("click", () => $("#presentNotesBar").classList.toggle("hidden"));
    $("#presentPrev")?.addEventListener("click", () => {
      if (!state.bundle?.deck) return;
      studio.presentIdx = Math.max(0, studio.presentIdx - 1);
      renderPresentFrame(state.bundle.deck);
    });
    $("#presentNext")?.addEventListener("click", () => {
      if (!state.bundle?.deck) return;
      const max = (state.bundle.deck.slides || []).length - 1;
      studio.presentIdx = Math.min(max, studio.presentIdx + 1);
      renderPresentFrame(state.bundle.deck);
    });
    document.addEventListener("keydown", (e) => {
      if ($("#presentOverlay").classList.contains("hidden") || !state.bundle?.deck) return;
      if (e.key === "Escape") $("#presentOverlay").classList.add("hidden");
      if (e.key === "ArrowRight" || e.key === " ") {
        studio.presentIdx = Math.min(state.bundle.deck.slides.length - 1, studio.presentIdx + 1);
        renderPresentFrame(state.bundle.deck);
      }
      if (e.key === "ArrowLeft") {
        studio.presentIdx = Math.max(0, studio.presentIdx - 1);
        renderPresentFrame(state.bundle.deck);
      }
    });
  }

  return {
    initStudio: async () => {
      bindStudioEvents();
      await Promise.all([loadTopics(), refreshZoteroStatus()]);
    },
    onPaperLoaded: () => {
      studio.pptWizardOpen = false;
      studio.activeSlideIdx = 0;
      renderTopicsSidebar();
      if (state.activeTab === "ppt") renderPptTab();
    },
    onPapersChanged: async () => {
      await loadTopics();
    },
    renderPptTab,
    getActiveTopicId: () => studio.activeTopicId,
    getTopics: () => studio.topics,
  };
}
