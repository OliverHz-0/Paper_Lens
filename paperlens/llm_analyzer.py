"""LLM deep-analysis engine (OpenAI-compatible / Gemini / DeepSeek / Ollama) + deterministic fallback."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

import httpx

from .config import load_config


def find_agy_binary() -> str | None:
    found = shutil.which("agy")
    if found:
        return found
    cand = Path.home() / ".local" / "bin" / "agy"
    return str(cand) if cand.exists() else None


def _call_agy_cli(messages: list[dict[str, str]], model: str, timeout: int = 240) -> str:
    agy_bin = find_agy_binary()
    if not agy_bin:
        raise RuntimeError("未在本机找到 `agy` CLI（Antigravity CLI），请在设置中切换为其他 API 厂商。")

    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            parts.append(f"[System Instructions]\n{content}")
        else:
            parts.append(content)
    prompt = "\n\n".join(parts)

    cmd = [
        agy_bin,
        "-p",
        prompt,
        "--disable-slash-commands",
        "--output-format",
        "text",
        "--print-timeout",
        f"{timeout}s",
    ]
    if model:
        cmd.extend(["--model", model])

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout + 20,
        env={**os.environ},
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()[-400:]
        raise RuntimeError(f"Antigravity CLI (`agy`) 执行失败 (rc={proc.returncode}): {err}")
    out = (proc.stdout or "").strip()
    if not out:
        raise RuntimeError("Antigravity CLI (`agy`) 返回内容为空。")
    return out


def _call_chat_completion(messages: list[dict[str, str]], max_tokens: int = 4096) -> str:
    cfg = load_config()
    provider = (cfg.get("llm_provider") or "agy_cli").strip()
    model = (cfg.get("llm_model") or "gemini-4-neon-high").strip()

    if provider == "agy_cli":
        return _call_agy_cli(messages, model=model, timeout=240)

    api_key = (cfg.get("llm_api_key") or "").strip()
    base_url = (cfg.get("llm_base_url") or "https://api.openai.com/v1").rstrip("/")
    proxy = (cfg.get("http_proxy") or "").strip() or None

    if not api_key and "localhost" not in base_url and "127.0.0.1" not in base_url:
        raise RuntimeError("尚未配置 LLM API Key，请点击右上角「设置」填入 API Key（或切换为免 Key 的 Antigravity CLI · Gemini 4 Neon）。")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.25,
        "max_tokens": max_tokens,
    }
    with httpx.Client(timeout=120.0, proxy=proxy) as client:
        r = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]


def _extract_json_block(text: str) -> Any:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: extract outermost {...} or [...]
        for open_c, close_c in (("{", "}"), ("[", "]")):
            s = text.find(open_c)
            e = text.rfind(close_c)
            if s != -1 and e > s:
                try:
                    return json.loads(text[s : e + 1])
                except Exception:
                    pass
        raise


def test_llm_connection(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Send a minimal ping via either local Antigravity CLI (`agy`) or HTTP OpenAI-compatible API."""
    cfg = load_config()
    if overrides:
        for k in ("llm_provider", "llm_base_url", "llm_model", "http_proxy"):
            if k in overrides and overrides[k] is not None:
                cfg[k] = str(overrides[k]).strip()
        raw_key = str(overrides.get("llm_api_key") or "").strip()
        if raw_key and not raw_key.startswith("••••"):
            cfg["llm_api_key"] = raw_key

    provider = (cfg.get("llm_provider") or "agy_cli").strip()
    model = (cfg.get("llm_model") or "gemini-4-neon-high").strip()

    if provider == "agy_cli":
        t0 = time.time()
        try:
            reply = _call_agy_cli(
                [{"role": "user", "content": "Reply with ONLY the two letters OK."}],
                model=model,
                timeout=45,
            )
            ms = int((time.time() - t0) * 1000)
            return {
                "ok": True,
                "provider": "agy_cli",
                "latency_ms": ms,
                "model": model,
                "reply": reply[:80],
            }
        except Exception as exc:
            ms = int((time.time() - t0) * 1000)
            return {
                "ok": False,
                "provider": "agy_cli",
                "latency_ms": ms,
                "model": model,
                "error": str(exc),
            }

    base_url = (cfg.get("llm_base_url") or "https://api.openai.com/v1").rstrip("/")
    api_key = (cfg.get("llm_api_key") or "").strip()
    proxy = (cfg.get("http_proxy") or "").strip() or None

    if not api_key and "localhost" not in base_url and "127.0.0.1" not in base_url:
        return {
            "ok": False,
            "model": model,
            "base_url": base_url,
            "error": "请先填写 API Key（本地 Ollama 或 Antigravity CLI 除外）。",
        }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    t0 = time.time()
    try:
        with httpx.Client(timeout=25.0, proxy=proxy) as client:
            r = client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Reply with OK only."}],
                    "max_tokens": 16,
                    "temperature": 0,
                },
            )
            ms = int((time.time() - t0) * 1000)
            if r.status_code >= 400:
                body_snippet = r.text[:260]
                hint = ""
                if r.status_code == 401:
                    hint = "（API Key 无效或未开通权限）"
                elif r.status_code == 404:
                    hint = "（Base URL 或 Model 名称不存在，请核对模型 ID）"
                return {
                    "ok": False,
                    "status_code": r.status_code,
                    "latency_ms": ms,
                    "model": model,
                    "base_url": base_url,
                    "error": f"HTTP {r.status_code} {hint}: {body_snippet}",
                }
            data = r.json()
            reply = (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
            return {
                "ok": True,
                "status_code": r.status_code,
                "latency_ms": ms,
                "model": data.get("model") or model,
                "base_url": base_url,
                "reply": reply[:80] or "OK",
            }
    except Exception as exc:
        ms = int((time.time() - t0) * 1000)
        return {
            "ok": False,
            "latency_ms": ms,
            "model": model,
            "base_url": base_url,
            "error": f"网络请求失败（如访问海外官方 API 请填写本机 HTTP 代理）：{exc}",
        }


def build_structural_fallback(paper_dir: Path) -> dict[str, Any]:
    """Create an immediate, zero-API-key structural analysis shell so every uploaded PDF is instantly readable."""
    manifest = json.loads((paper_dir / "manifest.json").read_text(encoding="utf-8"))
    slices = manifest.get("slices", [])

    def _collect(sec: str, limit: int = 3) -> list[str]:
        return [s["id"] for s in slices if s["section"] == sec][:limit]

    slice_notes = {}
    for s in slices:
        sec_hint = {
            "abstract": "全文摘要：高度浓缩了本文的问题背景、核心方法、关键实验数据与核心结论。",
            "introduction": "引言段落：铺垫研究领域痛点、梳理前人工作局限，并引出本文的核心研究假设。",
            "methods": "实验与计算方法：交代数据集、模型参数或湿实验验证的具体操作协议，保证可复现性。",
            "results": "结果与讨论：展示核心实验数据、图表证据与背后的科学机理解释。",
            "conclusions": "结论与展望：总结全文突破，客观指出当前局限与未来演进方向。",
        }.get(s["section"], "正文切片段落。")
        slice_notes[s["id"]] = {
            "heading": f"{s['section_label']} · 第 {s['page']} 页",
            "translation_zh": "（当前处于零 Key 快速结构化切图模式：点击右上角「设置」配置任意 LLM API Key 并运行 AI 深度解读，即可自动生成该段逐句中文直译。）",
            "role": sec_hint,
            "plain_explanation": "当前处于【结构化快速解析模式】。点击右上角「设置」配置任意大语言模型 API Key 后，再点「运行 AI 深度解读」，即可自动生成针对零背景读者的通俗类比与专业术语解释。",
            "key_takeaways": [f"所在页码：P{s['page']}"]
            + ([f"引用文献：{', '.join('Ref ' + str(r) for r in s['refs'])}"] if s.get("refs") else [])
            + ([f"关联图表：{', '.join(s['linked_figures'])}"] if s.get("linked_figures") else []),
            "terms": [],
        }

    abs_text = next((s["text"] for s in slices if s["section"] == "abstract"), "")
    analysis = {
        "mode": "structural_fallback",
        "paper_title_zh": manifest.get("title", ""),
        "one_sentence_tldr": abs_text[:280] + ("..." if len(abs_text) > 280 else "")
        if abs_text
        else "已自动完成全文逐段切片、高清截图、图表定位、参考文献解析与外部资源提取。配置 LLM API Key 后可解锁深度大白话解读。",
        "beginner_hook": "这篇论文已经完成版面拆解与高清切图！你可以直接在「逐段切片精读」里按顺序阅读原文截图并点击任意 [Ref #] 实时溯源，或配置 API Key 触发一键零基础科普解读。",
        "dimensions": [
            {
                "key": "background",
                "num": "01",
                "title": "研究背景",
                "subtitle": "为什么这个问题值得研究？前人卡在哪？",
                "summary": "请查看下方自动定位的引言原文切片（或配置 LLM API Key 一键提炼中文背景综述与通俗科普）。",
                "beginner_analogy": "配置 API Key 后，这里会自动用日常生活类比帮你 30 秒听懂该领域背景。",
                "bullets": ["已自动提取引言段落与关联引用文献，可点击切片卡片逐段对照。"],
                "slice_ids": _collect("introduction", 3),
                "figure_ids": [],
            },
            {
                "key": "objective",
                "num": "02",
                "title": "研究目的",
                "subtitle": "作者到底想解决什么核心问题？",
                "summary": "请结合摘要与引言末尾段落查看本文的核心科学目标。",
                "beginner_analogy": "配置 API Key 后，这里会提炼作者的“通关目标”。",
                "bullets": ["已自动定位摘要与引言目标段落。"],
                "slice_ids": _collect("abstract", 1) + _collect("introduction", 2)[-1:],
                "figure_ids": [],
            },
            {
                "key": "methods",
                "num": "03",
                "title": "使用了什么方法？",
                "subtitle": "核心技术路线与实验/算法框架",
                "summary": f"已自动切分 {len([s for s in slices if s['section']=='methods'])} 段方法学原文切片。",
                "beginner_analogy": "配置 API Key 后，这里会将复杂实验与算法拆解为通俗步骤。",
                "bullets": ["点击切片卡片可查看原始公式、参数与对应流程图。"],
                "slice_ids": _collect("methods", 4),
                "figure_ids": [f["id"] for f in manifest.get("figures", [])[:2]],
            },
            {
                "key": "validation",
                "num": "04",
                "title": "怎么样验证的？",
                "subtitle": "如何证明这个方法真的有效、不是自嗨？",
                "summary": "已自动提取验证实验段落与对照表格/图表。",
                "beginner_analogy": "配置 API Key 后，这里会拆解作者设计了哪些“考场”来检验成果。",
                "bullets": ["可结合 Methods 与 Results 中的验证图表对照核查。"],
                "slice_ids": _collect("results", 3),
                "figure_ids": [f["id"] for f in manifest.get("figures", [])[2:4]],
            },
            {
                "key": "results",
                "num": "05",
                "title": "结果是怎么样？",
                "subtitle": "核心实验数据与关键发现",
                "summary": f"已自动提取 {manifest.get('figure_count', 0)} 张核心图表与 {len([s for s in slices if s['section']=='results'])} 段结果讨论。",
                "beginner_analogy": "配置 API Key 后，这里会逐图逐表翻译关键数字的真实含义。",
                "bullets": ["下方已嵌入自动裁剪的高清原文图表。"],
                "slice_ids": _collect("results", 5),
                "figure_ids": [f["id"] for f in manifest.get("figures", [])],
            },
            {
                "key": "innovations",
                "num": "06",
                "title": "创新点与批判性审读",
                "subtitle": "突破在哪里？还有哪些局限？",
                "summary": "已自动定位结论与局限性段落。",
                "beginner_analogy": "配置 API Key 后，这里会客观评估论文含金量并指出隐藏局限。",
                "bullets": ["点击下方结论切片查看作者自述的突破与不足。"],
                "slice_ids": _collect("conclusions", 3),
                "figure_ids": [],
            },
        ],
        "workflow_steps": [
            {"step": "1", "title": "问题提出", "desc": "查看 Abstract / Introduction 切片"},
            {"step": "2", "title": "方法构建", "desc": "查看 Methods 切片与架构图"},
            {"step": "3", "title": "实验验证", "desc": "查看核心表格与对照图"},
            {"step": "4", "title": "结论发现", "desc": "查看 Results & Conclusions 切片"},
        ],
        "critical_notes": [
            "当前为无 API Key 的确定性结构解析模式：所有切图、引文提取、GitHub/SI 抓取与实时引文溯源均已就绪。",
            "在右上角「设置」中填入 OpenAI / Gemini / DeepSeek / Ollama 接口后，即可触发完整 AI 零基础深度剖析。",
        ],
        "glossary": {},
        "slice_notes": slice_notes,
        "figure_notes": {
            f["id"]: {
                "title_zh": f"{f['label']}（第 {f['page']} 页）",
                "caption_zh": f["caption"][:300],
                "plain_summary": f["caption"][:240],
                "how_to_read": "点击图片可全屏放大查看细节。配置 LLM API Key 后可生成逐子图拆解与上下文联系。",
                "subpanels": [],
                "context_connection": "与所在页前后段落直接对应，可点击下方原文切片按钮跳转核对。",
                "insert_after_slice": next(
                    (s["id"] for s in reversed(slices) if f["id"] in (s.get("linked_figures") or [])),
                    next((s["id"] for s in slices if s["page"] >= f["page"]), slices[-1]["id"] if slices else "S01"),
                ),
                "related_slices": [s["id"] for s in slices if f["id"] in (s.get("linked_figures") or [])][:6],
            }
            for f in manifest.get("figures", [])
        },
    }
    (paper_dir / "analysis.json").write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return analysis


def run_llm_deep_analysis(
    paper_dir: Path, progress_cb: Callable[[int, str], None] | None = None
) -> dict[str, Any]:
    """Run full 2-stage LLM deep analysis: (1) Global 6-dim + glossary + figures, (2) Batched slice-by-slice explanations."""
    manifest = json.loads((paper_dir / "manifest.json").read_text(encoding="utf-8"))
    slices = manifest.get("slices", [])
    figures = manifest.get("figures", [])

    if progress_cb:
        progress_cb(35, "正在调用大模型提炼六大核心维度、零基础通俗科普与术语词典...")

    # Build compact full-paper digest for Stage 1
    digest_lines = [f"Title: {manifest.get('title')}", f"Authors: {manifest.get('authors')}"]
    for s in slices:
        digest_lines.append(f"[{s['id']} | P{s['page']} | {s['section']}] {s['text'][:650]}")
    for f in figures:
        digest_lines.append(f"[{f['id']} | P{f['page']}] {f['caption'][:350]}")
    full_digest = "\n".join(digest_lines)[:28000]

    stage1_prompt = f"""你是一位顶级的跨学科科研论文解读专家，特别擅长把艰深的生物/AI/医学/物理论文讲给【完全没有该专业背景】的聪明外行听。
请彻底分析下面这篇论文，并严格返回合法的 JSON（不要附加任何多余文字），格式如下：
{{
  "paper_title_zh": "准确的中文译名",
  "one_sentence_tldr": "一句话讲清这篇论文干了什么、牛在哪里（60-100字）",
  "beginner_hook": "用一句生动的生活化类比，帮零基础读者瞬间建立直觉（80-150字）",
  "workflow_steps": [
    {{"step": "1", "title": "4-8字标题", "desc": "一句话说明这一步做什么"}}
  ],
  "dimensions": [
    {{
      "key": "background", "num": "01", "title": "研究背景", "subtitle": "为什么研究？行业卡点在哪？",
      "summary": "深度剖析（150-250字）", "beginner_analogy": "零基础大白话类比（80-120字）",
      "bullets": ["要点1", "要点2", "要点3"], "slice_ids": ["S01", "S02"], "figure_ids": []
    }},
    {{ "key": "objective", "num": "02", "title": "研究目的", "subtitle": "...", "summary": "...", "beginner_analogy": "...", "bullets": [...], "slice_ids": [...], "figure_ids": [] }},
    {{ "key": "methods", "num": "03", "title": "使用了什么方法？", "subtitle": "...", "summary": "...", "beginner_analogy": "...", "bullets": [...], "slice_ids": [...], "figure_ids": [...] }},
    {{ "key": "validation", "num": "04", "title": "怎么样验证的？", "subtitle": "...", "summary": "...", "beginner_analogy": "...", "bullets": [...], "slice_ids": [...], "figure_ids": [...] }},
    {{ "key": "results", "num": "05", "title": "结果是怎么样？", "subtitle": "...", "summary": "...", "beginner_analogy": "...", "bullets": [...], "slice_ids": [...], "figure_ids": [...] }},
    {{ "key": "innovations", "num": "06", "title": "创新点在哪？", "subtitle": "...", "summary": "...", "beginner_analogy": "...", "bullets": [...], "slice_ids": [...], "figure_ids": [] }}
  ],
  "critical_notes": ["批判性审读/局限性1", "局限性2", "局限性3"],
  "glossary": {{
    "专业术语原文或缩写": {{
      "zh": "中文名",
      "simple": "零基础一句话大白话解释",
      "analogy": "生动类比",
      "in_paper": "在本文中的具体作用"
    }}
  }},
  "figure_notes": {{
    "fig-1": {{
      "title_zh": "图 1 中文标题",
      "caption_zh": "原始图注的忠实中文翻译",
      "plain_summary": "一句话看懂这张图的核心结论",
      "how_to_read": "零基础看图指南：先看哪个子图、横纵坐标和颜色代表什么",
      "subpanels": [{{"label": "(a) 子图名", "detail": "这个子图展示了什么、结论是什么"}}],
      "context_connection": "这张图与正文哪些段落直接关联？它承接了前面的什么假设，又证明了后面的什么结论？",
      "insert_after_slice": "建议插在逐段精读的哪个 slice ID 后面（如 S28）",
      "related_slices": ["S28", "S30"]
    }}
  }},
  "mindmap": {{
    "root": {{"title": "论文核心主题（10-16字）", "subtitle": "一句话副标题"}},
    "branches": [
      {{
        "id": "b-bg", "title": "1. 研究背景与痛点", "color": "amber", "dim_key": "background",
        "children": [
          {{"label": "核心痛点短语", "detail": "简短说明", "target_type": "slice", "target_id": "S02"}}
        ]
      }}
    ]
  }}
}}

要求：
1. glossary 至少提炼 12-18 个最关键的专业术语。
2. slice_ids 与 figure_ids 必须严格使用下面给出的真实 ID（如 S01, fig-1, table-1）。
3. 严禁编造论文中不存在的数据。

论文全文摘要与切片：
{full_digest}
"""
    raw_s1 = _call_chat_completion(
        [{"role": "system", "content": "输出严格有效的 JSON。"}, {"role": "user", "content": stage1_prompt}],
        max_tokens=4096,
    )
    analysis = _extract_json_block(raw_s1)
    analysis["mode"] = "llm_deep"
    analysis.setdefault("slice_notes", {})

    # Stage 2: Batch slices (10 per batch) for thorough paragraph-by-paragraph analysis
    batch_size = 10
    total_batches = max(1, (len(slices) + batch_size - 1) // batch_size)
    for b_idx in range(0, len(slices), batch_size):
        batch = slices[b_idx : b_idx + batch_size]
        cur_b = b_idx // batch_size + 1
        if progress_cb:
            pct = 50 + int((cur_b / total_batches) * 45)
            progress_cb(pct, f"正在逐段精读与大白话翻译（第 {cur_b}/{total_batches} 批）...")

        batch_text = "\n".join(
            f"[{s['id']} | P{s['page']} | {s['section']}] {s['text']}" for s in batch
        )
        stage2_prompt = f"""请对以下论文原文段落逐段进行深度解读，面向【无相关专业背景】的读者。
返回严格 JSON，键为段落 ID（如 "S01"）：
{{
  "S01": {{
    "heading": "给这段起一个 6-14 字的中文小标题",
    "translation_zh": "【忠实中文翻译】将这段英文原文完整、准确、通顺地逐句翻译为中文，不遗漏关键数据与实验条件",
    "role": "【写作与逻辑作用】这段话为什么出现在这里？承接了什么、论证了什么？（50-100字）",
    "plain_explanation": "【零基础人话翻译】彻底抛开晦涩术语，用通俗易懂的语言或类比讲透这段话的意思（80-160字）",
    "key_takeaways": ["核心信息点1", "核心信息点2"],
    "terms": ["本段涉及的关键术语1", "术语2"]
  }}
}}

待解读段落：
{batch_text}
"""
        try:
            raw_s2 = _call_chat_completion(
                [{"role": "system", "content": "输出严格有效的 JSON。"}, {"role": "user", "content": stage2_prompt}],
                max_tokens=4096,
            )
            parsed_b = _extract_json_block(raw_s2)
            if isinstance(parsed_b, dict):
                analysis["slice_notes"].update(parsed_b)
        except Exception:
            for s in batch:
                analysis["slice_notes"].setdefault(
                    s["id"],
                    {
                        "heading": f"{s['section_label']} · P{s['page']}",
                        "role": "正文关键段落。",
                        "plain_explanation": s["text"][:220],
                        "key_takeaways": [],
                        "terms": [],
                    },
                )

    (paper_dir / "analysis.json").write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if progress_cb:
        progress_cb(100, "AI 深度剖析完成！")
    return analysis
