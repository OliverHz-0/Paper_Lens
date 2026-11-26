"""PaperLens CLI: ingest PDFs, auto-fetch GitHub/SI, trace citations, export Markdown, and launch Web UI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import DATA_DIR
from .exporter import export_markdown
from .llm_analyzer import build_structural_fallback, run_llm_deep_analysis
from .pdf_parser import ingest_pdf
from .ref_tracer import trace_reference
from .resource_fetcher import fetch_all_resources
from .server import _slugify, run_server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="paperlens",
        description="PaperLens — 论文深度解剖与零基础交互式解读器 (CLI + Web)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_serve = sub.add_parser("serve", help="启动交互式论文解读 Web 应用")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8765)

    p_ing = sub.add_parser("ingest", help="解析一篇 PDF：逐段切图 + 图表提取 + 抓取 GitHub/SI + 可选 AI 解读")
    p_ing.add_argument("pdf", type=Path, help="PDF 文件路径")
    p_ing.add_argument("--paper-id", default=None, help="自定义论文 ID")
    p_ing.add_argument("--no-fetch", action="store_true", help="跳过自动抓取 GitHub/DOI/SI")
    p_ing.add_argument("--llm", action="store_true", help="同时运行 LLM 深度解读（需配置 API Key）")

    p_ref = sub.add_parser("trace-ref", help="实时溯源某篇论文的第 N 条引用文献")
    p_ref.add_argument("paper_id")
    p_ref.add_argument("ref_num", type=int)
    p_ref.add_argument("--force", action="store_true", help="忽略缓存强制重新在线检索")

    p_res = sub.add_parser("fetch-resources", help="自动抓取论文中出现的 GitHub 仓库与 DOI/SI 资源")
    p_res.add_argument("paper_id")
    p_res.add_argument("--force", action="store_true")

    p_exp = sub.add_parser("export-md", help="导出带原文截图与大白话解析的 Markdown 报告")
    p_exp.add_argument("paper_id")
    p_exp.add_argument("-o", "--output", type=Path, default=None)

    args = parser.parse_args(argv)

    if args.cmd == "serve":
        run_server(host=args.host, port=args.port)
        return 0

    if args.cmd == "ingest":
        pdf_path = args.pdf.expanduser().resolve()
        if not pdf_path.exists():
            print(f"Error: PDF not found: {pdf_path}", file=sys.stderr)
            return 1
        pid = args.paper_id or _slugify(pdf_path.name)
        pdir = DATA_DIR / pid
        print(f"[1/3] 正在解析 PDF 版面、生成逐段截图与提取图表 -> {pdir}")
        manifest = ingest_pdf(pdf_path, pdir, pid)
        print(
            f"      完成: {manifest['page_count']} 页 | {manifest['slice_count']} 段切片 | "
            f"{manifest['figure_count']} 张图表 | {manifest['reference_count']} 条引文"
        )
        if not args.no_fetch:
            print("[2/3] 正在自动抓取 GitHub 仓库与 DOI/SI 资源...")
            res = fetch_all_resources(pdir, force=True)
            print(f"      GitHub 仓库: {len(res.get('github', []))} | 在线工具: {len(res.get('web_tools', []))}")
        if args.llm:
            print("[3/3] 正在调用大模型生成零基础深度解读...")
            run_llm_deep_analysis(pdir, progress_cb=lambda p, m: print(f"      [{p:3d}%] {m}"))
        else:
            print("[3/3] 生成结构化基础视图（如需 AI 解读可加 --llm 或在 Web 端点击运行）")
            build_structural_fallback(pdir)
        print(f"\nDone! 启动阅读器：python3 -m paperlens serve  (论文 ID: {pid})")
        return 0

    if args.cmd == "trace-ref":
        pdir = DATA_DIR / args.paper_id
        traced = trace_reference(pdir, args.ref_num, force=args.force)
        print(json.dumps(traced, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "fetch-resources":
        pdir = DATA_DIR / args.paper_id
        res = fetch_all_resources(pdir, force=args.force)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "export-md":
        pdir = DATA_DIR / args.paper_id
        md = export_markdown(pdir)
        if args.output:
            args.output.write_text(md, encoding="utf-8")
            print(f"Exported to {args.output}")
        else:
            print(md)
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
