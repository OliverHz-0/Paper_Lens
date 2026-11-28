/**
 * wetlab.js — Wet-Lab Experimental Protocol Handbook Extractor & Interactive SOP Viewer
 */

export function createWetlabController(ctx) {
  const { state, $, esc, apiJson, jumpToSlice, jumpToFigure } = ctx;

  const wl = {
    loadedPaperId: null,
    scan: null,
    protocol: null,
    focusNote: "",
    materialCatFilter: "all",
    activeProtoId: "all",
    extracting: false,
    progressPct: 0,
    progressMsg: "",
    errorMsg: "",
  };

  function getChecklistKey(paperId) {
    return `paperlens-wetlab-checks:${paperId}`;
  }

  function loadChecks(paperId) {
    try {
      return JSON.parse(localStorage.getItem(getChecklistKey(paperId)) || "{}");
    } catch {
      return {};
    }
  }

  function toggleCheck(paperId, key, checked) {
    const map = loadChecks(paperId);
    if (checked) map[key] = true;
    else delete map[key];
    try {
      localStorage.setItem(getChecklistKey(paperId), JSON.stringify(map));
    } catch {
      /* ignore quota */
    }
  }

  async function openWetlabTab(forceReload = false) {
    const pid = state.currentPaperId;
    if (!pid) {
      wl.loadedPaperId = null;
      wl.scan = null;
      wl.protocol = null;
      renderWetlabTab();
      return;
    }
    if (!forceReload && wl.loadedPaperId === pid && (wl.scan || wl.protocol)) {
      renderWetlabTab();
      return;
    }
    wl.loadedPaperId = pid;
    wl.errorMsg = "";
    wl.materialCatFilter = "all";
    wl.activeProtoId = "all";
    renderWetlabTab(true);
    try {
      const data = await apiJson(`/api/papers/${encodeURIComponent(pid)}/wetlab`);
      if (wl.loadedPaperId !== pid) return;
      wl.scan = data.scan || null;
      wl.protocol = data.protocol || null;
      if (wl.protocol?.focus_note && !wl.focusNote) {
        wl.focusNote = wl.protocol.focus_note;
      }
      renderWetlabTab();
    } catch (err) {
      wl.errorMsg = err.message || "加载湿实验扫描数据失败";
      renderWetlabTab();
    }
  }

  function onPaperLoaded() {
    wl.loadedPaperId = null;
    wl.scan = null;
    wl.protocol = null;
    wl.focusNote = "";
    wl.errorMsg = "";
    if (state.activeTab === "wetlab") {
      openWetlabTab(true);
    }
  }

  function renderSliceChip(sid) {
    return `<button type="button" class="wl-anchor-chip" data-wl-slice="${esc(sid)}" title="跳转查看原文段落 ${esc(sid)}">${esc(sid)} ↗</button>`;
  }

  function renderFigChip(fid) {
    return `<button type="button" class="wl-anchor-chip" data-wl-fig="${esc(fid)}" title="跳转查看关联图表 ${esc(fid)}">${esc(fid)} ↗</button>`;
  }

  function renderPreScanBody(scan) {
    if (!scan) {
      return `<div class="dim-card wl-empty-card"><p>正在扫描当前论文的湿实验章节与参数...</p></div>`;
    }
    const cats = (scan.detected_categories || [])
      .map((c) => `<span class="meta-pill">${esc(c.name)} · ${c.count}</span>`)
      .join("");

    const verdictHtml = scan.likely_has_wetlab
      ? `<div class="wl-well wl-well-accent">
           <strong>初步扫描：检测到 ${scan.strong_wetlab_slices} 段高置信度湿实验内容（共 ${scan.candidate_count} 段候选段落）。</strong>
           <span>点击上方「提取湿实验说明书」，AI 将把这些散落的方法与结果段落整理为可直接上台对照执行的 SOP 说明书（含物料清单、关键参数、对照设计与排错指南）。</span>
         </div>`
      : `<div class="wl-well wl-well-warm">
           <strong>初步扫描：本文未检测到明显湿实验强信号（候选段落 ${scan.candidate_count} 段），可能是纯计算 / 算法类论文。</strong>
           <span>你仍可点击上方「提取湿实验说明书」进行深度核验；若确属纯干实验论文，系统会如实说明并给出建议补充的湿实验验证方案。</span>
         </div>`;

    const candsHtml = (scan.candidates || []).length
      ? `<div class="dim-card">
           <div class="dim-header">
             <div class="dim-title-group">
               <span class="dim-num">SCAN</span>
               <h3>自动定位到的实验相关原文段落（${scan.candidates.length} 段）</h3>
             </div>
           </div>
           <div class="wl-scan-list">
             ${scan.candidates
               .slice(0, 12)
               .map(
                 (c) => `
               <div class="wl-scan-row">
                 <div class="wl-scan-row-head">
                   <div class="wl-scan-row-title">
                     ${renderSliceChip(c.slice_id)}
                     <strong>${esc(c.heading)}</strong>
                     <span class="wl-muted">P${c.page} · ${esc(c.section_label)}</span>
                   </div>
                   <div class="wl-tag-row">
                     ${(c.tags || []).map((t) => `<span class="meta-pill">${esc(t)}</span>`).join("")}
                   </div>
                 </div>
                 <p class="wl-scan-excerpt">${esc(c.excerpt)}</p>
                 ${
                   (c.params || []).length
                     ? `<div class="wl-param-strip">${c.params.map((p) => `<span class="wl-param-chip">${esc(p)}</span>`).join("")}</div>`
                     : ""
                 }
               </div>
             `
               )
               .join("")}
           </div>
         </div>`
      : "";

    return `
      <div class="dim-card" style="margin-bottom:16px">
        ${verdictHtml}
        ${cats ? `<div class="wl-tag-row" style="margin-top:12px">${cats}</div>` : ""}
      </div>
      ${candsHtml}
    `;
  }

  function renderProtocolBody(proto) {
    const pid = state.currentPaperId;
    const checks = loadChecks(pid);

    // Pure computational / dry-lab paper
    if (!proto.has_wetlab) {
      const sugs = proto.suggested_wetlab_validations || [];
      return `
        <div class="dim-card" style="margin-bottom:16px">
          <div class="wl-well wl-well-warm">
            <strong>湿实验核验结果：本文属于纯计算 / 干实验研究，未包含作者实际执行的湿实验。</strong>
            <p style="margin:6px 0 0">${esc(proto.no_wetlab_explanation || proto.executive_summary || "")}</p>
          </div>
        </div>
        ${
          sugs.length
            ? `<div class="dim-card">
                <div class="dim-header">
                  <div class="dim-title-group">
                    <span class="dim-num">PLAN</span>
                    <h3>建议补充的湿实验验证方案</h3>
                  </div>
                </div>
                <div class="wl-sug-grid">
                  ${sugs
                    .map(
                      (s, idx) => `
                    <div class="wl-sug-card">
                      <div class="wl-sug-head">
                        <span class="wl-step-badge">${idx + 1}</span>
                        <strong>${esc(s.title || "")}</strong>
                      </div>
                      ${s.goal ? `<p class="wl-sug-line"><strong>验证目标：</strong>${esc(s.goal)}</p>` : ""}
                      ${s.outline ? `<p class="wl-sug-line"><strong>实验思路：</strong>${esc(s.outline)}</p>` : ""}
                    </div>
                  `
                    )
                    .join("")}
                </div>
              </div>`
            : ""
        }
      `;
    }

    const bio = proto.biosafety_and_prerequisites || {};
    const mats = proto.materials_and_reagents || [];
    const protos = proto.protocols || [];
    const missing = proto.missing_details_and_si_notes || [];
    const trouble = proto.troubleshooting_guide || [];

    // 1. Handbook Summary + Biosafety
    const heroHtml = `
      <div class="dim-card" style="margin-bottom:16px">
        <div class="wl-doc-head">
          <div>
            <span class="meta-pill accent">湿实验操作说明书</span>
            <h2 class="wl-doc-title">${esc(proto.manual_title || "湿实验操作说明书")}</h2>
          </div>
          <div class="wl-doc-stats">
            <span class="meta-pill">${protos.length} 个实验模块</span>
            <span class="meta-pill">${mats.length} 项物料/仪器</span>
            ${bio.estimated_total_duration ? `<span class="meta-pill">${esc(bio.estimated_total_duration)}</span>` : ""}
          </div>
        </div>
        ${proto.executive_summary ? `<div class="hero-tldr"><strong>实验体系总览：</strong>${esc(proto.executive_summary)}</div>` : ""}
        ${
          proto.beginner_overview
            ? `<div class="hero-beginner-hook beginner-only"><strong>零基础大白话导读：</strong>${esc(proto.beginner_overview)}</div>`
            : ""
        }
        ${
          bio.biosafety_level || (bio.safety_notes || []).length
            ? `<div class="wl-safety-box">
                <div class="wl-safety-head">
                  <strong>生物安全与实验前提</strong>
                  ${bio.biosafety_level ? `<span class="meta-pill">${esc(bio.biosafety_level)}</span>` : ""}
                </div>
                ${
                  (bio.safety_notes || []).length
                    ? `<ul class="wl-bullet-list">${bio.safety_notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul>`
                    : ""
                }
              </div>`
            : ""
        }
      </div>
    `;

    // 2. Interactive Materials & Reagents Checklist
    const matCats = ["all", ...Array.from(new Set(mats.map((m) => m.category).filter(Boolean)))];
    const filteredMats =
      wl.materialCatFilter === "all"
        ? mats
        : mats.filter((m) => m.category === wl.materialCatFilter);
    const checkedMatCount = mats.filter((_, i) => checks[`mat:${i}`]).length;

    const matsHtml = mats.length
      ? `
      <div class="dim-card" style="margin-bottom:16px">
        <div class="dim-header">
          <div class="dim-title-group">
            <span class="dim-num">LIST</span>
            <h3>试剂、材料与仪器准备清单</h3>
          </div>
          <span class="wl-muted">已备齐 ${checkedMatCount} / ${mats.length}</span>
        </div>
        <div class="filter-chips" style="margin-bottom:12px">
          ${matCats
            .map(
              (c) =>
                `<button type="button" class="chip ${wl.materialCatFilter === c ? "active" : ""}" data-wl-matcat="${esc(c)}">${
                  c === "all" ? `全部 (${mats.length})` : esc(c)
                }</button>`
            )
            .join("")}
        </div>
        <div class="cmp-table-wrap">
          <table class="wl-table">
            <thead>
              <tr>
                <th style="width:46px;text-align:center">备齐</th>
                <th style="width:120px">类别</th>
                <th>名称</th>
                <th>规格 / 来源</th>
                <th>实验用途</th>
                <th style="width:90px">原文定位</th>
              </tr>
            </thead>
            <tbody>
              ${filteredMats
                .map((m) => {
                  const origIdx = mats.indexOf(m);
                  const ckKey = `mat:${origIdx}`;
                  const isDone = Boolean(checks[ckKey]);
                  return `
                  <tr class="${isDone ? "wl-row-done" : ""}">
                    <td style="text-align:center">
                      <input type="checkbox" data-wl-check="${esc(ckKey)}" ${isDone ? "checked" : ""} aria-label="标记已备齐" />
                    </td>
                    <td><span class="meta-pill">${esc(m.category || "物料")}</span></td>
                    <td><strong>${esc(m.name || "")}</strong></td>
                    <td>${esc(m.spec_or_source || "论文正文未注明")}</td>
                    <td>${esc(m.purpose || "")}</td>
                    <td><div class="wl-anchor-wrap">${(m.source_slices || []).map(renderSliceChip).join("")}</div></td>
                  </tr>
                `;
                })
                .join("")}
            </tbody>
          </table>
        </div>
      </div>
    `
      : "";

    // 3. Modular Step-by-Step SOP Protocols
    const visibleProtos =
      wl.activeProtoId === "all" ? protos : protos.filter((p) => p.id === wl.activeProtoId);

    const protoNavHtml =
      protos.length > 1
        ? `<div class="filter-chips" style="margin-bottom:14px">
            <button type="button" class="chip ${wl.activeProtoId === "all" ? "active" : ""}" data-wl-proto="all">全部模块 (${protos.length})</button>
            ${protos
              .map(
                (p) =>
                  `<button type="button" class="chip ${wl.activeProtoId === p.id ? "active" : ""}" data-wl-proto="${esc(p.id)}">${esc(p.id)} · ${esc((p.title || "").replace(/^[一二三四五六七八九十]+[、.．]\s*/, "").slice(0, 18))}</button>`
              )
              .join("")}
          </div>`
        : "";

    const protosHtml = protos.length
      ? `
      <div class="wl-protos-section">
        <div class="dim-header" style="margin-bottom:10px">
          <div class="dim-title-group">
            <span class="dim-num">SOP</span>
            <h3>分模块标准操作流程（可勾选执行进度 · 点击锚点直达原文截图）</h3>
          </div>
        </div>
        ${protoNavHtml}
        ${visibleProtos
          .map((p) => {
            const ctrl = p.inputs_and_controls || {};
            const steps = p.steps || [];
            const doneSteps = steps.filter((st) => checks[`step:${p.id}:${st.step_no}`]).length;
            return `
            <article class="dim-card wl-proto-card">
              <div class="wl-proto-head">
                <div class="wl-proto-title-wrap">
                  <span class="wl-proto-id">${esc(p.id || "SOP")}</span>
                  <h4>${esc(p.title || "")}</h4>
                </div>
                <div class="wl-tag-row">
                  ${p.estimated_time ? `<span class="meta-pill">${esc(p.estimated_time)}</span>` : ""}
                  ${p.difficulty ? `<span class="meta-pill">${esc(p.difficulty)}</span>` : ""}
                  <span class="meta-pill">进度 ${doneSteps}/${steps.length}</span>
                </div>
              </div>

              ${p.objective ? `<p class="wl-proto-obj"><strong>实验目的：</strong>${esc(p.objective)}</p>` : ""}
              ${
                p.beginner_analogy
                  ? `<div class="wl-well wl-well-warm beginner-only"><strong>大白话理解：</strong>${esc(p.beginner_analogy)}</div>`
                  : ""
              }

              <div class="wl-ctrl-grid">
                <div><span>待测样品</span><strong>${esc(ctrl.sample_input || "—")}</strong></div>
                <div><span>阳性对照</span><strong>${esc(ctrl.positive_control || "正文未明确提及")}</strong></div>
                <div><span>阴性 / 空白对照</span><strong>${esc(ctrl.negative_control || "正文未明确提及")}</strong></div>
                <div><span>重复次数</span><strong>${esc(ctrl.replicates || "正文未明确提及")}</strong></div>
              </div>

              <ol class="wl-steps-list">
                ${steps
                  .map((st) => {
                    const ckKey = `step:${p.id}:${st.step_no}`;
                    const isDone = Boolean(checks[ckKey]);
                    return `
                    <li class="wl-step-item ${isDone ? "done" : ""}">
                      <div class="wl-step-main">
                        <label class="wl-step-check">
                          <input type="checkbox" data-wl-check="${esc(ckKey)}" ${isDone ? "checked" : ""} />
                          <span class="wl-step-num">Step ${esc(String(st.step_no ?? ""))}</span>
                          <span class="wl-step-action">${esc(st.action || "")}</span>
                        </label>
                        ${st.source_slice ? renderSliceChip(st.source_slice) : ""}
                      </div>
                      ${
                        st.key_params || st.critical_tip
                          ? `<div class="wl-step-sub">
                              ${st.key_params ? `<span class="wl-param-chip">${esc(st.key_params)}</span>` : ""}
                              ${st.critical_tip ? `<span class="wl-tip-inline">注意：${esc(st.critical_tip)}</span>` : ""}
                            </div>`
                          : ""
                      }
                    </li>
                  `;
                  })
                  .join("")}
              </ol>

              ${
                p.readout_and_acceptance
                  ? `<div class="wl-well wl-well-accent" style="margin-top:12px">
                      <strong>检测判读与预期结果：</strong>${esc(p.readout_and_acceptance)}
                    </div>`
                  : ""
              }

              ${
                (p.source_slices || []).length || (p.related_figures || []).length
                  ? `<div class="wl-proto-foot">
                      ${
                        (p.source_slices || []).length
                          ? `<div class="wl-anchor-wrap"><span class="wl-muted">原文段落：</span>${p.source_slices.map(renderSliceChip).join("")}</div>`
                          : ""
                      }
                      ${
                        (p.related_figures || []).length
                          ? `<div class="wl-anchor-wrap"><span class="wl-muted">关联图表：</span>${p.related_figures.map(renderFigChip).join("")}</div>`
                          : ""
                      }
                    </div>`
                  : ""
              }
            </article>
          `;
          })
          .join("")}
      </div>
    `
      : "";

    // 4. Missing Details / SI Checkpoints + Troubleshooting
    const missingHtml = missing.length
      ? `
      <div class="dim-card" style="margin-bottom:16px">
        <div class="dim-header">
          <div class="dim-title-group">
            <span class="dim-num">SI</span>
            <h3>正文省略参数与 Supporting Information 核对提醒</h3>
          </div>
        </div>
        <ul class="wl-si-list">
          ${missing
            .map((item, idx) => {
              const ckKey = `si:${idx}`;
              const isDone = Boolean(checks[ckKey]);
              return `<li class="${isDone ? "done" : ""}"><label><input type="checkbox" data-wl-check="${esc(ckKey)}" ${isDone ? "checked" : ""} /> <span>${esc(item)}</span></label></li>`;
            })
            .join("")}
        </ul>
      </div>
    `
      : "";

    const troubleHtml = trouble.length
      ? `
      <div class="dim-card">
        <div class="dim-header">
          <div class="dim-title-group">
            <span class="dim-num">FAQ</span>
            <h3>实验复现常见问题排查（Troubleshooting）</h3>
          </div>
        </div>
        <div class="cmp-table-wrap">
          <table class="wl-table">
            <thead>
              <tr>
                <th style="width:26%">常见现象 / 隐患</th>
                <th style="width:32%">可能原因</th>
                <th>排查与解决建议</th>
              </tr>
            </thead>
            <tbody>
              ${trouble
                .map(
                  (t) => `
                <tr>
                  <td><strong>${esc(t.issue || "")}</strong></td>
                  <td>${esc(t.likely_cause || "")}</td>
                  <td>${esc(t.solution || "")}</td>
                </tr>
              `
                )
                .join("")}
            </tbody>
          </table>
        </div>
      </div>
    `
      : "";

    return heroHtml + matsHtml + protosHtml + missingHtml + troubleHtml;
  }

  function renderWetlabTab(loading = false) {
    const root = $("#tab-wetlab");
    if (!root) return;

    if (!state.currentPaperId) {
      root.innerHTML = `
        <div class="dim-card wl-empty-card">
          <h3>请先选择或导入一篇论文</h3>
          <p>导入论文后，可在此一键分离提取全文湿实验部分并生成可导出的标准操作说明书（SOP）。</p>
        </div>
      `;
      return;
    }

    const hasProto = Boolean(wl.protocol);
    root.innerHTML = `
      <div class="wl-toolbar-card">
        <div class="wl-toolbar-head">
          <div>
            <h2>湿实验操作说明书提取</h2>
            <p class="wl-muted">自动分离论文中的湿实验章节与结果细节，提炼为包含试剂清单、关键参数、对照设计与排错指南的可执行说明书，支持导出 Markdown 与可打印 PDF。</p>
          </div>
          <div class="wl-export-actions">
            <button id="btnExportWetlabMd" type="button" class="btn btn-secondary btn-sm" ${hasProto ? "" : "disabled"}>
              <svg class="ic"><use href="#i-download"/></svg>导出 Markdown (.md)
            </button>
            <button id="btnExportWetlabPrint" type="button" class="btn btn-secondary btn-sm" ${hasProto ? "" : "disabled"}>
              打印 / 导出 PDF 说明书
            </button>
            <button id="btnExportWetlabHtml" type="button" class="btn btn-ghost btn-sm" ${hasProto ? "" : "disabled"}>
              下载 HTML
            </button>
          </div>
        </div>

        <div class="wl-action-row">
          <input id="wlFocusInput" type="text" class="search-input" style="flex:1;min-width:240px"
            value="${esc(wl.focusNote)}"
            placeholder="可选：指定重点细化的实验环节（例如：重点拆解多肽合成纯化、MIC 测定与溶血实验步骤）" />
          <button id="btnExtractWetlab" type="button" class="btn btn-primary" ${wl.extracting ? "disabled" : ""}>
            ${wl.extracting ? "正在提炼说明书..." : hasProto ? "重新提取湿实验说明书" : "提取湿实验说明书"}
          </button>
        </div>

        ${
          wl.extracting
            ? `<div class="progress-box" style="margin-top:12px">
                <div class="progress-head">
                  <span>${esc(wl.progressMsg || "正在提炼湿实验操作说明书...")}</span>
                  <strong>${wl.progressPct}%</strong>
                </div>
                <div class="progress-track">
                  <div class="progress-fill" style="width:${wl.progressPct}%"></div>
                </div>
              </div>`
            : ""
        }
        ${wl.errorMsg ? `<div class="wl-well wl-well-error" style="margin-top:12px">${esc(wl.errorMsg)}</div>` : ""}
      </div>

      <div id="wlBodyRoot">
        ${loading ? `<div class="dim-card wl-empty-card"><p>正在读取论文湿实验信息...</p></div>` : hasProto ? renderProtocolBody(wl.protocol) : renderPreScanBody(wl.scan)}
      </div>
    `;

    bindWetlabEvents(root);
  }

  function bindWetlabEvents(root) {
    root.querySelector("#wlFocusInput")?.addEventListener("input", (e) => {
      wl.focusNote = e.target.value;
    });

    root.querySelector("#btnExtractWetlab")?.addEventListener("click", runExtraction);

    root.querySelector("#btnExportWetlabMd")?.addEventListener("click", () => {
      if (!state.currentPaperId || !wl.protocol) return;
      window.open(`/api/papers/${encodeURIComponent(state.currentPaperId)}/wetlab/export-md`, "_blank");
    });

    root.querySelector("#btnExportWetlabPrint")?.addEventListener("click", () => {
      if (!state.currentPaperId || !wl.protocol) return;
      window.open(`/api/papers/${encodeURIComponent(state.currentPaperId)}/wetlab/export-html`, "_blank");
    });

    root.querySelector("#btnExportWetlabHtml")?.addEventListener("click", () => {
      if (!state.currentPaperId || !wl.protocol) return;
      window.open(`/api/papers/${encodeURIComponent(state.currentPaperId)}/wetlab/export-html?download=1`, "_blank");
    });

    const bodyRoot = root.querySelector("#wlBodyRoot");
    bodyRoot?.addEventListener("click", (e) => {
      const sBtn = e.target.closest("[data-wl-slice]");
      if (sBtn) {
        jumpToSlice(sBtn.dataset.wlSlice);
        return;
      }
      const fBtn = e.target.closest("[data-wl-fig]");
      if (fBtn) {
        jumpToFigure(fBtn.dataset.wlFig);
        return;
      }
      const catBtn = e.target.closest("[data-wl-matcat]");
      if (catBtn) {
        wl.materialCatFilter = catBtn.dataset.wlMatcat;
        renderWetlabTab();
        return;
      }
      const pBtn = e.target.closest("[data-wl-proto]");
      if (pBtn) {
        wl.activeProtoId = pBtn.dataset.wlProto;
        renderWetlabTab();
      }
    });

    bodyRoot?.addEventListener("change", (e) => {
      const cb = e.target.closest("[data-wl-check]");
      if (!cb || !state.currentPaperId) return;
      toggleCheck(state.currentPaperId, cb.dataset.wlCheck, cb.checked);
      renderWetlabTab();
    });
  }

  async function runExtraction() {
    const pid = state.currentPaperId;
    if (!pid || wl.extracting) return;
    wl.extracting = true;
    wl.errorMsg = "";
    wl.progressPct = 10;
    wl.progressMsg = "正在启动湿实验说明书提炼...";
    renderWetlabTab();

    try {
      const { job_id } = await apiJson(`/api/papers/${encodeURIComponent(pid)}/wetlab/extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ focus_note: wl.focusNote }),
      });

      const timer = setInterval(async () => {
        try {
          const job = await apiJson(`/api/jobs/${job_id}`);
          wl.progressPct = job.progress || 0;
          wl.progressMsg = job.message || job.status;
          if (job.status === "done") {
            clearInterval(timer);
            wl.extracting = false;
            await openWetlabTab(true);
          } else if (job.status === "error") {
            clearInterval(timer);
            wl.extracting = false;
            wl.errorMsg = job.message || "湿实验说明书提炼失败，请检查模型配置后重试。";
            renderWetlabTab();
          } else {
            renderWetlabTab();
          }
        } catch (pollErr) {
          clearInterval(timer);
          wl.extracting = false;
          wl.errorMsg = pollErr.message || "轮询任务状态失败";
          renderWetlabTab();
        }
      }, 1200);
    } catch (err) {
      wl.extracting = false;
      wl.errorMsg = err.message || "启动提取任务失败";
      renderWetlabTab();
    }
  }

  return {
    openWetlabTab,
    onPaperLoaded,
    renderWetlabTab,
  };
}
