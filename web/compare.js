/**
 * compare.js — Cross-Paper Comparison & Relationship Synthesis Workspace
 */

const PAPER_PALETTE = ["#2563eb", "#0f766e", "#d97706", "#7c3aed", "#be123c", "#0284c7"];

const REL_TYPE_COLOR = {
  方法互补: "#059669",
  技术演进: "#2563eb",
  范式分歧: "#d97706",
  靶标重叠: "#0f766e",
  证据互印: "#7c3aed",
};

export function createCompareController(ctx) {
  const { state, $, $$, esc, apiJson, loadPaper, switchTab, getTopics } = ctx;

  const cmp = {
    topicFilter: "all",
    selectedIds: new Set(),
    focusQuestion: "",
    history: [],
    currentReport: null, // { id?, mode, title, deterministic, synthesis }
    matrixView: "ai", // "ai" | "raw6"
    activeRelIdx: 0,
    initializedSelection: false,
  };

  function getCandidatePapers() {
    const all = state.papers || [];
    const topics = getTopics ? getTopics() : [];
    if (cmp.topicFilter === "all") return all;
    if (cmp.topicFilter === "uncategorized") {
      const assigned = new Set(topics.flatMap((t) => t.paper_ids || []));
      return all.filter((p) => !assigned.has(p.paper_id));
    }
    const topic = topics.find((t) => t.id === cmp.topicFilter);
    const idSet = new Set(topic?.paper_ids || []);
    return all.filter((p) => idSet.has(p.paper_id));
  }

  function ensureDefaultSelection() {
    if (cmp.initializedSelection && cmp.selectedIds.size > 0) return;
    const cands = getCandidatePapers();
    if (cands.length >= 2) {
      cmp.selectedIds = new Set(cands.slice(0, 4).map((p) => p.paper_id));
      cmp.initializedSelection = true;
    } else if ((state.papers || []).length >= 2) {
      cmp.selectedIds = new Set(state.papers.slice(0, 4).map((p) => p.paper_id));
      cmp.initializedSelection = true;
    }
  }

  async function refreshHistory() {
    try {
      const { comparisons } = await apiJson("/api/comparisons");
      cmp.history = comparisons || [];
    } catch {
      cmp.history = [];
    }
  }

  async function openCompareTab() {
    await refreshHistory();
    ensureDefaultSelection();
    if (!cmp.currentReport && cmp.history.length > 0) {
      try {
        cmp.currentReport = await apiJson(`/api/comparisons/${encodeURIComponent(cmp.history[0].id)}`);
        cmp.matrixView = cmp.currentReport.synthesis ? "ai" : "raw6";
      } catch {
        cmp.currentReport = null;
      }
    }
    renderCompareTab();
  }

  function getTopicLabel() {
    if (cmp.topicFilter === "all") return "全部文献";
    if (cmp.topicFilter === "uncategorized") return "未分类文献";
    const t = (getTopics ? getTopics() : []).find((x) => x.id === cmp.topicFilter);
    return t ? t.name : "自定义研究方向";
  }

  function renderRelationGraphSvg(papers, relations) {
    const n = papers.length;
    if (n < 2) return "";
    const W = 760;
    const H = n === 2 ? 250 : 340;
    const cx = W / 2;
    const cy = H / 2;
    const rx = n === 2 ? 230 : 250;
    const ry = n === 2 ? 40 : 115;

    const coords = {};
    papers.forEach((p, i) => {
      const angle = n === 2 ? (i === 0 ? Math.PI : 0) : -Math.PI / 2 + (i * 2 * Math.PI) / n;
      coords[p.paper_id] = {
        x: cx + rx * Math.cos(angle),
        y: cy + ry * Math.sin(angle),
        color: PAPER_PALETTE[i % PAPER_PALETTE.length],
        paper: p,
      };
    });

    const edgesSvg = (relations || [])
      .map((rel, idx) => {
        const a = coords[rel.from_paper];
        const b = coords[rel.to_paper];
        if (!a || !b) return "";
        const col = REL_TYPE_COLOR[rel.relation_type] || "#2563eb";
        const isAct = idx === cmp.activeRelIdx;
        // Slightly curved quadratic edge offset from center for readability
        const mx = (a.x + b.x) / 2;
        const my = (a.y + b.y) / 2;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const len = Math.hypot(dx, dy) || 1;
        const offset = n === 2 ? (idx % 2 === 0 ? -48 : 48) : 22;
        const qx = mx - (dy / len) * offset;
        const qy = my + (dx / len) * offset;
        const lx = 0.25 * a.x + 0.5 * qx + 0.25 * b.x;
        const ly = 0.25 * a.y + 0.5 * qy + 0.25 * b.y;
        const rawLabel = rel.label || "";
        const shortEdgeText = rawLabel.length > 9 ? rawLabel.slice(0, 8) + "…" : rawLabel;
        const label = `${rel.relation_type || "关联"} · ${shortEdgeText}`;
        const pillW = Math.min(226, Math.max(118, label.length * 11.8 + 20));

        return `
          <g class="cmp-edge-group ${isAct ? "active" : ""}" data-select-rel="${idx}" style="cursor:pointer">
            <path d="M ${a.x.toFixed(1)} ${a.y.toFixed(1)} Q ${qx.toFixed(1)} ${qy.toFixed(1)} ${b.x.toFixed(1)} ${b.y.toFixed(1)}"
              fill="none" stroke="${col}" stroke-width="${isAct ? 4 : 2.3}" stroke-opacity="${isAct ? 0.95 : 0.6}"
              stroke-dasharray="${rel.relation_type === "范式分歧" ? "7 4" : ""}" />
            <rect x="${(lx - pillW / 2).toFixed(1)}" y="${(ly - 13).toFixed(1)}" width="${pillW}" height="26" rx="13"
              fill="${isAct ? col : "#ffffff"}" stroke="${col}" stroke-width="${isAct ? 2 : 1.5}" />
            <text x="${lx.toFixed(1)}" y="${(ly + 4).toFixed(1)}" text-anchor="middle" font-size="11" font-weight="700"
              fill="${isAct ? "#ffffff" : col}">${esc(label)}</text>
          </g>
        `;
      })
      .join("");

    const nodesSvg = papers
      .map((p, i) => {
        const c = coords[p.paper_id];
        const fullT = p.title_zh || p.title || "";
        const line1 = fullT.slice(0, 12);
        const rest = fullT.slice(12);
        const line2 = rest.length > 13 ? rest.slice(0, 12) + "…" : rest;
        const nw = 224;
        const nh = 68;
        return `
          <g class="cmp-node-group" data-jump-paper="${esc(p.paper_id)}" style="cursor:pointer">
            <rect x="${(c.x - nw / 2).toFixed(1)}" y="${(c.y - nh / 2).toFixed(1)}" width="${nw}" height="${nh}" rx="12"
              fill="#ffffff" stroke="${c.color}" stroke-width="2.5" />
            <rect x="${(c.x - nw / 2).toFixed(1)}" y="${(c.y - nh / 2).toFixed(1)}" width="38" height="${nh}" rx="10" fill="${c.color}" />
            <text x="${(c.x - nw / 2 + 19).toFixed(1)}" y="${(c.y + 5).toFixed(1)}" text-anchor="middle" font-size="14" font-weight="800" fill="#ffffff">${esc(p.short_label)}</text>
            <text x="${(c.x - nw / 2 + 48).toFixed(1)}" y="${(c.y - 6).toFixed(1)}" font-size="12" font-weight="700" fill="#181c24">${esc(line1)}</text>
            <text x="${(c.x - nw / 2 + 48).toFixed(1)}" y="${(c.y + 13).toFixed(1)}" font-size="11" fill="#5b6374">${esc(line2 || p.paper_id.slice(0, 18))}</text>
          </g>
        `;
      })
      .join("");

    return `
      <svg class="cmp-graph-svg" viewBox="0 0 ${W} ${H}" width="100%">
        ${edgesSvg}
        ${nodesSvg}
      </svg>
    `;
  }

  function renderReportHtml(report) {
    if (!report || !report.deterministic) {
      return `
        <div class="dim-card" style="text-align:center;padding:38px 24px">
          <div style="font-size:36px;margin-bottom:8px">⚖️</div>
          <h3 style="margin:0 0 8px">勾选上方同一方向下的 2 篇及以上论文开始对比</h3>
          <p style="margin:0;color:var(--text-muted);font-size:14px">支持「⚡ 0 秒瞬时并排对比（六大维度 + 共同引文/工具图谱）」与「✨ Gemini 4 Neon 跨文深度对比与融合创新挖掘」。</p>
        </div>
      `;
    }

    const det = report.deterministic;
    const syn = report.synthesis;
    const papers = det.papers || [];
    const pmap = Object.fromEntries(papers.map((p, i) => [p.paper_id, { ...p, color: PAPER_PALETTE[i % PAPER_PALETTE.length] }]));

    // 1. Synthesis Hero + Beginner Analogy
    const heroHtml = syn
      ? `
        <div class="dim-card" style="margin-bottom:18px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;margin-bottom:12px">
            <div>
              <span class="meta-pill accent">✨ Gemini 跨文深度对比与关联挖掘</span>
              ${report.topic_name ? `<span class="meta-pill" style="margin-left:6px">📂 ${esc(report.topic_name)}</span>` : ""}
              <h2 style="margin:8px 0 0;font-size:21px">${esc(report.title || syn.title || "多文对比分析")}</h2>
            </div>
            ${
              report.id
                ? `<div style="display:flex;gap:8px">
                    <button id="btnExportCmpMd" class="btn btn-secondary btn-sm">📥 导出对比综述 MD</button>
                  </div>`
                : ""
            }
          </div>
          <div class="hero-tldr"><strong>📌 全景定位：</strong>${esc(syn.synthesis_headline || "")}</div>
          ${
            syn.beginner_analogy
              ? `<div class="hero-beginner-hook beginner-only"><strong>🎓 零基础大白话流派对决：</strong>${esc(syn.beginner_analogy)}</div>`
              : ""
          }
          ${
            (syn.paper_roles || []).length
              ? `<div class="cmp-roles-grid">
                  ${syn.paper_roles
                    .map((pr) => {
                      const pm = pmap[pr.paper_id] || { short_label: "P?", title_zh: pr.paper_id, color: "#2563eb" };
                      return `
                        <div class="cmp-role-card" style="border-top:4px solid ${pm.color}">
                          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px">
                            <span class="meta-pill" style="background:${pm.color};color:#fff">${esc(pm.short_label)} · ${esc(pr.archetype || "")}</span>
                            <button class="link-btn" data-jump-paper="${esc(pr.paper_id)}">精读原文 ↗</button>
                          </div>
                          <div style="font-weight:700;font-size:13.5px;margin-bottom:8px;line-height:1.35">${esc(pm.title_zh)}</div>
                          <div style="font-size:12.5px;margin-bottom:5px"><strong style="color:var(--teal)">✓ 核心优势：</strong>${esc(pr.core_edge || "")}</div>
                          <div style="font-size:12.5px;color:var(--text-muted)"><strong style="color:var(--rose)">△ 主要短板：</strong>${esc(pr.main_gap || "")}</div>
                        </div>
                      `;
                    })
                    .join("")}
                </div>`
              : ""
          }
        </div>
      `
      : `
        <div class="dim-card" style="margin-bottom:18px;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">
          <div>
            <span class="meta-pill accent">⚡ 瞬时结构化对比模式</span>
            <h3 style="margin:6px 0 4px">已并排对齐 ${papers.length} 篇论文的六大维度与实证共享线索</h3>
            <p style="margin:0;font-size:13px;color:var(--text-muted)">点击上方「✨ 用 Gemini 4 Neon 深度对比与关联挖掘」可进一步生成流派关联图谱、互补/分歧剖析与新课题 Idea。</p>
          </div>
        </div>
      `;

    // 2. Interactive SVG Relation Graph (when synthesis has relations)
    const rels = syn?.relations || [];
    if (cmp.activeRelIdx >= rels.length) cmp.activeRelIdx = 0;
    const activeRel = rels[cmp.activeRelIdx];
    const relGraphHtml = rels.length
      ? `
        <div class="dim-card" style="margin-bottom:18px">
          <div class="dim-header">
            <div class="dim-title-group">
              <span class="dim-num">GRAPH</span>
              <h3>🕸️ 论文间深层关联网络图（点击连线查看解析 · 点击论文节点跳转精读）</h3>
            </div>
          </div>
          <div class="cmp-graph-layout">
            <div class="cmp-graph-canvas">
              ${renderRelationGraphSvg(papers, rels)}
            </div>
            <div class="cmp-rel-detail-pane">
              <div style="font-size:12px;font-weight:700;color:var(--text-muted);margin-bottom:8px">全部关联边（${rels.length} 条）</div>
              <div style="display:flex;flex-direction:column;gap:8px">
                ${rels
                  .map((r, i) => {
                    const a = pmap[r.from_paper] || { short_label: r.from_paper, color: "#2563eb" };
                    const b = pmap[r.to_paper] || { short_label: r.to_paper, color: "#0f766e" };
                    const col = REL_TYPE_COLOR[r.relation_type] || "#2563eb";
                    const isAct = i === cmp.activeRelIdx;
                    return `
                      <div class="cmp-rel-item ${isAct ? "active" : ""}" data-select-rel="${i}" style="border-left:4px solid ${col}">
                        <div style="display:flex;align-items:center;justify-content:space-between;gap:6px;margin-bottom:4px;flex-wrap:wrap">
                          <strong style="font-size:13px">${esc(a.short_label)} ↔ ${esc(b.short_label)} · ${esc(r.label || "")}</strong>
                          <span class="meta-pill" style="background:${col}1f;color:${col}">${esc(r.relation_type || "关联")}</span>
                        </div>
                        <div style="font-size:12.5px;color:var(--text);line-height:1.55">${esc(r.explanation || "")}</div>
                      </div>
                    `;
                  })
                  .join("")}
              </div>
            </div>
          </div>
        </div>
      `
      : "";

    // 3. Multi-dimensional Comparison Matrix (AI distilled vs Raw 6-dim side-by-side)
    const showAiMatrix = cmp.matrixView === "ai" && syn?.comparison_matrix?.length;
    const matrixTableHtml = showAiMatrix
      ? `
        <table class="cmp-table">
          <thead>
            <tr>
              <th style="width:150px">对比维度</th>
              ${papers
                .map(
                  (p, i) => `
                <th>
                  <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
                    <span class="meta-pill" style="background:${PAPER_PALETTE[i % PAPER_PALETTE.length]};color:#fff">${esc(p.short_label)}</span>
                    <button class="link-btn" data-jump-paper="${esc(p.paper_id)}">打开 ↗</button>
                  </div>
                  <div style="font-size:12.5px;font-weight:700;line-height:1.35">${esc(p.title_zh)}</div>
                </th>
              `
                )
                .join("")}
              <th style="width:210px">💡 横向洞察</th>
            </tr>
          </thead>
          <tbody>
            ${syn.comparison_matrix
              .map(
                (row) => `
              <tr>
                <td class="cmp-dim-cell"><strong>${esc(row.dimension || "")}</strong></td>
                ${papers
                  .map((p) => `<td>${esc((row.cells || {})[p.paper_id] || "—")}</td>`)
                  .join("")}
                <td class="cmp-insight-cell">${esc(row.insight || "")}</td>
              </tr>
            `
              )
              .join("")}
          </tbody>
        </table>
      `
      : `
        <table class="cmp-table">
          <thead>
            <tr>
              <th style="width:140px">六大核心维度</th>
              ${papers
                .map(
                  (p, i) => `
                <th>
                  <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
                    <span class="meta-pill" style="background:${PAPER_PALETTE[i % PAPER_PALETTE.length]};color:#fff">${esc(p.short_label)}</span>
                    <button class="link-btn" data-jump-paper="${esc(p.paper_id)}">打开 ↗</button>
                  </div>
                  <div style="font-size:12.5px;font-weight:700;line-height:1.35">${esc(p.title_zh)}</div>
                </th>
              `
                )
                .join("")}
            </tr>
          </thead>
          <tbody>
            ${(det.raw_six_dim_matrix || [])
              .map(
                (row) => `
              <tr>
                <td class="cmp-dim-cell"><strong>${esc(row.label)}</strong></td>
                ${papers
                  .map((p) => {
                    const cell = (row.cells || {})[p.paper_id] || {};
                    return `<td>
                      <div>${esc(cell.summary || "")}</div>
                      ${
                        cell.analogy
                          ? `<div class="beginner-only" style="margin-top:6px;padding:6px 8px;border-radius:7px;background:var(--amber-bg);font-size:12px"><strong>💡 类比：</strong>${esc(cell.analogy)}</div>`
                          : ""
                      }
                    </td>`;
                  })
                  .join("")}
              </tr>
            `
              )
              .join("")}
          </tbody>
        </table>
      `;

    const matrixCardHtml = `
      <div class="dim-card" style="margin-bottom:18px">
        <div class="dim-header">
          <div class="dim-title-group">
            <span class="dim-num">MATRIX</span>
            <h3>📊 多维度横向对比矩阵</h3>
          </div>
          <div class="display-mode-group">
            ${syn?.comparison_matrix?.length ? `<button class="mode-btn ${showAiMatrix ? "active" : ""}" data-matrix-view="ai">✨ AI 精炼维表</button>` : ""}
            <button class="mode-btn ${!showAiMatrix ? "active" : ""}" data-matrix-view="raw6">📋 六大维度并排</button>
          </div>
        </div>
        <div class="cmp-table-wrap">${matrixTableHtml}</div>
      </div>
    `;

    // 4. Complementarities vs Tensions + Research Ideas
    const compAndIdeasHtml = syn
      ? `
        <div class="cmp-two-col" style="margin-bottom:18px">
          <div class="dim-card" style="border-top:4px solid var(--teal)">
            <h3 style="margin:0 0 10px;color:var(--teal)">🔀 互补融合机会（如何强强联合？）</h3>
            <ul class="dim-bullets" style="margin:0">
              ${(syn.complementarities || []).map((c) => `<li>${esc(c)}</li>`).join("")}
            </ul>
          </div>
          <div class="dim-card" style="border-top:4px solid var(--amber-border)">
            <h3 style="margin:0 0 10px;color:var(--amber)">⚡ 核心分歧与范式张力</h3>
            <ul class="dim-bullets" style="margin:0">
              ${(syn.contradictions_or_tensions || []).map((c) => `<li>${esc(c)}</li>`).join("")}
            </ul>
          </div>
        </div>

        ${
          (syn.research_ideas || []).length
            ? `<div class="dim-card" style="margin-bottom:18px;border:1.5px solid color-mix(in srgb, var(--primary) 35%, var(--border))">
                <div class="dim-header">
                  <div class="dim-title-group">
                    <span class="dim-num">IDEAS</span>
                    <h3>🚀 基于对比空白区的下一步课题创新切入点</h3>
                  </div>
                </div>
                <div class="cmp-ideas-grid">
                  ${syn.research_ideas
                    .map(
                      (idea, idx) => `
                    <div class="cmp-idea-card">
                      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
                        <span class="wf-num" style="margin:0">${idx + 1}</span>
                        <strong style="font-size:14.5px">${esc(idea.title || "")}</strong>
                      </div>
                      <p style="margin:0 0 8px;font-size:13px;line-height:1.55">${esc(idea.rationale || "")}</p>
                      ${
                        idea.how_to_start
                          ? `<div style="padding:8px 10px;border-radius:8px;background:var(--teal-soft);font-size:12.5px"><strong style="color:var(--teal)">🧪 第一步验证路径：</strong>${esc(idea.how_to_start)}</div>`
                          : ""
                      }
                    </div>
                  `
                    )
                    .join("")}
                </div>
              </div>`
            : ""
        }
      `
      : "";

    // 5. Evidence-Backed Shared Links (Shared Refs, Direct Citations, Shared Concepts & Tools)
    const evidenceHtml = `
      <div class="dim-card">
        <div class="dim-header">
          <div class="dim-title-group">
            <span class="dim-num">LINKS</span>
            <h3>🔎 客观实证关联线索（共同引文 · 直接互引 · 共享术语/工具）</h3>
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <span class="meta-pill accent">共同引文 ${det.shared_references?.length || 0} 篇</span>
            <span class="meta-pill">直接互引 ${det.direct_citations?.length || 0} 条</span>
            <span class="meta-pill">共享技术/概念 ${det.shared_concepts?.length || 0} 个</span>
          </div>
        </div>

        ${
          (det.direct_citations || []).length
            ? `<div style="margin-bottom:14px">
                <div style="font-size:13px;font-weight:700;margin-bottom:6px">➡️ 直接引用传承关系：</div>
                ${det.direct_citations
                  .map((dc) => {
                    const a = pmap[dc.from_paper]?.short_label || dc.from_paper;
                    const b = pmap[dc.to_paper]?.short_label || dc.to_paper;
                    return `<div class="analysis-block role-block" style="margin-bottom:6px"><strong>${esc(a)} 直接引用了 ${esc(b)}</strong>（[Ref ${dc.ref_number}]）：${esc(dc.raw)}</div>`;
                  })
                  .join("")}
              </div>`
            : ""
        }

        ${
          (det.shared_concepts || []).length
            ? `<div style="margin-bottom:14px">
                <div style="font-size:13px;font-weight:700;margin-bottom:8px">🧩 跨论文共享术语、模型与数据库：</div>
                <div style="display:flex;flex-wrap:wrap;gap:7px">
                  ${det.shared_concepts
                    .map(
                      (c) => `
                    <span class="term-pill" style="cursor:default" title="${esc(c.desc || "")}">
                      ${esc(c.name)} (${c.papers.map((pid) => pmap[pid]?.short_label || pid).join("+")})
                    </span>
                  `
                    )
                    .join("")}
                </div>
              </div>`
            : ""
        }

        <div>
          <div style="font-size:13px;font-weight:700;margin-bottom:8px">📚 共同引用的基石参考文献（Bibliographic Coupling）：</div>
          ${
            (det.shared_references || []).length
              ? `<div class="ref-index-list">
                  ${det.shared_references
                    .map(
                      (r) => `
                    <div class="ref-row">
                      <div class="ref-row-main">
                        <strong>${esc(r.title)}</strong> ${r.year ? `(${r.year})` : ""}
                        <div style="font-size:12px;color:var(--text-muted);margin-top:2px">${esc(r.authors || "")}</div>
                      </div>
                      <div style="display:flex;gap:5px;flex-wrap:wrap;flex-shrink:0">
                        ${Object.entries(r.cited_by || {})
                          .map(([pid, rnum]) => `<span class="meta-pill accent">${esc(pmap[pid]?.short_label || pid)} [Ref ${rnum}]</span>`)
                          .join("")}
                      </div>
                    </div>
                  `
                    )
                    .join("")}
                </div>`
              : `<p style="font-size:13px;color:var(--text-muted);margin:0">所选论文的参考文献列表中暂无完全重合的条目（可能分别来自不同细分年份或子领域，可参考上方 AI 挖掘的方法与概念深层关联）。</p>`
          }
        </div>
      </div>
    `;

    return heroHtml + relGraphHtml + matrixCardHtml + compAndIdeasHtml + evidenceHtml;
  }

  function renderCompareTab() {
    const root = $("#tab-compare");
    if (!root) return;

    const topics = getTopics ? getTopics() : [];
    const cands = getCandidatePapers();
    const allCount = (state.papers || []).length;

    const topicChips = [
      `<button class="chip ${cmp.topicFilter === "all" ? "active" : ""}" data-cmp-topic="all">全部论文 (${allCount})</button>`,
      ...topics.map((t) => {
        const cnt = (t.paper_ids || []).filter((pid) => (state.papers || []).some((p) => p.paper_id === pid)).length;
        return `<button class="chip ${cmp.topicFilter === t.id ? "active" : ""}" data-cmp-topic="${esc(t.id)}">📂 ${esc(t.name)} (${cnt})</button>`;
      }),
    ].join("");

    const historyOptions = cmp.history.length
      ? [
          `<option value="">🕘 历史对比报告 (${cmp.history.length})</option>`,
          ...cmp.history.map(
            (h) =>
              `<option value="${esc(h.id)}" ${cmp.currentReport?.id === h.id ? "selected" : ""}>${esc(h.title)} (${h.paper_count}篇)</option>`
          ),
        ].join("")
      : `<option value="">暂无历史对比报告</option>`;

    root.innerHTML = `
      <div class="cmp-selector-card">
        <div class="cmp-selector-head">
          <div>
            <h2 style="margin:0 0 4px">⚖️ 同方向论文横向对比与关联分析</h2>
            <p style="margin:0;font-size:13px;color:var(--text-muted)">选择同一研究方向下的 2 篇及以上论文，一键剖析研究思路差异、挖掘隐藏关联与互补点，并生成下一步创新切入点。</p>
          </div>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
            <select id="cmpHistorySelect" class="paper-select" style="max-width:250px">${historyOptions}</select>
            ${
              cmp.currentReport?.id
                ? `<button id="btnDeleteCmp" class="btn btn-ghost btn-sm" title="删除当前保存的对比报告">🗑️ 删除报告</button>`
                : ""
            }
          </div>
        </div>

        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap">
          <div id="cmpTopicChips" class="filter-chips">${topicChips}</div>
          <div style="display:flex;gap:8px">
            <button id="btnCmpSelectAll" class="btn btn-ghost btn-xs">全选当前方向</button>
            <button id="btnCmpClearAll" class="btn btn-ghost btn-xs">清空勾选</button>
          </div>
        </div>

        <div id="cmpPaperGrid" class="cmp-paper-grid">
          ${
            cands.length
              ? cands
                  .map((p) => {
                    const checked = cmp.selectedIds.has(p.paper_id);
                    return `
                      <label class="cmp-paper-pick ${checked ? "selected" : ""}">
                        <input type="checkbox" data-cmp-pid="${esc(p.paper_id)}" ${checked ? "checked" : ""} />
                        <div style="min-width:0;flex:1">
                          <div style="font-weight:700;font-size:13px;line-height:1.35;margin-bottom:3px">${esc(p.title_zh || p.title)}</div>
                          <div style="font-size:11.5px;color:var(--text-muted)">
                            ${p.page_count}页 · ${p.figure_count}图 · ${p.reference_count}引文 ·
                            ${p.analysis_mode === "llm_deep" ? `<span style="color:var(--teal);font-weight:600">✓ 已深度剖析</span>` : `<span>快速切图态</span>`}
                          </div>
                        </div>
                      </label>
                    `;
                  })
                  .join("")
              : `<div style="font-size:13px;color:var(--text-muted);padding:10px">该课题方向下暂无足够论文，请先切换方向或从 Zotero 导入更多论文。</div>`
          }
        </div>

        <div class="cmp-action-bar">
          <input id="cmpFocusInput" type="text" class="search-input" style="flex:1;min-width:260px" value="${esc(cmp.focusQuestion)}" placeholder="可选：输入你最想对比的问题（例如：对比它们的特征表征、数据量需求和融合创新机会）" />
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
            <span style="font-size:12.5px;font-weight:700;color:var(--primary)">已选 ${cmp.selectedIds.size} 篇</span>
            <button id="btnCmpQuick" class="btn btn-secondary" ${cmp.selectedIds.size < 2 ? "disabled" : ""}>⚡ 瞬时并排对比</button>
            <button id="btnCmpDeep" class="btn btn-primary" ${cmp.selectedIds.size < 2 ? "disabled" : ""}>✨ 用 Gemini 4 Neon 深度对比与关联挖掘</button>
          </div>
        </div>

        <div id="cmpProgressBox" class="progress-box hidden">
          <div class="progress-head">
            <span id="cmpProgressMsg">准备分析...</span>
            <strong id="cmpProgressPct">5%</strong>
          </div>
          <div class="progress-track">
            <div id="cmpProgressBar" class="progress-fill" style="width: 5%"></div>
          </div>
        </div>
      </div>

      <div id="cmpResultRoot">${renderReportHtml(cmp.currentReport)}</div>
    `;

    // Bind selector & report interactions
    $("#cmpTopicChips")?.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-cmp-topic]");
      if (!btn) return;
      cmp.topicFilter = btn.dataset.cmpTopic;
      renderCompareTab();
    });

    $("#btnCmpSelectAll")?.addEventListener("click", () => {
      getCandidatePapers().forEach((p) => cmp.selectedIds.add(p.paper_id));
      renderCompareTab();
    });
    $("#btnCmpClearAll")?.addEventListener("click", () => {
      cmp.selectedIds.clear();
      renderCompareTab();
    });

    $("#cmpPaperGrid")?.addEventListener("change", (e) => {
      const cb = e.target.closest("[data-cmp-pid]");
      if (!cb) return;
      if (cb.checked) cmp.selectedIds.add(cb.dataset.cmpPid);
      else cmp.selectedIds.delete(cb.dataset.cmpPid);
      renderCompareTab();
    });

    $("#cmpFocusInput")?.addEventListener("input", (e) => {
      cmp.focusQuestion = e.target.value;
    });

    $("#cmpHistorySelect")?.addEventListener("change", async (e) => {
      const cid = e.target.value;
      if (!cid) return;
      cmp.currentReport = await apiJson(`/api/comparisons/${encodeURIComponent(cid)}`);
      cmp.matrixView = cmp.currentReport.synthesis ? "ai" : "raw6";
      cmp.activeRelIdx = 0;
      renderCompareTab();
    });

    $("#btnDeleteCmp")?.addEventListener("click", async () => {
      if (!cmp.currentReport?.id) return;
      if (!confirm("确定删除这份历史对比分析报告？")) return;
      await apiJson(`/api/comparisons/${encodeURIComponent(cmp.currentReport.id)}`, { method: "DELETE" });
      cmp.currentReport = null;
      await refreshHistory();
      renderCompareTab();
    });

    $("#btnCmpQuick")?.addEventListener("click", async () => {
      const pids = Array.from(cmp.selectedIds);
      if (pids.length < 2) return;
      const res = await apiJson("/api/comparisons/quick", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ paper_ids: pids }),
      });
      cmp.currentReport = res;
      cmp.matrixView = "raw6";
      renderCompareTab();
    });

    $("#btnCmpDeep")?.addEventListener("click", async (e) => {
      const pids = Array.from(cmp.selectedIds);
      if (pids.length < 2) return;
      const btn = e.currentTarget;
      btn.disabled = true;
      const pbox = $("#cmpProgressBox");
      pbox.classList.remove("hidden");
      $("#cmpProgressMsg").textContent = "⏳ 正在启动跨文深度对比（Gemini 4 Neon）...";
      $("#cmpProgressPct").textContent = "10%";
      $("#cmpProgressBar").style.width = "10%";

      try {
        const { job_id } = await apiJson("/api/comparisons/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            paper_ids: pids,
            topic_name: getTopicLabel(),
            focus_question: cmp.focusQuestion,
          }),
        });
        const timer = setInterval(async () => {
          try {
            const job = await apiJson(`/api/jobs/${job_id}`);
            $("#cmpProgressMsg").textContent = job.message || job.status;
            $("#cmpProgressPct").textContent = `${job.progress || 0}%`;
            $("#cmpProgressBar").style.width = `${job.progress || 0}%`;
            if (job.status === "done") {
              clearInterval(timer);
              await refreshHistory();
              cmp.currentReport = await apiJson(`/api/comparisons/${encodeURIComponent(job.comparison_id)}`);
              cmp.matrixView = "ai";
              cmp.activeRelIdx = 0;
              renderCompareTab();
            } else if (job.status === "error") {
              clearInterval(timer);
              btn.disabled = false;
            }
          } catch {
            clearInterval(timer);
            btn.disabled = false;
          }
        }, 1200);
      } catch (err) {
        $("#cmpProgressMsg").textContent = "❌ 启动失败：" + err.message;
        btn.disabled = false;
      }
    });

    // Result interactions (relation click, matrix toggle, paper jump, export MD)
    $("#cmpResultRoot")?.addEventListener("click", async (e) => {
      const relEl = e.target.closest("[data-select-rel]");
      if (relEl) {
        cmp.activeRelIdx = Number(relEl.dataset.selectRel);
        $("#cmpResultRoot").innerHTML = renderReportHtml(cmp.currentReport);
        return;
      }
      const mvBtn = e.target.closest("[data-matrix-view]");
      if (mvBtn) {
        cmp.matrixView = mvBtn.dataset.matrixView;
        $("#cmpResultRoot").innerHTML = renderReportHtml(cmp.currentReport);
        return;
      }
      const jp = e.target.closest("[data-jump-paper]");
      if (jp) {
        await loadPaper(jp.dataset.jumpPaper);
        switchTab("overview");
        return;
      }
      if (e.target.closest("#btnExportCmpMd") && cmp.currentReport?.id) {
        window.open(`/api/comparisons/${encodeURIComponent(cmp.currentReport.id)}/export-md`, "_blank");
      }
    });
  }

  return {
    openCompareTab,
    renderCompareTab,
  };
}
