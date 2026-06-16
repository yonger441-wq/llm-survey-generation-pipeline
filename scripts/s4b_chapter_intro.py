"""Stage 4b: Generate chapter introductions with cross-chapter links.

For each chapter, read all section final.md files, render
chapter_intro_prompt.md with chapter and neighbor info, call LLM,
and save as chapter_intro.md in the chapter directory.

Usage:
    python scripts/s4b_chapter_intro.py [--chapter N] [--model MODEL]
"""

import argparse
import json
from pathlib import Path

from llm_utils import (
    PROJECT_ROOT,
    call_llm,
    load_config,
    render_prompt_file,
    resolve_path,
)


def find_chapter_dirs(sections_dir: Path, chapter: int | None = None) -> list[Path]:
    """Find chapter directories (containing at least one section_info.json)."""
    chapters = {}
    for info_path in sections_dir.rglob("section_info.json"):
        info = json.loads(info_path.read_text(encoding="utf-8"))
        ch = info["chapter"]
        if chapter is not None and ch != chapter:
            continue
        ch_dir = info_path.parent.parent
        if ch not in chapters:
            chapters[ch] = ch_dir
    return [chapters[k] for k in sorted(chapters.keys())]


def get_section_dirs(chapter_dir: Path) -> list[Path]:
    """Get section directories within a chapter, ordered by section number."""
    dirs = []
    for info_path in sorted(chapter_dir.rglob("section_info.json")):
        dirs.append(info_path.parent)
    return dirs


def get_chapter_title(chapter_dir: Path) -> str:
    """Extract chapter title from directory name (NN_title)."""
    name = chapter_dir.name
    # Pattern: 02_foundations_of_large_language_models
    parts = name.split("_", 1)
    if len(parts) > 1:
        return parts[1].replace("_", " ").title()
    return name


def find_neighbor_title(sections_dir: Path, chapter_num: int, offset: int) -> str:
    """Find the title of a neighboring chapter."""
    target = chapter_num + offset
    for info_path in sections_dir.rglob("section_info.json"):
        info = json.loads(info_path.read_text(encoding="utf-8"))
        if info["chapter"] == target:
            return info.get("title", "")
    return ""


def build_section_list(section_dirs: list[Path]) -> str:
    """Build a list of section titles and summaries."""
    parts = []
    for sd in section_dirs:
        info = json.loads((sd / "section_info.json").read_text(encoding="utf-8"))
        parts.append(f"- {info['section']}: {info['title']}")
    return "\n".join(parts)


def build_section_contents(section_dirs: list[Path]) -> str:
    """Read and concatenate section final.md contents."""
    parts = []
    for sd in section_dirs:
        final_path = sd / "final.md"
        if final_path.exists():
            text = final_path.read_text(encoding="utf-8").strip()
            if text:
                parts.append(text)
    return "\n\n---\n\n".join(parts)


def run(chapter: int | None = None, model: str | None = None,
        sections_dir: Path | None = None, dry_run: bool = False) -> dict:
    """Generate chapter introductions. Returns summary stats."""
    cfg = load_config()
    if sections_dir is None:
        sections_dir = resolve_path(cfg, "sections_dir")
    else:
        sections_dir = Path(sections_dir)

    if not sections_dir.exists():
        raise FileNotFoundError(f"Sections directory not found: {sections_dir}")

    chapter_dirs = find_chapter_dirs(sections_dir, chapter)
    if not chapter_dirs:
        raise ValueError("No matching chapters found")

    stats = {"chapters_processed": 0, "errors": 0}

    for ch_dir in chapter_dirs:
        section_dirs = get_section_dirs(ch_dir)
        if not section_dirs:
            continue

        # Determine chapter number from first section
        first_info = json.loads((section_dirs[0] / "section_info.json").read_text(encoding="utf-8"))
        ch_num = first_info["chapter"]
        ch_title = get_chapter_title(ch_dir)

        intro_path = ch_dir / "chapter_intro.md"
        if intro_path.exists():
            print(f"  SKIP Ch {ch_num}: chapter_intro.md exists")
            stats["chapters_processed"] += 1
            continue

        # Check if any sections have final.md
        has_finals = any((sd / "final.md").exists() for sd in section_dirs)
        if not has_finals:
            print(f"  SKIP Ch {ch_num}: no section finals yet")
            continue

        print(f"\n  Ch {ch_num} {ch_title}: generating intro ({len(section_dirs)} sections)")

        if dry_run:
            print(f"    [DRY RUN] Would generate chapter_intro.md")
            stats["chapters_processed"] += 1
            continue

        # Build prompt variables
        section_list = build_section_list(section_dirs)
        section_contents = build_section_contents(section_dirs)

        # Truncate section_contents if too long (keep within reason for LLM context)
        max_chars = 12000
        if len(section_contents) > max_chars:
            section_contents = section_contents[:max_chars] + "\n\n[...truncated...]"

        prev_title = find_neighbor_title(sections_dir, ch_num, -1)
        next_title = find_neighbor_title(sections_dir, ch_num, 1)

        replacements = {
            "CHAPTER_TITLE": ch_title,
            "PREV_CHAPTER_TITLE": prev_title or "N/A (first chapter)",
            "NEXT_CHAPTER_TITLE": next_title or "N/A (last chapter)",
            "SECTION_LIST": section_list,
            "SECTION_CONTENTS": section_contents,
        }

        prompts_dir = resolve_path(cfg, "prompts_dir") if "prompts_dir" in cfg else None
        prompt = render_prompt_file("chapter_intro_prompt", replacements, prompts_dir=prompts_dir)

        try:
            intro_text = call_llm(prompt, cfg=cfg, model=model)
        except Exception as e:
            print(f"    ERROR: {e}")
            stats["errors"] += 1
            continue

        intro_path.write_text(intro_text, encoding="utf-8")
        print(f"    Saved chapter_intro.md")
        stats["chapters_processed"] += 1

    print(f"\nGenerated {stats['chapters_processed']} chapter intros")
    return stats


def main():
    parser = argparse.ArgumentParser(description="Stage 4b: Generate chapter introductions")
    parser.add_argument("--chapter", type=int, default=None, help="Only process chapter N")
    parser.add_argument("--model", type=str, default=None, help="Override LLM model name")
    args = parser.parse_args()

    stats = run(chapter=args.chapter, model=args.model)
    print(f"\nProcessed {stats['chapters_processed']} chapters")
    if stats["errors"]:
        print(f"Errors: {stats['errors']}")


if __name__ == "__main__":
    main()
