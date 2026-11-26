"""Real-time citation tracer: resolves any [Ref #] live via Crossref, Europe PMC, and Semantic Scholar."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import httpx

from .config import load_config


def _client(timeout: float = 9.0) -> httpx.Client:
    cfg = load_config()
    proxy = (cfg.get("http_proxy") or "").strip() or None
    return httpx.Client(
        timeout=timeout,
        proxy=proxy,
        headers={"User-Agent": "PaperLens/0.1 (Academic Citation Tracer; mailto:paperlens@local)"},
        follow_redirects=True,
    )


def _strip_html(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _query_live_apis(ref_entry: dict[str, Any]) -> dict[str, Any]:
    """Query Crossref -> Europe PMC -> Semantic Scholar to fetch abstract, citations, and links."""
    title = (ref_entry.get("title") or "").strip()
    raw = (ref_entry.get("raw") or "").strip()
    doi = ref_entry.get("doi")
    query_str = title if len(title) > 18 else raw[:140]

    live: dict[str, Any] = {
        "source": None,
        "title": title,
        "authors": ref_entry.get("authors") or "",
        "year": ref_entry.get("year"),
        "venue": "",
        "doi": doi,
        "url": f"https://doi.org/{doi}" if doi else None,
        "abstract": "",
        "citation_count": None,
        "open_access_pdf": None,
        "status": "parsed_local_only",
        "error": None,
    }

    try:
        with _client(timeout=9.0) as client:
            # 1. Crossref (by DOI or bibliographic query)
            cr_item = None
            if doi:
                r = client.get(f"https://api.crossref.org/works/{doi}")
                if r.status_code == 200:
                    cr_item = r.json().get("message")
            if not cr_item and query_str:
                r = client.get(
                    "https://api.crossref.org/works",
                    params={"query.bibliographic": query_str, "rows": 1},
                )
                if r.status_code == 200:
                    items = r.json().get("message", {}).get("items", [])
                    if items:
                        cr_item = items[0]

            if cr_item:
                live["source"] = "Crossref"
                live["status"] = "live_fetched"
                live["title"] = (cr_item.get("title") or [live["title"]])[0]
                live["doi"] = cr_item.get("DOI") or live["doi"]
                if live["doi"]:
                    live["url"] = f"https://doi.org/{live['doi']}"
                live["venue"] = (cr_item.get("container-title") or [""])[0]
                live["citation_count"] = cr_item.get("is-referenced-by-count")
                if cr_item.get("abstract"):
                    live["abstract"] = _strip_html(cr_item["abstract"])[:1200]
                issued = cr_item.get("published", {}).get("date-parts", [[None]])[0]
                if issued and issued[0]:
                    live["year"] = issued[0]
                auth_list = cr_item.get("author") or []
                if auth_list:
                    live["authors"] = ", ".join(
                        f"{a.get('given', '')} {a.get('family', '')}".strip() for a in auth_list[:6]
                    ) + (" et al." if len(auth_list) > 6 else "")

            # 2. Europe PMC (great for biomedical abstracts & free PMC full-text!)
            if not live["abstract"] and (live["doi"] or title):
                q = f'DOI:"{live["doi"]}"' if live["doi"] else f'TITLE:"{title[:100]}"'
                r_epmc = client.get(
                    "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                    params={"query": q, "format": "json", "resultType": "core", "pageSize": 1},
                )
                if r_epmc.status_code == 200:
                    hits = r_epmc.json().get("resultList", {}).get("result", [])
                    if hits:
                        h = hits[0]
                        live["source"] = (live["source"] + " + Europe PMC") if live["source"] else "Europe PMC"
                        live["status"] = "live_fetched"
                        if h.get("abstractText"):
                            live["abstract"] = _strip_html(h["abstractText"])[:1200]
                        if h.get("citedByCount") is not None and live["citation_count"] is None:
                            live["citation_count"] = h.get("citedByCount")
                        if h.get("pmcid"):
                            live["open_access_pdf"] = f"https://europepmc.org/articles/{h['pmcid']}?pdf=render"
                        if not live["venue"] and h.get("journalTitle"):
                            live["venue"] = h.get("journalTitle")

            # 3. Semantic Scholar fallback for TL;DR / citation count / abstract
            if not live["abstract"] and (live["doi"] or title):
                if live["doi"]:
                    r_s2 = client.get(
                        f"https://api.semanticscholar.org/graph/v1/paper/DOI:{live['doi']}",
                        params={"fields": "title,year,venue,citationCount,abstract,openAccessPdf,tldr,url"},
                    )
                    s2_item = r_s2.json() if r_s2.status_code == 200 else None
                else:
                    r_s2 = client.get(
                        "https://api.semanticscholar.org/graph/v1/paper/search",
                        params={"query": title[:120], "limit": 1, "fields": "title,year,venue,citationCount,abstract,openAccessPdf,tldr,url"},
                    )
                    data = r_s2.json().get("data", []) if r_s2.status_code == 200 else []
                    s2_item = data[0] if data else None
                if s2_item and s2_item.get("title"):
                    live["source"] = (live["source"] + " + Semantic Scholar") if live["source"] else "Semantic Scholar"
                    live["status"] = "live_fetched"
                    if s2_item.get("abstract"):
                        live["abstract"] = s2_item["abstract"][:1200]
                    if s2_item.get("tldr", {}) and isinstance(s2_item["tldr"], dict):
                        live["tldr"] = s2_item["tldr"].get("text")
                    if s2_item.get("citationCount") is not None:
                        live["citation_count"] = s2_item["citationCount"]
                    if s2_item.get("openAccessPdf") and isinstance(s2_item["openAccessPdf"], dict):
                        live["open_access_pdf"] = s2_item["openAccessPdf"].get("url")
                    if not live["url"] and s2_item.get("url"):
                        live["url"] = s2_item["url"]
    except Exception as exc:
        live["error"] = str(exc)

    if not live["url"] and query_str:
        # Provide direct Google Scholar search link as universal fallback
        from urllib.parse import quote_plus
        live["scholar_search_url"] = f"https://scholar.google.com/scholar?q={quote_plus(query_str[:120])}"
    return live


def trace_reference(paper_dir: Path, ref_num: int, force: bool = False) -> dict[str, Any]:
    """Return rich traced info for reference #ref_num, combining local cache + live API lookup + citation context."""
    manifest = json.loads((paper_dir / "manifest.json").read_text(encoding="utf-8"))
    ref_entry = next((r for r in manifest.get("references", []) if r["number"] == ref_num), None)
    if not ref_entry:
        return {"error": f"Reference #{ref_num} not found in manifest."}

    # Find every slice in this paper that cites ref_num
    citing_slices = [
        {
            "id": s["id"],
            "page": s["page"],
            "section_label": s["section_label"],
            "excerpt": s["text"][:220] + ("..." if len(s["text"]) > 220 else ""),
        }
        for s in manifest.get("slices", [])
        if ref_num in (s.get("refs") or [])
    ]

    cache_path = paper_dir / "ref_cache.json"
    cache: dict[str, Any] = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    key = str(ref_num)
    if key in cache and not force:
        cached = dict(cache[key])
        cached["citing_slices"] = citing_slices
        cached["raw"] = ref_entry["raw"]
        return cached

    live = _query_live_apis(ref_entry)
    # Merge with pre-existing curated explanation if present
    prev = cache.get(key, {})
    merged = {
        **prev,
        **{k: v for k, v in live.items() if v not in (None, "")},
        "number": ref_num,
        "raw": ref_entry["raw"],
        "citing_slices": citing_slices,
        "traced_at": int(time.time()),
    }
    # Preserve curated Chinese explanation when live API is offline
    if prev.get("why_cited") and not merged.get("why_cited"):
        merged["why_cited"] = prev["why_cited"]
    if prev.get("plain_summary") and not merged.get("plain_summary"):
        merged["plain_summary"] = prev["plain_summary"]
    if not merged.get("scholar_search_url"):
        from urllib.parse import quote_plus
        q = merged.get("title") or ref_entry["raw"][:120]
        merged["scholar_search_url"] = f"https://scholar.google.com/scholar?q={quote_plus(q)}"

    cache[key] = merged
    cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
    return merged
