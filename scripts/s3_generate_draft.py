"""Stage 3: Generate section drafts using structural templates.

Draft generation now applies a stricter citation coverage gate and can retry
low-coverage drafts before handing the section to revision.

Usage:
    python scripts/s3_generate_draft.py [--chapter N] [--section X.Y] [--model MODEL] [--force]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from citation_growth_utils import extract_cited_bibkeys, find_section_dirs, load_notes, load_section_info, load_selected_bibkeys
from llm_utils import call_llm, load_config, render_prompt_file, resolve_path


def build_structural_template(section_info: dict) -> str:
    """Build the structural template from #### sub-items."""
    sub_items = section_info.get("sub_items", [])
    if not sub_items:
        return ""
    parts = []
    for item in sub_items:
        heading = f"#### {item['id']} {item['title']}"
        guide = f"-> {item.get('writing_guide', 'Cover: ' + item['title'])}"
        parts.append(f"{heading}\n{guide}")
    return "\n\n".join(parts)


def group_notes_by_category(notes: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for note in notes:
        category = note.get("category", "uncategorized")
        groups.setdefault(category, []).append(note)
    return groups


def build_paper_notes_text(groups: dict[str, list[dict]]) -> str:
    """Format grouped notes for inclusion in the draft prompt."""
    if not groups:
        return ""
    parts = []
    for category, notes in groups.items():
        entries = []
        for note in sorted(notes, key=lambda entry: entry.get("importance", 0), reverse=True):
            entries.append(
                f"- [@{note['bibkey']}] ({note.get('importance', 0)}/5): {note.get('summary', '')}"
            )
        parts.append(f"### {category}\n" + "\n".join(entries))
    return "\n\n".join(parts)


def count_citations(text: str) -> tuple[int, set[str]]:
    """Count unique [@bibkey] patterns in text."""
    bibkeys = set()
    for match in re.finditer(r"\[@([^\]]+)\]", text):
        for part in match.group(1).split(";"):
            bibkey = part.strip().lstrip("@")
            if bibkey:
                bibkeys.add(bibkey)
    return len(bibkeys), bibkeys


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


def validate_draft(text: str, budget: int, min_rate: float = 0.6) -> dict:
    """Validate draft citation count against the configured threshold."""
    count, bibkeys = count_citations(text)
    rate = count / budget if budget > 0 else 0.0
    return {
        "count": count,
        "budget": budget,
        "rate": rate,
        "bibkeys": bibkeys,
        "pass": rate >= min_rate,
    }


def save_draft(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def update_manifest(sections_dir: Path, section_id: str) -> None:
    manifest_path = sections_dir / "sections_manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest:
        if entry["section"] == section_id:
            entry["status"]["s3_draft"] = "done"
            break
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def get_section_title_by_id(sections_dir: Path, section_id: str | None) -> str:
    if section_id is None:
        return ""
    for info_path in sections_dir.rglob("section_info.json"):
        info = json.loads(info_path.read_text(encoding="utf-8"))
        if info["section"] == section_id:
            return info.get("title", "")
    return ""


def _existing_coverage_rate(final_path: Path, selected_bibkeys: list[str]) -> float:
    if not final_path.exists() or not selected_bibkeys:
        return 0.0
    final_bibkeys = extract_cited_bibkeys(final_path.read_text(encoding="utf-8"))
    cited = len(final_bibkeys & set(selected_bibkeys))
    return cited / len(selected_bibkeys)


def _extra_guidance(section_id: str, selected_count: int, current_rate: float, cfg: dict) -> str:
    growth_cfg = cfg.get("growth", {})
    focus_sections = set(growth_cfg.get("expansion_priority", []))
    selected_threshold = int(growth_cfg.get("high_gain_selected_threshold", 140))
    rate_threshold = float(growth_cfg.get("high_gain_rate_threshold", 0.8))
    if section_id not in focus_sections and not (selected_count >= selected_threshold and current_rate < rate_threshold):
        return ""
    return (
        "## Additional Editorial Guidance\n"
        "- Maintain three clear body blocks in this section: topic synthesis, benchmark or method clusters, "
        "and additional representative studies.\n"
        "- The additional representative studies block is still part of the main text and should absorb long-tail "
        "papers that do not fit naturally in the earlier synthesis paragraphs.\n"
        "- Keep the max-two-citations-per-sentence rule, but add one extra synthesis sentence at the end of each "
        "major paragraph when needed to integrate missing papers.\n"
        "- Ensure every sub-topic consumes at least one batch of currently uncited papers.\n"
    )


def _draft_attempt(
    cfg: dict,
    info: dict,
    budget: int,
    template: str,
    paper_notes: str,
    selected_bibkeys: list[str],
    extra_guidance: str,
    sections_dir: Path,
    model: str | None,
) -> tuple[str, dict, int]:
    """Run one draft generation attempt."""
    prev_title = get_section_title_by_id(sections_dir, info.get("prev_section"))
    next_title = get_section_title_by_id(sections_dir, info.get("next_section"))
    replacements = {
        "SECTION_TITLE": info["title"],
        "SECTION_GOAL": info.get("goal", ""),
        "EXTRA_GUIDANCE": extra_guidance,
        "PREV_SECTION_TITLE": prev_title,
        "NEXT_SECTION_TITLE": next_title,
        "STRUCTURAL_TEMPLATE": template,
        "PAPER_NOTES": paper_notes,
        "PAPER_COUNT": str(len(selected_bibkeys)),
    }
    prompts_dir = resolve_path(cfg, "prompts_dir") if "prompts_dir" in cfg else None
    prompt = render_prompt_file("draft_prompt", replacements, prompts_dir=prompts_dir)
    draft_text = call_llm(prompt, cfg=cfg, model=model)
    draft_text, removed = filter_valid_citations(draft_text, set(selected_bibkeys))
    validation = validate_draft(
        draft_text,
        budget=budget,
        min_rate=cfg.get("coverage", {}).get("min_draft_rate", 0.85),
    )
    return draft_text, validation, removed


def run(
    chapter: int | None = None,
    section: str | None = None,
    model: str | None = None,
    sections_dir: Path | None = None,
    force: bool = False,
) -> dict:
    """Execute draft generation."""
    cfg = load_config()
    if sections_dir is None:
        sections_dir = resolve_path(cfg, "sections_dir")
    if not sections_dir.exists():
        raise FileNotFoundError(f"Sections directory not found: {sections_dir}")

    coverage_cfg = cfg.get("coverage", {})
    min_draft_rate = coverage_cfg.get("min_draft_rate", 0.85)
    max_attempts = max(1, int(coverage_cfg.get("draft_retry_attempts", 2)))
    section_dirs = find_section_dirs(sections_dir, chapter, section)
    if not section_dirs:
        raise ValueError("No matching sections found")

    stats = {
        "sections_processed": 0,
        "total_citations": 0,
        "errors": 0,
        "low_coverage": 0,
        "retries": 0,
    }

    for sec_dir in section_dirs:
        info = load_section_info(sec_dir)
        budget = info.get("budget") or 60
        section_id = info["section"]
        notes_path = sec_dir / "notes.jsonl"
        selected_path = sec_dir / "selected.csv"
        draft_path = sec_dir / "draft.md"

        if not notes_path.exists() or not selected_path.exists():
            print(f"  SKIP {section_id}: missing notes.jsonl or selected.csv")
            continue
        if draft_path.exists() and not force:
            print(f"  SKIP {section_id}: draft.md already exists")
            stats["sections_processed"] += 1
            continue

        notes = load_notes(notes_path)
        selected_bibkeys = load_selected_bibkeys(selected_path)
        current_rate = _existing_coverage_rate(sec_dir / "final.md", selected_bibkeys)
        template = build_structural_template(info)
        paper_notes = build_paper_notes_text(group_notes_by_category(notes))
        extra_guidance = _extra_guidance(section_id, len(selected_bibkeys), current_rate, cfg)

        print(f"\n  {section_id} {info['title']}: {len(notes)} notes, budget={budget}")

        growth_cfg = cfg.get("growth", {})
        best_text = ""
        best_validation = {"count": 0, "rate": 0.0, "pass": False, "budget": budget}
        best_removed = 0
        max_attempts = max(1, int(coverage_cfg.get("draft_retry_attempts", 2)))
        if len(selected_bibkeys) >= int(growth_cfg.get("high_gain_selected_threshold", 140)):
            max_attempts = max(max_attempts, int(growth_cfg.get("high_gain_draft_retry_attempts", max_attempts)))
        for attempt in range(1, max_attempts + 1):
            try:
                draft_text, validation, removed = _draft_attempt(
                    cfg,
                    info,
                    budget,
                    template,
                    paper_notes,
                    selected_bibkeys,
                    extra_guidance,
                    sections_dir,
                    model,
                )
            except Exception as exc:
                print(f"    ERROR on draft attempt {attempt}: {exc}")
                stats["errors"] += 1
                continue

            if removed > 0:
                print(f"    Attempt {attempt}: removed {removed} hallucinated citations")

            print(
                f"    Attempt {attempt}: {validation['count']}/{budget} "
                f"({validation['rate']:.0%}) -> {'PASS' if validation['pass'] else 'LOW'}"
            )

            if validation["rate"] > best_validation["rate"]:
                best_text = draft_text
                best_validation = validation
                best_removed = removed

            if validation["pass"]:
                best_text = draft_text
                best_validation = validation
                best_removed = removed
                break

            if attempt < max_attempts:
                stats["retries"] += 1

        if not best_text:
            continue

        if not best_validation["pass"]:
            stats["low_coverage"] += 1
            print(f"    WARNING: draft coverage stayed below target {min_draft_rate:.0%}; saving best attempt for revision")

        comment = (
            f"\n<!-- Citation check: {best_validation['count']}/{budget} papers cited "
            f"({best_validation['rate']:.0%}); threshold={min_draft_rate:.0%}; "
            f"removed_invalid={best_removed} -->\n"
        )
        save_draft(best_text.rstrip() + comment, draft_path)
        update_manifest(sections_dir, section_id)

        stats["sections_processed"] += 1
        stats["total_citations"] += best_validation["count"]

    print(
        f"\nDrafted {stats['sections_processed']} sections, {stats['total_citations']} total citations, "
        f"{stats['low_coverage']} below target"
    )
    return stats


def main():
    parser = argparse.ArgumentParser(description="Stage 3: Generate section drafts")
    parser.add_argument("--chapter", type=int, default=None, help="Only process chapter N")
    parser.add_argument("--section", type=str, default=None, help="Only process section X.Y")
    parser.add_argument("--model", type=str, default=None, help="Override LLM model name")
    parser.add_argument("--force", action="store_true", help="Re-run even if draft.md already exists")
    args = parser.parse_args()

    stats = run(chapter=args.chapter, section=args.section, model=args.model, force=args.force)
    print(f"\nProcessed {stats['sections_processed']} sections")
    print(f"Total citations: {stats['total_citations']}")
    print(f"Low coverage drafts: {stats['low_coverage']}")
    if stats["errors"]:
        print(f"Errors: {stats['errors']}")


if __name__ == "__main__":
    main()
