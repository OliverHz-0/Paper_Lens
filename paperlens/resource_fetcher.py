"""Automatic resource fetcher: GitHub repositories, DOI metadata, and Supporting Information (SI)."""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Any

import httpx

from .config import load_config


def _make_client(timeout: float = 10.0) -> httpx.Client:
    cfg = load_config()
    proxy = (cfg.get("http_proxy") or "").strip() or None
    headers = {
        "User-Agent": "PaperLens/0.1 (Academic Paper Reader; mailto:paperlens@local)",
        "Accept": "application/json",
    }
    return httpx.Client(timeout=timeout, proxy=proxy, headers=headers, follow_redirects=True)


def fetch_github_repo(repo_slug: str) -> dict[str, Any]:
    """Fetch repository metadata, root file tree, and README via GitHub REST API."""
    repo_slug = repo_slug.strip().rstrip("/")
    result: dict[str, Any] = {
        "repo": repo_slug,
        "url": f"https://github.com/{repo_slug}",
        "status": "pending",
        "fetched_at": int(time.time()),
        "description": "",
        "stars": None,
        "forks": None,
        "language": None,
        "default_branch": "main",
        "files": [],
        "readme_excerpt": "",
        "error": None,
    }
    try:
        with _make_client(timeout=10.0) as client:
            r_meta = client.get(f"https://api.github.com/repos/{repo_slug}")
            if r_meta.status_code == 200:
                meta = r_meta.json()
                result["description"] = meta.get("description") or ""
                result["stars"] = meta.get("stargazers_count")
                result["forks"] = meta.get("forks_count")
                result["language"] = meta.get("language")
                result["default_branch"] = meta.get("default_branch") or "main"
                result["updated_at"] = meta.get("updated_at")
                result["status"] = "fetched"
            else:
                result["status"] = "error"
                result["error"] = f"GitHub API HTTP {r_meta.status_code}"
                return result

            r_contents = client.get(f"https://api.github.com/repos/{repo_slug}/contents")
            if r_contents.status_code == 200 and isinstance(r_contents.json(), list):
                result["files"] = [
                    {
                        "name": f.get("name"),
                        "type": f.get("type"),
                        "size": f.get("size"),
                        "html_url": f.get("html_url"),
                    }
                    for f in r_contents.json()[:40]
                ]

            r_readme = client.get(f"https://api.github.com/repos/{repo_slug}/readme")
            if r_readme.status_code == 200:
                rd = r_readme.json()
                if rd.get("content"):
                    raw_md = base64.b64decode(rd["content"]).decode("utf-8", errors="replace")
                    result["readme_excerpt"] = raw_md[:3500]
    except Exception as exc:
        result["status"] = "offline_fallback"
        result["error"] = str(exc)
    return result


def fetch_doi_and_si(doi: str) -> dict[str, Any]:
    """Fetch DOI metadata & Supporting Information / Open Access links via Crossref + Europe PMC."""
    result: dict[str, Any] = {
        "doi": doi,
        "doi_url": f"https://doi.org/{doi}",
        "si_landing_url": f"https://pubs.acs.org/doi/suppl/{doi}" if doi.startswith("10.1021/") else f"https://doi.org/{doi}",
        "status": "pending",
        "fetched_at": int(time.time()),
        "journal": None,
        "published_date": None,
        "publisher": None,
        "is_referenced_by_count": None,
        "open_access_pdf": None,
        "pmc_id": None,
        "links": [],
        "error": None,
    }
    try:
        with _make_client(timeout=10.0) as client:
            r = client.get(f"https://api.crossref.org/works/{doi}")
            if r.status_code == 200:
                msg = r.json().get("message", {})
                result["journal"] = (msg.get("container-title") or [None])[0]
                result["publisher"] = msg.get("publisher")
                result["is_referenced_by_count"] = msg.get("is-referenced-by-count")
                issued = msg.get("published", {}).get("date-parts", [[None]])[0]
                if issued and issued[0]:
                    result["published_date"] = "-".join(str(x) for x in issued)
                result["links"] = [
                    {"url": lk.get("URL"), "content_type": lk.get("content-type")}
                    for lk in (msg.get("link") or [])[:8]
                ]
                result["status"] = "fetched"

            # Europe PMC check for free PMC full-text / supplementary files
            epmc = client.get(
                "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                params={"query": f'DOI:"{doi}"', "format": "json", "resultType": "core"},
            )
            if epmc.status_code == 200:
                hits = epmc.json().get("resultList", {}).get("result", [])
                if hits:
                    hit = hits[0]
                    result["pmc_id"] = hit.get("pmcid")
                    if hit.get("pmcid"):
                        result["open_access_pdf"] = f"https://europepmc.org/articles/{hit['pmcid']}?pdf=render"
                    if result["status"] != "fetched":
                        result["status"] = "fetched"
    except Exception as exc:
        if result["status"] != "fetched":
            result["status"] = "offline_fallback"
            result["error"] = str(exc)
    return result


def fetch_all_resources(paper_dir: Path, force: bool = False) -> dict[str, Any]:
    """Auto-fetch all GitHub repos, DOI/SI metadata, and web tools discovered in manifest.json."""
    res_path = paper_dir / "resources.json"
    if res_path.exists() and not force:
        try:
            existing = json.loads(res_path.read_text(encoding="utf-8"))
            if existing.get("github") or existing.get("doi_meta"):
                return existing
        except Exception:
            pass

    manifest = json.loads((paper_dir / "manifest.json").read_text(encoding="utf-8"))
    disc = manifest.get("discovered_resources", {})

    existing_cache = {}
    if res_path.exists():
        try:
            existing_cache = json.loads(res_path.read_text(encoding="utf-8"))
        except Exception:
            existing_cache = {}

    github_results = []
    for slug in disc.get("github_repos", []):
        fetched = fetch_github_repo(slug)
        # Preserve richer cached metadata if live fetch hit offline timeout
        if fetched["status"] == "offline_fallback":
            prev = next((g for g in existing_cache.get("github", []) if g.get("repo") == slug), None)
            if prev and prev.get("files"):
                prev["last_refresh_error"] = fetched.get("error")
                github_results.append(prev)
                continue
        github_results.append(fetched)

    doi_meta = None
    primary_doi = disc.get("primary_doi")
    if primary_doi:
        fetched_doi = fetch_doi_and_si(primary_doi)
        if fetched_doi["status"] == "offline_fallback" and existing_cache.get("doi_meta"):
            doi_meta = existing_cache["doi_meta"]
            doi_meta["last_refresh_error"] = fetched_doi.get("error")
        else:
            doi_meta = fetched_doi

    web_tools = []
    for url in disc.get("web_tools", []):
        if "pubs.acs.org" in url:
            continue
        label = url.split("//", 1)[-1].split("/")[0]
        web_tools.append({"name": label, "url": url})

    payload = {
        "fetched_at": int(time.time()),
        "github": github_results,
        "doi_meta": doi_meta,
        "web_tools": web_tools,
        "supporting_info": existing_cache.get("supporting_info")
        or (
            {
                "available": True,
                "url": (doi_meta or {}).get("si_landing_url") or disc.get("si_url"),
                "note": "可点击直达期刊 Supporting Information 页面查看完整补充表格与原始数据。",
            }
            if disc.get("si_url")
            else None
        ),
    }

    res_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload
