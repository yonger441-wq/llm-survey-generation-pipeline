"""Stage 2: Annotate candidate papers via LLM and select papers per section.

Selection is novelty-aware: it preserves the most important papers, enforces a
quota for globally under-used papers, and penalizes over-reused selections.

Usage:
    python scripts/s2_annotate.py [--chapter N] [--section X.Y] [--model MODEL] [--force]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from citation_growth_utils import (
    build_usage_counts_from_selected,
    classify_section,
    find_section_dirs,
    load_section_info,
    rebuild_used_papers,
)
from llm_utils import call_llm, extract_json, load_config, render_prompt_file, resolve_path

VALID_CATEGORIES = {"鏍稿績鏂规硶", "搴旂敤", "璇勪及/鍩哄噯", "鐞嗚鍒嗘瀽", "宸ュ叿/妗嗘灦", "璋冩煡/缁艰堪"}
DEFAULT_CATEGORY = "鏍稿績鏂规硶"


def build_candidate_text(candidates: list[dict]) -> str:
    """Format candidate papers for inclusion in the annotation prompt."""
    if not candidates:
        return ""
    blocks = []
    for candidate in candidates:
        blocks.append(
            f"- bibkey: {candidate.get('bibkey', '')}\n"
            f"  title: {candidate.get('title', '')}\n"
            f"  year: {candidate.get('year', '')}\n"
            f"  citation_count: {candidate.get('citation_count', '')}\n"
            f"  abstract: {candidate.get('abstract', '')}"
        )
    return "\n\n".join(blocks)


def parse_annotations(raw_text: str) -> list[dict]:
    """Parse the LLM annotation response."""
    json_str = extract_json(raw_text)
    items = json.loads(json_str)
    if not isinstance(items, list):
        raise ValueError("Expected JSON array from LLM annotation")

    results = []
    for item in items:
        if not isinstance(item, dict):
            continue
        importance = item.get("importance", 1)
        if isinstance(importance, str):
            try:
                importance = int(importance)
            except ValueError:
                importance = 1
        importance = max(1, min(5, importance))

        category = str(item.get("category", "")).strip()
        if category not in VALID_CATEGORIES:
            category = DEFAULT_CATEGORY

        results.append({
            "bibkey": str(item.get("bibkey", "")).strip(),
            "decision": str(item.get("decision", "no")).strip().lower(),
            "importance": importance,
            "category": category,
            "summary": str(item.get("summary", "")).strip(),
        })
    return results


def _safe_int(value: str | int | None, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def _selection_cfg(section_type: str, cfg: dict) -> dict:
    selection_cfg = cfg.get("selection", {})
    novelty_cfg = selection_cfg.get("novelty_quota", {})
    soft_cfg = selection_cfg.get("soft_penalty_at", {})
    hard_cfg = selection_cfg.get("hard_cap", {})
    return {
        "novelty_quota": float(novelty_cfg.get(section_type, 0.0)),
        "soft_penalty_at": int(soft_cfg.get(section_type, 4 if section_type == "technical" else 6)),
        "hard_cap": int(hard_cfg.get(section_type, 8 if section_type == "technical" else 10)),
    }


def _entry_priority(entry: dict, soft_penalty_at: int, novelty_first: bool = False) -> tuple:
    global_use = entry["_global_use_count"]
    soft_penalty = max(global_use - soft_penalty_at + 1, 0)
    novelty_flag = 1 if global_use <= 1 else 0
    priority = (
        novelty_flag if novelty_first else entry["_importance"],
        entry["_importance"] if novelty_first else novelty_flag,
        1 if entry.get("is_injected") == "true" else 0,
        -soft_penalty,
        float(entry.get("match_score", 0) or 0),
        _safe_int(entry.get("citation_count"), 0),
        _safe_int(entry.get("year"), 0),
    )
    return priority


def _prepare_entries(candidates: list[dict], annotations: list[dict], usage_counts: dict[str, int], cfg: dict, section_type: str) -> list[dict]:
    """Attach annotation and global-usage metadata to candidates."""
    candidate_by_key = {candidate["bibkey"]: candidate for candidate in candidates}
    selection_cfg = _selection_cfg(section_type, cfg)
    entries = []
    for annotation in annotations:
        if annotation["decision"] != "yes" or annotation["bibkey"] not in candidate_by_key:
            continue
        entry = dict(candidate_by_key[annotation["bibkey"]])
        entry["_importance"] = annotation["importance"]
        entry["_category"] = annotation["category"]
        entry["_summary"] = annotation["summary"]
        entry["_global_use_count"] = int(usage_counts.get(annotation["bibkey"], 0))
        entry["_force_keep"] = annotation["importance"] == 5 or entry.get("is_injected") == "true"
        if entry["_importance"] < 5 and entry["_global_use_count"] > selection_cfg["hard_cap"]:
            continue
        entries.append(entry)
    return entries


def _add_entry(selected: list[dict], selected_keys: set[str], entry: dict) -> bool:
    if entry["bibkey"] in selected_keys:
        return False
    selected.append(entry)
    selected_keys.add(entry["bibkey"])
    return True


def _novelty_count(selected: list[dict]) -> int:
    return sum(1 for entry in selected if entry["_global_use_count"] <= 1)


def _category_coverage(selected: list[dict]) -> dict[str, int]:
    coverage: dict[str, int] = {}
    for entry in selected:
        coverage[entry["_category"]] = coverage.get(entry["_category"], 0) + 1
    return coverage


def _trim_to_budget(selected: list[dict], budget: int, novelty_target: int, soft_penalty_at: int) -> list[dict]:
    """Trim low-value papers while protecting novelty quota and force-keeps."""
    selected = list(selected)
    while len(selected) > budget:
        category_counts = _category_coverage(selected)
        novelty_count = _novelty_count(selected)
        removable = []
        for entry in selected:
            if entry["_force_keep"]:
                continue
            if category_counts.get(entry["_category"], 0) <= 1:
                continue
            would_drop_novelty = entry["_global_use_count"] <= 1 and novelty_count - 1 < novelty_target
            if would_drop_novelty:
                continue
            removable.append(entry)
        if not removable:
            removable = [entry for entry in selected if not entry["_force_keep"]]
        if not removable:
            break
        worst = min(removable, key=lambda entry: _entry_priority(entry, soft_penalty_at, novelty_first=False))
        selected.remove(worst)
    return selected


def select_papers(
    candidates: list[dict],
    annotations: list[dict],
    budget: int,
    usage_counts: dict[str, int] | None = None,
    section_type: str = "technical",
    cfg: dict | None = None,
) -> list[dict]:
    """Select papers with a novelty-aware, budget-aware policy."""
    usage_counts = usage_counts or {}
    cfg = cfg or {}
    selection_cfg = _selection_cfg(section_type, cfg)
    entries = _prepare_entries(candidates, annotations, usage_counts, cfg, section_type)
    if not entries:
        return []

    selected: list[dict] = []
    selected_keys: set[str] = set()

    # Step 1: always preserve all importance=5 and injected papers.
    force_keep_entries = sorted(
        [entry for entry in entries if entry["_force_keep"]],
        key=lambda entry: _entry_priority(entry, selection_cfg["soft_penalty_at"], novelty_first=True),
        reverse=True,
    )
    for entry in force_keep_entries:
        _add_entry(selected, selected_keys, entry)

    # Step 2: ensure category coverage before regular filling.
    yes_categories = sorted({entry["_category"] for entry in entries})
    for category in yes_categories:
        if any(entry["_category"] == category for entry in selected):
            continue
        candidates_for_category = sorted(
            [entry for entry in entries if entry["_category"] == category],
            key=lambda entry: _entry_priority(entry, selection_cfg["soft_penalty_at"], novelty_first=True),
            reverse=True,
        )
        if candidates_for_category:
            _add_entry(selected, selected_keys, candidates_for_category[0])

    # Step 3: enforce novelty quota where possible.
    novelty_target = int(math.ceil(max(budget, 0) * selection_cfg["novelty_quota"]))
    novelty_candidates = sorted(
        [
            entry for entry in entries
            if entry["bibkey"] not in selected_keys and entry["_global_use_count"] <= 1
        ],
        key=lambda entry: _entry_priority(entry, selection_cfg["soft_penalty_at"], novelty_first=True),
        reverse=True,
    )
    while _novelty_count(selected) < novelty_target and novelty_candidates:
        _add_entry(selected, selected_keys, novelty_candidates.pop(0))

    # Step 4: fill remaining budget using importance + novelty-aware ranking.
    remaining = sorted(
        [entry for entry in entries if entry["bibkey"] not in selected_keys],
        key=lambda entry: _entry_priority(entry, selection_cfg["soft_penalty_at"], novelty_first=False),
        reverse=True,
    )
    for entry in remaining:
        if len(selected) >= budget:
            break
        _add_entry(selected, selected_keys, entry)

    selected = _trim_to_budget(selected, budget, novelty_target, selection_cfg["soft_penalty_at"])

    for entry in selected:
        entry["global_use_count_at_selection"] = str(entry["_global_use_count"])
        entry.pop("_importance", None)
        entry.pop("_category", None)
        entry.pop("_summary", None)
        entry.pop("_global_use_count", None)
        entry.pop("_force_keep", None)
    return selected


def apply_global_dedup(
    used_papers_path: Path,
    flag_threshold: int = 5,
    remove_threshold: int = 8,
) -> tuple[set[str], set[str]]:
    """Check used_papers.jsonl for over-used bibkeys."""
    if not used_papers_path.exists():
        return set(), set()

    bibkey_sections: dict[str, set[str]] = {}
    with used_papers_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            bibkey = entry.get("bibkey", "").strip()
            section_id = entry.get("section", "").strip()
            if bibkey and section_id:
                bibkey_sections.setdefault(bibkey, set()).add(section_id)

    flagged = set()
    removed = set()
    for bibkey, sections in bibkey_sections.items():
        count = len(sections)
        if count > remove_threshold:
            removed.add(bibkey)
            flagged.add(bibkey)
        elif count > flag_threshold:
            flagged.add(bibkey)
    return flagged, removed


SELECTED_FIELDS = [
    "uid", "bibkey", "title", "year", "citation_count",
    "authors", "abstract", "match_score", "is_injected",
    "global_use_count_at_selection",
]


def write_selected(papers: list[dict], path: Path) -> None:
    """Write selected.csv."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SELECTED_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(papers)


def write_notes(annotations: list[dict], selected_bibkeys: set[str], candidates: list[dict], path: Path) -> None:
    """Write notes.jsonl for selected papers only."""
    candidate_by_key = {candidate["bibkey"]: candidate for candidate in candidates}
    annotation_by_key = {annotation["bibkey"]: annotation for annotation in annotations}
    selected_global_use = {
        row["bibkey"]: row.get("global_use_count_at_selection", "")
        for row in candidates
        if row.get("bibkey", "") in selected_bibkeys
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for bibkey in sorted(selected_bibkeys):
            annotation = annotation_by_key.get(bibkey, {})
            candidate = candidate_by_key.get(bibkey, {})
            entry = {
                "bibkey": bibkey,
                "title": candidate.get("title", ""),
                "importance": annotation.get("importance", 0),
                "category": annotation.get("category", ""),
                "summary": annotation.get("summary", ""),
                "decision": annotation.get("decision", ""),
                "global_use_count_at_selection": selected_global_use.get(bibkey, ""),
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_candidates(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def update_manifest(sections_dir: Path, section_id: str) -> None:
    manifest_path = sections_dir / "sections_manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest:
        if entry["section"] == section_id:
            entry["status"]["s2_annotate"] = "done"
            break
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _importance_dist(annotations: list[dict], selected_keys: set[str]) -> str:
    dist: dict[int, int] = {}
    for annotation in annotations:
        if annotation["bibkey"] in selected_keys:
            importance = annotation.get("importance", 0)
            dist[importance] = dist.get(importance, 0) + 1
    return ", ".join(f"{k}:{v}" for k, v in sorted(dist.items(), reverse=True)) or "none"


def _load_selected_keys(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [row.get("bibkey", "").strip() for row in csv.DictReader(f) if row.get("bibkey", "").strip()]


def run(
    chapter: int | None = None,
    section: str | None = None,
    model: str | None = None,
    sections_dir: Path | None = None,
    force: bool = False,
    cfg: dict | None = None,
) -> dict:
    """Execute annotation and novelty-aware selection."""
    cfg = cfg or load_config()
    if sections_dir is None:
        sections_dir = resolve_path(cfg, "sections_dir")
    if not sections_dir.exists():
        raise FileNotFoundError(f"Sections directory not found: {sections_dir}")

    section_dirs = find_section_dirs(sections_dir, chapter, section)
    if not section_dirs:
        raise ValueError("No matching sections found")

    target_section_ids = {load_section_info(sec_dir)["section"] for sec_dir in section_dirs}
    usage_counts = build_usage_counts_from_selected(sections_dir, exclude_sections=target_section_ids)
    dedup_cfg = cfg.get("dedup", {})
    batch_size = cfg["llm"].get("batch_size", 25)
    stats = {"sections_processed": 0, "total_selected": 0, "errors": 0, "rerun": 0}

    for sec_dir in section_dirs:
        info = load_section_info(sec_dir)
        budget = info.get("budget", 60) or 60
        section_id = info["section"]
        section_type = classify_section(info, cfg)
        selected_path = sec_dir / "selected.csv"
        notes_path = sec_dir / "notes.jsonl"

        candidates_path = sec_dir / "candidates.csv"
        if not candidates_path.exists():
            print(f"  SKIP {section_id}: no candidates.csv")
            continue

        if selected_path.exists() and notes_path.exists() and not force:
            existing_keys = _load_selected_keys(selected_path)
            for bibkey in set(existing_keys):
                usage_counts[bibkey] = usage_counts.get(bibkey, 0) + 1
            print(f"  SKIP {section_id}: already annotated")
            stats["sections_processed"] += 1
            stats["total_selected"] += len(existing_keys)
            continue

        candidates = load_candidates(candidates_path)
        print(f"\n  {section_id} {info['title']}: {len(candidates)} candidates, budget={budget}, type={section_type}")
        if force and (selected_path.exists() or notes_path.exists()):
            stats["rerun"] += 1

        annotations = []
        for start in range(0, len(candidates), batch_size):
            batch = candidates[start:start + batch_size]
            replacements = {
                "SECTION_TITLE": info["title"],
                "SECTION_GOAL": info.get("goal", ""),
                "SUB_ITEMS": json.dumps(info.get("sub_items", []), ensure_ascii=False),
                "BUDGET": str(budget),
                "CANDIDATE_PAPERS": build_candidate_text(batch),
            }
            prompts_dir = resolve_path(cfg, "prompts_dir") if "prompts_dir" in cfg else None
            prompt = render_prompt_file("annotate_prompt", replacements, prompts_dir=prompts_dir)
            try:
                raw_response = call_llm(prompt, cfg=cfg, model=model)
                batch_annotations = parse_annotations(raw_response)
                annotations.extend(batch_annotations)
                print(f"    Batch {start // batch_size + 1}: {len(batch_annotations)} annotations")
            except Exception as exc:
                print(f"    ERROR in batch {start // batch_size + 1}: {exc}")
                stats["errors"] += 1

        if not annotations:
            print("    No annotations produced, skipping selection")
            continue

        selected = select_papers(
            candidates,
            annotations,
            budget=budget,
            usage_counts=usage_counts,
            section_type=section_type,
            cfg=cfg,
        )
        selected_bibkeys = {paper["bibkey"] for paper in selected}
        write_selected(selected, selected_path)
        write_notes(annotations, selected_bibkeys, selected, notes_path)
        update_manifest(sections_dir, section_id)

        for bibkey in selected_bibkeys:
            usage_counts[bibkey] = usage_counts.get(bibkey, 0) + 1

        novelty_count = sum(
            1 for paper in selected if _safe_int(paper.get("global_use_count_at_selection"), 99) <= 1
        )
        print(
            f"    Selected {len(selected)} papers "
            f"(importance dist: {_importance_dist(annotations, selected_bibkeys)}, novelty={novelty_count})"
        )
        stats["sections_processed"] += 1
        stats["total_selected"] += len(selected)

    used_papers_path = rebuild_used_papers(sections_dir)
    flagged, removed = apply_global_dedup(
        used_papers_path,
        dedup_cfg.get("flag_threshold", 5),
        dedup_cfg.get("remove_threshold", 8),
    )
    if flagged:
        print(f"\n  Dedup: {len(flagged)} papers flagged (> {dedup_cfg.get('flag_threshold', 5)} sections)")
    if removed:
        print(f"  Dedup: {len(removed)} papers above hard cap after selection")
    return stats


def main():
    parser = argparse.ArgumentParser(description="Stage 2: Annotate and select papers")
    parser.add_argument("--chapter", type=int, default=None, help="Only process chapter N")
    parser.add_argument("--section", type=str, default=None, help="Only process section X.Y")
    parser.add_argument("--model", type=str, default=None, help="Override LLM model name")
    parser.add_argument("--force", action="store_true", help="Re-run even if selected.csv already exists")
    args = parser.parse_args()

    stats = run(chapter=args.chapter, section=args.section, model=args.model, force=args.force)
    print(f"\nProcessed {stats['sections_processed']} sections")
    print(f"Total selected: {stats['total_selected']}")
    print(f"Re-run sections: {stats['rerun']}")
    if stats["errors"]:
        print(f"Errors: {stats['errors']}")


if __name__ == "__main__":
    main()
