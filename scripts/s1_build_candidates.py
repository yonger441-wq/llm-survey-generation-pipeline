"""Stage 1: Build candidate papers for each section.

For each section, extract keywords from title/sub-items, retrieve a wide
candidate pool, inject classic papers with section-type-aware caps, compute the
section budget, and write candidates.csv.

Usage:
    python scripts/s1_build_candidates.py [--chapter N] [--section X.Y] [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

from citation_growth_utils import (
    classify_section,
    extract_cited_bibkeys,
    find_section_dirs,
    load_section_info,
    load_selected_rows,
)
from llm_utils import load_config, resolve_path

CANDIDATE_FIELDS = [
    "uid", "bibkey", "title", "year", "citation_count",
    "authors", "abstract", "match_score", "is_injected",
]


def load_paper_pool(path: Path) -> list[dict]:
    """Load papers_master.csv into memory."""
    papers = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["citation_count"] = int(row.get("citation_count", "0") or "0")
            row["year"] = row.get("year", "").strip()
            row["title"] = row.get("title", "").strip()
            row["abstract"] = row.get("abstract", "").strip()
            row["bibkey"] = row.get("bibkey", "").strip()
            row["uid"] = row.get("uid", "").strip()
            papers.append(row)
    return papers


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase keywords."""
    stopwords = {
        "a", "an", "the", "and", "or", "of", "in", "for", "to", "with",
        "on", "at", "by", "from", "as", "is", "are", "was", "were", "be",
        "been", "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "can", "shall", "not",
        "but", "this", "that", "these", "those", "it", "its", "their", "they",
        "we", "our", "which", "what", "how", "when", "where", "who", "all",
        "each", "every", "both", "few", "more", "most", "other", "some",
        "such", "no", "only", "same", "so", "than", "too", "very", "just",
        "also", "into", "over", "after", "before", "between", "through",
        "during", "without", "about", "against", "up", "out", "if", "then",
        "vs", "vs.", "including", "across", "new", "using", "based",
    }
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", text.lower())
    return [token for token in tokens if len(token) >= 3 and token not in stopwords]


def normalize_phrase(text: str) -> str:
    return " ".join(tokenize(text))


def extract_keywords(section_info: dict) -> list[str]:
    """Extract de-duplicated keywords from title and sub-items."""
    words = []
    words.extend(tokenize(section_info["title"]))
    for item in section_info.get("sub_items", []):
        words.extend(tokenize(item["title"]))
    seen = set()
    deduped = []
    for word in words:
        if word not in seen:
            seen.add(word)
            deduped.append(word)
    return deduped


def extract_phrases(section_info: dict) -> list[str]:
    """Extract meaningful title phrases for phrase matching."""
    phrases = []
    title_phrase = normalize_phrase(section_info["title"])
    if title_phrase and len(title_phrase.split()) >= 2:
        phrases.append(title_phrase)
    for item in section_info.get("sub_items", []):
        phrase = normalize_phrase(item["title"])
        if phrase and len(phrase.split()) >= 2:
            phrases.append(phrase)
    return phrases


def match_papers(
    papers: list[dict],
    keywords: list[str],
    phrases: list[str],
    year_min: int = 2018,
    year_max: int = 2026,
) -> list[dict]:
    """Retrieve and score papers with a section-aware ranking function."""
    provisional = []
    for paper in papers:
        try:
            year = int(paper["year"])
        except (ValueError, TypeError):
            continue
        if year < year_min or year > year_max:
            continue

        title_text = paper["title"].lower()
        abstract_text = paper["abstract"].lower()
        title_hits = [kw for kw in keywords if kw in title_text]
        abstract_hits = [kw for kw in keywords if kw not in title_hits and kw in abstract_text]
        phrase_hits = [phrase for phrase in phrases if phrase and phrase in title_text]
        if not title_hits and not abstract_hits and not phrase_hits:
            continue
        provisional.append({
            "paper": paper,
            "title_hits": title_hits,
            "abstract_hits": abstract_hits,
            "phrase_hits": phrase_hits,
        })

    keyword_df = Counter()
    for item in provisional:
        matched_keywords = set(item["title_hits"]) | set(item["abstract_hits"])
        for keyword in matched_keywords:
            keyword_df[keyword] += 1

    results = []
    for item in provisional:
        paper = dict(item["paper"])
        rarity_bonus = sum(1.0 / max(keyword_df.get(keyword, 1), 1) for keyword in item["title_hits"])
        rarity_bonus += sum(0.5 / max(keyword_df.get(keyword, 1), 1) for keyword in item["abstract_hits"])
        phrase_bonus = 8 * len(item["phrase_hits"])
        title_bonus = 3 * len(item["title_hits"])
        abstract_bonus = 1 * len(item["abstract_hits"])
        citation_bonus = min(paper["citation_count"], 500) / 500.0
        score = phrase_bonus + title_bonus + abstract_bonus + rarity_bonus + citation_bonus
        paper["match_score"] = round(score, 4)
        paper["is_injected"] = "false"
        results.append(paper)

    results.sort(
        key=lambda paper: (
            float(paper["match_score"]),
            int(paper["citation_count"]),
            int(paper["year"] or 0),
        ),
        reverse=True,
    )
    return results


def inject_top_cited(
    papers: list[dict],
    matched: list[dict],
    keywords: list[str],
    phrases: list[str],
    k: int = 15,
    min_citations: int = 50,
) -> list[dict]:
    """Inject top-cited classic papers with section-aware keyword matching."""
    matched_bibkeys = {paper["bibkey"] for paper in matched}
    injected_candidates = []
    for paper in papers:
        if paper["bibkey"] in matched_bibkeys or paper["citation_count"] < min_citations:
            continue
        title_text = paper["title"].lower()
        abstract_text = paper["abstract"].lower()
        title_hits = [kw for kw in keywords if kw in title_text]
        abstract_hits = [kw for kw in keywords if kw in abstract_text]
        phrase_hit = any(phrase and phrase in title_text for phrase in phrases)
        if not title_hits and not abstract_hits and not phrase_hit:
            continue
        injected_candidates.append({
            "paper": paper,
            "score": (
                1 if phrase_hit else 0,
                len(title_hits),
                len(abstract_hits),
                paper["citation_count"],
                int(paper["year"] or 0),
            ),
        })

    injected_candidates.sort(key=lambda item: item["score"], reverse=True)
    for item in injected_candidates[:k]:
        paper = dict(item["paper"])
        paper["match_score"] = 0
        paper["is_injected"] = "true"
        matched.append(paper)
    return matched


def compute_budget(sub_item_count: int, candidate_pool_size: int, cfg: dict) -> int:
    """Compute the budget with clamp."""
    budget_cfg = cfg["budget"]
    raw = budget_cfg["base"] + budget_cfg["alpha"] * sub_item_count + budget_cfg["beta"] * candidate_pool_size
    return max(budget_cfg["min"], min(budget_cfg["max"], int(raw)))


def _current_section_growth_signals(sec_dir: Path) -> dict:
    selected_path = sec_dir / "selected.csv"
    final_path = sec_dir / "final.md"
    selected_keys = set()
    cited_keys = set()
    if selected_path.exists():
        selected_keys = {
            row.get("bibkey", "").strip()
            for row in load_selected_rows(selected_path)
            if row.get("bibkey", "").strip()
        }
    if final_path.exists():
        cited_keys = extract_cited_bibkeys(final_path.read_text(encoding="utf-8"))
    cited_selected = cited_keys & selected_keys
    selected_count = len(selected_keys)
    cited_count = len(cited_selected)
    rate = cited_count / selected_count if selected_count else 0.0
    return {
        "selected": selected_count,
        "cited": cited_count,
        "rate": rate,
        "potential_gain": max(selected_count - cited_count, 0),
    }


def save_candidates(candidates: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CANDIDATE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(candidates)


def save_section_info(section_dir: Path, info: dict) -> None:
    (section_dir / "section_info.json").write_text(
        json.dumps(info, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def update_manifest(sections_dir: Path, section_id: str) -> None:
    manifest_path = sections_dir / "sections_manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest:
        if entry["section"] == section_id:
            entry["status"]["s1_candidates"] = "done"
            break
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run(
    chapter: int | None = None,
    section: str | None = None,
    dry_run: bool = False,
    cfg: dict | None = None,
) -> dict:
    """Execute candidate building."""
    cfg = cfg or load_config()
    sections_dir = resolve_path(cfg, "sections_dir")
    paper_pool_path = resolve_path(cfg, "paper_pool")
    retrieval_cfg = cfg.get("retrieval", {})
    injection_cfg = cfg["injection"]
    growth_cfg = cfg.get("growth", {})

    if not sections_dir.exists():
        raise FileNotFoundError(f"Sections directory not found: {sections_dir}")

    print(f"Loading paper pool from {paper_pool_path}...")
    papers = load_paper_pool(paper_pool_path)
    print(f"Loaded {len(papers)} papers")

    section_dirs = find_section_dirs(sections_dir, chapter, section)
    if not section_dirs:
        raise ValueError("No matching sections found")

    stats = {"sections_processed": 0, "total_budget": 0, "total_candidates": 0}
    section_data = []

    for sec_dir in section_dirs:
        info = load_section_info(sec_dir)
        section_type = classify_section(info, cfg)
        keywords = extract_keywords(info)
        phrases = extract_phrases(info)

        if dry_run:
            print(f"\n  {info['section']} {info['title']} ({section_type})")
            print(f"    Keywords ({len(keywords)}): {', '.join(keywords[:15])}{'...' if len(keywords) > 15 else ''}")
            print(f"    Phrases ({len(phrases)}): {', '.join(phrases[:4])}{'...' if len(phrases) > 4 else ''}")
            stats["sections_processed"] += 1
            continue

        matched = match_papers(
            papers,
            keywords,
            phrases,
            year_min=retrieval_cfg.get("year_min", 2018),
            year_max=retrieval_cfg.get("year_max", 2026),
        )

        injection_top_k = (
            injection_cfg.get("meta_top_k", injection_cfg.get("top_k", 15))
            if section_type == "meta"
            else injection_cfg.get("technical_top_k", injection_cfg.get("top_k", 15))
        )
        matched = inject_top_cited(
            papers,
            matched,
            keywords,
            phrases,
            k=injection_top_k,
            min_citations=injection_cfg["min_citation_threshold"],
        )

        sub_item_count = len(info.get("sub_items", []))
        growth_signals = _current_section_growth_signals(sec_dir)
        estimated_budget = compute_budget(sub_item_count, len(matched), cfg)
        overselect_factor = retrieval_cfg.get("overselect_factor", 3)
        high_gain = growth_signals["potential_gain"] >= growth_cfg.get("high_gain_gap_threshold", 50)
        if high_gain:
            overselect_factor = retrieval_cfg.get("high_gain_overselect_factor", overselect_factor)
        low_coverage_needs_expand = (
            growth_signals["selected"] > 0
            and growth_signals["rate"] < growth_cfg.get("high_gain_rate_threshold", 0.8)
            and growth_signals["selected"] < growth_cfg.get("high_gain_selected_threshold", 140)
        )
        if low_coverage_needs_expand:
            estimated_budget = max(
                estimated_budget,
                min(
                    growth_cfg.get("low_coverage_expand_budget_max", 156),
                    max(
                        growth_cfg.get("low_coverage_expand_budget_min", 145),
                        growth_signals["selected"],
                    ),
                ),
            )
        over_select = max(estimated_budget * overselect_factor, estimated_budget)
        if len(matched) > over_select:
            injected = [paper for paper in matched if paper["is_injected"] == "true"]
            non_injected = [paper for paper in matched if paper["is_injected"] != "true"]
            keep_non_injected = max(over_select - len(injected), 0)
            matched = injected + non_injected[:keep_non_injected]

        save_candidates(matched, sec_dir / "candidates.csv")
        section_data.append({
            "dir": sec_dir,
            "info": info,
            "matched_count": len(matched),
            "sub_item_count": sub_item_count,
            "section_type": section_type,
            "growth_signals": growth_signals,
            "estimated_budget": estimated_budget,
        })
        stats["sections_processed"] += 1
        stats["total_candidates"] += len(matched)

    if dry_run:
        return stats

    total_budget = 0
    for item in section_data:
        item["budget"] = max(
            item.get("estimated_budget", 0),
            compute_budget(item["sub_item_count"], item["matched_count"], cfg),
        )
        total_budget += item["budget"]

    budget_cfg = cfg["budget"]
    target = budget_cfg["target_total"]
    tolerance = budget_cfg["tolerance_pct"] / 100.0
    if chapter is None and section is None and total_budget > 0 and abs(total_budget - target) / target > tolerance:
        scale = target / total_budget
        print(f"Total budget {total_budget} deviates from target {target} by >{budget_cfg['tolerance_pct']}%")
        print(f"Scaling by factor {scale:.4f}")
        total_budget = 0
        for item in section_data:
            item["budget"] = max(
                budget_cfg["min"],
                min(budget_cfg["max"], int(item["budget"] * scale)),
            )
            total_budget += item["budget"]

    for item in section_data:
        info = item["info"]
        info["budget"] = item["budget"]
        info["section_type"] = item["section_type"]
        info["growth_signals"] = item["growth_signals"]
        save_section_info(item["dir"], info)
        update_manifest(sections_dir, info["section"])
        with (item["dir"] / "candidates.csv").open("r", encoding="utf-8-sig", newline="") as f:
            injected_count = sum(1 for row in csv.DictReader(f) if row.get("is_injected") == "true")
        print(
            f"  {info['section']} {info['title']}: {item['matched_count']} candidates "
            f"({injected_count} injected, {item['section_type']}), budget={item['budget']}, "
            f"potential_gain={item['growth_signals']['potential_gain']}"
        )

    stats["total_budget"] = total_budget
    print(f"\nTotal budget: {total_budget}")
    return stats


def main():
    parser = argparse.ArgumentParser(description="Stage 1: Build candidate papers")
    parser.add_argument("--chapter", type=int, default=None, help="Only process chapter N")
    parser.add_argument("--section", type=str, default=None, help="Only process section X.Y")
    parser.add_argument("--dry-run", action="store_true", help="Show keywords without processing")
    args = parser.parse_args()

    stats = run(chapter=args.chapter, section=args.section, dry_run=args.dry_run)
    if args.dry_run:
        print(f"\n[DRY RUN] Would process {stats['sections_processed']} sections")
    else:
        print(f"\nProcessed {stats['sections_processed']} sections")
        print(f"Total candidates: {stats['total_candidates']}")
        print(f"Total budget: {stats['total_budget']}")


if __name__ == "__main__":
    main()
