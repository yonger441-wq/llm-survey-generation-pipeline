"""Stage 0: Parse outline and create section workspace structure.

Parses 0_outline/newoutline.md (## chapters, ### sections, #### sub-items),
creates the 2_sections/ folder tree, writes section_info.json per section
and sections_manifest.json for pipeline tracking.

Usage:
    python scripts/s0_setup.py [--dry-run] [--chapter N]
"""

import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from llm_utils import PROJECT_ROOT, load_config, resolve_path


def parse_outline(outline_path: Path) -> list[dict]:
    """Parse newoutline.md into structured chapters/sections/sub_items."""
    text = outline_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    chapters = []
    current_chapter = None
    current_section = None

    for line in lines:
        stripped = line.strip()

        # ## N. Chapter Title
        m_chapter = re.match(r"^##\s+(\d+)\.\s+(.+)$", stripped)
        if m_chapter:
            ch_num = int(m_chapter.group(1))
            ch_title = m_chapter.group(2).strip()
            current_chapter = {
                "chapter": ch_num,
                "title": ch_title,
                "dir_name": f"{ch_num:02d}_{to_slug(ch_title)}",
                "sections": [],
            }
            chapters.append(current_chapter)
            current_section = None
            continue

        # ### N.M Section Title
        m_section = re.match(r"^###\s+(\d+\.\d+)\s+(.+)$", stripped)
        if m_section and current_chapter is not None:
            sec_id = m_section.group(1)
            sec_title = m_section.group(2).strip()
            # Extract chapter.section numbers
            parts = sec_id.split(".")
            ch_part = parts[0]
            sec_part = parts[1]
            dir_name = f"{ch_part}_{sec_part}_{to_slug(sec_title)}"
            current_section = {
                "section": sec_id,
                "chapter": current_chapter["chapter"],
                "title": sec_title,
                "dir_name": dir_name,
                "sub_items": [],
            }
            current_chapter["sections"].append(current_section)
            continue

        # #### N.M.X Sub-item Title
        m_sub = re.match(r"^####\s+(\d+\.\d+\.\d+)\s+(.+)$", stripped)
        if m_sub and current_section is not None:
            sub_id = m_sub.group(1)
            sub_title = m_sub.group(2).strip()
            current_section["sub_items"].append({
                "id": sub_id,
                "title": sub_title,
                "writing_guide": f"Cover: {sub_title}",
            })

    return chapters


def to_slug(title: str) -> str:
    """Convert a title to a filesystem-safe slug."""
    slug = title.lower()
    # Remove special characters, keep alphanumeric and spaces
    slug = re.sub(r"[^\w\s-]", "", slug)
    # Replace spaces and consecutive hyphens with single underscore
    slug = re.sub(r"[\s-]+", "_", slug)
    slug = slug.strip("_")
    return slug


def build_section_info(section: dict, sections_list: list[dict]) -> dict:
    """Build section_info.json content for one section."""
    idx = next(i for i, s in enumerate(sections_list) if s["section"] == section["section"])
    prev_sec = sections_list[idx - 1]["section"] if idx > 0 else None
    next_sec = sections_list[idx + 1]["section"] if idx < len(sections_list) - 1 else None

    return {
        "chapter": section["chapter"],
        "section": section["section"],
        "title": section["title"],
        "goal": f"Survey section covering {section['title']}",
        "sub_items": section["sub_items"],
        "prev_section": prev_sec,
        "next_section": next_sec,
        "budget": None,
    }


def build_manifest_entry(section: dict) -> dict:
    """Build one manifest entry for sections_manifest.json."""
    return {
        "chapter": section["chapter"],
        "section": section["section"],
        "title": section["title"],
        "budget": None,
        "status": {
            "s0_setup": "done",
            "s1_candidates": "pending",
            "s2_annotate": "pending",
            "s3_draft": "pending",
            "s4_final": "pending",
            "s5_checks": "pending",
        },
    }


def run(dry_run: bool = False, chapter: int | None = None) -> dict:
    """Execute setup. Returns summary stats."""
    cfg = load_config()
    outline_path = resolve_path(cfg, "outline_file")
    sections_dir = resolve_path(cfg, "sections_dir")

    if not outline_path.exists():
        raise FileNotFoundError(f"Outline file not found: {outline_path}")

    # Parse outline
    chapters = parse_outline(outline_path)

    # Filter to specific chapter if requested
    if chapter is not None:
        chapters = [ch for ch in chapters if ch["chapter"] == chapter]
        if not chapters:
            raise ValueError(f"Chapter {chapter} not found in outline")

    # Build flat section list for prev/next linking
    all_sections = []
    for ch in chapters:
        all_sections.extend(ch["sections"])

    # Stats
    stats = {
        "chapters": len(chapters),
        "sections": len(all_sections),
        "sub_items": sum(len(s["sub_items"]) for s in all_sections),
    }

    if dry_run:
        print(f"[DRY RUN] Would create structure for {stats['chapters']} chapters, "
              f"{stats['sections']} sections, {stats['sub_items']} sub-items")
        for ch in chapters:
            print(f"  Ch {ch['chapter']}: {ch['title']} ({len(ch['sections'])} sections)")
            for sec in ch["sections"]:
                print(f"    {sec['section']} {sec['title']} ({len(sec['sub_items'])} items)")
        return stats

    # Archive existing 2_sections/
    if sections_dir.exists():
        archive_dir = sections_dir.parent / "2_sections_archive"
        if archive_dir.exists():
            # Remove old archive
            shutil.rmtree(archive_dir)
        shutil.move(str(sections_dir), str(archive_dir))
        print(f"Archived {sections_dir} → {archive_dir}")

    # Create directory tree and write files
    manifest_entries = []

    for ch in chapters:
        ch_dir = sections_dir / ch["dir_name"]
        ch_dir.mkdir(parents=True, exist_ok=True)

        for sec in ch["sections"]:
            sec_dir = ch_dir / sec["dir_name"]
            sec_dir.mkdir(parents=True, exist_ok=True)

            # Write section_info.json
            info = build_section_info(sec, all_sections)
            info_path = sec_dir / "section_info.json"
            info_path.write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n",
                                 encoding="utf-8")

            manifest_entries.append(build_manifest_entry(sec))

    # Write sections_manifest.json
    manifest_path = sections_dir / "sections_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest_entries, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Create reports/ and 4_output/chapters/ directories
    reports_dir = resolve_path(cfg, "reports_dir") if "reports_dir" in cfg else PROJECT_ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    output_chapters = resolve_path(cfg, "output_dir") / "chapters"
    output_chapters.mkdir(parents=True, exist_ok=True)

    print(f"Created {stats['chapters']} chapters, {stats['sections']} sections, "
          f"{stats['sub_items']} sub-items under {sections_dir}")
    print(f"Manifest: {manifest_path}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Stage 0: Parse outline and create workspace")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without executing")
    parser.add_argument("--chapter", type=int, default=None, help="Only process chapter N")
    args = parser.parse_args()

    stats = run(dry_run=args.dry_run, chapter=args.chapter)

    if not args.dry_run:
        print("\nVerification:")
        sections_dir = resolve_path(load_config(), "sections_dir")
        manifest_path = sections_dir / "sections_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        print(f"  Manifest entries: {len(manifest)}")
        # Verify every section has section_info.json
        missing = 0
        for entry in manifest:
            sec_id = entry["section"]
            # Find section_info.json using broader glob
            info_files = list(sections_dir.rglob(f"*/section_info.json"))
            found = any(
                json.loads(p.read_text(encoding="utf-8")).get("section") == sec_id
                for p in info_files
            )
            if not found:
                missing += 1
        if missing:
            print(f"  WARNING: {missing} sections missing section_info.json")
        else:
            print(f"  All {len(manifest)} sections have section_info.json OK")


if __name__ == "__main__":
    main()
