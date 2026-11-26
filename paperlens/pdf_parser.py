"""Deterministic PDF parser: layout-aware slicing, paragraph screenshots, figures, references & links.

Uses Poppler (`pdftotext -bbox-layout` and `pdftoppm`) + Pillow so it runs reliably
across Python versions without fragile native bindings.
"""

from __future__ import annotations

import json
import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from PIL import Image

NS = {"x": "http://www.w3.org/1999/xhtml"}

SECTION_PATTERNS = [
    ("abstract", re.compile(r"^(?:ABSTRACT)\s*:?", re.I)),
    ("introduction", re.compile(r"^(?:■\s*)?(?:\d+\.?\s*)?(?:INTRODUCTION)\b", re.I)),
    (
        "methods",
        re.compile(
            r"^(?:■\s*)?(?:\d+\.?\s*)?(?:MATERIALS?\s+AND\s+METHODS?|METHODS?|EXPERIMENTAL(?:\s+SECTION)?)\b",
            re.I,
        ),
    ),
    (
        "results",
        re.compile(
            r"^(?:■\s*)?(?:\d+\.?\s*)?(?:RESULTS?(?:\s+AND\s+DISCUSSION)?|DISCUSSION)\b",
            re.I,
        ),
    ),
    (
        "conclusions",
        re.compile(r"^(?:■\s*)?(?:\d+\.?\s*)?(?:CONCLUSIONS?|SUMMARY)\b", re.I),
    ),
    (
        "associated",
        re.compile(
            r"^(?:■\s*)?(?:ASSOCIATED\s+CONTENT|SUPPORTING\s+INFORMATION|DATA\s+AVAILABILITY|AUTHOR\s+INFORMATION|ACKNOWLEDGMENTS?)\b",
            re.I,
        ),
    ),
    ("references", re.compile(r"^(?:■\s*)?(?:REFERENCES?|BIBLIOGRAPHY)\b", re.I)),
]

CAPTION_RE = re.compile(r"^(Figure|Fig\.|Table|Scheme)\s+(\d+[A-Za-z]?)\s*[.:]\s*", re.I)
URL_RE = re.compile(r"https?://[^\s\)\],;\"'<>]+", re.I)
GITHUB_RE = re.compile(r"https?://(?:www\.)?github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)", re.I)
DOI_RE = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)\b")


@dataclass
class RawBlock:
    page: int
    x0: float
    y0: float
    x1: float
    y1: float
    page_w: float
    page_h: float
    text: str
    lines: list[dict[str, Any]]
    avg_line_h: float


def _clean_text(text: str) -> str:
    # Fix soft hyphens and join hyphenated line-breaks cleanly
    text = text.replace("\u00ad", "").replace("\ufb01", "fi").replace("\ufb02", "fl")
    text = re.sub(r"-\s*\n\s*", "", text)
    # Rejoin URLs wrapped across lines after '/', '.', or '-'
    text = re.sub(r"(https?://\S*[/.\-])\s*\n\s*(\S+)", r"\1\2", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Second pass in case a URL broke right after https://
    text = re.sub(r"(https?://)\s+([A-Za-z0-9_.-]+)", r"\1\2", text)
    text = re.sub(r"(https?://[A-Za-z0-9_.-]+/)\s+([A-Za-z0-9_./?=&%-]+)", r"\1\2", text)
    text = re.sub(r"(https?://[A-Za-z0-9_-]+\.)\s+([A-Za-z0-9_./?=&%-]+)", r"\1\2", text)
    return text


def _is_margin_noise(b: RawBlock) -> bool:
    w, h = b.page_w, b.page_h
    txt = b.text.strip()
    if not txt:
        return True
    # Vertical sidebar watermark (e.g., ACS "Downloaded from pubs.acs.org ...")
    if b.x0 > w * 0.90 or b.x1 < w * 0.05:
        return True
    if "Downloaded from" in txt or "pubs.acs.org/Biomac" in txt:
        return True
    # Header / footer running lines
    if b.y1 < h * 0.075 and len(txt) < 120:
        return True
    if b.y0 > h * 0.925 and len(txt) < 180:
        return True
    # License / page number / received-accepted metadata box
    if re.match(r"^\d{1,5}$", txt):
        return True
    if re.match(r"^(Received|Revised|Accepted|Published|Cite This|ACCESS|Metrics|Open Access|This article is licensed)", txt, re.I):
        return True
    return False


def _detect_column(b: RawBlock) -> int:
    """Return 0 for full-width, 1 for left column, 2 for right column."""
    mid = b.page_w / 2.0
    width = b.x1 - b.x0
    if width > b.page_w * 0.56:
        return 0
    center = (b.x0 + b.x1) / 2.0
    return 1 if center < mid else 2


_ILLEGAL_XML_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f\ud800-\udfff\ufffe\uffff]")
_STRAY_AMP_RE = re.compile(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)")


def _sanitize_poppler_xml(xml_str: str) -> str:
    """Strip illegal XML 1.0 control chars & fix stray ampersands emitted by Poppler on math/symbol fonts."""
    cleaned = _ILLEGAL_XML_RE.sub("", xml_str)
    cleaned = _STRAY_AMP_RE.sub("&amp;", cleaned)
    return cleaned


def parse_bbox_xml(pdf_path: Path) -> tuple[list[dict[str, Any]], list[RawBlock]]:
    """Extract all text blocks with exact coordinates via `pdftotext -bbox-layout`."""
    res = subprocess.run(
        ["pdftotext", "-bbox-layout", str(pdf_path), "-"],
        capture_output=True,
        text=True,
        errors="replace",
        check=True,
    )
    root = ET.fromstring(_sanitize_poppler_xml(res.stdout))
    pages_meta: list[dict[str, Any]] = []
    blocks: list[RawBlock] = []

    for p_idx, page_el in enumerate(root.findall(".//x:page", NS), start=1):
        pw = float(page_el.attrib["width"])
        ph = float(page_el.attrib["height"])
        pages_meta.append({"page": p_idx, "width": pw, "height": ph})

        for blk in page_el.findall(".//x:block", NS):
            x0 = float(blk.attrib["xMin"])
            y0 = float(blk.attrib["yMin"])
            x1 = float(blk.attrib["xMax"])
            y1 = float(blk.attrib["yMax"])
            lines_data = []
            line_texts = []
            heights = []
            for ln in blk.findall("x:line", NS):
                lx0 = float(ln.attrib["xMin"])
                ly0 = float(ln.attrib["yMin"])
                lx1 = float(ln.attrib["xMax"])
                ly1 = float(ln.attrib["yMax"])
                words = [w.text or "" for w in ln.findall("x:word", NS)]
                lt = " ".join(w for w in words if w)
                if lt.strip():
                    line_texts.append(lt)
                    heights.append(ly1 - ly0)
                    lines_data.append(
                        {"x0": lx0, "y0": ly0, "x1": lx1, "y1": ly1, "text": lt}
                    )
            if not line_texts:
                continue
            joined = "\n".join(line_texts)
            avg_h = sum(heights) / len(heights) if heights else 9.0
            blocks.append(
                RawBlock(
                    page=p_idx,
                    x0=x0,
                    y0=y0,
                    x1=x1,
                    y1=y1,
                    page_w=pw,
                    page_h=ph,
                    text=_clean_text(joined),
                    lines=lines_data,
                    avg_line_h=avg_h,
                )
            )
    return pages_meta, blocks


def render_pages(pdf_path: Path, pages_dir: Path, dpi: int = 180) -> dict[int, Path]:
    """Render all PDF pages to PNG via pdftoppm."""
    pages_dir.mkdir(parents=True, exist_ok=True)
    prefix = pages_dir / "page"
    subprocess.run(
        ["pdftoppm", "-png", "-r", str(dpi), str(pdf_path), str(prefix)],
        check=True,
    )
    rendered: dict[int, Path] = {}
    for p in sorted(pages_dir.glob("page-*.png")):
        m = re.search(r"page-(\d+)\.png$", p.name)
        if m:
            rendered[int(m.group(1))] = p
    return rendered


def _crop_pdf_box(
    page_img_path: Path,
    pdf_w: float,
    pdf_h: float,
    box: tuple[float, float, float, float],
    out_path: Path,
    pad: float = 8.0,
) -> tuple[int, int]:
    im = Image.open(page_img_path)
    iw, ih = im.size
    sx = iw / pdf_w
    sy = ih / pdf_h
    x0 = max(0, int((box[0] - pad) * sx))
    y0 = max(0, int((box[1] - pad) * sy))
    x1 = min(iw, int((box[2] + pad) * sx))
    y1 = min(ih, int((box[3] + pad) * sy))
    if x1 <= x0 + 4 or y1 <= y0 + 4:
        x0, y0, x1, y1 = 0, 0, iw, ih
    cropped = im.crop((x0, y0, x1, y1))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(out_path)
    return cropped.size


def _extract_citation_numbers(text: str, max_ref: int = 120) -> list[int]:
    """Extract inline citation markers from ACS/Nature superscripts and bracket styles."""
    found: set[int] = set()
    unit_follow = re.compile(
        r"^\s*(?:μM|uM|mM|nM|M\b|nm|mm|cm|Å|%|h\b|min|s\b|days?|weeks?|years?|°C|rpm|mL|μL|mg|g\b|L\b|N\b|mer|aa|residues?|amino|peptides?|sequences?|generations?|folds?|logs?|trials?|replicates?|donors?|strains?|bacteria|models?|features?|layers?|neurons?|sets?|plates?|well|times?|points?|to\b|and\b|or\b|of\b|×|x\b)",
        re.I,
    )
    skip_before = re.compile(
        r"(?:Figure|Fig\.|Table|Supplementary|Scheme|MAD|H37|mc\s*2|OD|IC|MIC|PC|L,|N,|A549|C18|7H|CO|H2|N2|O2|v/v|w/v|n\s*=|k\s*=|R\s*2|p\s*<|at|in|of|by|to|for|from|with|than|between|about|∼|~|≥|≤|>|<|=|\+|-)\s*$",
        re.I,
    )

    def _add_chunk(chunk: str) -> None:
        for part in re.split(r"[,;]+", chunk):
            part = part.strip()
            rng = re.match(r"^(\d{1,3})\s*[-−–]\s*(\d{1,3})$", part)
            if rng:
                a, b = int(rng.group(1)), int(rng.group(2))
                if 1 <= a <= b <= max_ref and (b - a) <= 12:
                    found.update(range(a, b + 1))
            elif part.isdigit():
                n = int(part)
                if 1 <= n <= max_ref:
                    found.add(n)

    # 1. Explicit `ref 10`, `refs 10-12`, `[1, 2]`
    for m in re.finditer(r"(?:\brefs?\.?\s*|\[)([\d,\s\-−–]+)(?:\])?", text, re.I):
        _add_chunk(m.group(1))

    # 2. ACS/Nature superscripts directly after punctuation: e.g. `bacteria. 1,2`, `template.10`, `μM. 10−13`
    for m in re.finditer(r"[.,;)]\s*(\d{1,2}(?:\s*[,−–-]\s*\d{1,2})*)(?=\s+[A-Z]|\s*$|\s*[.,;)])", text):
        tail = text[m.end() : m.end() + 20]
        if not unit_follow.match(tail):
            _add_chunk(m.group(1))

    # 3. Superscripts right after a word (before lowercase continuation or punctuation): e.g. `models 5 and`, `previously 25 for`, `assay 21 was`
    for m in re.finditer(r"(?<=[a-z]{3})\s+(\d{1,2}(?:[,−–-]\d{1,2})*)(?=\s+(?:and|was|were|is|are|for|to|that|in|on|of|with|by|from|as|has|have|used|show|shows)\b|\s*[.,;)])", text):
        head = text[max(0, m.start() - 25) : m.start()]
        tail = text[m.end() : m.end() + 20]
        if not skip_before.search(head) and not unit_follow.match(tail):
            _add_chunk(m.group(1))

    return sorted(found)


def _extract_references(ref_text: str) -> list[dict[str, Any]]:
    """Parse numbered references `(1) ... (2) ...` or `[1] ...` or `1. ...`."""
    cleaned = re.sub(r"\s+", " ", ref_text).strip()
    if not cleaned:
        return []

    # Try ACS style: (1) ... (2) ...
    matches = list(re.finditer(r"(?:^|\s)\((\d{1,3})\)\s+", cleaned))
    if len(matches) < 3:
        matches = list(re.finditer(r"(?:^|\s)\[(\d{1,3})\]\s+", cleaned))
    if len(matches) < 3:
        matches = list(re.finditer(r"(?:^|\s)(\d{1,3})\.\s+(?=[A-Z])", cleaned))

    refs: list[dict[str, Any]] = []
    seen: set[int] = set()
    for idx, m in enumerate(matches):
        num = int(m.group(1))
        if num in seen or num > 300:
            continue
        # Keep monotonic-ish sequence
        if refs and num > refs[-1]["number"] + 15:
            continue
        seen.add(num)
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(cleaned)
        raw = cleaned[start:end].strip()

        # Extract year
        year_m = re.search(r"\b(19\d{2}|20\d{2})\b", raw)
        year = int(year_m.group(1)) if year_m else None

        # Try heuristic title extraction (sentence after authors ending in period before journal/year)
        title = ""
        # Strip leading "(a) " if sub-entry
        first_entry = re.split(r"\s+\(b\)\s+", raw)[0]
        first_entry_clean = re.sub(r"^\(a\)\s*", "", first_entry).strip()
        # Usually authors have semicolons or initials, followed by Title. Journal Year
        parts = re.split(r"\.\s+", first_entry_clean)
        if len(parts) >= 2:
            # Find the longest non-author segment before year
            candidates = [
                p.strip()
                for p in parts[1:]
                if len(p.strip()) > 20 and not re.match(r"^(19|20)\d{2}", p.strip())
            ]
            if candidates:
                title = candidates[0]
            else:
                title = parts[1].strip()
        if not title:
            title = first_entry_clean[:120]

        authors = parts[0].strip() if parts else ""
        doi_m = DOI_RE.search(raw)

        refs.append(
            {
                "number": num,
                "raw": raw,
                "authors": authors[:200],
                "title": title[:260],
                "year": year,
                "doi": doi_m.group(1).rstrip(".,;)") if doi_m else None,
            }
        )
    return refs


def _split_block_into_paragraphs(blk: RawBlock) -> list[dict[str, Any]]:
    """Split a tall multi-paragraph PDF text block into individual paragraphs using line indents/gaps."""
    lines = blk.lines
    if len(lines) <= 2:
        return [{"x0": blk.x0, "y0": blk.y0, "x1": blk.x1, "y1": blk.y1, "text": blk.text}]

    # Compute left baseline of the block
    xs = sorted(l["x0"] for l in lines)
    left_margin = xs[len(xs) // 4]  # robust 25th percentile left margin
    avg_h = blk.avg_line_h or 9.0

    groups: list[list[dict[str, Any]]] = [[lines[0]]]
    for prev, cur in zip(lines, lines[1:]):
        gap = cur["y0"] - prev["y1"]
        is_indented = (cur["x0"] - left_margin) > 6.5
        starts_heading = bool(
            re.match(r"^(?:■\s*)?[A-Z][A-Za-z0-9\s\-–]{2,55}\.\s+", cur["text"])
            and (is_indented or gap > avg_h * 0.45)
        )
        # Large vertical gap or clear first-line paragraph indent
        if gap > avg_h * 0.85 or (is_indented and len(groups[-1]) >= 2) or starts_heading:
            groups.append([cur])
        else:
            groups[-1].append(cur)

    # Merge tiny orphan lines (< 65 chars) unless they are headings
    merged: list[list[dict[str, Any]]] = []
    for g in groups:
        txt = _clean_text("\n".join(l["text"] for l in g))
        if (
            merged
            and len(txt) < 75
            and not any(pat.match(txt) for _, pat in SECTION_PATTERNS)
            and not CAPTION_RE.match(txt)
        ):
            merged[-1].extend(g)
        else:
            merged.append(g)

    out = []
    for g in merged:
        txt = _clean_text("\n".join(l["text"] for l in g))
        if len(txt) < 25 and not any(pat.match(txt) for _, pat in SECTION_PATTERNS):
            continue
        out.append(
            {
                "x0": min(l["x0"] for l in g),
                "y0": min(l["y0"] for l in g),
                "x1": max(l["x1"] for l in g),
                "y1": max(l["y1"] for l in g),
                "text": txt,
            }
        )
    return out


def ingest_pdf(pdf_path: Path, paper_dir: Path, paper_id: str) -> dict[str, Any]:
    """Run complete deterministic PDF parsing, figure/table detection, paragraph slicing & cropping."""
    paper_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = paper_dir / "assets"
    pages_dir = assets_dir / "pages"
    slices_dir = assets_dir / "slices"
    figs_dir = assets_dir / "figures"

    # Copy PDF if not already at source.pdf
    target_pdf = paper_dir / "source.pdf"
    if pdf_path.resolve() != target_pdf.resolve():
        target_pdf.write_bytes(pdf_path.read_bytes())

    pages_meta, raw_blocks = parse_bbox_xml(target_pdf)
    rendered_pages = render_pages(target_pdf, pages_dir, dpi=180)
    page_dims = {p["page"]: (p["width"], p["height"]) for p in pages_meta}

    # 1. Extract title & authors from Page 1 top blocks
    p1_blocks = [b for b in raw_blocks if b.page == 1 and not _is_margin_noise(b)]
    title = paper_id
    authors_text = ""

    top_candidates = [b for b in p1_blocks if b.y0 < 185 and len(b.text) > 15]
    if top_candidates:
        title_blk = max(top_candidates, key=lambda b: (b.avg_line_h, -b.y0))
        title = title_blk.text
        author_cands = [
            b
            for b in p1_blocks
            if b.y0 >= title_blk.y1 - 2
            and b.y0 < 235
            and len(b.text) > 18
            and not re.match(r"^(Cite This|ACCESS|ABSTRACT)", b.text, re.I)
        ]
        if author_cands:
            authors_text = " ".join(b.text for b in sorted(author_cands, key=lambda x: x.y0))

    # 2. Identify Figures & Tables across all pages
    figures: list[dict[str, Any]] = []
    figure_regions_by_page: dict[int, list[tuple[float, float, float, float]]] = {}

    for p_info in pages_meta:
        p = p_info["page"]
        pw, ph = p_info["width"], p_info["height"]
        p_blocks = [b for b in raw_blocks if b.page == p and not _is_margin_noise(b)]

        # Find caption blocks
        for b in p_blocks:
            m = CAPTION_RE.match(b.text)
            if not m:
                continue
            kind = m.group(1).lower()
            num = m.group(2)
            fig_id = f"{'table' if 'table' in kind else 'fig'}-{num}"
            # Avoid duplicates
            if any(f["id"] == fig_id for f in figures):
                continue

            if "table" in kind:
                # Table caption is typically ABOVE the table; collect table blocks below it until next body paragraph or gap
                x0 = min(b.x0, pw * 0.08)
                x1 = max(b.x1, pw * 0.92)
                y0 = b.y0 - 4
                # Find lowest block belonging to table / footnotes above main 2-col body
                table_bottom = b.y1 + 20
                for ob in sorted(p_blocks, key=lambda item: item.y0):
                    if ob.y0 <= b.y1 - 2:
                        continue
                    # Footnote lines start with italic superscript letters aRF = ... or span full width
                    if _detect_column(ob) == 0 or ob.y0 < ph * 0.48:
                        # Stop if a 2-col narrative block starts well below
                        if _detect_column(ob) != 0 and len(ob.text) > 180 and ob.y0 > ph * 0.42:
                            break
                        table_bottom = max(table_bottom, ob.y1)
                y1 = min(ph * 0.92, table_bottom + 6)
            else:
                # Figure graphic is typically ABOVE its caption (top of page down to caption bottom)
                # Find lowest body block above the figure (if figure is mid-page) or start from top margin
                x0 = min(b.x0, pw * 0.08)
                x1 = max(b.x1, pw * 0.92)
                y1 = b.y1 + 4
                y0 = ph * 0.068  # top content margin
                # Check if there is full-width body text well above caption
                for ob in p_blocks:
                    if ob.y1 < b.y0 - 140 and len(ob.text) > 250 and not CAPTION_RE.match(ob.text):
                        # Figure is in the lower half of the page
                        y0 = max(y0, ob.y1 + 6)

            box = (x0, y0, x1, y1)
            figure_regions_by_page.setdefault(p, []).append(box)
            out_img = figs_dir / f"{fig_id}.png"
            _crop_pdf_box(rendered_pages[p], pw, ph, box, out_img, pad=6)

            figures.append(
                {
                    "id": fig_id,
                    "label": f"{m.group(1).capitalize()} {num}",
                    "kind": "table" if "table" in kind else "figure",
                    "page": p,
                    "caption": b.text,
                    "image": f"assets/figures/{fig_id}.png",
                    "bbox": list(box),
                }
            )

    # 3. Extract body slices in true reading order (Page -> Full-width top -> Left col -> Right col)
    slices: list[dict[str, Any]] = []
    ref_blocks_text: list[str] = []
    all_urls: set[str] = set()
    all_dois: set[str] = set()
    github_repos: set[str] = set()

    current_section = "abstract"
    in_references = False
    slice_counter = 0

    for p_info in pages_meta:
        p = p_info["page"]
        pw, ph = p_info["width"], p_info["height"]
        p_blocks = [b for b in raw_blocks if b.page == p and not _is_margin_noise(b)]

        # Collect URLs & DOIs from every block on the page
        for b in p_blocks:
            for u in URL_RE.findall(b.text):
                clean_u = u.rstrip(".,;)")
                all_urls.add(clean_u)
                gm = GITHUB_RE.match(clean_u)
                if gm:
                    github_repos.add(gm.group(1).rstrip(".,;)"))
            for d in DOI_RE.findall(b.text):
                all_dois.add(d.rstrip(".,;)"))

        # Filter out blocks that fall inside already-captured Figure/Table regions
        fig_boxes = figure_regions_by_page.get(p, [])
        body_blocks: list[RawBlock] = []
        for b in p_blocks:
            cy = (b.y0 + b.y1) / 2.0
            cx = (b.x0 + b.x1) / 2.0
            inside_fig = any(
                (fx0 - 5 <= cx <= fx1 + 5 and fy0 - 5 <= cy <= fy1 + 5)
                for (fx0, fy0, fx1, fy1) in fig_boxes
            )
            if inside_fig:
                continue
            # Skip title & author header blocks on page 1
            if p == 1 and b.y1 < 245:
                continue
            body_blocks.append(b)

        # Separate page-1 Abstract (top half) from 2-col body
        ordered_blocks: list[RawBlock] = []
        if p == 1:
            abs_blocks = [
                b
                for b in body_blocks
                if b.y0 < ph * 0.52
                and not re.match(r"^(Article Recommendations|\*?\s*Supporting Information|sı)", b.text, re.I)
            ]
            rest = [b for b in body_blocks if b.y0 >= ph * 0.52]
            if abs_blocks:
                # Merge abstract blocks into one clean abstract slice (including TOC graphic to the right!)
                ax0 = min(b.x0 for b in abs_blocks)
                ay0 = min(b.y0 for b in abs_blocks)
                ax1 = max(max(b.x1 for b in abs_blocks), pw * 0.92)
                ay1 = max(b.y1 for b in abs_blocks)
                abstract_text = " ".join(
                    b.text for b in sorted(abs_blocks, key=lambda x: (round(x.y0 / 12), x.x0))
                )
                # Strip TOC graphic label words if mixed in
                abstract_text = re.sub(
                    r"\b(?:Sequence Seed|Mutation & Crossover|Biophysical Parameterization|Random Forest|Neural Network|MIC Determination & Selection)\b",
                    "",
                    abstract_text,
                )
                abstract_text = re.sub(r"\s+", " ", abstract_text).strip()
                slice_counter += 1
                sid = f"S{slice_counter:02d}"
                img_path = slices_dir / f"{sid}.png"
                _crop_pdf_box(rendered_pages[p], pw, ph, (ax0, ay0, ax1, ay1), img_path, pad=10)
                slices.append(
                    {
                        "id": sid,
                        "index": slice_counter,
                        "page": p,
                        "section": "abstract",
                        "section_label": "Abstract 摘要",
                        "text": abstract_text,
                        "image": f"assets/slices/{sid}.png",
                        "bbox": [ax0, ay0, ax1, ay1],
                        "refs": _extract_citation_numbers(abstract_text),
                        "linked_figures": [],
                    }
                )
            body_blocks = rest

        # Sort remaining blocks in true 2-column academic reading order:
        # Left column (col=1) top-to-bottom, then Right column (col=2) top-to-bottom;
        # Full-width blocks (col=0) sorted by vertical position relative to columns.
        left_col = sorted([b for b in body_blocks if _detect_column(b) == 1], key=lambda x: x.y0)
        right_col = sorted([b for b in body_blocks if _detect_column(b) == 2], key=lambda x: x.y0)
        full_col = sorted([b for b in body_blocks if _detect_column(b) == 0], key=lambda x: x.y0)
        ordered_blocks = full_col + left_col + right_col

        for blk in ordered_blocks:
            sub_paras = _split_block_into_paragraphs(blk)
            for para in sub_paras:
                txt = para["text"].strip()
                if not txt:
                    continue

                # Detect section transitions
                for sec_key, sec_re in SECTION_PATTERNS:
                    if sec_re.match(txt):
                        current_section = sec_key
                        if sec_key == "references":
                            in_references = True
                        break

                if in_references or current_section == "references":
                    ref_blocks_text.append(txt)
                    continue

                if current_section == "associated":
                    # Still scan for SI links / data availability but don't clutter main reading slices unless meaningful
                    if "Supporting Information" in txt or "Data Availability" in txt:
                        pass
                    else:
                        continue

                # Skip pure tiny symbols, isolated formula lines, or lone section markers
                if len(txt) < 45:
                    continue

                # Check figure/table mentions in this paragraph (excluding Supplementary Figures/Tables)
                linked_figs: list[str] = []
                for fm in re.finditer(r"(?<!Supplementary\s)\b(Figure|Fig\.|Table)\s+(\d+)", txt, re.I):
                    prefix = "table" if "table" in fm.group(1).lower() else "fig"
                    fid = f"{prefix}-{fm.group(2)}"
                    if fid not in linked_figs and any(f["id"] == fid for f in figures):
                        linked_figs.append(fid)

                slice_counter += 1
                sid = f"S{slice_counter:02d}"
                img_path = slices_dir / f"{sid}.png"
                box = (para["x0"], para["y0"], para["x1"], para["y1"])
                _crop_pdf_box(rendered_pages[p], pw, ph, box, img_path, pad=7)

                sec_labels = {
                    "abstract": "Abstract 摘要",
                    "introduction": "Introduction 引言与背景",
                    "methods": "Materials & Methods 研究方法",
                    "results": "Results & Discussion 结果与讨论",
                    "conclusions": "Conclusions 结论与局限",
                    "associated": "Associated Content 补充材料",
                }
                slices.append(
                    {
                        "id": sid,
                        "index": slice_counter,
                        "page": p,
                        "section": current_section,
                        "section_label": sec_labels.get(current_section, current_section),
                        "text": txt,
                        "image": f"assets/slices/{sid}.png",
                        "bbox": list(box),
                        "refs": _extract_citation_numbers(txt),
                        "linked_figures": linked_figs,
                    }
                )

    references = _extract_references(" ".join(ref_blocks_text))
    valid_ref_nums = {r["number"] for r in references}
    if valid_ref_nums:
        for s in slices:
            s["refs"] = [n for n in s["refs"] if n in valid_ref_nums]

    # Identify primary paper DOI (most frequent or matching pubs.acs.org / doi.org)
    primary_doi = None
    if all_dois:
        # Prefer DOI appearing on page 1
        p1_all = " ".join(b.text for b in raw_blocks if b.page == 1)
        m_p1 = DOI_RE.search(p1_all)
        primary_doi = m_p1.group(1).rstrip(".,;)") if m_p1 else sorted(all_dois)[0]

    # Classify discovered external resources
    discovered_resources = {
        "primary_doi": primary_doi,
        "github_repos": sorted(github_repos),
        "web_tools": sorted(
            u for u in all_urls if "github.com" not in u.lower() and "doi.org" not in u.lower() and "orcid.org" not in u.lower() and "pubs.acs.org/Biomac" not in u
        ),
        "si_url": f"https://doi.org/{primary_doi}" if primary_doi else None,
        "all_urls": sorted(all_urls),
    }

    manifest = {
        "paper_id": paper_id,
        "title": title,
        "authors": authors_text,
        "doi": primary_doi,
        "page_count": len(pages_meta),
        "pages": [
            {"page": p["page"], "image": f"assets/pages/page-{p['page']:02d}.png"}
            for p in pages_meta
        ],
        "slice_count": len(slices),
        "figure_count": len(figures),
        "reference_count": len(references),
        "slices": slices,
        "figures": figures,
        "references": references,
        "discovered_resources": discovered_resources,
    }

    (paper_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest
