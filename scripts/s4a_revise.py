"""Stage 4a: Revise section drafts with citation verification.

Revision now targets higher final citation coverage and can run multiple
supplement rounds prioritized toward globally under-cited papers.

Usage:
    python scripts/s4a_revise.py [--chapter N] [--section X.Y] [--model MODEL] [--force]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from citation_growth_utils import (
    build_usage_counts_from_finals,
    count_citation_mentions,
    extract_cited_bibkeys,
    find_section_dirs,
    load_notes,
    load_section_info,
    load_selected_bibkeys,
)
from llm_utils import call_llm, load_config, render_prompt_file, resolve_path


def count_citations(text: str) -> tuple[int, set[str]]:
    """Count unique [@bibkey] patterns in text."""
    cited = extract_cited_bibkeys(text)
    return len(cited), cited


def filter_valid_citations(text: str, valid_bibkeys: set[str]) -> tuple[str, int]:
    """Remove citations to bibkeys not in valid_bibkeys."""
    removed = 0

    def replacer(match):
        nonlocal removed
        parts = [part.strip().lstrip("@") for part in match.group(1).split(";")]
        valid_parts = [part for part in parts if part in valid_bibkeys]
        removed += len(parts) - len(valid_parts)
        if not valid_parts:
            return ""
        return "[@" + "; @".join(valid_parts) + "]"

    cleaned = re.sub(r"\[@([^\]]+)\]", replacer, text)
    return cleaned, removed


def parse_revision_output(text: str) -> tuple[str, str]:
    """Split LLM output into (revised_text, report)."""
    lines = text.split("\n")
    last_sep_idx = -1
    for idx in range(len(lines) - 1, -1, -1):
        if lines[idx].strip() == "---":
            last_sep_idx = idx
            break
    if last_sep_idx == -1:
        return text, ""
    return "\n".join(lines[:last_sep_idx]).rstrip(), "\n".join(lines[last_sep_idx + 1:]).strip()


def compute_coverage(report: str) -> dict:
    """Parse a coverage line from a report body."""
    if not report:
        return {"cited": 0, "total": 0, "rate": 0.0}
    match = re.search(r"(\d+)\s*/\s*(\d+)\s*\((\d+)%\)", report)
    if match:
        return {
            "cited": int(match.group(1)),
            "total": int(match.group(2)),
            "rate": int(match.group(3)) / 100.0,
        }
    return {"cited": 0, "total": 0, "rate": 0.0}


def find_missing_bibkeys(text: str, all_bibkeys: list[str]) -> list[str]:
    """Find bibkeys not yet cited in text."""
    _, cited = count_citations(text)
    return [bibkey for bibkey in all_bibkeys if bibkey not in cited]


def needs_supplement(rate: float, threshold: float = 0.8) -> bool:
    return rate < threshold


def save_final(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def update_manifest(sections_dir: Path, section_id: str) -> None:
    manifest_path = sections_dir / "sections_manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest:
        if entry["section"] == section_id:
            entry["status"]["s4_final"] = "done"
            break
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_uncited_text(missing_bibkeys: list[str], notes: list[dict], global_final_usage: dict[str, int] | None = None) -> str:
    """Format uncited papers for the supplement prompt."""
    note_by_key = {note["bibkey"]: note for note in notes}
    parts = []
    for bibkey in missing_bibkeys:
        note = note_by_key.get(bibkey, {})
        parts.append(
            f"- bibkey: {bibkey}\n"
            f"  importance: {note.get('importance', 0)}\n"
            f"  global_final_use_count: {(global_final_usage or {}).get(bibkey, 0)}\n"
            f"  summary: {note.get('summary', 'No summary available.')}\n"
            f"  category: {note.get('category', 'uncategorized')}"
        )
    return "\n\n".join(parts)


def _existing_coverage_rate(final_path: Path, all_bibkeys: list[str]) -> float:
    if not final_path.exists() or not all_bibkeys:
        return 0.0
    final_bibkeys = extract_cited_bibkeys(final_path.read_text(encoding="utf-8"))
    cited = len(final_bibkeys & set(all_bibkeys))
    return cited / len(all_bibkeys)


def _extra_guidance(section_id: str, selected_count: int, current_rate: float, cfg: dict) -> str:
    growth_cfg = cfg.get("growth", {})
    focus_sections = set(growth_cfg.get("expansion_priority", []))
    selected_threshold = int(growth_cfg.get("high_gain_selected_threshold", 140))
    rate_threshold = float(growth_cfg.get("high_gain_rate_threshold", 0.8))
    if section_id not in focus_sections and not (selected_count >= selected_threshold and current_rate < rate_threshold):
        return ""
    return (
        "## Additional Editorial Guidance\n"
        "- Keep the section in three body blocks: topic synthesis, benchmark or method clusters, and additional representative studies.\n"
        "- The additional representative studies block remains part of the main text and should absorb uncited long-tail papers naturally.\n"
        "- Keep at most 2 citations per sentence, but add one synthesis sentence at the end of each major paragraph when needed.\n"
        "- Every sub-topic should integrate at least one batch of currently uncited papers before the section is considered complete.\n"
    )


def _missing_priority(bibkey: str, notes_by_key: dict[str, dict], global_final_usage: dict[str, int]) -> tuple:
    global_use = int(global_final_usage.get(bibkey, 0))
    if global_use == 0:
        priority_group = 0
    elif global_use <= 1:
        priority_group = 1
    else:
        priority_group = 2
    importance = int(notes_by_key.get(bibkey, {}).get("importance", 0) or 0)
    return (priority_group, -importance, global_use, bibkey)


def _revise_once(
    cfg: dict,
    info: dict,
    budget: int,
    draft_text: str,
    all_bibkeys: list[str],
    extra_guidance: str,
    model: str | None,
) -> str:
    prompts_dir = resolve_path(cfg, "prompts_dir") if "prompts_dir" in cfg else None
    replacements = {
        "SECTION_TITLE": info["title"],
        "SECTION_GOAL": info.get("goal", ""),
        "EXTRA_GUIDANCE": extra_guidance,
        "DRAFT_TEXT": draft_text,
        "ALL_BIBKEYS": ", ".join(f"[@{bibkey}]" for bibkey in all_bibkeys),
        "BUDGET": str(budget),
    }
    prompt = render_prompt_file("revise_prompt", replacements, prompts_dir=prompts_dir)
    return call_llm(prompt, cfg=cfg, model=model)


def _supplement_once(
    cfg: dict,
    title: str,
    existing_text: str,
    missing_batch: list[str],
    notes: list[dict],
    global_final_usage: dict[str, int],
    extra_guidance: str,
    model: str | None,
) -> str:
    prompts_dir = resolve_path(cfg, "prompts_dir") if "prompts_dir" in cfg else None
    replacements = {
        "SECTION_TITLE": title,
        "EXTRA_GUIDANCE": extra_guidance,
        "EXISTING_TEXT": existing_text,
        "MISSING_COUNT": str(len(missing_batch)),
        "UNCITED_PAPERS": build_uncited_text(missing_batch, notes, global_final_usage),
    }
    prompt = render_prompt_file("supplement_prompt", replacements, prompts_dir=prompts_dir)
    return call_llm(prompt, cfg=cfg, model=model)


def run(
    chapter: int | None = None,
    section: str | None = None,
    model: str | None = None,
    sections_dir: Path | None = None,
    force: bool = False,
) -> dict:
    """Execute revision + multi-round supplementation."""
    cfg = load_config()
    if sections_dir is None:
        sections_dir = resolve_path(cfg, "sections_dir")
    if not sections_dir.exists():
        raise FileNotFoundError(f"Sections directory not found: {sections_dir}")

    coverage_cfg = cfg.get("coverage", {})
    target_final_rate = coverage_cfg.get("target_final_rate", 0.9)
    base_max_rounds = max(1, int(coverage_cfg.get("max_supplement_rounds", 4)))
    base_batch_size = max(1, int(coverage_cfg.get("supplement_batch_size", 25)))
    section_dirs = find_section_dirs(sections_dir, chapter, section)
    if not section_dirs:
        raise ValueError("No matching sections found")

    target_section_ids = {load_section_info(sec_dir)["section"] for sec_dir in section_dirs}
    global_final_usage = build_usage_counts_from_finals(sections_dir, exclude_sections=target_section_ids)

    stats = {
        "sections_processed": 0,
        "supplemented": 0,
        "supplement_rounds": 0,
        "errors": 0,
        "low_coverage": 0,
    }

    for sec_dir in section_dirs:
        info = load_section_info(sec_dir)
        budget = info.get("budget") or 60
        section_id = info["section"]
        draft_path = sec_dir / "draft.md"
        selected_path = sec_dir / "selected.csv"
        notes_path = sec_dir / "notes.jsonl"
        final_path = sec_dir / "final.md"

        if not draft_path.exists():
            print(f"  SKIP {section_id}: no draft.md")
            continue
        if final_path.exists() and not force:
            print(f"  SKIP {section_id}: final.md already exists")
            for bibkey in extract_cited_bibkeys(final_path.read_text(encoding="utf-8")):
                global_final_usage[bibkey] = global_final_usage.get(bibkey, 0) + 1
            stats["sections_processed"] += 1
            continue

        draft_text = draft_path.read_text(encoding="utf-8")
        all_bibkeys = load_selected_bibkeys(selected_path) if selected_path.exists() else []
        notes = load_notes(notes_path) if notes_path.exists() else []
        valid_bibkeys = set(all_bibkeys)
        notes_by_key = {note["bibkey"]: note for note in notes}
        current_rate = _existing_coverage_rate(final_path, all_bibkeys)
        extra_guidance = _extra_guidance(section_id, len(all_bibkeys), current_rate, cfg)
        growth_cfg = cfg.get("growth", {})
        high_gain = (
            len(all_bibkeys) >= int(growth_cfg.get("high_gain_selected_threshold", 140))
            and current_rate < float(growth_cfg.get("high_gain_rate_threshold", 0.8))
        )
        max_rounds = base_max_rounds
        batch_size = base_batch_size
        if high_gain:
            max_rounds = max(max_rounds, int(growth_cfg.get("high_gain_max_supplement_rounds", max_rounds)))
            batch_size = min(batch_size, int(growth_cfg.get("high_gain_supplement_batch_size", batch_size)))

        print(f"\n  {section_id} {info['title']}: revising ({len(all_bibkeys)} papers)")

        try:
            raw_output = _revise_once(cfg, info, budget, draft_text, all_bibkeys, extra_guidance, model)
        except Exception as exc:
            print(f"    ERROR during revision: {exc}")
            stats["errors"] += 1
            continue

        revised_text, _ = parse_revision_output(raw_output)
        revised_text, removed = filter_valid_citations(revised_text, valid_bibkeys)
        if removed > 0:
            print(f"    Removed {removed} hallucinated citations after revision")

        revised_count, _ = count_citations(revised_text)
        revised_rate = revised_count / budget if budget > 0 else 0.0
        print(f"    Revision: {revised_count}/{budget} citations ({revised_rate:.0%})")

        rounds_used = 0
        while needs_supplement(revised_rate, target_final_rate) and notes:
            missing = find_missing_bibkeys(revised_text, all_bibkeys)
            if not missing or rounds_used >= max_rounds:
                break
            missing.sort(key=lambda bibkey: _missing_priority(bibkey, notes_by_key, global_final_usage))
            batch = missing[:batch_size]
            rounds_used += 1
            stats["supplement_rounds"] += 1
            print(f"    Supplement round {rounds_used}: targeting {len(batch)} papers")

            try:
                raw_supplement = _supplement_once(
                    cfg,
                    info["title"],
                    revised_text,
                    batch,
                    notes,
                    global_final_usage,
                    extra_guidance,
                    model,
                )
            except Exception as exc:
                print(f"    WARNING: supplement round {rounds_used} failed: {exc}")
                break

            supplemented_text, _ = parse_revision_output(raw_supplement)
            if not supplemented_text.strip():
                break
            supplemented_text, removed_after = filter_valid_citations(supplemented_text, valid_bibkeys)
            if removed_after > 0:
                print(f"    Removed {removed_after} hallucinated citations after supplement")

            supplemented_count, _ = count_citations(supplemented_text)
            supplemented_rate = supplemented_count / budget if budget > 0 else 0.0
            print(f"    After round {rounds_used}: {supplemented_count}/{budget} ({supplemented_rate:.0%})")

            if supplemented_count > revised_count or supplemented_rate > revised_rate:
                revised_text = supplemented_text
                revised_count = supplemented_count
                revised_rate = supplemented_rate
                stats["supplemented"] += 1
            else:
                print("    Supplement did not improve coverage; stopping early")
                break

        if final_path.exists():
            existing_text = final_path.read_text(encoding="utf-8")
            existing_text, existing_removed = filter_valid_citations(existing_text, valid_bibkeys)
            if existing_removed > 0:
                print(f"    Removed {existing_removed} hallucinated citations from existing final before comparison")
            existing_count, _ = count_citations(existing_text)
            existing_rate = existing_count / budget if budget > 0 else 0.0
            if existing_count > revised_count or existing_rate > revised_rate:
                print(
                    f"    Keeping stronger existing final: "
                    f"{existing_count}/{budget} ({existing_rate:.0%}) > "
                    f"{revised_count}/{budget} ({revised_rate:.0%})"
                )
                revised_text = existing_text
                revised_count = existing_count
                revised_rate = existing_rate

        if revised_rate < target_final_rate:
            stats["low_coverage"] += 1
            print(f"    WARNING: final coverage stayed below target {target_final_rate:.0%}")

        comment = (
            f"\n<!-- Final citation check: {revised_count}/{budget} papers cited "
            f"({revised_rate:.0%}); target={target_final_rate:.0%}; "
            f"supplement_rounds={rounds_used}; mentions={count_citation_mentions(revised_text)} -->\n"
        )
        save_final(revised_text.rstrip() + comment, final_path)
        update_manifest(sections_dir, section_id)

        for bibkey in extract_cited_bibkeys(revised_text):
            global_final_usage[bibkey] = global_final_usage.get(bibkey, 0) + 1

        stats["sections_processed"] += 1

    print(
        f"\nRevised {stats['sections_processed']} sections "
        f"({stats['supplemented']} improved, {stats['supplement_rounds']} supplement rounds, "
        f"{stats['low_coverage']} below target)"
    )
    return stats


def main():
    parser = argparse.ArgumentParser(description="Stage 4a: Revise section drafts")
    parser.add_argument("--chapter", type=int, default=None, help="Only process chapter N")
    parser.add_argument("--section", type=str, default=None, help="Only process section X.Y")
    parser.add_argument("--model", type=str, default=None, help="Override LLM model name")
    parser.add_argument("--force", action="store_true", help="Re-run even if final.md already exists")
    args = parser.parse_args()

    stats = run(chapter=args.chapter, section=args.section, model=args.model, force=args.force)
    print(f"\nProcessed {stats['sections_processed']} sections")
    print(f"Supplement rounds: {stats['supplement_rounds']}")
    print(f"Low coverage finals: {stats['low_coverage']}")
    if stats["errors"]:
        print(f"Errors: {stats['errors']}")


if __name__ == "__main__":
    main()
